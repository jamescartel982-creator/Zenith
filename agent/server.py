"""Local-first chat with optional password accounts and private memories."""
import argparse
import hmac
import logging
import time
from threading import Lock
from pathlib import Path
from typing import Literal
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse,StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field

from .config import Settings
from .core import Agent, BusyError
from .skill_access import SkillAccessDenied, ConversationAccessDenied
from .registry import Catalog
from .discovery import Discovery, DiscoveryError
from . import __version__

WEB = Path(__file__).parent / 'web'
logger = logging.getLogger('zenith')


class ManagedStreamingResponse(StreamingResponse):
    """ASGI 2.4 send failures do not otherwise guarantee iterator finalization."""
    def __init__(self,*args,close_stream,**kwargs):
        super().__init__(*args,**kwargs);self.close_stream=close_stream

    async def __call__(self,scope,receive,send):
        import anyio
        try:await super().__call__(scope,receive,send)
        finally:
            with anyio.CancelScope(shield=True):
                try:
                    close=getattr(self.body_iterator,'aclose',None)
                    if close:await close()
                finally:await anyio.to_thread.run_sync(self.close_stream)


class ChatRequest(BaseModel):
    session_id: UUID
    message: str = Field(min_length=1, max_length=12000)
    response_mode: Literal['fast', 'thorough'] | None = None
    skill: str | None = Field(default=None, max_length=40)
    reply_style: Literal['auto','brief','full'] | None = None


class ReviewRequest(BaseModel):
    session_id: UUID
    turn_id: UUID
    rating: Literal['good', 'bad']
    approved: bool = False
    correction: str | None = Field(default=None, max_length=24000)


class SkillCommandRequest(BaseModel):
    session_id: UUID
    command: str = Field(min_length=1, max_length=200)


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=40)
    password: str = Field(min_length=1, max_length=256)


class RegisterRequest(LoginRequest):
    display_name: str = Field(min_length=1, max_length=60)


class MemoryRequest(BaseModel):
    content: str = Field(min_length=1, max_length=500)


class AdminUnlockRequest(BaseModel):
    code: str = Field(min_length=1, max_length=128)
    otp: str = Field(default='',max_length=6)


class MFASetupRequest(BaseModel):
    password: str = Field(min_length=1,max_length=256)


class MFAConfirmRequest(BaseModel):
    otp: str = Field(min_length=6,max_length=6)


class CapabilityGrantRequest(BaseModel):
    capability: str = Field(max_length=40)
    scope: dict
    seconds: int = Field(default=300,ge=1,le=900)


class ExecutionRequest(BaseModel):
    capability: str = Field(max_length=40)
    arguments: dict


class ExecutionPlanRequest(BaseModel):
    steps: list[dict] = Field(min_length=1,max_length=8)


class AdminModeRequest(BaseModel):
    enabled: bool


class AdminToolRequest(BaseModel):
    tool: str = Field(max_length=40)
    text: str = Field(max_length=12000)


class HumanReviewRequest(BaseModel):
    session_id: UUID
    turn_id: UUID
    reason: str = Field(default='Please review this answer.',min_length=1,max_length=500)


class HumanResolution(BaseModel):
    resolution: str = Field(min_length=1,max_length=4000)


def create_app(settings=None, agent=None, catalog=None):
    settings = settings or Settings()
    agent = agent or Agent(settings)
    app = FastAPI(title='Zenith', version=__version__, docs_url=None, redoc_url=None)
    from .http_security import RequestSecurityMiddleware
    app.add_middleware(RequestSecurityMiddleware, allowed_hosts=settings.allowed_hosts)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, exc):
        from fastapi.responses import JSONResponse
        # Framework defaults echo rejected inputs, including passwords and OTPs.
        errors = [{key: error[key] for key in ('type', 'loc', 'msg') if key in error}
                  for error in exc.errors()[:24]]
        return JSONResponse({'detail': errors}, status_code=422)
    app.state.agent = agent
    app.state.catalog = catalog
    app.state.discovery = Discovery()
    attempts = {}
    attempt_lock = Lock()

    def get_catalog():
        if app.state.catalog is None:
            app.state.catalog = Catalog()
        return app.state.catalog

    def authenticate(authorization: str = Header(default='')):
        if settings.api_token and not hmac.compare_digest(
            authorization.encode(), f'Bearer {settings.api_token}'.encode()
        ):
            raise HTTPException(401, 'Enter the server access token to continue', headers={'WWW-Authenticate': 'Bearer'})

    def current_user(request: Request):
        return agent.personal.user_for_token(request.cookies.get('zenith_login', ''))

    def signed_in(user=Depends(current_user)):
        if user is None:
            raise HTTPException(401, 'Sign in to use your private memories')
        return user

    from .productivity_gateway import install_productivity
    install_productivity(app, agent, authenticate, signed_in)

    def administrator(request: Request, user=Depends(signed_in)):
        state = agent.admin.status(user['id'], request.cookies.get('zenith_login',''))
        if not state['eligible'] or not state['elevated']:
            raise HTTPException(403, 'Unlock administrator access for your owner account first')
        return user

    def guard_conversation(session_id, user, create=False):
        if not agent.personal.conversation_access(str(session_id), user['id'] if user else '', create):
            raise HTTPException(404, 'Conversation not found')

    def limit_login(request):
        key = request.client.host if request.client else 'local'
        now = time.monotonic()
        with attempt_lock:
            expired = [key for key, (started, _) in attempts.items() if now - started > 60]
            for old in expired:
                attempts.pop(old, None)
            started, count = attempts.get(key, (now, 0))
            if count >= 8 or (key not in attempts and len(attempts) >= 1024):
                raise HTTPException(429, 'Too many sign-in attempts. Wait a minute and retry.', headers={'Retry-After': '60'})
            attempts[key] = (started, count + 1)

    def login_response(user, request, response):
        old = request.cookies.get('zenith_login', '')
        if old:
            agent.personal.logout(old)
        token = agent.personal.issue_session(user['id'])
        response.set_cookie('zenith_login', token, max_age=7 * 86400, httponly=True,
                            secure=request.url.scheme == 'https', samesite='strict', path='/')
        return {'user': user, 'greeting': 'Welcome back, ' + user['display_name'] + '.'}

    @app.middleware('http')
    async def security_headers(request, call_next):
        origin = request.headers.get('origin')
        if request.method in {'POST', 'PUT', 'PATCH', 'DELETE'} and origin and origin != str(request.base_url).rstrip('/'):
            from fastapi.responses import JSONResponse
            return JSONResponse({'detail': 'Cross-site changes are not allowed'}, status_code=403)
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'"
        )
        response.headers['Cache-Control'] = 'no-store'
        return response

    @app.get('/')
    def index():
        return FileResponse(WEB / 'index.html')

    @app.get('/healthz')
    def health():
        info = agent.team_info()
        loaded = info.get('model_loaded', False) if settings.provider == 'ensemble' else getattr(agent.provider, 'model', None) is not None
        return {'status': 'ok', 'version':__version__, 'provider': settings.provider, 'model': settings.model_name, 'display_name': settings.display_name,
                'configured_members': len(info['members']), 'model_loaded': loaded,
                'authentication_required': bool(settings.api_token)}

    @app.get('/api/account', dependencies=[Depends(authenticate)])
    def account(user=Depends(current_user)):
        return {'user': user, 'greeting': ('Welcome back, ' + user['display_name'] + '.') if user else 'Welcome to Zenith.'}

    @app.post('/api/account/register', dependencies=[Depends(authenticate)])
    def register(body: RegisterRequest, request: Request, response: Response):
        limit_login(request)
        try:
            user = agent.personal.register(body.username, body.display_name, body.password)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        return login_response(user, request, response)

    @app.post('/api/account/login', dependencies=[Depends(authenticate)])
    def login(body: LoginRequest, request: Request, response: Response):
        limit_login(request)
        user = agent.personal.login(body.username, body.password)
        if user is None:
            raise HTTPException(401, 'Username or password was not accepted')
        return login_response(user, request, response)

    @app.post('/api/account/logout', dependencies=[Depends(authenticate)])
    def logout(request: Request, response: Response):
        agent.personal.logout(request.cookies.get('zenith_login', ''))
        response.delete_cookie('zenith_login', path='/')
        return {'signed_out': True}

    @app.get('/api/conversations', dependencies=[Depends(authenticate)])
    def conversations(user=Depends(signed_in)):
        return {'conversations': agent.personal.conversations(user['id'])}

    @app.get('/api/memories', dependencies=[Depends(authenticate)])
    def memories(user=Depends(signed_in)):
        return {'memories': agent.personal.memories(user['id'])}

    @app.post('/api/memories', dependencies=[Depends(authenticate)])
    def remember(body: MemoryRequest, user=Depends(signed_in)):
        try:
            identifier = agent.personal.remember(user['id'], body.content)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        return {'id': identifier, 'saved': True}

    @app.delete('/api/memories/{memory_id}', dependencies=[Depends(authenticate)])
    def forget(memory_id: UUID, user=Depends(signed_in)):
        if not agent.personal.forget(user['id'], str(memory_id)):
            raise HTTPException(404, 'Memory not found')
        return {'deleted': True}

    @app.delete('/api/memories', dependencies=[Depends(authenticate)])
    def forget_all(user=Depends(signed_in)):
        return {'deleted': agent.personal.forget(user['id'])}

    @app.get('/api/conversations/{session_id}/summary', dependencies=[Depends(authenticate)])
    def get_summary(session_id: UUID,user=Depends(signed_in)):
        from .summaries import current
        try:return {'summary':current(agent.store,agent.personal,user['id'],str(session_id))}
        except LookupError as exc:raise HTTPException(404,'Conversation not found') from exc

    @app.post('/api/conversations/{session_id}/summary', dependencies=[Depends(authenticate)])
    def save_summary(session_id: UUID,user=Depends(signed_in)):
        from .summaries import summarize
        try:return {'summary':summarize(agent,user['id'],str(session_id)),'weight_update':False}
        except LookupError as exc:raise HTTPException(404,'Conversation not found') from exc
        except BusyError as exc:raise HTTPException(429,str(exc)) from exc
        except ValueError as exc:raise HTTPException(400,str(exc)) from exc

    @app.delete('/api/conversations/{session_id}/summary', dependencies=[Depends(authenticate)])
    def delete_summary(session_id: UUID,user=Depends(signed_in)):
        guard_conversation(session_id,user)
        from .summaries import initialize
        initialize(agent.store)
        with agent.store.connect() as db:db.execute('DELETE FROM conversation_summaries WHERE session_id=? AND user_id=?',(str(session_id),user['id']))
        return {'deleted':True}

    @app.get('/api/model-packs', dependencies=[Depends(authenticate)])
    def model_packs():
        from .packs import summaries
        return {'packs': summaries()}

    @app.get('/api/skills', dependencies=[Depends(authenticate)])
    def skills(request: Request, user=Depends(current_user)):
        from .skills import skills_library
        allowed = agent.skills.is_admin(user['id'] if user else None, request.cookies.get('zenith_login', ''))
        return {**skills_library(include_admin=allowed), 'extended_catalog':agent.skills.catalog.status(allowed), 'kind':'instruction-profiles', 'default_response_mode':settings.response_mode,'default_reply_style':settings.reply_style}

    @app.get('/api/skills/search', dependencies=[Depends(authenticate)])
    def search_skills(request: Request, query: str=Query(default='',max_length=200), category: Literal['general','security']|None=None,
                      after: str=Query(default='',max_length=40), limit: int=Query(default=25,ge=1,le=100), user=Depends(signed_in)):
        allowed=agent.skills.is_admin(user['id'],request.cookies.get('zenith_login',''))
        return agent.skills.catalog.search(query,category,after,limit,allowed)

    @app.get('/api/skills/profile/{identifier}', dependencies=[Depends(authenticate)])
    def skill_profile(identifier: str,request: Request,user=Depends(signed_in)):
        try:return agent.skills.require(identifier,user['id'],request.cookies.get('zenith_login',''))
        except SkillAccessDenied as exc:raise HTTPException(403,str(exc)) from exc
        except ValueError as exc:raise HTTPException(404,'Unknown skill') from exc

    @app.get('/api/skills/current', dependencies=[Depends(authenticate)])
    def current_skill(request: Request, session_id: UUID, user=Depends(current_user)):
        guard_conversation(session_id, user)
        return agent.skills.command(str(session_id), '/skill status', user['id'] if user else None,
                                    request.cookies.get('zenith_login', ''))

    @app.post('/api/skills/command', dependencies=[Depends(authenticate)])
    def skill_command(body: SkillCommandRequest, request: Request, user=Depends(current_user)):
        try:
            return agent.skills.command(str(body.session_id), body.command, user['id'] if user else None,
                                        request.cookies.get('zenith_login', ''))
        except SkillAccessDenied as exc:
            raise HTTPException(403, str(exc)) from exc
        except ConversationAccessDenied as exc:
            raise HTTPException(404, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.get('/api/system', dependencies=[Depends(authenticate)])
    def system_status(user=Depends(current_user)):
        from .monitoring import system_snapshot
        return system_snapshot(agent,user['id'] if user else None)

    @app.get('/api/metrics', dependencies=[Depends(authenticate)])
    def my_metrics(user=Depends(signed_in)):
        return agent.monitor.summary(user['id'])

    @app.get('/api/admin/metrics', dependencies=[Depends(authenticate)])
    def server_metrics(user=Depends(administrator)):
        return agent.monitor.summary(all_users=True)

    @app.get('/api/admin/status', dependencies=[Depends(authenticate)])
    def admin_status(request: Request, user=Depends(signed_in)):
        return agent.admin.status(user['id'],request.cookies.get('zenith_login',''))

    @app.post('/api/admin/unlock', dependencies=[Depends(authenticate)])
    def admin_unlock(body: AdminUnlockRequest, request: Request, user=Depends(signed_in)):
        limit_login(request)
        token=request.cookies.get('zenith_login','')
        if not agent.admin.unlock(user['id'],token,body.code.strip(),body.otp):
            raise HTTPException(403,'Owner account or secret code was not accepted')
        return agent.admin.status(user['id'],token)

    @app.post('/api/admin/lock', dependencies=[Depends(authenticate)])
    def admin_lock(request: Request, user=Depends(signed_in)):
        agent.admin.lock(request.cookies.get('zenith_login',''))
        return {'locked':True}

    @app.post('/api/admin/mode', dependencies=[Depends(authenticate)])
    def admin_mode(body: AdminModeRequest, request: Request, user=Depends(administrator)):
        try:return agent.admin.mode(user['id'],request.cookies.get('zenith_login',''),body.enabled)
        except PermissionError as exc:raise HTTPException(403,str(exc)) from exc

    @app.get('/api/admin/tools', dependencies=[Depends(authenticate)])
    def admin_tools(user=Depends(administrator)):
        from .tools import TOOLS
        return {'tools':[{'id':key,'description':value} for key,value in TOOLS.items()]}

    @app.post('/api/admin/tools', dependencies=[Depends(authenticate)])
    def admin_run_tool(body: AdminToolRequest, request: Request, user=Depends(administrator)):
        if agent.execution.status(user['id'],request.cookies.get('zenith_login',''))['stopped']:
            raise HTTPException(403,'Emergency shutdown is active')
        if not agent.admin.status(user['id'],request.cookies.get('zenith_login',''))['devil_mode']:
            raise HTTPException(403,'Enable the administrator security workspace first')
        from .tools import run_tool
        try:
            if body.tool in {'code-audit','inspect-url'}:
                result=agent.execution.execute(user['id'],request.cookies.get('zenith_login',''),body.tool,{'text':body.text})
            else:
                result=run_tool(body.tool,body.text)
        except PermissionError as exc: raise HTTPException(403,str(exc)) from exc
        except ValueError as exc: raise HTTPException(400,str(exc)) from exc
        agent.admin.record_tool(user['id'],body.tool)
        return {'result':result,'executed_by':'bounded-local-tool','model_execution':False}

    @app.post('/api/admin/mfa/setup', dependencies=[Depends(authenticate)])
    def mfa_setup(body: MFASetupRequest,request: Request,user=Depends(administrator)):
        limit_login(request)
        if agent.personal.login(user['username'],body.password) is None:
            raise HTTPException(403,'Reauthentication failed')
        try:return agent.admin.mfa.begin(user['id'],user['username'])
        except ValueError as exc:raise HTTPException(400,str(exc)) from exc

    @app.post('/api/admin/mfa/confirm', dependencies=[Depends(authenticate)])
    def mfa_confirm(body: MFAConfirmRequest,request: Request,user=Depends(administrator)):
        limit_login(request)
        token=request.cookies.get('zenith_login','')
        if not agent.admin.mfa.verify(user['id'],token,body.otp,enroll=True):
            raise HTTPException(403,'Authenticator code was not accepted')
        return agent.admin.status(user['id'],token)

    @app.get('/api/admin/execution', dependencies=[Depends(authenticate)])
    def execution_status(request: Request,user=Depends(administrator)):
        return agent.execution.status(user['id'],request.cookies.get('zenith_login',''))

    @app.post('/api/admin/execution/grant', dependencies=[Depends(authenticate)])
    def execution_grant(body: CapabilityGrantRequest,request: Request,user=Depends(administrator)):
        try:return agent.execution.grant(user['id'],request.cookies.get('zenith_login',''),body.capability,body.scope,body.seconds)
        except PermissionError as exc:raise HTTPException(403,str(exc)) from exc
        except ValueError as exc:raise HTTPException(400,str(exc)) from exc

    @app.delete('/api/admin/execution/grants', dependencies=[Depends(authenticate)])
    def execution_revoke(request: Request,user=Depends(administrator)):
        agent.execution.revoke(user['id'],request.cookies.get('zenith_login',''))
        return {'revoked':True}

    @app.post('/api/admin/execution/stop', dependencies=[Depends(authenticate)])
    def execution_stop(request: Request,user=Depends(administrator)):
        return agent.execution.emergency(user['id'],request.cookies.get('zenith_login',''))

    @app.post('/api/admin/execution/resume', dependencies=[Depends(authenticate)])
    def execution_resume(request: Request,user=Depends(administrator)):
        try:return agent.execution.emergency(user['id'],request.cookies.get('zenith_login',''),False)
        except PermissionError as exc:raise HTTPException(403,str(exc)) from exc

    @app.post('/api/admin/execution/run', dependencies=[Depends(authenticate)])
    def execution_run(body: ExecutionRequest,request: Request,user=Depends(administrator)):
        try:return {'result':agent.execution.execute(user['id'],request.cookies.get('zenith_login',''),body.capability,body.arguments)}
        except PermissionError as exc:raise HTTPException(403,str(exc)) from exc
        except ValueError as exc:raise HTTPException(400,str(exc)) from exc
        except OSError as exc:raise HTTPException(502,'Scoped diagnostic failed; check the authorized target and local network') from exc

    @app.post('/api/admin/execution/plan', dependencies=[Depends(authenticate)])
    def execution_plan(body: ExecutionPlanRequest,request: Request,user=Depends(administrator)):
        try:return agent.execution.run_plan(user['id'],request.cookies.get('zenith_login',''),body.steps)
        except PermissionError as exc:raise HTTPException(403,str(exc)) from exc
        except ValueError as exc:raise HTTPException(400,str(exc)) from exc
        except OSError as exc:raise HTTPException(502,'A scoped diagnostic failed; plan stopped') from exc

    @app.get('/api/admin/execution/history', dependencies=[Depends(authenticate)])
    def execution_history(user=Depends(administrator)):
        with agent.store.connect() as db:
            return {'events':[dict(r) for r in db.execute('SELECT * FROM execution_audit WHERE user_id=? ORDER BY id DESC LIMIT 100',(user['id'],))],
                    'tasks':[dict(r) for r in db.execute('SELECT id,created,status,steps,results FROM agent_tasks WHERE user_id=? ORDER BY created DESC LIMIT 50',(user['id'],))]}

    @app.post('/api/review-requests', dependencies=[Depends(authenticate)])
    def request_human_review(body: HumanReviewRequest,user=Depends(signed_in)):
        guard_conversation(body.session_id,user)
        from .assurance import normalize_input
        try:identifier=agent.personal.request_human_review(user['id'],str(body.session_id),str(body.turn_id),normalize_input(body.reason))
        except ValueError as exc:raise HTTPException(400,str(exc)) from exc
        return {'id':identifier,'status':'open','notification_sent':False,'shared_with':'local-server-administrator'}

    @app.get('/api/review-requests', dependencies=[Depends(authenticate)])
    def my_review_requests(user=Depends(signed_in)):
        return {'requests':agent.personal.review_requests(user['id'])}

    @app.get('/api/admin/reviews', dependencies=[Depends(authenticate)])
    def admin_reviews(user=Depends(administrator)):
        return {'requests':agent.personal.review_requests()}

    @app.post('/api/admin/reviews/{review_id}', dependencies=[Depends(authenticate)])
    def resolve_review(review_id:UUID,body:HumanResolution,user=Depends(administrator)):
        from .assurance import normalize_input
        try:
            resolution=normalize_input(body.resolution)
            resolved=agent.personal.resolve_review(str(review_id),resolution)
        except ValueError as exc:raise HTTPException(400,str(exc)) from exc
        if not resolved:raise HTTPException(404,'Review request not found')
        agent.admin.record_tool(user['id'],'resolve-review')
        return {'resolved':True}

    @app.get('/api/team', dependencies=[Depends(authenticate)])
    def team():
        return agent.team_info()

    @app.get('/api/catalog', dependencies=[Depends(authenticate)])
    def catalog_search(kind: Literal['model', 'dataset'] | None = None,
                       source: Literal['huggingface', 'github'] | None = None,
                       q: str = Query(default='', max_length=200),
                       page: int = Query(default=1, ge=1),
                       page_size: int = Query(default=20, ge=1, le=100)):
        configured = {member['model'] for member in agent.team_info()['members'] if member['provider'] == 'huggingface'}
        return get_catalog().search(kind, source, q, page, page_size, configured)

    @app.get('/api/discovery', dependencies=[Depends(authenticate)])
    def discover(source: Literal['huggingface', 'github'] = 'huggingface',
                 kind: Literal['model', 'dataset'] = 'model',
                 q: str = Query(default='', max_length=200),
                 page: int = Query(default=1, ge=1, le=1000000),
                 page_size: int = Query(default=20, ge=1, le=50),
                 cursor: str = Query(default='', max_length=4096)):
        try:
            return app.state.discovery.search(source, kind, q, page, page_size, cursor)
        except DiscoveryError as exc:
            raise HTTPException(502, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.get('/api/knowledge', dependencies=[Depends(authenticate)])
    def knowledge_status():
        return agent.store.knowledge_stats()

    def prepare_chat(body, request, user):
        user_id = user['id'] if user else None
        token = request.cookies.get('zenith_login', '')
        skill = body.skill if body.skill is not None else agent.skills.active(str(body.session_id), user_id, token)
        agent.skills.require(skill, user_id, token)
        guard_conversation(body.session_id, user, create=True)
        return {'skill': skill, 'login_token': token}

    @app.post('/api/chat', dependencies=[Depends(authenticate)])
    def chat(body: ChatRequest, request: Request, user=Depends(current_user)):
        try:
            arguments = prepare_chat(body, request, user)
            return agent.answer(body.message, str(body.session_id), user_id=user['id'] if user else None,
                                response_mode=body.response_mode,reply_style=body.reply_style,**arguments)
        except SkillAccessDenied as exc:
            raise HTTPException(403, str(exc)) from exc
        except ConversationAccessDenied as exc:
            raise HTTPException(404, str(exc)) from exc
        except BusyError as exc:
            raise HTTPException(429, str(exc), headers={'Retry-After': '5'}) from exc
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception('Model generation failed')
            raise HTTPException(503, 'Model unavailable. Check server logs, model download, and provider settings.') from exc

    @app.post('/api/chat/stream', dependencies=[Depends(authenticate)])
    def stream_chat(body:ChatRequest,request:Request,user=Depends(current_user)):
        try:
            arguments=prepare_chat(body,request,user)
            stream=agent.stream_answer(body.message,str(body.session_id),user_id=user['id'] if user else None,
                                       response_mode=body.response_mode,reply_style=body.reply_style,**arguments)
        except SkillAccessDenied as exc:raise HTTPException(403,str(exc)) from exc
        except ConversationAccessDenied as exc:raise HTTPException(404,str(exc)) from exc
        except BusyError as exc:raise HTTPException(429,str(exc),headers={'Retry-After':'5'}) from exc
        except ValueError as exc:raise HTTPException(400,str(exc)) from exc
        import anyio
        import json
        def next_event():
            try:return next(stream)
            except StopIteration:return None
        async def events():
            try:
                while True:
                    event=await anyio.to_thread.run_sync(next_event)
                    if event is None:break
                    yield 'data: '+json.dumps(event,ensure_ascii=False)+'\n\n'
            except SkillAccessDenied:
                yield 'data: '+json.dumps({'type':'error','message':'Admin access expired or was locked. Unlock Admin and activate the security skill again. Incomplete text was not saved.'})+'\n\n'
            except Exception:
                logger.exception('Streaming generation failed')
                yield 'data: '+json.dumps({'type':'error','message':'Generation interrupted. Partial text was not saved; check model settings and retry.'})+'\n\n'
            finally:
                with anyio.CancelScope(shield=True):await anyio.to_thread.run_sync(stream.close)
        return ManagedStreamingResponse(events(),close_stream=stream.close,media_type='text/event-stream',headers={'X-Accel-Buffering':'no'})

    @app.get('/api/history/{session_id}', dependencies=[Depends(authenticate)])
    def history(session_id: UUID, user=Depends(current_user)):
        guard_conversation(session_id, user)
        return {'turns': agent.store.history(str(session_id), limit=100)}

    @app.delete('/api/history/{session_id}', dependencies=[Depends(authenticate)])
    def delete_history(session_id: UUID, user=Depends(current_user)):
        guard_conversation(session_id, user)
        if not agent.lock.acquire(blocking=False):
            raise HTTPException(429, 'Wait for the current answer before deleting history')
        try:
            agent.store.delete_session(str(session_id))
        finally:
            agent.lock.release()
        return {'deleted': True}

    @app.post('/api/feedback', dependencies=[Depends(authenticate)])
    def feedback(body: ReviewRequest, user=Depends(current_user)):
        guard_conversation(body.session_id, user)
        try:
            ok = agent.store.review(str(body.session_id), str(body.turn_id), body.rating, body.approved, body.correction)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        if not ok:
            raise HTTPException(404, 'Turn not found in this conversation')
        return {'saved': True, 'approved': body.approved}

    if settings.platform.enabled:
        from .gateway import install_platform
        install_platform(app, agent, settings.platform, authenticate, signed_in)
    app.mount('/static', StaticFiles(directory=WEB), name='static')
    return app


def main():
    parser = argparse.ArgumentParser(description='Run Zenith browser chat')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=7860)
    parser.add_argument('--open-browser', action='store_true', help='Open local chat in your default browser when the server is ready')
    parser.add_argument('--warmup',action='store_true',help='Load and warm the first configured model before accepting requests')
    args = parser.parse_args()
    if args.open_browser and not 1 <= args.port <= 65535:
        parser.error('--open-browser needs a port between 1 and 65535')
    settings = Settings()
    if args.host not in {'127.0.0.1', 'localhost', '::1'} and len(settings.api_token) < 32:
        parser.error('Set ZENITH_API_TOKEN to at least 32 characters before binding a public interface')
    app=create_app(settings)
    if args.warmup:
        from .efficiency import provider_limits
        from .ensemble import EnsembleProvider
        print('Warming the first configured model. Initial downloads/loading can take time.',flush=True)
        provider=app.state.agent.provider
        if isinstance(provider,EnsembleProvider):provider=provider._provider_for(provider.route('Hello')[0][0])
        with provider_limits(provider,16):provider.generate([{'role':'system','content':'You are Zenith.'},{'role':'user','content':'Say hello briefly.'}])
        print('Model warmed. Starting the local server.',flush=True)
    import uvicorn
    if not args.open_browser:
        uvicorn.run(app, host=args.host, port=args.port, workers=1)
        return
    from threading import Event, Thread
    from .browser import open_when_ready
    server = uvicorn.Server(uvicorn.Config(app, host=args.host, port=args.port, workers=1))
    stopped = Event()
    browser_host = '[::1]' if args.host == '::1' else '127.0.0.1'
    url = f'http://{browser_host}:{args.port}'
    print('Zenith: ' + url + ' · keep this terminal open; Ctrl+C stops the server.', flush=True)
    opener = Thread(target=open_when_ready, args=(server, url, stopped), daemon=True)
    opener.start()
    try:
        server.run()
    except KeyboardInterrupt:
        pass
    finally:
        stopped.set()
        opener.join(timeout=1)



if __name__ == '__main__':
    main()
