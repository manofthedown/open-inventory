# Quickstart — Raspberry Pi

Get open-inventory running on a Raspberry Pi (3B+, 4, or 5) running
Raspberry Pi OS (Bookworm 64-bit recommended) or Ubuntu Server 22.04+.

This guide sets up a **headless** Pi that serves the inventory UI over your
local network, with autostart via systemd.

---

## Prerequisites

```bash
sudo apt update && sudo apt install -y python3 python3-pip git
pip3 install --user pipx
python3 -m pipx ensurepath
exec $SHELL
```

> **pipx version:** The `deploy/linux/install.sh --local` flag requires
> **pipx >= 1.1.0** (it uses `pipx install --editable`, added in that
> release).  Check your version with `pipx --version` and upgrade if needed:
> ```bash
> pip3 install --user --upgrade pipx
> ```
> Installing from PyPI (`pipx install open-inventory`) works with any
> supported pipx version.

> **Python version:** Raspberry Pi OS Bookworm ships Python 3.11. If you are
> on an older Raspberry Pi OS (Bullseye, which ships 3.9), install a newer
> Python first:
> ```bash
> sudo apt install -y python3.11 python3.11-venv
> python3.11 -m pip install --user pipx
> ```

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

Creates the database under `~/.local/share/inventory/` (XDG standard).

---

## Run (one-off test)

```bash
inventory run --host 0.0.0.0
```

> `--host 0.0.0.0` is needed so the Pi accepts connections from other
> devices on your local network. By default it only listens on `127.0.0.1`.

Find your Pi's IP address:

```bash
hostname -I | awk '{print $1}'
```

Open `http://<pi-ip>:8765/scan` on any device on your local network.

Press `Ctrl+C` to stop.

---

## Run as a systemd user service (autostart)

```bash
git clone https://github.com/anomalyco/open-inventory.git
cd open-inventory

bash deploy/linux/install.sh
```

The service runs as your user and starts at login. For a **headless Pi that
must run without anyone logged in**, enable linger:

```bash
loginctl enable-linger "$USER"
```

This makes systemd start user services at boot even without an interactive
login session.

### Expose on the LAN

By default the service binds to `127.0.0.1`. To serve over the network,
edit the unit file or set an environment variable. The simplest approach is
to set an environment variable in the service override:

```bash
systemctl --user edit inventory
```

Add:

```ini
[Service]
Environment=INVENTORY_HOST=0.0.0.0
```

Save, then:

```bash
systemctl --user daemon-reload && systemctl --user restart inventory
```

### Firewall

If you have `ufw` enabled:

```bash
sudo ufw allow 8765/tcp comment 'open-inventory'
```

---

## Managing the service

```bash
systemctl --user status inventory
systemctl --user restart inventory
journalctl --user -u inventory -f
```

---

## USB barcode scanner on the Pi

USB scanners in HID wedge mode work the same way as on a desktop. Connect
the scanner to a Pi USB port — it registers as a keyboard device. The scan
page running in a browser on another device will receive the keystrokes
forwarded from the browser's own input field.

> No special drivers are needed. Raspberry Pi OS automatically enumerates
> USB HID devices.

---

## Upgrade

```bash
pipx upgrade open-inventory
inventory init                          # applies any new migrations (idempotent)
systemctl --user restart inventory
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `inventory: command not found` | `pipx ensurepath && exec $SHELL` |
| Service fails on boot (no session) | `loginctl enable-linger $USER` |
| Can't reach Pi from another device | `inventory run --host 0.0.0.0` and check firewall |
| Python 3.9 / `pipx` errors | Install Python 3.11: `sudo apt install python3.11 python3.11-venv` |
| Low disk space warning | SQLite is tiny; the Pi's SD card is the bottleneck, not the DB |
