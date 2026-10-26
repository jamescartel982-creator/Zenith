"""Explicit isolated bridge configuration and startup; no native source edits."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import secrets
import sys

from .config import BridgeConfig
from .shared.secrets import read_json, write_private_new


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init')
    init.add_argument('--directory', type=Path, required=True)
    init.add_argument('--zenith-origin', default='http://127.0.0.1:7860')
    init.add_argument('--inference-origin', default='http://127.0.0.1:8781')
    init.add_argument('--inference-key-file', type=Path, required=True)
    init.add_argument('--zenith-access-token-file', type=Path)
    serve = sub.add_parser('serve')
    serve.add_argument('--directory', type=Path, required=True)
    serve.add_argument('--port', type=int, default=8782)
    args = parser.parse_args(argv)
    directory = args.directory.expanduser().absolute()
    try:
        if args.command == 'init':
            if directory.exists() and any(directory.iterdir()):
                raise ValueError('Use a new empty private bridge directory')
            config = BridgeConfig(args.zenith_origin, args.inference_origin, str(args.inference_key_file.expanduser().absolute()),
                str(directory/'control.sqlite3'), str(args.zenith_access_token_file.expanduser().absolute()) if args.zenith_access_token_file else '',
                str(directory/'audit.key'))
            write_private_new(directory/'audit.key',secrets.token_urlsafe(48)+'\n')
            write_private_new(directory/'config.json',json.dumps(asdict(config),indent=2)+'\n')
            print('Created separate bridge configuration. Native settings and memory stores were not changed.')
            return 0
        if not 1024 <= args.port <= 65535:
            raise ValueError('Use a non-privileged private port')
        config = BridgeConfig(**read_json(directory/'config.json'))
        from .gateway import create_app
        import uvicorn
        uvicorn.run(create_app(config),host='127.0.0.1',port=args.port,access_log=False,
                    limit_concurrency=16,backlog=16,timeout_keep_alive=5)
        return 0
    except (ValueError,OSError,ImportError,RuntimeError) as exc:
        print('Bridge setup failed ('+type(exc).__name__+'). Verify private configuration and dependencies.',file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
