"""Scan endpoint and related routes."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from inv.api.deps import get_session
from inv.core.services import (
    LocationNotFoundError,
    NegativeStockError,
    record_scan,
)
from inv.lookup.chain import ChainRunner
from inv.web import templates

router = APIRouter(prefix="", tags=["scan"])


class ScanRequest(BaseModel):
    """Request body for POST /scan.

    Validation rules:
    - ``gtin`` must be between 6 and 14 characters (UPC-E up to GTIN-14).
      Non-digit content is allowed at this layer so future barcode
      symbologies (Code 128, ISBN-X) can pass through; strict GTIN-13
      check-digit validation is a separate concern.
    - ``direction`` is a strict enum — invalid values are rejected by
      Pydantic with a 422 instead of falling through to the DB's CHECK
      constraint.
    - ``qty_multiplier`` must be positive. Down-adjustments are a V2
      concern handled with signed-ADJUST tooling.
    """

    gtin: str = Field(..., min_length=6, max_length=14)
    direction: Literal["IN", "OUT", "ADJUST"] = "IN"
    qty_multiplier: int = Field(default=1, ge=1)
    location_id: int = Field(default=1, ge=1)
    actor: str | None = Field(default=None, max_length=255)
    note: str | None = Field(default=None, max_length=2000)


@router.get("/scan", response_class=HTMLResponse, tags=["web"])
async def get_scan_page(request: Request) -> HTMLResponse:
    """Render the scan page."""
    return templates.TemplateResponse(request, "scan.html", {})


@router.post("/scan", response_class=HTMLResponse)
async def post_scan(
    req: ScanRequest,
    session: Annotated[Session, Depends(get_session)],
    request: Request,
) -> HTMLResponse:
    """Record a barcode scan and update inventory.

    On first sight of a GTIN the lookup chain runs (cache → OFF →
    Open Library → OpenGTINdb → UPCitemdb). A hit enriches the item
    stub in the same transaction; a miss leaves it flagged
    ``needs_review=True``.

    Returns an HTML partial for HTMX/fetch clients. Errors use standard
    HTTP status codes with JSON ``{"detail": "..."}`` bodies:

    - 404: Location not found
    - 409: Negative stock (OUT direction would drop below 0)
    - 422: Validation error (bad direction, empty GTIN, non-positive
           qty_multiplier, etc.) — emitted by Pydantic automatically.
    """
    # Run the provider chain only for first-seen GTINs. We peek at the
    # DB first; if the item already exists we skip the network round-trip
    # entirely (the chain would just hit the cache anyway, but this is
    # cheaper and keeps the fast path fast).
    from inv.storage.repositories import ItemRepository

    item_repo = ItemRepository(session)
    is_new_gtin = item_repo.get_by_gtin(req.gtin) is None

    lookup_result = None
    if is_new_gtin:
        chain = ChainRunner(session)
        lookup_result = await chain.run(req.gtin)

    try:
        result = record_scan(
            session,
            gtin=req.gtin,
            direction=req.direction,
            qty_multiplier=req.qty_multiplier,
            location_id=req.location_id,
            actor=req.actor,
            note=req.note,
            lookup_result=lookup_result,
        )
    except LocationNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Location {e.location_id} not found",
        ) from e
    except NegativeStockError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e

    # Construct human-readable message
    verb = {"IN": "Scanned in", "OUT": "Scanned out", "ADJUST": "Adjusted"}[req.direction]
    item_label = result.item.name or result.item.gtin
    message = f"{verb} {req.qty_multiplier} × {item_label}"

    context = {
        "item": result.item,
        "on_hand": result.on_hand,
        "direction": req.direction,
        "delta": result.delta,
        "message": message,
    }
    return templates.TemplateResponse(request, "partials/scan_result.html", context)
