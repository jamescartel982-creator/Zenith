"""Actual loopback Chromium workflows; fixture model, real auth/storage/CSV/catalog."""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import socket
import tempfile
from threading import Thread
import time


class FixtureProvider:
    model=None
    def __init__(self):self.messages=[]
    def generate(self,messages):self.messages.append(messages);return 'Fixture answer.',messages


def run():
    from playwright.sync_api import sync_playwright,expect
    import uvicorn
    from agent.config import Settings
    from agent.core import Agent
    from agent.server import create_app
    from agent.skills import get_skill
    with tempfile.TemporaryDirectory(prefix='zenith-browser-productivity-') as folder:
        settings=replace(Settings(),provider='huggingface',data_dir=folder,api_token='')
        provider=FixtureProvider();agent=Agent(settings,provider)
        pack=Path(folder)/'fixture.jsonl'
        header={'kind':'zenith-skill-pack','schema_version':1,'pack_id':'browser','license':'Apache-2.0',
                'source':'local-authored','source_revision':'synthetic-browser-test','reviewed':True}
        profile=get_skill('general');profile.pop('resources',None)
        profile.update(id='x-browser-fixture',name='Browser fixture',instruction='Review the explicitly supplied browser fixture.')
        pack.write_text(json.dumps(header)+'\n'+json.dumps(profile)+'\n')
        agent.skills.catalog.install(pack,True)
        sock=socket.socket();sock.bind(('127.0.0.1',0));sock.listen(16)
        origin='http://127.0.0.1:'+str(sock.getsockname()[1])
        server=uvicorn.Server(uvicorn.Config(create_app(settings,agent),log_level='error',access_log=False))
        thread=Thread(target=lambda:server.run(sockets=[sock]),daemon=True);thread.start()
        deadline=time.monotonic()+15
        while not server.started:
            if not thread.is_alive() or time.monotonic()>deadline:raise RuntimeError('Test server failed to start')
            time.sleep(.02)
        errors=[]
        try:
            with sync_playwright() as playwright:
                browser=playwright.chromium.launch(headless=True)
                try:
                    page=browser.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
                    page.route('**/*',lambda route:route.continue_() if route.request.url.startswith(origin+'/') else route.abort())
                    page.goto(origin);expect(page.locator('#greeting')).to_contain_text('Welcome')
                    def register(name):
                        page.locator('#open-account').click();page.locator('#toggle-register').click()
                        page.locator('#username').fill(name);page.locator('#display-name').fill(name)
                        page.locator('#password').fill('temporary browser test password')
                        page.locator('#account-submit').click()
                        expect(page.locator('#greeting')).to_contain_text(name)
                    register('alice')
                    page.locator('#open-account').click();page.locator('#signed-in-panel details summary').click()
                    page.locator('#preference-language').select_option('fr')
                    page.locator('#preference-tone').select_option('friendly')
                    page.locator('#preference-reply_style').select_option('brief')
                    page.locator('#preferences-form button').click()
                    expect(page.locator('#preferences-status')).to_contain_text('Saved')
                    page.locator('[data-close="account-dialog"]').click()
                    page.locator('#open-analysis').click()
                    page.locator('#analysis-csv').fill('value\n0.1\n0.2\n0.2\n')
                    before=len(provider.messages);page.locator('#analysis-submit').click()
                    expect(page.locator('#analysis-status')).to_contain_text('Complete')
                    expect(page.locator('#analysis-result')).to_contain_text('0.5')
                    expect(page.locator('#analysis-result')).to_contain_text('1 exact duplicate')
                    assert len(provider.messages)==before
                    page.locator('#analysis-csv').fill('duplicate,duplicate\n1,2\n')
                    page.locator('#analysis-submit').click()
                    expect(page.locator('#analysis-status')).to_contain_text('Column names must be unique')
                    expect(page.locator('#analysis-result')).to_be_empty()
                    assert len(provider.messages)==before
                    page.locator('[data-close="analysis-dialog"]').click()
                    page.locator('#open-skills').click();page.locator('#skills-query').fill('Browser fixture')
                    page.get_by_role('button',name='Use Browser fixture',exact=True).click()
                    expect(page.locator('#skill-select')).to_have_value('x-browser-fixture')
                    page.locator('#prompt').fill('Explain this example briefly.')
                    page.locator('#composer').evaluate('(form) => form.requestSubmit()')
                    expect(page.locator('#messages')).to_contain_text('Fixture answer.')
                    assert 'French' in provider.messages[-1][0]['content']
                    assert 'untrusted task guidance' in provider.messages[-1][0]['content']
                    page.locator('#open-account').click();page.locator('#logout').click()
                    expect(page.locator('#greeting')).to_contain_text('Welcome to Zenith')
                    expect(page.locator('#analysis-csv')).to_have_value('')
                    register('bobby')
                    page.locator('#open-account').click();page.locator('#signed-in-panel details summary').click()
                    expect(page.locator('#preference-language')).to_have_value('default')
                    expect(page.locator('#preference-tone')).to_have_value('neutral')
                    assert not errors,errors
                finally:browser.close()
        finally:
            server.should_exit=True;thread.join(10);sock.close()
            if thread.is_alive():raise RuntimeError('Test server did not terminate')
    return {'actual_loopback_chromium':True,'csv_exact_sum_displayed':True,'stale_results_cleared_on_error':True,'csv_model_calls':0,
            'imported_profile_selected':True,'preferences_applied_to_model_context':True,
            'account_switch_isolated':True,'dataset_cleared_on_logout':True,'javascript_errors':errors,
            'model':'explicit fixture; no neural quality or language-generation claim', 'production_state_modified':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    from agent.config import Settings
    from agent.paths import config_file
    from scripts.platform_protection import check_destination
    try:args.output=check_destination(Settings(),config_file(),args.output)
    except ValueError as exc:parser.error(str(exc))
    report=run()
    with args.output.open('x') as handle:json.dump(report,handle,indent=2);handle.write('\n')
    print(json.dumps(report))
