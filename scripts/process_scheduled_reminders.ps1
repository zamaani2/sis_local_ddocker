# PowerShell script to process scheduled reminders

# Set the path to your Django project
$ProjectPath = "C:\Django\SchoolApp"

# Create logs directory if it doesn't exist
$LogsPath = Join-Path -Path $ProjectPath -ChildPath "logs"
if (-not (Test-Path -Path $LogsPath)) {
    New-Item -ItemType Directory -Path $LogsPath -Force
}

# Set log file path
$LogFile = Join-Path -Path $LogsPath -ChildPath "reminders.log"

# Navigate to the project directory
Set-Location -Path $ProjectPath

# Activate virtual environment if using one
# & "C:\path\to\venv\Scripts\Activate.ps1"

try {
    # Run the Django management command
    & python manage.py process_scheduled_reminders
    
    # Log success
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $LogFile -Value "$timestamp: Successfully processed scheduled reminders"
}
catch {
    # Log error
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $errorMessage = $_.Exception.Message
    Add-Content -Path $LogFile -Value "$timestamp: ERROR processing scheduled reminders - $errorMessage"
}

# Exit with success code
exit 0 