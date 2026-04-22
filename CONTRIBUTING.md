# Contributing to open-inventory

Thanks for picking this up. This document is the practical guide to working in
this repo — how we branch, how we review, and the gotchas that already bit
someone.

## What this project is (and isn't)

`open-inventory` is a lightweight, offline-first barcode scan-in / scan-out
inventory tool for mutual aid groups, emergency ops, and small ad-hoc
distribution efforts. A USB barcode scanner types GTINs into a web UI at
`http://127.0.0.1:8765/scan`; the server records movements; on first scan of
an unknown barcode, public open-data providers auto-fill product info.

**It is not** a WMS, ERP, POS, or full retail system. No slotting, picking,
routing, rate shopping, or complex workflows. If a feature sounds like
"enterprise inventory", it's almost certainly out of scope — see
`DEVELOPMENT_PLAN.md` §13.

## Licensing

This project is licensed under the **GNU Affero General Public License v3.0
(AGPL-3.0)**. By contributing, you agree that your contributions will be
licensed under the same license. See `LICENSE` for the full text.

## Before you start

1. **Read `DEVELOPMENT_PLAN.md` in the repo root.** This is the north star —
   sections 5 (data model), 6 (module architecture), 9 (milestones), and 13
   (out-of-scope) are the contract between coders and the PM. Don't deviate
   without a separate PR against the plan itself.
2. **Skim the recent PRs** in this repo (start with `#7`) to see how scoped
   commits, issue references, and PR bodies are shaped here.
3. **Check open issues** labelled `M<N>` and `blocker` — they're the current
   work queue.

## Getting Started

### Prerequisites

- **Python 3.11+**
- **`uv`** package manager ([install guide](https://github.com/astral-sh/uv))
- **Git**

### Development Setup

```bash
git clone https://github.com/manofthedown/open-inventory.git
cd open-inventory
uv sync                          # installs app + dev dependencies
uv run inventory init            # creates DB + default 'Main' location
uv run inventory run --reload    # http://127.0.0.1:8765
```

`uv sync` installs dev tooling automatically because it lives in
`[dependency-groups].dev` (PEP 735), not `[project.optional-dependencies]`.
Do not move dev deps into optional-dependencies — CI's `uv sync --frozen`
won't install extras by default and the whole pipeline breaks silently.

### Running Tests & Linting

```bash
make test      # uv run pytest
make lint      # uv run ruff check inv tests
make types     # uv run mypy inv
```

All three must be green before any merge. A PR that's "green except for ARM
CI" is acceptable (see "Known-broken CI" below); a PR that's "green except
for mypy" is not.

## Project norms

This project uses a **validator / coder workflow** that's slightly different
from a typical one-dev flow. Worth knowing up front:

- **The PM is non-technical.** Communicate via PR descriptions, issue
  comments, and commit messages — not Slack threads. Anything important has
  to survive in the git history after you've moved on.
- **Every milestone gets audited against its exit criteria** when a coder
  declares it done. Expect a validator report that files GitHub issues for
  real blockers and opportunities. Don't take it personally; the validator's
  job is to be picky so the PM doesn't have to be. See PRs `#7` and `#13`
  for the pattern — those are audit-response PRs.
- **Blockers get their own issues.** One issue per problem, with
  reproduction + acceptance criteria. One PR can close several related
  issues, with one commit per issue for clean review.
- **`main` is release-only.** All work merges into `develop`; `develop`
  gets promoted to `main` at release time.

## Development Workflow

1. **Create a branch off `origin/develop`:**
   ```bash
   git fetch origin
   git checkout -b <type>/<scope> origin/develop
   ```
   Naming conventions:
   - `feat/m<N>-<area>` — new milestone work (e.g. `feat/m3-openfoodfacts`)
   - `fix/m<N>-blockers` — audit-response fixes for a milestone
   - `fix/<issue-slug>` — one-off bug
   - `docs/<topic>` — docs only
   - `chore/<topic>` — tooling, CI, deps

2. **Write code + tests** following the architecture below.

3. **Commit one logical change per commit**, with the
   `<type>(<scope>,#<issue>): subject` format (see "Commit Message Format"
   below). Scoped commits are how the reviewer navigates the diff.

4. **Run local checks:**
   ```bash
   make test && make lint && make types
   ```

5. **Push and open a PR against `develop`** with a body that explains *why*,
   not just *what*. Templates:
   - `## Summary` — 2–5 bullet points.
   - `## Verification` — the exact commands you ran.
   - `## Not in this PR` — what you deliberately deferred.
   - `Closes #N, closes #M` — issues auto-close on merge.

6. **Respond to review comments in the PR**, not in DMs. Push fixup commits
   rather than rebasing while review is in flight (makes re-review easier);
   squash/clean-up happens at merge time.

### Known-broken CI

The ARM64 CI job (`arm-test`) is currently red on every PR because the
runner's apt repo doesn't ship Python 3.11/3.12. The main matrix
(`ubuntu/macos/windows × 3.11/3.12`) is authoritative. There's an open
issue to fix the ARM job properly. If you're touching CI anyway, feel
free to land it; otherwise ignore the red X.

## Code Style & Standards

### Python

- **Formatter / linter:** `ruff` (`make lint`; `uv run ruff check --fix` to auto-fix).
- **Type checker:** `mypy` (`make types`).
- **Target:** Python 3.11+ (but CI matrix also tests 3.12).
- `from __future__ import annotations` is the default at the top of new
  modules — it's cheaper than deferred-evaluation headaches later.

### Architecture Principles

- **Modular.** Domain logic, transport, and storage live in different
  packages. `inv/core/` never imports `inv/api/` or plugin modules.
- **Testable.** Services take a `Session` parameter; repositories take a
  `Session`; FastAPI DI wires them together. No module-level singletons.
- **Cross-platform.** Filesystem paths go through `platformdirs` via
  `inv/settings.py`. No hardcoded `/tmp/...` or `C:\...`. Shell scripts
  live only in `deploy/<os>/` and are optional conveniences.
- **Offline-first.** Network calls (provider chain) must have a fallback
  path. Failing any HTTP call is never fatal.

### Module Structure

| Package | Responsibility | Key contract |
|---------|----------------|--------------|
| `inv/core/` | Domain models (Pydantic), service layer, event signals | `inv/core/events.py` declares `movement.created`, `item.created`, `item.enriched`, `scan.unknown` — these names and their payload shapes are **locked** by `DEVELOPMENT_PLAN.md` §6. Plugins subscribe; core never imports plugins. |
| `inv/storage/` | SQLAlchemy ORM, repositories, Alembic migration runner | Repositories hide ORM details from services. Migrations are the single source of truth for schema — never `Base.metadata.create_all()` in app code. |
| `inv/api/` | FastAPI routers, dependencies | Reads settings + engine from `app.state` via the helpers in `inv/api/deps.py`. Do not instantiate `Settings()` at request time. |
| `inv/web/` | Jinja templates, HTMX partials, static assets | No build step, no bundler, no Node. Vendored JS/CSS in `inv/web/static/` with SHA256s in `VENDORED.md`. |
| `inv/lookup/` | Product data providers (chain pattern) | All providers implement `ProductLookupProvider`; `ChainRunner` fans out in plan order with per-provider timeouts. |
| `inv/scan/` | Scanner input abstraction | V1 is HTML keyboard-wedge; the protocol is intentionally broader so V2 camera/serial scanners can slot in. |

## Testing

- **Unit tests** in `tests/unit/` — service and repository layer.
- **Integration tests** in `tests/integration/` — FastAPI `TestClient`, real
  SQLite, real Alembic migration. Use these for anything that crosses the
  HTTP boundary.
- **Smoke tests** in `tests/smoke/` — optional Playwright/keystroke tests.

Use `respx` for mocking HTTPX calls (provider lookups). Recorded fixtures
live under `tests/fixtures/providers/` so the suite runs offline. Access
them via the `provider_fixtures_dir` session fixture from `conftest.py`
— never construct a `Path(__file__).parent...` chain pointing at that
directory from inside a test file (see Gotchas below).

### Example test

```python
# tests/integration/test_scan_flow.py
from fastapi.testclient import TestClient

def test_post_scan_over_scan_out_returns_409(client: TestClient) -> None:
    """Over-scan-out returns 409 with a clear error — M2 exit criterion."""
    gtin = "2222222222222"
    client.post("/scan", json={
        "gtin": gtin, "direction": "IN", "qty_multiplier": 2, "location_id": 1,
    })
    response = client.post("/scan", json={
        "gtin": gtin, "direction": "OUT", "qty_multiplier": 99, "location_id": 1,
    })
    assert response.status_code == 409
    assert "Cannot remove" in response.json()["detail"]
```

The `client` fixture (see `tests/conftest.py`) gives you a fresh migrated
SQLite DB + seeded default location per test. Don't instantiate `Settings()`
directly in tests — rely on the fixture chain.

## Gotchas (things that already bit someone)

These are in the codebase because a previous PR fixed them. Don't re-break them.

- **Dev deps live in `[dependency-groups]`, not `[project.optional-dependencies]`.**
  `uv sync --frozen` in CI won't install extras without `--all-extras`; PEP 735
  dev groups auto-install.
- **Vendored frontend assets are real libraries.** Check
  `inv/web/static/VENDORED.md` before touching. Don't "minify for M<N>" — the
  file sizes should match the SHA256s. Don't add a build step.
- **`alembic.ini`'s `sqlalchemy.url` is a placeholder.** The real URL is
  injected by `alembic/env.py` from `Settings.db_path`. If you want to run a
  migration from Python, use `inv.storage.migrations.upgrade_to_head(settings)`,
  not the `alembic` CLI.
- **Schema changes go through Alembic, never `Base.metadata.create_all`.**
  `inventory init` and the test `engine` fixture both run `alembic upgrade
  head` — if you add tables without a migration, you'll have drift between
  dev and test environments the moment someone pulls.
- **Event bus signals are a locked contract.** `inv/core/events.py` declares
  four `blinker.signal(...)` names matching `DEVELOPMENT_PLAN.md` §6.
  Renaming them (or changing the payload dataclasses) will break any future
  plugin that subscribes. Add new signals freely; don't rename existing ones.
- **Settings must come from app state, not `Settings()` at request time.**
  `create_app(settings)` is the only place that should instantiate
  `Settings`. Dependencies read it back out via helpers in `inv/api/deps.py`.
  If a dependency calls `Settings()` directly, tests will silently hit
  whatever `INVENTORY_DATABASE_URL` is set in the environment — including
  the user's real XDG database.
- **`record_scan` only sets `needs_review` at item creation time.** On
  subsequent scans it must not touch the flag, or M3's manual-enrichment
  queue permanently empties itself. When adding new item-lookup flows,
  model them as "get-or-create" (idempotent) rather than a generic
  upsert-with-kwargs that overwrites fields.
- **CORS `allow_credentials=True` + `allow_origins=["*"]` is a spec
  violation.** Browsers reject the combo. Keep origins explicit.
- **Don't use `__file__`-relative paths to reach `tests/fixtures/` from
  inside a test file.** Use the `provider_fixtures_dir` session fixture
  from `tests/conftest.py` instead. `conftest.py`'s location relative to
  `tests/` is guaranteed by pytest's discovery rules; a
  `Path(__file__).parent.parent / ...` chain silently resolves to the
  wrong directory if the test file is ever moved to a different depth.
  If a test fixture file needs a local fixture for intentionally isolated
  state (e.g. `fresh_settings` in `test_migrations.py`), add a comment
  explaining why it is local so the next contributor doesn't move it to
  `conftest.py` by mistake.

## Milestones & Scope

This project follows a milestone-driven plan (`DEVELOPMENT_PLAN.md` §9):

| Milestone | Focus |
|-----------|-------|
| M1 | Skeleton (FastAPI + SQLite + Alembic + CLI + vendored static) |
| M2 | Scan loop (`POST /scan`, HTMX UI, event bus, negative-stock guard) |
| M3 | Lookup chain (OFF, Open Library, OpenGTINdb, UPCitemdb + cache) |
| M4 | Casepacks, inventory views, CSV export |
| M5 | Packaging (pipx, systemd, macOS, Windows, Docker) + docs |

**Out of scope for V1** (explicitly deferred to V2+):

- Lot/expiry/FEFO tracking
- Camera/mobile scanning
- Multi-location transfer workflows
- Authentication & user roles
- External webhooks / integrations
- Label / receipt printing
- Reporting dashboards (CSV export only)
- Central sync between instances

Each deferred item has a modularity slot (event bus signals, provider
interfaces, settings sections) reserved so it can land as a V2 module
without touching core.

PRs should target the current active milestone unless they are bug fixes.

## Commit Message Format

Conventional commits, with milestone + issue tag when applicable:

```
<type>(<scope>,#<issue>): <subject>

<body — the why, not just the what>

Closes #<issue>
```

Scopes seen in this repo's history:

- `feat(M2,#8)` — new milestone work implementing issue #8
- `fix(M1,#3)` — audit-response fix closing issue #3
- `fix(M2)` — fix with no single issue (keep these rare)
- `test(M2,#11)` — tests added for issue #11
- `docs(contributing)` — docs changes
- `chore(ci)` — tooling / CI changes

If you close multiple issues with one commit, list them: `fix(M2,#8,#10):`.

## Pull Request Checklist

Before opening a PR:

- [ ] Tests pass: `make test`
- [ ] Linter passes: `make lint`
- [ ] Type checker passes: `make types`
- [ ] New behavior has tests — service-layer in `tests/unit/`, HTTP in
      `tests/integration/`.
- [ ] No hardcoded filesystem paths (use `platformdirs` / `Settings.db_path`).
- [ ] No OS-specific code outside `deploy/<os>/`.
- [ ] Commit messages follow `<type>(<scope>,#<issue>):` format.
- [ ] PR body explains *why* and includes `## Verification` with the commands
      you ran locally.
- [ ] Closes linked issues via `Closes #N` in the PR body.
- [ ] Main CI matrix is green (ARM job may be red — see "Known-broken CI").

## Questions?

Open a GitHub issue or discussion. For anything time-sensitive, leave a
comment on the relevant PR or issue — the PM watches those.

---

**Thank you for contributing to open-inventory!** 🙏
