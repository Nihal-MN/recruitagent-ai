"""Engine + session factory. Works against PostgreSQL (Docker) and SQLite (dev)."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings

_settings = get_settings()

_engine_kwargs: dict = {"pool_pre_ping": True}
if _settings.sqlalchemy_url.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
    if ":memory:" in _settings.sqlalchemy_url or _settings.sqlalchemy_url.endswith("sqlite://"):
        _engine_kwargs["poolclass"] = StaticPool

engine = create_engine(_settings.sqlalchemy_url, **_engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
