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
            stream=agent.stream_answer(text,session,response_mode=args.mode,skill=args.skill,reply_style=args.reply_style)
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
    print('\nGoodbye.')


if __name__ == '__main__':
    main()
