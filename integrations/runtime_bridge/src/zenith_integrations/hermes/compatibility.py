"""Verify an owner-selected native compatibility build without importing its code."""
import hashlib
import json
from pathlib import Path
from ..shared.secrets import read_json

POLICY='zenith-chat-only-v1'
PIN='d05095663342556788cf2a198bfa7844cc7968ab'
FILES={'agent/agent_init.py','gateway/platforms/api_server.py','gateway/run_turn_runner.py','zenith_chat_compat.py'}


def verify_manifest(path):
    record=read_json(path);definition=record['definition']
    if record.get('schema_version')!=1 or definition.get('policy')!=POLICY or definition.get('source_pin')!=PIN or set(definition.get('files',{}))!=FILES:
        raise ValueError('Unrecognized native compatibility policy')
    digest=hashlib.sha256(json.dumps(definition,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if digest!=record.get('build_sha256'):raise ValueError('Compatibility manifest digest mismatch')
    root=Path(path).absolute().parent
    for file,expected in definition['files'].items():
        target=root/file
        if target.is_symlink() or hashlib.sha256(target.read_bytes()).hexdigest()!=expected:raise ValueError('Native compatibility source was modified')
    return digest
