"""Scan endpoint and related routes."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from inv.api.deps import get_session
from inv.core.packs import resolve_alias
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

    Processing order:
    1. Resolve pack alias — if the scanned GTIN is a registered case/inner
       barcode, rewrite to the canonical item GTIN and apply the alias
       multiplier (overriding the operator's qty_multiplier).
    2. Run the provider chain (cache → OFF → Open Library → OpenGTINdb →
       UPCitemdb) only for first-seen canonical GTINs.
    3. Call record_scan with the resolved GTIN, effective multiplier, and
       any lookup result.

    Returns an HTML partial for HTMX/fetch clients. Errors use standard
    HTTP status codes with JSON ``{"detail": "..."}`` bodies:

    - 404: Location not found
    - 409: Negative stock (OUT direction would drop below 0)
    - 422: Validation error (bad direction, empty GTIN, non-positive
           qty_multiplier, etc.) — emitted by Pydantic automatically.
    """
    # Step 1: pack alias resolution — rewrites GTIN + multiplier if matched.
    resolution = resolve_alias(session, req.gtin)
    effective_gtin = resolution.canonical_gtin
    effective_multiplier = (
        resolution.multiplier if resolution.was_alias else req.qty_multiplier
    )

    # Step 2: provider chain — only for first-seen canonical GTINs.
    from inv.storage.repositories import ItemRepository

    item_repo = ItemRepository(session)
    is_new_gtin = item_repo.get_by_gtin(effective_gtin) is None

    lookup_result = None
    attempted_providers: tuple[str, ...] = ()
    if is_new_gtin:
        chain = ChainRunner(session)
        chain_result = await chain.run(effective_gtin)
        lookup_result = chain_result.result
        attempted_providers = chain_result.attempted_providers

    # Step 3: record the movement.
    try:
        result = record_scan(
            session,
            gtin=effective_gtin,
            direction=req.direction,
            qty_multiplier=effective_multiplier,
            location_id=req.location_id,
            actor=req.actor,
            note=req.note,
            lookup_result=lookup_result,
            attempted_providers=attempted_providers,
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

    # Build human-readable message; note alias auto-multiply if applicable.
    verb = {"IN": "Scanned in", "OUT": "Scanned out", "ADJUST": "Adjusted"}[req.direction]
    item_label = result.item.name or result.item.gtin
    if resolution.was_alias:
        alias_tag = f" via {resolution.alias_label or 'alias'} ×{resolution.multiplier}"
    else:
        alias_tag = ""
    message = f"{verb} {effective_multiplier} × {item_label}{alias_tag}"

    context = {
        "item": result.item,
        "on_hand": result.on_hand,
        "direction": req.direction,
        "delta": result.delta,
        "message": message,
        "was_alias": resolution.was_alias,
    }
    return templates.TemplateResponse(request, "partials/scan_result.html", context)
