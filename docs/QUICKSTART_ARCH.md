# Quickstart — Arch Linux

Get open-inventory running on Arch Linux in about 5 minutes.

---

## Prerequisites

```bash
sudo pacman -S python python-pipx uv git
pipx ensurepath        # adds ~/.local/bin to PATH
exec $SHELL            # reload PATH
```

> **Tip:** If your Arch install already has Python 3.11+ and pipx, skip the
> `pacman` line. Run `python --version` to check.

---

## Install

```bash
pipx install open-inventory
```

Verify the binary is on your PATH:

```bash
inventory --version
```

---

## Initialize

Creates the SQLite database and config directories under `~/.local/share/inventory/`:

```bash
inventory init
```

---

## Run (one-off)

```bash
inventory run
```

Open <http://127.0.0.1:8765/scan> in your browser.  
Plug in a USB barcode scanner (HID wedge mode) — it will type barcodes directly into the scan input.

Press `Ctrl+C` to stop the server.

---

## Run as a systemd user service (autostart)

Install and enable the service so it starts automatically at login:

```bash
# Clone the repo if you don't already have it (only needed for the deploy script)
git clone https://github.com/manofthedown/open-inventory.git
cd open-inventory

bash deploy/linux/install.sh
```

The script will:
1. Install open-inventory via pipx (skips if already installed)
2. Run `inventory init`
3. Install `~/.config/systemd/user/inventory.service`
4. Enable and start the service

### Managing the service

```bash
systemctl --user status inventory      # check status
systemctl --user restart inventory     # restart after upgrade
systemctl --user stop inventory        # stop
systemctl --user disable inventory     # disable autostart
journalctl --user -u inventory -f      # follow logs
```

---

## Upgrade

```bash
pipx upgrade open-inventory
inventory init                          # applies any new migrations (idempotent)
systemctl --user restart inventory
```

---

## Uninstall

```bash
systemctl --user disable --now inventory
rm ~/.config/systemd/user/inventory.service
systemctl --user daemon-reload
pipx uninstall open-inventory
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `inventory: command not found` | Run `pipx ensurepath && exec $SHELL` |
| Service fails to start | `journalctl --user -u inventory -f` for logs |
| Port 8765 already in use | `INVENTORY_PORT=8766 inventory run` |
| Database locked error | Only one `inventory run` instance can use the SQLite DB at a time |
