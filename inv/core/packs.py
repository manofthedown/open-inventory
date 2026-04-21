"""Pack alias resolution and multiplier math.

DEVELOPMENT_PLAN.md §3 describes the casepack model:
- ``item.pack_size`` stores the default eaches-per-pack.
- ``pack_alias`` maps alternate GTINs (inner, carton, case) → canonical
  item + multiplier.
- Scanning a case barcode that matches a ``pack_alias`` auto-multiplies
  without operator input.
- All storage math is in eaches; packs are purely scan-time multipliers.

This module exposes one public function used by the scan route:
``resolve_alias`` — look up a scanned GTIN and return the canonical item
GTIN + effective multiplier if an alias exists, otherwise return the
original GTIN + 1.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from inv.storage.repositories import AliasRepository


@dataclass
class AliasResolution:
    """Result of resolving a scanned GTIN through the pack_alias table.

    Attributes:
        canonical_gtin: The item GTIN that should be looked up / moved.
            Equal to the scanned GTIN if no alias matched.
        multiplier: Effective eaches-per-scan. 1 if no alias matched.
        alias_label: Human-readable alias label (e.g. "case-12"), or None.
        was_alias: True if the scanned GTIN matched a pack_alias row.
    """

    canonical_gtin: str
    multiplier: int
    alias_label: str | None
    was_alias: bool


def resolve_alias(session: Session, scanned_gtin: str) -> AliasResolution:
    """Resolve a scanned GTIN through the pack_alias table.

    Returns an :class:`AliasResolution` with the canonical GTIN and the
    effective multiplier. If no alias is registered the scanned GTIN is
    returned unchanged with multiplier=1.

    Called by the scan route *before* the lookup chain so that a case
    barcode resolves to the known canonical item without triggering a
    fresh provider lookup.
    """
    repo = AliasRepository(session)
    alias = repo.get_by_gtin(scanned_gtin)
    if alias is None:
        return AliasResolution(
            canonical_gtin=scanned_gtin,
            multiplier=1,
            alias_label=None,
            was_alias=False,
        )
    return AliasResolution(
        canonical_gtin=alias.item.gtin,
        multiplier=alias.multiplier,
        alias_label=alias.label,
        was_alias=True,
    )
