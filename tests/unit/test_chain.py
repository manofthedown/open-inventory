"""Unit tests for the lookup chain, cache, and individual providers.

All HTTP calls are intercepted by respx using recorded fixtures from
tests/fixtures/providers/ so the suite runs fully offline.
"""

from __future__ import annotations

import json
from pathlib import Path

import respx
from httpx import Response
from sqlalchemy.orm import Session

from inv.lookup.base import ProductLookupProvider, ProviderResult
from inv.lookup.cache import CacheProvider
from inv.lookup.chain import ChainRunner
from inv.lookup.openfoodfacts import OpenFoodFactsProvider
from inv.lookup.openlibrary import OpenLibraryProvider
from inv.lookup.upcitemdb import UPCitemdbProvider

FIXTURES = Path(__file__).parent.parent / "fixtures" / "providers"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


# ------------------------------------------------------------------ #
# ProviderResult / protocol smoke                                     #
# ------------------------------------------------------------------ #


def test_provider_result_defaults() -> None:
    """ProviderResult fills optional fields with None / empty defaults."""
    r = ProviderResult(gtin="1234567890123", provider="test")
    assert r.name is None
    assert r.brand is None
    assert r.extra == {}
    assert r.raw == {}


def test_productlookupprovider_protocol_satisfied() -> None:
    """OpenFoodFactsProvider satisfies the ProductLookupProvider protocol."""
    provider = OpenFoodFactsProvider()
    assert isinstance(provider, ProductLookupProvider)


# ------------------------------------------------------------------ #
# Open Food Facts                                                     #
# ------------------------------------------------------------------ #


@respx.mock
async def test_off_hit_returns_provider_result() -> None:
    """OFF provider returns a populated ProviderResult on a known GTIN."""
    gtin = "3017620422003"
    payload = _load("openfoodfacts_hit.json")
    respx.get(f"https://world.openfoodfacts.org/api/v2/product/{gtin}.json").mock(
        return_value=Response(200, json=payload)
    )

    provider = OpenFoodFactsProvider()
    result = await provider.lookup(gtin)

    assert result is not None
    assert result.provider == "openfoodfacts"
    assert result.gtin == gtin
    assert result.name == "Nutella"
    assert result.brand == "Nutella"
    assert result.category is not None


@respx.mock
async def test_off_miss_returns_none() -> None:
    """OFF provider returns None when status==0 (product not found)."""
    gtin = "0000000000000"
    payload = _load("openfoodfacts_miss.json")
    respx.get(f"https://world.openfoodfacts.org/api/v2/product/{gtin}.json").mock(
        return_value=Response(200, json=payload)
    )

    provider = OpenFoodFactsProvider()
    result = await provider.lookup(gtin)
    assert result is None


@respx.mock
async def test_off_network_error_returns_none() -> None:
    """OFF provider swallows network errors and returns None."""
    import httpx

    gtin = "3017620422003"
    respx.get(f"https://world.openfoodfacts.org/api/v2/product/{gtin}.json").mock(
        side_effect=httpx.ConnectError("unreachable")
    )

    provider = OpenFoodFactsProvider()
    result = await provider.lookup(gtin)
    assert result is None


@respx.mock
async def test_off_multibrand_normalised_to_first() -> None:
    """Brand field is normalised: only the first of a comma-separated list is kept."""
    gtin = "3017620422003"
    payload = _load("openfoodfacts_hit.json")
    payload["product"]["brands"] = "Nutella, Ferrero"
    respx.get(f"https://world.openfoodfacts.org/api/v2/product/{gtin}.json").mock(
        return_value=Response(200, json=payload)
    )

    provider = OpenFoodFactsProvider()
    result = await provider.lookup(gtin)
    assert result is not None
    assert result.brand == "Nutella"


# ------------------------------------------------------------------ #
# Open Library                                                        #
# ------------------------------------------------------------------ #


@respx.mock
async def test_openlibrary_isbn13_hit() -> None:
    """Open Library provider returns name + author for a known ISBN-13."""
    isbn = "9780140328721"
    payload = _load("openlibrary_hit.json")
    respx.get("https://openlibrary.org/api/books").mock(
        return_value=Response(200, json=payload)
    )

    provider = OpenLibraryProvider()
    result = await provider.lookup(isbn)

    assert result is not None
    assert result.provider == "openlibrary"
    assert result.name == "Fantastic Mr. Fox"
    assert result.author == "Roald Dahl"
    assert result.brand == "Puffin"


@respx.mock
async def test_openlibrary_miss_returns_none() -> None:
    """Open Library returns None when the ISBN key is absent from the response."""
    isbn = "9780140328721"
    payload = _load("openlibrary_miss.json")
    respx.get("https://openlibrary.org/api/books").mock(
        return_value=Response(200, json=payload)
    )

    provider = OpenLibraryProvider()
    result = await provider.lookup(isbn)
    assert result is None


async def test_openlibrary_non_isbn_skipped() -> None:
    """Open Library skips GTINs that don't look like ISBNs (no network call)."""
    provider = OpenLibraryProvider()
    # Plain 13-digit food GTIN — should skip immediately, no network
    result = await provider.lookup("3017620422003")
    assert result is None


# ------------------------------------------------------------------ #
# UPCitemdb                                                           #
# ------------------------------------------------------------------ #


@respx.mock
async def test_upcitemdb_hit() -> None:
    """UPCitemdb provider returns a result for a known 12-digit UPC."""
    upc = "012000161155"
    payload = _load("upcitemdb_hit.json")
    respx.get("https://api.upcitemdb.com/prod/trial/lookup").mock(
        return_value=Response(200, json=payload)
    )

    provider = UPCitemdbProvider()
    result = await provider.lookup(upc)

    assert result is not None
    assert result.provider == "upcitemdb"
    assert result.name == "LIFEWTR Premium Purified Bottled Water"
    assert result.brand == "LIFEWTR"


@respx.mock
async def test_upcitemdb_miss_returns_none() -> None:
    """UPCitemdb returns None when code != 'OK'."""
    upc = "012000000000"
    payload = _load("upcitemdb_miss.json")
    respx.get("https://api.upcitemdb.com/prod/trial/lookup").mock(
        return_value=Response(200, json=payload)
    )

    provider = UPCitemdbProvider()
    result = await provider.lookup(upc)
    assert result is None


async def test_upcitemdb_ean13_with_leading_zero_converted() -> None:
    """A 13-digit GTIN starting with 0 is stripped to 12 digits for the API."""
    # We just verify it doesn't skip — it will call the API (mocked to return miss)
    with respx.mock:
        respx.get("https://api.upcitemdb.com/prod/trial/lookup").mock(
            return_value=Response(200, json={"code": "NOT_FOUND"})
        )
        provider = UPCitemdbProvider()
        result = await provider.lookup("0012000161155")
        # Called (not skipped); returned None because of NOT_FOUND
        assert result is None


async def test_upcitemdb_14digit_skipped() -> None:
    """GTIN-14 is skipped — UPCitemdb free tier only accepts 12-digit UPC-A."""
    provider = UPCitemdbProvider()
    result = await provider.lookup("00012000161155")
    assert result is None


# ------------------------------------------------------------------ #
# CacheProvider                                                       #
# ------------------------------------------------------------------ #


def test_cache_miss_returns_none(session: Session) -> None:
    """CacheProvider returns None for a GTIN not yet in the cache."""
    cache = CacheProvider(session)

    async def _run() -> None:
        result = await cache.lookup("9999999999999")
        assert result is None

    import asyncio

    asyncio.get_event_loop().run_until_complete(_run())


def test_cache_store_and_hit(session: Session) -> None:
    """Stored result is returned on subsequent lookup."""
    cache = CacheProvider(session)
    original = ProviderResult(
        gtin="1234567890123",
        provider="openfoodfacts",
        name="Test Product",
        brand="Test Brand",
        category="Test Category",
    )
    cache.store(original)
    session.commit()

    async def _run() -> None:
        result = await cache.lookup("1234567890123")
        assert result is not None
        assert result.name == "Test Product"
        assert result.brand == "Test Brand"
        assert result.provider == "openfoodfacts"

    import asyncio

    asyncio.get_event_loop().run_until_complete(_run())


# ------------------------------------------------------------------ #
# ChainRunner                                                         #
# ------------------------------------------------------------------ #


@respx.mock
async def test_chain_returns_first_hit(session: Session) -> None:
    """ChainRunner stops at the first provider hit (OFF) and writes to cache."""
    gtin = "3017620422003"
    payload = _load("openfoodfacts_hit.json")
    respx.get(f"https://world.openfoodfacts.org/api/v2/product/{gtin}.json").mock(
        return_value=Response(200, json=payload)
    )

    chain = ChainRunner(session)
    result = await chain.run(gtin)

    assert result is not None
    assert result.provider == "openfoodfacts"
    assert result.name == "Nutella"

    # Verify written to cache
    cache = CacheProvider(session)
    cached = await cache.lookup(gtin)
    assert cached is not None
    assert cached.provider == "openfoodfacts"


@respx.mock
async def test_chain_cache_hit_skips_network(session: Session) -> None:
    """A pre-seeded cache entry is returned without any network provider being called."""
    gtin = "3017620422003"

    # Pre-seed the cache
    cache = CacheProvider(session)
    cache.store(
        ProviderResult(gtin=gtin, provider="openfoodfacts", name="Cached Nutella", brand="Nutella")
    )
    session.commit()

    # No network routes registered — if the chain hits the network, respx will raise
    chain = ChainRunner(session)
    result = await chain.run(gtin)

    assert result is not None
    assert result.name == "Cached Nutella"


@respx.mock
async def test_chain_all_miss_returns_none(session: Session) -> None:
    """ChainRunner returns None when every provider misses."""
    gtin = "0000000000000"

    # OFF miss
    respx.get(f"https://world.openfoodfacts.org/api/v2/product/{gtin}.json").mock(
        return_value=Response(200, json={"status": 0, "code": gtin})
    )
    # Open Library: not an ISBN — skipped automatically
    # OpenGTINdb: always None
    # UPCitemdb: 13-digit non-zero-prefixed — skipped
    chain = ChainRunner(session)
    result = await chain.run(gtin)
    assert result is None


async def test_chain_provider_timeout_returns_none(session: Session) -> None:
    """A provider that times out is swallowed and the chain continues."""
    import asyncio

    async def _slow_lookup(_gtin: str) -> ProviderResult | None:
        await asyncio.sleep(10)  # will be cancelled by wait_for
        return None  # pragma: no cover

    class SlowProvider:
        name = "slow"

        async def lookup(self, gtin: str) -> ProviderResult | None:
            return await _slow_lookup(gtin)

    # Chain with only the slow provider and a tiny timeout
    chain = ChainRunner(session, provider_timeout=0.01, extra_providers=[SlowProvider()])
    # Override built-in providers with empty list for this test
    chain._network_providers = [SlowProvider()]

    result = await chain.run("1234567890123")
    assert result is None
