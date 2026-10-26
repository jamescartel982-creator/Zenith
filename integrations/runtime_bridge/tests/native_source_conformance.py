"""Compare Python auth payloads with the actual unmodified pinned OpenClaw function."""
import argparse
import base64
import json
from pathlib import Path
import subprocess

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from zenith_integrations.openclaw.gateway_client import PIN,device_payload


def run(root,node,output):
    root=Path(root).resolve()
    actual=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
    if actual!=PIN:
        raise ValueError('Native source does not match the audited pin')
    file=root/'packages/gateway-client/src/device-auth.ts'
    before=file.read_bytes()
    vectors=[]
    for platform,family in [(' MACOS ',' Desktop '),('linux',''),('WiNdOwS','PC'),('ÄBC','İOS')]:
        vectors.append({'deviceId':'fixture-device','clientId':'gateway-client','clientMode':'backend','role':'operator',
            'scopes':['operator.read','operator.write'],'signedAtMs':123456,'token':'fixture-not-a-live-token',
            'nonce':'nonce_fixture','platform':platform,'deviceFamily':family})
    private=Ed25519PrivateKey.generate()
    public=private.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    expected=[device_payload(v['deviceId'],v['clientId'],v['clientMode'],v['role'],v['scopes'],v['signedAtMs'],v['token'],v['nonce'],v['platform'],v['deviceFamily']) for v in vectors]
    signatures=[base64.b64encode(private.sign(value.encode())).decode() for value in expected]
    program='''import {verify} from 'node:crypto';
const {buildDeviceAuthPayloadV3}=await import(FILE);
const vectors=VECTORS;
const publicKey=KEY;
const signatures=SIGNATURES;
console.log(JSON.stringify(vectors.map((v,i)=>{
 const payload=buildDeviceAuthPayloadV3(v);
 return {payload,signatureValid:verify(null,Buffer.from(payload),publicKey,Buffer.from(signatures[i],'base64'))};
})));'''.replace('FILE',json.dumps(file.as_uri())).replace('VECTORS',json.dumps(vectors,ensure_ascii=False)).replace('KEY',json.dumps(public)).replace('SIGNATURES',json.dumps(signatures))
    value=json.loads(subprocess.check_output([str(node),'--experimental-strip-types','--input-type=module','-'],input=program,
                                           text=True,encoding='utf-8',timeout=30))
    if [v['payload'] for v in value]!=expected or not all(v['signatureValid'] for v in value):
        raise AssertionError('Native auth builder or Node signature verification differs')
    if file.read_bytes()!=before or subprocess.check_output(['git','-C',str(root),'status','--porcelain'],text=True).strip():
        raise AssertionError('Pinned native source was modified')
    report={'source_pin':PIN,'native_function':'packages/gateway-client/src/device-auth.ts:buildDeviceAuthPayloadV3',
            'vectors':len(vectors),'payloads_match':True,'node_verified_ed25519_signatures':True,'native_source_unchanged':True,
            'actual_gateway_pairing_tested':False,'channel_delivery_tested':False}
    Path(output).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--openclaw-root',type=Path,required=True)
    parser.add_argument('--node',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();run(args.openclaw_root,args.node,args.output)
