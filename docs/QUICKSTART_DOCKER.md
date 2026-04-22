# Quickstart — Docker

Run open-inventory in a container — no Python installation required on the host.

Supported architectures: `linux/amd64` (x86-64), `linux/arm64` (Raspberry Pi 4/5, Apple Silicon via Rosetta).

---

## Prerequisites

- Docker 24+ with the Compose plugin  
  Install: <https://docs.docker.com/get-docker/>

Verify:

```bash
docker compose version
# Docker Compose version v2.x.x
```

---

## Quick start

```bash
# Pull and start (detached)
docker compose \
  -f https://raw.githubusercontent.com/anomalyco/open-inventory/main/deploy/docker/compose.yml \
  up -d
```

Or clone the repo first (recommended — gives you the compose file locally):

```bash
git clone https://github.com/anomalyco/open-inventory.git
cd open-inventory/deploy/docker

docker compose up -d
```

Open <http://127.0.0.1:8765/scan>.

---

## What happens on first start

1. Docker pulls the pre-built image from GHCR (`ghcr.io/anomalyco/open-inventory:latest`)
2. A named volume `open-inventory_inv-data` is created for the SQLite database
3. `inventory init` runs inside the container (creates schema, default location)
4. The server starts on port 8765

---

## Common commands

```bash
# Start (detached)
docker compose up -d

# View live logs
docker compose logs -f

# Stop (data is preserved)
docker compose down

# Restart after an upgrade
docker compose pull && docker compose up -d

# Open a shell inside the container
docker compose exec inventory bash

# ⚠️  DANGER: Stop AND delete all inventory data
docker compose down -v
```

---

## Data persistence

All inventory data (SQLite database) is stored in a named Docker volume:

```
open-inventory_inv-data  →  /home/inv/.local/share/inventory/  (inside container)
```

This volume **survives** `docker compose down` and image upgrades.  
It is **only deleted** by `docker compose down -v`.

### Backup the database

```bash
docker compose cp inventory:/home/inv/.local/share/inventory/inventory.db ./inventory-backup.db
```

### Restore from backup

```bash
docker compose stop inventory
docker compose cp ./inventory-backup.db inventory:/home/inv/.local/share/inventory/inventory.db
docker compose start inventory
```

---

## Build from source

To build the image from a local checkout instead of pulling from GHCR:

```bash
cd open-inventory   # repo root

# Edit deploy/docker/compose.yml:
# Comment out:  image: ghcr.io/anomalyco/open-inventory:latest
# Uncomment:    build: { context: ../.., dockerfile: deploy/docker/Dockerfile }

docker compose -f deploy/docker/compose.yml up -d --build
```

---

## LAN access

By default the server only listens on `127.0.0.1` (your machine only).  
To allow other devices on your network to reach it, edit `compose.yml`:

```yaml
ports:
  - "0.0.0.0:8765:8765"   # was: "127.0.0.1:8765:8765"
```

Then restart: `docker compose restart inventory`

Also open the port in your host firewall if applicable.

---

## Environment variables

Set these in the `environment:` section of `compose.yml`:

| Variable | Default | Description |
|----------|---------|-------------|
| `INVENTORY_LOG_LEVEL` | `info` | Verbosity: `debug`, `info`, `warning`, `error` |
| `INVENTORY_HOST` | `0.0.0.0` | Bind address inside the container |
| `INVENTORY_PORT` | `8765` | Bind port inside the container |
| `INVENTORY_DATABASE_URL` | *(platformdirs path)* | Override the SQLite path |

---

## Upgrade

```bash
docker compose pull           # fetch the latest image
docker compose up -d          # recreate container with new image (data volume unchanged)
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Port 8765 already in use | Change `ports:` in compose.yml to e.g. `"127.0.0.1:8766:8765"` |
| Container exits immediately | `docker compose logs inventory` to see the error |
| Permission denied on volume | The container runs as UID 1000 (`inv`); ensure the volume isn't owned by root |
| Apple Silicon image not found | Pull explicitly: `docker pull --platform linux/arm64 ghcr.io/anomalyco/open-inventory:latest` |
| Want to reset all data | `docker compose down -v && docker compose up -d` |
