"""Terminal chat with explicit rating, correction, and dataset approval."""
import argparse
import getpass
import sys
from uuid import uuid4
from .branding import show_banner
from .core import Agent
from .config import Settings
from .skills import get_skill
from .skill_access import parse_skill_command



class TerminalSession:
    """Masked owner login and command handling; secrets never reach the model."""
    def __init__(self, agent, session):
        self.agent, self.session = agent, session
        self.user = None
        self.token = None
        self.last_skill = None

    @property
    def user_id(self):
        return self.user['id'] if self.user else None

    def close(self):
        if self.token:
            self.agent.admin.lock(self.token)
            self.agent.personal.logout(self.token)
        self.user = None
        self.token = None

    def refresh(self):
        if self.token and self.agent.personal.user_for_token(self.token) is None:
            self.close()
            self.session = str(uuid4())
            print('Login expired. New anonymous conversation started; security skills are locked.')
        current = self.agent.skills.active(self.session, self.user_id, self.token)
        if self.last_skill and current != self.last_skill:
            print('Active skill: ' + get_skill(current)['name'] + '. Protected access may have expired or been locked.')
        self.last_skill = current

    def command(self, text):
        if text.split() and text.split()[0].casefold() == '/admin':
            if text.casefold() == '/admin unlock':
                if not sys.stdin.isatty():
                    raise ValueError('Admin unlock needs an interactive terminal with masked secret prompts')
                username = input('Owner username> ').strip()
                password = getpass.getpass('Account password> ')
                user = self.agent.personal.login(username, password)
                del password
                if user is None:
                    raise ValueError('Owner account or credentials were not accepted')
                token = self.agent.personal.issue_session(user['id'])
                try:
                    code = getpass.getpass('Private admin code> ')
                    accepted = self.agent.admin.unlock(user['id'], token, code.strip())
                    del code
                    if not accepted:
                        raise ValueError('Owner account or credentials were not accepted')
                except BaseException:
                    self.agent.personal.logout(token)
                    raise
                self.close()
                self.user, self.token = user, token
                self.session = str(uuid4())
                self.last_skill = 'general'
                show_banner()
                print('Welcome back, ' + user['display_name'] + '.')
                print('Owner unlocked for 15 minutes. New private conversation started. Use /skill list, then /skill ID.')
            elif text.casefold() == '/admin lock':
                self.close()
                self.session = str(uuid4())
                self.last_skill = 'general'
                print('Admin locked. Security skills cleared. New anonymous conversation started.')
            else:
                raise ValueError('Use /admin unlock or /admin lock; never type a code as a command argument')
            return True
        if parse_skill_command(text) is None:
            return False
        result = self.agent.skills.command(self.session, text, self.user_id, self.token)
        self.last_skill = result['skill']
        print(result['message'])
        for skill in result.get('skills', []):
            print(skill['id'] + ' — ' + skill['name'])
        return True


def main():
    parser = argparse.ArgumentParser(description='Chat with Zenith locally')
    parser.add_argument('--session', default=None, help='Resume a conversation UUID')
    parser.add_argument('--mode', choices=['fast','thorough'], default=None)
    parser.add_argument('--skill', default=None, help='Public starting skill; use /admin unlock for protected skills')
    parser.add_argument('--reply-style',choices=['auto','brief','full'],default=None)
    parser.add_argument('--stats',action='store_true',help='Show reported token usage after each completed answer')
    args = parser.parse_args()
    if args.session:
        from uuid import UUID
        try:
            session = str(UUID(args.session))
        except ValueError:
            parser.error("--session must be a valid conversation UUID")
    else:
        session = str(uuid4())
    agent = Agent(Settings())
    terminal = TerminalSession(agent, session)
    if not agent.personal.conversation_access(session):
        parser.error('This conversation belongs to a signed-in account. Start a new chat to sign in.')
    if args.skill is not None:
        try:
            agent.skills.select(session, args.skill)
        except (ValueError, PermissionError) as exc:
            parser.error(str(exc) + '; start chat, then use /admin unlock and /skill ID')
    last_id = None
    history = agent.store.history(session, limit=1)
    if history:
        last_id = history[-1]['id']
    show_banner()
    print(f'Zenith | {agent.settings.model_name}\nSession: {session}')
    print('/good /bad: rate | /approve: approve last answer for training')
    print('/correct: write & approve a better answer | /new: new chat | /quit')
    print('/skill list | /skill ID | /skill off | /skill status | /admin unlock | /admin lock')
    try:
        while True:
            try:
                text = input('\nYou> ').strip()
                if not text:
                    continue
                previous_session = session
                terminal.refresh()
                session = terminal.session
                if session != previous_session:
                    last_id = None
                if terminal.command(text):
                    session = terminal.session
                    last_id = None if not agent.store.history(session, limit=1) else agent.store.history(session, limit=1)[-1]['id']
                    continue
                if text == '/quit':
                    break
                if text == '/new':
                    session, last_id = str(uuid4()), None
                    terminal.session = session
                    print(f'Session: {session}')
                    continue
                if text in {'/good', '/bad', '/approve', '/correct'}:
                    if not last_id:
                        print('No response to rate yet.')
                        continue
                    correction = input('Correct answer> ').strip() if text == '/correct' else None
                    if text == '/correct' and not correction:
                        print('No correction saved.')
                        continue
                    previous = agent.store.history(session, limit=1)[-1]
                    if text == '/approve':
                        rating = previous['rating'] or 'good'
                        correction = previous['correction']
                    else:
                        rating = 'bad' if text in {'/bad', '/correct'} else 'good'
                    agent.store.review(session, last_id, rating, text in {'/approve', '/correct'}, correction)
                    print('Review saved. Weights change only when you run training.')
                    continue
                if not agent.personal.conversation_access(session, terminal.user_id or '', create=True):
                    raise PermissionError('Conversation not found')
                stream=agent.stream_answer(text,session,user_id=terminal.user_id,response_mode=args.mode,reply_style=args.reply_style,login_token=terminal.token)
                print('\nZenith> ',end='',flush=True)
                result=None
                try:
                    for event in stream:
                        if event['type']=='delta':print(event['text'],end='',flush=True)
                        elif event['type']=='result':result=event['result']
                finally:stream.close()
                print()
                if result:
                    last_id=result['id']
                    usage=result['performance'].get('usage') or {}
                    if args.stats:print(f"[Reported tokens: {usage.get('input_tokens')} in / {usage.get('output_tokens')} out · {result['latency_ms']/1000:.2f}s]")
                    if usage.get('finish_reason')=='length':print('[Output cap reached. Use --reply-style full or ask to continue.]')
            except (EOFError, KeyboardInterrupt):
                break
            except Exception as exc:
                print(f'Error: {exc}')
    finally:
        terminal.close()
    print('\nGoodbye.')


if __name__ == '__main__':
    main()
