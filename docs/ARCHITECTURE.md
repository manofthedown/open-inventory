# Architecture — open-inventory

> **Status:** living document — updated as the codebase evolves.

---

## Overview

open-inventory is a single-process Python web application.  All components
run in the same process; there is no message queue, no separate worker, and
no external cache daemon.  The design is intentionally minimal so the system
runs on a Raspberry Pi with no infrastructure overhead.

```
Browser (HTMX + Alpine.js)
        │  HTTP (FastAPI / Uvicorn)
        ▼
┌────────────────────────────────────────────────┐
│  inv/api/          — FastAPI route handlers    │
│  inv/web/          — Jinja2 template rendering │
├────────────────────────────────────────────────┤
│  inv/core/         — domain services           │
│    services.py     — record_scan, resolve_item │
│    events.py       — blinker signals (pub/sub) │
│    packs.py        — casepack multiplier math  │
├────────────────────────────────────────────────┤
│  inv/lookup/       — product data chain        │
│    chain.py        — ordered provider runner   │
│    cache.py        — local SQLite cache wrap   │
│    openfoodfacts.py / openlibrary.py / …       │
├────────────────────────────────────────────────┤
│  inv/storage/      — SQLAlchemy 2.x ORM        │
│    orm.py          — Item, Movement, Location… │
│    repositories.py — data-access objects       │
│    migrations.py   — Alembic helper            │
└────────────────────────────────────────────────┘
        │  SQLite (WAL mode)
        ▼
  inventory.db  (~/.local/share/inventory/)
```

---

## Key Design Decisions

| Concern | Decision | Rationale |
|---------|----------|-----------|
| Database | SQLite (WAL mode) | Zero operational overhead; sufficient for single-operator use |
| ORM | SQLAlchemy 2.x | Type-safe, well-understood, Alembic migration support |
| Event bus | `blinker` (in-process) | No serialisation boundary; zero infra; plugins subscribe without touching core |
| HTTP client | `httpx` (async) | Supports async/await; clean timeout API per provider |
| Paths | `platformdirs` | Resolves XDG, `~/Library`, `%APPDATA%` correctly on all platforms |
| Frontend | Jinja2 + HTMX + Alpine.js | No build step, no Node; works offline |

---

## Data Flow — Scan Path

```
POST /scan (gtin, direction, qty_multiplier, location_id)
  │
  ├─ ItemRepo.get_by_gtin(gtin)
  │     hit  → skip chain
  │     miss → ChainRunner.lookup(gtin)
  │               0: ProductCache (local)
  │               1: OpenFoodFacts
  │               2: OpenLibrary
  │               3: OpenGTINdb
  │               4: UPCitemdb
  │             all miss → create needs_review stub
  │
  ├─ MovementRepo.create(item, location, delta, direction)
  │
  ├─ commit()
  │
  └─ emit movement_created signal
       └─ (plugins subscribe here — not used in V1 core)
```

---

## Module Map

```
inv/
├── __init__.py          version constant
├── __main__.py          python -m inv entry point
├── asgi.py              importable app for uvicorn --reload
├── cli.py               typer CLI: init, run, version
├── main.py              FastAPI app factory + router registry
├── settings.py          pydantic-settings + platformdirs paths
│
├── core/
│   ├── events.py        blinker signals and frozen payload dataclasses
│   ├── models.py        Pydantic domain models (not ORM)
│   ├── packs.py         casepack multiplier resolution
│   └── services.py      record_scan(), enrich_item(), resolve_alias()
│
├── storage/
│   ├── db.py            engine factory, WAL pragma, session helper
│   ├── migrations.py    Alembic upgrade_to_head() helper
│   ├── orm.py           SQLAlchemy 2.x declarative models
│   └── repositories.py  ItemRepo, MovementRepo, LocationRepo, etc.
│
├── lookup/
│   ├── base.py          ProductLookupProvider protocol + ProviderResult
│   ├── cache.py         SQLite-backed cache wrapper provider
│   ├── chain.py         ordered chain runner with per-provider timeout
│   ├── openfoodfacts.py
│   ├── openlibrary.py
│   ├── opengtindb.py
│   └── upcitemdb.py
│
├── scan/
│   ├── base.py          ScannerInput protocol (future extension point)
│   └── hid.py           HID wedge scanner notes (V1: handled via browser)
│
├── api/
│   ├── deps.py          FastAPI DI helpers (session, repos, settings)
│   ├── routes_scan.py   POST /scan
│   ├── routes_items.py  GET/POST /items, /items/{id}/enrich
│   ├── routes_inventory.py  GET /inventory
│   ├── routes_export.py     GET /export/items.csv, /export/movements.csv
│   └── routes_health.py     GET /health, /version
│
└── web/
    └── templates/       Jinja2 HTML templates
```

---

## Extension Points

New capabilities should hook in at these seams without modifying core:

- **New lookup provider** — implement `ProductLookupProvider`, register in `chain.py`. See `docs/PROVIDERS.md`.
- **New scanner input** — implement `ScannerInput` (stub in `inv/scan/base.py`). See `docs/SCANNERS.md`.
- **Plugin reactions** — subscribe to blinker signals from `inv/core/events.py`. See `docs/EVENTS.md`.

---

## What Is Deferred to V2+

- Lot / expiry tracking
- Camera / mobile scanning
- Multi-location transfers
- External webhooks (event bus signals are the hook point)
- Label printing
- Central sync / multi-device
- PKGBUILD / AUR packaging (Arch stretch goal — see `DEVELOPMENT_PLAN.md`)
