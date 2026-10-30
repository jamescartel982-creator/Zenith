"""Real existing FastAPI/auth/SQLite application inside the optional envelope."""
from dataclasses import replace
import json
import secrets
import tempfile
import unittest
from unittest.mock import Mock
from uuid import uuid4
from fastapi.testclient import TestClient
from agent.config import Settings
from agent.core import Agent
from agent.cloudflare_origin import create_origin


class CloudflareOriginTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.key=secrets.token_urlsafe(32);self.edge=secrets.token_urlsafe(32)
        self.settings=replace(Settings(),provider='huggingface',data_dir=temp.name,api_token=self.key,
                              allowed_hosts=('127.0.0.1','zenith.example'))
        self.provider=Mock();self.provider.generate.side_effect=lambda messages:('Actual fixture answer.',messages)
        self.agent=Agent(self.settings,self.provider)
        self.app=create_origin(self.settings,self.agent,secret=self.edge)
        self.client=TestClient(self.app,base_url='http://127.0.0.1')
        self.headers={'X-Zenith-Origin-Secret':self.edge,'X-Zenith-Public-Origin':'https://zenith.example'}

    def test_direct_access_spoofing_duplicate_and_unknown_public_origins_are_denied(self):
        cases=[{}, {**self.headers,'X-Zenith-Origin-Secret':'wrong'}, {**self.headers,'X-Zenith-Public-Origin':'https://foreign.example'},
               {**self.headers,'X-Zenith-Public-Origin':'http://zenith.example'},
               [('X-Zenith-Origin-Secret',self.edge),('X-Zenith-Origin-Secret',self.edge),('X-Zenith-Public-Origin','https://zenith.example')]]
        for headers in cases:
            result=self.client.get('/healthz',headers=headers)
            self.assertEqual(result.status_code,403);self.assertEqual(result.headers['cache-control'],'no-store')
            self.assertNotIn(self.edge,result.text)

    def test_normal_app_health_host_headers_and_server_gate_are_preserved(self):
        health=self.client.get('/healthz',headers=self.headers)
        self.assertEqual(health.status_code,200);self.assertIn('strict-transport-security',health.headers)
        self.assertEqual(self.client.get('/api/account',headers=self.headers).status_code,401)
        headers={**self.headers,'Authorization':'Bearer '+self.key}
        self.assertEqual(self.client.get('/api/account',headers=headers).status_code,200)
        self.assertEqual(self.client.post('/api/access',headers={**headers,'Origin':'https://foreign.example'},json={'token':self.key}).status_code,403)

    def test_browser_exchange_account_and_real_fixture_chat_keep_auth_and_keys_private(self):
        # The TLS edge is represented by its public origin in TestClient; the
        # envelope overwrites the internal Host/scheme only after authentication.
        client=TestClient(self.app,base_url='https://zenith.example',headers=self.headers)
        result=client.post('/api/access',json={'token':self.key})
        self.assertEqual(result.status_code,200);self.assertIn('Secure',result.headers['set-cookie'])
        client.post('/api/account/register',json={'username':'reader','display_name':'Reader','password':'temporary isolated fixture password'}).raise_for_status()
        self.assertEqual(client.get('/api/admin/help').status_code,403)
        result=client.post('/api/chat',json={'session_id':str(uuid4()),'message':'Explain this example.'})
        result.raise_for_status();self.assertEqual(result.json()['response'],'Actual fixture answer.')
        self.assertNotIn(self.edge,json.dumps(self.provider.generate.call_args.args))
        self.assertNotIn(self.key,json.dumps(self.provider.generate.call_args.args))
        self.assertEqual(client.post('/api/chat',json={'session_id':str(uuid4()),'message':self.edge}).status_code,400)

    def test_invalid_weak_or_reused_credentials_fail_before_creating_an_app(self):
        for edge in ('', 'short',self.key):
            with self.assertRaises(ValueError):create_origin(self.settings,self.agent,secret=edge)
        with self.assertRaises(ValueError):create_origin(replace(self.settings,api_token='',allowed_hosts=('127.0.0.1',)),self.agent,secret=self.edge)

    def test_hosted_checkpoint_gate_rejects_missing_or_changed_state(self):
        from pathlib import Path
        from agent.checkpoints import inventory
        with self.assertRaisesRegex(ValueError,'existing trained checkpoint'):
            create_origin(replace(self.settings,adapter='',checkpoint_receipt=''),self.agent,secret=self.edge,require_checkpoint=True)
        root=Path(self.settings.data_dir);adapter=root/'adapter';adapter.mkdir()
        weights=adapter/'adapter_model.safetensors';weights.write_bytes(b'checksum fixture, not model weights')
        receipt=root/'receipt.json'
        receipt.write_text(json.dumps({'approved':True,'candidate':str(adapter),
            'base_model':self.settings.model,'base_revision':self.settings.revision,'checkpoint_files':inventory(adapter)}))
        selected=replace(self.settings,adapter=str(adapter),checkpoint_receipt=str(receipt))
        # Checks approval and hashes; fixture provider does not claim inference.
        create_origin(selected,self.agent,secret=self.edge,require_checkpoint=True)
        weights.write_bytes(b'tampered fixture')
        with self.assertRaisesRegex(ValueError,'existing trained checkpoint'):
            create_origin(selected,self.agent,secret=self.edge,require_checkpoint=True)

    def test_only_authenticated_validated_client_addresses_partition_login_limits(self):
        first={**self.headers,'X-Zenith-Client-IP':'203.0.113.10'}
        for _ in range(8):self.assertEqual(self.client.post('/api/access',headers=first,json={'token':'wrong'}).status_code,401)
        self.assertEqual(self.client.post('/api/access',headers=first,json={'token':self.key}).status_code,429)
        second={**self.headers,'X-Zenith-Client-IP':'203.0.113.11'}
        self.assertEqual(self.client.post('/api/access',headers=second,json={'token':self.key}).status_code,200)
        self.assertEqual(self.client.get('/healthz',headers={**second,'X-Zenith-Client-IP':'not-an-IP'}).status_code,403)


if __name__=='__main__':unittest.main()
