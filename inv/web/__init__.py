"""Web layer: Jinja2 template environment and static-file mounting.

Centralising these helpers keeps ``inv/main.py`` small and gives M2/M3
routers a single import point for rendering partials.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

_WEB_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = _WEB_DIR / "templates"
STATIC_DIR = _WEB_DIR / "static"

# Shared template environment. Import as `from inv.web import templates`.
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def mount_static(app: FastAPI, *, path: str = "/static") -> None:
    """Mount the vendored static assets (HTMX, Alpine, Pico, scan_focus)."""
    app.mount(path, StaticFiles(directory=str(STATIC_DIR)), name="static")
