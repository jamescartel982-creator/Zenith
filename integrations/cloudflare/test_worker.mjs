import test from 'node:test';
import assert from 'node:assert/strict';
import {handle} from './worker.mjs';

const key = 'synthetic-origin-key-for-isolated-tests-123';
const env = {ZENITH_BACKEND_URL:'https://origin.example', ZENITH_ORIGIN_SECRET:key};
const request = (path='/', options={}) => new Request('https://zenith.example'+path, options);

test('unconfigured and invalid/self-loop origins fail closed with protective headers', async () => {
  for (const config of [{}, {...env,ZENITH_BACKEND_URL:'http://origin.example'}, {...env,ZENITH_BACKEND_URL:'https://user:pass@origin.example'},
    {...env,ZENITH_BACKEND_URL:'https://zenith.example'}, {...env,ZENITH_BACKEND_URL:'https://origin.example/private'}]) {
    const result = await handle(request(), config, () => assert.fail('network must not be used'));
    assert.equal(result.status,503); assert.match(result.headers.get('content-security-policy'),/object-src 'none'/);
    assert.equal(result.headers.get('cache-control'),'no-store'); assert.ok(!(await result.text()).includes(key));
  }
});
test('health distinguishes edge configuration from actual inference', async () => {
  const result=await handle(request('/_edge/healthz'),env,()=>assert.fail());
  assert.equal(result.status,200); assert.equal((await result.json()).inference_verified,false);
  assert.equal((await handle(request('/_edge/healthz'),{...env,ZENITH_BACKEND_TIMEOUT_MS:'invalid'},()=>assert.fail())).status,503);
  assert.equal((await handle(new Request('http://zenith.example/'),env,()=>assert.fail())).status,426);
});
test('spoofed headers are removed, independent server/user credentials preserved, host fixed', async () => {
  const body=JSON.stringify({message:'ordinary task'});
  const result=await handle(request('/api/chat?q=1',{method:'POST',headers:{Origin:'https://zenith.example',Authorization:'Bearer browser-gate-token',Cookie:'zenith_login=account-session',
    'X-Zenith-Origin-Secret':'forged','X-Zenith-Public-Origin':'https://foreign.example','X-Zenith-Client-IP':'192.0.2.99','CF-Connecting-IP':'203.0.113.10','X-Forwarded-Host':'foreign.example'},body}),env,async upstream=>{
    assert.equal(upstream.url,'https://origin.example/api/chat?q=1');
    assert.equal(upstream.headers.get('X-Zenith-Origin-Secret'),key);
    assert.equal(upstream.headers.get('X-Zenith-Public-Origin'),'https://zenith.example');
    assert.equal(upstream.headers.get('X-Forwarded-Host'),null);
    assert.equal(upstream.headers.get('X-Zenith-Client-IP'),'203.0.113.10');
    assert.equal(upstream.headers.get('Authorization'),'Bearer browser-gate-token');
    assert.equal(upstream.headers.get('Cookie'),'zenith_login=account-session');
    assert.equal(await upstream.text(),body);assert.equal(upstream.redirect,'manual');
    return new Response('done',{headers:{'Set-Cookie':'zenith_login=new-session; HttpOnly; Secure; SameSite=Strict'}});
  });
  assert.equal(await result.text(),'done');assert.match(result.headers.get('set-cookie'),/HttpOnly/);
});
test('foreign/null Origin, cross-site API requests and unsupported methods are rejected',async()=>{
  for(const headers of [{Origin:'null'},{Origin:'https://foreign.example'},{Origin:'https://zenith.example, https://foreign.example'},{'Sec-Fetch-Site':'cross-site'}]) {
    assert.equal((await handle(request('/api/account',{method:'POST',headers}),env,()=>assert.fail())).status,403);
  }
  assert.equal((await handle(request('/',{method:'PROPFIND'}),env,()=>assert.fail())).status,405);
});
test('oversized/chunked request bodies never reach origin', async()=>{
  const result=await handle(request('/api/chat',{method:'POST',body:'a'.repeat(512*1024+1)}),env,()=>assert.fail());
  assert.equal(result.status,413);
});
test('backend errors and timeouts expose no exception details',async()=>{
  const error=await handle(request(),env,()=>{throw new Error('private '+key);});
  assert.equal(error.status,502);assert.ok(!(await error.text()).includes(key));
  const timeout=await handle(request(),{...env,ZENITH_BACKEND_TIMEOUT_MS:'1000'},req=>new Promise((_,reject)=>req.signal.addEventListener('abort',()=>reject(new Error(key)))));
  assert.equal(timeout.status,504);
});
test('SSE passes through progressively without buffering the final answer',async()=>{
  let finish;
  const stream=new ReadableStream({start(controller){controller.enqueue(new TextEncoder().encode('data: first\n\n'));finish=()=>{controller.enqueue(new TextEncoder().encode('data: second\n\n'));controller.close();};}});
  const result=await handle(request('/api/chat/stream'),env,async()=>new Response(stream,{headers:{'Content-Type':'text/event-stream'}}));
  const reader=result.body.getReader();assert.match(new TextDecoder().decode((await reader.read()).value),/first/);
  finish();assert.match(new TextDecoder().decode((await reader.read()).value),/second/);assert.equal((await reader.read()).done,true);
});
