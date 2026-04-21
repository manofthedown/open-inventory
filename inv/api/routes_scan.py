"""Scan endpoint and related routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette.templating import _TemplateResponse

from inv.api.deps import get_session
from inv.core.services import (
    LocationNotFoundError,
    NegativeStockError,
    record_scan,
)
from inv.web import templates

router = APIRouter(prefix="", tags=["scan"])


class ScanRequest(BaseModel):
    """Request body for POST /scan."""

    gtin: str
    direction: str = "IN"  # IN, OUT, ADJUST
    qty_multiplier: int = 1
    location_id: int = 1
    actor: str | None = None
    note: str | None = None


class ScanResponseItem(BaseModel):
    """Item details in scan response."""

    id: int
    gtin: str
    name: str | None
    brand: str | None
    on_hand: int


class ScanResponse(BaseModel):
    """Response body for POST /scan."""

    success: bool
    item: ScanResponseItem
    on_hand: int
    direction: str
    message: str


@router.get("/scan", response_class=HTMLResponse, tags=["web"])
async def get_scan_page(request: Request) -> _TemplateResponse:
    """Render the scan page."""
    return templates.TemplateResponse(request, "scan.html", {})


@router.post("/scan", response_class=HTMLResponse)
async def post_scan(
    req: ScanRequest,
    session: Annotated[Session, Depends(get_session)],
    request: Request,
) -> _TemplateResponse:
    """Record a barcode scan and update inventory.

    When called with `Accept: application/json`, returns JSON (standard REST).
    When called with `Accept: text/html` (from HTMX), returns an HTML partial.

    JSON Request body:
    ```json
    {
        "gtin": "5000112139107",
        "direction": "IN",
        "qty_multiplier": 1,
        "location_id": 1
    }
    ```

    JSON Response:
    ```json
    {
        "success": true,
        "item": {
            "id": 1,
            "gtin": "5000112139107",
            "name": "Coke Classic",
            "brand": "Coca-Cola",
            "on_hand": 42
        },
        "on_hand": 42,
        "direction": "IN",
        "message": "Scanned in 1 × Coke Classic"
    }
    ```

    Errors:
    - 404: Location not found
    - 409: Negative stock (OUT direction would drop below 0)
    """
    try:
        result = record_scan(
            session,
            gtin=req.gtin,
            direction=req.direction,
            qty_multiplier=req.qty_multiplier,
            location_id=req.location_id,
            actor=req.actor,
            note=req.note,
        )
    except LocationNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Location {e.location_id} not found",
        )
    except NegativeStockError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

    # Construct human-readable message
    verb = (
        "scanned in"
        if req.direction == "IN"
        else "scanned out"
        if req.direction == "OUT"
        else "adjusted"
    )
    item_label = result.item.name or result.item.gtin
    message = f"{verb.title()} {req.qty_multiplier} × {item_label}"

    # Return HTML partial for HTMX clients
    context = {
        "item": result.item,
        "on_hand": result.on_hand,
        "direction": req.direction,
        "delta": result.delta,
        "message": message,
    }
    return templates.TemplateResponse(request, "partials/scan_result.html", context)
