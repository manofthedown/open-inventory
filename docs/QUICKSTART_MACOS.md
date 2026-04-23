# Quickstart — macOS

Get open-inventory running on macOS (Intel or Apple Silicon) in about 5 minutes.

---

## Prerequisites

Install [Homebrew](https://brew.sh) if you don't have it, then:

```bash
brew install pipx
pipx ensurepath        # adds ~/.local/bin to PATH
exec $SHELL            # reload PATH
```

> **uv is optional** — pipx manages its own isolated environments and does
> not require uv. uv is only needed if you are contributing to development.

---

## Install

```bash
pipx install open-inventory
```

Verify:

```bash
inventory --version
```

---

## Initialize

```bash
inventory init
```

Creates the database under `~/Library/Application Support/inventory/`.

---

## Run (one-off)

```bash
inventory run
```

Open <http://127.0.0.1:8765/scan> in Safari or Chrome.

Press `Ctrl+C` to stop.

---

## Run as a launchd user agent (autostart)

Install the agent so open-inventory starts automatically at login:

```bash
git clone https://github.com/manofthedown/open-inventory.git
cd open-inventory

bash deploy/macos/install.sh
```

The script will:
1. Install open-inventory via pipx
2. Run `inventory init`
3. Install `~/Library/LaunchAgents/com.inventory.plist`
4. Load the agent with `launchctl bootstrap`

Logs are written to `~/Library/Logs/inventory/`.

### Managing the agent

```bash
# Check status
launchctl print gui/$(id -u)/com.inventory

# Restart
launchctl kickstart -k gui/$(id -u)/com.inventory

# Stop (does not disable autostart)
launchctl bootout gui/$(id -u)/com.inventory

# Re-enable after bootout
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.inventory.plist
```

### Apple Silicon / Gatekeeper note

On Apple Silicon Macs, macOS may quarantine unsigned binaries. If the server
does not start after install, run:

```bash
xattr -dr com.apple.quarantine "$(which inventory)"
launchctl kickstart -k gui/$(id -u)/com.inventory
```

---

## Upgrade

```bash
pipx upgrade open-inventory
inventory init                          # applies any new migrations (idempotent)
launchctl kickstart -k gui/$(id -u)/com.inventory
```

---

## Uninstall

```bash
launchctl bootout gui/$(id -u)/com.inventory
rm ~/Library/LaunchAgents/com.inventory.plist
pipx uninstall open-inventory
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `inventory: command not found` | `pipx ensurepath && exec $SHELL` |
| Agent won't start | Check `~/Library/Logs/inventory/inventory.stderr.log` |
| Gatekeeper blocks binary | `xattr -dr com.apple.quarantine "$(which inventory)"` |
| Port 8765 in use | `INVENTORY_PORT=8766 inventory run` |
