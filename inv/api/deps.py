"""FastAPI dependency injection helpers.

The app caches a single SQLAlchemy engine on ``app.state`` so every
request reuses the same connection pool. The alternative (creating an
engine per request) duplicates the Engine-class event listener on every
call and also makes test isolation impossible because ``get_settings``
re-reads environment variables on each dependency resolution.
"""

from __future__ import annotations

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from inv.settings import Settings
from inv.storage.db import init_engine
from inv.storage.repositories import ItemRepository, LocationRepository, MovementRepository


def get_settings_from_app(request: Request) -> Settings:
    """Return the :class:`Settings` bound to this app instance.

    Populated by :func:`inv.main.create_app`. Tests can override this
    dependency via ``app.dependency_overrides`` or just create the app
    with different settings — state is never read from the environment
    at request time.
    """
    settings: Settings = request.app.state.settings
    return settings


def get_engine(request: Request) -> Engine:
    """Return the app-scoped SQLAlchemy engine."""
    engine: Engine = request.app.state.engine
    return engine


def get_session(
    engine: Annotated[Engine, Depends(get_engine)],
) -> Generator[Session, None, None]:
    """Per-request SQLAlchemy session (the engine is app-scoped)."""
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_item_repository(session: Annotated[Session, Depends(get_session)]) -> ItemRepository:
    """Dependency: ItemRepository bound to the request session."""
    return ItemRepository(session)


def get_location_repository(
    session: Annotated[Session, Depends(get_session)],
) -> LocationRepository:
    """Dependency: LocationRepository bound to the request session."""
    return LocationRepository(session)


def get_movement_repository(
    session: Annotated[Session, Depends(get_session)],
) -> MovementRepository:
    """Dependency: MovementRepository bound to the request session."""
    return MovementRepository(session)


# Re-exported for backwards compat; init_engine is still the real entrypoint.
__all__ = [
    "get_engine",
    "get_item_repository",
    "get_location_repository",
    "get_movement_repository",
    "get_session",
    "get_settings_from_app",
    "init_engine",
]
