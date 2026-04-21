# 🚀 M5 (Packaging & Cross-Platform Docs) — Kickoff Brief

Welcome! You're inheriting a fully working inventory scanner at **M4 complete**. Your job is to package it for end-users and ensure fresh installs work on Linux, macOS, Windows, and Docker.

---

## Current State

**What's done:** M1–M4 are merged to `develop` and fully tested.
- ✅ Barcode scanner loop (`/scan` page, real USB HID scanning verified)
- ✅ Lookup chain (OFF, Open Library, UPCitemdb; local cache; offline fallback)
- ✅ Manual enrichment (stub items flagged `needs_review`)
- ✅ Casepacks & aliases (auto-multiplier on scan)
- ✅ Inventory view (`/inventory`) with on-hand summaries
- ✅ CSV export (`/export/items.csv`, `/export/movements.csv`)
- ✅ Full test suite: **80 tests**, all passing
- ✅ Type-safe (mypy ✅), linted (ruff ✅)
- ✅ Dev server with hot reload (`uv run inventory run --reload` ✅)

**What's missing:** User-facing deployment — your milestone.

---

## Before You Start: Validate the Foundation

The app is production-ready. Verify your local setup with the provided script:

```bash
cd open-inventory
bash scripts/validate-m5-readiness.sh
```

This checks:
- Python 3.11+, uv installed
- CLI entrypoints (`inventory init`, `inventory run`)
- 80 tests pass
- Cross-platform paths via `platformdirs`
- CI matrix configured
- Hot reload works

Then test the realistic install flow manually:

```bash
# Simulate a fresh clone (wipes .venv)
mkdir /tmp/test-fresh
cd /tmp/test-fresh
git clone <your-fork> .
rm -rf .venv

# The "4 commands" users will run on Arch
uv sync
uv run inventory init
uv run inventory run &
sleep 2
curl http://127.0.0.1:8765/health  # Should return 200 + JSON
killall python
```

If both pass, you're good. The code is solid; you're just wrapping it for distribution.

---

## M5 Exit Criteria

From DEVELOPMENT_PLAN.md §9:

> **Fresh Arch user** can run 4 commands and have a running service.
> **Fresh macOS/Windows user** can run `pipx install inventory && inventory run` and open the scan page.
> **Docker user** can run `docker compose up -d`.

This means:
1. ✅ `pipx install .` works on Arch, macOS, Windows
2. ✅ `inventory init && inventory run` actually starts the server
3. ✅ systemd user service on Linux
4. ✅ launchd user agent on macOS
5. ✅ Task Scheduler entry on Windows
6. ✅ Docker Compose for Docker-first users
7. ✅ README with per-OS quickstart links
8. ✅ CI/CD ready: wheel/sdist to PyPI + multi-arch image to GHCR

---

## Architecture You're Working With

```
inv/                     # Installable Python package
├── cli.py              # entrypoints: inventory init, inventory run, inventory backup, inventory export
├── asgi.py             # ASGI entrypoint for uvicorn reload mode (NEW)
├── __main__.py         # python -m inv
├── main.py             # FastAPI app factory
├── settings.py         # pydantic-settings; paths via platformdirs (XDG on Linux, ~/Library on macOS, APPDATA on Windows)
└── [core/ storage/ lookup/ api/ web/ scan/]  # Already implemented ✅

deploy/                 # Your main work area
├── linux/
│   ├── inventory.service      # systemd --user unit template
│   └── install.sh             # idempotent user setup script
├── macos/
│   ├── com.inventory.plist    # launchd user agent plist
│   └── install.sh
├── windows/
│   ├── install-task.ps1       # PowerShell Task Scheduler script
│   └── nssm-install.md        # optional: NSSM wrapper docs
├── docker/
│   ├── Dockerfile             # multi-stage; install Python, deps, inv package
│   ├── compose.yml            # docker-compose; bind to 127.0.0.1:8765
│   └── README.md              # beginner walkthrough (50-100 lines; copy/paste commands)
└── arch/
    └── PKGBUILD               # stretch goal: AUR packaging

docs/                   # User-facing docs (you may add/expand)
├── ARCHITECTURE.md
├── QUICKSTART_ARCH.md
├── QUICKSTART_PI.md
├── QUICKSTART_MACOS.md
├── QUICKSTART_WINDOWS.md
├── QUICKSTART_DOCKER.md
└── [SCANNERS.md, PROVIDERS.md, EVENTS.md]

.github/
└── workflows/
    ├── ci.yml                 # ✅ matrix: {ubuntu, macos, windows} × {3.11, 3.12} + ARM
    └── release.yml            # 🔲 NOT YET: publish to PyPI + GHCR (you'll create)

pyproject.toml          # ✅ Already configured for build (wheel/sdist)
README.md               # ✅ Top-level docs with hero + per-OS links
Makefile                # ✅ dev, test, lint, types, run, init
```

---

## Key Files & Patterns You Inherit

**CLI entrypoints** (inv/cli.py):
- `inventory init` — creates SQLite DB + config in XDG paths (no user input needed)
- `inventory run [--host 0.0.0.0] [--port 8765] [--reload]` — starts dev/prod server
  - `--reload` uses import string (`inv.asgi:app`) for hot reload ✅
  - No `--reload` uses app instance directly (faster) ✅
- `inventory backup` — dump DB for safekeeping (V2+ concern; stub OK for now)
- `inventory export [items|movements]` — CSV export via API

**Settings** (inv/settings.py):
- Uses `platformdirs` for OS-agnostic paths:
  - Config → `user_config_dir("inventory")` (e.g., `~/.config/inventory` on Linux, `~/Library/Preferences/inventory` on macOS)
  - Data (SQLite) → `user_data_dir("inventory")`
  - Logs → `user_log_dir("inventory")`
  - Cache → `user_cache_dir("inventory")`
- **You do NOT invent paths.** All systemd/launchd/Task Scheduler scripts read these paths from the Python app.

**ASGI entrypoint** (inv/asgi.py):
- NEW: Created for uvicorn reload mode
- Allows uvicorn to use import string: `inv.asgi:app`
- Respects settings at import time

**Existing test suite** (80 tests):
- Run before every commit: `uv run pytest`
- Linting: `uv run ruff check`
- Types: `uv run mypy inv`

---

## Your Checklist

### Phase 1: Local Install Validation (Day 1)

- [ ] Run `bash scripts/validate-m5-readiness.sh` → should pass all checks
- [ ] Test `uv sync` on Arch (should already work)
- [ ] Test `pipx install -e .` on Arch → `inventory init && inventory run` → `/health` 200 ✅
- [ ] (Stretch) Repeat on macOS if you have access (use `uv` or Homebrew to install Python 3.11+ first)
- [ ] (Stretch) Repeat on Windows if you have access (WSL2 counts; native is nicer but not required)
- [ ] Verify no OS-specific paths leak into source (grep for hardcoded `/home/`, `C:\`, `/Users/`)

### Phase 2: systemd User Service on Linux (Arch primary)

- [ ] Create `deploy/linux/inventory.service` template
  - Runs as `%u` (current user)
  - `ExecStart=/path/to/uv run inventory run` or equiv after pipx install
  - Binds to 127.0.0.1:8765 (default; can be overridden via env)
  - Uses XDG path env vars (set by systemd or app)
- [ ] Create `deploy/linux/install.sh` → idempotent setup script
  - Copies `.service` to `~/.config/systemd/user/`
  - Runs `systemctl --user daemon-reload`
  - Prints "run `systemctl --user enable inventory && systemctl --user start inventory`"
- [ ] Test on fresh Arch VM:
  ```bash
  git clone ...
  cd open-inventory
  bash deploy/linux/install.sh
  systemctl --user enable inventory
  systemctl --user start inventory
  curl http://127.0.0.1:8765/health  # should return 200 + version
  ```

### Phase 3: launchd User Agent on macOS (if you have access)

- [ ] Create `deploy/macos/com.inventory.plist`
  - `Label: com.inventory`
  - `ProgramArguments: [/usr/local/bin/inventory, run]` (assumes `pipx` install to system PATH)
  - Runs as current user
  - `KeepAlive: true` (restart on crash)
- [ ] Create `deploy/macos/install.sh`
  - Copies plist to `~/Library/LaunchAgents/`
  - Runs `launchctl load ~/Library/LaunchAgents/com.inventory.plist`
  - Prints status
- [ ] Test (or document expected behavior)

### Phase 4: Windows Task Scheduler (if you have access or can test via WSL2)

- [ ] Create `deploy/windows/install-task.ps1`
  - PowerShell script to create a scheduled task running `inventory run`
  - Trigger: "At log on" for current user
  - Task: `python -m inv run` (or equivalent)
  - Can be run as: `powershell -ExecutionPolicy Bypass -File install-task.ps1`
- [ ] Create `deploy/windows/nssm-install.md` (optional reference)
  - NSSM is a Windows service wrapper; alternative if Task Scheduler feels fragile
- [ ] Document or test the happy path

### Phase 5: Docker (Arch + Linux focus)

- [ ] Create `deploy/docker/Dockerfile`
  ```dockerfile
  FROM python:3.11-slim
  WORKDIR /app
  COPY . .
  RUN pip install .
  EXPOSE 8765
  CMD ["inventory", "run", "--host", "0.0.0.0"]
  ```
  - Multi-stage: optional (e.g., `builder` stage for uv if you want minimal final image)
  - Should run `inventory init` on first start (or accept environment to skip DB init)
- [ ] Create `deploy/docker/compose.yml`
  ```yaml
  services:
    inventory:
      build: ../..
      ports:
        - "127.0.0.1:8765:8765"
      volumes:
        - inventory_data:/root/.local/share/inventory  # adjust for XDG paths
      environment:
        - INVENTORY_DATA_DIR=/root/.local/share/inventory  # if env override needed
  volumes:
    inventory_data:
  ```
- [ ] Create `deploy/docker/README.md` (50–100 lines; copy/paste friendly)
  ```
  # Running open-inventory in Docker
  
  ## Quick Start
  
  Clone the repo, then:
  
  ```bash
  docker compose -f deploy/docker/compose.yml up -d
  curl http://127.0.0.1:8765/scan
  ```
  
  That's it. Your data persists in the `inventory_data` volume.
  
  ## Troubleshooting
  - Logs: `docker compose logs -f inventory`
  - Shell: `docker compose exec inventory sh`
  - Restart: `docker compose restart`
  ```
- [ ] Test: `docker compose -f deploy/docker/compose.yml up -d && curl http://127.0.0.1:8765/health`

### Phase 6: Documentation & README

- [ ] Update top-level `README.md`
  - Hero: what this project does (1–2 paragraphs)
  - "Get Started" section with links to per-OS quickstarts:
    - `docs/QUICKSTART_ARCH.md` — 4 commands for Arch users (clone, uv sync, inventory init, inventory run)
    - `docs/QUICKSTART_MACOS.md` — brew/uv install, pipx install, run commands
    - `docs/QUICKSTART_WINDOWS.md` — similar
    - `docs/QUICKSTART_PI.md` — for Raspberry Pi (Arch or Debian)
    - `docs/QUICKSTART_DOCKER.md` — docker compose up -d
  - Feature highlights (scan loop, offline cache, CSV export)
  - Contributing link to `CONTRIBUTING.md`
  - License badge (AGPL-3.0)
- [ ] Ensure each quickstart file:
  - Has one "happy path" that works for a beginner
  - Links to troubleshooting (e.g., "Python not found?" → install via X)
  - Ends with "you should now see `/scan` at `http://...`"

### Phase 7: CI/CD & Release Workflow (Day 2)

- [ ] Validate `.github/workflows/ci.yml` (should already exist from M1):
  - Matrix: `{ubuntu-latest, macos-latest, windows-latest} × {3.11, 3.12}`
  - One additional ARM64 job for Pi parity
  - Runs: `uv sync --frozen && uv run pytest && uv run ruff check && uv run mypy inv`
  - All must pass before merge
- [ ] Create `.github/workflows/release.yml`
  - Triggers on: push to tag `v*` (e.g., `v0.1.0`)
  - Build wheel + sdist: `uv build` (or `python -m build`)
  - Publish to PyPI: `twine upload` (requires `PYPI_TOKEN` secret)
  - Build + push Docker image to GHCR: `docker build && docker push ghcr.io/manofthedown/open-inventory:latest`
  - Create GitHub Release with changelog
  - (Stretch: sign binaries if you have a key)

### Phase 8: Testing the Full Flow (Day 2, final)

- [ ] Create a fresh Arch VM (or container):
  ```bash
  sudo pacman -S uv git
  git clone git@github.com:manofthedown/open-inventory.git
  cd open-inventory
  # **Exactly 4 commands per exit criteria:**
  uv sync
  uv run inventory init
  uv run inventory run
  # Open http://127.0.0.1:8765/scan in browser → should see scan form ✅
  ```
- [ ] Test macOS path (if you have access)
- [ ] Test Windows path (if you have access; WSL2 is OK)
- [ ] Test Docker:
  ```bash
  docker compose -f deploy/docker/compose.yml up -d
  curl http://127.0.0.1:8765/scan
  ```
- [ ] Verify all linting / typing still pass: `uv run ruff check && uv run mypy inv`

---

## Ground Rules (Consistent with M1–M4)

1. **Paths are sacred.** All file paths resolve through `inv/settings.py` (which uses `platformdirs`). You never hardcode `/home/user/...` in a script. If a service/agent needs to know the DB location, it reads it from the app or uses `platformdirs` itself.

2. **No shell scripts in the hot path.** User-facing actions (`inventory init`, `inventory run`) are Python entrypoints. `deploy/<os>/install.sh` scripts are **optional conveniences** — a power user should be able to manually copy the systemd unit or plist if they want.

3. **Tests first, deploy second.** Before you commit any deploy script, verify the happy path manually on the target OS (or document the assumption in the PR).

4. **CI matrix must be green.** Every PR must pass `{ubuntu, macos, windows} × {3.11, 3.12} + ARM`. If you can't test a platform locally, the CI will catch it.

5. **Documentation is code.** Every quickstart, docker README, and service template is user-facing; spell-check, test the copy/paste commands, and link liberally.

6. **License stays AGPL-3.0.** No proprietary build scripts or closed-source deployment aids.

---

## Handoff Notes from Prior Stages

**From M1–M2 (Scan Loop):**
- USB barcode scanner is HID keyboard-wedge; no special drivers. Browser focus handling is crucial (`autofocus` + JS refocus on HTMX swap).
- The app runs on `127.0.0.1:8765` by default; `--host 0.0.0.0` opts into LAN (for multi-device setups).

**From M3 (Lookup Chain):**
- Network providers have a **3-second timeout** per chain spec. If a provider is slow, it's a miss and the chain continues.
- OpenGTINdb is a stub (opengtindb.org returns HTML, not JSON); it always misses and is a slot-holder per plan.

**From M4 (Casepacks & Export):**
- CSV export endpoints (`/export/items.csv`, `/export/movements.csv`) are already implemented and tested.
- Casepacks use a `pack_alias` table; the enrich form lets operators define aliases.

---

## Commit Message Style (Established Pattern)

```
feat(M5): systemd user service + install script for Linux

- Create deploy/linux/inventory.service with systemd user unit
- Add deploy/linux/install.sh for idempotent setup
- Tested on fresh Arch VM: uv sync → install.sh → systemctl enable → /health 200 ✅

Closes: #XX (if there's a related issue)
```

Or for docs:
```
docs(M5): per-OS quickstart guides + top-level README

- Add QUICKSTART_ARCH.md, QUICKSTART_MACOS.md, QUICKSTART_WINDOWS.md
- Update README with hero + get-started links
- All paths verified for cross-platform correctness ✅
```

---

## Success Looks Like

After M5 is complete and merged:

1. **Arch user** clones, runs 4 commands, has a systemd user service ✅
2. **macOS user** runs `pipx install git@github.com:manofthedown/open-inventory.git && inventory run` ✅
3. **Windows user** runs PowerShell script or manual steps; scans work ✅
4. **Docker user** runs `docker compose up -d`; has a persistent DB volume ✅
5. **Contributor** reads `CONTRIBUTING.md` + `docs/QUICKSTART_ARCH.md` and is up and running in 10 min ✅
6. **Release workflow** is ready: tag → CI green → wheel/sdist to PyPI + image to GHCR ✅

---

## Questions?

- **Unclear on platformdirs?** Check `inv/settings.py` — the pattern is already set.
- **Unsure about systemd unit syntax?** Read `man systemd.service`; the pattern is standard.
- **Docker unfamiliar?** The Dockerfile is minimal; 10 lines covers it.
- **CI workflow missing pieces?** Check `.github/workflows/ci.yml` for the matrix and see if release.yml needs secrets wired.
- **Need help?** Check the DEVELOPMENT_PLAN.md §10 for the dev workflow, or reach out to the core team.

---

**You've got this.** The core app is done; M5 is plumbing and polish. Clear, well-documented, no surprises. 🚀
