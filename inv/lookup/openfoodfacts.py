"""Open Food Facts provider.

Covers food and consumable products. No auth required.
API: https://world.openfoodfacts.org/api/v2/product/<gtin>.json

Returns ``None`` on any miss or error — the chain continues uninterrupted.
"""

from __future__ import annotations

import httpx

from inv.lookup.base import ProviderResult


class OpenFoodFactsProvider:
    """Look up GTINs against the Open Food Facts open database."""

    name = "openfoodfacts"
    _base = "https://world.openfoodfacts.org/api/v2/product"

    async def lookup(self, gtin: str) -> ProviderResult | None:
        """Fetch product data from OFF; return None on miss or any error."""
        url = f"{self._base}/{gtin}.json"
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(url, follow_redirects=True)
                resp.raise_for_status()
                data = resp.json()
        except Exception:
            return None

        # status==1 means found; status==0 means not found
        if data.get("status") != 1:
            return None

        product = data.get("product", {})
        name = product.get("product_name") or product.get("product_name_en") or None
        brand = product.get("brands") or None
        category = product.get("categories") or None

        # Normalise brand — OFF sometimes returns comma-separated multi-brand strings;
        # keep the first one only for the canonical field.
        if brand and "," in brand:
            brand = brand.split(",")[0].strip()

        return ProviderResult(
            gtin=gtin,
            provider=self.name,
            name=name,
            brand=brand,
            category=category,
            raw=data,
        )
