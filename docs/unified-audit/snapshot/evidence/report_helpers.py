from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]; E=ROOT/'evidence'; R=ROOT/'reports'
META=json.loads((E/'repositories.json').read_text());ROWS=json.loads((E/'master-feature-matrix.json').read_text());PLAN=json.loads((E/'file-by-file-plan.json').read_text());SUMMARY=json.loads((E/'catalog-summary.json').read_text())
ROOTS={'hermes':ROOT/'hermes-agent','openclaw':Path('/workspace/openclaw-review-20261025/openclaw'),'zenith-main':ROOT/'zenith-main','zenith-pr19':Path('/workspace/zenith-platform')}
REPOS={'hermes':'NousResearch/hermes-agent','openclaw':'openclaw/openclaw','zenith-main':'jamescartel982-creator/Zenith','zenith-pr19':'jamescartel982-creator/Zenith'}
CITATIONS=[]
def ref(project,path,needle=None):
 p=ROOTS[project]/path;assert p.is_file(),(project,path)
 text=p.read_text(encoding='utf8',errors='replace');line=1
 if needle:
  assert needle in text,(path,needle)
  line=text.count('\n',0,text.index(needle))+1
 url=f'https://github.com/{REPOS[project]}/blob/{META[project]["commit"]}/{path}#L{line}'
 CITATIONS.append({'repository':project,'commit':META[project]['commit'],'path':path,'line':line,'needle':needle,'url':url})
 return f'[{path}:{line}]({url})'
def h(path,needle=None):return ref('hermes',path,needle)
def o(path,needle=None):return ref('openclaw',path,needle)
def z(path,needle=None):return ref('zenith-main',path,needle)
def p(path,needle=None):return ref('zenith-pr19',path,needle)
def put(name,text):(R/name).write_text(text.strip()+'\n',encoding='utf8')
def cell(value):return str(value).replace('|','\\|').replace('\n',' ')
def table(headers,rows):return '| '+' | '.join(headers)+' |\n| '+' | '.join('---' for _ in headers)+' |\n'+'\n'.join('| '+' | '.join(cell(x) for x in row)+' |' for row in rows)
LEGEND='**Evidence:** S = source-verified code/declaration; D = upstream documentation/policy claim; M = actually measured; P = proposed; H = hypothesis. A manifest, tool schema, doc page or test filename does not prove successful execution. Status describes Zenith parity, not whether a reference project works.'
COMMON=f'''**Date:** 2026-10-25 UTC. **Scope:** audit/design only; further Zenith edits await approval of this expanded project.\n\nOpenClaw `{META['openclaw']['commit']}`; Hermes `{META['hermes']['commit']}`; Zenith main `{META['zenith-main']['commit']}`; unmerged PR #19 `{META['zenith-pr19']['commit']}`.\n\n{LEGEND}'''
