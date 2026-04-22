#!/usr/bin/env bash
# deploy/macos/install.sh — Install open-inventory as a launchd user agent on macOS.
#
# Usage:
#   bash install.sh                  # install from PyPI (recommended)
#   bash install.sh --local          # install from the current repo checkout
#
# Requirements: pipx  (install via: brew install pipx && pipx ensurepath)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PLIST_NAME="com.inventory"
PLIST_SRC="${SCRIPT_DIR}/${PLIST_NAME}.plist"
LAUNCH_AGENTS_DIR="${HOME}/Library/LaunchAgents"
PLIST_DEST="${LAUNCH_AGENTS_DIR}/${PLIST_NAME}.plist"
LOG_DIR="${HOME}/Library/Logs/inventory"
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
    command -v "$1" &>/dev/null || fail "'$1' not found. Install it: $2"
}

# ---------------------------------------------------------------------------
# macOS check
# ---------------------------------------------------------------------------
[[ "$(uname -s)" == "Darwin" ]] || fail "This script is macOS-only."

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
info "Checking prerequisites..."
require_cmd pipx "brew install pipx && pipx ensurepath"
ok "Prerequisites satisfied."

# ---------------------------------------------------------------------------
# Install the package
# ---------------------------------------------------------------------------
if [ "$LOCAL_INSTALL" = true ]; then
    info "Installing from local repo: ${REPO_ROOT}"
    pipx install --editable "${REPO_ROOT}" 2>/dev/null || pipx reinstall open-inventory
else
    info "Installing open-inventory from PyPI..."
    pipx install open-inventory 2>/dev/null || {
        info "Already installed — upgrading..."
        pipx upgrade open-inventory
    }
fi

# Verify the binary is accessible
INVENTORY_BIN="$(command -v inventory 2>/dev/null || echo "${HOME}/.local/bin/inventory")"
[[ -x "${INVENTORY_BIN}" ]] || fail "'inventory' not found at ${INVENTORY_BIN}. Run: pipx ensurepath && exec \$SHELL"
ok "Installed: $(${INVENTORY_BIN} version)"

# ---------------------------------------------------------------------------
# Initialize the database (idempotent)
# ---------------------------------------------------------------------------
info "Running 'inventory init'..."
"${INVENTORY_BIN}" init
ok "Database initialised."

# ---------------------------------------------------------------------------
# Create log directory
# ---------------------------------------------------------------------------
info "Creating log directory: ${LOG_DIR}"
mkdir -p "${LOG_DIR}"

# ---------------------------------------------------------------------------
# Update plist log paths to use ~/Library/Logs/inventory/
# ---------------------------------------------------------------------------
# The plist ships with a __INVENTORY_LOG_DIR__ placeholder — launchd does
# not expand ~ or $HOME in path values, so the absolute path must be
# written at install time.  This also ensures the log directory exists
# before the agent is loaded (created above).
TMP_PLIST="$(mktemp /tmp/com.inventory.XXXXXX.plist)"
sed \
    -e "s|__INVENTORY_LOG_DIR__|${LOG_DIR}|g" \
    "${PLIST_SRC}" > "${TMP_PLIST}"

# ---------------------------------------------------------------------------
# Install and load the launchd agent
# ---------------------------------------------------------------------------
info "Installing launchd agent..."
mkdir -p "${LAUNCH_AGENTS_DIR}"
cp "${TMP_PLIST}" "${PLIST_DEST}"
rm -f "${TMP_PLIST}"

# Unload any previously loaded instance (ignore errors on first install)
launchctl bootout "gui/$(id -u)/${PLIST_NAME}" 2>/dev/null || true

# Load the new plist
launchctl bootstrap "gui/$(id -u)" "${PLIST_DEST}"
ok "LaunchAgent loaded."

# ---------------------------------------------------------------------------
# Gatekeeper note (Apple Silicon / unsigned binaries)
# ---------------------------------------------------------------------------
if [[ "$(uname -m)" == "arm64" ]]; then
    echo ""
    echo "[note]  On Apple Silicon you may see a Gatekeeper prompt."
    echo "        If the server does not start, run:"
    echo "          xattr -dr com.apple.quarantine \"\$(which inventory)\""
    echo "        then: launchctl kickstart -k gui/\$(id -u)/com.inventory"
fi

# ---------------------------------------------------------------------------
# Status summary
# ---------------------------------------------------------------------------
echo ""
echo "=========================================="
echo "  open-inventory is running!"
echo "  Scan page:  http://127.0.0.1:8765/scan"
echo "  Inventory:  http://127.0.0.1:8765/inventory"
echo ""
echo "  Logs:  ${LOG_DIR}/"
echo ""
echo "  Manage the agent:"
echo "    launchctl print gui/\$(id -u)/com.inventory"
echo "    launchctl kickstart -k gui/\$(id -u)/com.inventory"
echo "    launchctl bootout  gui/\$(id -u)/com.inventory"
echo "=========================================="
