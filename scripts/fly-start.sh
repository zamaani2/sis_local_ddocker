#!/bin/bash
# Startup script for Fly.io deployment
# This script runs migrations and collects static files before starting the server

set -e

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --settings=${DJANGO_SETTINGS_MODULE:-SchoolApp.settings_fly} --noinput

# Collect static files (if not already done in Dockerfile)
echo "Collecting static files..."
python manage.py collectstatic --settings=${DJANGO_SETTINGS_MODULE:-SchoolApp.settings_fly} --noinput || true

# Start Gunicorn
echo "Starting Gunicorn..."
exec gunicorn \
    --bind 0.0.0.0:8000 \
    --workers ${GUNICORN_WORKERS:-3} \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    SchoolApp.wsgi:application

