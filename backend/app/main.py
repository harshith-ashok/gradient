from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, ai, auth, faculty, health, student
from app.core.config import get_settings


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(title="Gradient API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=s.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router, prefix="/api")
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(student.router, prefix="/api/v1")
    app.include_router(faculty.router, prefix="/api/v1")
    app.include_router(admin.router, prefix="/api/v1")
    app.include_router(ai.router, prefix="/api/v1")
    return app


app = create_app()
