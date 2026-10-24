"""Authored retention repairs without importing diagnostic answers as examples."""
import argparse
import ast
import json
from pathlib import Path
from agent.checkpoints import digest
from agent.curriculum import prepare,row_keys,canonical,assert_disjoint
from agent.learning import load_examples,write_jsonl


def build(output,previous):
    output=Path(output);previous=Path(previous)
    if output.exists():raise ValueError('Use a new immutable curriculum directory')
    rows=[];revision=digest(__file__)
    def add(topic,prompt,answer):
        identifier=f'stability-{topic}-{len(rows):03d}'
        rows.append({'id':identifier,'document_id':identifier,'topic':topic,'source_id':'zenith-authored-stability',
            'source_revision':revision,'license':'Apache-2.0','approved_for_training':True,
            'review_note':'Authored regression-concept curriculum; code parses and JSON schemas are checked. Public development diagnostics guided topic selection.',
            'messages':[{'role':'system','content':'You are Zenith. Follow instructions accurately and respect authorization.'},
                        {'role':'user','content':prompt},{'role':'assistant','content':answer}]})
    for i,name in enumerate(['combine','sum_pair','total_pair','merge_values','pair_sum','joined_total','multiply_pair','pair_product','times_two_values','difference','subtract_pair','net_value']):
        left,right=[('x','y'),('left','right'),('first','second')][i%3]
        operator='+' if i<6 else '*' if i<9 else '-'
        answer=f'def {name}({left}, {right}):\n    return {left} {operator} {right}'
        ast.parse(answer)
        add('python-functions',f'Write only Python code for function {name}({left}, {right}) returning {left} {operator} {right}. Include the function definition.',answer)
    for i in range(12):
        tool='sha256' if i%2==0 else 'calculator';value=f'archive-entry-{i+20}' if i%2==0 else f'{i+30}+14'
        answer=json.dumps({'tool':tool,'arguments':{'text':value}});json.loads(answer)
        add('tool-schemas',f'Return only JSON selecting the existing {tool} tool. Its schema is {{"tool":string,"arguments":{{"text":string}}}}. Supply {value!r} as text.',answer)
    history=[
        ('Define sexagesimal notation.','Sexagesimal is a base-60 numeral system, with digit values from 0 through 59.'),
        ('What digit values are used in a sexagesimal place?','A base-60 place may contain a digit from 0 through 59.'),
        ('Convert sexagesimal digits [1, 5] to decimal.','1*60 + 5 = 65.'),
        ('Express decimal 120 using sexagesimal digits.','120 equals [2, 0] in base 60, because 2*60 + 0 = 120.'),
        ('How many seconds are in three minutes?','Three minutes contain 3*60 = 180 seconds.'),
        ('Describe the positional value of the third sexagesimal place from the right.','Its value is 60 squared, or 3600, times the digit in that place.'),
        ('How does sexagesimal notation differ from decimal notation?','Sexagesimal uses base 60; decimal uses base 10.'),
        ('Which ancient Mesopotamian mathematical tradition is associated with sexagesimal place value?','Babylonian mathematics used sexagesimal, or base-60, place-value notation.'),
        ('Describe a historical connection between sexagesimal arithmetic and modern timekeeping.','The base-60 sexagesimal tradition is reflected in sixty seconds per minute and sixty minutes per hour.'),
        ('What is the radix of binary notation?','Binary uses base 2.'),
        ('What is the radix of hexadecimal notation?','Hexadecimal uses base 16.'),
        ('Compare base-20 notation with sexagesimal notation.','Base-20 notation has radix 20, whereas sexagesimal notation has radix 60.')]
    for prompt,answer in history:add('numeral-systems',prompt,answer)
    custody=[
        'Name the documented sequence of evidence possession and transfers.',
        'Why is a chain of custody important to forensic evidence?',
        'How should investigators document a transfer of forensic evidence?',
        'Which forensic record identifies each evidence custodian and transfer time?',
        'Describe the chain of custody for a seized storage device.',
        'What connects an evidence artifact to its chronological handling record?',
        'Name the forensic process that documents evidence handlers and integrity checks.',
        'How can a forensic team establish continuity of evidence possession?',
        'Explain evidence custody tracking in one sentence.',
        'Which record supports accountability when physical evidence changes hands?',
        'What should accompany a verified copy of digital evidence?',
        'How should an analyst record who acquired, transferred, and analyzed an evidence image?']
    for prompt in custody:add('evidence-custody',prompt,'Maintain a chain of custody: record who acquired or handled the evidence, timestamps, transfers, and integrity checks. Preserve the original and analyze verified copies.')
    from agent.expansion_eval import CASES
    from scripts.evaluate_recovery_holdout import CASES as TRANSFER
    forbidden={('prompt',canonical(case[2])) for case in [*CASES,*TRANSFER]}
    repo=Path(__file__).resolve().parents[1]
    protected=[previous,repo/'docs/benchmarks/continuation-v1/dataset',repo/'docs/benchmarks/recovery-v1/dataset']
    for dataset in protected:
        if dataset.exists():
            for name in ['validation','test']:
                for row in load_examples(dataset/(name+'.jsonl')):forbidden.update(row_keys(row))
    if any(row_keys(row)&forbidden for row in rows):raise ValueError('Source overlaps a protected evaluation prompt')
    output.parent.mkdir(parents=True,exist_ok=True);source=output.parent/(output.name+'-source.jsonl');write_jsonl(source,rows)
    manifest=prepare(source,output,seed=101)
    replay=[{**row,'retention_replay':True} for row in load_examples(previous/'train.jsonl')]
    partitions={name:load_examples(output/(name+'.jsonl')) for name in ['train','validation','test']}
    partitions['train'].extend(replay);assert_disjoint(partitions)
    write_jsonl(output/'train.jsonl',partitions['train']);write_jsonl(output/'historical-train-replay.jsonl',replay)
    manifest['files']['train'].update(rows=len(partitions['train']),sha256=digest(output/'train.jsonl'))
    manifest['files']['train']['topics']={t:sum(r['topic']==t for r in partitions['train']) for t in sorted({r['topic'] for r in partitions['train']})}
    manifest['replay']={'path':'historical-train-replay.jsonl','snapshot_sha256':digest(output/'historical-train-replay.jsonl'),'source_sha256':digest(previous/'train.jsonl'),'rows':len(replay),'partition':'train-only'}
    manifest['limitations']=['Public diagnostic failures guided concept selection; diagnostic score is development evidence.','New authored examples are small and include related forms; separate transfer probes and retained evaluation remain necessary.']
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
    return manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--previous',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(build(args.output,args.previous),indent=2))


if __name__=='__main__':main()
