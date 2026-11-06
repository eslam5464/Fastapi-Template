"""Tests for the synchronous engine and session factory (app.core.db_sync)."""

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.db_sync import session_factory, sync_engine


def test_sync_engine_uses_sync_url():
    assert isinstance(sync_engine, Engine)
    assert sync_engine.url.drivername == settings.db_url_sync.scheme
    assert sync_engine.url.database == settings.db_url_sync.path.lstrip("/")


def test_session_factory_configuration():
    assert isinstance(session_factory, sessionmaker)
    assert session_factory.kw["bind"] is sync_engine
    assert issubclass(session_factory.class_, Session)
    assert session_factory.kw["expire_on_commit"] is False
    assert session_factory.kw["autoflush"] is False


def test_async_db_module_has_no_sync_engine():
    from app.core import db

    assert not hasattr(db, "sync_engine")
    assert not hasattr(db, "session_factory")
