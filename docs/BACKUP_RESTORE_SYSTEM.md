# Backup and Restore System Documentation

## Overview

The Backup and Restore system provides comprehensive data protection for the Multi-Tenant School Management System. It enables school administrators to securely backup their data and restore it from any location on the local drive, ensuring data isolation between different schools (tenants).

## Key Features

### ✅ Multi-Tenant Aware

- Each tenant's data is isolated and can be backed up and restored independently
- School-specific data filtering ensures no cross-tenant data leakage
- Tenant validation prevents restoring backups to wrong schools

### ✅ Local Storage Support

- Backups can be stored and restored from any location on the local drive
- Configurable backup directory via Django settings
- Support for custom backup file paths

### ✅ Secure Operations

- No data is left behind during backup and restore processes
- Automatic cleanup of temporary files
- Secure file handling with proper permissions

### ✅ Industry Standards

- Follows Django best practices for data serialization
- Uses ZIP compression for efficient storage
- Implements proper error handling and logging

## System Architecture

### Models

#### BackupOperation

Tracks backup operations with the following fields:

- `school`: Foreign key to SchoolInformation (tenant isolation)
- `created_by`: User who initiated the backup
- `backup_name`: Human-readable name for the backup
- `backup_file_path`: Full path to the backup file
- `backup_size`: Size of backup file in bytes
- `status`: Current status (pending, in_progress, completed, failed, cancelled)
- `includes_database`: Whether database records are included
- `includes_media_files`: Whether media files are included
- `includes_static_files`: Whether static files are included
- `database_records_count`: Number of database records backed up
- `media_files_count`: Number of media files backed up

#### RestoreOperation

Tracks restore operations with the following fields:

- `school`: Foreign key to SchoolInformation (tenant isolation)
- `created_by`: User who initiated the restore
- `backup_file_path`: Path to the backup file to restore from
- `status`: Current status (pending, in_progress, completed, failed, cancelled)
- `restore_database`: Whether to restore database records
- `restore_media_files`: Whether to restore media files
- `restore_static_files`: Whether to restore static files
- `backup_existing_data`: Whether to backup existing data before restore
- `restored_records_count`: Number of records restored
- `restored_files_count`: Number of files restored

### Services

#### BackupService

Handles backup operations for a specific school:

- `create_backup()`: Creates a comprehensive backup
- `list_backups()`: Lists all backups for the school
- `get_backup_info()`: Gets metadata about a backup file
- `validate_backup_file()`: Validates backup file integrity
- `delete_backup()`: Deletes backup file and record

#### RestoreService

Handles restore operations for a specific school:

- `restore_from_backup()`: Restores data from a backup file
- `get_restore_history()`: Gets restore operation history
- `validate_restore_compatibility()`: Validates backup compatibility

### Views

#### Backup Views

- `backup_dashboard`: Main backup management interface
- `create_backup`: Creates new backup (AJAX endpoint)
- `backup_status`: Gets backup operation status
- `download_backup`: Downloads backup file
- `delete_backup`: Deletes backup file

#### Restore Views

- `restore_dashboard`: Main restore management interface
- `upload_backup_file`: Uploads backup file for restore
- `restore_from_backup`: Performs restore operation
- `restore_status`: Gets restore operation status

#### Settings Views

- `backup_restore_settings`: Configuration interface
- `validate_backup_file`: Validates backup file compatibility

## User Interface

### Backup Dashboard

- Visual cards showing all backups with status indicators
- Progress indicators for in-progress operations
- Download and delete actions for completed backups
- Modal dialog for creating new backups with options

### Restore Dashboard

- Drag-and-drop file upload interface
- Backup file validation and information display
- Restore options configuration
- Restore history with detailed operation logs

### Settings Page

- Backup directory configuration
- Default backup/restore options
- System information and statistics
- Maintenance actions

## Security Features

### Access Control

- Admin-only access via `@admin_required` decorator
- School-specific data isolation
- User authentication and authorization

### Data Protection

- Automatic backup before restore operations
- Data integrity validation
- Secure file handling and cleanup

### Validation

- Backup file format validation
- School compatibility checks
- Django version compatibility verification

## Configuration

### Django Settings

```python
# Backup and Restore Settings
BACKUP_DIR = os.path.join(BASE_DIR, "backups")
BACKUP_RETENTION_DAYS = 30  # Keep backups for 30 days by default
BACKUP_MAX_SIZE_MB = 1000  # Maximum backup size in MB
BACKUP_COMPRESSION_LEVEL = 6  # ZIP compression level (1-9)
```

### URL Patterns

```python
# Backup and Restore URLs
path("backup/", backup_dashboard, name="backup_dashboard"),
path("backup/create/", create_backup, name="create_backup"),
path("backup/<int:backup_id>/status/", backup_status, name="backup_status"),
path("backup/<int:backup_id>/download/", download_backup, name="download_backup"),
path("backup/<int:backup_id>/delete/", delete_backup, name="delete_backup"),

path("restore/", restore_dashboard, name="restore_dashboard"),
path("restore/upload/", upload_backup_file, name="upload_backup_file"),
path("restore/restore/", restore_from_backup, name="restore_from_backup"),
path("restore/<int:restore_id>/status/", restore_status, name="restore_status"),

path("backup-restore/settings/", backup_restore_settings, name="backup_restore_settings"),
path("backup-restore/validate/", validate_backup_file, name="validate_backup_file"),
```

## Usage Instructions

### Creating a Backup

1. Navigate to Admin Dashboard
2. Click "Backup & Restore" in the sidebar
3. Click "Backup Management"
4. Click "Create New Backup"
5. Configure backup options:
   - Database Records (default: enabled)
   - Media Files (default: enabled)
   - Static Files (default: disabled)
6. Click "Create Backup"
7. Monitor progress and download when complete

### Restoring from Backup

1. Navigate to Admin Dashboard
2. Click "Backup & Restore" in the sidebar
3. Click "Restore Management"
4. Click "Restore from Backup"
5. Upload or drag-and-drop backup file
6. Review backup information
7. Configure restore options:
   - Database Records (default: enabled)
   - Media Files (default: enabled)
   - Static Files (default: disabled)
   - Backup Existing Data (default: enabled)
8. Click "Restore Data"
9. Monitor progress and review results

### Managing Backups

- View all backups in the backup dashboard
- Download completed backups
- Delete old or failed backups
- Monitor backup status and progress

## Technical Details

### Backup Process

1. Create BackupOperation record
2. Generate unique backup filename with timestamp
3. Create ZIP file with metadata
4. Serialize database records (school-specific filtering)
5. Copy media files to ZIP
6. Update operation record with completion status

### Restore Process

1. Validate backup file compatibility
2. Create RestoreOperation record
3. Extract backup to temporary directory
4. Create backup of existing data (if requested)
5. Clear existing school data
6. Restore database records in proper order
7. Restore media files
8. Update operation record with completion status

### Data Models Included

- User accounts and profiles
- Student and teacher records
- Academic years and terms
- Classes and subjects
- Assessments and scores
- Grading systems
- Departments and learning areas
- School information and signatures

## Error Handling

### Backup Errors

- File system permission issues
- Disk space limitations
- Database connection problems
- Serialization errors

### Restore Errors

- Invalid backup file format
- School compatibility issues
- Data integrity problems
- File system errors

### Recovery Procedures

- Automatic cleanup of failed operations
- Detailed error logging
- User-friendly error messages
- Rollback capabilities for failed restores

## Performance Considerations

### Backup Performance

- Efficient database serialization
- ZIP compression for file storage
- Progress tracking for large operations
- Background processing capabilities

### Restore Performance

- Atomic transactions for data integrity
- Proper model ordering for foreign key relationships
- Batch processing for large datasets
- Memory-efficient file handling

## Maintenance

### Regular Tasks

- Monitor backup storage usage
- Clean up old backup files
- Verify backup integrity
- Update backup retention policies

### Troubleshooting

- Check Django logs for errors
- Verify file system permissions
- Monitor database performance
- Review backup/restore operation logs

## Future Enhancements

### Planned Features

- Automated backup scheduling
- Cloud storage integration
- Incremental backup support
- Backup encryption
- Multi-threaded processing
- Backup verification tools

### Integration Opportunities

- Email notifications for backup completion
- Integration with monitoring systems
- API endpoints for external tools
- Command-line management interface

## Support and Documentation

### Getting Help

- Check Django logs for detailed error information
- Review backup/restore operation records
- Verify school and user permissions
- Test with small datasets first

### Best Practices

- Regular backup testing
- Multiple backup locations
- Document restore procedures
- Train administrators on usage
- Monitor system performance

---

**System Status**: ✅ Fully Implemented and Tested
**Last Updated**: October 10, 2025
**Version**: 1.0.0
