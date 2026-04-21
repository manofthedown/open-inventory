"""Health check and version endpoints.

These are intentionally thin — they live outside the database path so
they can be called by load-balancers, monitoring agents, and ``pipx``
post-install checks without any DB dependency.
"""

from __future__ import annotations

from fastapi import APIRouter

from inv import __version__

router = APIRouter(tags=["system"])


@router.get("/health")
async def health() -> dict:
    """Liveness probe. Returns 200 as long as the process is running."""
    return {"status": "ok", "version": __version__}


@router.get("/version")
async def version() -> dict:
    """Return the installed package version."""
    return {"version": __version__}
