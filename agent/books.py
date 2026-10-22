"""Bounded public-domain book snapshots for cited retrieval, separate from training."""
import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import time
import requests
from .config import Settings
from .storage import Store

BOOKS={'euclid':{'title':'The First Six Books of the Elements of Euclid, edited by John Casey',
    'url':'https://www.gutenberg.org/cache/epub/21076/pg21076-images.html',
    'catalog_url':'https://www.gutenberg.org/ebooks/21076','rights_note':'Ancient text and nineteenth-century edition; Project Gutenberg public-domain catalog. Preserve its notices and review local redistribution terms.'}}


class BookText(HTMLParser):
    def __init__(self):super().__init__(convert_charrefs=True);self.parts=[];self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in {'script','style','nav'}:self.skip+=1
        if tag in {'p','div','h1','h2','h3','br'} and not self.skip:self.parts.append('\n')
    def handle_endtag(self,tag):
        if tag in {'script','style','nav'} and self.skip:self.skip-=1
        if tag in {'p','div','h1','h2','h3'} and not self.skip:self.parts.append('\n')
    def handle_data(self,data):
        if not self.skip:self.parts.append(data)


def import_book(identifier,data_dir,max_chunks=300):
    if identifier not in BOOKS or not 1<=max_chunks<=1000:raise ValueError('Select a known book and a 1–1000 chunk limit')
    book=BOOKS[identifier];raw=bytearray();started=time.monotonic()
    with requests.get(book['url'],stream=True,timeout=(10,20)) as response:
        response.raise_for_status()
        for chunk in response.iter_content(65536):
            raw.extend(chunk)
            if len(raw)>5*1024**2 or time.monotonic()-started>60:raise ValueError('Book exceeds the bounded download limits')
    digest=hashlib.sha256(raw).hexdigest();parser=BookText();parser.feed(bytes(raw).decode('utf-8','strict'))
    text='\n'.join(re.sub(r'\s+',' ',line).strip() for line in ''.join(parser.parts).splitlines())
    text=re.sub(r'\n{3,}','\n\n',text).strip()
    if len(text)<1000:raise ValueError('Book extraction did not produce usable text')
    chunks=[text[start:start+6000] for start in range(0,len(text),5700)]
    if len(chunks)>max_chunks:raise ValueError('Book exceeds the explicit chunk limit; select a larger bounded limit')
    folder=Path(data_dir)/'book-snapshots';folder.mkdir(parents=True,exist_ok=True)
    snapshot=folder/(identifier+'-'+digest+'.html');snapshot.write_bytes(raw)
    store=Store(data_dir);source_id='book:'+identifier+':'+digest[:12]
    imported=sum(store.add_document(source_id,book['catalog_url'],chunk) is not None for chunk in chunks)
    report={'book':identifier,'title':book['title'],'source_url':book['url'],'catalog_url':book['catalog_url'],'source_sha256':digest,
            'snapshot_file':snapshot.name,'source_bytes':len(raw),'extracted_characters':len(text),'chunks':len(chunks),
            'new_documents':imported,'rights_note':book['rights_note'],'used_for_weight_training':False,
            'purpose':'Shared cited retrieval; original file and notices retained.'}
    (folder/(identifier+'-'+digest+'.json')).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('book',choices=BOOKS)
    parser.add_argument('--data-dir',default=Settings().data_dir)
    parser.add_argument('--max-chunks',type=int,default=300)
    args=parser.parse_args()
    try:report=import_book(args.book,args.data_dir,args.max_chunks)
    except (OSError,ValueError,requests.RequestException) as exc:parser.error(str(exc))
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
