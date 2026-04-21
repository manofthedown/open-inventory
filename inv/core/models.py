"""Pydantic domain models."""

from datetime import datetime

from pydantic import BaseModel, Field


class Item(BaseModel):
    """Product item."""

    id: int | None = None
    gtin: str
    name: str | None = None
    brand: str | None = None
    category: str | None = None
    uom: str = "each"
    pack_size: int = 1
    parent_item_id: int | None = None
    metadata: dict | None = None
    source: str | None = None
    needs_review: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Location(BaseModel):
    """Storage location."""

    id: int | None = None
    name: str
    notes: str | None = None


class Movement(BaseModel):
    """Inventory movement (event log entry)."""

    id: int | None = None
    item_id: int
    location_id: int
    delta: int = Field(..., description="Signed quantity in eaches")
    direction: str = Field(..., description="IN, OUT, or ADJUST")
    actor: str | None = None
    note: str | None = None
    created_at: datetime | None = None


class PackAlias(BaseModel):
    """Pack/case alias mapping."""

    gtin: str
    item_id: int
    multiplier: int
    label: str | None = None


class ProductCache(BaseModel):
    """Cached product lookup result."""

    gtin: str
    payload: dict
    provider: str
    fetched_at: datetime | None = None
