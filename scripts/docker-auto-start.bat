@echo off
REM Docker Auto-Start Script for SchoolApp (Windows)
REM This script ensures Docker containers start automatically on system boot

setlocal enabledelayedexpansion

REM Configuration
set COMPOSE_FILE=docker-compose.yml
set PROJECT_NAME=schoolapp
set LOG_FILE=%TEMP%\schoolapp-startup.log

REM Function to log messages
:log_message
echo %date% %time% - %~1 >> "%LOG_FILE%"
echo %date% %time% - %~1
goto :eof

REM Function to check if Docker is running
:check_docker
docker info >nul 2>&1
if %errorlevel% neq 0 (
    call :log_message "ERROR: Docker is not running. Please start Docker Desktop."
    exit /b 1
)
call :log_message "Docker is running"
exit /b 0

REM Function to check if containers are already running
:check_containers
for /f %%i in ('docker ps --filter "name=%PROJECT_NAME%" --format "{{.Names}}" ^| find /c /v ""') do set running_containers=%%i
if %running_containers% gtr 0 (
    call :log_message "Containers are already running"
    exit /b 0
)
exit /b 1

REM Function to start containers
:start_containers
call :log_message "Starting SchoolApp containers..."

REM Change to the project directory
cd /d "%~dp0.."

REM Start containers in detached mode
docker-compose up -d

REM Wait a moment for services to start
timeout /t 10 /nobreak >nul

REM Check container status
call :log_message "Checking container status..."
docker-compose ps

call :log_message "SUCCESS: SchoolApp containers started"
echo ✓ SchoolApp is now running at http://localhost:8000
exit /b 0

REM Function to stop containers
:stop_containers
call :log_message "Stopping SchoolApp containers..."
cd /d "%~dp0.."
docker-compose down
call :log_message "Containers stopped"
exit /b 0

REM Main execution
:main
call :log_message "=== SchoolApp Docker Auto-Start Script (Windows) ==="

if "%1"=="start" goto :start_action
if "%1"=="stop" goto :stop_action
if "%1"=="restart" goto :restart_action
if "%1"=="status" goto :status_action
goto :usage

:start_action
call :check_docker
if %errorlevel% neq 0 exit /b 1

call :check_containers
if %errorlevel% equ 0 (
    call :log_message "Containers are already running. Nothing to do."
    exit /b 0
)

call :start_containers
exit /b %errorlevel%

:stop_action
call :stop_containers
exit /b 0

:restart_action
call :stop_containers
timeout /t 5 /nobreak >nul
call :start_containers
exit /b %errorlevel%

:status_action
call :check_docker
if %errorlevel% neq 0 exit /b 1
cd /d "%~dp0.."
docker-compose ps
exit /b 0

:usage
echo Usage: %0 {start^|stop^|restart^|status}
exit /b 1

REM Run main function
call :main %1
