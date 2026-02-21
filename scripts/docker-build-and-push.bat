@echo off
REM Docker Build and Push Script for Docker Hub
REM Repository: zamaan2/schooolsystem

setlocal enabledelayedexpansion

REM Default tag
set TAG=latest
if not "%1"=="" set TAG=%1

set DOCKER_USERNAME=zamaan2
set REPOSITORY=schooolsystem
set IMAGE_NAME=%DOCKER_USERNAME%/%REPOSITORY%:%TAG%

echo ===========================================
echo Docker Build and Push Script
echo ===========================================
echo Repository: %IMAGE_NAME%
echo.

REM Check if Docker is running
echo Checking Docker...
docker info >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not running. Please start Docker Desktop.
    exit /b 1
)
echo Docker is running
echo.

REM Build the image
echo Building Docker image...
echo This may take several minutes...
echo.

docker build -t %IMAGE_NAME% .

if errorlevel 1 (
    echo ERROR: Build failed!
    exit /b 1
)

echo.
echo Build completed successfully!
echo.

REM Also tag as latest if a different tag was specified
if not "%TAG%"=="latest" (
    set LATEST_TAG=%DOCKER_USERNAME%/%REPOSITORY%:latest
    echo Tagging as latest: !LATEST_TAG!
    docker tag %IMAGE_NAME% !LATEST_TAG!
)

REM Push to Docker Hub
echo.
echo Pushing to Docker Hub...
echo Make sure you're logged in: docker login
echo.

echo Pushing %IMAGE_NAME% ...
docker push %IMAGE_NAME%

if errorlevel 1 (
    echo ERROR: Push failed! Make sure you're logged in with: docker login
    exit /b 1
)

echo.
echo Push completed successfully!
echo.

REM Push latest tag if it was created
if not "%TAG%"=="latest" (
    set LATEST_TAG=%DOCKER_USERNAME%/%REPOSITORY%:latest
    echo Pushing !LATEST_TAG! ...
    docker push !LATEST_TAG!
)

echo.
echo ===========================================
echo Done!
echo Image: %IMAGE_NAME%
echo.
echo To pull this image:
echo   docker pull %IMAGE_NAME%
echo.
echo To run this image:
echo   docker run -p 8000:8000 --env-file .env %IMAGE_NAME%
echo ===========================================

endlocal



