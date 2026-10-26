"""Explicit private service setup; never changes Zenith's saved profile."""
import argparse
import json
from pathlib import Path
import secrets
import sys

from zenith_integrations.shared.authorization import ServiceAuth
from zenith_integrations.shared.secrets import read_json, write_private_new
from .identity import capture
from .limits import Limits


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init', help='Snapshot the selected checkpoint and create separate private service credentials')
    init.add_argument('--directory', type=Path, required=True)
    serve = sub.add_parser('serve', help='Load the verified model and bind a loopback-only inference service')
    serve.add_argument('--directory', type=Path, required=True)
    serve.add_argument('--port', type=int, default=8781)
    serve.add_argument('--context-tokens', type=int)
    serve.add_argument('--max-output-tokens', type=int)
    serve.add_argument('--deadline-seconds', type=float, default=120)
    serve.add_argument('--queue-size',type=int,default=0,help='Optional waiting requests (0–8); one model generation remains active')
    args = parser.parse_args(argv)
    directory = args.directory.expanduser().absolute()
    try:
        if args.command == 'init':
            from agent.config import Settings
            # Preflight prevents partially replacing an existing service identity.
            if directory.exists() and any(directory.iterdir()):
                raise ValueError('Select a new empty service configuration directory')
            capture(Settings(), directory / 'identity.json')
            services = []
            for name in ['operator', 'hermes', 'openclaw', 'tradingagents']:
                key = directory / (name + '.key')
                write_private_new(key, secrets.token_urlsafe(48) + '\n')
                services.append({'id': name, 'token_file': str(key),
                    'capabilities': ['inference.read', 'inference.generate'], 'models': ['zenith']})
            write_private_new(directory / 'services.json', json.dumps({'services': services}, indent=2) + '\n')
            print('Captured the selected checkpoint and created separate service key files. Existing profiles and artifacts were not changed.')
            return 0
        if not 1024 <= args.port <= 65535:
            raise ValueError('Choose a non-privileged service port')
        if not 0<=args.queue_size<=8:
            raise ValueError('Choose a queue size from 0 to 8')
        from .backend import NativeBackend
        from .server import create_app
        record = read_json(directory / 'identity.json')
        limits = Limits(args.context_tokens or record['context_tokens'],
                        args.max_output_tokens or record['max_new_tokens'], args.deadline_seconds)
        auth = ServiceAuth.from_file(directory / 'services.json')
        backend = NativeBackend(directory / 'identity.json', limits)
        backend.load()
        import uvicorn
        uvicorn.run(create_app(backend, auth,queue_size=args.queue_size), host='127.0.0.1', port=args.port, access_log=False,
                    log_level='info', limit_concurrency=16, backlog=16, timeout_keep_alive=5)
        return 0
    except (ValueError, OSError, ImportError, RuntimeError) as exc:
        # External model/framework errors can contain local secrets or full prompts.
        print('Inference setup failed (' + type(exc).__name__ + '). Verify the private configuration, artifact integrity and optional local dependencies.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
