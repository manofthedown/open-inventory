"""OpenGTINdb provider — stub (not implemented).

opengtindb.org does not offer a stable, publicly documented JSON API.
The endpoint tested during M3 development returns HTML rather than
structured data, making reliable programmatic access impossible without
screen-scraping — which is fragile and likely against their ToS.

This module exists to hold the slot in the provider chain as specified in
DEVELOPMENT_PLAN.md §4 (order 3). It always returns ``None``, so the
chain falls through to UPCitemdb. If a usable API becomes available this
stub can be replaced without touching any other file.
"""

from __future__ import annotations

from inv.lookup.base import ProviderResult


class OpenGTINdbProvider:
    """Placeholder provider for OpenGTINdb.

    Always returns ``None`` — see module docstring for why.
    """

    name = "opengtindb"

    async def lookup(self, gtin: str) -> ProviderResult | None:  # noqa: ARG002
        """Return None — OpenGTINdb has no usable public JSON API."""
        return None
