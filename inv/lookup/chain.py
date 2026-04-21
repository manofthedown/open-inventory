"""ChainRunner — ordered lookup chain with per-provider timeout.

DEVELOPMENT_PLAN.md §4 defines the chain order:
  0. Local cache (CacheProvider)
  1. Open Food Facts
  2. Open Library
  3. OpenGTINdb  (stub — always misses; slot reserved)
  4. UPCitemdb

The runner stops at the first non-None result. On a network hit it writes
the result through to the cache before returning. If every provider misses,
it returns None and the caller is responsible for emitting ``scan.unknown``
and marking the item ``needs_review``.

Each *network* provider is wrapped in ``asyncio.wait_for`` with
``provider_timeout`` seconds (default 3 s). The cache provider is not
timed — it's a synchronous SQLite read and should be sub-millisecond.
"""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy.orm import Session

from inv.lookup.base import ProductLookupProvider, ProviderResult
from inv.lookup.cache import CacheProvider
from inv.lookup.openfoodfacts import OpenFoodFactsProvider
from inv.lookup.opengtindb import OpenGTINdbProvider
from inv.lookup.openlibrary import OpenLibraryProvider
from inv.lookup.upcitemdb import UPCitemdbProvider

log = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 3.0  # seconds per provider


class ChainRunner:
    """Run the provider chain for a single GTIN lookup.

    Construct once per scan (or per app startup if the providers are
    stateless). The ``session`` is required for the cache read/write;
    network providers are stateless and don't touch the DB.

    Args:
        session: Live SQLAlchemy session. The runner will commit cache
            writes; callers must not close the session before the lookup
            completes.
        provider_timeout: Per-network-provider timeout in seconds.
            Defaults to 3 s (plan §4). Cache is not timed.
        extra_providers: Additional providers inserted after the four
            built-ins (for testing or future extension).
    """

    def __init__(
        self,
        session: Session,
        provider_timeout: float = _DEFAULT_TIMEOUT,
        extra_providers: list[ProductLookupProvider] | None = None,
    ) -> None:
        self._cache = CacheProvider(session)
        self._session = session
        self._timeout = provider_timeout
        # Network providers in plan order (cache is handled separately)
        self._network_providers: list[ProductLookupProvider] = [
            OpenFoodFactsProvider(),
            OpenLibraryProvider(),
            OpenGTINdbProvider(),
            UPCitemdbProvider(),
            *(extra_providers or []),
        ]

    async def run(self, gtin: str) -> ProviderResult | None:
        """Look up a GTIN through the full chain.

        Returns the first successful ``ProviderResult``, or ``None`` if
        every provider misses. Cache hits are returned immediately without
        touching network providers.
        """
        # Step 0: local cache (no timeout — synchronous SQLite)
        cached = await self._cache.lookup(gtin)
        if cached is not None:
            log.debug("cache hit for %s (provider=%s)", gtin, cached.provider)
            return cached

        # Steps 1-4: network providers with per-provider timeout
        attempted: list[str] = []
        for provider in self._network_providers:
            attempted.append(provider.name)
            try:
                result = await asyncio.wait_for(
                    provider.lookup(gtin),
                    timeout=self._timeout,
                )
            except TimeoutError:
                log.warning("provider %s timed out for gtin=%s", provider.name, gtin)
                result = None
            except Exception:
                log.exception("provider %s raised for gtin=%s", provider.name, gtin)
                result = None

            if result is not None:
                log.debug(
                    "provider %s hit for gtin=%s name=%r",
                    provider.name,
                    gtin,
                    result.name,
                )
                # Write through to cache
                self._cache.store(result)
                self._session.commit()
                return result

        log.debug("all providers missed for gtin=%s attempted=%s", gtin, attempted)
        return None

    @property
    def provider_names(self) -> list[str]:
        """Names of all network providers in chain order."""
        return [p.name for p in self._network_providers]
