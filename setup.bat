# Quick Start Script for Windows
@echo off
echo ========================================
echo Django SchoolApp Docker Setup
echo ========================================
echo.

echo Step 1: Copying environment file...
if not exist .env (
    copy env.example .env
    echo Environment file created. Please edit .env with your settings.
) else (
    echo Environment file already exists.
)

echo.
echo Step 2: Starting Docker services...
docker-compose up -d

echo.
echo Step 3: Waiting for services to start...
timeout /t 30 /nobreak

echo.
echo Step 4: Running database migrations...
docker-compose exec django python manage.py migrate

echo.
echo Step 5: Creating superuser...
echo Please create a superuser account when prompted:
docker-compose exec django python manage.py createsuperuser

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Access your application at: http://localhost
echo Admin panel at: http://localhost/admin
echo.
echo To view logs: docker-compose logs -f
echo To stop services: docker-compose down
echo.
pause



