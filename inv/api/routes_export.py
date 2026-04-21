"""CSV export routes.

Covers:
  GET /export/items.csv     — all items with current on-hand totals
  GET /export/movements.csv — full movement log (append-only event log)

Both endpoints stream a plain CSV response with appropriate headers so
browsers trigger a file download. No pagination — V1 is designed for
small-scale deployments where the full dataset fits in memory.
"""

from __future__ import annotations

import csv
import io
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from inv.api.deps import get_session

router = APIRouter(prefix="/export", tags=["export"])


def _csv_response(filename: str, headers: list[str], rows: list[tuple]) -> StreamingResponse:
    """Build a StreamingResponse containing a UTF-8 CSV with BOM.

    The BOM (``\ufeff``) ensures Excel opens the file correctly without
    a manual encoding step — important for mutual aid groups who will
    likely use spreadsheet software to review exports.
    """
    buf = io.StringIO()
    buf.write("\ufeff")  # UTF-8 BOM for Excel compatibility
    writer = csv.writer(buf)
    writer.writerow(headers)
    writer.writerows(rows)
    buf.seek(0)

    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/items.csv")
async def export_items(
    session: Annotated[Session, Depends(get_session)],
) -> StreamingResponse:
    """Export all items with their total on-hand (summed across all locations).

    Columns: id, gtin, name, brand, category, uom, pack_size, source,
             needs_review, on_hand_total, created_at, updated_at
    """
    results = session.execute(
        text("""
            SELECT
                i.id,
                i.gtin,
                i.name,
                i.brand,
                i.category,
                i.uom,
                i.pack_size,
                i.source,
                i.needs_review,
                COALESCE(SUM(v.on_hand), 0) AS on_hand_total,
                i.created_at,
                i.updated_at
            FROM item i
            LEFT JOIN inventory_view v ON v.item_id = i.id
            GROUP BY i.id
            ORDER BY i.id
        """)
    ).fetchall()

    headers = [
        "id", "gtin", "name", "brand", "category", "uom", "pack_size",
        "source", "needs_review", "on_hand_total", "created_at", "updated_at",
    ]
    return _csv_response("items.csv", headers, [tuple(r) for r in results])


@router.get("/movements.csv")
async def export_movements(
    session: Annotated[Session, Depends(get_session)],
) -> StreamingResponse:
    """Export the full movement log.

    Columns: id, item_id, item_gtin, item_name, location_id, location_name,
             delta, direction, actor, note, created_at
    """
    results = session.execute(
        text("""
            SELECT
                m.id,
                m.item_id,
                i.gtin      AS item_gtin,
                i.name      AS item_name,
                m.location_id,
                l.name      AS location_name,
                m.delta,
                m.direction,
                m.actor,
                m.note,
                m.created_at
            FROM movement m
            JOIN item     i ON i.id = m.item_id
            JOIN location l ON l.id = m.location_id
            ORDER BY m.id
        """)
    ).fetchall()

    headers = [
        "id", "item_id", "item_gtin", "item_name",
        "location_id", "location_name",
        "delta", "direction", "actor", "note", "created_at",
    ]
    return _csv_response("movements.csv", headers, [tuple(r) for r in results])
