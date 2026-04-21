"""Items routes — list, detail, enrichment form, and pack alias CRUD.

Covers:
  GET  /items                          — item list, optional ?filter=needs_review
  GET  /items/{id}/enrich              — render enrichment form (with alias list)
  POST /items/{id}/enrich              — submit enrichment; clears needs_review
  POST /items/{id}/aliases             — add a pack alias
  POST /items/{id}/aliases/{gtin}/delete — remove a pack alias
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from inv.api.deps import get_session
from inv.core.services import enrich_item
from inv.storage.orm import Item
from inv.storage.repositories import AliasRepository, ItemRepository
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Item {item_id} not found")

    alias_repo = AliasRepository(session)
    aliases = alias_repo.list_for_item(item_id)

    return templates.TemplateResponse(
        request,
        "enrich_form.html",
        {"item": item, "aliases": aliases, "message": None},
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

    Redirects to /items on success (Post/Redirect/Get).
    """
    repo = ItemRepository(session)
    if repo.get_by_id(item_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Item {item_id} not found")

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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e

    return RedirectResponse(url="/items", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{item_id}/aliases")
async def add_alias(
    item_id: int,
    session: Annotated[Session, Depends(get_session)],
    alias_gtin: Annotated[str, Form(min_length=6, max_length=14)],
    multiplier: Annotated[int, Form(ge=2, le=10000)],
    label: Annotated[str, Form(max_length=100)] = "",
) -> RedirectResponse:
    """Register a new pack alias for an item.

    The alias GTIN must not already exist (either as an item GTIN or
    another alias). Redirects back to the enrichment form on success.
    """
    repo = ItemRepository(session)
    if repo.get_by_id(item_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Item {item_id} not found")

    alias_repo = AliasRepository(session)

    # Guard: alias GTIN must not conflict with an existing item GTIN
    if repo.get_by_gtin(alias_gtin) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"GTIN {alias_gtin} already exists as a canonical item",
        )
    # Guard: alias GTIN must not already be registered
    if alias_repo.get_by_gtin(alias_gtin) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Alias GTIN {alias_gtin} is already registered",
        )

    alias_repo.create(
        gtin=alias_gtin,
        item_id=item_id,
        multiplier=multiplier,
        label=label.strip() or None,
    )
    session.commit()

    return RedirectResponse(
        url=f"/items/{item_id}/enrich", status_code=status.HTTP_303_SEE_OTHER
    )


@router.post("/{item_id}/aliases/{alias_gtin}/delete")
async def delete_alias(
    item_id: int,
    alias_gtin: str,
    session: Annotated[Session, Depends(get_session)],
) -> RedirectResponse:
    """Delete a pack alias. Redirects back to the enrichment form."""
    repo = ItemRepository(session)
    if repo.get_by_id(item_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Item {item_id} not found")

    alias_repo = AliasRepository(session)
    if not alias_repo.delete(alias_gtin):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alias {alias_gtin} not found",
        )
    session.commit()

    return RedirectResponse(
        url=f"/items/{item_id}/enrich", status_code=status.HTTP_303_SEE_OTHER
    )
