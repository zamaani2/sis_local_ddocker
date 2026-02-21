"""
Mock Exam Views
Handles mock exam score entry, dashboard, and management functionality.
Similar to enhanced_scores.py but specifically for mock exams.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie, csrf_protect
from django.middleware.csrf import get_token
from django.views.decorators.http import require_POST
from django.db import transaction
from django.core.exceptions import ValidationError
from decimal import Decimal, InvalidOperation
import logging
import json
import openpyxl
from io import BytesIO
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
from openpyxl.utils import get_column_letter
from datetime import date, datetime
from django.utils import timezone


def sanitize_excel_sheet_name(name):
    """
    Sanitize a name to be used as an Excel sheet name.
    Excel sheet names have the following restrictions:
    - Maximum 31 characters
    - Cannot contain: [ ] : * ? / \ 
    - Cannot start or end with apostrophe
    - Cannot be empty
    """
    if not name:
        return "Sheet"
    
    # Remove invalid characters
    invalid_chars = [":", "\\", "/", "?", "*", "[", "]"]
    for char in invalid_chars:
        name = name.replace(char, "_")
    
    # Remove leading/trailing apostrophes
    name = name.strip("'")
    
    # Limit to 31 characters
    if len(name) > 31:
        name = name[:31]
    
    # Ensure not empty
    if not name:
        name = "Sheet"
    
    return name

from ..models import (
    User,
    Teacher,
    Student,
    StudentClass,
    Class,
    Subject,
    TeacherSubjectAssignment,
    ClassSubject,
    Assessment,
    AcademicYear,
    Term,
    ScoringConfiguration,
    GradingSystem,
    SchoolInformation,
    MockExam,
)

logger = logging.getLogger(__name__)


def get_user_school(user):
    """Get the school associated with the current user."""
    if hasattr(user, 'school') and user.school:
        return user.school
    
    # Try to get school from teacher profile
    if user.role == "teacher":
        try:
            teacher = Teacher.objects.get(user=user)
            if teacher.school:
                return teacher.school
        except Teacher.DoesNotExist:
            pass
    
    return None


@login_required
@ensure_csrf_cookie
def mock_exam_entry_view(request):
    """
    Mock exam score entry interface - similar to enhanced_enter_scores.html
    """
    user = request.user
    user_school = get_user_school(user)
    
    if not user_school:
        messages.error(request, "No school associated with your account.")
        return redirect('dashboard')
    
    # Get teacher if user is a teacher
    teacher = None
    if user.role == "teacher":
        try:
            teacher = Teacher.objects.get(user=user)
        except Teacher.DoesNotExist:
            messages.error(request, "Teacher profile not found.")
            return redirect('dashboard')
    
    # Get available assignments for the user
    if user.role == "teacher" and teacher:
        assignments = TeacherSubjectAssignment.objects.filter(
            teacher=teacher,
            is_active=True,
            school=user_school
        ).select_related('class_assigned', 'subject', 'academic_year')
    elif user.role == "admin":
        assignments = TeacherSubjectAssignment.objects.filter(
            is_active=True,
            school=user_school
        ).select_related('class_assigned', 'subject', 'academic_year')
    else:
        assignments = TeacherSubjectAssignment.objects.none()
    
    # Get current academic year
    current_academic_year = AcademicYear.objects.filter(
        school=user_school,
        is_current=True
    ).first()
    
    if not current_academic_year:
        messages.error(request, "No active academic year found.")
        return redirect('dashboard')
    
    # Get students for selected class/subject
    students = []
    selected_assignment = None
    
    if request.method == 'GET' and 'assignment_id' in request.GET:
        assignment_id = request.GET.get('assignment_id')
        try:
            selected_assignment = get_object_or_404(
                TeacherSubjectAssignment,
                id=assignment_id,
                school=user_school
            )
            
            # Get students in this class
            # Filter by assigned_class, is_active, and through the class's academic_year
            students_query = StudentClass.objects.filter(
                assigned_class=selected_assignment.class_assigned,
                is_active=True,
                assigned_class__academic_year=current_academic_year,
                school=user_school,
                student__school=user_school
            )
            
            students = students_query.select_related('student', 'assigned_class').order_by('student__full_name')
            
        except Http404:
            # Assignment not found - let 404 bubble up
            raise
        except Exception as e:
            logger.error(f"Error getting students for assignment {assignment_id}: {e}", exc_info=True)
            messages.error(request, f"Error loading students for selected class: {str(e)}")
    
    # Get active mock exams for the current academic year
    active_mock_exams = MockExam.objects.filter(
        school=user_school,
        academic_year=current_academic_year,
        is_active=True
    ).order_by('-exam_date', '-created_at')
    
    # Get default active mock exam (first one, most recent by date)
    default_mock_exam = active_mock_exams.first()
    
    # Get existing mock exam scores for the selected assignment
    existing_scores = {}
    selected_mock_exam_id = request.GET.get('mock_exam_id')
    selected_mock_exam = None
    
    # Use default mock exam if no specific one is selected
    if selected_mock_exam_id:
        try:
            selected_mock_exam = MockExam.objects.get(
                id=selected_mock_exam_id,
                school=user_school,
                is_active=True
            )
        except MockExam.DoesNotExist:
            selected_mock_exam = default_mock_exam
    else:
        selected_mock_exam = default_mock_exam
    
    # Only load existing scores if we have both assignment and mock exam
    if selected_assignment and selected_mock_exam:
        class_subject = ClassSubject.objects.filter(
            class_name=selected_assignment.class_assigned,
            subject=selected_assignment.subject,
            academic_year=current_academic_year,
            is_active=True
        ).first()
        
        if class_subject:
            assessments = Assessment.objects.filter(
                class_subject=class_subject,
                assessment_type='mock_exam',
                mock_exam=selected_mock_exam
            ).select_related('student')
            
            for assessment in assessments:
                existing_scores[assessment.student.id] = {
                    'raw_exam_score': assessment.raw_exam_score,
                    'total_score': assessment.total_score,
                    'grade': assessment.grade,
                    'remarks': assessment.remarks,
                    'position': assessment.position,
                    'date_recorded': assessment.date_recorded,
                }
    elif selected_assignment and not selected_mock_exam:
        # If assignment is selected but no mock exam, show warning
        if active_mock_exams.exists():
            messages.warning(request, "No active mock exam found. Please create an active mock exam first.")
        else:
            messages.warning(request, "No active mock exam found. Please create an active mock exam first.")
    
    context = {
        'assignments': assignments,
        'selected_assignment': selected_assignment,
        'students': students,
        'existing_scores': existing_scores,
        'current_academic_year': current_academic_year,
        'user_school': user_school,
        'active_mock_exams': active_mock_exams,
        'selected_mock_exam': selected_mock_exam,
    }
    
    return render(request, 'mock_exams/mock_exam_entry.html', context)


@login_required
@csrf_protect
@require_POST
def save_mock_exam_scores(request):
    """
    AJAX endpoint to save mock exam scores
    """
    # Verify user has permission (teacher or admin)
    if request.user.role not in ['teacher', 'admin']:
        return JsonResponse({
            'success': False,
            'message': 'You do not have permission to save mock exam scores.'
        }, status=403)
    
    try:
        data = json.loads(request.body)
        assignment_id = data.get('assignment_id')
        mock_exam_id = data.get('mock_exam_id')
        scores = data.get('scores', {})
        
        if not assignment_id or not mock_exam_id:
            return JsonResponse({
                'success': False,
                'message': 'Assignment ID and mock exam are required.'
            })
        
        # Get assignment
        assignment = get_object_or_404(
            TeacherSubjectAssignment,
            id=assignment_id,
            school=get_user_school(request.user)
        )
        
        # Get class subject
        current_academic_year = AcademicYear.objects.filter(
            school=get_user_school(request.user),
            is_current=True
        ).first()
        
        class_subject = ClassSubject.objects.filter(
            class_name=assignment.class_assigned,
            subject=assignment.subject,
            academic_year=current_academic_year,
            is_active=True
        ).first()
        
        if not class_subject:
            return JsonResponse({
                'success': False,
                'message': 'Class subject not found.'
            })
        
        # Get mock exam
        try:
            mock_exam = MockExam.objects.get(
                id=mock_exam_id,
                school=get_user_school(request.user),
                is_active=True
            )
        except MockExam.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Selected mock exam not found or is not active.'
            })
        
        # Term is now optional for mock exams, but we can still set it if available for reference
        # This allows mock exams to be associated with a term without requiring it
        term = None
        if current_academic_year:
            term = Term.objects.filter(
                school=get_user_school(request.user),
                academic_year=current_academic_year,
                is_current=True
            ).first()
            
            # If no current term, get the first term of the academic year (optional)
            if not term:
                term = Term.objects.filter(
                    school=get_user_school(request.user),
                    academic_year=current_academic_year
                ).first()
        
        with transaction.atomic():
            saved_assessments = []
            
            for student_id, score_data in scores.items():
                try:
                    student_id = int(student_id)
                    raw_score = Decimal(str(score_data.get('raw_score', 0)))
                    
                    if raw_score < 0 or raw_score > 100:
                        continue
                    
                    # Get student
                    student = get_object_or_404(Student, id=student_id, school=get_user_school(request.user))
                    
                    # Check if assessment already exists for this student and mock exam
                    # Note: The unique constraint is (class_subject, student, mock_exam)
                    existing_assessment = Assessment.objects.filter(
                        class_subject=class_subject,
                        student=student,
                        mock_exam=mock_exam,
                        assessment_type='mock_exam'
                    ).first()
                    
                    if existing_assessment:
                        # Update existing assessment
                        existing_assessment.raw_exam_score = raw_score
                        # For mock exams, set total_score directly from raw_exam_score
                        # (mock exams don't have class_score, so we use raw_exam_score as total)
                        existing_assessment.total_score = raw_score
                        existing_assessment.save()
                        assessment = existing_assessment
                    else:
                        # Create new assessment
                        # For mock exams, set total_score directly from raw_exam_score
                        # (mock exams don't have class_score, so we use raw_exam_score as total)
                        try:
                            assessment = Assessment.objects.create(
                                class_subject=class_subject,
                                student=student,
                                term=term,  # Optional - can be None for mock exams
                                assessment_type='mock_exam',
                                mock_exam=mock_exam,
                                raw_exam_score=raw_score,
                                total_score=raw_score,  # For mock exams, total = raw score
                                recorded_by=request.user,
                                school=get_user_school(request.user)
                            )
                        except Exception as create_error:
                            logger.error(f"Error creating assessment for student {student_id}: {create_error}", exc_info=True)
                            # Try to get existing one in case of race condition
                            existing_assessment = Assessment.objects.filter(
                                class_subject=class_subject,
                                student=student,
                                term=term,
                                assessment_type='mock_exam'
                            ).first()
                            if existing_assessment:
                                existing_assessment.raw_exam_score = raw_score
                                existing_assessment.total_score = raw_score
                                existing_assessment.save()
                                assessment = existing_assessment
                            else:
                                raise
                    
                    saved_assessments.append({
                        'student_id': student_id,
                        'student_name': student.full_name,
                        'raw_score': float(raw_score),
                        'total_score': float(assessment.total_score),
                        'grade': assessment.grade,
                        'remarks': assessment.remarks,
                        'position': assessment.position,
                    })
                    
                except (ValueError, InvalidOperation, ValidationError) as e:
                    logger.error(f"Error saving score for student {student_id}: {e}", exc_info=True)
                    continue
                except Exception as e:
                    logger.error(f"Unexpected error saving score for student {student_id}: {e}", exc_info=True)
                    continue
            
            return JsonResponse({
                'success': True,
                'message': f'Successfully saved {len(saved_assessments)} mock exam scores.',
                'assessments': saved_assessments
            })
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data.'
        })
    except Exception as e:
        logger.error(f"Error saving mock exam scores: {e}", exc_info=True)
        error_message = f'An error occurred while saving scores: {str(e)}'
        # Don't expose internal errors to users, but log them
        if 'unique' in str(e).lower() or 'constraint' in str(e).lower():
            error_message = 'A mock exam already exists for this student in this term. Please update the existing record instead.'
        return JsonResponse({
            'success': False,
            'message': error_message
        })


@login_required
def mock_exam_dashboard(request):
    """
    Teacher dashboard for mock exams
    """
    user = request.user
    user_school = get_user_school(user)
    
    # Get teacher if user is a teacher
    teacher = None
    if user.role == "teacher":
        try:
            teacher = Teacher.objects.get(user=user)
        except Teacher.DoesNotExist:
            messages.error(request, "Teacher profile not found.")
            return redirect('dashboard')
    
    # Get current academic year
    current_academic_year = AcademicYear.objects.filter(
        school=user_school,
        is_current=True
    ).first()
    
    if not current_academic_year:
        messages.error(request, "No active academic year found.")
        return redirect('dashboard')
    
    # Get teacher's assignments
    if user.role == "teacher" and teacher:
        assignments = TeacherSubjectAssignment.objects.filter(
            teacher=teacher,
            is_active=True,
            school=user_school
        ).select_related('class_assigned', 'subject', 'academic_year')
    elif user.role == "admin":
        assignments = TeacherSubjectAssignment.objects.filter(
            is_active=True,
            school=user_school
        ).select_related('class_assigned', 'subject', 'academic_year')
    else:
        assignments = TeacherSubjectAssignment.objects.none()
    
    # Get mock exam statistics for each assignment
    assignment_stats = []
    for assignment in assignments:
        class_subject = ClassSubject.objects.filter(
            class_name=assignment.class_assigned,
            subject=assignment.subject,
            academic_year=current_academic_year,
            is_active=True
        ).first()
        
        if class_subject:
            # Get mock exam counts and latest scores
            mock_count = Assessment.objects.filter(
                class_subject=class_subject,
                assessment_type='mock_exam'
            ).count()
            
            latest_mock = Assessment.objects.filter(
                class_subject=class_subject,
                assessment_type='mock_exam'
            ).order_by('-date_recorded').first()
            
            # Get class statistics from Assessment records
            if latest_mock and latest_mock.mock_exam:
                # Get all mock exams for this class_subject with the same mock_exam
                same_mock_exam_assessments = Assessment.objects.filter(
                    class_subject=class_subject,
                    assessment_type='mock_exam',
                    mock_exam=latest_mock.mock_exam
                )
                
                if same_mock_exam_assessments.exists():
                    scores = [float(m.total_score) for m in same_mock_exam_assessments if m.total_score]
                    class_average = sum(scores) / len(scores) if scores else 0
                    total_students = same_mock_exam_assessments.count()
                else:
                    class_average = 0
                    total_students = 0
            else:
                class_average = 0
                total_students = 0
            
            assignment_stats.append({
                'assignment': assignment,
                'class_subject': class_subject,
                'mock_count': mock_count,
                'latest_mock': latest_mock.mock_exam if latest_mock and latest_mock.mock_exam else None,
                'latest_mock_date': latest_mock.date_recorded.date() if latest_mock else None,
                'class_average': class_average,
                'total_students': total_students,
            })
    
    context = {
        'assignments': assignments,
        'assignment_stats': assignment_stats,
        'current_academic_year': current_academic_year,
        'user_school': user_school,
    }
    
    return render(request, 'mock_exams/mock_exam_dashboard.html', context)


