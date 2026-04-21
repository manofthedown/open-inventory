"""Database engine and session management."""

from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from inv.settings import Settings


def init_engine(settings: Settings) -> Engine:
    """Initialize SQLAlchemy engine with WAL mode for SQLite."""
    db_path = settings.db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Construct SQLite URL
    url = f"sqlite:///{db_path}"
    engine = create_engine(url, echo=False, connect_args={"check_same_thread": False})

    # Enable WAL mode for concurrent read access
    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
        """Set SQLite pragmas for WAL mode and other optimizations."""
        if hasattr(dbapi_connection, "execute"):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()

    return engine


def get_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a session factory."""
    return sessionmaker(engine, class_=Session, expire_on_commit=False)
