"""Bounded owned native worker processes; cancellation never kills unrelated services."""
import asyncio
from contextlib import suppress
from dataclasses import asdict
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import signal
import sys
import time

from zenith_integrations.shared.secrets import read_json,write_private_new
from zenith_integrations.shared.native_http import NativeRefused

logger=logging.getLogger('zenith.trading')


class NativeWorkerFailure(RuntimeError):
    def __init__(self,error_type='native_research_failed'):
        self.code=error_type if re.fullmatch(r'[a-zA-Z0-9_]{1,80}',error_type) else 'native_research_failed'
        super().__init__(self.code)


def scoped_account(service,account):
    return hashlib.sha256(json.dumps([service,account],separators=(',',':')).encode()).hexdigest()


class NativeExecutor:
    def __init__(self,config):
        self.config=config
        self.gate=asyncio.Semaphore(1)

    def ready(self):
        from importlib.metadata import distribution
        self.config.verify_source()
        native=distribution('tradingagents')
        provenance=json.loads(native.read_text('direct_url.json') or '{}')
        from . import PIN
        if provenance.get('vcs_info',{}).get('commit_id')!=PIN:
            raise NativeRefused('unverified_native_distribution')
        for name in ('langchain-openai','langgraph','pandas','yfinance'):
            distribution(name)

    async def terminate(self,process):
        if process.returncode is not None:
            return
        try:
            if os.name=='posix':
                os.killpg(process.pid,signal.SIGTERM)
            else:
                process.terminate()
            await asyncio.wait_for(process.wait(),5)
        except TimeoutError:
            if os.name=='posix':
                with suppress(ProcessLookupError):os.killpg(process.pid,signal.SIGKILL)
            else:
                with suppress(ProcessLookupError):process.kill()
            await process.wait()
        except ProcessLookupError:
            await process.wait()

    async def execute(self,identifier,principal,request):
        async with self.gate:
            self.ready()
            account=scoped_account(principal.name,request.account_id)
            root=Path(self.config.state_directory)/'accounts'/account/'runs'/identifier
            root.mkdir(parents=True,mode=0o700,exist_ok=False)
            # Parent directories must be private as well, including on shared hosts.
            if os.name=='posix':
                for parent in (root.parent,root.parent.parent,root.parent.parent.parent):
                    parent.chmod(0o700)
            config_path=root/'worker-config.json';request_path=root/'request.json';output=root/'report.json'
            write_private_new(config_path,json.dumps(asdict(self.config)))
            write_private_new(request_path,request.model_dump_json())
            # A new child inherits platform/runtime trust settings, not arbitrary provider,
            # broker, owner or application secrets. Source and private paths are operator-owned.
            names={'PATH','SYSTEMROOT','WINDIR','COMSPEC','PATHEXT','TEMP','TMP','TMPDIR',
                   'LANG','LC_ALL','TZ','VIRTUAL_ENV','SSL_CERT_FILE','SSL_CERT_DIR','REQUESTS_CA_BUNDLE',
                   'CURL_CA_BUNDLE','HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','NO_PROXY',
                   'http_proxy','https_proxy','all_proxy','no_proxy','PYTHONPATH'}
            env={key:value for key,value in os.environ.items() if key in names or key.startswith(('CODEX_NETWORK_','CODEX_PROXY_'))}
            if 'PYTHONPATH' in env:
                env['PYTHONPATH']=os.pathsep.join(str(Path(value).resolve()) for value in env['PYTHONPATH'].split(os.pathsep) if value)
            for name in ('NO_PROXY','no_proxy'):
                env[name]=','.join(filter(None,(env.get(name,''),'127.0.0.1,localhost,::1')))
            env['PYTHONDONTWRITEBYTECODE']='1'
            process=None
            started=time.monotonic()
            try:
                creation=asyncio.create_task(asyncio.create_subprocess_exec(sys.executable,'-m','zenith_trading_service.worker',
                    '--config',str(config_path),'--request',str(request_path),'--output',str(output),
                    cwd=root,env=env,stdout=asyncio.subprocess.DEVNULL,stderr=asyncio.subprocess.DEVNULL,
                    start_new_session=os.name=='posix'))
                try:
                    process=await asyncio.shield(creation)
                except asyncio.CancelledError:
                    # Retain the spawn handle even if cancellation races OS admission.
                    while not creation.done():
                        try:await asyncio.shield(creation)
                        except asyncio.CancelledError:continue
                    process=creation.result()
                    raise
                async with asyncio.timeout(self.config.deadline_seconds):
                    code=await process.wait()
                if code or not output.is_file() or output.stat().st_size>1024*1024:
                    diagnostic=root/'worker-failure.json'
                    if diagnostic.is_file():
                        value=read_json(diagnostic)
                        raise NativeWorkerFailure(value.get('error_type','native_research_failed'))
                    raise NativeWorkerFailure('native_research_failed_or_exceeded_result_budget')
                result=read_json(output)
                if result.get('live_orders_enabled') is not False or result.get('model')!='zenith':
                    raise NativeRefused('invalid_native_report')
                return result
            finally:
                # No admission slot is released while its owned process is still alive.
                if process is not None:
                    cleanup=asyncio.create_task(self.terminate(process))
                    while not cleanup.done():
                        try:await asyncio.shield(cleanup)
                        except asyncio.CancelledError:continue
                    cleanup.result()
                logger.info(json.dumps({'event':'trading.worker_finished','job_id':identifier,
                    'duration_ms':round((time.monotonic()-started)*1000),'worker_finished':process is None or process.returncode is not None}))
