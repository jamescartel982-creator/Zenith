from pathlib import Path
import json,csv,re,subprocess,collections
from urllib.parse import unquote
ROOT=Path(__file__).resolve().parents[1];E=ROOT/'evidence';R=ROOT/'reports'
roots={'openclaw':Path('/workspace/openclaw-review-20261025/openclaw'),'hermes':ROOT/'hermes-agent','zenith-main':ROOT/'zenith-main','zenith-pr19':Path('/workspace/zenith-platform'),'zenith-pr18':Path('/workspace/Zenith')}
meta=json.loads((E/'repositories.json').read_text());rows=json.loads((E/'master-feature-matrix.json').read_text());plan=json.loads((E/'file-by-file-plan.json').read_text());summary=json.loads((E/'catalog-summary.json').read_text())
checks={};checks['unique_matrix_ids']=len({r['id'] for r in rows})==len(rows)==summary['rows']
checks['allowed_statuses']=all(r['status'] in {'NOT STARTED','PARTIAL','IMPLEMENTED','VERIFIED','BLOCKED'} for r in rows)
checks['status_counts']=dict(collections.Counter(r['status'] for r in rows))==summary['by_status']
checks['types_match']=dict(collections.Counter(r['entry_type'] for r in rows))==summary['by_entry_type']
with (R/'MASTER_FEATURE_PARITY_MATRIX.csv').open() as f:csvrows=list(csv.DictReader(f))
checks['csv_json_equal']=len(csvrows)==len(rows) and all(a['id']==b['id'] and a['status']==b['status'] for a,b in zip(rows,csvrows))
checks['applicability_recorded']=all(r.get('applicability_review') for r in rows)
seen={};count=0
for row in rows:
 for s in row['sources']:
  key=(s['repository'],s['path']);path=roots[s['repository']]/s['path'];assert path.is_file(),key
  if key not in seen:seen[key]=len(path.read_text(errors='replace').splitlines())
  assert 1<=s['line']<=max(1,seen[key]),s
  assert s['commit']==meta[s['repository']]['commit'],s
  count+=1
checks['all_matrix_citations_resolve']=True
for fn in ('report-source-citations.json','design-source-citations.json'):
 for s in json.loads((E/fn).read_text()):
  path=roots[s['repository']]/s['path'];text=path.read_text(errors='replace');assert path.is_file() and 1<=s['line']<=len(text.splitlines())
  if s.get('needle'):assert s['needle'] in text
checks['report_helper_citations_resolve']=True
source_url=re.compile(r'https://github.com/([^/]+/[^/]+)/blob/([a-f0-9]{40})/([^\s)#]+)(?:#L(\d+))?')
repo_names={'openclaw/openclaw':'openclaw','NousResearch/hermes-agent':'hermes','jamescartel982-creator/Zenith':'zenith-main'}
report_links=0
for doc in list(R.glob('*.md'))+[ROOT/'README.md']:
 text=doc.read_text()
 for repo,sha,name,line in source_url.findall(text):
  project=repo_names[repo]
  if repo=='jamescartel982-creator/Zenith' and sha==meta['zenith-pr19']['commit']:project='zenith-pr19'
  if repo=='jamescartel982-creator/Zenith' and sha.startswith('ac989d8'):project='zenith-pr18'
  assert subprocess.check_output(['git','-C',str(roots[project]),'rev-parse','HEAD'],text=True).strip()==sha
  path=roots[project]/unquote(name);assert path.is_file(),(doc,name)
  if line:assert int(line)<=len(path.read_text(errors='replace').splitlines())
  report_links+=1
 for url in re.findall(r'\]\(([^)]+)\)',text):
  if url.startswith(('http:','https:','#','mailto:')):continue
  path=(doc.parent/unquote(url.split('#')[0])).resolve();assert path.exists(),(doc,url)
checks['markdown_local_and_pinned_links_resolve']=True
files=plan['files'];checks['unique_destinations']=len({x['destination'] for x in files})==len(files)
checks['all_file_contracts_present']=all(all(x.get(k) for k in ('groups','expected_behavior','tests','acceptance','feature_flag','rollback')) for x in files)
order=plan['group_order'];assert set(order)==set(plan['groups'])
checks['dependency_graph_acyclic']=all(order.index(d)<order.index(k) for k,v in plan['groups'].items() for d in v['deps'])
checks['all_group_tests_have_destinations']=all(t in {x['destination'] for x in files} for g in plan['groups'].values() for t in g['tests'])
checks['new_parity_not_claimed_verified']=summary['verified_new_parity_features']==0 and not any(x['status']=='VERIFIED' for x in rows)
assert all(checks.values()),{k:v for k,v in checks.items() if not v}
result={'purpose':'Audit artifact integrity, not acceptance of proposed platform code','checks':checks,'matrix_rows':len(rows),'source_citation_occurrences':count,'unique_source_files':len(seen),'report_pinned_source_links':report_links,'proposed_destinations':len(files),'proposed_test_destinations':sum(x['destination'].startswith('tests/') for x in files),'all_passed':True}
(E/'delivery-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
