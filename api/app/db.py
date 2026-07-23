"""SQLAlchemy engine and session management for the audit store.

SQLite by design: audit runs are transient and free hosts wipe local disk
on redeploy, which is acceptable here. Do not add a paid database.
"""

import threading

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session

from app.config import get_settings


class Base(DeclarativeBase):
    pass


_engine = None
_engine_lock = threading.Lock()


def _build_engine(database_url: str):
    connect_args = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(database_url, connect_args=connect_args)


def configure(database_url: str) -> None:
    """Point the store at a different database. Used by tests."""
    global _engine
    with _engine_lock:
        _engine = _build_engine(database_url)


def get_engine():
    global _engine
    with _engine_lock:
        if _engine is None:
            _engine = _build_engine(get_settings().database_url)
        return _engine


def init_db() -> None:
    from app import models  # noqa: F401, imports register the tables

    Base.metadata.create_all(get_engine())


def create_session() -> Session:
    return Session(bind=get_engine(), expire_on_commit=False)
