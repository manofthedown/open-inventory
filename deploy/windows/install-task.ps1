#Requires -Version 5.1
<#
.SYNOPSIS
    Install open-inventory as a Windows Task Scheduler task.

.DESCRIPTION
    Installs open-inventory via pipx (if not already installed), initialises
    the database, and registers an AtLogon Task Scheduler task that starts
    the inventory server automatically when the current user logs in.

.PARAMETER Local
    Install from the local repository checkout instead of PyPI.
    Use this during development or when testing a pre-release build.
    Must be run from the repository root or the script directory.

.PARAMETER Uninstall
    Remove the Task Scheduler task without uninstalling the package.

.EXAMPLE
    # Install from PyPI (recommended)
    powershell -ExecutionPolicy Bypass -File install-task.ps1

.EXAMPLE
    # Install from local checkout
    powershell -ExecutionPolicy Bypass -File install-task.ps1 -Local

.EXAMPLE
    # Remove the scheduled task
    powershell -ExecutionPolicy Bypass -File install-task.ps1 -Uninstall

.NOTES
    Requirements : Python 3.11+, pipx
    pipx install : python -m pip install --user pipx
    PyPI page    : https://pypi.org/project/open-inventory/
#>

[CmdletBinding()]
param(
    [switch]$Local,
    [switch]$Uninstall
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$TaskName   = 'open-inventory'
# Resolve to an absolute path regardless of how the script was invoked
# (e.g. via a relative path like .\install-task.ps1 or from a different
# working directory).  Without Resolve-Path the path may be relative,
# which breaks Join-Path and pipx install calls that embed the path.
$ScriptDir  = Resolve-Path (Split-Path -Parent $MyInvocation.MyCommand.Path)
$RepoRoot   = Resolve-Path (Split-Path -Parent $ScriptDir)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
function Write-Info  { param($msg) Write-Host "[info]  $msg" -ForegroundColor Cyan }
function Write-Ok    { param($msg) Write-Host "[ok]    $msg" -ForegroundColor Green }
function Write-Fail  { param($msg) Write-Host "[error] $msg" -ForegroundColor Red; exit 1 }

function Require-Command {
    param($Name, $Hint)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        Write-Fail "'$Name' not found. $Hint"
    }
}

# ---------------------------------------------------------------------------
# Uninstall path
# ---------------------------------------------------------------------------
if ($Uninstall) {
    Write-Info "Removing Task Scheduler task '$TaskName'..."
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Ok "Task '$TaskName' removed."
    Write-Host "Note: the open-inventory package is still installed. To remove it run: pipx uninstall open-inventory"
    exit 0
}

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
Write-Info "Checking prerequisites..."
Require-Command 'pipx' 'Install pipx: python -m pip install --user pipx  (then restart your shell)'
Write-Ok "pipx found."

# ---------------------------------------------------------------------------
# Install the package
# ---------------------------------------------------------------------------
if ($Local) {
    Write-Info "Installing from local repo: $RepoRoot"
    & pipx install --editable $RepoRoot 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Info "Already installed — reinstalling from local..."
        & pipx reinstall open-inventory
    }
} else {
    Write-Info "Installing open-inventory from PyPI..."
    & pipx install open-inventory 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Info "Already installed — upgrading..."
        & pipx upgrade open-inventory
    }
}

# Locate the installed binary
$InventoryBin = (Get-Command inventory -ErrorAction SilentlyContinue)?.Source
if (-not $InventoryBin) {
    # pipx default on Windows: %USERPROFILE%\.local\bin
    $InventoryBin = Join-Path $env:USERPROFILE '.local\bin\inventory.exe'
}
if (-not (Test-Path $InventoryBin)) {
    Write-Fail "'inventory' binary not found at '$InventoryBin'. Run: pipx ensurepath  then restart your shell."
}
Write-Ok "Installed: $(& $InventoryBin version)"

# ---------------------------------------------------------------------------
# Initialise the database (idempotent)
# ---------------------------------------------------------------------------
Write-Info "Running 'inventory init'..."
& $InventoryBin init
Write-Ok "Database initialised."

# ---------------------------------------------------------------------------
# Register the Task Scheduler task
# ---------------------------------------------------------------------------
Write-Info "Registering Task Scheduler task '$TaskName'..."

# Remove any existing task with the same name first (idempotent).
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

$Action = New-ScheduledTaskAction `
    -Execute $InventoryBin `
    -Argument 'run' `
    -WorkingDirectory $env:USERPROFILE

# AtLogon trigger — fires when THIS user logs in (not all users).
$Trigger = New-ScheduledTaskTrigger -AtLogon -User $env:USERNAME

# Run whether or not the user is logged on; do NOT store password.
# RunOnlyIfNetworkAvailable = false because we want offline-first.
$Settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew

# Principal: interactive logon only (no password required).
$Principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Limited

$Task = New-ScheduledTask `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Description 'open-inventory barcode inventory server (https://github.com/manofthedown/open-inventory)'

Register-ScheduledTask -TaskName $TaskName -InputObject $Task | Out-Null
Write-Ok "Task '$TaskName' registered."

# Start the task immediately so the user does not need to log out/in.
Write-Info "Starting task now..."
Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 2

$TaskInfo = Get-ScheduledTask -TaskName $TaskName
Write-Ok "Task state: $($TaskInfo.State)"

# ---------------------------------------------------------------------------
# USB HID / focus note
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "NOTE: USB barcode scanners (HID wedge mode) send keystrokes to" -ForegroundColor Yellow
Write-Host "      whichever window has focus. Keep the scan page open and" -ForegroundColor Yellow
Write-Host "      in focus while scanning. See QUICKSTART_WINDOWS.md for" -ForegroundColor Yellow
Write-Host "      tips on preventing focus-stealing." -ForegroundColor Yellow

# ---------------------------------------------------------------------------
# Status summary
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "=========================================="
Write-Host "  open-inventory is running!"
Write-Host "  Scan page:  http://127.0.0.1:8765/scan"
Write-Host "  Inventory:  http://127.0.0.1:8765/inventory"
Write-Host ""
Write-Host "  Manage the task:"
Write-Host "    Get-ScheduledTask -TaskName 'open-inventory'"
Write-Host "    Start-ScheduledTask -TaskName 'open-inventory'"
Write-Host "    Stop-ScheduledTask  -TaskName 'open-inventory'"
Write-Host "    Unregister-ScheduledTask -TaskName 'open-inventory' -Confirm:`$false"
Write-Host "=========================================="
