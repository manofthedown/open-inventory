# Event Bus — open-inventory

Reference for the in-process `blinker` event bus used throughout
open-inventory.  Plugin authors and contributors subscribe to these signals
to react to domain events without modifying core code.

---

## Overview

The event bus is provided by [`blinker`](https://blinker.readthedocs.io/).
All signals are in-process — there is no network boundary, no
serialisation, and no message broker.  Signals are emitted **after** the
database transaction that caused them has been committed, so subscribers
see a consistent state.

All signal payloads are frozen dataclasses (immutable).  Do not mutate
them; create new objects if you need derived state.

---

## Signals

All signals are defined in `inv/core/events.py`.

### `movement_created`

```python
from inv.core.events import movement_created, MovementCreatedEvent
```

Fired after a `movement` row is committed.  This is the primary hook for
anything that needs to react to stock changes: reporting, central sync,
external webhooks, alerts.

**Payload:** `MovementCreatedEvent`

| Field | Type | Description |
|-------|------|-------------|
| `movement_id` | `int` | DB primary key of the new movement row |
| `item_id` | `int` | FK to `item` |
| `location_id` | `int` | FK to `location` |
| `delta` | `int` | Signed quantity in eaches (+IN, -OUT, ±ADJUST) |
| `direction` | `Literal["IN", "OUT", "ADJUST"]` | Movement type |
| `actor` | `str \| None` | Who triggered the movement (future auth) |
| `created_at` | `datetime` | UTC timestamp of the committed row |

---

### `item_created`

```python
from inv.core.events import item_created, ItemCreatedEvent
```

Fired the **first time** an item row is created — from a scan stub, from a
provider hit, or from manual entry.  Not fired on subsequent enrichments
of the same item.

**Payload:** `ItemCreatedEvent`

| Field | Type | Description |
|-------|------|-------------|
| `item_id` | `int` | DB primary key |
| `gtin` | `str` | Barcode that triggered the creation |
| `source` | `str` | `"stub"`, `"openfoodfacts"`, `"manual"`, etc. |

---

### `item_enriched`

```python
from inv.core.events import item_enriched, ItemEnrichedEvent
```

Fired when an item's metadata is updated by a provider or manually via the
enrichment form.  Useful for cache invalidation or re-indexing.

**Payload:** `ItemEnrichedEvent`

| Field | Type | Description |
|-------|------|-------------|
| `item_id` | `int` | DB primary key |
| `provider` | `str` | `"openfoodfacts"`, `"manual"`, etc. |
| `fields_filled` | `tuple[str, ...]` | Names of fields that were set (e.g. `("name", "brand")`) |

---

### `scan_unknown`

```python
from inv.core.events import scan_unknown, ScanUnknownEvent
```

Fired when a scan's GTIN misses every provider in the lookup chain and the
item is created as a `needs_review` stub.  The manual enrichment queue
(`/items?filter=needs_review`) is populated by items that triggered this
event.

**Payload:** `ScanUnknownEvent`

| Field | Type | Description |
|-------|------|-------------|
| `gtin` | `str` | The unrecognised barcode |
| `attempted_providers` | `tuple[str, ...]` | Names of all providers that were tried |

---

## Subscribing to a Signal

```python
from inv.core.events import movement_created, MovementCreatedEvent

def on_movement(sender: object, event: MovementCreatedEvent) -> None:
    print(f"Stock change: item={event.item_id} delta={event.delta:+d}")

# Connect once at application startup (e.g. in a FastAPI lifespan handler)
movement_created.connect(on_movement)

# Disconnect when no longer needed (e.g. in tests)
movement_created.disconnect(on_movement)
```

Blinker signals are synchronous — the subscriber runs in the same thread
as the emitter.  Keep subscribers fast; offload heavy work to a background
thread or task queue.

---

## Signal Timing Guarantee

All signals in open-inventory are emitted **after the database transaction
is committed** (`session.commit()` then `signal.send()`).  This means:

- Subscribers that query the database will see the new state.
- If the process crashes between `commit()` and `send()`, the signal is
  lost.  Subscribers must be idempotent and tolerate missed events.

---

## Adding a New Signal

1. Define the payload dataclass in `inv/core/events.py` (use `@dataclass(frozen=True)`).
2. Define the signal: `my_signal = signal("my.signal")`.
3. Emit after commit in the relevant service function.
4. Add to `__all__`.
5. Document it here.
