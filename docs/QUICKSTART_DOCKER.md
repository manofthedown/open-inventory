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
git clone https://github.com/manofthedown/open-inventory.git
cd open-inventory

docker compose -f deploy/docker/compose.yml up -d
```

Open <http://127.0.0.1:8765/scan>.

---

## What happens on first start

1. Docker pulls the pre-built multi-arch image from GHCR (`ghcr.io/manofthedown/open-inventory:latest`)
2. A named volume `open-inventory_inv-data` is created for the SQLite database
3. `inventory init` runs inside the container (creates schema, seeds the default location)
4. The server starts at `http://127.0.0.1:8765`

Subsequent starts re-use the cached image and existing volume.

---

## Common commands

Run these from the **repo root** (where `deploy/docker/compose.yml` lives):

```bash
# Start (pulls image on first run, then starts detached)
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

Pull the latest image and recreate the container:

```bash
docker compose -f deploy/docker/compose.yml pull
docker compose -f deploy/docker/compose.yml up -d
```

Your data volume is untouched. `inventory init` runs on startup and applies
any new migrations automatically.

---

## Build from source (instead of pulling from GHCR)

If you want to run a local code change without tagging a release, edit
`deploy/docker/compose.yml` — comment out `image:` and uncomment the
`build:` block, then:

```bash
docker compose -f deploy/docker/compose.yml up -d --build
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
