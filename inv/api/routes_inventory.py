"""Inventory view routes.

Covers:
  GET /inventory — per-item on-hand quantities across all locations,
                   with last-movement timestamp and optional filters.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from inv.api.deps import get_session
from inv.web import templates

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("", response_class=HTMLResponse)
async def get_inventory(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
) -> HTMLResponse:
    """Render the inventory on-hand view.

    Queries the ``inventory_view`` SQL VIEW (created by the baseline
    migration) and joins item + location names. Only rows where
    ``on_hand > 0`` are returned — fully depleted items are not shown
    here (they remain visible on ``/items`` and in the CSV export).
    The last movement timestamp is fetched per item/location pair.
    """
    rows = session.execute(
        text("""
            SELECT
                i.id        AS item_id,
                i.gtin      AS gtin,
                i.name      AS name,
                i.brand     AS brand,
                i.needs_review AS needs_review,
                l.id        AS location_id,
                l.name      AS location_name,
                v.on_hand   AS on_hand,
                (
                    SELECT MAX(m.created_at)
                    FROM movement m
                    WHERE m.item_id = v.item_id
                      AND m.location_id = v.location_id
                ) AS last_movement_at
            FROM inventory_view v
            JOIN item     i ON i.id = v.item_id
            JOIN location l ON l.id = v.location_id
            WHERE v.on_hand > 0
            ORDER BY l.name, i.name NULLS LAST, i.gtin
        """)
    ).mappings().all()

    return templates.TemplateResponse(
        request,
        "inventory.html",
        {"rows": rows},
    )
