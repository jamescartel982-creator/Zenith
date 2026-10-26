"""Explicit independent research-service setup; never edits any original profile."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import secrets
import sys
from zenith_integrations.shared.authorization import ServiceAuth
from zenith_integrations.shared.ledger import Ledger
from zenith_integrations.shared.secrets import read_json,read_private,write_private_new
from .config import TradingConfig


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    init=sub.add_parser('init');init.add_argument('--directory',required=True,type=Path)
    init.add_argument('--source-root',required=True,type=Path);init.add_argument('--inference-key-file',required=True,type=Path)
    init.add_argument('--inference-origin',default='http://127.0.0.1:8781')
    serve=sub.add_parser('serve');serve.add_argument('--directory',required=True,type=Path);serve.add_argument('--port',type=int,default=8783)
    args=parser.parse_args(argv);directory=args.directory.expanduser().absolute()
    try:
        if args.command=='init':
            if directory.exists() and any(directory.iterdir()):raise ValueError('Use a new empty private service directory')
            config=TradingConfig(str(args.source_root.resolve()),str(directory),args.inference_origin,str(args.inference_key_file.expanduser().absolute()))
            config.verify_source()
            if len(read_private(config.inference_key_file,maximum=1024).strip())<32:raise ValueError('Dedicated inference key required')
            write_private_new(directory/'config.json',json.dumps(asdict(config),indent=2)+'\n')
            write_private_new(directory/'bridge.key',secrets.token_urlsafe(48)+'\n')
            write_private_new(directory/'audit.key',secrets.token_urlsafe(48)+'\n')
            write_private_new(directory/'services.json',json.dumps({'services':[{'id':'bridge','token_file':str(directory/'bridge.key'),
                'capabilities':['jobs.submit','jobs.read','jobs.cancel','grants.manage'],'models':[]}]},indent=2)+'\n')
            print('Created a separate native research profile. No live orders, broker keys or original profile changes.')
            return 0
        if not 1024<=args.port<=65535:raise ValueError('Use a non-privileged private service port')
        config=TradingConfig(**read_json(directory/'config.json'));config.verify_source()
        auth=ServiceAuth.from_file(directory/'services.json')
        ledger=Ledger(directory/'control.sqlite3',read_private(directory/'audit.key').strip().encode())
        from .execution import NativeExecutor
        from .server import create_app
        import uvicorn
        executor=NativeExecutor(config);executor.ready()
        uvicorn.run(create_app(executor,auth,ledger),host='127.0.0.1',port=args.port,
                    access_log=False,limit_concurrency=8,backlog=16,timeout_keep_alive=5)
        return 0
    except Exception as exc:
        print('Native research setup failed ('+type(exc).__name__+'). Verify the pinned source, private profile and isolated native dependencies.',file=sys.stderr)
        return 1


if __name__=='__main__':raise SystemExit(main())
