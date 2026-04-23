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

Clone the repo and build the image from source:

```bash
git clone https://github.com/manofthedown/open-inventory.git
cd open-inventory

docker compose -f deploy/docker/compose.yml up -d --build
```

Open <http://127.0.0.1:8765/scan>.

> **Why `--build`?** The compose file builds the image from the local
> `Dockerfile` by default. A pre-built image will be published to GHCR once
> a versioned release is tagged — see [Using the pre-built image](#using-the-pre-built-image-after-a-release-is-tagged)
> below. Until then, `--build` is required on first run.

---

## What happens on first start

1. Docker builds the image from the local `Dockerfile` (builder + runtime stages, ~200 MB)
2. A named volume `open-inventory_inv-data` is created for the SQLite database
3. `inventory init` runs inside the container (creates schema, seeds the default location)
4. The server starts at `http://127.0.0.1:8765`

Subsequent starts skip the build (the image is cached) and re-use the existing volume.

---

## Common commands

Run these from the **repo root** (where `deploy/docker/compose.yml` lives):

```bash
# Start (build image if not yet built, then start detached)
docker compose -f deploy/docker/compose.yml up -d --build

# Start without rebuilding (faster — use after first build)
docker compose -f deploy/docker/compose.yml up -d

# View live logs
docker compose -f deploy/docker/compose.yml logs -f

# Stop (data is preserved)
docker compose -f deploy/docker/compose.yml down

# Restart
docker compose -f deploy/docker/compose.yml restart inventory

# Open a shell inside the container
docker compose -f deploy/docker/compose.yml exec inventory bash

# ⚠️  DANGER: Stop AND delete all inventory data
docker compose -f deploy/docker/compose.yml down -v
```

> **Tip:** If you `cd deploy/docker/` first you can drop the `-f` flag and
> just run `docker compose up -d --build` etc.

---

## Data persistence

All inventory data (SQLite database) is stored in a named Docker volume:

```
open-inventory_inv-data  →  /home/inv/.local/share/inventory/  (inside container)
```

This volume **survives** `docker compose down` and rebuilds.  
It is **only deleted** by `docker compose down -v`.

### Backup the database

```bash
docker compose -f deploy/docker/compose.yml cp \
  inventory:/home/inv/.local/share/inventory/inventory.db \
  ./inventory-backup.db
```

### Restore from backup

```bash
docker compose -f deploy/docker/compose.yml stop inventory
docker compose -f deploy/docker/compose.yml cp \
  ./inventory-backup.db \
  inventory:/home/inv/.local/share/inventory/inventory.db
docker compose -f deploy/docker/compose.yml start inventory
```

---

## LAN access

By default the server only listens on `127.0.0.1` (your machine only).  
To allow other devices on your network to reach it, edit `deploy/docker/compose.yml`:

```yaml
ports:
  - "0.0.0.0:8765:8765"   # was: "127.0.0.1:8765:8765"
```

Then restart:

```bash
docker compose -f deploy/docker/compose.yml restart inventory
```

Also open port 8765 in your host firewall if applicable.

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

While no tagged release exists, upgrading means pulling the latest source and
rebuilding the image:

```bash
cd open-inventory
git pull
docker compose -f deploy/docker/compose.yml up -d --build
```

Your data volume is untouched. `inventory init` runs on startup and applies
any new migrations automatically.

---

## Using the pre-built image (after a release is tagged)

Once a versioned release is published to GHCR, you can skip the build step
entirely. Edit `deploy/docker/compose.yml`:

```yaml
# Comment out the build block:
# build:
#   context: ../..
#   dockerfile: deploy/docker/Dockerfile

# Uncomment the image line:
image: ghcr.io/manofthedown/open-inventory:latest
```

Then:

```bash
docker compose -f deploy/docker/compose.yml pull
docker compose -f deploy/docker/compose.yml up -d
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Port 8765 already in use | Change `ports:` in compose.yml to e.g. `"127.0.0.1:8766:8765"` |
| Container exits immediately | `docker compose -f deploy/docker/compose.yml logs inventory` |
| Permission denied on volume | The container runs as UID 1000 (`inv`); re-create the volume: `docker compose down -v && docker compose up -d --build` |
| Build fails (no disk space) | `docker system prune` to free space, then retry |
| Want to reset all data | `docker compose -f deploy/docker/compose.yml down -v && docker compose -f deploy/docker/compose.yml up -d --build` |
