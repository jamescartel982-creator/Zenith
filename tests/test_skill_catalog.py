"""Pack validation, atomic imports, access boundaries and real FTS pagination."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
from uuid import uuid4

from fastapi.testclient import TestClient
from agent.config import Settings
from agent.core import Agent
from agent.server import create_app
from agent.skill_catalog import SkillCatalog
from agent.skills import get_skill
from agent.storage import Store


def pack_header(pack='checks'):
    return {'kind':'zenith-skill-pack','schema_version':1,'pack_id':pack,'license':'Apache-2.0',
        'source':'local-authored','source_revision':'test-fixture-v1','reviewed':True}


def example(index=0,pack='checks',security=False):
    profile=get_skill('general');profile.pop('resources',None)
    profile.update(id=f'x-{pack}-case{index:06d}',name=f'Case {index}',instruction=f'Inspect the supplied synthetic case {index} and check its evidence.')
    if security:profile.update(category='security',access='admin')
    return profile


def write_pack(path,rows,header=None):
    with Path(path).open('w',encoding='utf-8') as stream:
        for item in [header or pack_header(),*rows]:stream.write(json.dumps(item)+'\n')


class SkillCatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=Store(self.temp.name);self.catalog=SkillCatalog(self.store)
        self.file=Path(self.temp.name)/'pack.jsonl'

    def test_default_reads_create_no_library_and_capacity_is_not_a_fake_count(self):
        self.assertEqual(self.catalog.status()['installed_profiles'],0)
        self.assertEqual(self.catalog.status()['capacity'],100000)
        self.assertEqual(self.catalog.search()['skills'],[])
        with self.store.connect() as db:self.assertIsNone(db.execute("SELECT 1 FROM sqlite_master WHERE name='skill_pack_profiles'").fetchone())

    def test_atomic_import_pagination_search_and_remove(self):
        write_pack(self.file,[example(i) for i in range(5)])
        with self.assertRaises(PermissionError):self.catalog.install(self.file)
        result=self.catalog.install(self.file,True)
        self.assertEqual(result['installed'],5)
        first=self.catalog.search(limit=2);second=self.catalog.search(after=first['next'],limit=2)
        self.assertFalse({p['id'] for p in first['skills']} & {p['id'] for p in second['skills']})
        self.assertEqual(self.catalog.search('case000004')['skills'][0]['id'],'x-checks-case000004')
        self.assertEqual(self.catalog.get('x-checks-case000000')['origin'],'operator-imported-instruction-profile')
        with self.assertRaises(ValueError):self.catalog.install(self.file,True)
        self.assertEqual(self.catalog.remove('checks',True),5)
        self.assertEqual(self.catalog.search()['skills'],[])

    def test_bad_late_row_rolls_back_pack_and_profiles(self):
        bad=example(1);bad['access']='admin'
        write_pack(self.file,[example(),bad])
        with self.assertRaises(ValueError):self.catalog.install(self.file,True)
        self.assertEqual(self.catalog.status()['installed_profiles'],0)

    def test_wrong_namespace_unknown_resources_executable_fields_and_duplicates_rejected(self):
        cases=[]
        for key,value in [('id','general'),('resource_ids',['unknown']),('kind','executable-plugin'),('shell','rm anything')]:
            changed=example();changed[key]=value;cases.append([changed])
        duplicate=example(1);duplicate['instruction']=example()['instruction'].upper()
        cases.append([example(),duplicate])
        for rows in cases:
            with self.subTest(rows=rows):
                write_pack(self.file,rows)
                with self.assertRaises(ValueError):self.catalog.install(self.file,True)
                self.assertEqual(self.catalog.status()['installed_profiles'],0)

    def test_security_rows_hidden_without_admin_and_queries_are_not_sql(self):
        write_pack(self.file,[example(),example(1,security=True)])
        self.catalog.install(self.file,True)
        self.assertEqual(self.catalog.status()['installed_profiles'],1)
        self.assertEqual(self.catalog.status(True)['installed_profiles'],2)
        self.assertEqual(self.catalog.search(category='security')['skills'],[])
        self.assertEqual(len(self.catalog.search(category='security',include_admin=True)['skills']),1)
        self.assertEqual(self.catalog.search('" OR 1=1 --')['skills'],[])
        with self.assertRaises(ValueError):self.catalog.search(limit=100001)

    def test_pack_capacity_enforced_transactionally(self):
        from unittest.mock import patch
        write_pack(self.file,[example(i) for i in range(3)])
        with patch('agent.skill_catalog.CAPACITY',2):
            with self.assertRaises(ValueError):self.catalog.install(self.file,True)
        self.assertEqual(self.catalog.status()['installed_profiles'],0)

    def test_http_selection_uses_imported_instructions_and_preserves_security_gate(self):
        provider=Mock();provider.generate.side_effect=lambda messages:('Fixture answer',messages)
        settings=replace(Settings(),data_dir=self.temp.name,api_token='',provider='huggingface')
        agent=Agent(settings,provider,store=self.store)
        write_pack(self.file,[example(),example(1,security=True)])
        agent.skills.catalog.install(self.file,True)
        client=TestClient(create_app(settings,agent),base_url='http://127.0.0.1')
        client.post('/api/account/register',json={'username':'reader','display_name':'Reader','password':'temporary test account password'}).raise_for_status()
        session=str(uuid4())
        data=client.get('/api/skills/search').json()
        self.assertEqual([p['id'] for p in data['skills']],['x-checks-case000000'])
        self.assertEqual(client.get('/api/skills/profile/x-checks-case000001').status_code,403)
        response=client.post('/api/skills/command',json={'session_id':session,'command':'/skill x-checks-case000000'})
        self.assertEqual(response.status_code,200,response.text)
        response=client.post('/api/chat',json={'session_id':session,'message':'Explain this example.'})
        self.assertEqual(response.status_code,200,response.text)
        self.assertIn('synthetic case 0',provider.generate.call_args.args[0][0]['content'])
        self.assertIn('untrusted task guidance',provider.generate.call_args.args[0][0]['content'])
        agent.skills.catalog.remove('checks',True)
        self.assertEqual(client.get('/api/skills/current',params={'session_id':session}).json()['skill'],'general')


if __name__=='__main__':unittest.main()
