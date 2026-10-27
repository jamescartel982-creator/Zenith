"""Create an approved opt-in compatibility copy; never patch the upstream tree."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile

PIN='d05095663342556788cf2a198bfa7844cc7968ab'
ORIGINALS={'agent/agent_init.py':'a30e1ae93021daa9448d6a5e72747f62fc00d9e3d362f72b61489ec59eee1f2c',
           'gateway/platforms/api_server.py':'9f3cf704330d75ad246b62a3c8698c12259b77c89a7167878724046abe3322a1',
           'gateway/run_turn_runner.py':'23fee696d5090fbef9d1841c4eccaea9cb93b4204cc9dcf4c2a49ac198a50aaf'}


def build(source,output):
    source=Path(source).resolve();output=Path(output).absolute()
    if output.exists():raise ValueError('Use a new destination; existing native files must remain untouched')
    if output.is_relative_to(source):raise ValueError('Keep the compatibility copy outside the original source')
    actual=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
    if actual!=PIN or subprocess.run(['git','-C',str(source),'diff','--quiet','HEAD']).returncode:
        raise ValueError('A clean exact pinned upstream tree is required')
    for path,digest in ORIGINALS.items():
        if hashlib.sha256((source/path).read_bytes()).hexdigest()!=digest:raise ValueError('Audited upstream file hash mismatch')
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.zenith-hermes-build-',dir=output.parent) as temporary:
        root=Path(temporary)/'runtime';root.mkdir(mode=0o700)
        process=subprocess.Popen(['git','-C',str(source),'archive',PIN],stdout=subprocess.PIPE)
        try:
            with tarfile.open(fileobj=process.stdout,mode='r|') as archive:archive.extractall(root,filter='data')
            if process.wait()!=0:raise ValueError('Native source export failed')
        finally:
            if process.stdout:process.stdout.close()
            if process.poll() is None:process.terminate();process.wait()
        file=root/'agent/agent_init.py';content=file.read_text()
        anchor='    if _ctx and _ctx < MINIMUM_CONTEXT_LENGTH and not _allow_lmstudio_explicit_below_floor:\n'
        if content.count(anchor)!=1:raise ValueError('Native minimum-context guard changed')
        file.write_text(content.replace(anchor,anchor+'        from zenith_chat_compat import allow_small_context\n        if allow_small_context(agent, _ctx):\n            return\n'))
        file=root/'gateway/platforms/api_server.py';content=file.read_text()
        anchor='            "object": "hermes.api_server.capabilities", "platform": "hermes-agent",\n'
        if content.count(anchor)!=1:raise ValueError('Native capability response changed')
        file.write_text(content.replace(anchor,anchor+'            **__import__("zenith_chat_compat").capability_field(),\n'))
        file=root/'gateway/run_turn_runner.py';content=file.read_text()
        anchor="    if api is None or not isinstance(result, dict):\n        return\n"
        if content.count(anchor)!=1:raise ValueError('Native served-runtime capture changed')
        file.write_text(content.replace(anchor,"    if api is None or not isinstance(result, dict):\n        from zenith_chat_compat import record_served_runtime\n        record_served_runtime(agent, result, captured)\n        return\n"))
        shutil.copyfile(Path(__file__).with_name('zenith_chat_compat.py'),root/'zenith_chat_compat.py')
        paths=list(ORIGINALS)+['zenith_chat_compat.py']
        definition={'policy':'zenith-chat-only-v1','source_pin':PIN,'files':{path:hashlib.sha256((root/path).read_bytes()).hexdigest() for path in paths}}
        digest=hashlib.sha256(json.dumps(definition,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        manifest={'schema_version':1,'definition':definition,'build_sha256':digest,'original_files':ORIGINALS}
        file=root/'zenith-compat-build.json';file.write_text(json.dumps(manifest,indent=2)+'\n');file.chmod(0o600)
        root.rename(output)
    print(json.dumps({'compatibility_copy':str(output),'build_sha256':digest,'upstream_unchanged':True,'enabled':False}))
    return manifest


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();build(args.source,args.output)
