"""FastAPI dependency injection helpers."""

from __future__ import annotations

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session, sessionmaker

from inv.settings import Settings, get_settings
from inv.storage.db import init_engine
from inv.storage.repositories import ItemRepository, LocationRepository, MovementRepository


def get_session(settings: Annotated[Settings, Depends(get_settings)]) -> Generator[Session, None, None]:
    """Dependency: get a database session.

    Each request gets a fresh session that's closed after the request.
    """
    engine = init_engine(settings)
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
