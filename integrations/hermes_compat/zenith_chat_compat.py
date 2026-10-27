"""Approved chat-only policy copied into a separate pinned Hermes build."""
import hashlib
import json
import os
from pathlib import Path
import re
from urllib.parse import urlsplit

POLICY='zenith-chat-only-v1'
SOURCE_PIN='d05095663342556788cf2a198bfa7844cc7968ab'
FILES={'agent/agent_init.py','gateway/platforms/api_server.py','gateway/run_turn_runner.py','zenith_chat_compat.py'}
ROOT=Path(__file__).resolve().parent


def verified_build():
    try:
        manifest=json.loads((ROOT/'zenith-compat-build.json').read_text())
        if manifest.get('schema_version')!=1:return None
        definition=manifest['definition']
        if definition.get('policy')!=POLICY or definition.get('source_pin')!=SOURCE_PIN or set(definition.get('files',{}))!=FILES:return None
        encoded=json.dumps(definition,sort_keys=True,separators=(',',':')).encode()
        if hashlib.sha256(encoded).hexdigest()!=manifest['build_sha256']:return None
        for path,digest in definition['files'].items():
            if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=digest:return None
        return manifest
    except (OSError,ValueError,KeyError,TypeError):return None


def selected_window(model, provider, platform, base_url, window, enabled_tools, tools):
    if os.environ.get('ZENITH_HERMES_CHAT_ONLY')!='1':return False
    profile=os.environ.get('ZENITH_HERMES_PROFILE_ID','')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',profile):return False
    if model!='zenith' or provider!='custom' or platform!='api_server':return False
    if enabled_tools!=[] or tools!=[] or type(window) is not int or not 4000<=window<=32768:return False
    try:
        url=urlsplit(base_url)
        if url.scheme not in {'http','https'} or url.hostname not in {'127.0.0.1','localhost','::1'} or url.username or url.password or url.query or url.fragment or url.path.rstrip('/')!='/v1':return False
    except (ValueError,TypeError):return False
    return verified_build() is not None


def allow_small_context(agent, window):
    # A constructor must satisfy its actual tool surface and exact configured
    # window, regardless of what the listener advertised before admission.
    if getattr(agent,'_config_context_length',None)!=window:return False
    return selected_window(getattr(agent,'model',None),getattr(agent,'provider',None),getattr(agent,'platform',None),getattr(agent,'base_url',None),window,getattr(agent,'enabled_toolsets',None),getattr(agent,'tools',None))


def record_served_runtime(agent, result, captured):
    """Record actual post-turn agent attributes; never echo requested routing."""
    if not isinstance(result,dict) or not isinstance(captured,dict):return
    window=getattr(getattr(agent,'context_compressor',None),'context_length',None)
    if allow_small_context(agent,window):
        captured.setdefault('usage',{})['runtime']={'provider':agent.provider,'model':agent.model}


def capability_field():
    if os.environ.get('ZENITH_HERMES_CHAT_ONLY')!='1':return {}
    try:
        from hermes_cli.config import load_config_readonly
        config=load_config_readonly();model=config.get('model',{});tools=config.get('platform_toolsets',{}).get('api_server')
        window=model.get('context_length')
        if not selected_window(model.get('default'),model.get('provider'),'api_server',model.get('base_url'),window,tools,[]):return {}
        build=verified_build()
        return {'zenith_compatibility':{'policy':POLICY,'source_pin':SOURCE_PIN,'build_sha256':build['build_sha256'],
            'enabled':True,'profile_id':os.environ['ZENITH_HERMES_PROFILE_ID'],'context_tokens':window,'model':'zenith','provider':'custom','execution_tools':False}}
    except (ImportError,OSError,ValueError,TypeError,KeyError):return {}
