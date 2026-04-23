# open-inventory — Docker

Quick reference for running open-inventory via Docker Compose.  
For full setup instructions see [`docs/QUICKSTART_DOCKER.md`](../../docs/QUICKSTART_DOCKER.md).

---

## Requirements

- Docker 24+ with the Compose plugin (`docker compose version`)
- Supported architectures: `linux/amd64`, `linux/arm64` (Raspberry Pi 4/5)

---

## Start

From the **repo root**:

```bash
docker compose -f deploy/docker/compose.yml up -d
```

Open <http://127.0.0.1:8765/scan>.

Pulls `ghcr.io/manofthedown/open-inventory:latest` on first run.  
See [`docs/QUICKSTART_DOCKER.md`](../../docs/QUICKSTART_DOCKER.md) for full details.

---

## Common commands

Run from the repo root:

| Task | Command |
|------|---------|
| Start | `docker compose -f deploy/docker/compose.yml up -d` |
| View logs | `docker compose -f deploy/docker/compose.yml logs -f` |
| Stop | `docker compose -f deploy/docker/compose.yml down` |
| Restart | `docker compose -f deploy/docker/compose.yml restart inventory` |
| Upgrade to latest release | `docker compose -f deploy/docker/compose.yml pull && docker compose -f deploy/docker/compose.yml up -d` |
| Open a shell | `docker compose -f deploy/docker/compose.yml exec inventory bash` |
| Build from source | `docker compose -f deploy/docker/compose.yml up -d --build` |
| **Delete all data** | `docker compose -f deploy/docker/compose.yml down -v` ⚠️ |

---

## Data persistence

Inventory data (SQLite database) is stored in a named Docker volume:

```
inv-data  →  /home/inv/.local/share/inventory/  (inside container)
```

The volume survives `docker compose down` and `docker compose up` cycles.  
It is **only** deleted when you run `docker compose down -v`.

To back up the database:

```bash
docker compose cp inventory:/home/inv/.local/share/inventory/inventory.db ./backup.db
```

---

## LAN access

To allow other devices on your local network to reach the server:

1. Edit `compose.yml` — change the port binding:
   ```yaml
   ports:
     - "0.0.0.0:8765:8765"
   ```
2. Restart: `docker compose restart inventory`
3. Open your firewall for port 8765 if necessary.

---

## How the container starts

The container runs two commands on startup (see `Dockerfile` `CMD`):

```
inventory init && exec inventory run --host 0.0.0.0
```

`inventory init` creates the SQLite database and runs Alembic migrations.
It is **idempotent** — safe to run on every restart.

**If `inventory init` fails** (e.g. the named volume is full, the mount
path has wrong permissions, or the container user cannot write to
`/home/inv/.local/share/inventory/`), the shell short-circuits and the
server never starts.  The container will then restart in a tight loop
(`restart: unless-stopped`) until the underlying issue is resolved.

To diagnose:

```bash
# View the last startup attempt
docker compose logs inventory

# Run init manually to see the error
docker compose run --rm inventory inventory init

# Check volume permissions
docker compose exec inventory ls -la /home/inv/.local/share/inventory/
```

The most common causes are permission problems on the named volume on first
use.  Re-creating the volume (`docker compose down -v && docker compose up -d`)
resolves most cases — **this deletes all inventory data**, so back up first.

---

## Environment variables

All settings use the `INVENTORY_` prefix. Set them in `compose.yml` under `environment:`:

| Variable | Default | Description |
|----------|---------|-------------|
| `INVENTORY_LOG_LEVEL` | `info` | Logging verbosity (`debug`, `info`, `warning`, `error`) |
| `INVENTORY_HOST` | `0.0.0.0` | Bind address (inside container) |
| `INVENTORY_PORT` | `8765` | Bind port |
| `INVENTORY_DATABASE_URL` | *(platformdirs path)* | Override SQLite path |
