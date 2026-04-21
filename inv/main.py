"""FastAPI application factory and router registration."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from inv import __version__
from inv.settings import Settings


def create_app(settings: Settings) -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="open-inventory",
        version=__version__,
        description="Lightweight barcode scan-in/scan-out inventory system",
    )

    # CORS middleware (allows localhost frontend calls)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # V1 localhost only; tighten in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check endpoint
    @app.get("/health", tags=["system"])
    async def health() -> dict:
        """Health check endpoint."""
        return {"status": "ok", "version": __version__}

    @app.get("/version", tags=["system"])
    async def version() -> dict:
        """Version endpoint."""
        return {"version": __version__}

    @app.get("/", tags=["system"])
    async def root() -> RedirectResponse:
        """Redirect root to scan page."""
        return RedirectResponse(url="/scan")

    # TODO: Mount static files and templates in M2/M3
    # TODO: Register API routers (scan, items, inventory, export)

    return app
