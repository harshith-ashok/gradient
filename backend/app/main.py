from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from app.api import admin, ai, auth, coding, faculty, health, ops, student
from app.core.config import get_settings
from app.core.observability import RequestContextMiddleware, actor, configure_logging, route_template
from app.services import monitor

# (router, prefix) pairs, kept so the admin dashboard can list every endpoint and who may call it.
ROUTERS = [
    (health.router, "/api"), (auth.router, "/api/v1"), (student.router, "/api/v1"),
    (faculty.router, "/api/v1"), (admin.router, "/api/v1"), (ops.router, "/api/v1"),
    (ai.router, "/api/v1"), (coding.router, "/api/v1"),
]


def create_app() -> FastAPI:
    s = get_settings()
    configure_logging(s.log_json)
    app = FastAPI(title="Gradient API", version="0.1.0")
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=s.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )
    for router, prefix in ROUTERS:
        app.include_router(router, prefix=prefix)
    app.state.routers = ROUTERS

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception) -> JSONResponse:
        # Record the crash (with its stack trace) for the admin dashboard; the caller only gets an id.
        rid = getattr(request.state, "request_id", None)
        who = actor(request)
        await run_in_threadpool(
            monitor.capture_exception, exc, request_id=rid, method=request.method,
            path=route_template(request), user_id=who[0],
        )
        return JSONResponse({"detail": "Something went wrong on our side.", "request_id": rid},
                            status_code=500, headers={"X-Request-ID": rid or "-"})
    return app


app = create_app()
