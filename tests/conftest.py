"""Pytest configuration and fixtures."""

import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from inv.main import create_app
from inv.settings import Settings
from inv.storage.db import init_engine
from inv.storage.migrations import upgrade_to_head


@pytest.fixture
def temp_db() -> Path:
    """Create a temporary SQLite database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        return Path(f.name)


@pytest.fixture
def settings(temp_db: Path) -> Settings:
    """Create test settings with temporary database."""
    settings = Settings(
        host="127.0.0.1",
        port=8765,
        database_url=f"sqlite:///{temp_db}",
        log_level="debug",
    )
    return settings


@pytest.fixture
def engine(settings: Settings) -> Iterator[Engine]:
    """Create SQLAlchemy engine with schema migrated via Alembic.

    Tests go through the same migration path as production so ORM/migration
    drift is caught immediately.
    """
    upgrade_to_head(settings)
    engine = init_engine(settings)

    # Seed the default Main location (same as `inventory init`)
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as session:
        from inv.storage.orm import Location

        default_location = Location(name="Main", notes="Default storage location")
        session.add(default_location)
        session.commit()

    yield engine

    engine.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    """Create a database session bound to a rolled-back transaction."""
    connection = engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection)
    session = SessionLocal()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def app(settings: Settings, engine: Engine):  # type: ignore[no-untyped-def]
    """Create a FastAPI test app bound to a migrated temp DB.

    Depends on ``engine`` so the schema is guaranteed to exist and the
    default ``Main`` location is seeded. The app instance itself will
    call ``init_engine(settings)`` again — both engines point at the
    same SQLite file (the one in ``temp_db``), so there's no bleed.
    """
    return create_app(settings)


@pytest.fixture
def client(app) -> TestClient:  # type: ignore[no-untyped-def]
    """Create FastAPI test client."""
    return TestClient(app)
