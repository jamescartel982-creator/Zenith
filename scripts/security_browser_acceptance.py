"""Real isolated Chromium/HTTP security checks; fixture model, never a live target."""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import secrets
import socket
import tempfile
from threading import Event, Thread
import time


def run():
    from playwright.sync_api import sync_playwright, expect
    from fastapi import HTTPException, Request
    import httpx
    import uvicorn
    from agent.config import Settings
    from agent.core import Agent
    from agent.server import create_app
    key = secrets.token_urlsafe(32)
    payload = ('Safe prefix ' + key + ' end.\n<script>window.__xss=true</script>\n'
               '<img id="xss-node" src=x onerror="window.__xss=true">\n'
               '<svg onload="window.__xss=true"></svg>\n[javascript](javascript:alert(1))')
    class FixtureProvider:
        model = None
        def stream(self, messages, cancel):
            for offset in range(0, len(payload), 7):
                if cancel.is_set(): return
                yield payload[offset:offset+7], messages
    with tempfile.TemporaryDirectory(prefix='zenith-security-browser-') as folder:
        settings = replace(Settings(), provider='huggingface', data_dir=folder, api_token=key)
        agent = Agent(settings, FixtureProvider())
        password = 'temporary isolated browser password'
        agent.personal.register('owner1', 'Owner', password)
        agent.personal.register('reader1', '<img src=x onerror=window.__xss=true>', password)
        code_path = agent.admin.initialize('owner1', path=Path(folder)/'private-owner-code.txt')
        app = create_app(settings, agent)
        waiting, release = Event(), Event()
        @app.get('/api/admin/_test_delayed')
        def delayed(request: Request):
            token = request.cookies.get('zenith_login', '')
            user = agent.personal.user_for_token(token)
            state = agent.admin.status(user['id'], token) if user else {}
            if not state.get('eligible') or not state.get('elevated'): raise HTTPException(403, 'Owner required')
            waiting.set()
            if not release.wait(15): raise RuntimeError('Test response release timed out')
            return {'private': 'owner-private-test-marker'}
        sock = socket.socket(); sock.bind(('127.0.0.1', 0)); sock.listen(16)
        origin = 'http://127.0.0.1:' + str(sock.getsockname()[1])
        server = uvicorn.Server(uvicorn.Config(app, log_level='error', access_log=False))
        thread = Thread(target=lambda: server.run(sockets=[sock]), daemon=True); thread.start()
        deadline = time.monotonic() + 15
        while not server.started:
            if not thread.is_alive() or time.monotonic() > deadline: raise RuntimeError('Test server failed to start')
            time.sleep(.02)
        errors, outside = [], []
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                try:
                    page = browser.new_page()
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    def restrict(route):
                        if route.request.url.startswith(origin + '/'): route.continue_()
                        else: outside.append(route.request.url); route.abort()
                    page.route('**/*', restrict)
                    page.add_init_script("sessionStorage.setItem('zenith_token','legacy-test-key-to-be-removed')")
                    page.goto(origin)
                    expect(page.locator('#access')).to_have_attribute('open', '')
                    page.locator('#token').fill(key); page.locator('#connect').click()
                    expect(page.locator('#greeting')).to_contain_text('Welcome to Zenith')
                    expect(page.locator('#token')).to_have_value('')
                    assert page.evaluate("sessionStorage.getItem('zenith_token')") is None
                    assert key not in page.content()
                    assert 'zenith_access' not in page.evaluate('document.cookie')
                    cookie = next(item for item in page.context.cookies() if item['name'] == 'zenith_access')
                    assert cookie['httpOnly'] and cookie['sameSite'] == 'Strict' and key not in cookie['value']
                    page.reload(); expect(page.locator('#access')).not_to_have_attribute('open', '')
                    def login(username):
                        page.locator('#open-account').click()
                        page.locator('#username').fill(username); page.locator('#password').fill(password)
                        page.locator('#account-submit').click()
                        expect(page.locator('#greeting')).to_contain_text('Welcome back,')
                        expect(page.locator('#account-dialog')).not_to_be_visible()
                        # Greeting and dialog closure precede connect()'s skill
                        # hydration. Wait for the completed login, not a delay.
                        expect(page.locator('#account-submit')).to_be_enabled()
                        page.wait_for_function('() => skillStateReady')
                    login('owner1'); expect(page.locator('#open-admin')).to_be_visible()
                    page.locator('#prompt').fill('Show the supplied security test answer.')
                    page.locator('#composer').evaluate('(form) => form.requestSubmit()')
                    expect(page.locator('#messages')).to_contain_text('[REDACTED]')
                    expect(page.locator('#messages')).to_contain_text('<script>')
                    assert key not in page.locator('#messages').inner_text()
                    assert page.locator('#xss-node').count() == 0
                    assert page.evaluate('window.__xss === undefined')
                    assert page.locator('#messages a[href^="javascript:"]').count() == 0
                    # Test the renderer independently of backend redaction.
                    assert page.evaluate("""() => {
                        const node = renderMarkdown('[bad](https://user:pass@outside.invalid/path)');
                        return node.querySelectorAll('a').length;
                    }""") == 0
                    page.evaluate("""() => {
                        window.__cspViolations = [];
                        document.addEventListener('securitypolicyviolation', e => window.__cspViolations.push(e.violatedDirective));
                        const script = document.createElement('script'); script.textContent = 'window.__cspProbe=true'; document.body.append(script);
                    }""")
                    page.wait_for_function('() => window.__cspViolations.length > 0')
                    assert page.evaluate('window.__cspProbe === undefined')
                    page.locator('#open-admin').click()
                    page.locator('#admin-code').fill(code_path.read_text().strip())
                    page.locator('#admin-unlock button').click()
                    expect(page.locator('#admin-controls')).to_be_visible()
                    page.locator('#owner-help').click()
                    expect(page.locator('#owner-help-text')).to_contain_text('zenith admin')
                    page.locator('[data-close="admin-dialog"]').click()
                    page.evaluate("""() => { void api('/api/admin/_test_delayed')
                        .then(value => {window.__lateOwnerResult = value;})
                        .catch(error => {window.__lateOwnerError = error.message;}); }""")
                    deadline = time.monotonic() + 5
                    while not waiting.is_set():
                        if time.monotonic() > deadline: raise RuntimeError('Delayed owner request did not start')
                        page.wait_for_timeout(20)  # Pump routed browser requests while the server starts waiting.
                    page.locator('#open-account').click(); page.locator('#logout').click()
                    expect(page.locator('#greeting')).to_contain_text('Welcome to Zenith')
                    login('reader1'); expect(page.locator('#open-admin')).to_be_hidden()
                    expect(page.locator('#greeting')).to_contain_text('<img src=x')
                    assert page.evaluate('window.__xss === undefined')
                    release.set(); page.wait_for_function('() => window.__lateOwnerError !== undefined')
                    assert page.evaluate('window.__lateOwnerResult === undefined')
                    assert page.locator('#owner-help-text').inner_text() == ''
                    assert page.evaluate("fetch('/api/admin/help').then(r => r.status)") == 403
                    title = 'Reader confidential test title 173'
                    page.locator('#prompt').fill(title)
                    page.locator('#composer').evaluate('(form) => form.requestSubmit()')
                    expect(page.locator('#messages')).to_contain_text('[REDACTED]')
                    expect(page.locator('#conversation-list')).to_contain_text(title)
                    assert not outside, 'Untrusted output attempted a network request'
                    if not page.locator('#access').evaluate('(node) => node.open'): page.locator('#access summary').click()
                    page.locator('#clear-access').click(); expect(page.locator('#status')).to_have_text('Disconnected')
                    assert all(item['name'] not in {'zenith_access','zenith_login'} for item in page.context.cookies())
                    assert title not in page.locator('#conversation-list').inner_text()
                    assert not errors, errors
                    native = httpx.get(origin + '/api/account', headers={'Authorization':'Bearer ' + key}, timeout=5)
                    assert native.status_code == 200
                finally: browser.close()
        finally:
            release.set(); server.should_exit = True; thread.join(10); sock.close()
            if thread.is_alive(): raise RuntimeError('Test server did not stop')
    return {'actual_loopback_chromium': True, 'model': 'explicit fixture; no neural quality claim',
        'raw_access_key_absent_from_storage_dom_and_output': True, 'httponly_grant_survived_reload': True,
        'html_svg_and_stored_display_name_did_not_execute': True, 'unsafe_link_rejected': True,
        'inline_script_blocked_by_csp': True, 'owner_help_requires_owner_elevation': True,
        'late_owner_response_discarded_after_account_switch': True, 'disconnect_cleared_credentials': True,
        'disconnect_cleared_private_conversation_titles': True,
        'native_bearer_compatibility': True, 'external_requests': 0, 'javascript_errors': errors,
        'production_state_modified': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--output', type=Path, required=True); args = parser.parse_args()
    from agent.config import Settings
    from agent.paths import config_file
    from scripts.platform_protection import check_destination
    args.output = check_destination(Settings(), config_file(), args.output)
    result = run()
    with args.output.open('x', encoding='utf-8') as handle: json.dump(result, handle, indent=2); handle.write('\n')
    print(json.dumps(result, indent=2))
