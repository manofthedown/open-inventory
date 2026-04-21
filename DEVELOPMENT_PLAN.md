# open-inventory — Development Plan (V1)

> A lightweight, modular, offline-first barcode scan-in / scan-out inventory system for mutual aid, emergency management, indie providers, and other small-scale ad-hoc distribution efforts.

---

## 1. Project Intent

**What it is:** a minimalist inventory program that captures USB barcode scans and records units in/out of stock. On first-ever scan of a given barcode, the system auto-fills basic product information from public open data sources.

**What it is NOT:** a WMS, TMS, ERP, or full retail POS. No slotting, picking, routing, rate shopping, or complex workflows.

**Design pillars:**
1. **Minimalist but modular** — small, focused core with clean seams so new capabilities (reporting, multi-location transfers, donor tracking, label printing, central sync, etc.) can bolt on without touching core.
2. **Offline-first** — everything works without internet; network is only used to enrich never-before-seen barcodes, with a persistent local cache.
3. **Low operational cost** — runs happily on a cheap laptop, an Arch desktop, or a Raspberry Pi.
4. **Use existing OSS** — don't reinvent. Rely on mature, permissive-licensed libraries.
5. **Cross-platform from day one** — dev on Arch Linux; end users may run on Arch, any Linux, Raspberry Pi OS, macOS, or Windows.

---

## 2. Locked-In Technical Decisions

| Area | Decision |
|---|---|
| **Primary dev environment** | Arch Linux (native, not containerized) |
| **Dev package manager** | `uv` (installed via `pacman -S uv`; cross-platform for other contributors) |
| **Backend language** | Python 3.11+ |
| **Web framework** | FastAPI + Uvicorn |
| **Frontend** | Jinja2 templates + HTMX + Alpine.js + Pico.css (no build step, no bundler, no Node) |
| **Database** | SQLite (WAL mode), SQLAlchemy 2.x ORM, Alembic migrations |
| **HTTP client (for provider calls)** | `httpx` (async, with retries) |
| **Settings** | `pydantic-settings` (env + TOML) |
| **Event bus** | `blinker` (in-process signals) |
| **Paths (all OS)** | `platformdirs` |
| **Logging** | `structlog` |
| **Tests / lint / types** | `pytest`, `pytest-asyncio`, `ruff`, `mypy` |
| **License** | AGPL-3.0 |
| **Deployment (V1)** | `pipx install inventory` (primary) + Docker image (secondary escape hatch) |
| **Linux service unit** | `systemd --user` unit |
| **Auth** | None in V1 (pluggable slot reserved) |

**Deferred to V2+:** lot/expiry tracking, camera/mobile scanning, multi-location transfers, external webhooks, label printing, central sync.

---

## 3. Target User Experience (V1)

**Primary flow — scan-in:**
1. Operator opens `http://127.0.0.1:8765/scan` in a browser on the host machine.
2. A USB barcode scanner (HID keyboard-wedge; no drivers needed) is plugged in.
3. Cursor is auto-focused on the scan input. Mode selector shows `[ Each (×1) | Case | Cluster | Custom ×N ]`.
4. Operator squeezes the scanner trigger. The scanner "types" the GTIN followed by Enter.
5. HTMX posts `POST /scan` with `{gtin, direction: IN, qty_multiplier, location}`.
6. Server:
   - Looks up item in local DB → miss? runs provider chain (Open Food Facts → Open Library → OpenGTINdb → UPCitemdb) → cache + create item (or stub flagged `needs_review` if all providers miss).
   - Inserts a `movement` record.
   - Returns an HTMX partial: item name, brand, current on-hand, last-action toast.
7. Input re-focuses automatically. Operator immediately scans the next item.

**Scan-out flow:** identical, but `direction=OUT`. Scan-out is **rejected** if it would drop on-hand below zero (operator must record an `ADJUST` movement to reconcile).

**Casepack / clusterpack handling:**
- `item.pack_size` stores default eaches-per-pack.
- `pack_alias` table maps alternate GTINs (inner, carton, case) → canonical item + multiplier.
- Scanning a case barcode that matches a `pack_alias` auto-multiplies without operator input.
- Otherwise, the UI mode selector (`Each | Case | Cluster | Custom`) supplies the multiplier.
- **All storage math is in eaches.** Packs are purely scan-time multipliers.

**Manual enrichment:** items flagged `needs_review` appear in a queue at `/items?filter=needs_review`. A single-page form edits name/brand/category/pack_size and clears the flag.

**Export:** `GET /export/items.csv` and `GET /export/movements.csv`.

---

## 4. Barcode Data Lookup Chain

Implemented as a `ProductLookupProvider` protocol. Each provider is a separate module; the chain is ordered and stops at the first successful lookup. All successful lookups write through to `product_cache`.

| Order | Provider | Coverage | Auth | Notes |
|---|---|---|---|---|
| 0 | Local cache (`product_cache`) | anything scanned before | none | always first |
| 1 | **Open Food Facts** | food & consumables | none | `world.openfoodfacts.org/api/v2/product/<gtin>.json` |
| 2 | **Open Library** | ISBN-10/13 books/media | none | `openlibrary.org/api/books?bibkeys=ISBN:<isbn>&format=json&jscmd=data` |
| 3 | **OpenGTINdb** | community GTIN data | none | fallback for general goods |
| 4 | **UPCitemdb (free tier)** | broad consumer goods | none, rate-limited | final network fallback |
| 5 | Manual enrichment | anything else | n/a | stub item flagged `needs_review` |

Provider timeouts are short (default 3s) and failures are swallowed into the chain — offline operation is always valid.

---

## 5. Data Model

Event-sourced: `movement` is the source of truth; quantities are derived.

```sql
item
  id INTEGER PK
  gtin TEXT UNIQUE NOT NULL
  name TEXT
  brand TEXT
  category TEXT
  uom TEXT DEFAULT 'each'
  pack_size INTEGER DEFAULT 1
  parent_item_id INTEGER NULL REFERENCES item(id)
  metadata JSON
  source TEXT              -- which provider filled it
  needs_review BOOLEAN DEFAULT 0
  created_at, updated_at

pack_alias
  gtin TEXT PK
  item_id INTEGER FK item(id)
  multiplier INTEGER NOT NULL
  label TEXT               -- e.g. "case-12", "inner-6"

location
  id INTEGER PK
  name TEXT UNIQUE
  notes TEXT

movement                    -- append-only, event log
  id INTEGER PK
  item_id INTEGER FK
  location_id INTEGER FK
  delta INTEGER NOT NULL   -- signed eaches
  direction TEXT CHECK (direction IN ('IN','OUT','ADJUST'))
  actor TEXT NULL
  note TEXT NULL
  created_at TIMESTAMP

product_cache
  gtin TEXT PK
  payload JSON NOT NULL
  provider TEXT NOT NULL
  fetched_at TIMESTAMP

inventory_view (SQL VIEW)
  SELECT item_id, location_id, SUM(delta) AS on_hand
  FROM movement GROUP BY item_id, location_id;
```

Seed data: one default location named `"Main"`.

---

## 6. Module Architecture

```
inv/
├── core/          # Domain models (Pydantic), service layer, event bus
├── storage/       # SQLAlchemy engine, session, repositories
├── scan/          # ScannerInput protocol; V1 implementation = HTML-focused HID wedge
├── lookup/        # ProductLookupProvider protocol + chain + cache + per-provider modules
├── api/           # FastAPI routers (scan, items, inventory, export)
└── web/           # Jinja templates, HTMX partials, static assets
```

**Modularity mechanisms (how V2 modules bolt on):**
1. **Protocols/ABCs** for `ProductLookupProvider`, `ScannerInput`, and repositories. Adding a new provider = new file + register in chain.
2. **In-process event bus** with stable signal payloads:
   - `movement.created` → `{movement_id, item_id, location_id, delta, direction, actor, created_at}`
   - `item.created` → `{item_id, gtin, source}`
   - `item.enriched` → `{item_id, provider, fields_filled}`
   - `scan.unknown` → `{gtin, attempted_providers}`
   V1 core never imports plugin modules; plugins subscribe.
3. **Router plugin registry** in `main.py` — new modules append a FastAPI router.
4. **Pluggable settings sections** via `pydantic-settings` so modules declare their own config.
5. **Feature flags** in settings to toggle deferred modules on when they land.

---

## 7. Home File Structure (ground truth for the coder)

```
open-inventory/
├── README.md
├── DEVELOPMENT_PLAN.md           # ← this file; coder's north star
├── LICENSE                       # AGPL-3.0
├── CONTRIBUTING.md
├── CHANGELOG.md
├── pyproject.toml                # uv/pip metadata, ruff + mypy + pytest config
├── uv.lock                       # cross-platform lockfile
├── .python-version               # 3.11
├── .gitignore
├── .pre-commit-config.yaml
├── Makefile                      # shortcuts: make dev, make test, make lint, make run
│
├── .github/
│   └── workflows/
│       ├── ci.yml                # matrix: {ubuntu, macos, windows} x {3.11, 3.12}
│       ├── ci-arm.yml            # ARM64 job for Pi parity
│       └── release.yml           # build+publish wheel/sdist to PyPI, Docker to GHCR
│
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 0001_initial.py
│
├── inv/                          # application package (installable)
│   ├── __init__.py
│   ├── __main__.py               # `python -m inv`
│   ├── cli.py                    # click/typer entrypoints: init, run, backup, export
│   ├── main.py                   # FastAPI app factory + module/router registry
│   ├── settings.py               # pydantic-settings; paths via platformdirs
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── models.py             # Pydantic domain models
│   │   ├── services.py           # record_scan(), resolve_item(), enrich_item()
│   │   ├── packs.py              # pack/alias resolution + multiplier math
│   │   └── events.py             # blinker signals + payload schemas
│   │
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── db.py                 # engine, session, WAL pragma
│   │   ├── orm.py                # SQLAlchemy 2.x declarative models
│   │   └── repositories.py       # ItemRepo, MovementRepo, LocationRepo, CacheRepo, AliasRepo
│   │
│   ├── scan/
│   │   ├── __init__.py
│   │   ├── base.py               # ScannerInput protocol
│   │   └── hid.py                # V1 HID wedge (via HTML input)
│   │
│   ├── lookup/
│   │   ├── __init__.py
│   │   ├── base.py               # ProductLookupProvider protocol + ProviderResult
│   │   ├── chain.py              # ordered chain runner
│   │   ├── cache.py              # local SQLite provider cache wrapper
│   │   ├── openfoodfacts.py
│   │   ├── openlibrary.py
│   │   ├── opengtindb.py
│   │   └── upcitemdb.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py               # DI helpers (session, repos, settings)
│   │   ├── routes_scan.py        # POST /scan, POST /scan/out
│   │   ├── routes_items.py       # list, detail, enrich
│   │   ├── routes_inventory.py   # on-hand views
│   │   ├── routes_export.py      # CSV export endpoints
│   │   └── routes_health.py      # /health, /version
│   │
│   └── web/
│       ├── __init__.py
│       ├── templates/
│       │   ├── base.html
│       │   ├── scan.html         # main scan screen
│       │   ├── items_list.html
│       │   ├── item_detail.html
│       │   ├── enrich_form.html
│       │   ├── inventory.html
│       │   └── partials/
│       │       ├── scan_result.html
│       │       ├── item_row.html
│       │       └── toast.html
│       └── static/
│           ├── css/pico.min.css
│           ├── js/htmx.min.js
│           ├── js/alpine.min.js
│           └── js/scan_focus.js   # keeps the scan input focused
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── fixtures/
│   │   └── providers/             # recorded JSON responses for respx
│   ├── unit/
│   │   ├── test_packs.py
│   │   ├── test_services.py
│   │   ├── test_repositories.py
│   │   └── test_chain.py
│   ├── integration/
│   │   ├── test_scan_flow.py      # TestClient end-to-end
│   │   ├── test_enrich_flow.py
│   │   └── test_export.py
│   └── smoke/
│       └── test_hid_input.py      # optional Playwright keystroke test
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── QUICKSTART_ARCH.md
│   ├── QUICKSTART_PI.md
│   ├── QUICKSTART_MACOS.md
│   ├── QUICKSTART_WINDOWS.md
│   ├── QUICKSTART_DOCKER.md       # beginner-friendly Docker walkthrough
│   ├── SCANNERS.md                # tested scanner models, troubleshooting
│   ├── PROVIDERS.md               # how to add a ProductLookupProvider
│   └── EVENTS.md                  # event bus contract for plugin authors
│
└── deploy/
    ├── linux/
    │   ├── inventory.service       # systemd --user unit template
    │   └── install.sh              # idempotent user-space setup
    ├── macos/
    │   ├── com.inventory.plist     # launchd user agent
    │   └── install.sh
    ├── windows/
    │   ├── install-task.ps1        # Task Scheduler on login
    │   └── nssm-install.md
    ├── arch/
    │   └── PKGBUILD                # stretch goal (AUR)
    └── docker/
        ├── Dockerfile
        ├── compose.yml
        └── README.md               # full beginner walkthrough
```

---

## 8. Cross-Platform Compatibility Rules

Hard rules for the coder to follow throughout V1:

1. **No OS-specific paths in source.** All filesystem paths resolve through `platformdirs` helpers in `inv/settings.py`:
   - Config → `user_config_dir("inventory")`
   - Data (SQLite DB) → `user_data_dir("inventory")`
   - Cache → `user_cache_dir("inventory")`
   - Logs → `user_log_dir("inventory")`
2. **No shell scripts in the hot path.** Every user-facing action is a Python entrypoint (`inventory init`, `inventory run`, `inventory backup`, `inventory export`). Platform-specific scripts live only under `deploy/<os>/` and are optional conveniences.
3. **Dependencies:** only packages that publish wheels for Linux, macOS, Windows on Python 3.11+. No packages requiring C compilation on the user's machine.
4. **No case-sensitive filename collisions.** No `:`, `?`, `*`, `|`, `<`, `>` in filenames. Always `\n` line endings in templates; let Jinja render.
5. **Default bind address:** `127.0.0.1:8765`. Opt-in to LAN via `--host 0.0.0.0`.
6. **CI matrix (required to be green before merge):** `{ubuntu-latest, macos-latest, windows-latest} × {python 3.11, 3.12}` running `uv sync --frozen && uv run pytest && uv run ruff check && uv run mypy inv`. One additional `ubuntu-22.04-arm` (or QEMU) job for Pi parity.

---

## 9. Milestones

### M1 — Skeleton (est. 1–2 days)
- `uv`-initialized repo, `pyproject.toml`, `uv.lock`, `.python-version`, `Makefile`.
- FastAPI app factory with `/health`.
- SQLite engine + Alembic baseline migration creating all tables above.
- `platformdirs` paths wired through `inv/settings.py`.
- `inventory init` / `inventory run` CLI entrypoints.
- CI matrix green on 3 OSes.
- Base Jinja template with Pico.css, HTMX, Alpine all vendored locally.

**Exit criteria:** `pipx install -e .` on Arch → `inventory init && inventory run` → `/health` returns 200; `pytest` passes; CI matrix green.

### M2 — Scan Loop (est. 2 days)
- `POST /scan` endpoint with `{gtin, direction, qty_multiplier, location_id}`.
- `record_scan()` service: upsert item stub if unknown, insert movement, emit `movement.created`.
- HTMX scan screen at `/scan`: mode selector, autofocus input, last-scan partial, toast, running on-hand.
- Negative-stock guard on OUT.
- USB HID scanner verified end-to-end on Arch (any cheap Symcode/Eyoyo style).

**Exit criteria:** scanning a known-to-the-DB barcode increments/decrements on-hand; focus stays on input; attempting to over-scan-out returns a clear error.

### M3 — Lookup Chain (est. 3 days)
- `ProductLookupProvider` protocol + `ProviderResult` dataclass.
- Implementations: `openfoodfacts`, `openlibrary`, `opengtindb`, `upcitemdb`.
- `ChainRunner` with ordered fallback and per-provider timeout.
- `product_cache` read-through wrapper.
- On unknown GTIN: create stub item with `needs_review=True`, emit `scan.unknown`.
- Manual enrichment form at `/items/{id}/enrich`.
- `respx`-based recorded fixtures for all four providers; offline test mode.

**Exit criteria:** first-ever scan of a real food barcode fills name/brand from OFF; first-ever ISBN scan fills title/author from Open Library; offline operation still records movements and flags `needs_review`.

### M4 — Casepacks, Inventory Views, Export (est. 2 days)
- `pack_alias` CRUD in the enrichment form.
- UI mode selector multiplier logic.
- Auto-multiplier when a scanned GTIN matches a `pack_alias`.
- `/inventory` page: per-item on-hand, last movement, filters.
- `GET /export/items.csv`, `GET /export/movements.csv`.

**Exit criteria:** scanning a case barcode for a known alias adds the multiplied eaches in one scan; CSV exports open cleanly in a spreadsheet.

### M5 — Packaging & Cross-Platform Docs (est. 2 days)
- `pipx install .` validated on Arch and at least one other OS (macOS or Windows).
- `deploy/linux/inventory.service` + `deploy/linux/install.sh` (`systemd --user`).
- `deploy/macos/com.inventory.plist` + install script.
- `deploy/windows/install-task.ps1` + docs.
- `deploy/docker/Dockerfile`, `compose.yml`, and the beginner walkthrough at `deploy/docker/README.md`.
- README with per-OS quickstart links.
- Release workflow: wheel/sdist to PyPI, multi-arch image to GHCR.

**Exit criteria:** fresh Arch user can run 4 commands and have a running service; fresh macOS/Windows user can run `pipx install inventory && inventory run` and open the scan page; Docker user can run `docker compose up -d`.

---

## 10. Dev Workflow on Arch

```bash
# one-time
sudo pacman -S --needed uv git
git clone git@github.com:manofthedown/open-inventory.git
cd open-inventory

# daily
uv sync                          # creates .venv, installs from uv.lock
uv run inventory init            # creates DB + config in XDG paths
uv run inventory run --reload    # dev server at http://127.0.0.1:8765
uv run pytest                    # full suite
uv run ruff check                # lint
uv run mypy inv                  # types
```

---

## 11. Risk Register

| Risk | Mitigation |
|---|---|
| OFF / UPCitemdb rate limits or downtime | Local cache + ordered chain + manual enrichment fallback |
| Barcode misreads from cheap scanners | Log raw scanner input; show last 5 scans with undo |
| SQLite concurrent writers | WAL mode; single writer path in service layer; fine for LAN-scale |
| AGPL-3.0 contributor friction | Documented in CONTRIBUTING.md; acceptable given mutual-aid framing |
| Windows focus-stealing interfering with HID scanner | `autofocus` + JS focus-refocus handler in `scan_focus.js` |
| macOS Gatekeeper on pipx-installed binaries | Not applicable to pipx (Python script); would become a concern only if we later ship a signed Tauri wrapper |

---

## 12. Deliverables at End of V1

1. PyPI-published package (`pipx install inventory`).
2. Working web UI covering `/scan`, `/inventory`, `/items`, `/items/<id>/enrich`, `/export`.
3. Provider chain (OFF + Open Library + OpenGTINdb + UPCitemdb) with local cache.
4. Casepack / clusterpack scanning with alias auto-multiplier.
5. CSV export.
6. `deploy/` units/scripts for Linux, macOS, Windows + Docker walkthrough.
7. `pytest` suite with recorded provider fixtures; CI green on 3 OSes + ARM.
8. `README.md`, `CONTRIBUTING.md`, `docs/` quickstarts, AGPL-3.0 `LICENSE`.

---

## 13. Out of Scope for V1 (Explicitly Deferred)

- Lot / expiry / FEFO tracking
- Camera / mobile scanning
- Multi-location transfer workflows
- Authentication & user roles
- External webhooks / integrations
- Label / receipt printing
- Reporting dashboards (CSV export only in V1)
- Central sync between instances

Each of these has an architectural slot reserved (event bus signals, provider interfaces, settings sections) so a V2 module can land without core changes.
