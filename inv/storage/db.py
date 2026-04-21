"""Database engine and session management."""

from __future__ import annotations

from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from inv.settings import Settings


def init_engine(settings: Settings) -> Engine:
    """Initialize a SQLAlchemy engine with SQLite WAL + sensible pragmas.

    Listeners are attached to the returned engine **instance** — not to
    the ``Engine`` class — so repeated ``init_engine`` calls (tests,
    multiple app factories) do not accumulate duplicate PRAGMA
    executions on every ``connect``.
    """
    db_path = settings.db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(
        f"sqlite:///{db_path}",
        echo=False,
        connect_args={"check_same_thread": False},
        future=True,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection: Any, _connection_record: Any) -> None:
        """WAL mode + NORMAL sync for the SQLite workload described in §8."""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def get_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a session factory bound to the given engine."""
    return sessionmaker(engine, class_=Session, expire_on_commit=False)
