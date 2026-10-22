"""Terminal chat with explicit rating, correction, and dataset approval."""
import argparse
from uuid import uuid4
from .core import Agent
from .config import Settings


def main():
    parser = argparse.ArgumentParser(description='Chat with Zenith locally')
    parser.add_argument('--session', default=None, help='Resume a conversation UUID')
    parser.add_argument('--mode', choices=['fast','thorough'], default=None)
    parser.add_argument('--skill', default='general', help='Instruction skill, such as mathematics or cybersecurity')
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
    last_id = None
    history = agent.store.history(session, limit=1)
    if history:
        last_id = history[-1]['id']
    print(f'Zenith | {agent.settings.model_name}\nSession: {session}')
    print('/good /bad: rate | /approve: approve last answer for training')
    print('/correct: write & approve a better answer | /new: new chat | /quit')
    while True:
        try:
            text = input('\nYou> ').strip()
            if not text:
                continue
            if text == '/quit':
                break
            if text == '/new':
                session, last_id = str(uuid4()), None
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
            result = agent.answer(text, session, response_mode=args.mode, skill=args.skill)
            last_id = result['id']
            print('\nZenith> ' + result['response'])
        except (EOFError, KeyboardInterrupt):
            break
        except Exception as exc:
            print(f'Error: {exc}')
    print('\nGoodbye.')


if __name__ == '__main__':
    main()
