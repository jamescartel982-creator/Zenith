"""Supervised task pilot: native chat and explicit, authorized diagnostic plans.

This is not an autonomous model-tool loop. Optional isolated Python uses its
separate default-off container policy; no host shell, plugin, browser or channel
is executable through this runtime.
"""
import json
import logging
import os
from threading import Event, Lock, Thread
import time
from urllib.parse import urlparse
from uuid import UUID, uuid4

from .approvals import Approvals, action_hash
from .audit_chain import AuditChain
from .event_bus import EventBus
from .permissions import ActorContext, Permissions
from .platform_migrations import migrate
from .platform_repository import canonical
from .redaction import Redactor
from .task_store import LeaseLost, TaskStore
from .tool_protocol import parse_plan
from .tool_registry import ToolRegistry

logger = logging.getLogger('zenith')


class PlatformRuntime:
    def __init__(self, agent, config):
        if not config.enabled:
            raise ValueError('Platform is disabled')
        self.agent, self.store, self.config = agent, agent.store, config
        migrate(self.store)
        self.permissions = Permissions(self.store, agent.personal, agent.execution, config)
        self.audit = AuditChain(self.store)
        self.tasks = TaskStore(self.store, self.permissions, self.audit, config)
        self.events = EventBus(self.store, self.permissions)
        self.approvals = Approvals(self.tasks, self.permissions, self.audit)
        self.tools = ToolRegistry(self.permissions, agent.execution)
        self.redactor = Redactor([agent.settings.api_token] + [os.getenv(name, '') for name in (
            'OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'HF_TOKEN', 'HUGGING_FACE_HUB_TOKEN')])
        self._stop, self._wake = Event(), Event()
        self._lifecycle = Lock()
        self._run_lock = Lock()
        self._thread, self._active_cancel = None, None
        self.worker_id = str(uuid4())

    def available(self):
        settings = self.agent.settings
        local = settings.provider in {'huggingface', 'tiny', 'localserver'}
        if settings.provider == 'ollama':
            endpoint = urlparse(settings.ollama_url)
            local = endpoint.scheme in {'http', 'https'} and endpoint.hostname in {'localhost', '127.0.0.1', '::1'} and not endpoint.username and not endpoint.password
        return local

    def status(self):
        from .sandbox import SandboxPolicy
        sandbox = SandboxPolicy.from_env()
        return {'enabled': True, 'runtime_enabled': self.config.runtime_enabled,
                'tools_enabled': self.config.tools_enabled, 'memory_enabled': self.config.memory_enabled,
                'worker_running': bool(self._thread and self._thread.is_alive() and not self._stop.is_set()),
                'native_chat_available': self.available(), 'model': self.agent.settings.model_name,
                'task_modes': (['chat'] if self.config.runtime_enabled and self.available() else []) +
                              (['diagnostics'] if self.config.runtime_enabled and self.config.tools_enabled else []),
                'autonomous_tool_generation': False, 'project_retrieval': 'unavailable',
                'sandbox': 'configured-not-probed' if sandbox.enabled else 'disabled', 'plugins': 'unavailable', 'channels': 'unavailable',
                'browser_automation': 'unavailable', 'computer_automation': 'unavailable',
                'default_model_preserved': True}

    def clean_input(self, value):
        encoded = canonical(value, 32000)
        def check(part):
            if isinstance(part, str):
                self.redactor.require_clean(part)
            elif isinstance(part, list):
                for child in part: check(child)
            elif isinstance(part, dict):
                for key, child in part.items():
                    self.redactor.require_clean(key); check(child)
        check(value)
        from .owner_mfa import contains_enrollment_secret
        if contains_enrollment_secret(self.store, encoded):
            raise ValueError('Keep authenticator material out of persistent tasks')

    def filter_output(self, value):
        if isinstance(value, str):
            from .owner_mfa import contains_enrollment_secret
            if contains_enrollment_secret(self.store, value):
                return '[REDACTED AUTHENTICATOR MATERIAL]'
            return self.redactor.text(value)
        if isinstance(value, list):
            return [self.filter_output(v) for v in value]
        if isinstance(value, dict):
            return {self.redactor.text(str(k)): self.filter_output(v) for k, v in value.items()}
        return value

    def submit(self, actor, kind, payload, conversation_id=None):
        if not self.config.runtime_enabled or self._stop.is_set():
            raise PermissionError('Platform task runtime is disabled or draining')
        self.permissions.validate(actor)
        self.clean_input(payload)
        if kind == 'chat':
            if not self.available():
                raise ValueError('The supervised chat pilot needs an explicitly configured local provider')
            if set(payload) != {'message'} or not isinstance(payload['message'], str) or not 1 <= len(payload['message'].strip()) <= 12000:
                raise ValueError('Chat tasks need bounded message text')
            conversation_id = str(UUID(conversation_id)) if conversation_id else str(uuid4())
            task = self.tasks.create(actor, kind, payload, conversation_id)
        elif kind == 'diagnostics':
            if set(payload) != {'steps'}:
                raise ValueError('Diagnostic tasks need explicit steps')
            calls = parse_plan(payload['steps'], self.config.max_steps)
            for call in calls:
                self.tools.prepare(actor, call)
            task = self.tasks.create(actor, kind, {'steps': [{'tool': c.tool, 'arguments': c.arguments} for c in calls]})
        else:
            raise ValueError('Unsupported task kind')
        self._wake.set()
        return task

    def start(self):
        with self._lifecycle:
            if not self.config.runtime_enabled or (self._thread and self._thread.is_alive()):
                return
            self._stop.clear()
            self._thread = Thread(target=self._loop, name='zenith-platform', daemon=True)
            self._thread.start()

    def stop(self, timeout=5):
        self._stop.set(); self._wake.set()
        if self._active_cancel:
            self._active_cancel.set()
        if self._thread:
            self._thread.join(timeout=timeout)
        stopped = not self._thread or not self._thread.is_alive()
        if not stopped:
            logger.warning('Platform worker is still draining; no host fallback or replacement worker was started')
        return stopped

    def _loop(self):
        while not self._stop.is_set():
            try:
                if self.run_once():
                    continue
            except Exception:
                # Exception strings can contain transport credentials or model data.
                logger.warning('Platform task service paused after an internal failure')
                self._stop.set()
                return
            self._wake.wait(0.25); self._wake.clear()

    def _guard(self, task_id, actor, cancel):
        if cancel.is_set() or self._stop.is_set():
            raise LeaseLost('Task cancellation requested')
        with self.store.connect() as db:
            self.tasks.fenced(db, task_id, self.worker_id)
            self.permissions.validate(actor, db)

    def run_once(self):
        if not self._run_lock.acquire(blocking=False):
            return False
        try:
            return self._run_once()
        finally:
            self._run_lock.release()

    def _run_once(self):
        if not self.config.runtime_enabled or self._stop.is_set():
            return False
        task = self.tasks.claim(self.worker_id)
        if task is None:
            return False
        actor = ActorContext(task['user_id'], task['session_hash'], task['auth_revision'])
        cancel, done = Event(), Event()
        self._active_cancel = cancel
        stream_holder = []
        def heartbeat():
            while not done.wait(0.25):
                try:
                    if self._stop.is_set() or not self.tasks.heartbeat(task['id'], self.worker_id):
                        cancel.set()
                    self.permissions.validate(actor)
                except Exception:
                    cancel.set()
                if cancel.is_set():
                    for stream in stream_holder:
                        stream.cancel.set()
        pulse = Thread(target=heartbeat, name='zenith-platform-lease', daemon=True)
        pulse.start()
        try:
            self._guard(task['id'], actor, cancel)
            payload = json.loads(task['payload'])
            if task['kind'] == 'chat':
                def privacy(value):
                    self._guard(task['id'], actor, cancel)
                    return self.filter_output(value)
                stream = self.agent.stream_answer(payload['message'], task['conversation_id'], actor.user_id,
                    privacy_filter=privacy)
                stream_holder.append(stream)
                result = None
                try:
                    for event in stream:
                        self._guard(task['id'], actor, cancel)
                        if event['type'] == 'result':
                            result = event['result']
                finally:
                    stream.close()
                if result is None:
                    raise LeaseLost('Native generation did not complete')
            else:
                result = self._diagnostics(task, actor, payload, cancel)
                if result is None:  # Persisted approval wait; worker lease was released.
                    return True
            self._guard(task['id'], actor, cancel)
            self.tasks.finish(task['id'], self.worker_id, 'completed', self.filter_output(result))
        except Exception as exc:
            with self.store.connect() as db:
                uncertain = db.execute("SELECT 1 FROM platform_receipts WHERE task_id=? AND status='started'", (task['id'],)).fetchone()
            status = 'needs_reconciliation' if uncertain else 'failed'
            reason = 'effect-outcome-unknown' if uncertain else 'authorization-denied' if isinstance(exc, PermissionError) else 'task-interrupted' if isinstance(exc, LeaseLost) else 'task-failed'
            try:
                self.tasks.finish(task['id'], self.worker_id, status, error=reason)
            except LeaseLost:
                pass  # An expired worker cannot overwrite the recovery decision.
        finally:
            done.set(); pulse.join(timeout=2); self._active_cancel = None
        return True

    def _diagnostics(self, task, actor, payload, cancel):
        from .event_bus import append_event
        results = []
        for step, call in enumerate(parse_plan(payload['steps'], self.config.max_steps)):
            self._guard(task['id'], actor, cancel)
            approval_required = self.tools.prepare(actor, call)
            with self.store.connect() as db:
                receipt = db.execute('SELECT * FROM platform_receipts WHERE task_id=? AND step=?', (task['id'], step)).fetchone()
            if receipt:
                if receipt['tool'] != call.tool or receipt['args_hash'] != action_hash(call.tool, call.arguments) or receipt['status'] != 'completed':
                    raise LeaseLost('Uncertain or changed tool receipt needs review')
                results.append(json.loads(receipt['result']))
                continue
            if approval_required and not self.approvals.prepare(actor, task['id'], self.worker_id, step, call.tool, call.arguments):
                return None
            with self.store.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                self.tasks.fenced(db, task['id'], self.worker_id)
                self.permissions.validate(actor, db)
                self.tools.prepare(actor, call)
                if approval_required:
                    self.approvals.consume(db, actor, task['id'], step, call.tool, call.arguments)
                digest = action_hash(call.tool, call.arguments)
                db.execute('INSERT INTO platform_receipts VALUES (?,?,?,?,?,?,?)',
                           (task['id'], step, call.tool, digest, 'started', None, time.time()))
                self.audit.append('tool-intent', {'task_id': task['id'], 'user_id': actor.user_id,
                    'tool': call.tool, 'step': step, 'args_hash': digest}, db)
            self._guard(task['id'], actor, cancel)
            value = self.filter_output(self.tools.execute(actor, call, guard=lambda:self._guard(task['id'], actor, cancel)))
            encoded = canonical(value, 16000)
            self._guard(task['id'], actor, cancel)
            with self.store.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                self.tasks.fenced(db, task['id'], self.worker_id)
                self.permissions.validate(actor, db)
                db.execute("UPDATE platform_receipts SET status='completed',result=? WHERE task_id=? AND step=?", (encoded, task['id'], step))
                append_event(db, task['id'], actor.user_id, 'tool-completed', {'step': step, 'tool': call.tool})
                self.audit.append('tool-completed', {'task_id': task['id'], 'user_id': actor.user_id, 'tool': call.tool, 'step': step}, db)
            results.append(value)
        return {'results': results, 'model_calls': 0}
