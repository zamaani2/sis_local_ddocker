# Podman Boot Start Script for SchoolApp
# This script ensures Podman machine and containers start automatically on Windows boot
# Designed to be run by Windows Task Scheduler

param(
    [Parameter(Position=0)]
    [ValidateSet("start", "stop", "status")]
    [string]$Action = "start"
)

# Configuration
$ProjectDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.PSCommandPath)
$LogFile = "$env:TEMP\schoolapp-podman-boot.log"
$MaxWaitTime = 120  # Maximum seconds to wait for Podman machine to start

# Function to log messages
function Write-LogMessage {
    param([string]$Message)
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogEntry = "$Timestamp - $Message"
    Write-Host $LogEntry
    Add-Content -Path $LogFile -Value $LogEntry
}

# Function to wait for Podman machine to be ready
function Wait-ForPodmanMachine {
    $Attempt = 0
    $MaxAttempts = $MaxWaitTime / 5  # Check every 5 seconds
    
    Write-LogMessage "Waiting for Podman machine to be ready..."
    
    while ($Attempt -lt $MaxAttempts) {
        try {
            podman info | Out-Null
            Write-LogMessage "Podman machine is ready"
            return $true
        } catch {
            $Attempt++
            if ($Attempt -lt $MaxAttempts) {
                Start-Sleep -Seconds 5
                Write-LogMessage "Attempt $Attempt/$MaxAttempts - Waiting for Podman machine..."
            }
        }
    }
    
    Write-LogMessage "ERROR: Podman machine did not become ready within $MaxWaitTime seconds"
    return $false
}

# Function to start Podman machine
function Start-PodmanMachine {
    Write-LogMessage "Checking Podman machine status..."
    
    # Check if machine exists
    $MachineList = podman machine list 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-LogMessage "ERROR: Failed to list Podman machines"
        return $false
    }
    
    # Check if machine is already running
    if ($MachineList -match "Currently running") {
        Write-LogMessage "Podman machine is already running"
        return $true
    }
    
    # Start the machine
    Write-LogMessage "Starting Podman machine..."
    try {
        podman machine start 2>&1 | Out-String | ForEach-Object { Write-LogMessage $_ }
        
        if ($LASTEXITCODE -eq 0) {
            Write-LogMessage "Podman machine started successfully"
            return Wait-ForPodmanMachine
        } else {
            Write-LogMessage "ERROR: Failed to start Podman machine"
            return $false
        }
    } catch {
        Write-LogMessage "ERROR: Exception while starting Podman machine: $_"
        return $false
    }
}

# Function to start containers
function Start-Containers {
    Write-LogMessage "Starting SchoolApp containers..."
    
    Set-Location $ProjectDir
    
    # Use the podman-auto-start script
    $AutoStartScript = Join-Path $ProjectDir "scripts\podman-auto-start.ps1"
    
    if (Test-Path $AutoStartScript) {
        & $AutoStartScript start
        if ($LASTEXITCODE -eq 0) {
            Write-LogMessage "SUCCESS: Containers started successfully"
            return $true
        } else {
            Write-LogMessage "ERROR: Failed to start containers"
            return $false
        }
    } else {
        Write-LogMessage "ERROR: podman-auto-start.ps1 not found at $AutoStartScript"
        return $false
    }
}

# Function to stop containers and machine
function Stop-All {
    Write-LogMessage "Stopping SchoolApp containers and Podman machine..."
    
    Set-Location $ProjectDir
    
    # Stop containers first
    $AutoStartScript = Join-Path $ProjectDir "scripts\podman-auto-start.ps1"
    if (Test-Path $AutoStartScript) {
        & $AutoStartScript stop
    }
    
    # Stop Podman machine
    Write-LogMessage "Stopping Podman machine..."
    podman machine stop 2>&1 | Out-String | ForEach-Object { Write-LogMessage $_ }
    
    Write-LogMessage "All services stopped"
}

# Main execution
Write-LogMessage "=== SchoolApp Podman Boot Start Script ==="
Write-LogMessage "Action: $Action"

switch ($Action) {
    "start" {
        # Step 1: Start Podman machine
        if (-not (Start-PodmanMachine)) {
            Write-LogMessage "ERROR: Failed to start Podman machine. Exiting."
            exit 1
        }
        
        # Step 2: Wait a bit for machine to fully initialize
        Start-Sleep -Seconds 5
        
        # Step 3: Start containers
        if (-not (Start-Containers)) {
            Write-LogMessage "ERROR: Failed to start containers"
            exit 1
        }
        
        Write-LogMessage "SUCCESS: Podman machine and containers started successfully"
        Write-Host "✓ SchoolApp is ready at http://localhost:8000" -ForegroundColor Green
    }
    "stop" {
        Stop-All
    }
    "status" {
        Write-LogMessage "Checking Podman machine status..."
        podman machine list
        
        Write-LogMessage "Checking container status..."
        Set-Location $ProjectDir
        $AutoStartScript = Join-Path $ProjectDir "scripts\podman-auto-start.ps1"
        if (Test-Path $AutoStartScript) {
            & $AutoStartScript status
        }
    }
    default {
        Write-Host "Usage: .\podman-boot-start.ps1 {start|stop|status}"
        exit 1
    }
}

