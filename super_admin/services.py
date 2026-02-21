"""
Super Admin Backup and Restore Services

This module provides enhanced backup and restore functionality for Super Admins,
allowing them to restore backups to both existing and non-existing schools.
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
from django.utils.text import slugify
import logging

from shs_system.models import (
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
from super_admin.models import SchoolDomain

logger = logging.getLogger(__name__)
User = get_user_model()


class SuperAdminRestoreService:
    """
    Enhanced restore service for Super Admins that can restore backups to any school,
    including creating new schools from backup data.
    """
    
    def __init__(self, super_admin_user: User):
        """
        Initialize Super Admin restore service.
        
        Args:
            super_admin_user: Super Admin user instance
        """
        self.super_admin_user = super_admin_user
        self.temp_dir = tempfile.mkdtemp()
    
    def __del__(self):
        """Clean up temporary directory"""
        try:
            if hasattr(self, 'temp_dir') and self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception:
            pass  # Ignore errors during cleanup
    
    def get_backup_info(self, backup_path: str) -> Optional[Dict]:
        """
        Get information about a backup file without school validation.
        
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
        Validate a backup file without school-specific restrictions.
        
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
    
    def restore_to_existing_school(
        self,
        backup_path: str,
        target_school: SchoolInformation,
        restore_database: bool = True,
        restore_media_files: bool = True,
        restore_static_files: bool = False,
        backup_existing_data: bool = True
    ) -> RestoreOperation:
        """
        Restore backup data to an existing school.
        
        Args:
            backup_path: Path to backup file
            target_school: Target school to restore to
            restore_database: Whether to restore database records
            restore_media_files: Whether to restore media files
            restore_static_files: Whether to restore static files
            backup_existing_data: Whether to backup existing data before restore
            
        Returns:
            RestoreOperation instance
        """
        # Validate backup file first
        is_valid, error_message = self.validate_backup_file(backup_path)
        if not is_valid:
            raise ValueError(f"Invalid backup file: {error_message}")
        
        # Create restore operation record
        restore_op = RestoreOperation.objects.create(
            school=target_school,
            created_by=self.super_admin_user,
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
                self._backup_existing_data(target_school)
            
            # Restore database
            if restore_database:
                self._restore_database_to_existing_school(target_school, restore_op)
            
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
            
            logger.info(f"Restore completed successfully for school {target_school.name}")
            return restore_op
            
        except Exception as e:
            # Update restore operation with error
            restore_op.status = 'failed'
            restore_op.error_message = str(e)
            restore_op.save()
            
            logger.error(f"Restore failed for school {target_school.name}: {str(e)}")
            raise
        finally:
            # Clean up temporary directory
            self._cleanup_temp_dir()
    
    def restore_to_new_school(
        self,
        backup_path: str,
        new_school_name: str,
        new_school_domain: str,
        admin_name: str,
        admin_email: str,
        restore_database: bool = True,
        restore_media_files: bool = True,
        restore_static_files: bool = False
    ) -> Tuple[SchoolInformation, RestoreOperation]:
        """
        Restore backup data to a new school (create school from backup).
        
        Args:
            backup_path: Path to backup file
            new_school_name: Name for the new school
            new_school_domain: Domain for the new school
            admin_name: Name of the admin user
            admin_email: Email of the admin user
            restore_database: Whether to restore database records
            restore_media_files: Whether to restore media files
            restore_static_files: Whether to restore static files
            
        Returns:
            Tuple of (SchoolInformation, RestoreOperation) instances
        """
        # Validate backup file first
        is_valid, error_message = self.validate_backup_file(backup_path)
        if not is_valid:
            raise ValueError(f"Invalid backup file: {error_message}")
        
        # Get backup metadata
        backup_info = self.get_backup_info(backup_path)
        if not backup_info:
            raise ValueError("Could not read backup metadata")
        
        # Extract backup to temporary directory
        self._extract_backup(backup_path)
        
        # Create new school
        new_school = self._create_school_from_backup(
            backup_info, new_school_name, new_school_domain, admin_name, admin_email
        )
        
        # Create restore operation record
        restore_op = RestoreOperation.objects.create(
            school=new_school,
            created_by=self.super_admin_user,
            backup_file_path=backup_path,
            status='pending',
            restore_database=restore_database,
            restore_media_files=restore_media_files,
            restore_static_files=restore_static_files,
            backup_existing_data=False  # No existing data to backup for new school
        )
        
        try:
            # Update status to in progress
            restore_op.status = 'in_progress'
            restore_op.save()
            
            # Restore database
            if restore_database:
                self._restore_database_to_new_school(new_school, restore_op)
            
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
            
            logger.info(f"New school '{new_school.name}' created and restored successfully")
            return new_school, restore_op
            
        except Exception as e:
            # Update restore operation with error
            restore_op.status = 'failed'
            restore_op.error_message = str(e)
            restore_op.save()
            
            # Clean up the created school if restore failed
            try:
                new_school.delete()
            except:
                pass
            
            logger.error(f"Restore failed for new school: {str(e)}")
            raise
        finally:
            # Clean up temporary directory
            self._cleanup_temp_dir()
    
    def _extract_backup(self, backup_path: str):
        """Extract backup file to temporary directory."""
        with zipfile.ZipFile(backup_path, 'r') as backup_zip:
            backup_zip.extractall(self.temp_dir)
        
        logger.info(f"Backup extracted to {self.temp_dir}")
    
    def _create_school_from_backup(
        self, 
        backup_info: Dict, 
        new_school_name: str, 
        new_school_domain: str,
        admin_name: str,
        admin_email: str
    ) -> SchoolInformation:
        """
        Create a new school based on backup information.
        
        Args:
            backup_info: Backup metadata
            new_school_name: Name for the new school
            new_school_domain: Domain for the new school
            admin_name: Name of the admin user
            admin_email: Email of the admin user
            
        Returns:
            SchoolInformation instance
        """
        # Generate a unique slug from the school name
        base_slug = slugify(new_school_name)
        slug = base_slug
        counter = 1
        
        # Check if the slug already exists, if so, append a number
        while SchoolInformation.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        # Create the school
        school = SchoolInformation.objects.create(
            name=new_school_name,
            slug=slug,
            short_name=new_school_name[:20] if len(new_school_name) > 20 else new_school_name,
            created_by=self.super_admin_user,
            updated_by=self.super_admin_user,
            is_active=True,
            # Set default values for required fields
            address='',  # Will be populated from backup data if available
            phone_number='',  # Will be populated from backup data if available
            email='',  # Will be populated from backup data if available
        )
        
        # Create domain for the school
        if "." in new_school_domain:
            domain_value = new_school_domain
        else:
            domain_value = f"{new_school_domain}.localhost"
        
        domain = SchoolDomain.objects.create(
            school=school, 
            domain=domain_value, 
            is_primary=True
        )
        
        # Create admin user for the school
        username = admin_email.split("@")[0]  # Use part of email as username
        
        # Generate a random password
        import random
        import string
        password = "".join(
            random.choices(string.ascii_letters + string.digits, k=10)
        )
        
        admin_user = User.objects.create(
            username=username,
            email=admin_email,
            full_name=admin_name,
            role="admin",
            school=school,
        )
        admin_user.set_password(password)
        admin_user.save()
        
        logger.info(f"Created new school '{school.name}' with admin user '{admin_user.username}'")
        return school
    
    def _backup_existing_data(self, school: SchoolInformation):
        """Create backup of existing data before restore."""
        from shs_system.services.backup_service import BackupService
        
        backup_service = BackupService(school)
        backup_name = f"Pre-restore backup - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        try:
            backup_service.create_backup(
                backup_name=backup_name,
                created_by=self.super_admin_user,
                includes_database=True,
                includes_media_files=True,
                includes_static_files=False
            )
            logger.info("Pre-restore backup created successfully")
        except Exception as e:
            logger.warning(f"Failed to create pre-restore backup: {str(e)}")
            # Don't fail the restore if backup creation fails
    
    def _restore_database_to_existing_school(self, school: SchoolInformation, restore_op: RestoreOperation):
        """Restore database records to an existing school."""
        database_file = os.path.join(self.temp_dir, 'database.json')
        if not os.path.exists(database_file):
            logger.warning("No database backup found in restore file")
            return
        
        with open(database_file, 'r') as f:
            database_data = json.load(f)
        
        restored_count = 0
        
        # Define restore order (important for foreign key relationships)
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
            'ClassSubject',
            'StudentClass',
            'Assessment',
            'TeacherSubjectAssignment',
            'AttendanceRecord',
            'PerformanceRequirement',
            'StudentTermRemarks',
            'ReportCard',
            'ScheduledReminder',
            'ScoringConfiguration',
            'BackupOperation',
            'RestoreOperation',
            'AcademicYearTemplate',
            'ClassTeacher',
        ]
        
        try:
            # First, clear existing data for this school
            self._clear_school_data(school)
            
            # Restore data in proper order
            for model_name in restore_order:
                if model_name in database_data:
                    model_data = database_data[model_name]
                    try:
                        count = self._restore_model_data(model_name, model_data, school)
                        restored_count += count
                        logger.info(f"Restored {count} records for {model_name}")
                    except Exception as e:
                        logger.error(f"Failed to restore {model_name}: {str(e)}")
                        continue
            
            # Update counts
            restore_op.restored_records_count = restored_count
            restore_op.save()
            
            logger.info(f"Database restore completed: {restored_count} records restored")
            
            # Log final summary of what was restored
            logger.info(f"\n=== RESTORE SUMMARY ===")
            from shs_system.models import Student, Teacher, Class, Subject, AcademicYear, Term, Assessment, User
            final_counts = {
                'students': Student.objects.filter(school=school).count(),
                'teachers': Teacher.objects.filter(school=school).count(),
                'classes': Class.objects.filter(school=school).count(),
                'subjects': Subject.objects.filter(school=school).count(),
                'academic_years': AcademicYear.objects.filter(school=school).count(),
                'terms': Term.objects.filter(school=school).count(),
                'assessments': Assessment.objects.filter(school=school).count(),
                'users': User.objects.filter(school=school).count(),
            }
            
            for model_name, count in final_counts.items():
                logger.info(f"Final {model_name} count: {count}")
            
            logger.info(f"=== END RESTORE SUMMARY ===")
            
        except Exception as e:
            logger.error(f"Database restore failed: {str(e)}")
            restore_op.status = 'failed'
            restore_op.error_message = f"Database restore failed: {str(e)}"
            restore_op.save()
            raise
    
    def _restore_database_to_new_school(self, school: SchoolInformation, restore_op: RestoreOperation):
        """Restore database records to a new school using a two-phase approach."""
        database_file = os.path.join(self.temp_dir, 'database.json')
        if not os.path.exists(database_file):
            logger.warning("No database backup found in restore file")
            return
        
        with open(database_file, 'r') as f:
            database_data = json.load(f)
        
        restored_count = 0
        
        # Define restore order (important for foreign key relationships)
        # Skip SchoolInformation for new schools since we already created it
        # Follow the exact same order as the regular restore service
        restore_order = [
            # 'SchoolInformation',  # Skip - already created
            'AcademicYear',           # Academic years before terms
            'Term',                   # Terms after academic years
            'Department',             # Departments before teachers/subjects
            'LearningArea',           # Learning areas before subjects
            'Form',                   # Forms before classes/students
            'Class',                  # Classes before students
            'Subject',                # Subjects after departments/learning areas
            'Teacher',                # Teachers after departments
            'Student',                # Students after forms/learning areas
            'User',                   # Users after teachers/students (for profiles)
            'GradingSystem',          # Grading systems
            'SchoolAuthoritySignature',
            'ClassSubject',           # Must come BEFORE Assessment
            'StudentClass',           # Must come BEFORE Assessment
            'Assessment',             # References ClassSubject and requires StudentClass
            'TeacherSubjectAssignment',
            'AttendanceRecord',
            'PerformanceRequirement',
            'StudentTermRemarks',
            'ReportCard',
            'ScheduledReminder',
            'ScoringConfiguration',
            'BackupOperation',
            'RestoreOperation',
            'AcademicYearTemplate',
            'ClassTeacher',
        ]
        
        try:
            # Log what's available in the backup
            logger.info(f"Available models in backup: {list(database_data.keys())}")
            for model_name, model_data in database_data.items():
                logger.info(f"  {model_name}: {len(model_data)} records")
                
                # Log sample data for ALL Phase 1 models to see what's there
                if len(model_data) > 0 and model_name in ['Department', 'LearningArea', 'Form', 'AcademicYear', 'Term', 'Student', 'Teacher', 'User', 'Class', 'Subject']:
                    sample_record = model_data[0]
                    logger.info(f"    Sample {model_name} record: {sample_record}")
            
            # Check specifically for Phase 1 models
            phase1_models = ['Department', 'LearningArea', 'Form', 'AcademicYear', 'Term', 'Subject', 'Teacher', 'Student', 'User', 'GradingSystem', 'SchoolAuthoritySignature', 'Class']
            logger.info(f"\n=== CHECKING PHASE 1 MODELS IN BACKUP ===")
            for model_name in phase1_models:
                if model_name in database_data:
                    count = len(database_data[model_name])
                    logger.info(f"✅ {model_name}: {count} records found")
                else:
                    logger.info(f"❌ {model_name}: NOT FOUND in backup")
            
            # PHASE 1: Restore basic models first (without complex dependencies)
            # Order is critical - dependencies must be restored before dependents
            # Note: Model names in backup are full Django paths (e.g., 'shs_system.academicyear')
            phase1_models = [
                'shs_system.department',           # No dependencies
                'shs_system.learningarea',         # No dependencies  
                'shs_system.form',                 # No dependencies
                'shs_system.academicyear',         # No dependencies
                'shs_system.term',                 # Depends on AcademicYear
                'shs_system.subject',              # Depends on Department, LearningArea
                'shs_system.teacher',              # Depends on Department
                'shs_system.student',              # Depends on Form, LearningArea
                'shs_system.user',                 # Depends on Teacher/Student profiles
                'shs_system.gradingsystem',        # No dependencies
                'shs_system.schoolauthoritysignature', # No dependencies
                'shs_system.class',                # Depends on Form, LearningArea, AcademicYear (must come after these)
            ]
            
            logger.info(f"\n=== PHASE 1: RESTORING BASIC MODELS ===")
            for model_name in phase1_models:
                if model_name in database_data:
                    model_data = database_data[model_name]
                    try:
                        logger.info(f"🔄 Starting restore of {model_name} - {len(model_data)} records")
                        
                        # Log sample data for debugging
                        if len(model_data) > 0:
                            sample_record = model_data[0]
                            logger.info(f"Sample {model_name} record: {sample_record}")
                        
                        count = self._restore_model_data(model_name, model_data, school)
                        restored_count += count
                        logger.info(f"✅ Restored {count}/{len(model_data)} records for {model_name}")
                        
                        # If no records were restored, log detailed error info
                        if count == 0 and len(model_data) > 0:
                            logger.warning(f"⚠️ No records restored for {model_name} despite having {len(model_data)} records in backup")
                            logger.warning(f"This might indicate validation errors or foreign key issues")
                            
                    except Exception as e:
                        logger.error(f"❌ Failed to restore {model_name}: {str(e)}")
                        import traceback
                        logger.error(f"Traceback: {traceback.format_exc()}")
                        continue
                else:
                    logger.info(f"⚠️ No data found for {model_name} in backup")
            
            # PHASE 2: Restore dependent models (that reference Phase 1 models)
            phase2_models = ['ClassSubject', 'StudentClass', 'Assessment', 'TeacherSubjectAssignment', 'AttendanceRecord', 'PerformanceRequirement', 'StudentTermRemarks', 'ReportCard', 'ScheduledReminder', 'ScoringConfiguration', 'BackupOperation', 'RestoreOperation', 'AcademicYearTemplate', 'ClassTeacher']
            
            logger.info(f"\n=== PHASE 2: RESTORING DEPENDENT MODELS ===")
            for model_name in phase2_models:
                if model_name in database_data:
                    model_data = database_data[model_name]
                    try:
                        logger.info(f"🔄 Starting restore of {model_name} - {len(model_data)} records")
                        count = self._restore_model_data(model_name, model_data, school)
                        restored_count += count
                        logger.info(f"✅ Restored {count}/{len(model_data)} records for {model_name}")
                        
                        # If no records were restored, log detailed error info
                        if count == 0 and len(model_data) > 0:
                            logger.warning(f"⚠️ No records restored for {model_name} despite having {len(model_data)} records in backup")
                            logger.warning(f"This might indicate validation errors or foreign key issues")
                            
                    except Exception as e:
                        logger.error(f"❌ Failed to restore {model_name}: {str(e)}")
                        import traceback
                        logger.error(f"Traceback: {traceback.format_exc()}")
                        continue
                else:
                    logger.info(f"⚠️ No data found for {model_name} in backup")
            
            # Update counts
            restore_op.restored_records_count = restored_count
            restore_op.save()
            
            # Log final summary of what was restored
            logger.info(f"\n=== RESTORE SUMMARY ===")
            from shs_system.models import Student, Teacher, Class, Subject, AcademicYear, Term, Assessment, User
            final_counts = {
                'students': Student.objects.filter(school=school).count(),
                'teachers': Teacher.objects.filter(school=school).count(),
                'classes': Class.objects.filter(school=school).count(),
                'subjects': Subject.objects.filter(school=school).count(),
                'academic_years': AcademicYear.objects.filter(school=school).count(),
                'terms': Term.objects.filter(school=school).count(),
                'assessments': Assessment.objects.filter(school=school).count(),
                'users': User.objects.filter(school=school).count(),
            }
            
            for model_name, count in final_counts.items():
                logger.info(f"Final {model_name} count: {count}")
            
            logger.info(f"=== END RESTORE SUMMARY ===")
            
            # Verify the restore by checking record counts
            self._verify_restore(school, restore_op)
            
            logger.info(f"Database restore completed: {restored_count} records restored")
            
        except Exception as e:
            logger.error(f"Database restore failed: {str(e)}")
            restore_op.status = 'failed'
            restore_op.error_message = f"Database restore failed: {str(e)}"
            restore_op.save()
            raise
    
    def _clear_school_data(self, school: SchoolInformation):
        """Clear existing data for the school before restore."""
        from django.db import connection
        
        # Use raw SQL to clear all data for the school
        with connection.cursor() as cursor:
            try:
                school_id = school.id
                
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
                
                # Clear users separately, but preserve superusers AND admin users
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
    
    def _restore_model_data(self, model_name: str, model_data: List[Dict], target_school: SchoolInformation) -> int:
        """
        Restore data for a specific model to the target school.
        
        Args:
            model_name: Name of the model
            model_data: List of serialized model instances
            target_school: Target school to restore to
            
        Returns:
            Number of records restored
        """
        restored_count = 0
        
        for obj_data in model_data:
            try:
                # Use individual transaction per record to prevent contamination
                with transaction.atomic():
                    # Log the raw object data
                    logger.debug(f"Processing {model_name} object data: {obj_data}")
                    
                    # Deserialize the object
                    try:
                        # Use ignorenonexistent=True to skip problematic fields
                        obj = next(deserialize('json', json.dumps([obj_data]), ignorenonexistent=True))
                        logger.debug(f"Successfully deserialized {model_name} object")
                        
                        # CRITICAL: Update school reference IMMEDIATELY after deserialization
                        # This prevents the __str__ method from trying to access the old school
                        # Check if the model has a school field by looking at the model's fields
                        if 'school' in [field.name for field in obj.object._meta.get_fields()]:
                            obj.object.school = target_school
                            obj.object.school_id = target_school.id
                        
                        # Handle reverse relationships that can't be directly assigned
                        # These are ManyToManyField reverse relationships
                        reverse_relationships = []
                        for field in obj.object._meta.get_fields():
                            if field.is_relation and hasattr(field, 'related_model'):
                                try:
                                    # Check if this is a reverse ManyToManyField
                                    if field.many_to_many and not hasattr(field, 'through'):
                                        reverse_relationships.append(field.name)
                                    # Also check for reverse ForeignKey relationships that might cause issues
                                    elif field.many_to_one and hasattr(field, 'related_name'):
                                        # This might be a reverse relationship
                                        if field.related_name and not field.related_name.endswith('_set'):
                                            reverse_relationships.append(field.name)
                                except AttributeError:
                                    # Skip fields that don't have the expected attributes
                                    pass
                        
                        # Clear reverse relationships to avoid assignment errors
                        for rel_name in reverse_relationships:
                            if hasattr(obj.object, rel_name):
                                try:
                                    # Clear the reverse relationship
                                    rel_obj = getattr(obj.object, rel_name)
                                    if hasattr(rel_obj, 'clear'):
                                        rel_obj.clear()
                                    elif hasattr(rel_obj, 'set'):
                                        rel_obj.set([])
                                except Exception as e:
                                    logger.debug(f"Could not clear reverse relationship {rel_name}: {str(e)}")
                        
                        # Special handling for User model's created_school_info field
                        if model_name == 'shs_system.user' and hasattr(obj.object, 'created_school_info'):
                            try:
                                # Clear the reverse relationship
                                obj.object.created_school_info.clear()
                                logger.debug(f"Cleared created_school_info reverse relationship")
                            except Exception as e:
                                logger.debug(f"Could not clear created_school_info: {str(e)}")
                                # Try alternative approach - set to empty list
                                try:
                                    obj.object.created_school_info.set([])
                                    logger.debug(f"Set created_school_info to empty list")
                                except Exception as e2:
                                    logger.debug(f"Could not set created_school_info to empty list: {str(e2)}")
                        
                    except Exception as deserialize_error:
                        logger.error(f"Failed to deserialize {model_name} object: {str(deserialize_error)}")
                        logger.error(f"Object data: {obj_data}")
                        continue
                    
                    # Special handling for User model - skip admin users to avoid conflicts
                    if model_name == 'User':
                        # Skip admin users as they might conflict with the newly created admin
                        if obj.object.role == 'admin':
                            logger.info(f"Skipping admin user {obj.object.username} - already created")
                            continue
                    
                    # Clear primary key to force creation of new records (avoid conflicts)
                    obj.object.pk = None
                    obj.object.id = None
                    
                    # Handle unique constraints for specific models
                    if model_name == 'shs_system.student' and hasattr(obj.object, 'admission_number'):
                        # Generate a new unique admission number (max 10 characters)
                        import time
                        timestamp = int(time.time())
                        # Use last 6 digits of timestamp to keep it short
                        short_timestamp = str(timestamp)[-6:]
                        obj.object.admission_number = f"ST{short_timestamp}"
                        logger.info(f"Generated new admission number: {obj.object.admission_number}")
                        
                        # Also generate a unique email to prevent User creation conflicts
                        if hasattr(obj.object, 'email') and obj.object.email:
                            obj.object.email = f"student{timestamp}@restored.example.com"
                            logger.info(f"Generated new student email: {obj.object.email}")
                    
                    elif model_name == 'User' and hasattr(obj.object, 'username'):
                        # Generate a new unique username and email if they conflict
                        import time
                        timestamp = int(time.time())
                        if obj.object.username.startswith('student_') or obj.object.username.startswith('teacher_'):
                            obj.object.username = f"{obj.object.username.split('_')[0]}_{timestamp}"
                            logger.info(f"Generated new username: {obj.object.username}")
                        
                        # Also generate a unique email to avoid conflicts
                        if hasattr(obj.object, 'email') and obj.object.email:
                            obj.object.email = f"user{timestamp}@restored.example.com"
                            logger.info(f"Generated new email: {obj.object.email}")
                    
                    elif model_name == 'shs_system.teacher' and hasattr(obj.object, 'staff_id'):
                        # Generate a new unique staff ID (max 10 characters)
                        import time
                        timestamp = int(time.time())
                        # Use last 6 digits of timestamp to keep it short
                        short_timestamp = str(timestamp)[-6:]
                        obj.object.staff_id = f"TCH{short_timestamp}"
                        logger.info(f"Generated new staff ID: {obj.object.staff_id}")
                    
                    elif model_name == 'shs_system.subject' and hasattr(obj.object, 'subject_code'):
                        # Generate a new unique subject_code manually since deserializer bypasses save() method
                        from shs_system.models import generate_unique_id
                        obj.object.subject_code = generate_unique_id(entity_type="subject", length=5)
                        logger.info(f"Generated new subject_code: {obj.object.subject_code}")
                    
                    elif model_name == 'shs_system.form' and hasattr(obj.object, 'form_number'):
                        # Check if form with this number already exists in the school
                        existing_form = Form.objects.filter(
                            school=target_school, 
                            form_number=obj.object.form_number
                        ).first()
                        if existing_form:
                            logger.info(f"Form {obj.object.form_number} already exists, skipping")
                            continue
                    
                    elif model_name == 'shs_system.class' and hasattr(obj.object, 'form_id'):
                        # Map Class form reference to existing Form in target school
                        if obj.object.form_id:
                            try:
                                # Find existing form by form_number in target school
                                existing_form = Form.objects.filter(
                                    school=target_school,
                                    form_number=obj.object.form.form_number if hasattr(obj.object, 'form') and obj.object.form else None
                                ).first()
                                
                                if existing_form:
                                    obj.object.form = existing_form
                                    obj.object.form_id = existing_form.id
                                    logger.info(f"Updated Class form reference to: {existing_form}")
                                else:
                                    logger.warning(f"No matching form found for Class, skipping")
                                    continue
                                
                                # Also map learning_area reference to existing LearningArea in target school
                                if hasattr(obj.object, 'learning_area_id') and obj.object.learning_area_id:
                                    existing_learning_area = LearningArea.objects.filter(
                                        school=target_school
                                    ).first()  # Get the first learning area in the target school
                                    
                                    if existing_learning_area:
                                        obj.object.learning_area = existing_learning_area
                                        obj.object.learning_area_id = existing_learning_area.id
                                        logger.info(f"Updated Class learning_area reference to: {existing_learning_area}")
                                
                                # Also map academic_year reference to existing AcademicYear in target school
                                if hasattr(obj.object, 'academic_year_id') and obj.object.academic_year_id:
                                    existing_academic_year = AcademicYear.objects.filter(
                                        school=target_school
                                    ).first()  # Get the first academic year in the target school
                                    
                                    if existing_academic_year:
                                        obj.object.academic_year = existing_academic_year
                                        obj.object.academic_year_id = existing_academic_year.id
                                        logger.info(f"Updated Class academic_year reference to: {existing_academic_year}")
                                        
                            except Exception as e:
                                logger.error(f"Error updating Class references: {e}")
                                continue
                    
                    elif model_name == 'shs_system.academicyear' and hasattr(obj.object, 'name'):
                        # For new schools, we don't need to check for duplicates since we're creating fresh
                        logger.info(f"Processing AcademicYear: {obj.object.name}")
                    
                    elif model_name == 'shs_system.term' and hasattr(obj.object, 'academic_year_id'):
                        # Map Term to the newly created AcademicYear in the target school
                        if obj.object.academic_year_id:
                            try:
                                # Find the first academic year in the target school (should be the one we just created)
                                matching_academic_year = AcademicYear.objects.filter(
                                    school=target_school
                                ).first()
                                
                                if matching_academic_year:
                                    obj.object.academic_year = matching_academic_year
                                    obj.object.academic_year_id = matching_academic_year.id
                                    logger.info(f"Updated Term academic_year to: {matching_academic_year}")
                                else:
                                    logger.warning(f"No academic year found in target school, skipping Term")
                                    continue
                            except Exception as e:
                                logger.error(f"Error updating Term academic_year: {e}")
                                continue
                    
                    # CRITICAL: Update school reference BEFORE any other operations
                    if hasattr(obj.object, 'school'):
                        logger.debug(f"Updating school reference for {model_name} object")
                        obj.object.school = target_school
                        # Also update the school_id field directly to ensure consistency
                        obj.object.school_id = target_school.id
                    
                    # Handle foreign key relationships that might reference the old school
                    self._update_foreign_keys(obj.object, target_school)
                    
                    # Additional PostgreSQL-specific handling
                    self._fix_postgresql_references(obj.object, target_school)
                    
                    # Log the object details for debugging
                    logger.info(f"Restoring {model_name} object:")
                    logger.info(f"  Object: {obj.object}")
                    if hasattr(obj.object, 'school'):
                        logger.info(f"  School reference: {obj.object.school} (ID: {obj.object.school_id})")
                    else:
                        logger.info(f"  No school field found")
                    
                    # Log all foreign key fields for debugging
                    for field in obj.object._meta.get_fields():
                        if field.is_relation and hasattr(field, 'related_model'):
                            field_name = field.name
                            id_field_name = f"{field_name}_id"
                            if hasattr(obj.object, id_field_name):
                                fk_id = getattr(obj.object, id_field_name)
                                logger.info(f"  {field_name}_id: {fk_id}")
                    
                    # Save the object
                    try:
                        # Log object details before saving
                        logger.info(f"Attempting to save {model_name} object:")
                        logger.info(f"  Object type: {type(obj.object)}")
                        logger.info(f"  Object pk: {obj.object.pk}")
                        logger.info(f"  Object id: {getattr(obj.object, 'id', 'No id field')}")
                        
                        # Try to save
                        obj.save()
                        restored_count += 1
                        logger.info(f"✅ Successfully saved {model_name} object (ID: {obj.object.pk})")
                        
                        # Verify the object was actually saved
                        try:
                            # Try to retrieve the object from database
                            saved_obj = obj.object.__class__.objects.get(pk=obj.object.pk)
                            logger.info(f"✅ Verified object exists in database: {saved_obj}")
                        except Exception as verify_error:
                            logger.error(f"❌ Object not found in database after save: {str(verify_error)}")
                        
                    except Exception as save_error:
                        logger.error(f"❌ Failed to save {model_name} object: {str(save_error)}")
                        logger.error(f"Object details: {obj.object}")
                        logger.error(f"Object school: {getattr(obj.object, 'school', 'No school field')}")
                        logger.error(f"Object school_id: {getattr(obj.object, 'school_id', 'No school_id field')}")
                        
                        # Log specific error types for better debugging
                        error_msg = str(save_error).lower()
                        if 'foreign key' in error_msg:
                            logger.error(f"🔗 Foreign key constraint violation - related object may not exist")
                        elif 'unique constraint' in error_msg or 'duplicate key' in error_msg:
                            logger.error(f"🔑 Unique constraint violation - duplicate record")
                        elif 'validation' in error_msg:
                            logger.error(f"✅ Validation error - data doesn't meet model requirements")
                        elif 'not null' in error_msg:
                            logger.error(f"📝 Not null constraint violation - required field missing")
                        elif 'direct assignment to the reverse side' in error_msg:
                            logger.error(f"🔄 Reverse relationship assignment error - this should be handled by clearing relationships")
                        elif 'value too long for type character varying' in error_msg:
                            logger.error(f"📏 String too long for database field - field length constraint violated")
                        
                        # Try to get more details about the error
                        import traceback
                        logger.error(f"Full traceback: {traceback.format_exc()}")
                        
                        # Don't raise the error, just log it and continue
                        logger.error(f"Skipping this {model_name} object due to save error")
                        continue
                
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
    
    def _update_foreign_keys(self, obj, target_school: SchoolInformation):
        """
        Update foreign key relationships that might reference the old school.
        This is more comprehensive than the regular restore service.
        
        Args:
            obj: The model instance to update
            target_school: The target school to update references to
        """
        # Get the model class
        model_class = obj.__class__
        
        # Get all foreign key fields
        for field in model_class._meta.get_fields():
            if field.is_relation and hasattr(field, 'related_model'):
                related_model = field.related_model
                
                # If the related model is SchoolInformation, update the reference
                if related_model == SchoolInformation:
                    field_name = field.name
                    if hasattr(obj, field_name):
                        setattr(obj, field_name, target_school)
                        # Also update the _id field if it exists
                        id_field_name = f"{field_name}_id"
                        if hasattr(obj, id_field_name):
                            setattr(obj, id_field_name, target_school.id)
                
                # Handle other foreign key relationships that might need updating
                elif related_model and hasattr(related_model, 'school'):
                    # This is a foreign key to another model that has a school field
                    field_name = field.name
                    if hasattr(obj, field_name):
                        related_obj = getattr(obj, field_name)
                        if related_obj and hasattr(related_obj, 'school'):
                            # Update the related object's school reference
                            related_obj.school = target_school
                            related_obj.school_id = target_school.id
                            try:
                                related_obj.save()
                            except Exception as e:
                                error_msg = str(e).lower()
                                if 'duplicate key' in error_msg or 'unique constraint' in error_msg:
                                    logger.warning(f"Could not update related object {field_name}: duplicate key value violates unique constraint")
                                    # Skip this related object update
                                    continue
                                else:
                                    logger.warning(f"Could not update related object {field_name}: {str(e)}")
                                    continue
    
    def _fix_postgresql_references(self, obj, target_school: SchoolInformation):
        """
        Fix PostgreSQL-specific foreign key reference issues.
        This handles cases where Django's deserializer preserves old foreign key IDs.
        
        Args:
            obj: The model instance to fix
            target_school: The target school to update references to
        """
        try:
            # Get all fields from the model
            for field in obj._meta.get_fields():
                if field.is_relation and hasattr(field, 'related_model'):
                    related_model = field.related_model
                    
                    # If this field references SchoolInformation, ensure it points to the new school
                    if related_model == SchoolInformation:
                        field_name = field.name
                        id_field_name = f"{field_name}_id"
                        
                        # Check if the _id field exists and has the wrong value
                        if hasattr(obj, id_field_name):
                            current_id = getattr(obj, id_field_name)
                            if current_id and current_id != target_school.id:
                                logger.debug(f"Fixing {field_name}_id: {current_id} -> {target_school.id}")
                                setattr(obj, id_field_name, target_school.id)
                                setattr(obj, field_name, target_school)
                    
                    # Handle other foreign key relationships that might have school references
                    elif related_model and hasattr(related_model, 'school'):
                        field_name = field.name
                        id_field_name = f"{field_name}_id"
                        
                        if hasattr(obj, id_field_name):
                            related_id = getattr(obj, id_field_name)
                            if related_id:
                                # Try to find the related object and update its school reference
                                try:
                                    related_obj = related_model.objects.get(id=related_id)
                                    if hasattr(related_obj, 'school') and related_obj.school_id != target_school.id:
                                        logger.debug(f"Updating related object {field_name} school reference")
                                        related_obj.school = target_school
                                        related_obj.school_id = target_school.id
                                        related_obj.save()
                                except related_model.DoesNotExist:
                                    logger.warning(f"Related object {field_name} with ID {related_id} not found")
                                except Exception as e:
                                    logger.warning(f"Could not update related object {field_name}: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error fixing PostgreSQL references: {str(e)}")
    
    def _restore_media_files(self, restore_op: RestoreOperation):
        """Restore media files from backup."""
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
        """Restore static files from backup."""
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
    
    def _verify_restore(self, school: SchoolInformation, restore_op: RestoreOperation):
        """
        Verify that the restore was successful by checking record counts.
        
        Args:
            school: The school that was restored to
            restore_op: The restore operation record
        """
        try:
            # Check key model counts
            verification_data = {
                'students': Student.objects.filter(school=school).count(),
                'teachers': Teacher.objects.filter(school=school).count(),
                'classes': Class.objects.filter(school=school).count(),
                'subjects': Subject.objects.filter(school=school).count(),
                'academic_years': AcademicYear.objects.filter(school=school).count(),
                'terms': Term.objects.filter(school=school).count(),
                'assessments': Assessment.objects.filter(school=school).count(),
                'users': User.objects.filter(school=school).count(),
            }
            
            logger.info(f"Restore verification for school {school.name}:")
            for model_name, count in verification_data.items():
                logger.info(f"  {model_name}: {count} records")
            
            # Update restore operation with verification data
            restore_op.error_message = f"Verification: {verification_data}"
            restore_op.save()
            
        except Exception as e:
            logger.error(f"Error during restore verification: {str(e)}")
