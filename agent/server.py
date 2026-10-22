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
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import Settings
from .core import Agent, BusyError
from .registry import Catalog

WEB = Path(__file__).parent / 'web'
logger = logging.getLogger('zenith')


class ChatRequest(BaseModel):
    session_id: UUID
    message: str = Field(min_length=1, max_length=12000)


class ReviewRequest(BaseModel):
    session_id: UUID
    turn_id: UUID
    rating: Literal['good', 'bad']
    approved: bool = False
    correction: str | None = Field(default=None, max_length=24000)


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=40)
    password: str = Field(min_length=1, max_length=256)


class RegisterRequest(LoginRequest):
    display_name: str = Field(min_length=1, max_length=60)


class MemoryRequest(BaseModel):
    content: str = Field(min_length=1, max_length=500)


def create_app(settings=None, agent=None, catalog=None):
    settings = settings or Settings()
    agent = agent or Agent(settings)
    app = FastAPI(title='Zenith', version='0.5.0', docs_url=None, redoc_url=None)
    app.state.agent = agent
    app.state.catalog = catalog
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
        return {'status': 'ok', 'provider': settings.provider, 'model': settings.model_name, 'display_name': settings.display_name,
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

    @app.get('/api/model-packs', dependencies=[Depends(authenticate)])
    def model_packs():
        from .packs import summaries
        return {'packs': summaries()}

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

    @app.get('/api/knowledge', dependencies=[Depends(authenticate)])
    def knowledge_status():
        return agent.store.knowledge_stats()

    @app.post('/api/chat', dependencies=[Depends(authenticate)])
    def chat(body: ChatRequest, user=Depends(current_user)):
        guard_conversation(body.session_id, user, create=True)
        try:
            return agent.answer(body.message, str(body.session_id), user_id=user['id'] if user else None)
        except BusyError as exc:
            raise HTTPException(429, str(exc), headers={'Retry-After': '5'}) from exc
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        except Exception as exc:
            logger.exception('Model generation failed')
            raise HTTPException(503, 'Model unavailable. Check server logs, model download, and provider settings.') from exc

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

    app.mount('/static', StaticFiles(directory=WEB), name='static')
    return app


def main():
    parser = argparse.ArgumentParser(description='Run Zenith browser chat')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=7860)
    args = parser.parse_args()
    settings = Settings()
    if args.host not in {'127.0.0.1', 'localhost', '::1'} and len(settings.api_token) < 32:
        parser.error('Set ZENITH_API_TOKEN to at least 32 characters before binding a public interface')
    import uvicorn
    uvicorn.run(create_app(settings), host=args.host, port=args.port, workers=1)


if __name__ == '__main__':
    main()
