"""ASGI application entry point for Uvicorn reload mode.

This module provides an importable `app` object for Uvicorn to use when
reload is enabled. Uvicorn's reload feature spawns a new process and needs
an import string (e.g., "inv.asgi:app") rather than a live app object.

The actual app construction happens in inv.main.create_app(), which is
settings-aware and used by the CLI, tests, and this module.
"""

from inv.main import create_app
from inv.settings import get_settings

# Construct the app once at import time using default settings.
# This is used by Uvicorn in reload mode.
app = create_app(get_settings())

__all__ = ["app"]
