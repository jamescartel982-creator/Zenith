"""Operator-invoked acceptance against four real, separately started runtimes.

Uses original Zenith account/MFA code in fresh test-owned state; never substitutes
scripted models, sends external messages, or enables native execution tools.
"""
import argparse
from dataclasses import replace
import importlib.util
import json
from pathlib import Path
import secrets
import time


def run(args):
    import httpx
    import pyotp
    from agent.config import Settings
    from agent.core import Agent
    from agent.server import create_app as account_app
    from zenith_integrations.config import BridgeConfig
    from zenith_integrations.gateway import create_app
    from zenith_integrations.shared.native_task import chat_scope
    from zenith_integrations.shared.secrets import read_json, write_private_new
    from zenith_inference.identity import verify

    project = Path(__file__).resolve().parents[4]
    helper = project/'integrations/inference_service/tests/integration/native_acceptance.py'
    spec = importlib.util.spec_from_file_location('acceptance_service', helper)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    root = args.directory.absolute()
    root.mkdir(mode=0o700, parents=True, exist_ok=False)
    identity_before = verify(args.identity)[1]
    configuration = BridgeConfig(**read_json(args.config))
    report = {'scripted_model':False, 'external_message_sent':False, 'live_orders_enabled':False, 'jobs':{}}
    settings = replace(Settings(), data_dir=str(root/'accounts'), api_token='')
    agent = Agent(settings)
    try:
        with module.serve(account_app(settings,agent=agent)) as accounts:
            write_private_new(root/'audit.key', secrets.token_urlsafe(48))
            config = replace(configuration, zenith_origin=accounts, zenith_access_token_file='',
                             database=str(root/'control.sqlite3'), audit_key_file=str(root/'audit.key'))
            with module.serve(create_app(config)) as bridge_origin, httpx.Client(base_url=accounts, timeout=10, trust_env=False) as account:
                password = secrets.token_urlsafe(32)
                account.post('/api/account/register', json={'username':'owner','display_name':'Acceptance Owner','password':password}).raise_for_status()
                agent.admin.initialize('owner', root/'test-owner.key')
                account.post('/api/admin/unlock', json={'code':(root/'test-owner.key').read_text().strip()}).raise_for_status()
                enrollment=account.post('/api/admin/mfa/setup', json={'password':password});enrollment.raise_for_status()
                account.post('/api/admin/mfa/confirm', json={'otp':pyotp.TOTP(enrollment.json()['secret']).now()}).raise_for_status()
                with httpx.Client(base_url=bridge_origin, cookies={'zenith_login':account.cookies['zenith_login']}, timeout=40, trust_env=False) as bridge:
                    response=bridge.get('/v1/runtimes');response.raise_for_status()
                    report['runtimes']=response.json()['runtimes']
                    unavailable={row['runtime']:row for row in report['runtimes'] if not row['connected']}
                    for runtime in ('zenith','hermes','openclaw','tradingagents'):
                        if runtime in unavailable:
                            report['jobs'][runtime]={'status':'blocked','reason':unavailable[runtime].get('unavailable_reason','native_runtime_not_ready')}
                            continue
                        operation='research' if runtime=='tradingagents' else 'chat'
                        if runtime=='zenith':payload={'model':'zenith','messages':[{'role':'user','content':'What is 2 plus 2? Answer with the number only.'}],'max_tokens':16,'temperature':0}
                        elif runtime=='tradingagents':payload={'ticker':'AAPL','as_of':'2025-01-17'}
                        else:payload={'message':'What is 2 plus 2? Answer with the number only.', 'conversation_id':'acceptance_'+runtime}
                        body={'runtime':runtime,'operation':operation,'payload':payload}
                        if runtime!='zenith':
                            denied=bridge.post('/v1/jobs', json=body, headers={'Idempotency-Key':secrets.token_hex(16)})
                            if denied.status_code!=403:raise AssertionError('Native execution was admitted without an exact owner grant')
                            scope={'runtime':runtime,'operation':operation,**(payload if runtime=='tradingagents' else chat_scope(payload,operation))}
                            grant=bridge.post('/v1/grants', json={'capability':'jobs.submit.'+runtime,'scope':scope,'seconds':300});grant.raise_for_status()
                            body['grant_id']=grant.json()['id']
                        started=time.monotonic();key=secrets.token_hex(16)
                        admitted=bridge.post('/v1/jobs', json=body, headers={'Idempotency-Key':key});admitted.raise_for_status()
                        job_id=admitted.json()['id']
                        duplicate=bridge.post('/v1/jobs', json=body, headers={'Idempotency-Key':key});duplicate.raise_for_status()
                        if duplicate.json()['id']!=job_id:raise AssertionError('Duplicate native execution admitted')
                        deadline=time.monotonic()+config.job_timeout+20
                        while True:
                            response=bridge.get('/v1/jobs/'+job_id);response.raise_for_status();state=response.json()
                            if state['status'] in {'succeeded','failed','cancelled','interrupted'}:break
                            if time.monotonic()>deadline:raise AssertionError('Bridge execution exceeded its bounded deadline')
                            time.sleep(.2)
                        measured={'status':state['status'],'seconds':time.monotonic()-started,'exact_grant_required':runtime!='zenith','duplicate_prevented':True}
                        report['jobs'][runtime]=measured
                        if state['status']!='succeeded':
                            measured['error_code']=state.get('error_code');measured['native_receipt']=state.get('native_receipt')
                            continue
                        response=bridge.get('/v1/jobs/'+job_id+'/result');response.raise_for_status();value=response.json()['result']
                        if runtime=='zenith':
                            measured['arithmetic_correct']=value['choices'][0]['message']['content'].strip()=='4';measured['usage']=value['usage']
                        elif runtime=='hermes':
                            measured['actual_runtime']=value['result'].get('runtime');measured['native_status']=value['result']['status']
                        elif runtime=='openclaw':measured['native_state']=value['result']['state']
                        else:
                            native=value['report'];measured.update(all_native_roles_completed=native.get('all_native_roles_completed'), rating=native.get('rating'), financial_quality_verified=native.get('financial_quality_verified'),model=native.get('model'), execution_metrics=native.get('execution_metrics'))
                        print(runtime+': '+json.dumps(measured),flush=True)
                    account.post('/api/account/logout').raise_for_status()
                    report['logout_revokes_bridge']=bridge.get('/healthz').status_code==401
                    if not report['logout_revokes_bridge']:raise AssertionError('Original account logout did not revoke bridge access')
        report['all_four_native_workflows_completed']=len(report['jobs'])==4 and all(job['status']=='succeeded' for job in report['jobs'].values())
    finally:
        report['original_model_artifacts_unchanged']=verify(args.identity)[1]==identity_before
        args.output.write_text(json.dumps(report,indent=2)+'\n')
    if not report['original_model_artifacts_unchanged']:raise AssertionError('Model identity changed')
    if not report['all_four_native_workflows_completed']:raise AssertionError('Four-system acceptance incomplete; inspect measured blockers in the report')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--identity',type=Path,required=True)
    parser.add_argument('--directory',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    run(parser.parse_args())
