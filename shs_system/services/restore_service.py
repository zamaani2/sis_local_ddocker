"""
Restore Service for Multi-Tenant School Management System

This service provides comprehensive restore functionality for school data,
including database records and media files, with proper tenant isolation and data integrity checks.
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
from django.core.serializers import deserialize
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
import logging

from ..models import (
    SchoolInformation,
    RestoreOperation,
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
    # Additional models for complete restore
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
    AcademicYearTemplate,
    ClassTeacher,
)

logger = logging.getLogger(__name__)
User = get_user_model()


class RestoreService:
    """
    Service class for handling restore operations in a multi-tenant environment.
    Ensures data isolation and integrity during restore operations.
    """
    
    def __init__(self, school: SchoolInformation):
        """
        Initialize restore service for a specific school (tenant).
        
        Args:
            school: SchoolInformation instance representing the tenant
        """
        self.school = school
        self.temp_dir = tempfile.mkdtemp()
    
    def __del__(self):
        """Clean up temporary directory"""
        try:
            if hasattr(self, 'temp_dir') and self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception:
            pass  # Ignore errors during cleanup
    
    def restore_from_backup(
        self,
        backup_path: str,
        created_by: User,
        restore_database: bool = True,
        restore_media_files: bool = True,
        restore_static_files: bool = False,
        backup_existing_data: bool = True
    ) -> RestoreOperation:
        """
        Restore school data from a backup file.
        
        Args:
            backup_path: Path to backup file
            created_by: User who initiated the restore
            restore_database: Whether to restore database records
            restore_media_files: Whether to restore media files
            restore_static_files: Whether to restore static files
            backup_existing_data: Whether to backup existing data before restore
            
        Returns:
            RestoreOperation instance
        """
        # Validate backup file first
        is_valid, error_message = self._validate_backup_file(backup_path)
        if not is_valid:
            raise ValueError(f"Invalid backup file: {error_message}")
        
        # Create restore operation record
        restore_op = RestoreOperation.objects.create(
            school=self.school,
            created_by=created_by,
            backup_file_path=backup_path,
            status='pending',
            restore_database=restore_database,
            restore_media_files=restore_media_files,
            restore_static_files=restore_static_files,
            backup_existing_data=backup_existing_data
        )
        
        try:
            # Update status to in progress
            restore_op.status = 'in_progress'
            restore_op.save()
            
            # Extract backup to temporary directory
            self._extract_backup(backup_path)
            
            # Create backup of existing data if requested
            if backup_existing_data:
                self._backup_existing_data(created_by)
            
            # Restore database
            if restore_database:
                self._restore_database(restore_op)
            
            # Restore media files
            if restore_media_files:
                self._restore_media_files(restore_op)
            
            # Restore static files
            if restore_static_files:
                self._restore_static_files(restore_op)
            
            # Update restore operation with completion details
            restore_op.status = 'completed'
            restore_op.completed_at = timezone.now()
            restore_op.save()
            
            logger.info(f"Restore completed successfully for school {self.school.name}")
            return restore_op
            
        except Exception as e:
            # Update restore operation with error
            restore_op.status = 'failed'
            restore_op.error_message = str(e)
            restore_op.save()
            
            logger.error(f"Restore failed for school {self.school.name}: {str(e)}")
            raise
    
    def restore_from_backup_with_operation(
        self,
        backup_path: str,
        created_by: User,
        restore_database: bool = True,
        restore_media_files: bool = True,
        restore_static_files: bool = False,
        backup_existing_data: bool = True,
        restore_op: RestoreOperation = None
    ) -> RestoreOperation:
        """
        Restore school data from a backup file using an existing RestoreOperation.
        
        Args:
            backup_path: Path to backup file
            created_by: User who initiated the restore
            restore_database: Whether to restore database records
            restore_media_files: Whether to restore media files
            restore_static_files: Whether to restore static files
            backup_existing_data: Whether to backup existing data before restore
            restore_op: Existing RestoreOperation to update
            
        Returns:
            RestoreOperation instance
        """
        # Validate backup file first
        is_valid, error_message = self._validate_backup_file(backup_path)
        if not is_valid:
            raise ValueError(f"Invalid backup file: {error_message}")
        
        try:
            # Update status to in progress
            restore_op.status = 'in_progress'
            restore_op.save()
            
            # Extract backup to temporary directory
            self._extract_backup(backup_path)
            
            # Create backup of existing data if requested
            if backup_existing_data:
                self._backup_existing_data(created_by)
            
            # Restore database
            if restore_database:
                self._restore_database(restore_op)
            
            # Restore media files
            if restore_media_files:
                self._restore_media_files(restore_op)
            
            # Restore static files
            if restore_static_files:
                self._restore_static_files(restore_op)
            
            # Update restore operation with completion details
            restore_op.status = 'completed'
            restore_op.completed_at = timezone.now()
            restore_op.save()
            
            logger.info(f"Restore completed successfully for school {self.school.name}")
            return restore_op
            
        except Exception as e:
            # Update restore operation with error
            restore_op.status = 'failed'
            restore_op.error_message = str(e)
            restore_op.save()
            
            logger.error(f"Restore failed for school {self.school.name}: {str(e)}")
            raise
        finally:
            # Clean up temporary directory
            self._cleanup_temp_dir()
    
    def _validate_backup_file(self, backup_path: str) -> Tuple[bool, str]:
        """
        Validate backup file before restore.
        
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
                
                # Read metadata
                metadata_str = backup_zip.read('metadata.json').decode('utf-8')
                metadata = json.loads(metadata_str)
                
                # Validate school compatibility
                if metadata.get('school_id') != self.school.id:
                    return False, f"Backup is for school ID {metadata.get('school_id')}, but current school is {self.school.id}"
                
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
    
    def _extract_backup(self, backup_path: str):
        """
        Extract backup file to temporary directory.
        
        Args:
            backup_path: Path to backup file
        """
        with zipfile.ZipFile(backup_path, 'r') as backup_zip:
            backup_zip.extractall(self.temp_dir)
        
        logger.info(f"Backup extracted to {self.temp_dir}")
    
    def _backup_existing_data(self, created_by: User):
        """
        Create backup of existing data before restore.
        
        Args:
            created_by: User who initiated the restore
        """
        from .backup_service import BackupService
        
        backup_service = BackupService(self.school)
        backup_name = f"Pre-restore backup - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        try:
            backup_service.create_backup(
                backup_name=backup_name,
                created_by=created_by,
                includes_database=True,
                includes_media_files=True,
                includes_static_files=False
            )
            logger.info("Pre-restore backup created successfully")
        except Exception as e:
            logger.warning(f"Failed to create pre-restore backup: {str(e)}")
            # Don't fail the restore if backup creation fails
    
    def _restore_database(self, restore_op: RestoreOperation):
        """
        Restore database records from backup.
        """
        database_file = os.path.join(self.temp_dir, 'database.json')
        if not os.path.exists(database_file):
            logger.warning("No database backup found in restore file")
            return
        
        with open(database_file, 'r') as f:
            database_data = json.load(f)
        
        restored_count = 0
        
        # Define restore order (important for foreign key relationships)
        # Must restore User before any models that reference users
        restore_order = [
            'SchoolInformation',
            'AcademicYear',
            'Term',
            'Department',
            'LearningArea',
            'Form',
            'Class',
            'Subject',
            'Teacher',
            'Student',
            'User',  # Must come before models that reference users
            'GradingSystem',
            'SchoolAuthoritySignature',
            # Models that reference users - must come after User
            'ClassSubject',  # Must come BEFORE Assessment (Assessment references ClassSubject)
            'StudentClass',  # Must come BEFORE Assessment (Assessment.clean() requires StudentClass)
            'Assessment',  # references recorded_by_id, class_subject_id AND requires StudentClass to exist
            'TeacherSubjectAssignment',  # references assigned_by_id
            'AttendanceRecord',
            'PerformanceRequirement',
            'StudentTermRemarks',
            'ReportCard',  # references generated_by_id
            'ScheduledReminder',
            'ScoringConfiguration',  # references created_by_id
            'BackupOperation',  # references created_by_id
            'RestoreOperation',  # references created_by_id
            # Additional models found in analysis
            'AcademicYearTemplate',  # references created_by_id
            'ClassTeacher',  # references assigned_by_id
        ]
        
        try:
            # First, clear existing data for this school
            self._clear_school_data()
            
            # Restore data in proper order
            # Each record has its own transaction in _restore_model_data
            for model_name in restore_order:
                if model_name in database_data:
                    model_data = database_data[model_name]
                    try:
                        count = self._restore_model_data(model_name, model_data)
                        restored_count += count
                        logger.info(f"Restored {count} records for {model_name}")
                    except Exception as e:
                        logger.error(f"Failed to restore {model_name}: {str(e)}")
                        # Continue with other models
                        continue
            
            # Only update counts if we got this far
            restore_op.restored_records_count = restored_count
            restore_op.save()
            
            logger.info(f"Database restore completed: {restored_count} records restored")
            
        except Exception as e:
            # Transaction failed - mark restore as failed
            logger.error(f"Database restore failed: {str(e)}")
            restore_op.status = 'failed'
            restore_op.error_message = f"Database restore failed: {str(e)}"
            restore_op.save()
            raise
    
    def _clear_school_data(self):
        """
        Clear existing data for the school before restore.
        """
        from django.db import connection
        
        # Use raw SQL to clear all data for the school
        # This approach avoids foreign key constraint issues
        with connection.cursor() as cursor:
            try:
                school_id = self.school.id
                
                # First, disable foreign key checks temporarily
                cursor.execute("SET session_replication_role = replica;")
                
                # Clear orphaned tables that don't have Django models
                orphaned_tables = [
                    'shs_system_scoresheetentry',
                    'shs_system_scoresheet',
                ]
                
                for table in orphaned_tables:
                    try:
                        # Check if table exists
                        cursor.execute("""
                            SELECT EXISTS (
                                SELECT FROM information_schema.tables 
                                WHERE table_schema = 'public' 
                                AND table_name = %s
                            );
                        """, [table])
                        
                        if cursor.fetchone()[0]:
                            # Clear the table
                            cursor.execute(f"DELETE FROM {table};")
                            deleted_count = cursor.rowcount
                            logger.info(f"Cleared {deleted_count} records from {table}")
                    except Exception as e:
                        logger.error(f"Error clearing {table}: {str(e)}")
                
                # Clear all school-related tables using raw SQL
                # This avoids foreign key constraint issues
                # IMPORTANT: Preserve admin users (is_superuser=True or is_staff=True)
                tables_to_clear = [
                    'shs_system_restoreoperation',
                    'shs_system_backupoperation',
                    'shs_system_scoringconfiguration',
                    'shs_system_scheduledreminder',
                    'shs_system_reportcard',
                    'shs_system_studenttermremarks',
                    'shs_system_performancerequirement',
                    'shs_system_attendancerecord',
                    'shs_system_classsubject',
                    'shs_system_teachersubjectassignment',
                    'shs_system_studentclass',
                    'shs_system_assessment',
                    'shs_system_gradingsystem',
                    'shs_system_student',
                    'shs_system_teacher',
                    # 'shs_system_user',  # Handled separately to preserve admins
                    'shs_system_subject',
                    'shs_system_class',
                    'shs_system_form',
                    'shs_system_learningarea',
                    'shs_system_department',
                    'shs_system_term',
                    'shs_system_academicyear',
                    'shs_system_schoolauthoritysignature',
                    'shs_system_classteacher',
                    'shs_system_academicyeartemplate',
                ]
                
                total_cleared = 0
                for table in tables_to_clear:
                    try:
                        # Clear records for this school
                        cursor.execute(f"DELETE FROM {table} WHERE school_id = %s;", [school_id])
                        deleted_count = cursor.rowcount
                        if deleted_count > 0:
                            logger.info(f"Cleared {deleted_count} records from {table}")
                            total_cleared += deleted_count
                    except Exception as e:
                        logger.error(f"Error clearing {table}: {str(e)}")
                        # Continue with other tables
                
                # Clear users separately, but preserve superusers AND admin users
                # School admins (role='admin') should be preserved to prevent lockout
                try:
                    cursor.execute("""
                        DELETE FROM shs_system_user 
                        WHERE school_id = %s 
                        AND is_superuser = FALSE
                        AND role != 'admin';
                    """, [school_id])
                    deleted_count = cursor.rowcount
                    if deleted_count > 0:
                        logger.info(f"Cleared {deleted_count} non-admin users from shs_system_user (preserved superusers and admin users)")
                        total_cleared += deleted_count
                except Exception as e:
                    logger.error(f"Error clearing users: {str(e)}")
                
                # Re-enable foreign key checks
                cursor.execute("SET session_replication_role = DEFAULT;")
                
                logger.info(f"Total records cleared: {total_cleared}")
                
            except Exception as e:
                # Make sure to re-enable foreign key checks even if there's an error
                try:
                    cursor.execute("SET session_replication_role = DEFAULT;")
                except:
                    pass
                logger.error(f"Error during data clearing: {str(e)}")
                raise
    
    def _restore_model_data(self, model_name: str, model_data: List[Dict]) -> int:
        """
        Restore data for a specific model.
        Each record gets its own transaction to prevent cascading failures.
        
        Args:
            model_name: Name of the model
            model_data: List of serialized model instances
            
        Returns:
            Number of records restored
        """
        restored_count = 0
        
        for obj_data in model_data:
            try:
                # Use individual transaction per record to prevent contamination
                with transaction.atomic():
                    # Deserialize the object
                    obj = next(deserialize('json', json.dumps([obj_data]), ignorenonexistent=True))
                    
                    # Ensure the object belongs to the correct school
                    if hasattr(obj.object, 'school'):
                        obj.object.school = self.school
                    
                    # Save the object
                    obj.save()
                    restored_count += 1
                
            except Exception as e:
                error_msg = str(e).lower()

                # Handle different types of errors
                if 'duplicate key' in error_msg or 'unique constraint' in error_msg:
                    logger.warning(f"Skipping duplicate {model_name} record")
                    continue
                elif 'foreign key' in error_msg:
                    logger.warning(f"Skipping {model_name} record due to foreign key constraint: {str(e)}")
                    continue
                else:
                    logger.error(f"Error restoring {model_name} object: {str(e)}")
                    continue
        
        return restored_count
    
    def _restore_media_files(self, restore_op: RestoreOperation):
        """
        Restore media files from backup.
        """
        media_backup_dir = os.path.join(self.temp_dir, 'media')
        if not os.path.exists(media_backup_dir):
            logger.warning("No media files found in backup")
            return
        
        media_root = settings.MEDIA_ROOT
        os.makedirs(media_root, exist_ok=True)
        
        restored_count = 0
        
        # Walk through backup media directory
        for root, dirs, files in os.walk(media_backup_dir):
            for file in files:
                src_path = os.path.join(root, file)
                relative_path = os.path.relpath(src_path, media_backup_dir)
                dst_path = os.path.join(media_root, relative_path)
                
                # Create destination directory if it doesn't exist
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                
                # Copy file
                shutil.copy2(src_path, dst_path)
                restored_count += 1
        
        # Update restore operation with file count
        restore_op.restored_files_count = restored_count
        restore_op.save()
        
        logger.info(f"Media files restore completed: {restored_count} files restored")
    
    def _restore_static_files(self, restore_op: RestoreOperation):
        """
        Restore static files from backup.
        """
        static_backup_dir = os.path.join(self.temp_dir, 'static')
        if not os.path.exists(static_backup_dir):
            logger.warning("No static files found in backup")
            return
        
        static_root = settings.STATIC_ROOT or settings.STATICFILES_DIRS[0] if settings.STATICFILES_DIRS else None
        if not static_root:
            logger.warning("Static files root not configured")
            return
        
        os.makedirs(static_root, exist_ok=True)
        
        restored_count = 0
        
        # Walk through backup static directory
        for root, dirs, files in os.walk(static_backup_dir):
            for file in files:
                src_path = os.path.join(root, file)
                relative_path = os.path.relpath(src_path, static_backup_dir)
                dst_path = os.path.join(static_root, relative_path)
                
                # Create destination directory if it doesn't exist
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                
                # Copy file
                shutil.copy2(src_path, dst_path)
                restored_count += 1
        
        logger.info(f"Static files restore completed: {restored_count} files restored")
    
    def _cleanup_temp_dir(self):
        """Clean up temporary directory"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            logger.info("Temporary directory cleaned up")
    
    def get_restore_history(self) -> List[RestoreOperation]:
        """
        Get restore history for the school.
        
        Returns:
            List of RestoreOperation instances
        """
        return RestoreOperation.objects.filter(school=self.school).order_by('-created_at')
    
    def validate_restore_compatibility(self, backup_path: str) -> Tuple[bool, str]:
        """
        Validate if a backup is compatible with the current school.
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            Tuple of (is_compatible, message)
        """
        try:
            with zipfile.ZipFile(backup_path, 'r') as backup_zip:
                metadata_str = backup_zip.read('metadata.json').decode('utf-8')
                metadata = json.loads(metadata_str)
                
                # Check school compatibility
                if metadata.get('school_id') != self.school.id:
                    return False, f"This backup belongs to '{metadata.get('school_name')}' (ID: {metadata.get('school_id')}), not '{self.school.name}' (ID: {self.school.id})"
                
                # Check Django version compatibility
                backup_django_version = metadata.get('django_version')
                current_django_version = getattr(settings, 'DJANGO_VERSION', '5.0.14')
                
                if backup_django_version != current_django_version:
                    return False, f"Backup was created with Django {backup_django_version}, but current version is {current_django_version}"
                
                return True, "Backup is compatible with current school"
                
        except Exception as e:
            return False, f"Error validating backup compatibility: {str(e)}"

    def cleanup_old_temp_files(self, retention_hours=24):
        """
        Clean up old temporary backup files from the temp_backups directory.
        
        Args:
            retention_hours: Hours to retain files (default 24)
        """
        try:
            from django.conf import settings
            import time
            
            temp_dir = os.path.join(getattr(settings, 'BACKUP_DIR', r'C:\backups'), 'temp_uploads')
            if not os.path.exists(temp_dir):
                return
            
            current_time = time.time()
            retention_seconds = retention_hours * 3600
            
            files_cleaned = 0
            total_size_cleaned = 0
            
            for filename in os.listdir(temp_dir):
                file_path = os.path.join(temp_dir, filename)
                if os.path.isfile(file_path):
                    file_age = current_time - os.path.getmtime(file_path)
                    if file_age > retention_seconds:
                        file_size = os.path.getsize(file_path)
                        os.remove(file_path)
                        files_cleaned += 1
                        total_size_cleaned += file_size
                        logger.info(f"Cleaned up old temp file: {filename} ({file_size} bytes)")
            
            if files_cleaned > 0:
                logger.info(f"Cleaned up {files_cleaned} old temp files ({total_size_cleaned} bytes total)")
            else:
                logger.info("No old temp files to clean up")
                
        except Exception as e:
            logger.error(f"Error cleaning up old temp files: {str(e)}")
