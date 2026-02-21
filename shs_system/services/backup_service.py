"""
Backup Service for Multi-Tenant School Management System

This service provides comprehensive backup functionality for school data,
including database records and media files, with proper tenant isolation.
"""

import os
import json
import zipfile
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from django.conf import settings
from django.db import connection, transaction
from django.core.files.storage import default_storage
from django.core.serializers import serialize
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.auth import get_user_model
from django.utils import timezone
import logging

from ..models import (
    SchoolInformation,
    BackupOperation,
    User,
    Student,
    Teacher,
    Class,
    Subject,
    AcademicYear,
    Term,
    Assessment,
    GradingSystem,
    Department,
    LearningArea,
    Form,
    SchoolAuthoritySignature,
    # Additional models for complete backup
    StudentClass,
    TeacherSubjectAssignment,
    ClassSubject,
    AttendanceRecord,
    PerformanceRequirement,
    StudentTermRemarks,
    ReportCard,
    ScheduledReminder,
    ScoringConfiguration,
    RestoreOperation,
    AcademicYearTemplate,
    ClassTeacher,
)

logger = logging.getLogger(__name__)
User = get_user_model()


class BackupService:
    """
    Service class for handling backup operations in a multi-tenant environment.
    Ensures data isolation between different schools (tenants).
    """
    
    def __init__(self, school: SchoolInformation):
        """
        Initialize backup service for a specific school (tenant).
        
        Args:
            school: SchoolInformation instance representing the tenant
        """
        self.school = school
        self.backup_dir = getattr(settings, 'BACKUP_DIR', r'C:\backups')
        self.ensure_backup_directory()
    
    def ensure_backup_directory(self):
        """Ensure backup directory exists"""
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def _create_backup_for_operation(
        self,
        backup_op: BackupOperation,
        includes_database: bool = True,
        includes_media_files: bool = True,
        includes_static_files: bool = False
    ):
        """
        Create backup for an existing BackupOperation record.
        Used for asynchronous backup creation.
        """
        try:
            # Update status to in progress
            backup_op.status = 'in_progress'
            backup_op.save()
            
            # Generate backup file path
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.school.slug}_backup_{timestamp}.zip"
            backup_path = os.path.join(self.backup_dir, filename)
            
            # Update backup operation with file path
            backup_op.backup_file_path = backup_path
            backup_op.save()
            
            # Create backup
            self._create_backup_file(
                backup_path, 
                includes_database, 
                includes_media_files, 
                includes_static_files,
                backup_op
            )
            
            # Update backup operation with completion details
            backup_op.status = 'completed'
            backup_op.completed_at = timezone.now()
            backup_op.backup_size = os.path.getsize(backup_path)
            backup_op.save()
            
            logger.info(f"Backup completed successfully for school {self.school.name}: {backup_path}")
            
        except Exception as e:
            # Update backup operation with error
            backup_op.status = 'failed'
            backup_op.error_message = str(e)
            backup_op.save()
            
            logger.error(f"Backup failed for school {self.school.name}: {str(e)}")
            raise

    def create_backup(
        self, 
        backup_name: str, 
        created_by: User,
        includes_database: bool = True,
        includes_media_files: bool = True,
        includes_static_files: bool = False
    ) -> BackupOperation:
        """
        Create a comprehensive backup for the school.
        
        Args:
            backup_name: Human-readable name for the backup
            created_by: User who initiated the backup
            includes_database: Whether to include database records
            includes_media_files: Whether to include media files
            includes_static_files: Whether to include static files
            
        Returns:
            BackupOperation instance
        """
        # Create backup operation record
        backup_op = BackupOperation.objects.create(
            school=self.school,
            created_by=created_by,
            backup_name=backup_name,
            backup_file_path="",  # Will be set after backup creation
            status='pending',
            includes_database=includes_database,
            includes_media_files=includes_media_files,
            includes_static_files=includes_static_files
        )
        
        try:
            # Generate backup file path
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.school.slug}_backup_{timestamp}.zip"
            backup_path = os.path.join(self.backup_dir, filename)
            
            # Update backup operation with file path
            backup_op.backup_file_path = backup_path
            backup_op.status = 'in_progress'
            backup_op.save()
            
            # Create backup
            self._create_backup_file(
                backup_path, 
                includes_database, 
                includes_media_files, 
                includes_static_files,
                backup_op
            )
            
            # Update backup operation with completion details
            backup_op.status = 'completed'
            backup_op.completed_at = timezone.now()
            backup_op.backup_size = os.path.getsize(backup_path)
            backup_op.save()
            
            logger.info(f"Backup completed successfully for school {self.school.name}: {backup_path}")
            return backup_op
            
        except Exception as e:
            # Update backup operation with error
            backup_op.status = 'failed'
            backup_op.error_message = str(e)
            backup_op.save()
            
            logger.error(f"Backup failed for school {self.school.name}: {str(e)}")
            raise
    
    def _create_backup_file(
        self, 
        backup_path: str, 
        includes_database: bool,
        includes_media_files: bool,
        includes_static_files: bool,
        backup_op: BackupOperation
    ):
        """
        Create the actual backup file with all specified components.
        
        Args:
            backup_path: Path where backup file will be created
            includes_database: Whether to include database records
            includes_media_files: Whether to include media files
            includes_static_files: Whether to include static files
        """
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as backup_zip:
            # Add metadata
            metadata = {
                'school_id': self.school.id,
                'school_name': self.school.name,
                'school_slug': self.school.slug,
                'backup_created_at': timezone.now().isoformat(),
                'django_version': getattr(settings, 'DJANGO_VERSION', '5.0.14'),
                'includes_database': includes_database,
                'includes_media_files': includes_media_files,
                'includes_static_files': includes_static_files,
            }
            
            backup_zip.writestr('metadata.json', json.dumps(metadata, indent=2))
            
            # Add database backup
            if includes_database:
                self._backup_database(backup_zip, backup_op)
            
            # Add media files
            if includes_media_files:
                self._backup_media_files(backup_zip, backup_op)
            
            # Add static files (optional)
            if includes_static_files:
                self._backup_static_files(backup_zip, backup_op)
    
    def _backup_database(self, backup_zip: zipfile.ZipFile, backup_op: BackupOperation):
        """
        Backup database records for the school.
        
        Args:
            backup_zip: ZipFile instance to write database backup to
            backup_op: BackupOperation instance to update with record count
        """
        # Define models to backup (all models that have school relationship)
        models_to_backup = [
            User,
            Student,
            Teacher,
            Class,
            Subject,
            AcademicYear,
            Term,
            Assessment,
            GradingSystem,
            Department,
            LearningArea,
            Form,
            SchoolAuthoritySignature,
            SchoolInformation,  # Include school info itself
            # Additional models that were missing
            StudentClass,
            TeacherSubjectAssignment,
            ClassSubject,
            AttendanceRecord,
            PerformanceRequirement,
            StudentTermRemarks,
            ReportCard,
            ScheduledReminder,
            ScoringConfiguration,
            BackupOperation,
            RestoreOperation,
            # Additional models found in analysis
            AcademicYearTemplate,
            ClassTeacher,
        ]
        
        database_data = {}
        total_records = 0
        
        for model in models_to_backup:
            try:
                # Filter records by school if model has school field
                if hasattr(model, 'school'):
                    queryset = model.objects.filter(school=self.school)
                elif model == SchoolInformation:
                    queryset = model.objects.filter(id=self.school.id)
                else:
                    # For models without school field, include all records
                    # This might need adjustment based on your specific requirements
                    queryset = model.objects.all()
                
                # Serialize queryset
                serialized_data = serialize('json', queryset, cls=DjangoJSONEncoder)
                database_data[model.__name__] = json.loads(serialized_data)
                
                record_count = queryset.count()
                total_records += record_count
                
                logger.info(f"Backed up {record_count} records from {model.__name__}")
                
            except Exception as e:
                logger.error(f"Error backing up {model.__name__}: {str(e)}")
                # Continue with other models even if one fails
                continue
        
        # Write database backup to zip
        backup_zip.writestr('database.json', json.dumps(database_data, indent=2))
        
        # Update backup operation with record count
        backup_op.database_records_count = total_records
        backup_op.save()
        
        logger.info(f"Backed up {total_records} database records")
    
    def _backup_media_files(self, backup_zip: zipfile.ZipFile, backup_op: BackupOperation):
        """
        Backup media files for the school.
        
        Args:
            backup_zip: ZipFile instance to write media files to
            backup_op: BackupOperation instance to update with file count
        """
        media_root = settings.MEDIA_ROOT
        if not os.path.exists(media_root):
            return
        
        file_count = 0
        
        # Walk through media directory and add files
        for root, dirs, files in os.walk(media_root):
            for file in files:
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, media_root)
                
                # Add file to zip
                backup_zip.write(file_path, f'media/{relative_path}')
                file_count += 1
        
        # Update backup operation with file count
        backup_op.media_files_count = file_count
        backup_op.save()
        
        logger.info(f"Backed up {file_count} media files")
    
    def _backup_static_files(self, backup_zip: zipfile.ZipFile, backup_op: BackupOperation):
        """
        Backup static files (optional).
        
        Args:
            backup_zip: ZipFile instance to write static files to
            backup_op: BackupOperation instance (for consistency)
        """
        static_root = settings.STATIC_ROOT or settings.STATICFILES_DIRS[0] if settings.STATICFILES_DIRS else None
        
        if not static_root or not os.path.exists(static_root):
            return
        
        file_count = 0
        
        # Walk through static directory and add files
        for root, dirs, files in os.walk(static_root):
            for file in files:
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, static_root)
                
                # Add file to zip
                backup_zip.write(file_path, f'static/{relative_path}')
                file_count += 1
        
        logger.info(f"Backed up {file_count} static files")
    
    def list_backups(self) -> List[BackupOperation]:
        """
        List all backups for the school.
        
        Returns:
            List of BackupOperation instances
        """
        return BackupOperation.objects.filter(school=self.school).order_by('-created_at')
    
    def get_backup_info(self, backup_path: str) -> Optional[Dict]:
        """
        Get information about a backup file.
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            Dictionary with backup metadata or None if file doesn't exist
        """
        if not os.path.exists(backup_path):
            return None
        
        try:
            with zipfile.ZipFile(backup_path, 'r') as backup_zip:
                metadata_str = backup_zip.read('metadata.json').decode('utf-8')
                metadata = json.loads(metadata_str)
                
                # Add file info
                metadata['file_size'] = os.path.getsize(backup_path)
                metadata['file_modified'] = datetime.fromtimestamp(os.path.getmtime(backup_path))
                
                return metadata
                
        except Exception as e:
            logger.error(f"Error reading backup info from {backup_path}: {str(e)}")
            return None
    
    def validate_backup_file(self, backup_path: str) -> Tuple[bool, str]:
        """
        Validate a backup file.
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not os.path.exists(backup_path):
            return False, "Backup file does not exist"
        
        try:
            with zipfile.ZipFile(backup_path, 'r') as backup_zip:
                # Check if metadata exists
                if 'metadata.json' not in backup_zip.namelist():
                    return False, "Backup file is missing metadata"
                
                # Try to read metadata
                metadata_str = backup_zip.read('metadata.json').decode('utf-8')
                metadata = json.loads(metadata_str)
                
                # Validate required fields
                required_fields = ['school_id', 'school_name', 'backup_created_at']
                for field in required_fields:
                    if field not in metadata:
                        return False, f"Backup file is missing required field: {field}"
                
                return True, "Backup file is valid"
                
        except zipfile.BadZipFile:
            return False, "Backup file is corrupted or not a valid zip file"
        except json.JSONDecodeError:
            return False, "Backup file metadata is corrupted"
        except Exception as e:
            return False, f"Error validating backup file: {str(e)}"
    
    def delete_backup(self, backup_path: str) -> bool:
        """
        Delete a backup file and its operation record.
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            # Delete the file
            if os.path.exists(backup_path):
                os.remove(backup_path)
            
            # Delete the operation record
            BackupOperation.objects.filter(backup_file_path=backup_path).delete()
            
            logger.info(f"Backup deleted successfully: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting backup {backup_path}: {str(e)}")
            return False
