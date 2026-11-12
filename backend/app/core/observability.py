"""Request ids, structured logs and security headers."""

import contextvars
import json
import logging
import re
import time
import uuid

from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.deps import ACCESS_COOKIE
from app.core.security import decode_token
from app.services import monitor

request_id: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")
access_log = logging.getLogger("gradient.access")
_SAFE_ID = re.compile(r"^[A-Za-z0-9_.-]{8,64}$")

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "same-origin",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Give every request an id (kept if the caller sent a sane one), log it with its duration,
    and add security headers. API responses are never cached by browsers or proxies."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        incoming = request.headers.get("x-request-id", "")
        rid = incoming if _SAFE_ID.match(incoming) else uuid.uuid4().hex
        token = request_id.set(rid)
        request.state.request_id = rid
        start = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
        finally:
            ms = round((time.perf_counter() - start) * 1000)
            access_log.info("%s %s -> %s in %dms", request.method, request.url.path, status, ms,
                            extra={"http_status": status, "duration_ms": ms})
            await self._save(request, rid, status, ms)
            request_id.reset(token)
        response.headers["X-Request-ID"] = rid
        for k, v in SECURITY_HEADERS.items():
            response.headers.setdefault(k, v)
        if request.url.path.startswith("/api"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response


    @staticmethod
    async def _save(request: Request, rid: str, status: int, ms: int) -> None:
        path = request.url.path
        if not path.startswith("/api") or path.startswith("/api/health"):
            return
        if request.method == "GET" and path == "/api/v1/admin/logs":
            return  # the log viewer polling itself would drown everything else
        if path == "/api/v1/auth/me" and status < 400:
            return  # the web app checks the session on every page; only failures are interesting
        who = actor(request)
        await run_in_threadpool(
            monitor.record_request, request_id=rid, method=request.method,
            path=route_template(request), status=status, duration_ms=ms,
            user_id=who[0], role=who[1],
        )


API_PREFIXES = ("/api/v1", "/api")  # where main.py mounts the routers


def route_template(request: Request) -> str:
    """The matched route as written in code (/api/v1/courses/{course_id}), so numbers and ids in the
    URL do not make every request look like a different endpoint. Unmatched URLs keep their raw path."""
    path = request.url.path
    route = request.scope.get("route")
    tpl = getattr(route, "path", None)
    if not tpl:
        return path
    prefix = next((p for p in API_PREFIXES if path.startswith(p + "/")), "")
    return tpl if tpl.startswith(prefix + "/") else prefix + tpl


def actor(request: Request) -> tuple[str | None, str | None]:
    """Who made the request, read from the token's claims (no database lookup)."""
    token = request.cookies.get(ACCESS_COOKIE)
    claims = decode_token(token, "access") if token else None
    return (claims.get("sub"), claims.get("role")) if claims else (None, None)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        out = {"ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"), "level": record.levelname,
               "logger": record.name, "msg": record.getMessage(), "request_id": request_id.get()}
        for k in ("http_status", "duration_ms", "llm"):
            if hasattr(record, k):
                out[k] = getattr(record, k)
        if record.exc_info:
            out["exc"] = self.formatException(record.exc_info)
        return json.dumps(out)


class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.rid = request_id.get()
        return True


def configure_logging(json_logs: bool) -> None:
    root = logging.getLogger()
    handler = logging.StreamHandler()
    handler.addFilter(_RequestIdFilter())
    handler.setFormatter(JsonFormatter() if json_logs else logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s [%(rid)s] %(message)s"))
    root.handlers = [handler, monitor.DatabaseLogHandler()]
    root.setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").disabled = True  # replaced by gradient.access
