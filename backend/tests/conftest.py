import os

os.environ["ENV"] = "dev"
os.environ["DATABASE_URL"] = "sqlite://"

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401
from app.core.db import Base, get_db
from app.core.deps import require_role
from app.main import create_app
from app.seed import run as seed


@pytest.fixture
def db():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session = sessionmaker(engine, expire_on_commit=False)()
    seed.run(session, history=False)  # history is slow-ish; tests that need it opt in
    yield session
    session.close()


@pytest.fixture
def app(db) -> FastAPI:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db

    # Minimal role-gated routes so RBAC can be tested before real feature routes exist.
    for role in ("student", "faculty", "admin"):
        app.add_api_route(
            f"/_test/{role}", lambda user=Depends(require_role(role)): {"id": user.id}, methods=["GET"]
        )
    return app


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app)


def login(client: TestClient, email: str, password: str, portal: str):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password, "portal": portal})


@pytest.fixture
def as_user(app):
    """Return a fresh client signed in as the given demo account."""

    def _as(email: str, password: str, portal: str) -> TestClient:
        c = TestClient(app)
        assert login(c, email, password, portal).status_code == 200
        return c

    return _as


class FakeCache:
    """In-memory stand-in for Redis so tests never touch a real server."""

    def __init__(self):
        self.store: dict[str, str] = {}
        self.reads = 0

    def get(self, key):
        self.reads += 1
        return self.store.get(key)

    def set(self, key, value, ex=None):
        self.store[key] = value

    def delete(self, *keys):
        for k in keys:
            self.store.pop(k, None)


@pytest.fixture(autouse=True)
def fake_cache():
    from app.core import cache

    fake = FakeCache()
    cache.set_backend(fake)
    yield fake
    cache.set_backend(None)


@pytest.fixture(autouse=True)
def reset_clock():
    from app.core import clock

    yield
    clock.reset()


@pytest.fixture(autouse=True)
def fake_ai(tmp_path, monkeypatch):
    """Every test gets a deterministic model, an in-memory vector store and a private upload dir."""
    from app.agents import llm as llm_mod
    from app.agents import vectorstore
    from app.core.config import get_settings

    fake = llm_mod.FakeLLM()
    llm_mod.set_llm(fake)
    vectorstore.set_store(vectorstore.MemoryStore())
    monkeypatch.setattr(get_settings(), "upload_dir", str(tmp_path / "uploads"))
    yield fake
    llm_mod.set_llm(None)
    vectorstore.set_store(None)
