#!/bin/bash
# Fix Podman volume permissions for SchoolApp
# This script fixes permission issues with Podman volumes

set -e

echo "=========================================="
echo "Fixing Podman Volume Permissions"
echo "=========================================="

# Get the container name
CONTAINER_NAME="schoolapp_django"

# Check if container is running
if ! podman ps --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$"; then
    echo "❌ Container ${CONTAINER_NAME} is not running!"
    echo "Please start the container first: podman compose up -d"
    exit 1
fi

echo "✅ Container ${CONTAINER_NAME} is running"

# Fix permissions inside the container
echo "Fixing permissions inside container..."
podman exec -u root ${CONTAINER_NAME} bash -c "
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
"

echo ""
echo "=========================================="
echo "✅ Permissions fixed successfully!"
echo "=========================================="
echo ""
echo "You can now try uploading files again."

