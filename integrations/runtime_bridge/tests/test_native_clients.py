"""Source-contract tests use isolated protocol servers, not mock production backends."""
import asyncio
import base64
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import httpx
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from zenith_integrations.hermes.api_client import HermesAPI
from zenith_integrations.hermes.session_bridge import session_name
from zenith_integrations.openclaw.gateway_client import GatewayClient,create_device,device_payload
from zenith_integrations.openclaw.channel_bridge import ChannelBridge
from zenith_integrations.shared.identity import User
from zenith_integrations.shared.ledger import Ledger
from zenith_integrations.shared.native_http import NativeRefused,UnknownExecution
from zenith_integrations.shared.secrets import write_private_new


class HermesContracts(unittest.IsolatedAsyncioTestCase):
    async def test_missing_ack_and_wrong_actual_model_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            key=Path(folder)/'native.key';write_private_new(key,'h'*48)
            requests=[]
            client=HermesAPI('http://127.0.0.1:8642',key,'profile',transport=httpx.MockTransport(
                lambda request:(requests.append(request.method) or httpx.Response(202,json=[]))))
            client.capabilities={'verified_for_test':True}
            with self.assertRaises(UnknownExecution):await client.submit('Task','zenith_test','stable_key')
            self.assertEqual(requests,['POST'])
            client.http.transport=httpx.MockTransport(lambda _:httpx.Response(202,json={'run_id':'run_test','status':'started'}))
            handle=await client.submit('Task','zenith_test','stable_key')
            client.http.transport=httpx.MockTransport(lambda _:httpx.Response(200,json={'object':'hermes.run',
                'run_id':'run_test','session_id':'zenith_test','status':'completed','runtime':{'model':'other','provider':'remote'}}))
            with self.assertRaises(NativeRefused):await client.status(handle)

    async def test_native_capabilities_idempotent_admission_and_model_attribution(self):
        with tempfile.TemporaryDirectory() as folder:
            secret='h'*48;key=Path(folder)/'native.key';write_private_new(key,secret)
            requests=[]
            def handler(request):
                self.assertEqual(request.headers['Authorization'],'Bearer '+secret)
                requests.append((request.method,request.url.path))
                if request.url.path=='/v1/capabilities':
                    return httpx.Response(200,json={'object':'hermes.api_server.capabilities','platform':'hermes-agent','model':'profile-agent',
                        'auth':{'type':'bearer','required':True},'features':{'run_submission':True,'run_status':True,'run_stop':True,
                        'runs_idempotency':{'supported':True,'durable':True}},'endpoints':{
                        'runs':{'method':'POST','path':'/v1/runs'},'run_status':{'method':'GET','path':'/v1/runs/{run_id}'},
                        'run_stop':{'method':'POST','path':'/v1/runs/{run_id}/stop'}}})
                if request.url.path=='/v1/runs':
                    self.assertEqual(request.headers['Idempotency-Key'],'stable_key')
                    body=json.loads(request.content)
                    self.assertEqual(body,{'input':'Supporting research','session_id':'zenith_test','model':'zenith','provider':'custom'})
                    return httpx.Response(202,json={'run_id':'run_test','status':'started'})
                return httpx.Response(200,json={'object':'hermes.run','run_id':'run_test','session_id':'zenith_test',
                    'status':'completed','output':'Native report '+secret,'runtime':{'provider':'custom','model':'zenith'}})
            client=HermesAPI('http://127.0.0.1:8642',key,'owner-profile',transport=httpx.MockTransport(handler))
            discovered=await client.discover()
            self.assertEqual(discovered['agent_alias'],'profile-agent')
            run=await client.submit('Supporting research','zenith_test','stable_key')
            state=await client.wait(run,seconds=1)
            self.assertEqual(state['status'],'completed')
            self.assertNotIn(secret,json.dumps(state))
            self.assertEqual(sum(method=='POST' for method,path in requests),1)

    async def test_lost_admission_and_non_durable_modes_do_not_retry(self):
        with tempfile.TemporaryDirectory() as folder:
            key=Path(folder)/'native.key';write_private_new(key,'h'*48)
            count=0
            def timeout(request):
                nonlocal count
                count+=1
                raise httpx.ReadTimeout('Do not expose private upstream details',request=request)
            client=HermesAPI('http://127.0.0.1:8642',key,'profile',transport=httpx.MockTransport(timeout))
            client.capabilities={'verified_for_test':True}
            with self.assertRaises(UnknownExecution):await client.submit('Task','zenith_test','stable_key')
            self.assertEqual(count,1)
            client.http.transport=httpx.MockTransport(lambda _:httpx.Response(200,json={'object':'hermes.api_server.capabilities',
                'platform':'hermes-agent','auth':{'required':True},'features':{'runs_idempotency':{'durable':False}}}))
            with self.assertRaises(NativeRefused):await client.discover()


class GatewayContracts(unittest.IsolatedAsyncioTestCase):
    async def test_broad_or_reduced_native_grants_and_invalid_challenge_rejected(self):
        from websockets.asyncio.server import serve
        with tempfile.TemporaryDirectory() as folder:
            private=Path(folder)/'device.key';token=Path(folder)/'token.key'
            create_device(private);write_private_new(token,'paired-device-token-fixture-00000000000000')
            for scopes,stamp in [(['operator.admin'],123),(['operator.read'],123),(['operator.read','operator.write'],True)]:
                async def gateway(socket):
                    await socket.send(json.dumps({'type':'event','event':'connect.challenge','payload':{'nonce':'fixture','ts':stamp}}))
                    if stamp is True:
                        await socket.wait_closed();return
                    request=json.loads(await socket.recv())
                    await socket.send(json.dumps({'type':'res','id':request['id'],'ok':True,'payload':{
                        'type':'hello-ok','protocol':4,'server':{'version':'fixture','connId':'fixture'},
                        'features':{'methods':['chat.send'],'events':['chat']},'snapshot':{},
                        'auth':{'role':'operator','method':'device-token','scopes':scopes},
                        'policy':{'maxPayload':100000,'maxBufferedBytes':100000,'tickIntervalMs':1000}}}))
                    await socket.wait_closed()
                async with serve(gateway,'127.0.0.1',0) as server:
                    url='ws://127.0.0.1:'+str(server.sockets[0].getsockname()[1])
                    client=GatewayClient(url,private,token)
                    with self.assertRaises(NativeRefused):await client.connect()
                    self.assertIsNone(client.socket)

    async def test_revoked_grant_is_rechecked_and_late_receipt_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger=Ledger(Path(folder)/'control.sqlite3',b'a'*48);actor=User('owner','session')
            text='Approved report';scope={'runtime':'openclaw','operation':'deliver','channel':'telegram','recipient':'12345',
                                        'report_sha256':hashlib.sha256(text.encode()).hexdigest()}
            class Client:
                hello=True;url='ws://127.0.0.1:18789';device_id='device';credential_fingerprint='cred';calls=0
                async def _rpc(self,method,params):
                    self.calls+=1
                    ledger.transition(params['idempotencyKey'],{'running'},'cancel_requested')
                    return {'runId':params['idempotencyKey'],'channel':'telegram','messageId':'actual_fixture_receipt'}
            client=Client();verifications=0;revoke=True
            grant=ledger.grant(actor,'reports.deliver',scope,60)
            async def verified():
                nonlocal verifications
                verifications+=1
                return User('different','other-session') if revoke and verifications>1 else actor
            delivery=ChannelBridge(client,ledger,'profile',verified)
            with self.assertRaises(NativeRefused):await delivery.deliver(actor,grant['id'],text,'telegram','12345','first_key')
            self.assertEqual(client.calls,0)
            revoke=False
            result=await delivery.deliver(actor,grant['id'],text,'telegram','12345','second_key')
            self.assertEqual(result['status'],'native_acknowledged');self.assertTrue(result['cancellation_requested'])
            again=await delivery.deliver(actor,grant['id'],text,'telegram','12345','second_key')
            self.assertEqual(again,result);self.assertEqual(client.calls,1)

    async def test_signed_challenge_effective_scopes_and_native_chat_frames(self):
        from websockets.asyncio.server import serve
        with tempfile.TemporaryDirectory() as folder:
            private=Path(folder)/'device.key';token=Path(folder)/'token.key'
            device=create_device(private);write_private_new(token,'paired-device-token-fixture-00000000000000')
            observed=[]
            async def gateway(socket):
                await socket.send(json.dumps({'type':'event','event':'connect.challenge','payload':{'nonce':'challenge_fixture','ts':123456}}))
                first=json.loads(await socket.recv());params=first['params'];observed.append(first)
                self.assertEqual(params['client']['mode'],'backend')
                self.assertNotIn('token',params['auth'])
                self.assertEqual(params['device']['signedAt'],123456)
                public=base64.urlsafe_b64decode(params['device']['publicKey']+'==')
                self.assertEqual(hashlib.sha256(public).hexdigest(),device['device_id'])
                signed=device_payload(device['device_id'],'gateway-client','backend','operator',params['scopes'],123456,
                    params['auth']['deviceToken'],'challenge_fixture','python')
                Ed25519PublicKey.from_public_bytes(public).verify(base64.urlsafe_b64decode(params['device']['signature']+'=='),signed.encode())
                await socket.send(json.dumps({'type':'res','id':first['id'],'ok':True,'payload':{
                    'type':'hello-ok','protocol':4,'server':{'version':'pinned-test','connId':'test_conn'},
                    'features':{'methods':['chat.send'],'events':['chat']},'snapshot':{},
                    'auth':{'role':'operator','method':'device-token','scopes':['operator.read','operator.write']},
                    'policy':{'maxPayload':1024*1024,'maxBufferedBytes':1024*1024,'tickIntervalMs':30000}}}))
                frame=json.loads(await socket.recv());observed.append(frame)
                self.assertEqual(frame['method'],'chat.send')
                self.assertFalse(frame['params']['deliver'])
                self.assertTrue(frame['params']['suppressCommandInterpretation'])
                event={'type':'event','event':'chat','payload':{'sessionKey':'agent:zenith:test','runId':'native_run','seq':1,'state':'final','message':{'role':'assistant','content':'Done'}}}
                # A terminal event can arrive before its acknowledgement.
                await socket.send(json.dumps(event))
                await socket.send(json.dumps({'type':'res','id':frame['id'],'ok':True,'payload':{'runId':'native_run','status':'started'}}))
                await socket.wait_closed()
            async with serve(gateway,'127.0.0.1',0) as server:
                port=server.sockets[0].getsockname()[1]
                async with GatewayClient('ws://127.0.0.1:'+str(port),private,token) as client:
                    accepted=await client.submit_turn('agent:zenith:test','Hello','stable_key')
                    terminal=await client.terminal('agent:zenith:test',accepted['runId'])
                    self.assertEqual(terminal['state'],'final')
                    with self.assertRaises(NativeRefused):await client._rpc('config.set',{})
            self.assertEqual(len(observed),2)

    async def test_report_approval_and_unknown_ack_never_duplicate_delivery(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger=Ledger(Path(folder)/'control.sqlite3',b'a'*48)
            actor=User('owner','session')
            class Client:
                hello={'server':{'connId':'conn'}}
                url='ws://127.0.0.1:18789'
                device_id='device'
                credential_fingerprint='credential'
                calls=0
                async def _rpc(self,method,params):
                    self.calls+=1
                    self.last=(method,params)
                    raise UnknownExecution('Acknowledgement lost')
            client=Client()
            async def verified():return actor
            delivery=ChannelBridge(client,ledger,'native-profile',verified)
            text='Approved test report'
            scope={'runtime':'openclaw','operation':'deliver','channel':'telegram','recipient':'12345',
                   'report_sha256':hashlib.sha256(text.encode()).hexdigest()}
            grant=ledger.grant(actor,'reports.deliver',scope,60)
            with self.assertRaises(NativeRefused):await delivery.deliver(actor,grant['id'],text+' changed','telegram','12345','stable_key')
            self.assertEqual(client.calls,0)
            with self.assertRaises(UnknownExecution):await delivery.deliver(actor,grant['id'],text,'telegram','12345','stable_key')
            self.assertEqual(client.last[0],'send')
            with self.assertRaises(UnknownExecution):await delivery.deliver(actor,grant['id'],text,'telegram','12345','stable_key')
            self.assertEqual(client.calls,1)

    async def test_session_names_do_not_collide_between_accounts_profiles_or_conversations(self):
        key=b'a'*48
        names={session_name(a,c,p,key) for a in ('owner','reader') for c in ('one','two') for p in ('hermes','openclaw')}
        self.assertEqual(len(names),8)
