"""
Views for Backup and Restore functionality in Multi-Tenant School Management System

This module provides views for managing backup and restore operations,
ensuring proper access control and user experience.
"""

import os
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils.decorators import method_decorator
from django.views import View
from django.conf import settings
from django.utils import timezone
from django.db import transaction
import logging

from ..models import SchoolInformation, BackupOperation, RestoreOperation
from ..services.backup_service import BackupService
from ..services.restore_service import RestoreService
from ..decorators import admin_required

logger = logging.getLogger(__name__)


@login_required
@admin_required
def backup_dashboard(request):
    """
    Main dashboard for backup operations.
    Shows list of existing backups and provides options to create new ones.
    """
    school = request.user.school
    if not school:
        messages.error(request, "No school associated with your account.")
        return redirect('admin_dashboard')
    
    backup_service = BackupService(school)
    backups = backup_service.list_backups()
    
    context = {
        'school': school,
        'backups': backups,
        'page_title': 'Backup Management',
    }
    
    return render(request, 'backup_restore/backup_dashboard.html', context)


@login_required
@admin_required
@require_http_methods(["POST"])
def create_backup(request):
    """
    Create a new backup for the school.
    """
    school = request.user.school
    if not school:
        return JsonResponse({'success': False, 'message': 'No school associated with your account.'})
    
    try:
        # Get form data
        backup_name = request.POST.get('backup_name', '').strip()
        # Checkboxes: if present in POST data, they are checked (True), otherwise unchecked (False)
        includes_database = 'includes_database' in request.POST
        includes_media_files = 'includes_media_files' in request.POST
        includes_static_files = 'includes_static_files' in request.POST
        
        # Validate backup name
        if not backup_name:
            backup_name = f"Backup - {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Create backup operation record first
        backup_op = BackupOperation.objects.create(
            school=school,
            created_by=request.user,
            backup_name=backup_name,
            backup_file_path="",  # Will be set after backup creation
            status='pending',
            includes_database=includes_database,
            includes_media_files=includes_media_files,
            includes_static_files=includes_static_files
        )
        
        # Start backup process asynchronously
        import threading
        
        def run_backup():
            try:
                # Import here to avoid circular imports
                from shs_system.services.backup_service import BackupService
                
                # Create new Django connection for this thread
                from django.db import connection
                connection.close()
                
                backup_service = BackupService(school)
                backup_service._create_backup_for_operation(
                    backup_op,
                    includes_database,
                    includes_media_files,
                    includes_static_files
                )
                
            except Exception as e:
                logger.error(f"Error in backup thread: {str(e)}")
                # Update backup operation to failed status
                try:
                    backup_op.status = 'failed'
                    backup_op.error_message = str(e)
                    backup_op.save()
                except:
                    pass
        
        # Start backup in background thread
        thread = threading.Thread(target=run_backup)
        thread.daemon = True
        thread.start()
        
        return JsonResponse({
            'success': True,
            'message': 'Backup process started!',
            'backup_id': backup_op.id,
            'backup_name': backup_op.backup_name,
            'status': backup_op.status
        })
        
    except Exception as e:
        logger.error(f"Error creating backup: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Error creating backup: {str(e)}'
        })


@login_required
@admin_required
def backup_status(request, backup_id):
    """
    Get status of a backup operation.
    """
    school = request.user.school
    if not school:
        return JsonResponse({'success': False, 'message': 'No school associated with your account.'})
    
    try:
        backup_op = get_object_or_404(BackupOperation, id=backup_id, school=school)
        
        return JsonResponse({
            'success': True,
            'status': backup_op.status,
            'backup_name': backup_op.backup_name,
            'created_at': backup_op.created_at.isoformat(),
            'completed_at': backup_op.completed_at.isoformat() if backup_op.completed_at else None,
            'backup_size': backup_op.backup_size_human,
            'error_message': backup_op.error_message,
            'database_records_count': backup_op.database_records_count,
            'media_files_count': backup_op.media_files_count,
        })
        
    except Exception as e:
        logger.error(f"Error getting backup status: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Error getting backup status: {str(e)}'
        })


@login_required
@admin_required
def download_backup(request, backup_id):
    """
    Download a backup file.
    """
    school = request.user.school
    if not school:
        messages.error(request, "No school associated with your account.")
        return redirect('backup_dashboard')
    
    try:
        backup_op = get_object_or_404(BackupOperation, id=backup_id, school=school)
        
        if backup_op.status != 'completed':
            messages.error(request, "Backup is not completed yet.")
            return redirect('backup_dashboard')
        
        if not os.path.exists(backup_op.backup_file_path):
            messages.error(request, "Backup file not found.")
            return redirect('backup_dashboard')
        
        # Create response with file
        with open(backup_op.backup_file_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename="{backup_op.backup_name}.zip"'
            return response
            
    except Exception as e:
        logger.error(f"Error downloading backup: {str(e)}")
        messages.error(request, f"Error downloading backup: {str(e)}")
        return redirect('backup_dashboard')


@login_required
@admin_required
@require_http_methods(["POST"])
def delete_backup(request, backup_id):
    """
    Delete a backup file and its record.
    """
    school = request.user.school
    if not school:
        return JsonResponse({'success': False, 'message': 'No school associated with your account.'})
    
    try:
        backup_op = get_object_or_404(BackupOperation, id=backup_id, school=school)
        
        backup_service = BackupService(school)
        success = backup_service.delete_backup(backup_op.backup_file_path)
        
        if success:
            return JsonResponse({
                'success': True,
                'message': 'Backup deleted successfully!'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Error deleting backup file.'
            })
            
    except Exception as e:
        logger.error(f"Error deleting backup: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Error deleting backup: {str(e)}'
        })


@login_required
@admin_required
def restore_dashboard(request):
    """
    Main dashboard for restore operations.
    Shows restore history and provides options to restore from backup files.
    """
    school = request.user.school
    if not school:
        messages.error(request, "No school associated with your account.")
        return redirect('admin_dashboard')
    
    restore_service = RestoreService(school)
    restores = restore_service.get_restore_history()
    
    context = {
        'school': school,
        'restores': restores,
        'page_title': 'Restore Management',
    }
    
    return render(request, 'backup_restore/restore_dashboard.html', context)


@login_required
@admin_required
@require_http_methods(["POST"])
def upload_backup_file(request):
    """
    Upload a backup file for restore operation.
    """
    school = request.user.school
    if not school:
        return JsonResponse({'success': False, 'message': 'No school associated with your account.'})
    
    try:
        if 'backup_file' not in request.FILES:
            return JsonResponse({'success': False, 'message': 'No backup file provided.'})
        
        backup_file = request.FILES['backup_file']
        
        # Validate file type
        if not backup_file.name.endswith('.zip'):
            return JsonResponse({'success': False, 'message': 'Please upload a valid backup file (.zip).'})
        
        # Save uploaded file temporarily to a more accessible location
        upload_dir = os.path.join(getattr(settings, 'BACKUP_DIR', r'C:\backups'), 'temp_uploads')
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, backup_file.name)
        with open(file_path, 'wb') as f:
            for chunk in backup_file.chunks():
                f.write(chunk)
        
        # Validate backup file
        restore_service = RestoreService(school)
        is_compatible, message = restore_service.validate_restore_compatibility(file_path)
        
        if not is_compatible:
            # Clean up uploaded file
            os.remove(file_path)
            return JsonResponse({'success': False, 'message': message})
        
        # Get backup info
        backup_service = BackupService(school)
        backup_info = backup_service.get_backup_info(file_path)
        
        return JsonResponse({
            'success': True,
            'message': 'Backup file uploaded and validated successfully!',
            'file_path': file_path,
            'backup_info': backup_info
        })
        
    except Exception as e:
        logger.error(f"Error uploading backup file: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Error uploading backup file: {str(e)}'
        })


@login_required
@admin_required
@require_http_methods(["POST"])
def restore_from_backup(request):
    """
    Restore school data from a backup file.
    """
    school = request.user.school
    if not school:
        return JsonResponse({'success': False, 'message': 'No school associated with your account.'})
    
    try:
        # Get form data
        backup_file_path = request.POST.get('backup_file_path', '').strip()
        # Checkboxes: if present in POST data, they are checked (True), otherwise unchecked (False)
        restore_database = 'restore_database' in request.POST
        restore_media_files = 'restore_media_files' in request.POST
        restore_static_files = 'restore_static_files' in request.POST
        backup_existing_data = 'backup_existing_data' in request.POST
        
        if not backup_file_path or not os.path.exists(backup_file_path):
            return JsonResponse({'success': False, 'message': 'Invalid backup file path.'})
        
        # Create restore operation first
        from shs_system.models import RestoreOperation
        restore_op = RestoreOperation.objects.create(
            school=school,
            created_by=request.user,
            backup_file_path=backup_file_path,
            status='in_progress',
            restore_database=restore_database,
            restore_media_files=restore_media_files,
            restore_static_files=restore_static_files,
            backup_existing_data=backup_existing_data
        )
        
        # Start restore process asynchronously
        import threading
        
        def run_restore():
            try:
                # Import here to avoid circular imports
                from shs_system.services.restore_service import RestoreService
                
                # Create new Django connection for this thread
                from django.db import connection
                connection.close()
                
                restore_service = RestoreService(school)
                restore_service.restore_from_backup_with_operation(
                    backup_path=backup_file_path,
                    created_by=request.user,
                    restore_database=restore_database,
                    restore_media_files=restore_media_files,
                    restore_static_files=restore_static_files,
                    backup_existing_data=backup_existing_data,
                    restore_op=restore_op
                )
                
            except Exception as e:
                logger.error(f"Restore failed for school {school.name}: {str(e)}")
                # Update restore operation to failed status
                try:
                    restore_op.status = 'failed'
                    restore_op.error_message = str(e)
                    restore_op.save()
                except:
                    pass
        
        # Start restore in background thread
        thread = threading.Thread(target=run_restore)
        thread.daemon = True
        thread.start()
        
        return JsonResponse({
            'success': True,
            'message': 'Restore operation started successfully.',
            'restore_id': restore_op.id
        })
        
    except Exception as e:
        logger.error(f"Error restoring from backup: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Error restoring from backup: {str(e)}'
        })


@login_required
@admin_required
def restore_status(request, restore_id):
    """
    Get status of a restore operation.
    """
    school = request.user.school
    if not school:
        return JsonResponse({'success': False, 'message': 'No school associated with your account.'})
    
    try:
        restore_op = get_object_or_404(RestoreOperation, id=restore_id, school=school)
        
        return JsonResponse({
            'success': True,
            'status': restore_op.status,
            'created_at': restore_op.created_at.isoformat(),
            'completed_at': restore_op.completed_at.isoformat() if restore_op.completed_at else None,
            'error_message': restore_op.error_message,
            'restored_records_count': restore_op.restored_records_count,
            'restored_files_count': restore_op.restored_files_count,
        })
        
    except Exception as e:
        logger.error(f"Error getting restore status: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Error getting restore status: {str(e)}'
        })


@login_required
@admin_required
def backup_restore_settings(request):
    """
    Settings page for backup and restore configuration.
    """
    school = request.user.school
    if not school:
        messages.error(request, "No school associated with your account.")
        return redirect('admin_dashboard')
    
    context = {
        'school': school,
        'page_title': 'Backup & Restore Settings',
        'backup_dir': getattr(settings, 'BACKUP_DIR', os.path.join(settings.BASE_DIR, 'backups')),
    }
    
    return render(request, 'backup_restore/settings.html', context)


@login_required
@admin_required
def validate_backup_file(request):
    """
    Validate a backup file without uploading it.
    """
    school = request.user.school
    if not school:
        return JsonResponse({'success': False, 'message': 'No school associated with your account.'})
    
    try:
        backup_file_path = request.GET.get('file_path', '').strip()
        
        if not backup_file_path or not os.path.exists(backup_file_path):
            return JsonResponse({'success': False, 'message': 'Backup file not found.'})
        
        restore_service = RestoreService(school)
        is_compatible, message = restore_service.validate_restore_compatibility(backup_file_path)
        
        return JsonResponse({
            'success': is_compatible,
            'message': message
        })
        
    except Exception as e:
        logger.error(f"Error validating backup file: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Error validating backup file: {str(e)}'
        })


@login_required
@admin_required
def backup_settings(request):
    """
    Get current backup settings for the school.
    """
    school = request.user.school
    if not school:
        return JsonResponse({'success': False, 'message': 'No school associated with your account.'})
    
    try:
        from shs_system.models import BackupSettings
        settings = BackupSettings.get_or_create_for_school(school)
        
        return JsonResponse({
            'success': True,
            'settings': {
                'default_backup_name': settings.default_backup_name,
                'default_includes_database': settings.default_includes_database,
                'default_includes_media_files': settings.default_includes_media_files,
                'default_includes_static_files': settings.default_includes_static_files,
                'default_restore_database': settings.default_restore_database,
                'default_restore_media_files': settings.default_restore_media_files,
                'default_restore_static_files': settings.default_restore_static_files,
                'default_backup_existing_data': settings.default_backup_existing_data,
                'auto_cleanup_temp_files': settings.auto_cleanup_temp_files,
                'temp_file_retention_hours': settings.temp_file_retention_hours,
                'updated_at': settings.updated_at.isoformat() if settings.updated_at else None,
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting backup settings: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Error getting backup settings: {str(e)}'
        })


@login_required
@admin_required
@require_http_methods(["POST"])
def save_backup_settings(request):
    """
    Save backup settings for the school.
    """
    school = request.user.school
    if not school:
        return JsonResponse({'success': False, 'message': 'No school associated with your account.'})
    
    try:
        from shs_system.models import BackupSettings
        
        # Get form data
        settings_data = {
            'default_backup_name': request.POST.get('default_backup_name', '').strip(),
            'default_includes_database': 'default_includes_database' in request.POST,
            'default_includes_media_files': 'default_includes_media_files' in request.POST,
            'default_includes_static_files': 'default_includes_static_files' in request.POST,
            'default_restore_database': 'default_restore_database' in request.POST,
            'default_restore_media_files': 'default_restore_media_files' in request.POST,
            'default_restore_static_files': 'default_restore_static_files' in request.POST,
            'default_backup_existing_data': 'default_backup_existing_data' in request.POST,
            'auto_cleanup_temp_files': 'auto_cleanup_temp_files' in request.POST,
            'temp_file_retention_hours': int(request.POST.get('temp_file_retention_hours', 24)),
            'updated_by': request.user,
        }
        
        # Validate temp_file_retention_hours
        if settings_data['temp_file_retention_hours'] < 1 or settings_data['temp_file_retention_hours'] > 168:
            return JsonResponse({
                'success': False,
                'message': 'Temp file retention must be between 1 and 168 hours.'
            })
        
        # Get or create settings
        settings = BackupSettings.get_or_create_for_school(school)
        
        # Update settings
        for key, value in settings_data.items():
            if hasattr(settings, key):
                setattr(settings, key, value)
        
        settings.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Backup settings saved successfully!',
            'settings': {
                'default_backup_name': settings.default_backup_name,
                'default_includes_database': settings.default_includes_database,
                'default_includes_media_files': settings.default_includes_media_files,
                'default_includes_static_files': settings.default_includes_static_files,
                'default_restore_database': settings.default_restore_database,
                'default_restore_media_files': settings.default_restore_media_files,
                'default_restore_static_files': settings.default_restore_static_files,
                'default_backup_existing_data': settings.default_backup_existing_data,
                'auto_cleanup_temp_files': settings.auto_cleanup_temp_files,
                'temp_file_retention_hours': settings.temp_file_retention_hours,
                'updated_at': settings.updated_at.isoformat(),
            }
        })
        
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'message': f'Invalid input: {str(e)}'
        })
    except Exception as e:
        logger.error(f"Error saving backup settings: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Error saving backup settings: {str(e)}'
        })


@login_required
@admin_required
@require_http_methods(["POST"])
def reset_backup_settings(request):
    """
    Reset backup settings to defaults for the school.
    """
    school = request.user.school
    if not school:
        return JsonResponse({'success': False, 'message': 'No school associated with your account.'})
    
    try:
        from shs_system.models import BackupSettings
        
        # Get or create settings
        settings = BackupSettings.get_or_create_for_school(school)
        
        # Reset to defaults
        settings.default_backup_name = f"{school.name} Backup"
        settings.default_includes_database = True
        settings.default_includes_media_files = True
        settings.default_includes_static_files = False
        settings.default_restore_database = True
        settings.default_restore_media_files = True
        settings.default_restore_static_files = False
        settings.default_backup_existing_data = True
        settings.auto_cleanup_temp_files = True
        settings.temp_file_retention_hours = 24
        settings.updated_by = request.user
        
        settings.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Backup settings reset to defaults successfully!',
            'settings': {
                'default_backup_name': settings.default_backup_name,
                'default_includes_database': settings.default_includes_database,
                'default_includes_media_files': settings.default_includes_media_files,
                'default_includes_static_files': settings.default_includes_static_files,
                'default_restore_database': settings.default_restore_database,
                'default_restore_media_files': settings.default_restore_media_files,
                'default_restore_static_files': settings.default_restore_static_files,
                'default_backup_existing_data': settings.default_backup_existing_data,
                'auto_cleanup_temp_files': settings.auto_cleanup_temp_files,
                'temp_file_retention_hours': settings.temp_file_retention_hours,
                'updated_at': settings.updated_at.isoformat(),
            }
        })
        
    except Exception as e:
        logger.error(f"Error resetting backup settings: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Error resetting backup settings: {str(e)}'
        })


@login_required
@admin_required
@require_http_methods(["POST"])
def cleanup_temp_files(request):
    """
    Clean up old temporary backup files.
    """
    school = request.user.school
    if not school:
        return JsonResponse({'success': False, 'message': 'No school associated with your account.'})
    
    try:
        from shs_system.services.restore_service import RestoreService
        
        # Get retention hours from request or use default
        retention_hours = int(request.POST.get('retention_hours', 24))
        
        restore_service = RestoreService(school)
        restore_service.cleanup_old_temp_files(retention_hours)
        
        return JsonResponse({
            'success': True,
            'message': f'Temporary files older than {retention_hours} hours have been cleaned up.'
        })
        
    except Exception as e:
        logger.error(f"Error cleaning up temp files: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Error cleaning up temp files: {str(e)}'
        })
