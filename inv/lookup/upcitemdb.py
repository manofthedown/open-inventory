"""UPCitemdb provider (free trial tier).

Covers broad consumer goods as a final network fallback. No auth required
on the free tier, but the API is rate-limited (~100 lookups/day by IP).
API: https://api.upcitemdb.com/prod/trial/lookup?upc=<upc>

The free tier only accepts 12-digit UPC-A codes (no EAN-13 with a leading
zero, no GTIN-14). GTINs that don't meet this constraint are skipped to
avoid a guaranteed 400 response and wasted rate-limit quota.

Returns ``None`` on any miss or error — the chain continues uninterrupted.
"""

from __future__ import annotations

import logging

import httpx

from inv.lookup.base import ProviderResult

logger = logging.getLogger(__name__)

_API = "https://api.upcitemdb.com/prod/trial/lookup"


def _to_upc12(gtin: str) -> str | None:
    """Try to produce a 12-digit UPC-A from a GTIN string.

    - 12-digit input: use as-is.
    - 13-digit EAN-13 with leading zero: strip the leading zero.
    - Anything else: return None (not a valid UPC-A for this API).
    """
    if not gtin.isdigit():
        return None
    if len(gtin) == 12:
        return gtin
    if len(gtin) == 13 and gtin.startswith("0"):
        return gtin[1:]
    return None


class UPCitemdbProvider:
    """Look up UPC-A codes against the UPCitemdb free trial API."""

    name = "upcitemdb"

    async def lookup(self, gtin: str) -> ProviderResult | None:
        """Fetch product data from UPCitemdb; return None on miss or any error."""
        upc = _to_upc12(gtin)
        if upc is None:
            return None

        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(_API, params={"upc": upc}, follow_redirects=True)
                if resp.status_code == 429:
                    # Rate-limit hit — log distinctly so operators know why the
                    # chain fell through rather than silently treating it as a miss.
                    logger.warning(
                        "upcitemdb rate limit reached (HTTP 429) for UPC %s; "
                        "skipping provider. The free tier allows ~100 lookups/day per IP.",
                        upc,
                    )
                    return None
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError:
            return None
        except Exception:
            return None

        if data.get("code") != "OK":
            return None

        items = data.get("items", [])
        if not items:
            return None

        item = items[0]
        name = item.get("title") or None
        brand = item.get("brand") or None
        category = item.get("category") or None

        return ProviderResult(
            gtin=gtin,
            provider=self.name,
            name=name,
            brand=brand,
            category=category,
            raw=data,
        )
