# Docker Build and Push Script for Docker Hub
# Repository: zamaan2/schooolsystem

param(
    [string]$Tag = "latest",
    [switch]$NoBuild = $false,
    [switch]$NoPush = $false
)

$DOCKER_USERNAME = "zamaan2"
$REPOSITORY = "schooolsystem"
$IMAGE_NAME = "${DOCKER_USERNAME}/${REPOSITORY}:${Tag}"

Write-Host "===========================================" -ForegroundColor Cyan
Write-Host "Docker Build and Push Script" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host "Repository: $IMAGE_NAME" -ForegroundColor Yellow
Write-Host ""

# Check if Docker is running
Write-Host "Checking Docker..." -ForegroundColor Green
try {
    docker info | Out-Null
    Write-Host "✓ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}

# Build the image
if (-not $NoBuild) {
    Write-Host ""
    Write-Host "Building Docker image..." -ForegroundColor Green
    Write-Host "This may take several minutes..." -ForegroundColor Yellow
    
    docker build -t $IMAGE_NAME .
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "✗ Build failed!" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "✓ Build completed successfully!" -ForegroundColor Green
    
    # Also tag as latest if a different tag was specified
    if ($Tag -ne "latest") {
        $LATEST_TAG = "${DOCKER_USERNAME}/${REPOSITORY}:latest"
        Write-Host "Tagging as latest: $LATEST_TAG" -ForegroundColor Yellow
        docker tag $IMAGE_NAME $LATEST_TAG
    }
} else {
    Write-Host "Skipping build (--NoBuild specified)" -ForegroundColor Yellow
}

# Push to Docker Hub
if (-not $NoPush) {
    Write-Host ""
    Write-Host "Pushing to Docker Hub..." -ForegroundColor Green
    Write-Host "Make sure you're logged in: docker login" -ForegroundColor Yellow
    Write-Host ""
    
    # Check if logged in
    $loginCheck = docker system info 2>&1 | Select-String -Pattern "Username"
    if (-not $loginCheck) {
        Write-Host "You may need to login first. Running: docker login" -ForegroundColor Yellow
        docker login
        if ($LASTEXITCODE -ne 0) {
            Write-Host "✗ Login failed!" -ForegroundColor Red
            exit 1
        }
    }
    
    Write-Host "Pushing $IMAGE_NAME ..." -ForegroundColor Yellow
    docker push $IMAGE_NAME
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "✗ Push failed!" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "✓ Push completed successfully!" -ForegroundColor Green
    
    # Push latest tag if it was created
    if ($Tag -ne "latest") {
        $LATEST_TAG = "${DOCKER_USERNAME}/${REPOSITORY}:latest"
        Write-Host "Pushing $LATEST_TAG ..." -ForegroundColor Yellow
        docker push $LATEST_TAG
    }
} else {
    Write-Host "Skipping push (--NoPush specified)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "===========================================" -ForegroundColor Cyan
Write-Host "✓ Done!" -ForegroundColor Green
Write-Host "Image: $IMAGE_NAME" -ForegroundColor Yellow
Write-Host ""
Write-Host "To pull this image:" -ForegroundColor Cyan
Write-Host "  docker pull $IMAGE_NAME" -ForegroundColor White
Write-Host ""
Write-Host "To run this image:" -ForegroundColor Cyan
Write-Host "  docker run -p 8000:8000 --env-file .env $IMAGE_NAME" -ForegroundColor White
Write-Host "===========================================" -ForegroundColor Cyan



