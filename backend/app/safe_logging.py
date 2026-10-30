"""Allowlisted diagnostics. Never format exception/message/SQL/request values."""

from contextvars import ContextVar
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import logging
import sys
from uuid import uuid4


_SCOPE_KEY = "ssalfer.diagnostics"
_CURRENT = ContextVar("ssalfer_diagnostics", default=None)
_LOGGER = logging.getLogger("ssalfer.diagnostics")
_METHODS = frozenset({"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "TRACE", "CONNECT"})
_ERRORS = {
    "database_integrity": ("DB_INTEGRITY_ERROR", "database"),
    "database_internal": ("DB_INTERNAL_ERROR", "database"),
    "database_error": ("DB_API_ERROR", "database"),
    "database_statement": ("DB_STATEMENT_ERROR", "database"),
    "database_driver": ("DB_DRIVER_ERROR", "database"),
    "internal_error": ("API_INTERNAL_ERROR", "api"),
}
_SERVER_CODES = {
    "Exception in ASGI application\n": "ASGI_APPLICATION_ERROR",
    "Exception in lifespan protocol\n": "SERVER_LIFESPAN_ERROR",
    "Application startup complete.": "SERVER_STARTED",
    "Application shutdown complete.": "SERVER_STOPPED",
    "Shutting down": "SERVER_STOPPING",
}
_POOL_CODES = {
    "Exception during reset or similar": "DB_POOL_RESET_ERROR",
    "Exception terminating connection %r": "DB_POOL_TERMINATION_ERROR",
    "Invalidate connection %r (reason: %s:%s)": "DB_CONNECTION_INVALIDATED",
}


@dataclass
class RequestDiagnostics:
    correlation_id: str
    scope: dict
    routes: frozenset[str]
    status: int = 500
    started: bool = False
    complete: bool = False


@dataclass(frozen=True)
class DiagnosticEvent:
    category: str
    code: str
    component: str
    correlation_id: str | None
    method: str | None
    route: str | None
    status: int | None = None
    response_complete: bool | None = None


def _metadata(context: RequestDiagnostics | None) -> dict:
    if context is None:
        return {"correlation_id": None, "method": None, "route": None,
                "status": None, "response_complete": None}
    method = context.scope.get("method")
    template = getattr(context.scope.get("route"), "path", None)
    route = template if isinstance(template, str) and template in context.routes else "<unmatched>"
    return {"correlation_id": context.correlation_id,
            "method": method if isinstance(method, str) and method in _METHODS else "OTHER",
            "route": route, "status": context.status, "response_complete": context.complete}


def _event(category, code, component, context, status=None):
    # Snapshot primitives: never put the request scope/context on a LogRecord.
    metadata = _metadata(context)
    if status is not None:
        metadata["status"] = status
    return DiagnosticEvent(category, code, component, **metadata)


class SafeJSONFormatter(logging.Formatter):
    """Project known metadata; do not call getMessage/formatException at all.

    Third-party records retain severity/category/component, never arbitrary text,
    args, extras, stack_info, cached exc_text or exception class names.
    """
    def format(self, record):
        event = getattr(record, "safe_event", None)
        if type(event) is DiagnosticEvent:
            data = asdict(event)
        else:
            data = _metadata(_CURRENT.get())
            name = record.name
            if name == "sqlalchemy" or name.startswith("sqlalchemy."):
                component = "database"
                codes = _POOL_CODES
            elif name == "uvicorn" or name.startswith("uvicorn."):
                component = "server"
                codes = _SERVER_CODES
            elif name.startswith(("psycopg2", "psycopg")):
                component = "database_driver"
                codes = {}
            else:
                component = "dependency"
                codes = {}
            # Recognize fixed library templates, never interpolate their args.
            code = codes.get(record.msg, "RUNTIME_DIAGNOSTIC") if type(record.msg) is str else "RUNTIME_DIAGNOSTIC"
            data.update(category="runtime_diagnostic", code=code, component=component)
        level = record.levelno
        data["level"] = ("CRITICAL" if level >= logging.CRITICAL else "ERROR" if level >= logging.ERROR
                         else "WARNING" if level >= logging.WARNING else "INFO" if level >= logging.INFO else "DEBUG")
        data["timestamp"] = datetime.now(timezone.utc).isoformat()
        return json.dumps(data, ensure_ascii=True, separators=(",", ":"))


class SafeStreamHandler(logging.StreamHandler):
    def handleError(self, record):
        # logging's default fallback prints the original message and arguments.
        # An IO/formatter failure must not reopen that disclosure path.
        try:
            sys.stderr.write('{"level":"ERROR","code":"OBSERVABILITY_FAILURE",'
                             '"category":"logging_failure","component":"logging"}\n')
        except Exception:
            pass


def log_request_error(scope: dict, category: str, status: int) -> None:
    category = category if category in _ERRORS else "internal_error"
    code, component = _ERRORS[category]
    context = scope.get(_SCOPE_KEY)
    if type(context) is not RequestDiagnostics:
        context = RequestDiagnostics(uuid4().hex, scope, frozenset())
        scope[_SCOPE_KEY] = context
    # A failure after response start cannot change its HTTP status.
    response_status = context.status if context.started else status
    event = _event(category, code, component, context, response_status)
    _LOGGER.error("request_error", extra={"safe_event": event}, exc_info=False, stack_info=False)


class SafeDiagnosticsMiddleware:
    """Observe ASGI without consuming bodies, changing responses or errors."""
    def __init__(self, app, routes):
        self.app = app
        self.routes = frozenset(route.path for route in routes if isinstance(getattr(route, "path", None), str))

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        context = RequestDiagnostics(uuid4().hex, scope, self.routes)
        scope[_SCOPE_KEY] = context
        token = _CURRENT.set(context)

        async def observe_send(message):
            if message["type"] == "http.response.start":
                context.status = message["status"]
                context.started = True
            await send(message)
            if message["type"] == "http.response.body" and not message.get("more_body", False):
                context.complete = True

        try:
            await self.app(scope, receive, observe_send)
        finally:
            try:
                event = _event("http_response", "HTTP_RESPONSE", "api", context)
                _LOGGER.info("http_response", extra={"safe_event": event}, exc_info=False, stack_info=False)
            finally:
                _CURRENT.reset(token)
