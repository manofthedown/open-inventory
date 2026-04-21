"""Alembic migration round-trip tests.

Keeps the baseline migration honest: if the ORM and migration drift,
these tests fail at the next commit rather than at release time.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text

from inv.settings import Settings
from inv.storage.migrations import downgrade_to_base, upgrade_to_head

EXPECTED_TABLES = {"item", "location", "movement", "pack_alias", "product_cache"}
EXPECTED_VIEWS = {"inventory_view"}


@pytest.fixture
def fresh_settings() -> Settings:
    """Settings pointing at a fresh temporary SQLite file."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        return Settings(database_url=f"sqlite:///{Path(f.name)}")


def _engine(settings: Settings):  # type: ignore[no-untyped-def]
    return create_engine(f"sqlite:///{settings.db_path}")


def test_upgrade_creates_all_tables(fresh_settings: Settings) -> None:
    """`alembic upgrade head` creates every table declared in DEVELOPMENT_PLAN §5."""
    upgrade_to_head(fresh_settings)
    insp = inspect(_engine(fresh_settings))
    assert EXPECTED_TABLES.issubset(set(insp.get_table_names()))


def test_upgrade_creates_inventory_view(fresh_settings: Settings) -> None:
    """`inventory_view` is created and queryable on a fresh DB."""
    upgrade_to_head(fresh_settings)
    engine = _engine(fresh_settings)
    insp = inspect(engine)
    assert EXPECTED_VIEWS.issubset(set(insp.get_view_names()))

    with engine.connect() as conn:
        rows = conn.execute(text("SELECT item_id, location_id, on_hand FROM inventory_view")).all()
    # Fresh DB — no movements, so the view returns no rows
    assert rows == []


def test_alembic_version_row_recorded(fresh_settings: Settings) -> None:
    """After upgrade, Alembic records its revision in alembic_version."""
    upgrade_to_head(fresh_settings)
    with _engine(fresh_settings).connect() as conn:
        version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
    assert version == "0001"


def test_downgrade_removes_schema(fresh_settings: Settings) -> None:
    """`alembic downgrade base` drops all tables and views."""
    upgrade_to_head(fresh_settings)
    downgrade_to_base(fresh_settings)

    insp = inspect(_engine(fresh_settings))
    remaining = set(insp.get_table_names())
    # Only Alembic's own bookkeeping table should remain.
    assert remaining == {"alembic_version"}
    assert set(insp.get_view_names()) == set()
