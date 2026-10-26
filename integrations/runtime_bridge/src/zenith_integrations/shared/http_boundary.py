"""Pure ASGI private-API boundary without body-stream or cancellation task wrappers."""
from starlette.responses import JSONResponse
from agent.http_security import RequestSecurityMiddleware


class PrivateAPIBoundary:
    def __init__(self, app, allowed_hosts=('127.0.0.1','localhost','::1')):
        self.app = RequestSecurityMiddleware(app, allowed_hosts=tuple(allowed_hosts))

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http':
            headers = scope.get('headers', [])
            if any(name.lower() == b'origin' or (name.lower() == b'sec-fetch-site' and value.lower() == b'cross-site') for name,value in headers):
                response = JSONResponse({'detail':'Browser-origin integration requests are disabled'},status_code=403,
                                        headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})
                return await response(scope,receive,send)
        async def guarded_send(message):
            if message['type'] == 'http.response.start':
                headers = [(k,v) for k,v in message.get('headers',[]) if k.lower() not in {b'cache-control',b'x-content-type-options'}]
                message = {**message,'headers':headers+[(b'cache-control',b'no-store'),(b'x-content-type-options',b'nosniff')]}
            await send(message)
        await self.app(scope,receive,guarded_send)
