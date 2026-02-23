# Fix Podman volume permissions for SchoolApp (PowerShell)
# This script fixes permission issues with Podman volumes

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Fixing Podman Volume Permissions" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

$CONTAINER_NAME = "schoolapp_django"

# Check if container is running
$running = podman ps --format "{{.Names}}" | Select-String -Pattern "^${CONTAINER_NAME}$"
if (-not $running) {
    Write-Host "❌ Container ${CONTAINER_NAME} is not running!" -ForegroundColor Red
    Write-Host "Please start the container first: podman compose up -d" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Container ${CONTAINER_NAME} is running" -ForegroundColor Green
Write-Host ""

# Fix permissions inside the container
Write-Host "Fixing permissions inside container..." -ForegroundColor Yellow

$fixScript = @"
    # Ensure media directory exists and is writable
    mkdir -p /app/media/school_image /app/media/signatures /app/media/profile_pictures/teachers /app/media/profile_pictures/students
    chown -R django:django /app/media
    chmod -R 755 /app/media
    echo '✅ Media directory permissions fixed'
    
    # Ensure staticfiles directory is writable
    chown -R django:django /app/staticfiles
    chmod -R 755 /app/staticfiles
    echo '✅ Staticfiles directory permissions fixed'
    
    # Ensure logs directory is writable
    chown -R django:django /app/logs
    chmod -R 755 /app/logs
    echo '✅ Logs directory permissions fixed'
"@

podman exec -u root $CONTAINER_NAME bash -c $fixScript

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "✅ Permissions fixed successfully!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "You can now try uploading files again." -ForegroundColor Green

