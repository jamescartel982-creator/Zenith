"""Single-owner web chat and authenticated JSON API."""
import argparse
import hmac
import logging
from pathlib import Path
from typing import Literal
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import Settings
from .core import Agent, BusyError

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


def create_app(settings=None, agent=None):
    settings = settings or Settings()
    agent = agent or Agent(settings)
    app = FastAPI(title='Zenith', version='0.2.0', docs_url=None, redoc_url=None)
    app.state.agent = agent

    def authenticate(authorization: str = Header(default='')):
        if settings.api_token and not hmac.compare_digest(
            authorization.encode(), f'Bearer {settings.api_token}'.encode()
        ):
            raise HTTPException(401, 'Enter the server access token to continue', headers={'WWW-Authenticate': 'Bearer'})

    @app.middleware('http')
    async def security_headers(request, call_next):
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
        return {'status': 'ok', 'provider': settings.provider, 'model': settings.model_name,
                'model_loaded': getattr(agent.provider, 'model', None) is not None,
                'authentication_required': bool(settings.api_token)}

    @app.post('/api/chat', dependencies=[Depends(authenticate)])
    def chat(body: ChatRequest):
        try:
            return agent.answer(body.message, str(body.session_id))
        except BusyError as exc:
            raise HTTPException(429, str(exc), headers={'Retry-After': '5'}) from exc
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        except Exception as exc:
            logger.exception('Model generation failed')
            raise HTTPException(503, 'Model unavailable. Check server logs, model download, and provider settings.') from exc

    @app.get('/api/history/{session_id}', dependencies=[Depends(authenticate)])
    def history(session_id: UUID):
        return {'turns': agent.store.history(str(session_id), limit=100)}

    @app.delete('/api/history/{session_id}', dependencies=[Depends(authenticate)])
    def delete_history(session_id: UUID):
        if not agent.lock.acquire(blocking=False):
            raise HTTPException(429, 'Wait for the current answer before deleting history')
        try:
            agent.store.delete_session(str(session_id))
        finally:
            agent.lock.release()
        return {'deleted': True}

    @app.post('/api/feedback', dependencies=[Depends(authenticate)])
    def feedback(body: ReviewRequest):
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
