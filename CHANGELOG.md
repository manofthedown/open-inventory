# Changelog

All notable changes to open-inventory are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Version numbers follow [Semantic Versioning](https://semver.org/).

---

## [Unreleased] — M5 Packaging & Cross-Platform Deployment

### Added
- Multi-stage `Dockerfile` (pinned uv, non-root `inv` user, XDG env vars,
  named volume at `/home/inv/.local/share/inventory/`)
- `deploy/docker/compose.yml` with persistent `inv-data` volume, localhost
  port binding, and lightweight `wget` health check
- `deploy/docker/README.md` — beginner Docker walkthrough with diagnosis
  commands for startup failures
- `deploy/linux/inventory.service` — systemd `--user` unit template
- `deploy/linux/install.sh` — idempotent Linux setup script (pipx install,
  systemd unit, database init); documents pipx >= 1.1.0 requirement for
  `--local` flag
- `deploy/macos/com.inventory.plist` — launchd user agent (log paths
  written by `install.sh` to `~/Library/Logs/inventory/`)
- `deploy/macos/install.sh` — macOS setup script (pipx install, plist
  path rewrite, launchd bootstrap, Gatekeeper note for Apple Silicon)
- `deploy/windows/install-task.ps1` — PowerShell Task Scheduler script
  (AtLogon trigger, idempotent, `$RepoRoot` resolved to absolute path)
- `deploy/windows/nssm-install.md` — optional NSSM service wrapper guide
- `.github/workflows/release.yml` — tag-triggered release workflow:
  CI matrix → PyPI OIDC trusted-publisher publish → GitHub Release →
  multi-arch Docker image (linux/amd64 + linux/arm64) to GHCR
- `docs/ARCHITECTURE.md` — module map, data flow diagram, extension points
- `docs/SCANNERS.md` — HID wedge model, tested scanners, troubleshooting,
  V2+ extension guide
- `docs/PROVIDERS.md` — lookup chain reference, built-in provider docs,
  step-by-step guide for adding a new provider
- `docs/EVENTS.md` — blinker signal contract for plugin authors; payload
  schemas, timing guarantee, subscription examples
- `inv/asgi.py` — importable ASGI entrypoint for `uvicorn --reload` mode
- `scripts/validate-m5-readiness.sh` — pre-flight check script for M5 coder

### Fixed
- `UniqueConstraint("id")` on `Movement` was a no-op (PK is already
  unique) with a misleading "append-only guarantee" comment; removed the
  constraint and replaced with an accurate application-layer comment (#30)
- `test_enrich_flow.py` hardcoded `item_id=1` (anti-pattern from #19);
  replaced with `_item_id_for_gtin()` dynamic lookup helper (#31)
- HTTP 429 from UPCitemdb was silently treated as a miss; now logged as
  a warning so operators can diagnose daily quota exhaustion (#34)
- macOS plist shipped `/tmp` log paths that disappear on reboot; replaced
  with `__INVENTORY_LOG_DIR__` placeholder expanded by `install.sh` to
  `~/Library/Logs/inventory/` (#32)
- `install-task.ps1` `$RepoRoot` not resolved to absolute path; now
  wrapped in `Resolve-Path` (#37)
- Docker healthcheck spawned a full Python interpreter every 30 s; replaced
  with `wget --spider` (ships in python:3.12-slim) (#38)
- `uv` version unpinned in `release.yml`; pinned to `0.5.18` to match
  the Dockerfile builder stage (#35)
- `deploy/linux/install.sh --local` silently failed with old pipx; now
  checks for pipx >= 1.1.0 and fails fast with a clear message (#36)
- `inv/scan/base.py` and `inv/scan/hid.py` were empty files, misleading
  to contributors; added stub docstrings explaining the V1 HID wedge
  model and the extension point for future scanner backends (#39)
- Docker `CMD` failure mode (volume errors causing a restart loop)
  documented in `deploy/docker/README.md` with diagnosis commands (#33)

---

## [0.0.4] — M4: Casepacks, Inventory View & CSV Export

### Added
- `pack_alias` table mapping alternate GTINs (case, inner, carton) to a
  canonical item + eaches multiplier
- `AliasRepository` with CRUD operations
- `resolve_alias()` service function — auto-multiplier on scan
- Alias CRUD in the enrichment form (`/items/{id}/enrich`)
- `/inventory` view — on-hand quantity summaries by location
- `/export/items.csv` and `/export/movements.csv` endpoints
- Scan history panel (last 5 scans rendered client-side)
- `GET /health` and `GET /version` endpoints (`routes_health.py`)

### Fixed
- Zero-stock filter in `/inventory` — items with no movements no longer
  show as negative (#18)
- Dynamic item ID lookup in enrichment tests (#19)
- Health router missing from app factory (#20)
- `ScanUnknownEvent.attempted_providers` populated with provider names
  instead of empty tuple (#22)

---

## [0.0.3] — M3: Product Lookup Chain & Enrichment

### Added
- `ProductLookupProvider` protocol and `ProviderResult` dataclass
- `ChainRunner` — ordered provider runner with per-provider timeout
- Providers: Open Food Facts, Open Library, OpenGTINdb (stub), UPCitemdb
- Local SQLite provider cache (`product_cache` table)
- Manual enrichment form (`GET/POST /items/{id}/enrich`)
- `needs_review` item flag and `/items?filter=needs_review` queue
- `scan.unknown` blinker signal fired when all providers miss

---

## [0.0.2] — M2: Scan Loop

### Added
- HTMX-powered scan form at `/scan`
- `POST /scan` route — records movement, looks up item, returns partial
- `blinker` event bus integration (`movement_created`, `item_created`)
- Input validation and scan-out zero-stock rejection
- ARM CI job (ubuntu-22.04-arm)

### Fixed
- Barcode scanner form submission and scan history display
- `datetime.utcnow()` → `datetime.now(UTC)` throughout
- Dead HTMX event listeners removed

---

## [0.0.1] — M1: Skeleton

### Added
- `uv` project skeleton (`pyproject.toml`, `uv.lock`, `Makefile`)
- FastAPI + Uvicorn application factory (`inv/main.py`)
- `pydantic-settings` configuration with `platformdirs` paths
- SQLAlchemy 2.x ORM models: `Item`, `Location`, `Movement`, `PackAlias`,
  `ProductCache`
- Alembic migrations (initial schema)
- `inventory init` and `inventory run` CLI commands (Typer)
- CI matrix: `{ubuntu, macos, windows} × {3.11, 3.12}`
- `CONTRIBUTING.md`, `DEVELOPMENT_PLAN.md`, `LICENSE` (AGPL-3.0)

---

[Unreleased]: https://github.com/manofthedown/open-inventory/compare/develop...fix/m5-review
