"""Synchronous database engine and session factory.

For code that cannot run on the event loop, such as Celery tasks. The
application itself uses the async engine and sessions in `app.core.db`.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

sync_engine = create_engine(
    settings.db_url_sync.human_repr(),
    echo=True if settings.debug else False,
    future=True,
    pool_pre_ping=True,
)

session_factory = sessionmaker(
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    bind=sync_engine,
    class_=Session,
)
