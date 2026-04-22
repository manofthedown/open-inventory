# Windows: NSSM Service Install (Optional)

> **Default approach**: For most users, `install-task.ps1` (Task Scheduler) is
> the recommended method — no extra downloads required.  
> Use NSSM only if you need a **true Windows Service** that runs in the
> background even when no user is logged in (e.g. a shared workstation or
> kiosk scenario).

---

## What is NSSM?

[NSSM](https://nssm.cc) (Non-Sucking Service Manager) wraps any executable as
a proper Windows Service managed via `services.msc` and `sc.exe`.

---

## Prerequisites

1. **Python 3.11+** — [python.org](https://www.python.org/downloads/windows/)  
2. **pipx** — `python -m pip install --user pipx`  
3. **open-inventory** — `pipx install open-inventory`  
4. **NSSM** — download from <https://nssm.cc/download> (no installer; just a `.exe`)  
5. **Administrator privileges** — required to install a Windows Service

---

## Step-by-step

### 1. Install open-inventory

```powershell
pipx install open-inventory
inventory init
```

### 2. Download NSSM

Download the latest release from <https://nssm.cc/download>.  
Extract the zip and note the path to `nssm.exe` (e.g. `C:\tools\nssm\win64\nssm.exe`).

### 3. Find the inventory binary path

```powershell
(Get-Command inventory).Source
# Example output: C:\Users\YourName\.local\bin\inventory.exe
```

Copy that path — you will need it below.

### 4. Install the service (run as Administrator)

Open an **Administrator** PowerShell prompt:

```powershell
$nssm     = 'C:\tools\nssm\win64\nssm.exe'
$binary   = 'C:\Users\YourName\.local\bin\inventory.exe'  # from step 3
$svcName  = 'open-inventory'

& $nssm install $svcName $binary 'run'
& $nssm set     $svcName AppDirectory   "$env:USERPROFILE"
& $nssm set     $svcName Description    'open-inventory barcode inventory server'
& $nssm set     $svcName Start          SERVICE_AUTO_START
& $nssm set     $svcName AppStdout      "$env:USERPROFILE\AppData\Local\inventory\logs\service.log"
& $nssm set     $svcName AppStderr      "$env:USERPROFILE\AppData\Local\inventory\logs\service.log"
& $nssm set     $svcName AppRotateFiles 1
```

### 5. Start the service

```powershell
Start-Service open-inventory
Get-Service  open-inventory   # should show: Running
```

### 6. Verify

Open <http://127.0.0.1:8765/scan> in your browser.

---

## Managing the service

| Action | Command |
|--------|---------|
| Start  | `Start-Service open-inventory` |
| Stop   | `Stop-Service open-inventory` |
| Restart | `Restart-Service open-inventory` |
| View logs | Open `%USERPROFILE%\AppData\Local\inventory\logs\service.log` |
| Remove | `& $nssm remove open-inventory confirm` (Admin PowerShell) |

---

## Notes

- The service runs as **Local System** by default. For better security, create
  a dedicated local user account and set it via:  
  `& $nssm set open-inventory ObjectName ".\inventory-svc" "password"`
- The server binds to `127.0.0.1:8765` by default. To bind to all interfaces
  (e.g. for LAN access from another machine), change the `run` argument to  
  `run --host 0.0.0.0` and open the port in Windows Firewall.
- USB barcode scanners in HID wedge mode send keystrokes to the focused window.
  This works correctly when the browser scan page is in focus regardless of
  whether inventory runs as a Task Scheduler task or an NSSM service.
