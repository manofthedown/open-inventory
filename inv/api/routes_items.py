"""Items routes — list, detail, and manual enrichment form.

Covers:
  GET  /items                — paginated item list, optional ?filter=needs_review
  GET  /items/{id}/enrich   — render the enrichment form
  POST /items/{id}/enrich   — submit enrichment; clears needs_review flag
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from inv.api.deps import get_session
from inv.core.services import enrich_item
from inv.storage.orm import Item
from inv.storage.repositories import ItemRepository
from inv.web import templates

router = APIRouter(prefix="/items", tags=["items"])


@router.get("", response_class=HTMLResponse)
async def list_items(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    filter: str | None = None,  # noqa: A002
) -> HTMLResponse:
    """List all items, with optional ``?filter=needs_review`` filter."""
    if filter == "needs_review":
        items: list[Item] = (
            session.query(Item).filter_by(needs_review=True).order_by(Item.created_at.desc()).all()
        )
    else:
        items = session.query(Item).order_by(Item.created_at.desc()).all()

    return templates.TemplateResponse(
        request,
        "items_list.html",
        {"items": items, "filter": filter},
    )


@router.get("/{item_id}/enrich", response_class=HTMLResponse)
async def get_enrich_form(
    item_id: int,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
) -> HTMLResponse:
    """Render the manual enrichment form for a single item."""
    repo = ItemRepository(session)
    item = repo.get_by_id(item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item {item_id} not found",
        )
    return templates.TemplateResponse(
        request,
        "enrich_form.html",
        {"item": item, "message": None},
    )


@router.post("/{item_id}/enrich")
async def post_enrich_form(
    item_id: int,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
    name: Annotated[str, Form()] = "",
    brand: Annotated[str, Form()] = "",
    category: Annotated[str, Form()] = "",
    note: Annotated[str, Form()] = "",
) -> RedirectResponse:
    """Submit enrichment data for an item and clear its needs_review flag.

    Redirects to the items list on success so a re-POST on refresh is
    avoided (Post/Redirect/Get pattern).
    """
    repo = ItemRepository(session)
    item = repo.get_by_id(item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item {item_id} not found",
        )

    try:
        enrich_item(
            session,
            item_id=item_id,
            name=name.strip() or None,
            brand=brand.strip() or None,
            category=category.strip() or None,
            note=note.strip() or None,
        )
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    return RedirectResponse(url="/items", status_code=status.HTTP_303_SEE_OTHER)
