"""Real temporary 100k-profile load and CSV timing; never installs fake skills."""
import argparse
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import tempfile
import time


def measure():
    from agent.data_analysis import analyze_csv
    from agent.skill_catalog import SkillCatalog
    from agent.skills import get_skill
    from agent.storage import Store
    watched=['agent/data_analysis.py','agent/skill_catalog.py','agent/skills.py','agent/resources/skills-v1.json']
    hashes={name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in watched}
    with tempfile.TemporaryDirectory(prefix='zenith-productivity-load-') as folder:
        path=Path(folder)/'synthetic-load-only.jsonl'
        profile=get_skill('general');profile.pop('resources',None)
        with path.open('w',encoding='utf-8',newline='\n') as handle:
            header={'kind':'zenith-skill-pack','schema_version':1,'pack_id':'scale','license':'Apache-2.0',
                    'source':'local-authored','source_revision':'synthetic-load-test-v1','reviewed':True}
            handle.write(json.dumps(header)+'\n')
            for index in range(100000):
                row=deepcopy(profile)
                row.update(id=f'x-scale-case{index:06d}',name=f'Synthetic case {index}',
                    instruction=f'Inspect synthetic load-test record {index}; this is not a curated production skill.')
                if index%10==0:row.update(category='security',access='admin')
                handle.write(json.dumps(row)+'\n')
        catalog=SkillCatalog(Store(Path(folder)/'temporary-state'))
        started=time.perf_counter();receipt=catalog.install(path,True);import_seconds=time.perf_counter()-started
        assert receipt['installed']==100000 and catalog.status(True)['installed_profiles']==100000
        assert catalog.status()['installed_profiles']==90000
        first=catalog.search(limit=25);second=catalog.search(after=first['next'],limit=25)
        assert not {row['id'] for row in first['skills']} & {row['id'] for row in second['skills']}
        assert catalog.search('case000000')['skills']==[]
        assert catalog.search('case000000',include_admin=True)['skills'][0]['id']=='x-scale-case000000'
        searches=[]
        for _ in range(9):
            started=time.perf_counter();found=catalog.search('case099999');searches.append((time.perf_counter()-started)*1000)
            assert [row['id'] for row in found['skills']]==['x-scale-case099999']
        data='value,weight\n'+''.join(f'{index},0.1\n' for index in range(1,10001))
        timings=[]
        for _ in range(5):
            started=time.perf_counter();result=analyze_csv(data);timings.append((time.perf_counter()-started)*1000)
            assert result['rows']==10000 and result['duplicate_rows']==0
            assert Decimal(result['column_summaries'][0]['sum'])==10000*10001//2
            assert Decimal(result['column_summaries'][1]['sum'])==Decimal(1000)
        if any(hashlib.sha256(Path(name).read_bytes()).hexdigest()!=digest for name,digest in hashes.items()):
            raise RuntimeError('Benchmark source changed during measurement')
        return {'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
                'source_sha256':hashes,'synthetic_profiles_for_load_test':100000,'production_profiles_added':0,
                'import_seconds':import_seconds,'search_median_ms':statistics.median(searches),'search_samples_ms':searches,
                'public_profile_count':90000,'restricted_profile_count':10000,'security_filter_passed':True,
                'pagination_disjoint':True,'csv_fixture_sha256':hashlib.sha256(data.encode()).hexdigest(),
                'csv_rows':10000,'csv_columns':2,'csv_median_ms':statistics.median(timings),'csv_samples_ms':timings,
                'csv_exact_sums_verified':True,'model_calls':0,'training_performed':False,
                'limitations':['Synthetic load profiles exist only in removed test-owned state, not in the installed skill library.',
                    'No previous CSV engine baseline exists; these are measured new-path timings, not an overall model speedup.',
                    'Single CPU host; no GPU, frontier intelligence or general accuracy claim.']}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    from agent.config import Settings
    from agent.paths import config_file
    from scripts.platform_protection import check_destination
    try:args.output=check_destination(Settings(),config_file(),args.output)
    except ValueError as exc:parser.error(str(exc))
    report=measure()
    with args.output.open('x') as handle:json.dump(report,handle,indent=2);handle.write('\n')
    print(json.dumps(report,indent=2))
