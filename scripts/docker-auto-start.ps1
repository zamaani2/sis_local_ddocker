# Docker Auto-Start PowerShell Script for SchoolApp
# This script ensures Docker containers start automatically on system boot

param(
    [Parameter(Position=0)]
    [ValidateSet("start", "stop", "restart", "status")]
    [string]$Action = "start"
)

# Configuration
$ComposeFile = "docker-compose.yml"
$ProjectName = "schoolapp"
$LogFile = "$env:TEMP\schoolapp-startup.log"

# Function to log messages
function Write-LogMessage {
    param([string]$Message)
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogEntry = "$Timestamp - $Message"
    Write-Host $LogEntry
    Add-Content -Path $LogFile -Value $LogEntry
}

# Function to check if Docker is running
function Test-DockerRunning {
    try {
        docker info | Out-Null
        Write-LogMessage "Docker is running"
        return $true
    }
    catch {
        Write-LogMessage "ERROR: Docker is not running. Please start Docker Desktop."
        return $false
    }
}

# Function to check if containers are already running
function Test-ContainersRunning {
    try {
        $RunningContainers = docker ps --filter "name=$ProjectName" --format "{{.Names}}" | Measure-Object | Select-Object -ExpandProperty Count
        if ($RunningContainers -gt 0) {
            Write-LogMessage "Containers are already running"
            return $true
        }
        return $false
    }
    catch {
        return $false
    }
}

# Function to start containers
function Start-Containers {
    Write-LogMessage "Starting SchoolApp containers..."
    
    # Change to the project directory
    $ScriptDir = Split-Path -Parent $MyInvocation.PSCommandPath
    $ProjectDir = Split-Path -Parent $ScriptDir
    Set-Location $ProjectDir
    
    # Start containers in detached mode
    docker-compose up -d
    
    # Wait for services to start
    Start-Sleep -Seconds 10
    
    # Check container status
    Write-LogMessage "Checking container status..."
    docker-compose ps
    
    Write-LogMessage "SUCCESS: SchoolApp containers started"
    Write-Host "✓ SchoolApp is now running at http://localhost:8000" -ForegroundColor Green
}

# Function to stop containers
function Stop-Containers {
    Write-LogMessage "Stopping SchoolApp containers..."
    $ScriptDir = Split-Path -Parent $MyInvocation.PSCommandPath
    $ProjectDir = Split-Path -Parent $ScriptDir
    Set-Location $ProjectDir
    docker-compose down
    Write-LogMessage "Containers stopped"
}

# Main execution
Write-LogMessage "=== SchoolApp Docker Auto-Start Script (PowerShell) ==="

switch ($Action) {
    "start" {
        if (-not (Test-DockerRunning)) {
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
        if (-not (Test-DockerRunning)) {
            exit 1
        }
        $ScriptDir = Split-Path -Parent $MyInvocation.PSCommandPath
        $ProjectDir = Split-Path -Parent $ScriptDir
        Set-Location $ProjectDir
        docker-compose ps
    }
    default {
        Write-Host "Usage: .\docker-auto-start.ps1 {start|stop|restart|status}"
        exit 1
    }
}
