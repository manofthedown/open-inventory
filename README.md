# open-inventory

A lightweight, modular, offline-first barcode scan-in / scan-out inventory system for mutual aid, emergency management, indie providers, and other small-scale ad-hoc distribution efforts.

## What It Is

A minimalist inventory program that captures USB barcode scans and records units in/out of stock. On first-ever scan of a given barcode, the system auto-fills basic product information from public open data sources (Open Food Facts, Open Library, OpenGTINdb, UPCitemdb).

## What It Is NOT

- **Not a WMS, TMS, ERP, or full retail POS.** No slotting, picking, routing, rate shopping, or complex workflows.
- **Not cloud-dependent.** Works entirely offline; network is only used to enrich never-before-seen barcodes.
- **Not an app store bloatware.** Runs happily on a cheap laptop, an Arch desktop, a Raspberry Pi, or a docker container.

## Design Pillars

1. **Minimalist but modular** — Small, focused core with clean seams so new capabilities (reporting, multi-location transfers, donor tracking, label printing, central sync, etc.) can bolt on without touching core.
2. **Offline-first** — Everything works without internet; network is only used to enrich never-before-seen barcodes, with a persistent local cache.
3. **Low operational cost** — Runs happily on a cheap laptop, an Arch desktop, or a Raspberry Pi.
4. **Use existing OSS** — Don't reinvent. Rely on mature, permissive-licensed libraries.
5. **Cross-platform from day one** — Dev on Arch Linux; end users may run on Arch, any Linux, Raspberry Pi OS, macOS, or Windows.

## Installation

### Quick Start (Arch Linux)

```bash
sudo pacman -S --needed uv git
git clone https://github.com/manofthedown/open-inventory.git
cd open-inventory
uv sync
uv run inventory init
uv run inventory run
```

Open your browser to `http://127.0.0.1:8765/scan`.

### Other Platforms

See the [docs/](docs/) directory for platform-specific quickstart guides:

- [Arch Linux](docs/QUICKSTART_ARCH.md)
- [Raspberry Pi](docs/QUICKSTART_PI.md)
- [macOS](docs/QUICKSTART_MACOS.md)
- [Windows](docs/QUICKSTART_WINDOWS.md)
- [Docker](docs/QUICKSTART_DOCKER.md)

## Usage

### Scanning Items In

1. Open `http://127.0.0.1:8765/scan` in your browser.
2. Plug in a USB barcode scanner (HID keyboard-wedge; no drivers needed).
3. The input field auto-focuses. Select your mode: **Each**, **Case**, **Cluster**, or **Custom ×N**.
4. Scan a barcode. The scanner "types" it as if it were a keyboard.
5. The system looks it up (local cache → Open Food Facts → Open Library → OpenGTINdb → UPCitemdb).
6. If found, the item name, brand, and current on-hand quantity are displayed.
7. Focus returns to the input. Scan the next item.

### Managing Inventory

- **View inventory**: `http://127.0.0.1:8765/inventory`
- **Enrich missing items**: `http://127.0.0.1:8765/items?filter=needs_review`
- **Export CSV**: `http://127.0.0.1:8765/export/items.csv` and `/export/movements.csv`

## Stack

| Component | Choice |
|-----------|--------|
| **Backend** | Python 3.11+ |
| **Framework** | FastAPI + Uvicorn |
| **Frontend** | Jinja2 + HTMX + Alpine.js + Pico.css |
| **Database** | SQLite (WAL mode), SQLAlchemy 2.x, Alembic migrations |
| **Package Manager** | `uv` (cross-platform) |
| **Code quality** | `ruff`, `mypy`, `pytest` |
| **License** | AGPL-3.0 |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, testing, and code standards.

We welcome contributions! Please:
1. Fork the repo and create a feature branch from `develop`.
2. Write tests for new functionality.
3. Run `make test && make lint && make types`.
4. Open a pull request with a clear description.

## Roadmap (Milestones)

- **M1**: Skeleton (core FastAPI setup, database, basic CLI)
- **M2**: Scan Loop (POST /scan endpoint, HTMX UI, HID scanner integration)
- **M3**: Lookup Chain (product data providers, caching, manual enrichment)
- **M4**: Casepacks, Inventory Views, CSV Export
- **M5**: Packaging & Cross-Platform Docs (pipx, systemd, macOS, Windows, Docker)

**Out of Scope for V1** (explicitly deferred to V2+):
- Lot/expiry/FEFO tracking
- Camera/mobile scanning
- Multi-location transfer workflows
- Authentication & user roles
- External webhooks/integrations
- Label/receipt printing
- Reporting dashboards

## Running Tests

```bash
make test      # Run pytest
make lint      # Run ruff linter
make types     # Run mypy type checker
```

## Development

```bash
# Install dev dependencies
uv sync

# Run dev server with hot reload
make run

# Or manually:
uv run inventory run --reload
```

Visit `http://127.0.0.1:8765/health` to check the server is running.

## Architecture

For a deep dive into the module structure, data model, and provider chain, see [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## License

This project is licensed under the **GNU Affero General Public License v3.0 (AGPL-3.0)**. See [LICENSE](LICENSE) for details.

## Support

- **Bug reports & feature requests**: [GitHub Issues](https://github.com/manofthedown/open-inventory/issues)
- **Discussions**: [GitHub Discussions](https://github.com/manofthedown/open-inventory/discussions)

---

**Made with ❤️ for mutual aid and emergency management.**
