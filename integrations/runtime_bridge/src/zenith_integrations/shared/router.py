"""One explicitly selected runtime per job; no hidden fallbacks or effect broadcasts."""
import json
import httpx
from fastapi import HTTPException


class NativeInference:
    def __init__(self, config, transport=None):
        self.config, self.transport = config, transport

    async def health(self):
        try:
            async with httpx.AsyncClient(base_url=self.config.inference_origin, transport=self.transport,
                    follow_redirects=False, timeout=3,
                    headers={'Authorization':'Bearer '+self.config.secret(self.config.inference_key_file)}) as client:
                response = await client.get('/readyz')
                return response.status_code == 200 and response.json().get('ready') is True
        except (httpx.HTTPError, ValueError, OSError):
            return False

    async def execute(self, payload):
        # This service generates responses; it never interprets output as commands.
        async with httpx.AsyncClient(base_url=self.config.inference_origin, transport=self.transport,
                follow_redirects=False, timeout=self.config.job_timeout,
                headers={'Authorization':'Bearer '+self.config.secret(self.config.inference_key_file)}) as client:
            async with client.stream('POST', '/v1/chat/completions', json={**payload, 'stream':False}) as response:
                if response.status_code != 200:
                    raise RuntimeError('Native inference did not complete')
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    if len(body) + len(chunk) > 1024*1024:
                        raise RuntimeError('Native inference exceeded its response budget')
                    body.extend(chunk)
                value = json.loads(body)
            if value.get('object') != 'chat.completion' or value.get('model') != 'zenith' or not value.get('choices'):
                raise RuntimeError('Native inference returned an invalid completion')
            return value


class Router:
    def __init__(self, native):
        self.adapters = {'zenith': native}
        self.stopped = False

    def resolve(self, runtime):
        if self.stopped:
            raise HTTPException(503, 'Bridge emergency shutdown is active')
        if runtime not in self.adapters:
            raise HTTPException(503, 'This independently deployed native runtime is not connected')
        return self.adapters[runtime]

    def status(self):
        return [{'runtime':name,'connected':name in self.adapters and not self.stopped,
                 'default_model':'zenith' if name == 'zenith' else None,
                 'live_execution':False} for name in ('zenith','hermes','openclaw','tradingagents')]
