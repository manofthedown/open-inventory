#!/usr/bin/env bash
# deploy/linux/install.sh — Install open-inventory as a systemd user service.
#
# Usage:
#   bash install.sh                  # install from PyPI (recommended)
#   bash install.sh --local          # install from the current repo checkout
#
# Requirements:
#   pipx >= 1.1.0  — the --local / --editable flag requires pipx 1.1.0+.
#                    Check your version: pipx --version
#                    Upgrade: pip install --user --upgrade pipx
#   systemd        — required for the user service unit
#
# Tested on: Arch Linux, Debian/Ubuntu, Raspberry Pi OS (Bookworm)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
UNIT_NAME="inventory"
UNIT_FILE="${SCRIPT_DIR}/inventory.service"
UNIT_DEST="${HOME}/.config/systemd/user/${UNIT_NAME}.service"
LOCAL_INSTALL=false

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
for arg in "$@"; do
    case "$arg" in
        --local) LOCAL_INSTALL=true ;;
        *) echo "Unknown argument: $arg"; exit 1 ;;
    esac
done

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
info()  { echo "[info]  $*"; }
ok()    { echo "[ok]    $*"; }
fail()  { echo "[error] $*" >&2; exit 1; }

require_cmd() {
    command -v "$1" &>/dev/null || fail "'$1' not found. Install it first: $2"
}

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
info "Checking prerequisites..."
require_cmd pipx "https://pipx.pypa.io"
require_cmd systemctl "systemd is required for this install method"

ok "Prerequisites satisfied."

# ---------------------------------------------------------------------------
# Install the package
# ---------------------------------------------------------------------------
if [ "$LOCAL_INSTALL" = true ]; then
    # --editable requires pipx >= 1.1.0; check before attempting.
    PIPX_VERSION="$(pipx --version 2>/dev/null | grep -oP '\d+\.\d+\.\d+' | head -1)"
    PIPX_MAJOR="$(echo "${PIPX_VERSION}" | cut -d. -f1)"
    PIPX_MINOR="$(echo "${PIPX_VERSION}" | cut -d. -f2)"
    if [ "${PIPX_MAJOR}" -lt 1 ] || { [ "${PIPX_MAJOR}" -eq 1 ] && [ "${PIPX_MINOR}" -lt 1 ]; }; then
        fail "pipx >= 1.1.0 is required for --local installs (found ${PIPX_VERSION}). Upgrade: pip install --user --upgrade pipx"
    fi
    info "Installing from local repo: ${REPO_ROOT}"
    pipx install --editable "${REPO_ROOT}" || pipx upgrade open-inventory --pip-args="--editable ${REPO_ROOT}"
else
    info "Installing open-inventory from PyPI..."
    pipx install open-inventory 2>/dev/null || {
        info "Already installed — upgrading..."
        pipx upgrade open-inventory
    }
fi

# Verify the binary is accessible
command -v inventory &>/dev/null || fail "'inventory' not found on PATH after install. Try: pipx ensurepath && exec \$SHELL"
ok "Installed: $(inventory version)"

# ---------------------------------------------------------------------------
# Initialize the database (idempotent)
# ---------------------------------------------------------------------------
info "Running 'inventory init'..."
inventory init
ok "Database initialised."

# ---------------------------------------------------------------------------
# Install the systemd user unit
# ---------------------------------------------------------------------------
info "Installing systemd user service..."
mkdir -p "$(dirname "${UNIT_DEST}")"
cp "${UNIT_FILE}" "${UNIT_DEST}"

systemctl --user daemon-reload
systemctl --user enable --now "${UNIT_NAME}.service"

ok "Service enabled and started."

# ---------------------------------------------------------------------------
# Status summary
# ---------------------------------------------------------------------------
echo ""
echo "=========================================="
echo "  open-inventory is running!"
echo "  Scan page:  http://127.0.0.1:8765/scan"
echo "  Inventory:  http://127.0.0.1:8765/inventory"
echo ""
echo "  Manage the service:"
echo "    systemctl --user status inventory"
echo "    systemctl --user restart inventory"
echo "    systemctl --user stop inventory"
echo "    journalctl --user -u inventory -f"
echo "=========================================="
