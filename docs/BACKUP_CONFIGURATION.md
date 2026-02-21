# Backup and Restore Configuration

## Overview

The School Management System now saves backup files to a local drive location (`C:\backups` by default) instead of inside the project directory. This makes it easier to access backup files when running the application in Docker containers.

## Configuration

### Default Backup Directory

- **Default Location**: `C:\backups`
- **Environment Variable**: `BACKUP_DIR`
- **Configuration**: Set in `SchoolApp/settings.py`

### Directory Structure

```
C:\backups\
├── school_slug_backup_YYYYMMDD_HHMMSS.zip  # Backup files
└── temp_uploads\                            # Temporary upload directory
    └── uploaded_backup_files.zip            # Files uploaded for restore
```

## Environment Configuration

### For Local Development

The system will automatically use `C:\backups` as the default backup directory.

### For Docker Deployment

Set the `BACKUP_DIR` environment variable to map a Docker volume:

```bash
# Example Docker run command
docker run -e BACKUP_DIR=/host/backups -v C:\backups:/host/backups your-app

# Or in docker-compose.yml
environment:
  - BACKUP_DIR=/host/backups
volumes:
  - C:\backups:/host/backups
```

### For Production

Set the `BACKUP_DIR` environment variable to your preferred backup location:

```bash
export BACKUP_DIR="/var/backups/schoolapp"
```

## Testing Backup Directory

Use the management command to test the backup directory configuration:

```bash
# Test basic configuration
python manage.py test_backup_directory

# Test with creating a test file
python manage.py test_backup_directory --create-test-file
```

## Benefits

1. **Docker Compatibility**: Backup files are stored outside the container, making them accessible from the host system
2. **Easy Access**: Users can easily navigate to `C:\backups` to find backup files
3. **Persistence**: Backup files persist even when containers are recreated
4. **Flexibility**: Backup directory can be configured via environment variables

## File Locations

- **Backup Files**: `C:\backups\school_slug_backup_YYYYMMDD_HHMMSS.zip`
- **Uploaded Files**: `C:\backups\temp_uploads\uploaded_file.zip`
- **Temporary Processing**: System creates temporary directories for processing (automatically cleaned up)

## Security Considerations

- Ensure the backup directory has appropriate permissions
- Consider encrypting sensitive backup files
- Regularly clean up old backup files
- Monitor disk space usage

## Troubleshooting

### Permission Issues

If you encounter permission issues:

1. Ensure the backup directory exists and is writable
2. Run the test command: `python manage.py test_backup_directory`
3. Check file system permissions on Windows

### Docker Volume Issues

If Docker can't access the backup directory:

1. Ensure the volume is properly mounted
2. Check Docker volume permissions
3. Verify the `BACKUP_DIR` environment variable is set correctly



