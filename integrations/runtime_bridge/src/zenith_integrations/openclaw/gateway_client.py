"""OpenClaw protocol 4 device-auth client at the audited immutable source pin.

No owner/shared-token fallback, automatic pairing, arbitrary admin RPC, model
substitution or automatic retry of accepted work is implemented here.
"""
import asyncio
from collections import deque
import base64
import hashlib
import json
import re
from urllib.parse import urlsplit
import uuid

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from ..shared.native_http import NativeRefused, NativeUnavailable, UnknownExecution
from ..shared.secrets import read_private, write_private_new
from ..shared.redaction import redact
from .event_mapper import chat_event

PIN='2f5727b9c61c2ba9dccc3c880d9115f02cb8652f'
ASCII_LOWER=str.maketrans('ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')


def b64url(value):
    return base64.urlsafe_b64encode(value).decode().rstrip('=')


def device_payload(device_id,client_id,client_mode,role,scopes,signed_at,token,nonce,platform,device_family=''):
    # Matches the native buildDeviceAuthPayloadV3, including ASCII-only case folding.
    return '|'.join(('v3',device_id,client_id,client_mode,role,','.join(scopes),str(signed_at),
                     token,nonce,platform.strip().translate(ASCII_LOWER),device_family.strip().translate(ASCII_LOWER)))


def create_device(path):
    key=Ed25519PrivateKey.generate()
    private=key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption())
    write_private_new(path,private.decode())
    public=key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
    return {'device_id':hashlib.sha256(public).hexdigest(),'public_key':b64url(public),'paired':False}


class GatewayClient:
    def __init__(self,url,private_key_file,device_token_file,scopes=('operator.read','operator.write'),timeout=30):
        parts=urlsplit(url)
        if parts.scheme not in {'ws','wss'} or parts.hostname not in {'localhost','127.0.0.1','::1'} or parts.username or parts.password or parts.query or parts.fragment or parts.path not in {'','/'}:
            raise ValueError('Use the dedicated private loopback Gateway or an explicit local tunnel')
        if not scopes or len(set(scopes))!=len(scopes) or set(scopes)-{'operator.read','operator.write'}:
            raise ValueError('Only least-privilege native read/write scopes are allowed')
        if not 0<timeout<=60:
            raise ValueError('Use a bounded Gateway timeout')
        self.url,self.key_file,self.token_file=url,private_key_file,device_token_file
        self.requested_scopes,self.timeout=tuple(scopes),timeout
        self.socket,self.hello=None,None
        self.events=deque()
        self.secret_values=()
        self.device_id=None
        self.credential_fingerprint=None
        self.rpc_lock=asyncio.Lock()

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self,*args):
        await self.close()

    async def close(self):
        if self.socket:
            socket,self.socket=self.socket,None
            await socket.close()
        self.hello=None
        self.events.clear()

    async def receive(self):
        if self.socket is None:
            raise NativeUnavailable('Gateway is not connected')
        try:
            raw=await asyncio.wait_for(self.socket.recv(),self.timeout)
            if not isinstance(raw,str):
                raise NativeRefused('binary_gateway_frame_rejected')
            frame=json.loads(raw)
            if not isinstance(frame,dict) or frame.get('type') not in {'event','res'}:
                raise NativeRefused('invalid_gateway_frame')
            return frame
        except (ValueError,TypeError):
            raise NativeRefused('invalid_gateway_json') from None
        except NativeRefused:
            raise
        except Exception:
            raise NativeUnavailable('Gateway receive did not complete') from None

    def buffer(self,event):
        if len(self.events)>=128:
            raise UnknownExecution('Native event buffer overflow; reconcile the admitted run')
        self.events.append(event)

    async def connect(self):
        if self.socket:
            raise ValueError('Use a new connection or close the existing one')
        from websockets.asyncio.client import connect
        key=serialization.load_pem_private_key(read_private(self.key_file,maximum=4096).encode(),password=None)
        if not isinstance(key,Ed25519PrivateKey):
            raise ValueError('An integration-owned Ed25519 device identity is required')
        token=read_private(self.token_file,maximum=1024).strip()
        if not 16<=len(token)<=512 or not token.isascii() or any(c.isspace() for c in token):
            raise ValueError('Configure an already paired native device token')
        self.secret_values=(token,read_private(self.key_file,maximum=4096))
        public=key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
        device_id=hashlib.sha256(public).hexdigest()
        self.device_id=device_id
        self.credential_fingerprint=hashlib.sha256(token.encode()).hexdigest()
        try:
            self.socket=await connect(self.url,open_timeout=self.timeout,close_timeout=5,max_size=1024*1024,
                                      max_queue=16,ping_interval=20,ping_timeout=20,proxy=None)
            challenge=await self.receive()
            payload=challenge.get('payload',{})
            if not isinstance(payload,dict):
                raise NativeRefused('invalid_native_challenge')
            nonce,ts=payload.get('nonce'),payload.get('ts')
            if challenge.get('type')!='event' or challenge.get('event')!='connect.challenge' or not isinstance(nonce,str) or not 1<=len(nonce)<=512 or type(ts) is not int or ts<0:
                raise NativeRefused('invalid_native_challenge')
            scopes=list(self.requested_scopes)
            signed=device_payload(device_id,'gateway-client','backend','operator',scopes,ts,token,nonce,'python')
            identifier=uuid.uuid4().hex
            params={'minProtocol':4,'maxProtocol':4,'client':{'id':'gateway-client','version':'0.2.0','platform':'python','mode':'backend'},
                    'role':'operator','scopes':scopes,'caps':[], 'auth':{'deviceToken':token},
                    'device':{'id':device_id,'publicKey':b64url(public),'signature':b64url(key.sign(signed.encode())),
                              'signedAt':ts,'nonce':nonce}}
            await self.socket.send(json.dumps({'type':'req','id':identifier,'method':'connect','params':params}))
            response=await self.receive()
            hello=response.get('payload',{})
            if not isinstance(hello,dict):
                raise NativeRefused('invalid_native_hello')
            if response.get('type')!='res' or response.get('id')!=identifier or response.get('ok') is not True or hello.get('type')!='hello-ok' or hello.get('protocol')!=4:
                raise NativeRefused('native_pairing_or_protocol_refused')
            if not all(isinstance(hello.get(k),dict) for k in ('auth','server','features','snapshot','policy')):
                raise NativeRefused('incomplete_native_hello')
            auth=hello['auth']
            actual=auth.get('scopes')
            if auth.get('role')!='operator' or auth.get('method') not in (None,'device-token') or not isinstance(actual,list) or any(not isinstance(v,str) for v in actual) or set(actual)-set(scopes) or not set(scopes).issubset(actual):
                raise NativeRefused('effective_native_scopes_do_not_match')
            if any(type(hello['policy'].get(k)) is not int or hello['policy'][k]<1 for k in ('maxPayload','maxBufferedBytes','tickIntervalMs')):
                raise NativeRefused('invalid_native_payload_policy')
            if any(not isinstance(hello['server'].get(k),str) or not hello['server'][k] for k in ('version','connId')):
                raise NativeRefused('invalid_native_server_identity')
            if any(not isinstance(hello['features'].get(k),list) or any(not isinstance(v,str) or not v for v in hello['features'][k]) for k in ('methods','events')):
                raise NativeRefused('invalid_native_feature_advertisement')
            self.hello=hello
            return {'runtime':'openclaw','protocol':4,'scopes':actual,'server_version':hello['server'].get('version'),
                    'device_id':device_id,'target_source_pin':PIN}
        except BaseException:
            await self.close()
            raise

    async def _rpc(self,method,params):
        policy={'health':'operator.read','chat.history':'operator.read','chat.send':'operator.write',
                'chat.abort':'operator.write','send':'operator.write'}
        if method not in policy or not self.hello or policy[method] not in self.hello['auth']['scopes']:
            raise NativeRefused('native_rpc_scope_denied')
        if method not in self.hello['features']['methods']:
            raise NativeRefused('native_rpc_not_advertised')
        if self.rpc_lock.locked():
            raise NativeRefused('one_operation_per_connection_required')
        async with self.rpc_lock:
            identifier=uuid.uuid4().hex
            encoded=json.dumps({'type':'req','id':identifier,'method':method,'params':params},allow_nan=False)
            if len(encoded.encode())>min(self.hello['policy']['maxPayload'],1024*1024):
                raise ValueError('Native request exceeds the negotiated frame limit')
            try:
                await self.socket.send(encoded)
                async with asyncio.timeout(self.timeout):
                    while True:
                        frame=await self.receive()
                        if frame['type']=='event':
                            self.buffer(frame)
                            continue
                        if frame.get('id')!=identifier:
                            raise NativeUnavailable('unexpected_native_response_id')
                        if frame.get('ok') is not True:
                            if method in {'chat.send','chat.abort','send'}:
                                raise UnknownExecution('Native mutation refusal may include partial effects; reconcile')
                            raise NativeRefused('native_rpc_refused')
                        return redact(frame.get('payload'),self.secret_values)
            except NativeRefused:
                if method in {'chat.send','chat.abort','send'}:
                    raise UnknownExecution('Invalid native acknowledgement; reconcile without resubmission') from None
                raise
            except UnknownExecution:
                raise
            except Exception:
                if method in {'chat.send','chat.abort','send'}:
                    raise UnknownExecution('Native acknowledgement was lost; reconcile without resubmission') from None
                raise NativeUnavailable('Native read did not complete') from None

    async def health(self):
        return await self._rpc('health',{})

    async def submit_turn(self,session_key,message,idempotency_key):
        if not isinstance(session_key,str) or not re.fullmatch(r'[a-zA-Z0-9:._-]{1,256}',session_key):
            raise ValueError('Use an integration-owned native session key')
        if not isinstance(message,str) or not 1<=len(message)<=16000 or not re.fullmatch(r'[a-zA-Z0-9_-]{8,128}',idempotency_key):
            raise ValueError('A bounded message and stable idempotency key are required')
        return await self._rpc('chat.send',{'sessionKey':session_key,'message':message,'idempotencyKey':idempotency_key,
                                           'deliver':False,'suppressCommandInterpretation':True})

    async def cancel_turn(self,session_key,run_id):
        return await self._rpc('chat.abort',{'sessionKey':session_key,'runId':run_id})

    async def terminal(self,session_key,run_id,seconds=120):
        if not 0<seconds<=900:
            raise ValueError('Use a bounded native wait')
        if self.rpc_lock.locked():
            raise NativeRefused('one_operation_per_connection_required')
        try:
            async with self.rpc_lock,asyncio.timeout(seconds):
                last_sequence=-1
                while True:
                    event=self.events.popleft() if self.events else await self.receive()
                    value=chat_event(event,session_key,run_id,self.secret_values)
                    if value is None:
                        continue
                    if value['sequence']<=last_sequence:
                        continue
                    last_sequence=value['sequence']
                    if value['state'] in {'final','aborted','error'}:
                        value.pop('delta',None)
                        if value['state']!='final':
                            value['message']=None
                        return value
        except (TimeoutError,NativeUnavailable,NativeRefused):
            raise UnknownExecution('Native turn may still be running; reconcile before retrying') from None
