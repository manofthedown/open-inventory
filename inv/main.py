"""FastAPI application factory and router registration."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from inv import __version__
from inv.api.routes_scan import router as scan_router
from inv.settings import Settings
from inv.storage.db import init_engine
from inv.web import mount_static, templates


def create_app(settings: Settings) -> FastAPI:
    """Create and configure the FastAPI application.

    The settings and a single SQLAlchemy engine are stored on
    ``app.state`` so every request (and every test) shares the same
    connection pool and the same configuration. Tests that want a
    different DB construct a new app with fresh settings; nothing is
    read from the environment at request time.
    """
    app = FastAPI(
        title="open-inventory",
        version=__version__,
        description="Lightweight barcode scan-in/scan-out inventory system",
    )

    # Bind settings + engine on app state (DI reads from here).
    app.state.settings = settings
    app.state.engine = init_engine(settings)

    # CORS: V1 binds 127.0.0.1 only by default; loosen only on LAN deploys.
    # NOTE: allow_credentials=True with allow_origins=["*"] is rejected by
    # browsers per the CORS spec, so we keep origins explicit.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[f"http://{settings.host}:{settings.port}"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Serve vendored HTMX / Alpine / Pico from inv/web/static/.
    mount_static(app)

    @app.get("/health", tags=["system"])
    async def health() -> dict:
        """Health check endpoint."""
        return {"status": "ok", "version": __version__}

    @app.get("/version", tags=["system"])
    async def version() -> dict:
        """Version endpoint."""
        return {"version": __version__}

    @app.get("/", response_class=HTMLResponse, tags=["system"])
    async def index(request: Request) -> HTMLResponse:
        """Render the base template as the M1 landing page.

        M2 will replace this with the scan page. For now the page exists
        so that `/` is a valid entry point, static assets are exercised,
        and we don't 404 the user on first visit.
        """
        return templates.TemplateResponse(request, "base.html", {"version": __version__})

    # Register M2 routers
    app.include_router(scan_router)

    # TODO: Register API routers for M3/M4 (items, inventory, export)

    return app
