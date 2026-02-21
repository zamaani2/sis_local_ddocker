# School Backup & Restore System

## Overview

A comprehensive, school-specific backup and restore system for the multi-tenant SchoolApp. Simple to use via web interface or command line, with the ability to save backups anywhere on your computer.

## ✨ Features

- ✅ **School-Specific Backups**: Each school's data is backed up independently
- 💾 **Save Anywhere**: Save backups to any location on your hard disk
- 🌐 **Web Interface**: Easy-to-use web dashboard for backup/restore operations
- 💻 **Command Line**: Full CLI support for automation
- 🖼️ **Media Files**: Optional inclusion of images and documents
- 🔄 **Multiple Restore Modes**: Merge, Replace, or Create New school
- 🔐 **Access Control**: Only admins and principals can access
- 📦 **Compressed Format**: ZIP files for efficient storage
- 🚀 **Efficient**: Uses Django serialization for MySQL database

## 🚀 Quick Start

### Using Web Interface

1. **Login** as Admin or Principal
2. **Navigate** to `/backup-restore/`
3. **Create Backup**:
   - Check options (include media files)
   - Enter custom save path (optional)
   - Click "Create Backup Now"
4. **Download or Restore** as needed

### Using Command Line

**Create Backup:**
```bash
python manage.py backup_school myschool --output "C:\Backups" --include-media
```

**Restore Backup:**
```bash
python manage.py restore_school "C:\Backups\backup_myschool_20231104.zip" --mode merge
```

## 📋 What's Included

### Data Backed Up
- School information and settings
- Academic years, terms, forms
- Students (active and archived)
- Teachers and staff
- Classes and subjects
- Teacher assignments
- Student enrollments
- Assessments and scores
- Report cards and remarks
- Attendance records
- Grading systems
- Departments and learning areas

### Optional: Media Files
- School logos and stamps
- Student profile pictures
- Teacher profile pictures
- Authority signatures

## 📁 Files Created

### Management Commands
- `shs_system/management/commands/backup_school.py` - Backup command
- `shs_system/management/commands/restore_school.py` - Restore command

### Views
- `shs_system/views/backup_restore.py` - Web interface views

### Templates
- `shs_system/templates/school/backup_restore.html` - Main interface
- `shs_system/templates/super_admin/backup_all_schools.html` - Bulk backup interface

### Documentation
- `docs/BACKUP_RESTORE_GUIDE.md` - Complete documentation
- `docs/BACKUP_QUICK_START.md` - Quick reference guide
- `README_BACKUP_SYSTEM.md` - This file

## 🔧 Configuration

### URLs Added

```python
# In shs_system/urls.py
path("backup-restore/", backup_restore_dashboard, name="backup_restore_dashboard"),
path("backup/create/", create_backup, name="create_backup"),
path("backup/download/<str:filename>/", download_backup, name="download_backup"),
path("backup/restore/", restore_backup, name="restore_backup"),
path("backup/delete/<str:filename>/", delete_backup, name="delete_backup"),
path("backup/super-admin/all/", super_admin_backup_all, name="super_admin_backup_all"),
```

### Default Backup Directory

Backups are saved to: `{BASE_DIR}/backups/`

You can specify any custom directory when creating backups.

## 📖 Usage Examples

### Example 1: Daily Automated Backup

```bash
# Windows
cd C:\Django\SchoolApp
python manage.py backup_school greenvalley --output "D:\DailyBackups"
```

### Example 2: Full Backup with Media

```bash
python manage.py backup_school myschool --output "C:\Backups\Full" --include-media
```

### Example 3: Restore After Data Loss

```bash
python manage.py restore_school "C:\Backups\backup_myschool_20231104.zip" --mode replace
```

### Example 4: Clone School Setup

```bash
# Backup template school
python manage.py backup_school template --output "C:\Backups"

# Create new school from backup
python manage.py restore_school "C:\Backups\backup_template.zip" --mode new --new-slug newschool
```

### Example 5: Migrate to New Server

```bash
# On old server
python manage.py backup_school myschool --output "C:\Transfer" --include-media

# Copy backup file to new server

# On new server
python manage.py restore_school "backup_myschool.zip" --mode merge
```

## 🔐 Security & Permissions

### Access Control
- **Web Interface**: Requires login with admin, principal, or super_admin role
- **Command Line**: Requires database access

### Best Practices
1. Store backups on encrypted drives
2. Secure backup directories (not in public web folders)
3. Use proper file permissions
4. Regularly test restore procedures
5. Keep backups in multiple locations

## 🛠️ Automation

### Windows Task Scheduler

Create `backup_daily.bat`:
```batch
@echo off
cd C:\Django\SchoolApp
python manage.py backup_school myschool --output "C:\Backups\Daily"
```

Schedule it to run daily at 2 AM.

### Linux Cron Job

Add to crontab:
```bash
0 2 * * * cd /var/www/SchoolApp && python manage.py backup_school myschool --output "/backups/daily"
```

## 🎯 Restore Modes

### Merge Mode (Default, Safest)
- Adds backup data to existing data
- No data deletion
- Use when: Importing data from another source

### Replace Mode (Dangerous!)
- Deletes ALL existing school data first
- Then restores from backup
- ⚠️ Use with extreme caution!
- Use when: Complete disaster recovery needed

### New Mode (Create Copy)
- Creates a brand new school from backup
- Requires a new unique slug
- Use when: Cloning school setup

## 📊 Backup File Structure

```
backup_schoolslug_timestamp.zip
├── metadata.json              # Backup information
├── school.json                # School details
├── students.json              # Student records
├── teachers.json              # Teacher records
├── classes.json               # Classes
├── assessments.json           # Scores and assessments
├── report_cards.json          # Report cards
└── media/                     # Media files (if included)
    ├── profile_pictures/
    └── school_image/
```

## 🔍 Troubleshooting

### Common Issues

**"School does not exist"**
- Check the school slug is correct
- Use `SchoolInformation.objects.all()` to list schools

**"Permission denied"**
- Check directory write permissions
- Try a different output directory

**"Backup file not found"**
- Verify the file path is correct
- Use absolute paths

**"Out of disk space"**
- Clean old backups
- Use `--skip-media` for data-only backup

## 📞 Support

For detailed documentation, see:
- `docs/BACKUP_RESTORE_GUIDE.md` - Complete guide
- `docs/BACKUP_QUICK_START.md` - Quick reference

## 🎉 Benefits

✅ **Simple** - Easy web interface and CLI commands  
✅ **Efficient** - Compressed ZIP files with fast MySQL serialization  
✅ **Flexible** - Save anywhere on your computer or network  
✅ **Safe** - Multiple restore modes with confirmation  
✅ **Complete** - All school data in one file  
✅ **Automated** - Easy to schedule with task scheduler/cron  
✅ **Tenant-Aware** - Works perfectly with multi-tenant architecture  

## 📝 Version

Version: 1.0  
Database: MySQL  
Framework: Django 5.0+  
Multi-Tenant: Yes

