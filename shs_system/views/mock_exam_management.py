"""
Views for Mock Exam Management.
Handles CRUD operations for mock exams.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from datetime import date
import json

from ..models import (
    MockExam,
    AcademicYear,
    SchoolInformation,
    Assessment,
    User,
)
from .auth import is_admin


@login_required
@user_passes_test(is_admin)
def mock_exam_list(request):
    """
    List all mock exams for the user's school.
    """
    school = request.user.school
    
    # Get current academic year
    current_academic_year = AcademicYear.objects.filter(
        school=school,
        is_current=True
    ).first()
    
    # Get all mock exams for the school
    mock_exams = MockExam.objects.filter(
        school=school
    ).select_related('academic_year', 'created_by').order_by('-exam_date', '-created_at')
    
    # Filter by academic year if requested
    academic_year_id = request.GET.get('academic_year')
    if academic_year_id:
        mock_exams = mock_exams.filter(academic_year_id=academic_year_id)
    
    # Filter by active status if requested
    status_filter = request.GET.get('status')
    if status_filter == 'active':
        mock_exams = mock_exams.filter(is_active=True)
    elif status_filter == 'inactive':
        mock_exams = mock_exams.filter(is_active=False)
    
    # Get statistics for each mock exam
    mock_exam_stats = []
    for mock_exam in mock_exams:
        # Count assessments for this mock exam
        assessment_count = Assessment.objects.filter(
            mock_exam=mock_exam,
            assessment_type='mock_exam'
        ).count()
        
        # Count unique students
        student_count = Assessment.objects.filter(
            mock_exam=mock_exam,
            assessment_type='mock_exam'
        ).values('student').distinct().count()
        
        mock_exam_stats.append({
            'mock_exam': mock_exam,
            'assessment_count': assessment_count,
            'student_count': student_count,
        })
    
    # Get all academic years for filter dropdown
    academic_years = AcademicYear.objects.filter(
        school=school
    ).order_by('-start_date')
    
    # Get academic years for modal dropdown (JSON serializable)
    academic_years_list = [
        {
            'id': year.id,
            'name': year.name,
            'is_current': year.id == current_academic_year.id if current_academic_year else False
        }
        for year in academic_years
    ]
    
    context = {
        'mock_exam_stats': mock_exam_stats,
        'academic_years': academic_years,
        'academic_years_json': json.dumps(academic_years_list),
        'current_academic_year': current_academic_year,
        'selected_academic_year_id': academic_year_id,
        'status_filter': status_filter,
        'title': 'Mock Exam Management',
        'school': school,
        'today': timezone.now().date().isoformat(),
    }
    
    return render(request, 'mock_exams/mock_exam_list.html', context)


@login_required
@user_passes_test(is_admin)
@require_http_methods(["GET", "POST"])
def mock_exam_create(request):
    """
    Create a new mock exam (supports both regular POST and AJAX).
    """
    school = request.user.school
    
    if request.method == 'POST':
        # Check if it's an AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
                name = data.get('name')
                exam_date = data.get('exam_date')
                academic_year_id = data.get('academic_year')
                description = data.get('description', '')
                is_active = data.get('is_active', True)
                
                # Validation
                if not name or not exam_date or not academic_year_id:
                    return JsonResponse({
                        'success': False,
                        'message': 'Name, exam date, and academic year are required.',
                        'errors': {'__all__': ['Name, exam date, and academic year are required.']}
                    }, status=400)
                
                academic_year = AcademicYear.objects.get(
                    id=academic_year_id,
                    school=school
                )
                
                # Parse date
                exam_date_obj = date.fromisoformat(exam_date)
                
                # Create mock exam
                mock_exam = MockExam.objects.create(
                    name=name,
                    exam_date=exam_date_obj,
                    academic_year=academic_year,
                    school=school,
                    description=description,
                    is_active=is_active,
                    created_by=request.user
                )
                
                return JsonResponse({
                    'success': True,
                    'message': f'Mock exam "{name}" created successfully.',
                    'mock_exam': {
                        'id': mock_exam.id,
                        'name': mock_exam.name,
                        'exam_date': mock_exam.exam_date.isoformat(),
                        'academic_year': mock_exam.academic_year.name,
                        'is_active': mock_exam.is_active,
                    }
                })
                
            except AcademicYear.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Selected academic year not found.',
                    'errors': {'academic_year': ['Selected academic year not found.']}
                }, status=400)
            except ValueError as e:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid date format.',
                    'errors': {'exam_date': ['Invalid date format.']}
                }, status=400)
            except ValidationError as e:
                return JsonResponse({
                    'success': False,
                    'message': str(e),
                    'errors': {'__all__': [str(e)]}
                }, status=400)
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': f'Error creating mock exam: {str(e)}',
                    'errors': {'__all__': [str(e)]}
                }, status=500)
        else:
            # Regular form POST
            name = request.POST.get('name')
            exam_date = request.POST.get('exam_date')
            academic_year_id = request.POST.get('academic_year')
            description = request.POST.get('description', '')
            is_active = request.POST.get('is_active') == 'on'
            
            # Validation
            if not name or not exam_date or not academic_year_id:
                messages.error(request, 'Name, exam date, and academic year are required.')
                return redirect('mock_exam_list')
            
            try:
                academic_year = AcademicYear.objects.get(
                    id=academic_year_id,
                    school=school
                )
                
                # Parse date
                exam_date_obj = date.fromisoformat(exam_date)
                
                # Create mock exam
                mock_exam = MockExam.objects.create(
                    name=name,
                    exam_date=exam_date_obj,
                    academic_year=academic_year,
                    school=school,
                    description=description,
                    is_active=is_active,
                    created_by=request.user
                )
                
                messages.success(request, f'Mock exam "{name}" created successfully.')
                return redirect('mock_exam_list')
                
            except (AcademicYear.DoesNotExist, ValueError, ValidationError) as e:
                messages.error(request, str(e))
                return redirect('mock_exam_list')
    
    # GET request - return JSON for AJAX or render form for regular request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Return academic years as JSON for AJAX
        academic_years = AcademicYear.objects.filter(
            school=school
        ).order_by('-start_date')
        
        current_academic_year = AcademicYear.objects.filter(
            school=school,
            is_current=True
        ).first()
        
        return JsonResponse({
            'academic_years': [
                {
                    'id': year.id,
                    'name': year.name,
                    'is_current': year.id == current_academic_year.id if current_academic_year else False
                }
                for year in academic_years
            ],
            'current_academic_year_id': current_academic_year.id if current_academic_year else None,
            'today': timezone.now().date().isoformat()
        })
    
    # Regular GET - redirect to list (shouldn't happen with modal)
    return redirect('mock_exam_list')


@login_required
@user_passes_test(is_admin)
@require_http_methods(["GET", "PUT", "POST"])
def mock_exam_update(request, pk):
    """
    Update an existing mock exam (supports both regular POST and AJAX).
    """
    school = request.user.school
    
    mock_exam = get_object_or_404(MockExam, pk=pk, school=school)
    
    if request.method in ['POST', 'PUT']:
        # Check if it's an AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json':
            try:
                data = json.loads(request.body) if request.content_type == 'application/json' else {
                    'name': request.POST.get('name'),
                    'exam_date': request.POST.get('exam_date'),
                    'academic_year': request.POST.get('academic_year'),
                    'description': request.POST.get('description', ''),
                    'is_active': request.POST.get('is_active') == 'on' if request.method == 'POST' else request.POST.get('is_active', True)
                }
                
                name = data.get('name')
                exam_date = data.get('exam_date')
                academic_year_id = data.get('academic_year')
                description = data.get('description', '')
                is_active = data.get('is_active', True)
                
                # Validation
                if not name or not exam_date or not academic_year_id:
                    return JsonResponse({
                        'success': False,
                        'message': 'Name, exam date, and academic year are required.',
                        'errors': {'__all__': ['Name, exam date, and academic year are required.']}
                    }, status=400)
                
                academic_year = AcademicYear.objects.get(
                    id=academic_year_id,
                    school=school
                )
                
                # Parse date
                exam_date_obj = date.fromisoformat(exam_date)
                
                # Update mock exam
                mock_exam.name = name
                mock_exam.exam_date = exam_date_obj
                mock_exam.academic_year = academic_year
                mock_exam.description = description
                mock_exam.is_active = is_active
                mock_exam.save()
                
                return JsonResponse({
                    'success': True,
                    'message': f'Mock exam "{name}" updated successfully.',
                    'mock_exam': {
                        'id': mock_exam.id,
                        'name': mock_exam.name,
                        'exam_date': mock_exam.exam_date.isoformat(),
                        'academic_year': mock_exam.academic_year.name,
                        'is_active': mock_exam.is_active,
                    }
                })
                
            except AcademicYear.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Selected academic year not found.',
                    'errors': {'academic_year': ['Selected academic year not found.']}
                }, status=400)
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid date format.',
                    'errors': {'exam_date': ['Invalid date format.']}
                }, status=400)
            except ValidationError as e:
                return JsonResponse({
                    'success': False,
                    'message': str(e),
                    'errors': {'__all__': [str(e)]}
                }, status=400)
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': f'Error updating mock exam: {str(e)}',
                    'errors': {'__all__': [str(e)]}
                }, status=500)
        else:
            # Regular form POST
            name = request.POST.get('name')
            exam_date = request.POST.get('exam_date')
            academic_year_id = request.POST.get('academic_year')
            description = request.POST.get('description', '')
            is_active = request.POST.get('is_active') == 'on'
            
            # Validation
            if not name or not exam_date or not academic_year_id:
                messages.error(request, 'Name, exam date, and academic year are required.')
                return redirect('mock_exam_list')
            
            try:
                academic_year = AcademicYear.objects.get(
                    id=academic_year_id,
                    school=school
                )
                
                # Parse date
                exam_date_obj = date.fromisoformat(exam_date)
                
                # Update mock exam
                mock_exam.name = name
                mock_exam.exam_date = exam_date_obj
                mock_exam.academic_year = academic_year
                mock_exam.description = description
                mock_exam.is_active = is_active
                mock_exam.save()
                
                messages.success(request, f'Mock exam "{name}" updated successfully.')
                return redirect('mock_exam_list')
                
            except (AcademicYear.DoesNotExist, ValueError, ValidationError) as e:
                messages.error(request, str(e))
                return redirect('mock_exam_list')
    
    # GET request - return JSON for AJAX
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'id': mock_exam.id,
            'name': mock_exam.name,
            'exam_date': mock_exam.exam_date.isoformat(),
            'academic_year_id': mock_exam.academic_year.id,
            'description': mock_exam.description or '',
            'is_active': mock_exam.is_active,
        })
    
    # Regular GET - redirect to list (shouldn't happen with modal)
    return redirect('mock_exam_list')


@login_required
@user_passes_test(is_admin)
def mock_exam_delete(request, pk):
    """
    Delete a mock exam.
    """
    school = request.user.school
    
    mock_exam = get_object_or_404(MockExam, pk=pk, school=school)
    
    if request.method == 'POST':
        # Check if mock exam has assessments
        assessment_count = Assessment.objects.filter(
            mock_exam=mock_exam,
            assessment_type='mock_exam'
        ).count()
        
        if assessment_count > 0:
            messages.error(
                request,
                f'Cannot delete mock exam "{mock_exam.name}" because it has {assessment_count} assessment(s). '
                'Please delete or reassign the assessments first.'
            )
            return redirect('mock_exam_list')
        
        mock_exam_name = mock_exam.name
        mock_exam.delete()
        messages.success(request, f'Mock exam "{mock_exam_name}" deleted successfully.')
        return redirect('mock_exam_list')
    
    # Get assessment count for confirmation
    assessment_count = Assessment.objects.filter(
        mock_exam=mock_exam,
        assessment_type='mock_exam'
    ).count()
    
    context = {
        'mock_exam': mock_exam,
        'assessment_count': assessment_count,
        'title': 'Delete Mock Exam',
        'school': school,
    }
    
    return render(request, 'mock_exams/mock_exam_confirm_delete.html', context)


@login_required
@user_passes_test(is_admin)
def mock_exam_toggle_active(request, pk):
    """
    Toggle the active status of a mock exam.
    """
    school = request.user.school
    
    mock_exam = get_object_or_404(MockExam, pk=pk, school=school)
    
    mock_exam.is_active = not mock_exam.is_active
    mock_exam.save()
    
    status = 'activated' if mock_exam.is_active else 'deactivated'
    messages.success(request, f'Mock exam "{mock_exam.name}" has been {status}.')
    
    return redirect('mock_exam_list')

