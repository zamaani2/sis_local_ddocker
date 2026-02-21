"""
Super Admin Backup and Restore Views

This module provides views for Super Admins to manage backup and restore operations
across all schools in the system.
"""

import os
import json
import tempfile
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
import logging

from shs_system.models import SchoolInformation, BackupOperation, RestoreOperation
from .services import SuperAdminRestoreService
from .backup_restore_forms import SuperAdminRestoreForm, SuperAdminNewSchoolRestoreForm

logger = logging.getLogger(__name__)


# Helper function to check if user is a super admin
def is_superadmin(user):
    return user.is_authenticated and user.is_superadmin


@login_required
@user_passes_test(is_superadmin)
def backup_restore_dashboard(request):
    """Super Admin backup and restore dashboard"""
    
    # Get all schools
    schools = SchoolInformation.objects.all().order_by('name')
    
    # Get recent backup operations across all schools
    recent_backups = BackupOperation.objects.select_related('school', 'created_by').order_by('-created_at')[:10]
    
    # Get recent restore operations across all schools
    recent_restores = RestoreOperation.objects.select_related('school', 'created_by').order_by('-created_at')[:10]
    
    # Get backup statistics
    total_backups = BackupOperation.objects.count()
    successful_backups = BackupOperation.objects.filter(status='completed').count()
    failed_backups = BackupOperation.objects.filter(status='failed').count()
    
    # Get restore statistics
    total_restores = RestoreOperation.objects.count()
    successful_restores = RestoreOperation.objects.filter(status='completed').count()
    failed_restores = RestoreOperation.objects.filter(status='failed').count()
    
    context = {
        'schools': schools,
        'recent_backups': recent_backups,
        'recent_restores': recent_restores,
        'total_backups': total_backups,
        'successful_backups': successful_backups,
        'failed_backups': failed_backups,
        'total_restores': total_restores,
        'successful_restores': successful_restores,
        'failed_restores': failed_restores,
    }
    
    return render(request, 'super_admin/backup_restore/dashboard.html', context)


@login_required
@user_passes_test(is_superadmin)
def restore_to_existing_school(request):
    """Restore backup to an existing school"""
    
    if request.method == 'POST':
        form = SuperAdminRestoreForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Get form data
                target_school = form.cleaned_data['target_school']
                backup_file = request.FILES.get('backup_file')
                restore_database = form.cleaned_data.get('restore_database', True)
                restore_media_files = form.cleaned_data.get('restore_media_files', True)
                restore_static_files = form.cleaned_data.get('restore_static_files', False)
                backup_existing_data = form.cleaned_data.get('backup_existing_data', True)
                
                # Save uploaded file temporarily
                temp_dir = os.path.join(getattr(settings, 'BACKUP_DIR', r'C:\backups'), 'temp_uploads')
                os.makedirs(temp_dir, exist_ok=True)
                
                temp_file_path = os.path.join(temp_dir, backup_file.name)
                with open(temp_file_path, 'wb') as temp_file:
                    for chunk in backup_file.chunks():
                        temp_file.write(chunk)
                
                # Initialize restore service
                restore_service = SuperAdminRestoreService(request.user)
                
                # Start restore process
                restore_op = restore_service.restore_to_existing_school(
                    backup_path=temp_file_path,
                    target_school=target_school,
                    restore_database=restore_database,
                    restore_media_files=restore_media_files,
                    restore_static_files=restore_static_files,
                    backup_existing_data=backup_existing_data
                )
                
                # Clean up temp file
                try:
                    os.remove(temp_file_path)
                except:
                    pass
                
                messages.success(
                    request, 
                    f"Restore operation started for '{target_school.name}'. "
                    f"Operation ID: {restore_op.id}"
                )
                return redirect('super_admin:restore_status', restore_id=restore_op.id)
                
            except Exception as e:
                logger.error(f"Error starting restore: {str(e)}")
                messages.error(request, f"Error starting restore: {str(e)}")
                
                # Clean up temp file if it exists
                try:
                    if 'temp_file_path' in locals():
                        os.remove(temp_file_path)
                except:
                    pass
    else:
        form = SuperAdminRestoreForm()
    
    context = {
        'form': form,
        'title': 'Restore to Existing School',
        'action': 'restore_existing'
    }
    
    return render(request, 'super_admin/backup_restore/restore_form.html', context)


@login_required
@user_passes_test(is_superadmin)
def restore_to_new_school(request):
    """Restore backup to create a new school"""
    
    if request.method == 'POST':
        form = SuperAdminNewSchoolRestoreForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Get form data
                backup_file = request.FILES.get('backup_file')
                new_school_name = form.cleaned_data['new_school_name']
                new_school_domain = form.cleaned_data['new_school_domain']
                admin_name = form.cleaned_data['admin_name']
                admin_email = form.cleaned_data['admin_email']
                restore_database = form.cleaned_data.get('restore_database', True)
                restore_media_files = form.cleaned_data.get('restore_media_files', True)
                restore_static_files = form.cleaned_data.get('restore_static_files', False)
                
                # Save uploaded file temporarily
                temp_dir = os.path.join(getattr(settings, 'BACKUP_DIR', r'C:\backups'), 'temp_uploads')
                os.makedirs(temp_dir, exist_ok=True)
                
                temp_file_path = os.path.join(temp_dir, backup_file.name)
                with open(temp_file_path, 'wb') as temp_file:
                    for chunk in backup_file.chunks():
                        temp_file.write(chunk)
                
                # Initialize restore service
                restore_service = SuperAdminRestoreService(request.user)
                
                # Start restore process
                new_school, restore_op = restore_service.restore_to_new_school(
                    backup_path=temp_file_path,
                    new_school_name=new_school_name,
                    new_school_domain=new_school_domain,
                    admin_name=admin_name,
                    admin_email=admin_email,
                    restore_database=restore_database,
                    restore_media_files=restore_media_files,
                    restore_static_files=restore_static_files
                )
                
                # Clean up temp file
                try:
                    os.remove(temp_file_path)
                except:
                    pass
                
                messages.success(
                    request, 
                    f"New school '{new_school.name}' created and restored successfully. "
                    f"Operation ID: {restore_op.id}"
                )
                return redirect('super_admin:restore_status', restore_id=restore_op.id)
                
            except Exception as e:
                logger.error(f"Error creating new school from backup: {str(e)}")
                messages.error(request, f"Error creating new school: {str(e)}")
                
                # Clean up temp file if it exists
                try:
                    if 'temp_file_path' in locals():
                        os.remove(temp_file_path)
                except:
                    pass
    else:
        form = SuperAdminNewSchoolRestoreForm()
    
    context = {
        'form': form,
        'title': 'Create New School from Backup',
        'action': 'restore_new'
    }
    
    return render(request, 'super_admin/backup_restore/restore_form.html', context)


@login_required
@user_passes_test(is_superadmin)
def restore_status(request, restore_id):
    """View restore operation status"""
    
    restore_op = get_object_or_404(RestoreOperation, id=restore_id)
    
    context = {
        'restore_op': restore_op,
        'school': restore_op.school,
    }
    
    return render(request, 'super_admin/backup_restore/restore_status.html', context)


@login_required
@user_passes_test(is_superadmin)
def validate_backup_file(request):
    """Validate a backup file and return information about it"""
    
    if request.method == 'POST':
        try:
            backup_file = request.FILES.get('backup_file')
            if not backup_file:
                return JsonResponse({
                    'success': False,
                    'message': 'No backup file provided'
                })
            
            # Save uploaded file temporarily
            temp_dir = os.path.join(getattr(settings, 'BACKUP_DIR', r'C:\backups'), 'temp_uploads')
            os.makedirs(temp_dir, exist_ok=True)
            
            temp_file_path = os.path.join(temp_dir, backup_file.name)
            with open(temp_file_path, 'wb') as temp_file:
                for chunk in backup_file.chunks():
                    temp_file.write(chunk)
            
            # Initialize restore service
            restore_service = SuperAdminRestoreService(request.user)
            
            # Validate backup file
            is_valid, error_message = restore_service.validate_backup_file(temp_file_path)
            
            if is_valid:
                # Get backup info
                backup_info = restore_service.get_backup_info(temp_file_path)
                
                # Clean up temp file
                try:
                    os.remove(temp_file_path)
                except:
                    pass
                
                return JsonResponse({
                    'success': True,
                    'message': 'Backup file is valid',
                    'backup_info': backup_info
                })
            else:
                # Clean up temp file
                try:
                    os.remove(temp_file_path)
                except:
                    pass
                
                return JsonResponse({
                    'success': False,
                    'message': error_message
                })
                
        except Exception as e:
            logger.error(f"Error validating backup file: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': f'Error validating backup file: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method'
    })


@login_required
@user_passes_test(is_superadmin)
def school_backups(request, school_id):
    """View all backups for a specific school"""
    
    school = get_object_or_404(SchoolInformation, id=school_id)
    backups = BackupOperation.objects.filter(school=school).order_by('-created_at')
    
    context = {
        'school': school,
        'backups': backups,
    }
    
    return render(request, 'super_admin/backup_restore/school_backups.html', context)


@login_required
@user_passes_test(is_superadmin)
def school_restores(request, school_id):
    """View all restore operations for a specific school"""
    
    school = get_object_or_404(SchoolInformation, id=school_id)
    restores = RestoreOperation.objects.filter(school=school).order_by('-created_at')
    
    context = {
        'school': school,
        'restores': restores,
    }
    
    return render(request, 'super_admin/backup_restore/school_restores.html', context)


@login_required
@user_passes_test(is_superadmin)
def all_backups(request):
    """View all backups across all schools"""
    
    backups = BackupOperation.objects.select_related('school', 'created_by').order_by('-created_at')
    
    # Add pagination if needed
    from django.core.paginator import Paginator
    paginator = Paginator(backups, 25)  # Show 25 backups per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'backups': page_obj,
    }
    
    return render(request, 'super_admin/backup_restore/all_backups.html', context)


@login_required
@user_passes_test(is_superadmin)
def all_restores(request):
    """View all restore operations across all schools"""
    
    restores = RestoreOperation.objects.select_related('school', 'created_by').order_by('-created_at')
    
    # Add pagination if needed
    from django.core.paginator import Paginator
    paginator = Paginator(restores, 25)  # Show 25 restores per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'restores': page_obj,
    }
    
    return render(request, 'super_admin/backup_restore/all_restores.html', context)


@login_required
@user_passes_test(is_superadmin)
def download_backup(request, backup_id):
    """Download a backup file"""
    
    backup_op = get_object_or_404(BackupOperation, id=backup_id)
    
    if not os.path.exists(backup_op.backup_file_path):
        messages.error(request, 'Backup file not found')
        return redirect('super_admin:backup_restore_dashboard')
    
    try:
        with open(backup_op.backup_file_path, 'rb') as backup_file:
            response = HttpResponse(backup_file.read(), content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(backup_op.backup_file_path)}"'
            return response
    except Exception as e:
        logger.error(f"Error downloading backup: {str(e)}")
        messages.error(request, f'Error downloading backup: {str(e)}')
        return redirect('super_admin:backup_restore_dashboard')


@login_required
@user_passes_test(is_superadmin)
def delete_backup(request, backup_id):
    """Delete a backup file and its operation record"""
    
    backup_op = get_object_or_404(BackupOperation, id=backup_id)
    
    if request.method == 'POST':
        try:
            # Delete the file if it exists
            if os.path.exists(backup_op.backup_file_path):
                os.remove(backup_op.backup_file_path)
            
            # Delete the operation record
            backup_name = backup_op.backup_name
            backup_op.delete()
            
            messages.success(request, f'Backup "{backup_name}" deleted successfully')
            
        except Exception as e:
            logger.error(f"Error deleting backup: {str(e)}")
            messages.error(request, f'Error deleting backup: {str(e)}')
    
    return redirect('super_admin:backup_restore_dashboard')
