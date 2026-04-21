"""Open Library provider.

Covers ISBN-10 and ISBN-13 barcodes (books and media). No auth required.
API: https://openlibrary.org/api/books?bibkeys=ISBN:<isbn>&format=json&jscmd=data

Only attempted when the GTIN looks like an ISBN (10 or 13 digits starting
with 978 or 979, or exactly 10 digits). If the GTIN doesn't look like an
ISBN we return None immediately to avoid unnecessary network hits.

Returns ``None`` on any miss or error — the chain continues uninterrupted.
"""

from __future__ import annotations

import httpx

from inv.lookup.base import ProviderResult

_ISBN13_PREFIXES = ("978", "979")


def _looks_like_isbn(gtin: str) -> bool:
    """Return True if the GTIN is plausibly an ISBN-10 or ISBN-13."""
    if not gtin.isdigit():
        return False
    if len(gtin) == 10:
        return True
    if len(gtin) == 13 and gtin[:3] in _ISBN13_PREFIXES:
        return True
    return False


class OpenLibraryProvider:
    """Look up ISBNs against the Open Library Books API."""

    name = "openlibrary"
    _base = "https://openlibrary.org/api/books"

    async def lookup(self, gtin: str) -> ProviderResult | None:
        """Fetch book data from Open Library; return None on miss or any error."""
        if not _looks_like_isbn(gtin):
            return None

        url = self._base
        params = {
            "bibkeys": f"ISBN:{gtin}",
            "format": "json",
            "jscmd": "data",
        }
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(url, params=params, follow_redirects=True)
                resp.raise_for_status()
                data = resp.json()
        except Exception:
            return None

        key = f"ISBN:{gtin}"
        if key not in data:
            return None

        book = data[key]
        title = book.get("title") or None

        # Authors is a list of {"name": "...", "url": "..."}
        authors_raw = book.get("authors", [])
        author: str | None = None
        if authors_raw:
            names = [a.get("name", "") for a in authors_raw if a.get("name")]
            author = ", ".join(names) if names else None

        # Publishers → brand equivalent for books
        publishers_raw = book.get("publishers", [])
        brand: str | None = None
        if publishers_raw:
            brand = publishers_raw[0].get("name") or None

        # Subjects → category
        subjects_raw = book.get("subjects", [])
        category: str | None = None
        if subjects_raw:
            category = subjects_raw[0].get("name") or None

        return ProviderResult(
            gtin=gtin,
            provider=self.name,
            name=title,
            brand=brand,
            category=category,
            author=author,
            raw=data,
        )
