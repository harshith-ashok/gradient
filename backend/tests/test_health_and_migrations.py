from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.pool import StaticPool

from alembic import command
from app.core.db import Base


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_migration_matches_models():
    """Upgrading to head must create every table the models define (and downgrade removes them)."""
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    cfg = Config("alembic.ini")
    cfg.attributes["engine"] = engine
    command.upgrade(cfg, "head")
    tables = set(inspect(engine).get_table_names()) - {"alembic_version"}
    assert tables == set(Base.metadata.tables)
    command.downgrade(cfg, "base")
    assert set(inspect(engine).get_table_names()) == {"alembic_version"}
