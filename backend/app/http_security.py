"""Error headers at the HTTP boundary; bodies, statuses and streaming stay intact."""
import re

from starlette.datastructures import MutableHeaders
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse


def _error_headers(message):
    if message['type'] != 'http.response.start' or message['status'] < 400:
        return
    headers = MutableHeaders(scope=message)
    headers['X-Content-Type-Options'] = 'nosniff'
    # Retain stronger directives and quoted field lists, including multiple lines.
    value = ', '.join(headers.getlist('cache-control'))
    parts = [p.strip() for p in re.split(r',(?=(?:[^"]*"[^"]*")*[^"]*$)', value)
             if p.strip() and p.strip().lower() != 'public']
    for directive in ('private', 'no-store'):
        if directive not in {p.lower() for p in parts}:
            parts.append(directive)
    headers['Cache-Control'] = ', '.join(parts)


class ErrorHeadersMiddleware:
    """Pure ASGI: no body buffering, request inspection or exception replacement."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)

        async def secured_send(message):
            _error_headers(message)
            await send(message)

        await self.app(scope, receive, secured_send)


class ErrorJSONResponse(JSONResponse):
    """The global 500 is emitted above user middleware by ServerErrorMiddleware.

    Reuse the application's registered CORS configuration for that response,
    rather than duplicating origin/credentials/exposed-header decisions here.
    """
    async def __call__(self, scope, receive, send):
        cors = next((item for item in getattr(scope.get('app'), 'user_middleware', ())
                     if item.cls is CORSMiddleware), None)
        response = ErrorHeadersMiddleware(super().__call__)
        if cors is not None:
            response = CORSMiddleware(response, **cors.kwargs)
        await response(scope, receive, send)
