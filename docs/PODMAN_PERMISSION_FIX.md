# Podman Permission Fix Guide

## Problem
When running the SchoolApp in Podman, you may encounter permission errors when uploading files (school logos, signatures, etc.):

```
PermissionError: [Errno 13] Permission denied: '/app/media/static'
```

This happens because Podman handles volume permissions differently than Docker Desktop.

## Solution Options

### Option 1: Run Container as Root (Recommended for Podman)

Set the container to run as root user in Podman:

```powershell
# Set environment variable
$env:DJANGO_CONTAINER_USER="0:0"

# Restart containers
podman compose down
podman compose up -d
```

Or add to your `.env` file:
```
DJANGO_CONTAINER_USER=0:0
```

### Option 2: Fix Permissions After Starting

Use the provided script to fix permissions:

**PowerShell:**
```powershell
.\scripts\fix-podman-permissions.ps1
```

**Bash/Linux:**
```bash
chmod +x scripts/fix-podman-permissions.sh
./scripts/fix-podman-permissions.sh
```

### Option 3: Manual Permission Fix

If the scripts don't work, fix permissions manually:

```powershell
# Fix permissions inside the running container
podman exec -u root schoolapp_django bash -c "
    mkdir -p /app/media/school_image /app/media/signatures /app/media/profile_pictures/teachers /app/media/profile_pictures/students
    chown -R django:django /app/media
    chmod -R 755 /app/media
    chown -R django:django /app/staticfiles
    chmod -R 755 /app/staticfiles
    chown -R django:django /app/logs
    chmod -R 755 /app/logs
"
```

## Run Migration

After fixing permissions, ensure the migration has run:

```powershell
podman compose exec django python manage.py migrate
```

This will apply the migration that fixes the upload paths (removes `static/` from paths).

## Verify Fix

1. Check that migration `0003_update_upload_paths` has been applied:
   ```powershell
   podman compose exec django python manage.py showmigrations shs_system
   ```

2. Try uploading a school logo or signature again.

## Why This Happens

- **Docker Desktop**: Automatically handles volume permissions, allowing the `django` user to write to volumes
- **Podman**: Uses different volume mounting that may preserve host permissions, causing permission denied errors for non-root users

## Permanent Fix

For a permanent fix, add to your `.env` file:

```
# Podman: Use root user to avoid volume permission issues
DJANGO_CONTAINER_USER=0:0
```

**Note**: Running as root in containers is generally acceptable for development, but for production, consider using proper volume permission management or rootless Podman with proper configuration.



