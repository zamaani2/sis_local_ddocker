# Super Admin Backup & Restore System

## Overview

The Super Admin Backup & Restore system provides enhanced functionality for Super Admins to manage backup and restore operations across all schools in the system. Unlike the regular school admin backup system, Super Admins can:

1. **Restore backups to existing schools** - Update data for schools that already exist
2. **Create new schools from backups** - Import backup data as a completely new school
3. **Override school validation** - Restore any backup to any school, even if the school doesn't exist

## Key Features

### ✅ Enhanced Restore Capabilities

- **Restore to Existing Schools**: Update existing school data with backup content
- **Create New Schools**: Generate new schools from backup data
- **Cross-School Restore**: Restore backups from one school to another
- **Flexible School Creation**: Automatically create school domains and admin users

### ✅ Comprehensive Management

- **Centralized Dashboard**: View all backup and restore operations across all schools
- **Real-time Status Monitoring**: Track restore progress with live updates
- **Detailed Operation History**: Complete audit trail of all operations
- **File Validation**: Automatic backup file validation before restore

### ✅ Safety Features

- **Pre-restore Backups**: Automatically backup existing data before restore
- **Transaction Safety**: Each restore operation is wrapped in database transactions
- **Error Handling**: Comprehensive error handling with detailed error messages
- **Admin User Preservation**: Preserve existing admin users during restore

## Usage Guide

### Accessing the System

1. **Login** as a Super Admin user
2. **Navigate** to the Super Admin dashboard
3. **Click** "Backup & Restore" in the sidebar navigation
4. **Access** the centralized backup and restore management interface

### Restoring to an Existing School

1. **Click** "Restore to Existing School" on the dashboard
2. **Upload** the backup file (ZIP format)
3. **Select** the target school from the dropdown
4. **Configure** restore options:
   - Database Records (recommended)
   - Media Files (recommended)
   - Static Files (optional)
   - Backup Existing Data (recommended)
5. **Click** "Start Restore" to begin the operation
6. **Monitor** progress on the status page

### Creating a New School from Backup

1. **Click** "Create New School from Backup" on the dashboard
2. **Upload** the backup file (ZIP format)
3. **Enter** new school information:
   - School Name
   - School Domain
   - Admin Name
   - Admin Email
4. **Configure** restore options (same as above)
5. **Click** "Create School & Restore" to begin
6. **Monitor** progress on the status page

### Monitoring Operations

- **Dashboard**: Overview of all operations across all schools
- **Status Pages**: Detailed progress monitoring for individual operations
- **Operation History**: Complete history of all backup and restore operations
- **School-specific Views**: View operations for specific schools

## Technical Details

### File Structure

```
super_admin/
├── services.py                    # SuperAdminRestoreService
├── backup_restore_views.py        # View functions
├── backup_restore_forms.py        # Form classes
├── templates/super_admin/backup_restore/
│   ├── dashboard.html             # Main dashboard
│   ├── restore_form.html         # Restore form
│   ├── restore_status.html       # Status monitoring
│   ├── all_backups.html          # All backups list
│   └── all_restores.html         # All restores list
└── templatetags/super_admin_tags.py  # Template filters
```

### Key Components

#### SuperAdminRestoreService

- **Enhanced validation**: No school-specific restrictions
- **Flexible restore**: Support for both existing and new schools
- **Comprehensive data handling**: Database, media, and static files
- **Error handling**: Detailed error reporting and recovery

#### Restore Views

- **Dashboard**: Centralized management interface
- **Restore Forms**: Separate forms for existing vs new school restore
- **Status Monitoring**: Real-time progress tracking
- **File Management**: Upload, validation, and cleanup

#### Forms

- **SuperAdminRestoreForm**: For restoring to existing schools
- **SuperAdminNewSchoolRestoreForm**: For creating new schools
- **Validation**: File format, size, and school uniqueness checks

### Database Operations

The restore process follows a specific order to maintain referential integrity:

1. **School Information** (for new schools)
2. **Academic Years & Terms**
3. **Departments & Learning Areas**
4. **Forms & Classes**
5. **Subjects & Teachers**
6. **Students & Users**
7. **Grading Systems**
8. **School Authority Signatures**
9. **Class Subjects & Student Classes**
10. **Assessments & Teacher Assignments**
11. **Attendance Records**
12. **Performance Requirements**
13. **Student Term Remarks**
14. **Report Cards**
15. **Scheduled Reminders**
16. **Scoring Configurations**
17. **Backup & Restore Operations**
18. **Academic Year Templates**
19. **Class Teachers**

### Security Considerations

- **Super Admin Only**: All operations require Super Admin privileges
- **File Validation**: Comprehensive backup file validation
- **Transaction Safety**: All operations wrapped in database transactions
- **Error Recovery**: Graceful handling of restore failures
- **Data Preservation**: Existing admin users are preserved during restore

## Error Handling

The system provides comprehensive error handling:

- **File Validation Errors**: Invalid file format, size, or corruption
- **School Creation Errors**: Duplicate names, domains, or emails
- **Database Errors**: Foreign key constraints, duplicate records
- **File System Errors**: Permission issues, disk space
- **Network Errors**: Timeout, connection issues

All errors are logged and displayed to the user with actionable information.

## Best Practices

1. **Always backup existing data** before restoring
2. **Validate backup files** before starting restore operations
3. **Monitor restore progress** and check for errors
4. **Test restore operations** in a development environment first
5. **Keep backup files** in a secure location
6. **Document restore operations** for audit purposes

## Troubleshooting

### Common Issues

1. **File Upload Errors**: Check file size limits and format
2. **School Creation Failures**: Verify school name and domain uniqueness
3. **Database Errors**: Check foreign key constraints and data integrity
4. **Permission Errors**: Ensure proper file system permissions

### Support

For technical support or issues:

1. Check the operation logs for detailed error messages
2. Verify backup file integrity
3. Ensure sufficient disk space and permissions
4. Contact system administrator for complex issues

## Future Enhancements

Potential future improvements:

- **Bulk Operations**: Restore multiple backups simultaneously
- **Scheduled Restores**: Automated restore operations
- **Advanced Filtering**: Filter operations by date, school, status
- **Export Reports**: Generate restore operation reports
- **API Integration**: REST API for programmatic access
