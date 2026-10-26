import tempfile
import unittest
from unittest.mock import Mock
from uuid import uuid4
from fastapi.testclient import TestClient
from agent.core import Agent
from agent.config import Settings
from agent.server import create_app


class SummaryTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.provider=Mock();self.provider.generate.side_effect=lambda messages:('Build passed. Owner approval is pending.',messages)
        self.agent=Agent(Settings(provider='ollama',data_dir=self.folder.name),self.provider)
        app=create_app(self.agent.settings,self.agent)
        self.owner=TestClient(app, base_url="http://127.0.0.1");self.other=TestClient(app, base_url="http://127.0.0.1")
        for client,name in [(self.owner,'owner'),(self.other,'other')]:
            client.post('/api/account/register',json={'username':name,'display_name':name,'password':'a good fixture password'})
        self.session=str(uuid4())
        self.owner.post('/api/chat',json={'session_id':self.session,'message':'Please review the release status.'})

    def test_summary_is_explicit_owned_context_and_not_a_weight_update(self):
        path='/api/conversations/'+self.session+'/summary'
        self.assertIsNone(self.owner.get(path).json()['summary'])
        result=self.owner.post(path)
        self.assertEqual(result.status_code,200,result.text)
        self.assertFalse(result.json()['weight_update'])
        self.assertIn('approval',result.json()['summary']['summary'])
        self.assertEqual(self.other.get(path).status_code,404)
        self.assertEqual(self.other.post(path).status_code,404)
        self.owner.post('/api/chat',json={'session_id':self.session,'message':'What remains to be done?'})
        context=self.provider.generate.call_args.args[0][0]['content']
        self.assertIn('Earlier conversation summary',context)
        self.owner.delete(path)
        self.assertIsNone(self.owner.get(path).json()['summary'])

    def test_deleting_conversation_also_deletes_its_summary(self):
        path='/api/conversations/'+self.session+'/summary'
        self.assertEqual(self.owner.post(path).status_code,200)
        self.owner.delete('/api/history/'+self.session)
        self.assertIsNone(self.owner.get(path).json()['summary'])
