"""Real Chromium: open chat without a shared token, preserve browser/account isolation."""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import secrets
import socket
import tempfile
from threading import Thread
import time


def run():
    import uvicorn
    from playwright.sync_api import sync_playwright, expect
    from agent.config import Settings
    from agent.core import Agent
    from agent.server import create_app
    class Fixture:
        model = None
        def generate(self, messages):
            return 'Public chat fixture answer.', messages
    with tempfile.TemporaryDirectory(prefix='zenith-public-chat-ui-') as folder:
        key = secrets.token_urlsafe(32)
        settings = replace(Settings(), provider='huggingface', data_dir=folder, api_token=key, public_chat=True)
        agent = Agent(settings, Fixture())
        sock = socket.socket(); sock.bind(('127.0.0.1', 0)); sock.listen(16)
        origin = 'http://127.0.0.1:' + str(sock.getsockname()[1])
        server = uvicorn.Server(uvicorn.Config(create_app(settings, agent), access_log=False, log_level='error'))
        thread = Thread(target=lambda: server.run(sockets=[sock]), daemon=True); thread.start()
        deadline = time.monotonic() + 15
        while not server.started:
            if not thread.is_alive() or time.monotonic() > deadline: raise RuntimeError('Fixture server failed')
            time.sleep(.02)
        errors = []
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                try:
                    context = browser.new_context(); other = browser.new_context()
                    page = context.new_page(); page.on('pageerror', lambda e: errors.append(str(e)))
                    page.goto(origin)
                    expect(page.locator('#access')).to_be_hidden()
                    page.wait_for_function('() => skillStateReady')
                    expect(page.locator('#error')).to_be_hidden()
                    page.locator('#prompt').fill('Explain the supplied public chat example.')
                    page.locator('#composer').evaluate('(form) => form.requestSubmit()')
                    expect(page.locator('#messages')).to_contain_text('Public chat fixture answer.')
                    expect(page.locator('#send')).to_be_visible(); expect(page.locator('#send')).to_be_enabled()
                    expect(page.locator('#messages details.review')).to_have_count(0)
                    session = page.evaluate("sessionStorage.getItem('zenith_session')")
                    assert key not in page.content()
                    assert 'zenith_guest' not in page.evaluate('document.cookie')
                    assert other.request.get(origin + '/api/account').status == 200
                    assert other.request.get(origin + '/api/history/' + session).status == 404
                    page.reload(); page.wait_for_function('() => skillStateReady')
                    expect(page.locator('#messages')).to_contain_text('Public chat fixture answer.')
                    expect(page.locator('#access')).to_be_hidden()
                    page.locator('#open-account').click(); page.locator('#toggle-register').click()
                    page.locator('#username').fill('public_reader'); page.locator('#display-name').fill('Public Reader')
                    page.locator('#password').fill('temporary public chat fixture password')
                    page.locator('#account-submit').click()
                    expect(page.locator('#greeting')).to_contain_text('Public Reader')
                    page.wait_for_function('() => skillStateReady')
                    expect(page.locator('#open-admin')).to_be_hidden()
                    assert context.request.get(origin + '/api/admin/help').status == 403
                    user_id = page.evaluate('activeUser.id')
                    page.locator('#prompt').fill('Explain the account-owned example.')
                    page.locator('#composer').evaluate('(form) => form.requestSubmit()')
                    expect(page.locator('#messages')).to_contain_text('Public chat fixture answer.')
                    expect(page.locator('#send')).to_be_visible(); expect(page.locator('#send')).to_be_enabled()
                    expect(page.locator('#messages details.review')).to_have_count(1)
                    account_session = page.evaluate("sessionStorage.getItem('zenith_session')")
                    page.locator('#open-account').click(); page.locator('#logout').click()
                    expect(page.locator('#open-account')).to_have_text('Sign in')
                    page.wait_for_function('() => skillStateReady')
                    assert page.evaluate('(key) => localStorage.getItem(key)', 'zenith_last_' + user_id) == account_session
                    page.locator('#open-account').click()
                    page.locator('#username').fill('public_reader')
                    page.locator('#password').fill('temporary public chat fixture password')
                    page.locator('#account-submit').click()
                    expect(page.locator('#greeting')).to_contain_text('Public Reader')
                    page.wait_for_function('() => skillStateReady')
                    expect(page.locator('#messages')).to_contain_text('Public chat fixture answer.')
                    assert page.evaluate("sessionStorage.getItem('zenith_session')") == account_session
                    assert not errors, errors
                    return {'real_chromium':True, 'model':'explicit fixture', 'token_entry_required':False,
                            'server_access_prompt_hidden':True, 'chat_and_reload':True,
                            'guest_browser_isolation':True, 'account_registration_without_server_key':True,
                            'guest_review_controls_hidden':True, 'account_conversation_restored_after_logout':True,
                            'admin_denied':True, 'no_javascript_errors':True}
                finally: browser.close()
        finally: server.should_exit = True; thread.join(15)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True); args = parser.parse_args()
    result = run(); args.output.write_text(json.dumps(result, indent=2) + '\n'); print(json.dumps(result))


if __name__ == '__main__': main()
