"""In-process event bus signals and their payload schemas.

DEVELOPMENT_PLAN.md §6 locks the signal names and payload shapes down as
the plugin modularity contract. Core services emit these; plugin modules
subscribe without ever being imported by core. The signals use ``blinker``
(in-process pub/sub) so there is no serialization boundary to maintain.

Payload dataclasses are frozen so subscribers can stash them without
worrying about mutation from later code.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from blinker import signal

# ----------------------------------------------------------------------
# Signals
# ----------------------------------------------------------------------

#: Fired after a ``movement`` row is committed. Subscribers get a
#: :class:`MovementCreatedEvent`. Plugins (reporting, central-sync,
#: webhooks) hook here.
movement_created = signal("movement.created")

#: Fired the first time an item row is created (from a scan stub, from
#: the provider chain, or from manual entry). NOT fired on subsequent
#: upserts/enrichments of the same item.
item_created = signal("item.created")

#: Fired when an item is enriched by a provider or manually. Plugins
#: that cache or re-index products subscribe here.
item_enriched = signal("item.enriched")

#: Fired when a scan's GTIN misses every provider in the lookup chain
#: and ends up as a ``needs_review`` stub. M3's manual enrichment UX
#: populates its queue off this signal.
scan_unknown = signal("scan.unknown")


# ----------------------------------------------------------------------
# Payload schemas (frozen)
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class MovementCreatedEvent:
    """Payload for :data:`movement_created`."""

    movement_id: int
    item_id: int
    location_id: int
    delta: int
    direction: Literal["IN", "OUT", "ADJUST"]
    actor: str | None
    created_at: datetime


@dataclass(frozen=True)
class ItemCreatedEvent:
    """Payload for :data:`item_created`."""

    item_id: int
    gtin: str
    source: str  # "stub", "openfoodfacts", "manual", etc.


@dataclass(frozen=True)
class ItemEnrichedEvent:
    """Payload for :data:`item_enriched`."""

    item_id: int
    provider: str
    fields_filled: tuple[str, ...]


@dataclass(frozen=True)
class ScanUnknownEvent:
    """Payload for :data:`scan_unknown`."""

    gtin: str
    attempted_providers: tuple[str, ...]


__all__ = [
    "ItemCreatedEvent",
    "ItemEnrichedEvent",
    "MovementCreatedEvent",
    "ScanUnknownEvent",
    "item_created",
    "item_enriched",
    "movement_created",
    "scan_unknown",
]
