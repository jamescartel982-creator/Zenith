"""Reviewed, versioned datasets with grouped train/validation/final-test isolation."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import random
import re
import unicodedata
from .learning import load_examples, write_jsonl, file_sha256
from .paths import zenith_home

RESOURCE_ROOT=Path(__file__).parent/'resources'
SECRET_PATTERN=re.compile(r'(?:zenith-admin-[A-Za-z0-9_-]{43}|hf_[A-Za-z0-9]{25,}|sk-(?:proj-)?[A-Za-z0-9_-]{30,}|gh[pousr]_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16})')
ALLOWED_LICENSES={'Apache-2.0','MIT','CC0-1.0','CC-BY-4.0','CC-BY-3.0','public-domain'}


def canonical(text):
    text=unicodedata.normalize('NFKC',text).casefold()
    return ' '.join(''.join(c for c in text if unicodedata.category(c)!='Cf').split())


def row_keys(row):
    keys={('document',row.get('document_id') or row.get('conversation_id') or '')}
    keys.discard(('document',''))
    for message in row['messages']:
        if message['role']=='user':keys.add(('prompt',canonical(message['content'])))
    return keys


def validate_rows(rows):
    seen=set();clean=[];duplicates=0;inputs={};topics=defaultdict(int)
    for row in rows:
        if not isinstance(row,dict) or not isinstance(row.get('messages'),list):raise ValueError('Each row needs messages')
        if row.get('approved_for_training') is not True:raise ValueError('Every imported row requires explicit training approval')
        if row.get('license') not in ALLOWED_LICENSES:raise ValueError('Record a supported license/rights basis before training')
        if not all(isinstance(row.get(k),str) and row[k].strip() for k in ['id','source_id','document_id','topic','source_revision']):raise ValueError('Rows need id, source_id, document_id, topic and source_revision')
        messages=row['messages']
        if not 2<=len(messages)<=64 or messages[-1].get('role')!='assistant':raise ValueError('A row needs a final assistant answer and bounded history')
        expected='user'
        for i,message in enumerate(messages):
            if not isinstance(message,dict) or not isinstance(message.get('content'),str) or not message['content'].strip() or len(message['content'])>24000:raise ValueError('Empty or oversized message')
            role=message.get('role')
            if i==0 and role=='system':continue
            if role!=expected:raise ValueError('Chat roles must alternate user and assistant after an optional system message')
            expected='assistant' if expected=='user' else 'user'
            if SECRET_PATTERN.search(message['content']):raise ValueError('A credential-like value was found; remove it before training')
        if any(SECRET_PATTERN.search(message['content']) for message in messages):raise ValueError('A credential-like value was found')
        prompt=json.dumps([(m['role'],canonical(m['content'])) for m in messages[:-1]],ensure_ascii=False)
        answer=canonical(messages[-1]['content'])
        if prompt in inputs and inputs[prompt]!=answer:raise ValueError('Conflicting answers exist for the same normalized context')
        inputs[prompt]=answer
        fingerprint=hashlib.sha256((prompt+'\n'+answer).encode()).hexdigest()
        if fingerprint in seen:duplicates+=1;continue
        seen.add(fingerprint);clean.append(row);topics[row['topic']]+=1
    if not clean:raise ValueError('No approved usable rows')
    return clean,{'input_rows':len(rows),'usable_rows':len(clean),'exact_duplicates_removed':duplicates,'topics':dict(topics)}


def split_rows(rows,seed=42):
    parents=list(range(len(rows)))
    def find(i):
        while parents[i]!=i:parents[i]=parents[parents[i]];i=parents[i]
        return i
    def union(a,b):parents[find(b)]=find(a)
    owners={}
    for i,row in enumerate(rows):
        for key in row_keys(row):
            if key in owners:union(i,owners[key])
            else:owners[key]=i
    groups=defaultdict(list)
    for i,row in enumerate(rows):groups[find(i)].append(row)
    by_topic=defaultdict(list)
    for group in groups.values():by_topic[min(r['topic'] for r in group)].append(group)
    splits={'train':[],'validation':[],'test':[]}
    for topic,parts in sorted(by_topic.items()):
        if len(parts)<3:raise ValueError(f'{topic}: need at least three independent document/prompt groups for three partitions')
        parts.sort(key=lambda group:min(row['id'] for row in group));random.Random(str(seed)+topic).shuffle(parts)
        count=max(1,int(len(parts)*0.2));count=min(count,(len(parts)-1)//2)
        for i,group in enumerate(parts):splits['test' if i<count else 'validation' if i<2*count else 'train'].extend(group)
    assert_disjoint(splits)
    return splits


def assert_disjoint(splits):
    keys={name:set().union(*(row_keys(row) for row in rows)) if rows else set() for name,rows in splits.items()}
    names=list(keys)
    for i,left in enumerate(names):
        for right in names[i+1:]:
            if keys[left]&keys[right]:raise ValueError(f'{left}/{right} contain overlapping document or user-prompt groups')


def prepare(path,output,seed=42,balance_topics=False):
    rows=load_examples(path);rows,quality=validate_rows(rows);splits=split_rows(rows,seed)
    if balance_topics:
        by_topic=defaultdict(list)
        for row in rows:by_topic[row['topic']].append(row)
        count=min(len(values) for values in by_topic.values());selected=[]
        for topic,values in sorted(by_topic.items()):
            values.sort(key=lambda row:row['id']);random.Random(str(seed)+topic).shuffle(values);selected.extend(values[:count])
        quality['topic_balancing']={'rows_per_topic':count,'selected_rows':len(selected),'excluded_for_balance':len(rows)-len(selected)}
        rows=selected;splits=split_rows(rows,seed)
    output=Path(output)
    if output.exists() and any(output.iterdir()):raise ValueError('Dataset output must be empty; versions and final-test sets are immutable')
    output.mkdir(parents=True,exist_ok=True)
    snapshot=output/'source.jsonl';snapshot.write_bytes(Path(path).read_bytes())
    files={}
    for name,values in splits.items():
        target=output/(name+'.jsonl');write_jsonl(target,values)
        files[name]={'path':target.name,'rows':len(values),'sha256':file_sha256(target),'topics':dict((topic,sum(row['topic']==topic for row in values)) for topic in sorted({row['topic'] for row in values}))}
    manifest={'schema_version':1,'source_sha256':file_sha256(path),'source_snapshot':'source.jsonl','seed':seed,'quality':quality,'files':files,'final_test_used_for_training':False,'automatic_promotion':False,
              'limitations':['Original starter examples are a plumbing curriculum, not comprehensive subject training.','Public facts may already be present in the base model pretraining.','Final-test isolation applies to this dataset version, not all unknown upstream training.']}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    return manifest


def audit_directory(path):
    path=Path(path);manifest=json.loads((path/'manifest.json').read_text(encoding='utf-8'));splits={}
    if manifest.get('source_snapshot'):
        source=(path/manifest['source_snapshot']).resolve()
        if source.parent!=path.resolve() or file_sha256(source)!=manifest['source_sha256']:raise ValueError('Versioned source snapshot was modified')
    for name,row in manifest['files'].items():
        target=(path/row['path']).resolve()
        if target.parent!=path.resolve() or file_sha256(target)!=row['sha256']:raise ValueError('A versioned partition was modified or has an unsafe path')
        splits[name]=load_examples(target)
    assert_disjoint(splits)
    return manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['sources','prepare','audit'])
    parser.add_argument('--input',type=Path,default=RESOURCE_ROOT/'starter-v1.jsonl')
    parser.add_argument('--output',type=Path,default=zenith_home()/'curricula'/'starter-v1')
    parser.add_argument('--seed',type=int,default=42)
    parser.add_argument('--balance-topics',action='store_true',help='Version an equally represented subset of approved topic rows')
    args=parser.parse_args()
    try:
        if args.action=='sources':result=json.loads((RESOURCE_ROOT/'sources-v1.json').read_text(encoding='utf-8'))
        elif args.action=='prepare':result=prepare(args.input,args.output,args.seed,args.balance_topics)
        else:result=audit_directory(args.output)
    except (ValueError,OSError,KeyError) as exc:parser.error(str(exc))
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
