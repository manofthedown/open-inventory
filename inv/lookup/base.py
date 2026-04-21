"""ProductLookupProvider protocol and ProviderResult dataclass.

DEVELOPMENT_PLAN.md §4 and §6 define the lookup chain contract. Every
provider must implement the ``ProductLookupProvider`` protocol; the
``ChainRunner`` in ``inv/lookup/chain.py`` fans out in plan order with a
per-provider timeout and stops at the first hit.

Adding a new provider:
1. Create a new module in ``inv/lookup/``.
2. Implement a class that satisfies ``ProductLookupProvider``.
3. Register it in the ``ChainRunner`` constructor list (``chain.py``).
See ``docs/PROVIDERS.md`` for the full walkthrough.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class ProviderResult:
    """Normalised product data returned by a successful provider lookup.

    All fields except ``gtin`` and ``provider`` are optional — providers
    only populate what they have. ``ChainRunner`` merges nothing; it
    returns the first non-``None`` result and stops.

    ``raw`` holds the verbatim API payload so callers can inspect or
    store it in ``product_cache`` without information loss.
    """

    gtin: str
    provider: str  # e.g. "openfoodfacts", "openlibrary", "upcitemdb"

    name: str | None = None
    brand: str | None = None
    category: str | None = None
    # Books/media extra fields
    author: str | None = None
    # Free-form extras that don't fit a first-class field
    extra: dict = field(default_factory=dict)
    # Verbatim API response payload (stored in product_cache.payload)
    raw: dict = field(default_factory=dict)


@runtime_checkable
class ProductLookupProvider(Protocol):
    """Protocol that every lookup provider must satisfy.

    The ``name`` class attribute identifies the provider in logs, cache
    rows, and event payloads. It must be a stable string constant —
    renaming it is a breaking change for anything that reads
    ``product_cache.provider``.

    ``lookup`` is called by ``ChainRunner`` with a per-provider timeout
    applied externally via ``asyncio.wait_for``. Providers must:
    - Return ``None`` on any miss (GTIN not found).
    - Swallow all network / parse exceptions and return ``None`` — the
      chain must never propagate a provider failure to the caller.
    - Never block the event loop; use ``httpx.AsyncClient``.
    """

    name: str

    async def lookup(self, gtin: str) -> ProviderResult | None:
        """Look up a GTIN and return a result, or None on miss/error."""
        ...


__all__ = ["ProductLookupProvider", "ProviderResult"]
