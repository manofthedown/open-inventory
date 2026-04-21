"""Local SQLite product cache — read-through wrapper.

The cache sits at position 0 in the lookup chain (before any network
provider). On a hit it deserialises the stored payload back into a
``ProviderResult`` so callers see a uniform interface regardless of
whether the data came from the DB or the network.

On a network hit the ``ChainRunner`` calls ``CacheProvider.store`` to
write the result through; this keeps cache population out of the
individual provider implementations (they stay stateless / session-free).

The cache is synchronous under the hood (SQLAlchemy + SQLite), wrapped in
an async interface so it fits the ``ProductLookupProvider`` protocol
without special-casing in the chain runner.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from inv.lookup.base import ProviderResult
from inv.storage.repositories import CacheRepository


class CacheProvider:
    """Read-through cache backed by the ``product_cache`` SQLite table.

    Construct with a live ``Session``; the session lifetime is managed
    by the caller (typically the FastAPI dependency or a service function).
    """

    name = "cache"

    def __init__(self, session: Session) -> None:
        """Bind to a SQLAlchemy session."""
        self._repo = CacheRepository(session)
        self._session = session

    async def lookup(self, gtin: str) -> ProviderResult | None:
        """Return a cached ProviderResult, or None if not in cache."""
        entry = self._repo.get(gtin)
        if entry is None:
            return None

        payload = entry.payload or {}
        # The cache stores the raw API payload plus the normalised fields
        # we extracted at store time. Re-hydrate the ProviderResult from
        # the stored normalised fields so callers don't have to re-parse
        # provider-specific payload shapes.
        return ProviderResult(
            gtin=gtin,
            provider=entry.provider,
            name=payload.get("_name"),
            brand=payload.get("_brand"),
            category=payload.get("_category"),
            author=payload.get("_author"),
            extra=payload.get("_extra", {}),
            raw=payload.get("_raw", {}),
        )

    def store(self, result: ProviderResult) -> None:
        """Persist a ProviderResult into the cache. Caller owns the commit.

        We store normalised fields with a ``_`` prefix alongside the raw
        payload so that cache hits don't need provider-specific parsing.
        """
        payload = {
            "_name": result.name,
            "_brand": result.brand,
            "_category": result.category,
            "_author": result.author,
            "_extra": result.extra,
            "_raw": result.raw,
        }
        self._repo.set(gtin=result.gtin, provider=result.provider, payload=payload)
