# Quickstart — Windows

Get open-inventory running on Windows 10/11 in about 10 minutes.

---

## Prerequisites

### Option A — winget (recommended, built into Windows 11)

```powershell
winget install Python.Python.3.12
winget install astral-sh.uv          # optional, only needed for development
```

### Option B — Scoop

```powershell
scoop install python
```

### Install pipx

```powershell
python -m pip install --user pipx
python -m pipx ensurepath
```

Close and reopen your terminal after running `ensurepath` so the PATH change takes effect.

---

## Install

```powershell
pipx install open-inventory
```

Verify:

```powershell
inventory --version
```

---

## Initialize

```powershell
inventory init
```

Creates the database under `%APPDATA%\inventory\`.

---

## Run (one-off)

```powershell
inventory run
```

Open <http://127.0.0.1:8765/scan> in your browser.

Press `Ctrl+C` to stop.

---

## Run as a Task Scheduler task (autostart)

Set up open-inventory to start automatically when you log in:

```powershell
# Clone the repo if you don't already have it
git clone https://github.com/anomalyco/open-inventory.git
cd open-inventory

powershell -ExecutionPolicy Bypass -File deploy\windows\install-task.ps1
```

The script will:
1. Install open-inventory via pipx (skips if already installed)
2. Run `inventory init`
3. Register an **AtLogon** Task Scheduler task
4. Start the task immediately

### Managing the task

```powershell
# Check status
Get-ScheduledTask -TaskName 'open-inventory'

# Start manually
Start-ScheduledTask -TaskName 'open-inventory'

# Stop
Stop-ScheduledTask -TaskName 'open-inventory'

# Remove (does not uninstall the package)
Unregister-ScheduledTask -TaskName 'open-inventory' -Confirm:$false

# Uninstall (remove task + package)
powershell -ExecutionPolicy Bypass -File deploy\windows\install-task.ps1 -Uninstall
pipx uninstall open-inventory
```

### Alternative: NSSM (true Windows Service)

If you need open-inventory to run even when no user is logged in, see
[`deploy/windows/nssm-install.md`](../deploy/windows/nssm-install.md) for
instructions using the Non-Sucking Service Manager.

---

## USB barcode scanner (HID wedge) — important note

Most USB barcode scanners operate as **HID keyboard devices**: they type the
barcode digits into whatever window has keyboard focus. This is how
open-inventory expects scanners to work.

**To scan reliably:**
- Keep the browser tab with `http://127.0.0.1:8765/scan` **in focus**.
- The scan input field auto-focuses after each scan (handled by `scan_focus.js`).

**Focus-stealing warning:** The `inventory run` server window must stay open
(you can minimise it, but not close it). If the terminal window captures focus
during a scan, the barcode will be typed into the terminal instead of the
browser. Consider using the Task Scheduler approach, which runs the server
headlessly.

---

## Upgrade

```powershell
pipx upgrade open-inventory
inventory init                          # applies any new migrations (idempotent)
Stop-ScheduledTask  -TaskName 'open-inventory'
Start-ScheduledTask -TaskName 'open-inventory'
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `inventory` not recognised | Close and reopen terminal after `pipx ensurepath` |
| Task does not start at login | Open Task Scheduler (`taskschd.msc`), find `open-inventory`, check status |
| Port 8765 in use | Set `INVENTORY_PORT=8766` in environment variables and re-run `install-task.ps1` |
| `ExecutionPolicy` error | Run: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| Antivirus blocks the binary | Add `%USERPROFILE%\.local\bin\inventory.exe` to your AV exclusions |
