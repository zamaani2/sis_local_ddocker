# Setup Podman Auto-Start on Windows Boot
# This script configures Windows Task Scheduler to auto-start Podman and containers on boot

param(
    [switch]$Remove
)

$ScriptPath = $MyInvocation.PSCommandPath
$ScriptDir = Split-Path -Parent $ScriptPath
$ProjectDir = Split-Path -Parent $ScriptDir
$BootScript = Join-Path $ScriptDir "podman-boot-start.ps1"

# Task Scheduler configuration
$TaskName = "SchoolApp-Podman-AutoStart"
$TaskDescription = "Auto-start Podman machine and SchoolApp containers on Windows boot"

Write-Host "=== Podman Auto-Start Setup ===" -ForegroundColor Cyan
Write-Host ""

if ($Remove) {
    Write-Host "Removing auto-start task..." -ForegroundColor Yellow
    
    # Remove existing task
    $ExistingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($ExistingTask) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "✓ Auto-start task removed" -ForegroundColor Green
    } else {
        Write-Host "No existing task found" -ForegroundColor Yellow
    }
    
    exit 0
}

# Check if running as Administrator
$IsAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $IsAdmin) {
    Write-Host "ERROR: This script must be run as Administrator" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

# Check if boot script exists
if (-not (Test-Path $BootScript)) {
    Write-Host "ERROR: Boot script not found: $BootScript" -ForegroundColor Red
    exit 1
}

Write-Host "Project Directory: $ProjectDir" -ForegroundColor Cyan
Write-Host "Boot Script: $BootScript" -ForegroundColor Cyan
Write-Host ""

# Check for existing task
$ExistingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($ExistingTask) {
    Write-Host "Existing task found. Removing..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Create the action (run the boot script)
$Action = New-ScheduledTaskAction `
    -Execute "PowerShell.exe" `
    -Argument "-ExecutionPolicy Bypass -File `"$BootScript`" start" `
    -WorkingDirectory $ProjectDir

# Create the trigger (on system startup, with delay)
$Trigger = New-ScheduledTaskTrigger -AtStartup
$Trigger.Delay = "PT1M"  # Wait 1 minute after boot to allow system to stabilize

# Create settings
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

# Create principal (run as current user)
$Principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive `
    -RunLevel Highest

# Register the task
try {
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $Action `
        -Trigger $Trigger `
        -Settings $Settings `
        -Principal $Principal `
        -Description $TaskDescription | Out-Null
    
    Write-Host "✓ Auto-start task created successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Task Name: $TaskName" -ForegroundColor Cyan
    Write-Host "Trigger: On system startup (with 1 minute delay)" -ForegroundColor Cyan
    Write-Host "Action: Start Podman machine and containers" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "To verify:" -ForegroundColor Yellow
    Write-Host "  Get-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Gray
    Write-Host ""
    Write-Host "To remove:" -ForegroundColor Yellow
    Write-Host "  .\setup-podman-autostart.ps1 -Remove" -ForegroundColor Gray
    Write-Host ""
    Write-Host "To test manually:" -ForegroundColor Yellow
    Write-Host "  .\scripts\podman-boot-start.ps1 start" -ForegroundColor Gray
    
} catch {
    Write-Host "ERROR: Failed to create task: $_" -ForegroundColor Red
    exit 1
}

