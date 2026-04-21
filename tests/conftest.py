"""Pytest configuration and fixtures."""

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from inv.main import create_app
from inv.settings import Settings
from inv.storage.orm import Base


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
def engine(settings: Settings):
    """Create SQLAlchemy engine."""
    engine = create_engine(f"sqlite:///{settings.db_path}")
    Base.metadata.create_all(engine)

    # Insert default location
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        from inv.storage.orm import Location

        default_location = Location(name="Main", notes="Default storage location")
        session.add(default_location)
        session.commit()
    finally:
        session.close()

    yield engine

    # Cleanup
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def session(engine):
    """Create a database session for testing."""
    connection = engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection)
    session = SessionLocal()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def app(settings: Settings):
    """Create FastAPI test app."""
    return create_app(settings)


@pytest.fixture
def client(app):
    """Create FastAPI test client."""
    return TestClient(app)
