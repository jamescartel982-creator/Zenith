"""Real Linux-container security probes and owner-authorized task integration.

No models are loaded, no profile changed, and no image is downloaded implicitly.
All account data/keys and the host canary are temporary owned fixtures.
"""
import argparse
from dataclasses import replace
import json
import os
from pathlib import Path
import socket
import sys
import subprocess
import tempfile
from threading import Event
import time
from unittest.mock import patch

from agent.sandbox import SandboxPolicy
from agent.sandbox_docker import DockerSandbox


def smoke(image, include_runtime=True):
    policy = SandboxPolicy(enabled=True, image=image)
    sandbox = DockerSandbox(policy)
    checks = []
    def record(name, action):
        start = time.monotonic(); action()
        checks.append({'name': name, 'passed': True, 'elapsed_ms': round((time.monotonic()-start)*1000, 3)})
    def execute(source):
        result = sandbox.run(source, lambda: None)
        assert result['status'] == 'completed', result
        return result
    def expect_failure(backend, source, text, guard=lambda: None):
        try: backend.run(source, guard)
        except (ValueError, PermissionError) as exc: assert text in str(exc), str(exc)
        else: raise AssertionError('Execution should have been stopped')
    with tempfile.TemporaryDirectory(prefix='zenith-sandbox-host-canary-') as folder, socket.socket() as listener:
        host_canary = Path(folder)/'private-canary';host_canary.write_text('owned-fixture')
        listener.bind(('127.0.0.1',0));listener.listen(1)
        port = listener.getsockname()[1]
        source = f'''import os, socket
assert os.geteuid() == 65534
assert not os.environ
assert not os.path.exists({str(host_canary)!r})
assert not os.path.exists('/var/run/docker.sock')
assert not os.path.exists('/app/data/profile/config.env')
status = open('/proc/self/status').read()
assert 'CapEff:\\t0000000000000000' in status
assert 'NoNewPrivs:\\t1' in status
assert open('/sys/fs/cgroup/memory.max').read().strip() == '134217728'
assert open('/sys/fs/cgroup/pids.max').read().strip() == '32'
quota,period = map(int,open('/sys/fs/cgroup/cpu.max').read().split())
assert quota / period == 0.5
try:
    open('/zenith-root-write-probe','w').write('forbidden')
    raise AssertionError('root must be readonly')
except OSError:
    pass
s = socket.socket();s.settimeout(0.3)
assert s.connect_ex(('127.0.0.1',{port})) != 0
s.close()
open('/work/ephemeral','w').write('fixture')
print(sum(x*x for x in range(10)))
'''
        def boundary_probe():
            result = execute(source);assert result['stdout'].strip() == '285'
            listener.settimeout(0.1)
            try: connection,_ = listener.accept()
            except socket.timeout: pass
            else: connection.close();raise AssertionError('Worker reached host listener')
        record('uid-caps-nnp-environment-host-files-rootfs-network-and-real-python', boundary_probe)
        record('ephemeral-workspace-not-reused', lambda: execute("import os; assert not os.path.exists('/work/ephemeral'); print('clean')"))
        record('wall-time-cancels-and-cleans', lambda: expect_failure(DockerSandbox(replace(policy, seconds=1)), 'while True: pass', 'wall-time'))
        record('output-quota-cancels-and-cleans', lambda: expect_failure(sandbox, "print('x'*100000)", 'output budget'))
        active = Event()
        def revoke():
            if active.is_set():
                raise PermissionError('revoked-fixture')
        # Revoke during the container lifecycle after creation. This checks
        # cleanup of in-flight work; exact user-program start is not asserted.
        original = sandbox._control
        def controls(*args, **kwargs):
            value = original(*args, **kwargs)
            if args and args[0]=='create':
                from threading import Timer
                timer=Timer(1, active.set);timer.daemon=True;timer.start()
            return value
        with patch.object(sandbox, '_control', side_effect=controls):
            record('lifecycle-revocation-cancels-and-cleans', lambda: expect_failure(sandbox, 'import time; time.sleep(20)', 'revoked-fixture', revoke))
    def controller_loss():
        before=sandbox._control('ps','-a','--filter','label=io.zenith.sandbox=1','--format','{{.ID}}').split()
        assert not before, 'Do not run the controller-loss fixture concurrently with other sandbox work'
        code=('from agent.sandbox import SandboxPolicy; from agent.sandbox_docker import DockerSandbox; '
            + 'DockerSandbox(SandboxPolicy(True,'+repr(image)+',seconds=2)).run('
            + repr('import time; time.sleep(45)')+',lambda:None)')
        controller=subprocess.Popen([sys.executable,'-c',code],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        identifier=None
        try:
            deadline=time.monotonic()+15
            while time.monotonic()<deadline:
                identifiers=sandbox._control('ps','-a','--filter','label=io.zenith.sandbox=1','--format','{{.ID}}').split()
                if identifiers:
                    assert len(identifiers)==1
                    identifier=identifiers[0].decode()
                    state=json.loads(sandbox._control('inspect','--format','{{json .State}}',identifier))
                    if state['Running']:break
                time.sleep(.1)
            else:raise AssertionError('Owned crash fixture never started')
            controller.kill();controller.wait(timeout=3)
            deadline=time.monotonic()+8
            while time.monotonic()<deadline:
                state=json.loads(sandbox._control('inspect','--format','{{json .State}}',identifier))
                if not state['Running']:break
                time.sleep(.1)
            else:raise AssertionError('Container outlived its independent program budget')
            assert state['Status']=='exited' and state['ExitCode']==124,state
        finally:
            if controller.poll() is None:controller.kill();controller.wait(timeout=3)
            if identifier:sandbox._control('rm','--force','--volumes',identifier)
    record('container-deadline-survives-forced-controller-loss',controller_loss)
    if include_runtime:
        from agent.config import Settings
        from agent.core import Agent
        from agent.platform_config import PlatformConfig
        from agent.runtime import PlatformRuntime
        import pyotp
        class NoModelCalls:
            def generate(self, messages): raise AssertionError('Diagnostic task must not call a model')
        with tempfile.TemporaryDirectory(prefix='zenith-sandbox-accounts-') as folder, patch.dict(os.environ, {
                'ZENITH_SANDBOX_ENABLED': 'true', 'ZENITH_SANDBOX_IMAGE': image}):
            config=PlatformConfig(enabled=True,runtime_enabled=True,tools_enabled=True)
            agent=Agent(Settings(provider='huggingface',data_dir=folder,platform=config),provider=NoModelCalls())
            service=PlatformRuntime(agent,config)
            try:
                user=agent.personal.register('fixture-owner','Fixture Owner','only a disposable fixture password')
                token=agent.personal.issue_session(user['id']);actor=service.permissions.resolve(token)
                request={'steps':[{'tool':'sandbox-python','arguments':{'source':'print(6*7)'}}]}
                def unauthorized():
                    try:service.submit(actor,'diagnostics',request)
                    except PermissionError:pass
                    else:raise AssertionError('Unprivileged user could submit')
                record('unprivileged-user-denied', unauthorized)
                code_path=Path(folder)/'owner-fixture-code'
                agent.admin.initialize('fixture-owner',code_path)
                assert agent.admin.unlock(user['id'],token,code_path.read_text().strip())
                secret=agent.admin.mfa.begin(user['id'],'fixture-owner')['secret']
                assert agent.admin.mfa.verify(user['id'],token,pyotp.TOTP(secret).now(),enroll=True)
                agent.execution.grant(user['id'],token,'sandbox-python',{'kind':'offline'})
                def queued():
                    task=service.submit(actor,'diagnostics',request)
                    service.run_once();assert service.tasks.get(actor,task['id'])['status']=='waiting_approval'
                    approvals=service.approvals.list(actor,task['id']);assert len(approvals)==1
                    service.approvals.decide(actor,approvals[0]['id'],True)
                    service.run_once();done=service.tasks.get(actor,task['id'])
                    assert done['status']=='completed',done
                    assert done['result']['results'][0]['stdout'].strip()=='42'
                    assert not service.run_once()
                record('real-owner-mfa-grant-exact-approval-container-task',queued)
                def stop_in_flight():
                    from threading import Timer
                    task=service.submit(actor,'diagnostics',{'steps':[{'tool':'sandbox-python',
                        'arguments':{'source':'import time; time.sleep(20)'}}]})
                    service.run_once()
                    approval=service.approvals.list(actor,task['id'])[0]
                    service.approvals.decide(actor,approval['id'],True)
                    failures=[]
                    def shutdown():
                        try: agent.execution.emergency(user['id'],token,True)
                        except Exception as exc: failures.append(type(exc).__name__)
                    timer=Timer(2,shutdown);timer.daemon=True;timer.start()
                    try: service.run_once()
                    finally: timer.join(timeout=5)
                    assert not timer.is_alive() and not failures, failures
                    assert service.tasks.get(actor,task['id'])['status']=='needs_reconciliation'
                record('emergency-stop-during-approved-container-task',stop_in_flight)
                def stopped():
                    agent.execution.emergency(user['id'],token,True)
                    unauthorized()
                record('emergency-stop-denies-new-task',stopped)
            finally:service.stop()
    # The test owns every created sandbox container; no one else should run this
    # same smoke concurrently in the selected daemon.
    remaining=sandbox._control('ps','-a','--filter','name=zenith-sandbox-','--format','{{.Names}}')
    assert not remaining.strip(), 'Sandbox containers remain after cleanup'
    return {'purpose':'Finite real backend probes, not universal escape resistance or model quality',
            'image':image,'checks':checks,'all_passed':True,'containers_remaining':0,
            'production_profile_changed':False,'model_calls':0}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image',required=True,help='Reviewed existing immutable local sha256 image ID')
    parser.add_argument('--backend-only',action='store_true',help='Skip account task path when application dependencies are absent')
    args=parser.parse_args()
    print(json.dumps(smoke(args.image,not args.backend_only),indent=2))


if __name__=='__main__':main()
