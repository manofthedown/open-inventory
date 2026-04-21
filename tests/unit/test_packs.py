"""Unit tests for pack alias resolution (inv/core/packs.py).

Tests the AliasRepository and resolve_alias() using the real SQLite
session fixture so alias FK constraints are exercised.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from inv.core.packs import resolve_alias
from inv.storage.orm import Item
from inv.storage.repositories import AliasRepository, ItemRepository


def _make_item(session: Session, gtin: str, name: str | None = None) -> Item:
    repo = ItemRepository(session)
    item = repo.create(gtin, name=name, needs_review=False, source="test")
    session.commit()
    return item


# ------------------------------------------------------------------ #
# AliasRepository                                                     #
# ------------------------------------------------------------------ #


def test_alias_repo_create_and_get(session: Session) -> None:
    """Creating an alias and fetching it by GTIN round-trips correctly."""
    item = _make_item(session, "1234567890123", "Canonical Item")
    repo = AliasRepository(session)
    repo.create(gtin="0012345678901", item_id=item.id, multiplier=12, label="case-12")
    session.commit()

    fetched = repo.get_by_gtin("0012345678901")
    assert fetched is not None
    assert fetched.multiplier == 12
    assert fetched.label == "case-12"
    assert fetched.item_id == item.id


def test_alias_repo_list_for_item(session: Session) -> None:
    """list_for_item returns all aliases registered for a given item."""
    item = _make_item(session, "1111111111111")
    repo = AliasRepository(session)
    repo.create(gtin="0011111111111", item_id=item.id, multiplier=6, label="inner-6")
    repo.create(gtin="0021111111111", item_id=item.id, multiplier=24, label="case-24")
    session.commit()

    aliases = repo.list_for_item(item.id)
    assert len(aliases) == 2
    gtins = {a.gtin for a in aliases}
    assert "0011111111111" in gtins
    assert "0021111111111" in gtins


def test_alias_repo_delete(session: Session) -> None:
    """delete() removes the alias and returns True; returns False if missing."""
    item = _make_item(session, "2222222222222")
    repo = AliasRepository(session)
    repo.create(gtin="0022222222222", item_id=item.id, multiplier=12)
    session.commit()

    assert repo.delete("0022222222222") is True
    session.commit()
    assert repo.get_by_gtin("0022222222222") is None

    assert repo.delete("0022222222222") is False


def test_alias_repo_get_missing_returns_none(session: Session) -> None:
    """get_by_gtin returns None for an unregistered GTIN."""
    repo = AliasRepository(session)
    assert repo.get_by_gtin("9999999999999") is None


# ------------------------------------------------------------------ #
# resolve_alias                                                       #
# ------------------------------------------------------------------ #


def test_resolve_alias_no_match(session: Session) -> None:
    """resolve_alias returns the original GTIN unchanged when no alias exists."""
    resolution = resolve_alias(session, "3333333333333")
    assert resolution.canonical_gtin == "3333333333333"
    assert resolution.multiplier == 1
    assert resolution.was_alias is False
    assert resolution.alias_label is None


def test_resolve_alias_hit(session: Session) -> None:
    """resolve_alias returns the canonical GTIN + multiplier when an alias matches."""
    item = _make_item(session, "4444444444444", "Canonical Product")
    repo = AliasRepository(session)
    repo.create(gtin="0044444444444", item_id=item.id, multiplier=12, label="case-12")
    session.commit()

    resolution = resolve_alias(session, "0044444444444")
    assert resolution.canonical_gtin == "4444444444444"
    assert resolution.multiplier == 12
    assert resolution.was_alias is True
    assert resolution.alias_label == "case-12"
