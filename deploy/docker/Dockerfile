# syntax=docker/dockerfile:1
# =============================================================================
# open-inventory — multi-stage Docker image
# =============================================================================
# Build:  docker build -t open-inventory .
# Run:    docker run --rm -p 8765:8765 -v inv-data:/home/inv/.local/share/inventory open-inventory
#
# Multi-arch: built for linux/amd64 and linux/arm64 (Raspberry Pi 4/5).
# See deploy/docker/compose.yml for the recommended compose workflow.
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1 — builder
# Installs uv and builds the wheel so the final image has no build tools.
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS builder

# Install uv (fast Python package manager used in development).
# Pinning to a specific release keeps the image reproducible.
COPY --from=ghcr.io/astral-sh/uv:0.5.18 /uv /usr/local/bin/uv

WORKDIR /home/inv

# Copy only the files needed to resolve dependencies first, so Docker
# layer caching skips the heavy install step when only source changes.
COPY pyproject.toml uv.lock README.md ./
# uv needs the package source to build an editable install; copy it all.
COPY inv/ inv/

# Install runtime dependencies into an isolated venv at the SAME path
# that the runtime stage will use. This ensures the shebang line in
# entry-point scripts (/home/inv/.venv/bin/python) is valid at runtime.
# --no-dev       → skip test/lint deps (pytest, ruff, mypy, respx)
# --no-editable  → produce a proper installed package, not a dev link
RUN uv sync --frozen --no-dev --no-editable

# -----------------------------------------------------------------------------
# Stage 2 — runtime
# Minimal image: no build tools, no uv, non-root user.
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.title="open-inventory" \
      org.opencontainers.image.description="Lightweight offline-first barcode inventory system" \
      org.opencontainers.image.licenses="AGPL-3.0-or-later" \
      org.opencontainers.image.source="https://github.com/anomalyco/open-inventory"

# Create a non-root user. UID/GID 1000 is the conventional first user.
RUN groupadd --gid 1000 inv && \
    useradd --uid 1000 --gid inv --shell /bin/bash --create-home inv

# Copy the installed venv from the builder stage.
# The venv was built at /home/inv/.venv so shebangs resolve correctly.
COPY --from=builder /home/inv/.venv /home/inv/.venv

# Ensure the venv's bin directory is on PATH so `inventory` is found.
ENV PATH="/home/inv/.venv/bin:${PATH}" \
    # platformdirs XDG overrides: keep everything inside the user home so
    # the named volume mount path is predictable.
    XDG_CONFIG_HOME="/home/inv/.config" \
    XDG_DATA_HOME="/home/inv/.local/share" \
    XDG_CACHE_HOME="/home/inv/.cache" \
    XDG_STATE_HOME="/home/inv/.local/state" \
    # Prevent Python from writing .pyc files into the image layers.
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Pre-create the data directory with correct ownership so the named volume
# mount inherits these permissions on first run.
RUN mkdir -p /home/inv/.local/share/inventory && \
    chown -R inv:inv /home/inv

USER inv
WORKDIR /home/inv

# Expose the default port (127.0.0.1:8765 in dev; 0.0.0.0:8765 in Docker).
EXPOSE 8765

# Initialise the database schema on first start, then run the server.
# Using a shell wrapper lets us run two commands while keeping PID 1
# as a proper process (exec replaces the shell with uvicorn).
CMD ["sh", "-c", "inventory init && exec inventory run --host 0.0.0.0"]
