# Podman Auto-Start PowerShell Script for SchoolApp
# This script ensures Podman containers start automatically on system boot

param(
    [Parameter(Position=0)]
    [ValidateSet("start", "stop", "restart", "status")]
    [string]$Action = "start"
)

# Configuration
$ComposeFile = "docker-compose.yml"
$ProjectName = "schoolapp"
$LogFile = "$env:TEMP\schoolapp-podman-startup.log"

# Function to log messages
function Write-LogMessage {
    param([string]$Message)
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogEntry = "$Timestamp - $Message"
    Write-Host $LogEntry
    Add-Content -Path $LogFile -Value $LogEntry
}

# Function to check if Podman is available and running
function Test-PodmanRunning {
    # Check if podman command exists
    if (-not (Get-Command podman -ErrorAction SilentlyContinue)) {
        Write-LogMessage "ERROR: Podman is not installed. Please install Podman Desktop first."
        Write-LogMessage "Download from: https://podman-desktop.io"
        return $false
    }
    
    # Check if podman-compose is available
    if (-not (Get-Command podman-compose -ErrorAction SilentlyContinue)) {
        # Try podman compose (v2 syntax)
        try {
            podman compose version | Out-Null
            $script:UsePodmanComposeV2 = $true
            Write-LogMessage "Found podman compose (v2). Using podman compose commands."
        } catch {
            Write-LogMessage "WARNING: podman-compose is not available."
            Write-LogMessage "Installation: pip install podman-compose"
            Write-LogMessage "Or use: podman compose (v2) - ensure Podman Desktop is running"
            # Continue anyway, user might have podman compose v2
            $script:UsePodmanComposeV2 = $true
        }
    } else {
        $script:UsePodmanComposeV2 = $false
    }
    
    # Check if Podman is accessible
    try {
        podman info | Out-Null
        Write-LogMessage "Podman is running"
        return $true
    } catch {
        Write-LogMessage "ERROR: Podman is not accessible. Please start Podman Desktop."
        Write-LogMessage "Note: On Windows, Podman Desktop must be running."
        return $false
    }
}

# Function to get the compose command
function Get-ComposeCommand {
    if ($script:UsePodmanComposeV2) {
        return "podman", "compose"
    } else {
        return "podman-compose"
    }
}

# Function to check if containers are already running
function Test-ContainersRunning {
    try {
        $RunningContainers = podman ps --filter "name=$ProjectName" --format "{{.Names}}" | Measure-Object | Select-Object -ExpandProperty Count
        if ($RunningContainers -gt 0) {
            Write-LogMessage "Containers are already running"
            return $true
        }
        return $false
    } catch {
        return $false
    }
}

# Function to start containers
function Start-Containers {
    Write-LogMessage "Starting SchoolApp containers with Podman..."
    
    # Change to the project directory
    $ScriptDir = Split-Path -Parent $MyInvocation.PSCommandPath
    $ProjectDir = Split-Path -Parent $ScriptDir
    Set-Location $ProjectDir
    
    $ComposeCmd = Get-ComposeCommand
    
    # Start containers in detached mode
    if ($ComposeCmd -is [array]) {
        & $ComposeCmd[0] $ComposeCmd[1] up -d
    } else {
        & $ComposeCmd up -d
    }
    
    # Wait for services to start
    Start-Sleep -Seconds 10
    
    # Check container status
    Write-LogMessage "Checking container status..."
    if ($ComposeCmd -is [array]) {
        & $ComposeCmd[0] $ComposeCmd[1] ps
    } else {
        & $ComposeCmd ps
    }
    
    Write-LogMessage "SUCCESS: SchoolApp containers started with Podman"
    Write-Host "✓ SchoolApp is now running at http://localhost:8000" -ForegroundColor Green
}

# Function to stop containers
function Stop-Containers {
    Write-LogMessage "Stopping SchoolApp containers..."
    $ScriptDir = Split-Path -Parent $MyInvocation.PSCommandPath
    $ProjectDir = Split-Path -Parent $ScriptDir
    Set-Location $ProjectDir
    
    $ComposeCmd = Get-ComposeCommand
    
    if ($ComposeCmd -is [array]) {
        & $ComposeCmd[0] $ComposeCmd[1] down
    } else {
        & $ComposeCmd down
    }
    
    Write-LogMessage "Containers stopped"
}

# Main execution
Write-LogMessage "=== SchoolApp Podman Auto-Start Script (PowerShell) ==="

switch ($Action) {
    "start" {
        if (-not (Test-PodmanRunning)) {
            exit 1
        }
        
        if (Test-ContainersRunning) {
            Write-LogMessage "Containers are already running. Nothing to do."
            exit 0
        }
        
        Start-Containers
    }
    "stop" {
        Stop-Containers
    }
    "restart" {
        Stop-Containers
        Start-Sleep -Seconds 5
        Start-Containers
    }
    "status" {
        if (-not (Test-PodmanRunning)) {
            exit 1
        }
        $ScriptDir = Split-Path -Parent $MyInvocation.PSCommandPath
        $ProjectDir = Split-Path -Parent $ScriptDir
        Set-Location $ProjectDir
        
        $ComposeCmd = Get-ComposeCommand
        if ($ComposeCmd -is [array]) {
            & $ComposeCmd[0] $ComposeCmd[1] ps
        } else {
            & $ComposeCmd ps
        }
    }
    default {
        Write-Host "Usage: .\podman-auto-start.ps1 {start|stop|restart|status}"
        exit 1
    }
}


