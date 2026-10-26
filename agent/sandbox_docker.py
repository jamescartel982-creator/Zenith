"""Linux Docker isolation backend with no host mounts, network or fallback.

The local daemon and operator-approved image are trusted. Containers share their
host kernel: this is not a claim of VM isolation or universal escape resistance.
"""
import json
import os
import shutil
import subprocess
from threading import Event, Lock, Thread
import time
from uuid import uuid4

# The image must be public/runtime-only, with no embedded credentials. Reject
# unfamiliar environment names rather than forwarding image-provided secrets.
IMAGE_ENV = frozenset({'PATH', 'LANG', 'LC_ALL', 'LC_CTYPE', 'GPG_KEY',
    'PYTHON_VERSION', 'PYTHON_SHA256', 'PYTHONUNBUFFERED', 'PYTHONDONTWRITEBYTECODE',
    'PIP_NO_CACHE_DIR', 'AI_PROVIDER', 'HF_MODEL', 'HF_HOME', 'HF_HUB_DISABLE_XET',
    'AGENT_DATA_DIR', 'HF_REVISION', 'ZENITH_HOME', 'ZENITH_RESPONSE_MODE',
    'ZENITH_REPLY_STYLE', 'OMP_NUM_THREADS', 'TOKENIZERS_PARALLELISM'})
PROXY_NAMES = ('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'NO_PROXY', 'FTP_PROXY',
               'http_proxy', 'https_proxy', 'all_proxy', 'no_proxy', 'ftp_proxy')
# PID 1 owns the deadline in a separate process from submitted code. The timer
# starts before stdin is read and survives loss of the host controller/attach
# client. Exiting the namespace init stops its remaining processes as well.
BOOTSTRAP = """import os,subprocess,sys,threading
os.environ.clear()
timer=threading.Timer(int(sys.argv[1]),lambda:os._exit(124))
timer.daemon=True
timer.start()
try:
    source=sys.stdin.buffer.read(8193)
    if len(source)>8192:
        sys.exit(125)
    runner="import os,sys; os.environ.clear(); exec(compile(sys.argv[1],'<zenith-sandbox>','exec'),{'__name__':'__main__'})"
    result=subprocess.run([sys.executable,'-I','-S','-B','-u','-c',runner,source.decode('utf-8')],env={},stdin=subprocess.DEVNULL)
    sys.exit(result.returncode)
finally:
    timer.cancel()
"""


class SandboxUnavailable(OSError):
    pass


class DockerSandbox:
    def __init__(self, policy):
        self.policy = policy
        # Explicit socket, no inherited remote context/TLS. No credential file is
        # read or changed and no image pull/build or package install is performed.
        self.docker = shutil.which('docker')
        self.environment = {k: v for k, v in os.environ.items() if k not in {
            'DOCKER_HOST', 'DOCKER_CONTEXT', 'DOCKER_TLS', 'DOCKER_TLS_VERIFY', 'DOCKER_CERT_PATH'}}

    def _command(self, *args):
        if not self.docker or os.name != 'posix':
            raise SandboxUnavailable('A local Linux Docker backend is required; no host fallback')
        return [self.docker, '--host=unix:///var/run/docker.sock', *args]

    def _control(self, *args, timeout=5):
        try:
            result = subprocess.run(self._command(*args), env=self.environment,
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=timeout, check=False)
        except (OSError, subprocess.TimeoutExpired):
            raise SandboxUnavailable('Local sandbox control failed; no host fallback') from None
        if result.returncode or len(result.stdout) > 65536:
            # Docker's error text may contain private configuration; don't relay it.
            raise SandboxUnavailable('Local sandbox control failed; no host fallback')
        return result.stdout

    def _preflight(self):
        if not self.policy.enabled:
            raise PermissionError('Isolated Python execution is disabled')
        if self._control('info', '--format', '{{.OSType}}').strip() != b'linux':
            raise SandboxUnavailable('The sandbox requires a Linux Docker daemon')
        if self._control('info', '--format', '{{.CgroupVersion}} {{.MemoryLimit}} {{.PidsLimit}} {{.CPUCfsQuota}}').strip() != b'2 true true true':
            raise SandboxUnavailable('Cgroup v2 memory, process and CPU limits are required')
        try:
            security = json.loads(self._control('info', '--format', '{{json .SecurityOptions}}'))
            if 'name=seccomp,profile=builtin' not in security:
                raise ValueError('Builtin seccomp is required')
            image = json.loads(self._control('image', 'inspect', self.policy.image))[0]
            config = image['Config']
            names = {v.partition('=')[0] for v in config.get('Env') or []}
            if image['Id'] != self.policy.image or image.get('Os') != 'linux' or config.get('Volumes') or names - IMAGE_ENV:
                raise ValueError('Unapproved image properties')
        except (ValueError, KeyError, TypeError, IndexError):
            raise SandboxUnavailable('Sandbox image must be reviewed, local, Linux, without volumes or secret-bearing environment') from None

    def run(self, source, authority_check):
        # The caller is trusted Python, but still enforce the same program bound
        # for direct backend uses and never accept user-selected Docker arguments.
        from .sandbox import validate_program
        validate_program({'source': source})
        authority_check()
        self._preflight()
        authority_check()
        name = 'zenith-sandbox-' + uuid4().hex
        process = None
        readers = []
        writer = None
        output = {'stdout': bytearray(), 'stderr': bytearray()}
        overflow, io_failed, write_done = Event(), Event(), Event()
        lock = Lock()
        created = False
        started = time.monotonic()
        try:
            # All configuration is server-owned. None of these resources can be
            # enlarged through a model's source or arguments.
            arguments = ['create', '--name', name, '--pull', 'never', '--interactive',
                '--network', 'none', '--ipc', 'none', '--cgroupns', 'private', '--read-only', '--user', '65534:65534',
                '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges=true',
                '--pids-limit', '32', '--memory', '128m', '--memory-swap', '128m',
                '--cpus', '0.5', '--ulimit', 'nofile=64:64', '--ulimit', 'nproc=32:32',
                '--label', 'io.zenith.sandbox=1',
                '--label', 'io.zenith.deadline_seconds=' + str(self.policy.seconds),
                '--restart', 'no', '--no-healthcheck', '--stop-timeout', '1', '--log-driver', 'none',
                '--tmpfs', '/work:rw,noexec,nosuid,nodev,size=16m,mode=1777',
                '--tmpfs', '/tmp:rw,noexec,nosuid,nodev,size=16m,mode=1777',
                '--workdir', '/work', '--entrypoint', 'python']
            # Docker client proxy defaults must not become worker credentials.
            for key in PROXY_NAMES:
                arguments.extend(['--env', key + '='])
            arguments.extend([self.policy.image, '-I', '-S', '-B', '-u', '-c', BOOTSTRAP, str(self.policy.seconds)])
            self._control(*arguments)
            created = True
            authority_check()
            process = subprocess.Popen(self._command('start', '--attach', '--interactive', name),
                env=self.environment, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            def read_stream(key, stream):
                try:
                    while True:
                        chunk = os.read(stream.fileno(), 1024)
                        if not chunk:
                            return
                        with lock:
                            size = sum(len(value) for value in output.values())
                            if size + len(chunk) > self.policy.output_bytes:
                                overflow.set()
                            else:
                                output[key].extend(chunk)
                        if overflow.is_set():
                            return
                except (OSError, ValueError):
                    io_failed.set()

            def write_source():
                try:
                    process.stdin.write(source.encode('utf-8'))
                    process.stdin.close()
                except (BrokenPipeError, OSError, ValueError):
                    io_failed.set()
                finally:
                    write_done.set()

            for key in output:
                thread = Thread(target=read_stream, args=(key, getattr(process, key)), daemon=True)
                thread.start(); readers.append(thread)
            writer = Thread(target=write_source, daemon=True); writer.start()
            deadline = time.monotonic() + self.policy.seconds
            while process.poll() is None:
                authority_check()
                if overflow.is_set():
                    raise ValueError('Sandbox output budget exceeded')
                if io_failed.is_set():
                    raise SandboxUnavailable('Sandbox communication failed')
                if time.monotonic() >= deadline:
                    raise ValueError('Sandbox wall-time budget exceeded')
                time.sleep(0.05)
            for thread in readers:
                thread.join(timeout=1)
            authority_check()
            if overflow.is_set():
                raise ValueError('Sandbox output budget exceeded')
            if io_failed.is_set() or not write_done.wait(1) or any(t.is_alive() for t in readers):
                raise SandboxUnavailable('Sandbox communication failed')
            # ExitCode comes from the container, not merely the attach client.
            try:
                state = json.loads(self._control('inspect', '--format', '{{json .State}}', name))
                if state['Running'] or state.get('Status') != 'exited' or type(state['ExitCode']) is not int or state.get('OOMKilled') or process.returncode != state['ExitCode']:
                    raise ValueError()
                exit_code = state['ExitCode']
            except (ValueError, KeyError, TypeError):
                raise SandboxUnavailable('Sandbox did not stop cleanly') from None
            authority_check()
            if exit_code == 124:
                raise ValueError('Sandbox wall-time budget exceeded')
            return {'status': 'completed' if exit_code == 0 else 'failed', 'exit_code': exit_code,
                'stdout': bytes(output['stdout']).decode('utf-8', errors='replace'),
                'stderr': bytes(output['stderr']).decode('utf-8', errors='replace'),
                'elapsed_ms': round((time.monotonic()-started)*1000, 3),
                'backend': 'docker-linux', 'image': self.policy.image, 'network': 'none',
                'host_mounts': False, 'persistent_workspace': False, 'deadline_owner': 'container-pid1'}
        finally:
            # Remove even on cancellation/revocation, budget failure or create
            # timeout (the daemon may have created it before its response failed).
            cleanup_failed = False
            try:
                self._control('rm', '--force', '--volumes', name)
            except SandboxUnavailable:
                cleanup_failed = created
            if process is not None:
                if process.poll() is None:
                    process.kill()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    cleanup_failed = True
                for stream in (process.stdin, process.stdout, process.stderr):
                    if stream and not stream.closed:
                        try: stream.close()
                        except OSError: pass
            for thread in readers + ([writer] if writer else []):
                thread.join(timeout=1)
            if cleanup_failed:
                raise SandboxUnavailable('Sandbox cleanup could not be confirmed; operator reconciliation required')
