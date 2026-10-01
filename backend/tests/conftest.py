"""Shared pytest fixtures — hermetic: in-memory SQLite + demo provider."""

from __future__ import annotations

import os

# Must be set before any app module is imported.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["AI_PROVIDER"] = "mock"
os.environ.pop("OPENAI_API_KEY", None)

import pytest  # noqa: E402

from app.core.config import get_settings  # noqa: E402

get_settings.cache_clear()

from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.seed import run_seed  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _schema():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture()
def db(_schema):
    """A session over freshly seeded demo data (reset per test)."""
    session = SessionLocal()
    run_seed.reset_all(session)
    run_seed.seed(session)
    yield session
    session.close()


@pytest.fixture()
def client(db):
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)
