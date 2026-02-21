from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.urls import reverse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_protect
from shs_system.models import (
    Student,
    Class,
    StudentClass,
    User,
    AcademicYear,
    Form,
    LearningArea,
    SchoolInformation,
)
from shs_system.forms import StudentForm, StudentClassAssignmentForm
import datetime
import logging
from django.template.loader import render_to_string
from django.utils import timezone
import json
import csv
import io
from datetime import datetime as dt
from django.core.exceptions import ValidationError
from .dashboard import student_profile, student_update_profile
import os
import re
from PIL import Image
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

# Configure logger
logger = logging.getLogger(__name__)


def is_admin(user):
    return user.is_authenticated and user.role == "admin"


# Debug function to check student profile picture URLs
@login_required
def debug_student_images(request):
    """Debug view to check if student profile picture URLs are being generated correctly."""
    # Get user's school
    school = request.user.school

    # Get all students with profile pictures
    students_with_images = Student.objects.filter(
        school=school, profile_picture__isnull=False
    ).exclude(profile_picture="")

    # Generate debug information
    debug_info = ["<h1>Student Profile Picture Debug</h1>"]
    debug_info.append(
        f"<p>Found {students_with_images.count()} students with profile pictures</p>"
    )

    for student in students_with_images:
        debug_info.append("<hr>")
        debug_info.append(f"<h3>Student: {student.full_name}</h3>")
        debug_info.append(f"<p>Profile Picture Field: {student.profile_picture}</p>")
        debug_info.append(f"<p>Profile Picture URL: {student.profile_picture.url}</p>")
        debug_info.append(
            f"<p>Profile Picture Path: {student.profile_picture.path}</p>"
        )
        debug_info.append(
            f'<img src="{student.profile_picture.url}" style="max-width: 200px; border: 1px solid #ccc;">'
        )

    return HttpResponse("".join(debug_info))


@login_required
@user_passes_test(is_admin)
def student_list(request):
    """Display list of students with search and filter functionality - Optimized for performance"""
    # Get user's school for multi-tenancy
    school = request.user.school

    # Build optimized queryset with select_related and prefetch_related - exclude graduated students
    students = (
        Student.objects.filter(school=school)
        .exclude(archivedstudent__isnull=False)  # Exclude graduated students
        .select_related("form", "learning_area", "school")
        .prefetch_related("studentclass_set__assigned_class")
        .order_by("full_name")
    )

    # Get filters from request
    search_query = request.GET.get("search", "")
    form_filter = request.GET.get("form", "")
    learning_area_filter = request.GET.get("learning_area", "")
    gender_filter = request.GET.get("gender", "")
    status_filter = request.GET.get("status", "")
    class_filter = request.GET.get("class_id", "")

    # Apply filters if provided
    if search_query:
        students = students.filter(
            Q(full_name__icontains=search_query)
            | Q(admission_number__icontains=search_query)
        )

    if form_filter:

        students = students.filter(studentclass__assigned_class__form_id=form_filter, studentclass__is_active=True).distinct()

    if learning_area_filter:
        students = students.filter(studentclass__assigned_class__learning_area_id=learning_area_filter, studentclass__is_active=True).distinct()


    if gender_filter:
        students = students.filter(gender=gender_filter)

    if status_filter:
        if status_filter == "active":
            students = students.filter(studentclass__is_active=True)
        elif status_filter == "inactive":
            # Include students who are either archived or have no active class assignments
            students = students.filter(
                Q(studentclass__is_active=False) | Q(studentclass__isnull=True)
            ).distinct()

    if class_filter:
        # Include both active and archived students who were/are in this class
        students = students.filter(studentclass__assigned_class_id=class_filter)

    # Get current academic year for the school
    current_academic_year = SchoolInformation.get_current_academic_year(school=school)

    # Implement proper pagination instead of loading all students
    from django.core.paginator import Paginator

    paginator = Paginator(students, 50)  # Show 50 students per page
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    # Only create forms for students on the current page (major performance improvement)
    student_forms = {}
    assignment_forms = {}

    # Only process students on current page
    for student in page_obj:
        student_forms[student.id] = StudentForm(instance=student, school=school)
        if current_academic_year:
            assignment_forms[student.id] = StudentClassAssignmentForm(
                student=student,
                current_academic_year=current_academic_year,
                school=school,
            )

    # Cache these queries for better performance
    form_choices = [

        (form.id, form.name)

        for form in Form.objects.filter(school=school).order_by("form_number")
    ]
    learning_area_choices = [
        (area.id, area.name) for area in LearningArea.objects.filter(school=school)
    ]

    # Get available classes for adding new students and filtering
    available_classes = []
    if current_academic_year:
        available_classes = Class.objects.filter(
            academic_year=current_academic_year, school=school
        ).select_related("academic_year")

    # Use paginator.count instead of queryset.count() for better performance
    total_count = paginator.count

    context = {
        "page_obj": page_obj,
        "search_query": search_query,
        "form_choices": form_choices,
        "learning_area_choices": learning_area_choices,
        "form_filter": form_filter,
        "learning_area_filter": learning_area_filter,
        "gender_filter": gender_filter,
        "status_filter": status_filter,
        "class_filter": class_filter,
        "total_count": total_count,
        "student_forms": student_forms,
        "assignment_forms": assignment_forms,
        "new_student_form": StudentForm(school=school),
        "available_classes": available_classes,
        "school": school,
        "current_academic_year": current_academic_year,
    }

    return render(request, "student/student_list.html", context)


@login_required
@user_passes_test(is_admin)
def student_class_assignment(request):
    """Student class assignment view - shows existing students for assignment to classes"""
    # Get user's school for multi-tenancy
    school = request.user.school

    # Get current academic year for the school
    current_academic_year = SchoolInformation.get_current_academic_year(school=school)

    if not current_academic_year:
        messages.error(
            request,
            "No current academic year is set. Please set one before assigning students to classes.",
        )
        return redirect("admin_dashboard")

    # Get all students in the school - exclude graduated students
    students_query = (
        Student.objects.filter(school=school)
        .exclude(archivedstudent__isnull=False)
        .select_related("form", "learning_area")
    )

    # Apply filters from GET parameters
    current_class_filter = request.GET.get("current_class", "")
    form_filter = request.GET.get("form", "")
    learning_area_filter = request.GET.get("learning_area", "")
    gender_filter = request.GET.get("gender", "")
    status_filter = request.GET.get("status", "")

    if current_class_filter:
        if current_class_filter == "unassigned":
            # Students not assigned to any class in current academic year
            students_query = students_query.filter(
                ~Q(
                    studentclass__assigned_class__academic_year=current_academic_year,
                    studentclass__is_active=True,
                )
            )
        else:
            # Students assigned to specific class
            students_query = students_query.filter(
                studentclass__assigned_class_id=current_class_filter,
                studentclass__is_active=True,
            )

    if form_filter:
        students_query = students_query.filter(form_id=form_filter)

    if learning_area_filter:
        students_query = students_query.filter(learning_area_id=learning_area_filter)

    if gender_filter:
        students_query = students_query.filter(gender=gender_filter)

    if status_filter:
        if status_filter == "assigned":
            students_query = students_query.filter(
                studentclass__assigned_class__academic_year=current_academic_year,
                studentclass__is_active=True,
            )
        elif status_filter == "unassigned":
            students_query = students_query.filter(
                ~Q(
                    studentclass__assigned_class__academic_year=current_academic_year,
                    studentclass__is_active=True,
                )
            )

    # Get distinct students (to avoid duplicates from joins)
    students = students_query.distinct()

    # Add current class assignment information to each student
    for student in students:
        current_assignment = (
            StudentClass.objects.filter(
                student=student,
                assigned_class__academic_year=current_academic_year,
                is_active=True,
                school=school,
            )
            .select_related("assigned_class")
            .first()
        )

        # Use a different attribute name to avoid conflict with the current_class property
        student.current_class_assignment = (
            current_assignment.assigned_class if current_assignment else None
        )

    # Get available classes for assignment
    available_classes = Class.objects.filter(
        academic_year=current_academic_year, school=school
    ).order_by("name")

    # Get available forms and learning areas
    available_forms = Form.objects.filter(school=school).order_by("form_number")
    available_learning_areas = LearningArea.objects.filter(school=school).order_by(
        "name"
    )

    # Calculate statistics
    total_students = students.count()
    assigned_students = (
        students.filter(
            studentclass__assigned_class__academic_year=current_academic_year,
            studentclass__is_active=True,
        )
        .distinct()
        .count()
    )
    unassigned_students = total_students - assigned_students

    context = {
        "students": students,
        "available_classes": available_classes,
        "available_forms": available_forms,
        "available_learning_areas": available_learning_areas,
        "current_academic_year": current_academic_year,
        "school": school,
        "total_students": total_students,
        "assigned_students": assigned_students,
        "unassigned_students": unassigned_students,
        # Filter values for maintaining state
        "current_class_filter": current_class_filter,
        "form_filter": form_filter,
        "learning_area_filter": learning_area_filter,
        "gender_filter": gender_filter,
        "status_filter": status_filter,
    }

    return render(request, "student/student_class_assignment.html", context)


@login_required
@user_passes_test(is_admin)
@csrf_protect
def bulk_assign_students_to_class(request):
    """Bulk assign students to a specific class"""
    if request.method != "POST":
        return JsonResponse(
            {"success": False, "message": "Invalid request method"}, status=405
        )

    # Get user's school for multi-tenancy
    school = request.user.school

    try:
        student_ids = request.POST.getlist("student_ids")
        class_id = request.POST.get("class_id")

        if not student_ids:
            return JsonResponse(
                {"success": False, "message": "No students selected"}, status=400
            )

        if not class_id:
            return JsonResponse(
                {"success": False, "message": "No class selected"}, status=400
            )

        # Get current academic year
        current_academic_year = SchoolInformation.get_current_academic_year(
            school=school
        )
        if not current_academic_year:
            return JsonResponse(
                {"success": False, "message": "No current academic year set"},
                status=400,
            )

        # Validate class belongs to school and current academic year
        try:
            target_class = Class.objects.get(
                id=class_id, school=school, academic_year=current_academic_year
            )
        except Class.DoesNotExist:
            return JsonResponse(
                {"success": False, "message": "Invalid class selection"}, status=400
            )

        # Validate students belong to school
        students = Student.objects.filter(id__in=student_ids, school=school)
        if students.count() != len(student_ids):
            return JsonResponse(
                {
                    "success": False,
                    "message": "Some students do not belong to your school",
                },
                status=400,
            )

        success_count = 0
        error_count = 0
        errors = []

        with transaction.atomic():
            for student in students:
                try:
                    # Deactivate current assignments for this academic year
                    StudentClass.objects.filter(
                        student=student,
                        assigned_class__academic_year=current_academic_year,
                        is_active=True,
                        school=school,
                    ).update(is_active=False)

                    # Create new assignment with proper validation
                    new_assignment = StudentClass(
                        student=student,
                        assigned_class=target_class,
                        assigned_by=request.user,
                        is_active=True,
                        school=school,
                    )
                    new_assignment.clean()  # Call clean method for validation
                    new_assignment.save()

                    success_count += 1
                    logger.info(f"Assigned {student.full_name} to {target_class.name}")

                except Exception as e:
                    error_count += 1
                    error_msg = f"Failed to assign {student.full_name}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)

        if success_count > 0:
            message = f"Successfully assigned {success_count} student(s) to {target_class.name}"
            if error_count > 0:
                message += f". {error_count} assignment(s) failed."

            return JsonResponse(
                {
                    "success": True,
                    "message": message,
                    "assigned_count": success_count,
                    "error_count": error_count,
                    "errors": errors,
                }
            )
        else:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Failed to assign any students",
                    "errors": errors,
                }
            )

    except Exception as e:
        logger.error(f"Error in bulk assignment: {str(e)}")
        return JsonResponse(
            {"success": False, "message": f"An error occurred: {str(e)}"}, status=500
        )


@login_required
@user_passes_test(is_admin)
@csrf_protect
def bulk_unassign_students_from_class(request):
    """Bulk unassign students from their current classes"""
    if request.method != "POST":
        return JsonResponse(
            {"success": False, "message": "Invalid request method"}, status=405
        )

    # Get user's school for multi-tenancy
    school = request.user.school

    try:
        student_ids = request.POST.getlist("student_ids")

        if not student_ids:
            return JsonResponse(
                {"success": False, "message": "No students selected"}, status=400
            )

        # Get current academic year
        current_academic_year = SchoolInformation.get_current_academic_year(
            school=school
        )
        if not current_academic_year:
            return JsonResponse(
                {"success": False, "message": "No current academic year set"},
                status=400,
            )

        # Validate students belong to school
        students = Student.objects.filter(id__in=student_ids, school=school)
        if students.count() != len(student_ids):
            return JsonResponse(
                {
                    "success": False,
                    "message": "Some students do not belong to your school",
                },
                status=400,
            )

        success_count = 0
        error_count = 0
        errors = []

        with transaction.atomic():
            for student in students:
                try:
                    # Deactivate current assignments for this academic year
                    updated = StudentClass.objects.filter(
                        student=student,
                        assigned_class__academic_year=current_academic_year,
                        is_active=True,
                        school=school,
                    ).update(is_active=False)

                    if updated > 0:
                        success_count += 1
                        logger.info(f"Unassigned {student.full_name} from class")
                    else:
                        logger.info(
                            f"{student.full_name} was not assigned to any class"
                        )

                except Exception as e:
                    error_count += 1
                    error_msg = f"Failed to unassign {student.full_name}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)

        message = (
            f"Successfully unassigned {success_count} student(s) from their classes"
        )
        if error_count > 0:
            message += f". {error_count} unassignment(s) failed."

        return JsonResponse(
            {
                "success": True,
                "message": message,
                "unassigned_count": success_count,
                "error_count": error_count,
                "errors": errors,
            }
        )

    except Exception as e:
        logger.error(f"Error in bulk unassignment: {str(e)}")
        return JsonResponse(
            {"success": False, "message": f"An error occurred: {str(e)}"}, status=500
        )


@login_required
@user_passes_test(is_admin)
def student_enrollment(request):
    """Modern student enrollment view with step-by-step form"""
    # Get user's school for multi-tenancy
    school = request.user.school

    # Get current academic year for the school
    current_academic_year = SchoolInformation.get_current_academic_year(school=school)

    # Get available classes for the current academic year, filtered by school
    available_classes = []
    if current_academic_year:
        available_classes = Class.objects.filter(
            academic_year=current_academic_year, school=school
        )

    # Get available forms and learning areas for the school
    available_forms = Form.objects.filter(school=school).order_by("form_number")
    available_learning_areas = LearningArea.objects.filter(school=school)

    # Check if this is an AJAX request
    is_ajax = request.headers.get(
        "X-Requested-With"
    ) == "XMLHttpRequest" or request.POST.get("ajax_submit")

    if request.method == "POST":
        try:
            form = StudentForm(request.POST, request.FILES, school=school)
            if form.is_valid():
                # Create student but don't save yet
                student = form.save(commit=False)

                # Set the school for the student
                student.school = school

                # Save the student
                student.save()

                # Handle class assignment if provided
                class_id = request.POST.get("class_id")
                if class_id:
                    try:
                        assigned_class = Class.objects.get(
                            id=class_id,
                            academic_year=current_academic_year,
                            school=school,
                        )
                        StudentClass.objects.create(
                            student=student,
                            assigned_class=assigned_class,
                            assigned_by=request.user,
                            school=school,
                        )
                        logger.info(
                            f"Student {student.full_name} assigned to class {assigned_class.name}"
                        )
                    except Class.DoesNotExist:
                        logger.warning(
                            f"Class with ID {class_id} not found for assignment"
                        )

                success_message = f"Student '{student.full_name}' has been successfully enrolled with admission number {student.admission_number}."

                if is_ajax:
                    return JsonResponse(
                        {
                            "success": True,
                            "message": success_message,
                            "redirect": reverse("student_list"),
                        }
                    )
                else:
                    messages.success(request, success_message)
                    return redirect("student_list")

            else:
                # Form has validation errors
                error_message = "Please correct the errors below."
                form_errors = []
                for field, errors in form.errors.items():
                    for error in errors:
                        form_errors.append(f"{field}: {error}")

                if is_ajax:
                    return JsonResponse(
                        {
                            "success": False,
                            "message": error_message,
                            "errors": form_errors,
                        }
                    )
                else:
                    messages.error(request, error_message)

        except Exception as e:
            error_message = f"An error occurred while enrolling the student: {str(e)}"
            logger.error(f"Error in student enrollment: {str(e)}")

            if is_ajax:
                return JsonResponse({"success": False, "message": error_message})
            else:
                messages.error(request, error_message)

    else:
        form = StudentForm(school=school)

    context = {
        "form": form,
        "available_classes": available_classes,
        "available_forms": available_forms,
        "available_learning_areas": available_learning_areas,
        "school": school,
        "today": timezone.now().date(),
    }

    return render(request, "student/student_enrollment.html", context)


@login_required
@user_passes_test(is_admin)
def add_student(request):
    # Get user's school for multi-tenancy
    school = request.user.school

    # Get current academic year for the school
    current_academic_year = SchoolInformation.get_current_academic_year(school=school)

    # Get available classes for the current academic year, filtered by school
    available_classes = []
    if current_academic_year:
        available_classes = Class.objects.filter(
            academic_year=current_academic_year, school=school
        )

    # Check if this is an AJAX request
    is_ajax = request.headers.get(
        "X-Requested-With"
    ) == "XMLHttpRequest" or request.POST.get("ajax_submit")

    if request.method == "POST":
        try:
            form = StudentForm(request.POST, request.FILES, school=school)
            if form.is_valid():
                # Create student but don't save yet
                student = form.save(commit=False)
                # Set the school
                student.school = school
                # Now save the student
                student.save()

                # Check if we should assign to a class
                class_id = request.POST.get("class_id")
                if class_id:
                    try:
                        assigned_class = Class.objects.get(id=class_id, school=school)
                        # Create student class assignment
                        StudentClass.objects.create(
                            student=student,
                            assigned_class=assigned_class,
                            assigned_by=request.user,
                            school=school,
                        )
                    except Class.DoesNotExist:
                        # Log the error but continue
                        logger.error(
                            f"Failed to assign student to class: Class {class_id} not found"
                        )

                success_message = f'Student "{student.full_name}" added successfully with admission number {student.admission_number}.'

                # Check if we need to redirect to a specific class detail page
                redirect_class = request.GET.get("redirect_class")
                if redirect_class:
                    # Only add message if not an AJAX request
                    if not is_ajax:
                        messages.success(request, success_message)
                    return redirect("class_detail", class_id=redirect_class)

                # Handle AJAX requests
                if is_ajax:
                    return JsonResponse(
                        {
                            "success": True,
                            "message": success_message,
                            "redirect": reverse("student_list"),
                        }
                    )

                # Only add message if not an AJAX request
                if not is_ajax:
                    messages.success(request, success_message)

                return redirect("student_list")
            elif is_ajax:
                # Return form errors for AJAX requests
                return JsonResponse(
                    {"success": False, "errors": form.errors.as_json()}, status=400
                )
        except Exception as e:
            logger.error(f"Error adding student: {str(e)}")
            if is_ajax:
                return JsonResponse(
                    {"success": False, "message": f"Error adding student: {str(e)}"},
                    status=500,
                )
            else:
                messages.error(request, f"Error adding student: {str(e)}")
                return redirect("student_list")
    else:
        form = StudentForm(school=school)

    context = {
        "form": form,
        "title": "Add New Student",
        "available_classes": available_classes,
        "school": school,  # Add school to context
    }

    return render(request, "student/student_form.html", context)


@login_required
@user_passes_test(is_admin)
def edit_student(request, student_id):
    """Edit existing student details"""
    # Get user's school for multi-tenancy
    school = request.user.school

    # Ensure student belongs to user's school
    student = get_object_or_404(Student, id=student_id, school=school)
    is_ajax = request.headers.get(
        "X-Requested-With"
    ) == "XMLHttpRequest" or request.POST.get("ajax_submit")

    if request.method == "POST":
        form = StudentForm(request.POST, request.FILES, instance=student, school=school)
        if form.is_valid():
            # Update student but don't save yet
            updated_student = form.save(commit=False)
            # Ensure school remains the same
            updated_student.school = school
            # Now save the student
            updated_student.save()

            success_message = f'Student "{student.full_name}" updated successfully.'

            # Only add message if not an AJAX request
            if not is_ajax:
                messages.success(request, success_message)

            # Handle AJAX requests
            if is_ajax:
                return JsonResponse(
                    {
                        "success": True,
                        "message": success_message,
                        "redirect": reverse("student_list"),
                    }
                )

            return redirect("student_list")
        elif is_ajax:
            # Return form errors for AJAX requests
            return JsonResponse(
                {"success": False, "errors": form.errors.as_json()}, status=400
            )
    else:
        form = StudentForm(instance=student, school=school)

    context = {
        "form": form,
        "student": student,
        "school": school,  # Add school to context
    }

    return render(request, "student/edit_student.html", context)


@login_required
@user_passes_test(is_admin)
@csrf_protect
def delete_student(request, student_id):
    """Delete a student and their associated user account using AJAX"""
    # Get user's school for multi-tenancy
    school = request.user.school

    # Ensure student belongs to user's school
    student = get_object_or_404(Student, id=student_id, school=school)
    is_ajax = request.headers.get(
        "X-Requested-With"
    ) == "XMLHttpRequest" or request.POST.get("ajax_submit")

    if request.method == "POST":
        try:
            student_name = student.full_name
            # Delete associated user account if exists
            User.objects.filter(student_profile=student).delete()

            # Delete the student
            student.delete()

            success_message = f'Student "{student_name}" and associated user account deleted successfully.'

            # Only add message if not an AJAX request
            if not is_ajax:
                messages.success(request, success_message)

            # Handle AJAX requests
            if is_ajax:
                return JsonResponse(
                    {
                        "success": True,
                        "message": success_message,
                        "redirect": reverse("student_list"),
                    }
                )

            return redirect("student_list")
        except Exception as e:
            error_message = f"Error deleting student: {str(e)}"
            if is_ajax:
                return JsonResponse(
                    {"success": False, "message": error_message}, status=400
                )

            messages.error(request, error_message)
            return redirect("student_list")

    # For GET requests - show confirmation page
    # Since we're now handling deletion entirely through AJAX, this will rarely be used
    # but we keep it for backward compatibility
    context = {
        "student": student,
        "title": f"Delete Student: {student.full_name}",
        "school": school,  # Add school to context
    }

    return render(request, "student/delete_student.html", context)


from django.db import transaction


@login_required
@user_passes_test(is_admin)
def assign_student_class(request, student_id):
    # Get user's school for multi-tenancy
    school = request.user.school

    # Ensure student belongs to user's school
    student = get_object_or_404(Student, pk=student_id, school=school)
    redirect_class = request.GET.get("redirect_class", None)

    # Get current academic year for the school
    current_academic_year = SchoolInformation.get_current_academic_year(school=school)

    # Debug logging
    if current_academic_year:
        logger.info(
            f"Current academic year: {current_academic_year.name} (ID: {current_academic_year.id})"
        )
        class_count = Class.objects.filter(
            academic_year=current_academic_year, school=school
        ).count()
        logger.info(f"Available classes count: {class_count}")
        if class_count == 0:
            logger.warning(
                f"No classes found for the current academic year '{current_academic_year.name}' in school '{school.name}'. Please create classes for this academic year."
            )
    else:
        logger.warning(
            f"No current academic year is set for school '{school.name}'. Cannot assign students to classes."
        )
        messages.error(
            request,
            "No current academic year is set. Please set a current academic year in School Information settings before assigning classes.",
        )

        # Redirect if no current academic year
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {
                    "success": False,
                    "message": "No current academic year is set. Please set a current academic year in School Information settings.",
                },
                status=400,
            )
        else:
            return redirect("student_list")

    if request.method == "POST":
        form = StudentClassAssignmentForm(
            request.POST,
            current_academic_year=current_academic_year,
            school=school,  # Pass school to form for filtering available classes
        )
        if form.is_valid():
            # Get the target class
            assigned_class = form.cleaned_data["assigned_class"]

            # Ensure class belongs to user's school
            if assigned_class.school != school:
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse(
                        {
                            "success": False,
                            "message": "Invalid class selection. Class does not belong to your school.",
                        },
                        status=400,
                    )
                messages.error(
                    request,
                    "Invalid class selection. Class does not belong to your school.",
                )
                return redirect("student_list")

            # Use transaction for data consistency
            with transaction.atomic():
                # Deactivate current class assignment, filtered by school
                StudentClass.objects.filter(
                    student=student, is_active=True, school=school
                ).update(is_active=False)

                # Create new class assignment with proper validation
                new_assignment = StudentClass(
                    student=student,
                    assigned_class=assigned_class,
                    is_active=True,
                    assigned_by=request.user,
                    school=school,  # Set the school for multi-tenancy
                )
                new_assignment.clean()  # Call clean method for validation
                new_assignment.save()

            message = f"{student.full_name} has been assigned to {assigned_class.name}."

            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {
                        "success": True,
                        "message": message,
                        "student_id": student_id,
                        "class_id": assigned_class.class_id,
                    }
                )
            else:
                messages.success(request, message)

                # Redirect logic
                if redirect_class:
                    return redirect("class_detail", class_id=redirect_class)
                else:
                    return redirect("student_list")
        else:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {"success": False, "errors": form.errors.as_json()}, status=400
                )
    else:
        form = StudentClassAssignmentForm(
            student=student,
            current_academic_year=current_academic_year,
            school=school,  # Pass school to form for filtering available classes
        )

    # For GET requests
    context = {
        "student": student,
        "form": form,
        "title": f"Assign {student.full_name} to Class",
        "school": school,  # Add school to context
    }

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        html = render_to_string(
            "student/includes/assign_class_form.html", context, request=request
        )
        return JsonResponse({"html": html})

    return render(request, "student/assign_class_form.html", context)


@login_required
@user_passes_test(is_admin)
@csrf_protect
def assign_student_class_ajax(request, student_id):
    """AJAX endpoint for individual student class assignment"""
    if request.method != "POST":
        return JsonResponse(
            {"success": False, "message": "Invalid request method"}, status=405
        )

    # Get user's school for multi-tenancy
    school = request.user.school

    try:
        # Ensure student belongs to user's school
        student = get_object_or_404(Student, pk=student_id, school=school)

        class_id = request.POST.get("class_id")

        if not class_id:
            return JsonResponse(
                {"success": False, "message": "No class selected"}, status=400
            )

        # Get current academic year
        current_academic_year = SchoolInformation.get_current_academic_year(
            school=school
        )
        if not current_academic_year:
            return JsonResponse(
                {"success": False, "message": "No current academic year set"},
                status=400,
            )

        # Validate class belongs to school and current academic year
        try:
            target_class = Class.objects.get(
                id=class_id, school=school, academic_year=current_academic_year
            )
        except Class.DoesNotExist:
            return JsonResponse(
                {"success": False, "message": "Invalid class selection"}, status=400
            )

        with transaction.atomic():
            # Deactivate current assignments for this academic year
            StudentClass.objects.filter(
                student=student,
                assigned_class__academic_year=current_academic_year,
                is_active=True,
                school=school,
            ).update(is_active=False)

            # Create new assignment with proper validation
            new_assignment = StudentClass(
                student=student,
                assigned_class=target_class,
                assigned_by=request.user,
                is_active=True,
                school=school,
            )
            new_assignment.clean()  # Call clean method for validation
            new_assignment.save()

        message = f"{student.full_name} has been assigned to {target_class.name}."
        return JsonResponse(
            {
                "success": True,
                "message": message,
                "student_id": student_id,
                "class_name": target_class.name,
            }
        )

    except ValidationError as e:
        return JsonResponse({"success": False, "message": str(e)}, status=400)
    except Exception as e:
        logger.error(f"Error in individual assignment: {str(e)}")
        return JsonResponse(
            {"success": False, "message": f"An error occurred: {str(e)}"}, status=500
        )


@login_required
@user_passes_test(is_admin)
def student_class_history(request, student_id):
    """View student class assignment history"""
    # Get user's school for multi-tenancy
    school = request.user.school

    # Ensure student belongs to user's school
    student = get_object_or_404(Student, id=student_id, school=school)

    # Get class history and filter by school
    class_history = StudentClass.objects.filter(
        student=student, school=school
    ).order_by("-date_assigned")

    context = {
        "student": student,
        "class_history": class_history,
        "school": school,  # Add school to context
    }

    return render(request, "student/student_class_history.html", context)


@login_required
@user_passes_test(is_admin)
@csrf_protect
def bulk_delete_students(request):
    """Bulk delete selected students and their associated user accounts with batch processing"""
    # Get user's school for multi-tenancy
    school = request.user.school

    if request.method == "POST":
        try:
            # Debug logging
            logger.info(f"Bulk delete request from user: {request.user}")
            logger.info(f"Request POST data: {request.POST}")
            logger.info(f"Request POST keys: {list(request.POST.keys())}")

            # Try multiple ways to get the student IDs
            student_ids = request.POST.getlist("student_ids")
            student_ids_alt = request.POST.getlist(
                "student_ids[]"
            )  # Alternative format

            logger.info(f"Method 1 - getlist('student_ids'): {student_ids}")
            logger.info(f"Method 2 - getlist('student_ids[]'): {student_ids_alt}")

            # Use whichever method returned data
            if not student_ids and student_ids_alt:
                student_ids = student_ids_alt
                logger.info(
                    f"Using alternative method, final student_ids: {student_ids}"
                )

            if not student_ids:
                return JsonResponse(
                    {"success": False, "message": "No students selected for deletion."},
                    status=400,
                )

            # Convert string IDs to integers for better performance
            try:
                student_ids = [int(id) for id in student_ids if id.isdigit()]
            except (ValueError, TypeError):
                return JsonResponse(
                    {"success": False, "message": "Invalid student IDs provided."},
                    status=400,
                )

            # Get students belonging to user's school only
            logger.info(f"User's school: {school}")
            students = Student.objects.filter(
                id__in=student_ids, school=school
            ).select_related("school")
            student_count = students.count()
            logger.info(
                f"Found {student_count} students matching IDs {student_ids} in school {school}"
            )

            if not students.exists():
                return JsonResponse(
                    {
                        "success": False,
                        "message": "No valid students found for deletion.",
                    },
                    status=400,
                )

            deleted_count = 0
            failed_deletions = []
            batch_size = 50  # Process in batches to avoid lock timeouts

            # Process deletions in batches to prevent database lock timeouts
            student_list = list(
                students.values("id", "full_name")
            )  # Get all data at once

            for i in range(0, len(student_list), batch_size):
                batch = student_list[i : i + batch_size]
                batch_ids = [student["id"] for student in batch]

                try:
                    # Use atomic transaction for each batch
                    from django.db import transaction

                    with transaction.atomic():
                        # Delete associated user accounts in batch
                        User.objects.filter(student_profile_id__in=batch_ids).delete()

                        # Delete students in batch
                        batch_students = Student.objects.filter(
                            id__in=batch_ids, school=school
                        )
                        batch_deleted_count = batch_students.count()
                        batch_students.delete()

                        deleted_count += batch_deleted_count
                        logger.info(
                            f"Successfully deleted batch of {batch_deleted_count} students"
                        )

                except Exception as e:
                    # If batch fails, try individual deletions for this batch
                    logger.warning(
                        f"Batch deletion failed, trying individual deletions: {str(e)}"
                    )
                    for student_data in batch:
                        try:
                            with transaction.atomic():
                                student_id = student_data["id"]
                                student_name = student_data["full_name"]

                                # Delete associated user account if exists
                                User.objects.filter(
                                    student_profile_id=student_id
                                ).delete()

                                # Delete the student
                                Student.objects.filter(
                                    id=student_id, school=school
                                ).delete()
                                deleted_count += 1
                                logger.info(
                                    f"Successfully deleted student: {student_name}"
                                )

                        except Exception as individual_error:
                            failed_deletions.append(
                                f"{student_data['full_name']}: {str(individual_error)}"
                            )
                            logger.error(
                                f"Failed to delete student {student_data['full_name']}: {str(individual_error)}"
                            )

            # Prepare response message
            if deleted_count > 0:
                message = f"Successfully deleted {deleted_count} student(s)"
                if failed_deletions:
                    message += f" ({len(failed_deletions)} failed)"

                return JsonResponse(
                    {
                        "success": True,
                        "message": message,
                        "deleted_count": deleted_count,
                        "failed_count": len(failed_deletions),
                        "failed_deletions": failed_deletions[
                            :10
                        ],  # Limit error details
                    }
                )
            else:
                return JsonResponse(
                    {"success": False, "message": "Failed to delete any students."},
                    status=400,
                )

        except Exception as e:
            logger.error(f"Error in bulk delete: {str(e)}")
            return JsonResponse(
                {"success": False, "message": f"Error during bulk deletion: {str(e)}"},
                status=500,
            )

    return JsonResponse(
        {"success": False, "message": "Invalid request method."}, status=405
    )


@login_required
@user_passes_test(is_admin)
@csrf_protect
def bulk_import_preview(request):
    """Preview CSV file and allow column mapping before import"""
    # Get user's school for multi-tenancy
    school = request.user.school

    if request.method == "POST" and request.FILES.get("csv_file"):
        try:
            csv_file = request.FILES["csv_file"]

            # Validate file type
            if not csv_file.name.endswith(".csv"):
                return JsonResponse(
                    {"success": False, "message": "Please upload a CSV file."},
                    status=400,
                )

            # Read CSV file
            try:
                # Decode the file content
                file_content = csv_file.read().decode("utf-8")
                csv_reader = csv.DictReader(io.StringIO(file_content))

                # Get headers
                headers = csv_reader.fieldnames
                if not headers:
                    return JsonResponse(
                        {
                            "success": False,
                            "message": "CSV file appears to be empty or invalid.",
                        },
                        status=400,
                    )

                # Read first few rows for preview
                preview_rows = []
                all_rows = []

                for i, row in enumerate(csv_reader):
                    all_rows.append(row)
                    if i < 5:  # Preview first 5 rows
                        preview_rows.append(row)

                if not all_rows:
                    return JsonResponse(
                        {
                            "success": False,
                            "message": "CSV file contains no data rows.",
                        },
                        status=400,
                    )

                # Define available student model fields for mapping
                student_fields = {
                    "full_name": "Full Name (Required)",

                    "date_of_birth": "Date of Birth (Optional, YYYY-MM-DD, defaults to 10 years ago)",
                    "gender": "Gender (Required, M/F)",
                    "admission_date": "Admission Date (Optional, YYYY-MM-DD, defaults to today)",
                    "parent_contact": "Parent Contact (Optional, defaults to 'Not provided')",

                    "email": "Email (Optional)",
                    "form": "Form Number (Optional)",
                    "learning_area": "Learning Area Name (Optional)",
                }

                # Auto-suggest column mappings based on header names
                suggested_mappings = {}
                for header in headers:
                    header_lower = header.lower().replace(" ", "_").replace("-", "_")

                    # Direct matches
                    if header_lower in student_fields:
                        suggested_mappings[header] = header_lower
                    # Fuzzy matching
                    elif "name" in header_lower and "full" in header_lower:
                        suggested_mappings[header] = "full_name"
                    elif "name" in header_lower and header_lower not in [
                        "parent_name",
                        "guardian_name",
                    ]:
                        suggested_mappings[header] = "full_name"
                    elif "birth" in header_lower or "dob" in header_lower:
                        suggested_mappings[header] = "date_of_birth"
                    elif "gender" in header_lower or "sex" in header_lower:
                        suggested_mappings[header] = "gender"
                    elif "admission" in header_lower and "date" in header_lower:
                        suggested_mappings[header] = "admission_date"
                    elif "parent" in header_lower and (
                        "contact" in header_lower or "phone" in header_lower
                    ):
                        suggested_mappings[header] = "parent_contact"
                    elif "email" in header_lower or "mail" in header_lower:
                        suggested_mappings[header] = "email"
                    elif "form" in header_lower and "class" not in header_lower:
                        suggested_mappings[header] = "form"
                    elif "learning" in header_lower and "area" in header_lower:
                        suggested_mappings[header] = "learning_area"

                # Get available forms and learning areas for validation
                available_forms = list(
                    Form.objects.filter(school=school).values_list(
                        "form_number", flat=True
                    )
                )
                available_learning_areas = list(
                    LearningArea.objects.filter(school=school).values_list(
                        "name", flat=True
                    )
                )

                # Store data for later import
                import_data = {
                    "rows": all_rows,
                    "headers": headers,
                    "total_rows": len(all_rows),
                    "available_forms": available_forms,
                    "available_learning_areas": available_learning_areas,
                }

                # Generate preview HTML
                preview_html = render_to_string(
                    "student/bulk_import_preview.html",
                    {
                        "headers": headers,
                        "preview_rows": preview_rows,
                        "student_fields": student_fields,
                        "suggested_mappings": suggested_mappings,
                        "total_rows": len(all_rows),
                        "school": school,
                    },
                    request=request,
                )

                return JsonResponse(
                    {
                        "success": True,
                        "preview_html": preview_html,
                        "import_data": import_data,
                        "total_rows": len(all_rows),
                    }
                )

            except UnicodeDecodeError:
                return JsonResponse(
                    {
                        "success": False,
                        "message": "Unable to read CSV file. Please ensure it's properly encoded (UTF-8).",
                    },
                    status=400,
                )
            except csv.Error as e:
                return JsonResponse(
                    {"success": False, "message": f"Error reading CSV file: {str(e)}"},
                    status=400,
                )

        except Exception as e:
            logger.error(f"Error in bulk import preview: {str(e)}")
            return JsonResponse(
                {"success": False, "message": f"Error processing file: {str(e)}"},
                status=500,
            )

    return JsonResponse(
        {"success": False, "message": "No file uploaded or invalid request."},
        status=400,
    )


@login_required
@user_passes_test(is_admin)
@csrf_protect
def bulk_import_students(request):
    """Import students from CSV data with column mappings using batch processing"""
    # Get user's school for multi-tenancy
    school = request.user.school

    if request.method == "POST":
        try:
            # Get import data and mappings
            import_data = json.loads(request.POST.get("import_data", "{}"))
            column_mappings = json.loads(request.POST.get("column_mappings", "{}"))
            assign_class_id = request.POST.get("assign_class", "")

            # Debug logging
            logger.info(f"Column mappings: {column_mappings}")
            logger.info(f"Assign class ID: {assign_class_id}")
            logger.info(f"Total rows to import: {len(import_data.get('rows', []))}")

            if not import_data or not import_data.get("rows"):
                return JsonResponse(
                    {"success": False, "message": "No import data available."},
                    status=400,
                )


            # Validate required mappings - only full_name and gender are truly required
            required_fields = ["full_name", "gender"]

            mapped_fields = set(column_mappings.values())
            missing_required = [
                field for field in required_fields if field not in mapped_fields
            ]

            if missing_required:
                return JsonResponse(
                    {
                        "success": False,
                        "message": f"Missing required field mappings: {', '.join(missing_required)}",
                    },
                    status=400,
                )

            # Get class for assignment if provided
            assign_class = None
            if assign_class_id:
                try:
                    assign_class = Class.objects.get(id=assign_class_id, school=school)
                except Class.DoesNotExist:
                    return JsonResponse(
                        {"success": False, "message": "Selected class not found."},
                        status=400,
                    )

            # Get available forms and learning areas for validation
            forms_by_number = {
                form.form_number: form for form in Form.objects.filter(school=school)
            }
            learning_areas_by_name = {
                area.name.lower(): area
                for area in LearningArea.objects.filter(school=school)
            }

            imported_count = 0
            failed_count = 0
            errors = []
            batch_size = 100  # Process in smaller batches to avoid database locks

            # Process rows in batches
            rows = import_data["rows"]
            total_rows = len(rows)

            for batch_start in range(0, total_rows, batch_size):
                batch_end = min(batch_start + batch_size, total_rows)
                batch_rows = rows[batch_start:batch_end]

                # Prepare batch data
                students_to_create = []
                student_classes_to_create = []

                # Process each row in the batch
                for row_index, row in enumerate(batch_rows, start=batch_start + 1):
                    try:
                        # Extract data based on column mappings
                        student_data = {}

                        for csv_column, model_field in column_mappings.items():
                            # Only process if the mapping is not empty and the CSV column actually exists in the row
                            if model_field and csv_column in row:
                                value = (
                                    str(row[csv_column]).strip()
                                    if row[csv_column]
                                    else ""
                                )

                                # Skip empty values for optional fields
                                if not value and model_field not in required_fields:
                                    continue

                                if (
                                    model_field == "date_of_birth"
                                    or model_field == "admission_date"
                                ):
                                    # Parse date
                                    try:
                                        # Try multiple date formats
                                        for date_format in [
                                            "%Y-%m-%d",
                                            "%m/%d/%Y",
                                            "%d/%m/%Y",
                                            "%Y/%m/%d",
                                        ]:
                                            try:
                                                parsed_date = dt.strptime(
                                                    value, date_format
                                                ).date()
                                                student_data[model_field] = parsed_date
                                                break
                                            except ValueError:
                                                continue
                                        else:
                                            raise ValueError(
                                                f"Invalid date format: {value}"
                                            )
                                    except ValueError as e:
                                        raise ValueError(f"{model_field}: {str(e)}")

                                elif model_field == "gender":
                                    # Validate gender
                                    gender = value.upper()
                                    if gender not in ["M", "F", "MALE", "FEMALE"]:
                                        raise ValueError(
                                            f"Invalid gender: {value}. Use M/F or Male/Female"
                                        )
                                    student_data[model_field] = (
                                        "M" if gender in ["M", "MALE"] else "F"
                                    )

                                elif model_field == "form":
                                    # Look up form by number
                                    try:
                                        form_number = int(value)
                                        if form_number not in forms_by_number:
                                            raise ValueError(
                                                f"Form {form_number} not found"
                                            )
                                        student_data["form"] = forms_by_number[
                                            form_number
                                        ]
                                    except (ValueError, TypeError):
                                        raise ValueError(
                                            f"Invalid form number: {value}"
                                        )

                                elif model_field == "learning_area":
                                    # Look up learning area by name
                                    area_name = value.lower()
                                    if area_name not in learning_areas_by_name:
                                        raise ValueError(
                                            f"Learning area '{value}' not found"
                                        )
                                    student_data["learning_area"] = (
                                        learning_areas_by_name[area_name]
                                    )

                                else:
                                    # Regular field
                                    student_data[model_field] = value

                        # Check required fields
                        for field in required_fields:
                            if field not in student_data or not student_data[field]:
                                raise ValueError(
                                    f"Missing required field: {field}. Please ensure this field is mapped and has a value."
                                )


                        # Set default values for optional fields if not provided
                        from datetime import date
                        today = date.today()
                        
                        # Default date_of_birth to 10 years ago if not provided
                        if "date_of_birth" not in student_data or not student_data["date_of_birth"]:
                            student_data["date_of_birth"] = date(today.year - 10, 1, 1)
                        
                        # Default admission_date to today if not provided
                        if "admission_date" not in student_data or not student_data["admission_date"]:
                            student_data["admission_date"] = today
                        
                        # Default parent_contact to "Not provided" if not provided
                        if "parent_contact" not in student_data or not student_data["parent_contact"]:
                            student_data["parent_contact"] = "Not provided"


                        # Create student object (but don't save yet)
                        student = Student(
                            full_name=student_data["full_name"],
                            date_of_birth=student_data["date_of_birth"],
                            gender=student_data["gender"],
                            admission_date=student_data["admission_date"],
                            parent_contact=student_data.get("parent_contact", ""),
                            email=student_data.get("email", ""),
                            school=school,
                        )

                        # Set form and learning area if provided
                        if "form" in student_data:
                            student.form = student_data["form"]
                        if "learning_area" in student_data:
                            student.learning_area = student_data["learning_area"]

                        # Mark to skip email sending during bulk import (but keep user creation)
                        student._skip_email = True

                        # Validate the student data
                        student.full_clean()

                        # Add to batch for creation
                        students_to_create.append(student)

                    except Exception as e:
                        failed_count += 1
                        error_msg = f"Row {row_index}: {str(e)}"
                        errors.append(error_msg)
                        logger.error(
                            f"Failed to process student from row {row_index}: {str(e)}"
                        )

                # Bulk create students in this batch using transaction
                if students_to_create:
                    try:
                        from django.db import transaction

                        with transaction.atomic():
                            # Use bulk_create for better performance
                            created_students = Student.objects.bulk_create(
                                students_to_create,
                                batch_size=50,  # MySQL bulk insert batch size
                                ignore_conflicts=False,
                            )

                            batch_imported_count = len(created_students)
                            imported_count += batch_imported_count

                            # Create class assignments if needed
                            if assign_class and created_students:
                                # Get the created students with their IDs
                                # Since bulk_create doesn't return IDs in older Django versions,
                                # we need to fetch them
                                student_names = [
                                    s.full_name for s in students_to_create
                                ]
                                created_student_objects = Student.objects.filter(
                                    full_name__in=student_names, school=school
                                ).order_by("-id")[:batch_imported_count]

                                student_class_assignments = [
                                    StudentClass(
                                        student=student,
                                        assigned_class=assign_class,
                                        assigned_by=request.user,
                                        school=school,
                                    )
                                    for student in created_student_objects
                                ]

                                StudentClass.objects.bulk_create(
                                    student_class_assignments,
                                    batch_size=50,
                                    ignore_conflicts=True,
                                )

                            logger.info(
                                f"Successfully imported batch of {batch_imported_count} students"
                            )

                    except Exception as batch_error:
                        # If batch creation fails, try individual creation for this batch
                        logger.warning(
                            f"Batch creation failed, trying individual creation: {str(batch_error)}"
                        )
                        for student in students_to_create:
                            try:
                                with transaction.atomic():
                                    # Ensure email skipping flag is set for individual saves too
                                    student._skip_email = True
                                    student.save()

                                    # Assign to class if specified
                                    if assign_class:
                                        StudentClass.objects.create(
                                            student=student,
                                            assigned_class=assign_class,
                                            assigned_by=request.user,
                                            school=school,
                                        )

                                    imported_count += 1
                                    logger.info(
                                        f"Successfully imported student: {student.full_name}"
                                    )

                            except Exception as individual_error:
                                failed_count += 1
                                error_msg = f"Student {student.full_name}: {str(individual_error)}"
                                errors.append(error_msg)
                                logger.error(
                                    f"Failed to import student {student.full_name}: {str(individual_error)}"
                                )

            # Prepare response
            if imported_count > 0:
                message = f"Successfully imported {imported_count} students"
                if failed_count > 0:
                    message += f" ({failed_count} failed)"

                return JsonResponse(
                    {
                        "success": True,
                        "message": message,
                        "imported_count": imported_count,
                        "failed_count": failed_count,
                        "errors": errors[:20],  # Return first 20 errors
                    }
                )
            else:
                return JsonResponse(
                    {
                        "success": False,
                        "message": f"Failed to import any students. {failed_count} errors occurred.",
                        "errors": errors[:20],
                    },
                    status=400,
                )

        except Exception as e:
            logger.error(f"Error in bulk import: {str(e)}")
            return JsonResponse(
                {"success": False, "message": f"Error during import: {str(e)}"},
                status=500,
            )

    return JsonResponse(
        {"success": False, "message": "Invalid request method."}, status=405
    )


@login_required
@user_passes_test(is_admin)

def download_student_csv_template(request):
    """Download CSV template for bulk student import"""
    # Get user's school for multi-tenancy
    school = request.user.school
    
    # Create response with CSV content type
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="student_import_template.csv"'
    
    # Create CSV writer
    writer = csv.writer(response)
    
    # Define the CSV headers based on student model fields
    headers = [
        'full_name',
        'gender',
        'date_of_birth', 
        'admission_date',
        'parent_contact',
        'email'
    ]
    
    # Write headers
    writer.writerow(headers)
    
    # Write sample data rows with examples
    sample_rows = [
        [
            'John Doe',
            'M',
            '2010-05-15',
            '2024-01-15',
            '+1234567890',
            'john.doe@example.com'
        ],
        [
            'Jane Smith',
            'F',
            '',
            '',
            '',
            'jane.smith@example.com'
        ],
        [
            'Mike Johnson',
            'M',
            '2009-12-03',
            '',
            '',
            ''
        ]
    ]
    
    # Write sample rows
    for row in sample_rows:
        writer.writerow(row)
    
    return response


@login_required
@user_passes_test(is_admin)

@csrf_protect
def bulk_operation_progress(request):
    """Track progress of bulk operations using session storage"""
    if request.method == "GET":
        operation_id = request.GET.get("operation_id")
        if not operation_id:
            return JsonResponse({"error": "Operation ID required"}, status=400)

        # Get progress from session
        progress_key = f"bulk_operation_{operation_id}"
        progress_data = request.session.get(
            progress_key,
            {
                "status": "not_found",
                "message": "Operation not found",
                "progress": 0,
                "total": 0,
                "current_item": "",
                "errors": [],
            },
        )

        return JsonResponse(progress_data)

    return JsonResponse({"error": "Invalid request method"}, status=405)


@login_required
@user_passes_test(is_admin)
@csrf_protect
def bulk_upload_student_images(request):
    """
    Handle bulk upload of student images with intelligent matching
    """
    if request.method != "POST":
        return JsonResponse(
            {"success": False, "message": "Invalid request method"}, status=405
        )

    # Get user's school for multi-tenancy
    school = request.user.school

    try:
        # Get uploaded files
        uploaded_files = request.FILES.getlist("images")

        if not uploaded_files:
            return JsonResponse(
                {"success": False, "message": "No images uploaded"}, status=400
            )

        # Validate file count (max 100 images per batch)
        if len(uploaded_files) > 100:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Too many images. Maximum 100 images per batch.",
                },
                status=400,
            )

        # Get all students for matching
        students = Student.objects.filter(school=school).select_related(
            "form", "learning_area"
        )

        # Create a mapping of students by different identifiers
        student_mapping = create_student_mapping(students)

        # Process uploaded images
        uploaded_file_data = []
        matches = {"matched": [], "unmatched": []}

        for uploaded_file in uploaded_files:
            # Validate file
            if not is_valid_image(uploaded_file):
                matches["unmatched"].append(
                    {"name": uploaded_file.name, "reason": "Invalid image format"}
                )
                continue

            # Save file temporarily
            file_path = save_temp_image(uploaded_file, school)
            if not file_path:
                matches["unmatched"].append(
                    {"name": uploaded_file.name, "reason": "Failed to save file"}
                )
                continue

            # Try to match with student
            student = match_student_to_image(uploaded_file.name, student_mapping)

            if student:
                matches["matched"].append(
                    {
                        "student": {
                            "id": student.id,
                            "full_name": student.full_name,
                            "admission_number": student.admission_number,
                            "current_class": get_student_current_class(student),
                        },
                        "image_url": file_path,
                        "filename": uploaded_file.name,
                    }
                )
                uploaded_file_data.append(
                    {
                        "student_id": student.id,
                        "file_path": file_path,
                        "filename": uploaded_file.name,
                    }
                )
            else:
                matches["unmatched"].append(
                    {
                        "name": uploaded_file.name,
                        "url": file_path,
                        "reason": "No matching student found",
                    }
                )

        return JsonResponse(
            {
                "success": True,
                "message": f"Processed {len(uploaded_files)} images",
                "matches": matches,
                "uploaded_files": uploaded_file_data,
            }
        )

    except Exception as e:
        logger.error(f"Bulk image upload error: {str(e)}")
        return JsonResponse(
            {"success": False, "message": f"Error processing images: {str(e)}"},
            status=500,
        )


@login_required
@user_passes_test(is_admin)
@csrf_protect
def apply_bulk_student_images(request):
    """
    Apply uploaded images to student profiles
    """
    if request.method != "POST":
        return JsonResponse(
            {"success": False, "message": "Invalid request method"}, status=405
        )

    # Get user's school for multi-tenancy
    school = request.user.school

    try:
        uploaded_files_data = json.loads(request.POST.get("uploaded_files", "[]"))

        if not uploaded_files_data:
            return JsonResponse(
                {"success": False, "message": "No uploaded files data"}, status=400
            )

        updated_count = 0
        errors = []

        for file_data in uploaded_files_data:
            try:
                student_id = file_data.get("student_id")
                file_path = file_data.get("file_path")

                if not student_id or not file_path:
                    continue

                # Get student
                student = Student.objects.get(id=student_id, school=school)

                # Move temp file to permanent location
                permanent_path = move_temp_to_permanent(file_path, student)

                if permanent_path:
                    # Update student profile picture
                    student.profile_picture = permanent_path
                    student.save()
                    updated_count += 1
                else:
                    errors.append(f"Failed to save image for {student.full_name}")

            except Student.DoesNotExist:
                errors.append(f"Student with ID {student_id} not found")
            except Exception as e:
                errors.append(
                    f"Error updating {file_data.get('filename', 'unknown')}: {str(e)}"
                )

        return JsonResponse(
            {
                "success": True,
                "message": f"Updated {updated_count} student profile pictures",
                "updated_count": updated_count,
                "errors": errors,
            }
        )

    except Exception as e:
        logger.error(f"Apply bulk images error: {str(e)}")
        return JsonResponse(
            {"success": False, "message": f"Error applying images: {str(e)}"},
            status=500,
        )


def create_student_mapping(students):
    """
    Create multiple mappings for student matching
    """
    mapping = {
        "by_admission_number": {},
        "by_full_name": {},
        "by_id": {},
        "by_name_variations": {},
    }

    for student in students:
        # Map by admission number
        mapping["by_admission_number"][student.admission_number.lower()] = student

        # Map by full name (normalized)
        normalized_name = normalize_name(student.full_name)
        mapping["by_full_name"][normalized_name] = student

        # Map by ID
        mapping["by_id"][str(student.id)] = student

        # Create name variations
        name_parts = student.full_name.lower().split()
        for part in name_parts:
            if len(part) > 2:  # Skip very short parts
                mapping["by_name_variations"][part] = student

    return mapping


def normalize_name(name):
    """
    Normalize name for matching (remove spaces, special chars, convert to lowercase)
    """
    # Remove special characters and extra spaces
    normalized = re.sub(r"[^\w\s]", "", name.lower())
    normalized = re.sub(r"\s+", "_", normalized.strip())
    return normalized


def match_student_to_image(filename, student_mapping):
    """
    Try to match an image filename to a student using various strategies
    """
    # Remove file extension
    name_without_ext = os.path.splitext(filename)[0].lower()

    # Strategy 1: Direct admission number match
    if name_without_ext in student_mapping["by_admission_number"]:
        return student_mapping["by_admission_number"][name_without_ext]

    # Strategy 2: Direct ID match
    if name_without_ext in student_mapping["by_id"]:
        return student_mapping["by_id"][name_without_ext]

    # Strategy 3: Normalized name match
    normalized_name = normalize_name(name_without_ext)
    if normalized_name in student_mapping["by_full_name"]:
        return student_mapping["by_full_name"][normalized_name]

    # Strategy 4: Partial name match
    for name_part in name_without_ext.split("_"):
        if name_part in student_mapping["by_name_variations"]:
            return student_mapping["by_name_variations"][name_part]

    # Strategy 5: Try without underscores/spaces
    name_no_separators = (
        name_without_ext.replace("_", "").replace("-", "").replace(" ", "")
    )
    for student in student_mapping["by_full_name"].values():
        student_name_normalized = normalize_name(student.full_name).replace("_", "")
        if name_no_separators == student_name_normalized:
            return student

    return None


def is_valid_image(file):
    """
    Validate if uploaded file is a valid image
    """
    try:
        # Check file size (max 5MB)
        if file.size > 5 * 1024 * 1024:
            return False

        # Check file extension
        allowed_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
        file_ext = os.path.splitext(file.name)[1].lower()
        if file_ext not in allowed_extensions:
            return False

        # Try to open with PIL to validate image
        file.seek(0)
        with Image.open(file) as img:
            img.verify()
        file.seek(0)  # Reset file pointer

        return True
    except Exception:
        return False


def save_temp_image(uploaded_file, school):
    """
    Save uploaded image to temporary location
    """
    try:
        # Create temp directory path
        temp_dir = f"temp_images/{school.id}/{timezone.now().strftime('%Y%m%d_%H%M%S')}"

        # Generate unique filename
        file_ext = os.path.splitext(uploaded_file.name)[1]
        temp_filename = (
            f"{uploaded_file.name}_{timezone.now().strftime('%H%M%S')}{file_ext}"
        )
        temp_path = os.path.join(temp_dir, temp_filename)

        # Save file
        saved_path = default_storage.save(temp_path, uploaded_file)

        return saved_path
    except Exception as e:
        logger.error(f"Error saving temp image: {str(e)}")
        return None


def move_temp_to_permanent(temp_path, student):
    """
    Move temporary image to permanent student profile picture location
    """
    try:
        # Generate permanent path
        file_ext = os.path.splitext(temp_path)[1]
        permanent_filename = (
            f"student_{student.id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}{file_ext}"
        )
        permanent_path = f"profile_pictures/students/{permanent_filename}"

        # Read temp file
        if default_storage.exists(temp_path):
            with default_storage.open(temp_path, "rb") as temp_file:
                file_content = temp_file.read()

            # Save to permanent location
            saved_path = default_storage.save(permanent_path, ContentFile(file_content))

            # Delete temp file
            default_storage.delete(temp_path)

            return saved_path

        return None
    except Exception as e:
        logger.error(f"Error moving temp to permanent: {str(e)}")
        return None


def get_student_current_class(student):
    """
    Get student's current class name
    """
    try:
        current_academic_year = SchoolInformation.get_current_academic_year(
            school=student.school
        )
        if current_academic_year:
            student_class = (
                StudentClass.objects.filter(
                    student=student, academic_year=current_academic_year
                )
                .select_related("assigned_class")
                .first()
            )

            if student_class and student_class.assigned_class:
                return student_class.assigned_class.name
    except Exception:
        pass

    return None



@login_required
@user_passes_test(is_admin)
@csrf_protect
def quick_upload_student_image(request, student_id):
    """
    AJAX endpoint for quick individual student image upload
    """
    if request.method != "POST":
        return JsonResponse(
            {"success": False, "message": "Invalid request method"}, status=405
        )

    # Get user's school for multi-tenancy
    school = request.user.school

    try:
        # Ensure student belongs to user's school
        student = get_object_or_404(Student, id=student_id, school=school)

        # Get uploaded file
        uploaded_file = request.FILES.get("image")
        if not uploaded_file:
            return JsonResponse(
                {"success": False, "message": "No image uploaded"}, status=400
            )

        # Validate file
        if not is_valid_image(uploaded_file):
            return JsonResponse(
                {"success": False, "message": "Invalid image format. Please upload a valid image file (JPG, PNG, GIF, WebP) under 5MB."}, 
                status=400
            )

        # Save file to permanent location
        permanent_path = save_student_profile_image(uploaded_file, student)
        
        if permanent_path:
            # Update student profile picture
            student.profile_picture = permanent_path
            student.save()

            return JsonResponse(
                {
                    "success": True,
                    "message": f"Profile picture updated successfully for {student.full_name}",
                    "image_url": student.profile_picture.url,
                    "student_id": student.id,
                    "student_name": student.full_name,
                }
            )
        else:
            return JsonResponse(
                {"success": False, "message": "Failed to save image"}, status=500
            )

    except Student.DoesNotExist:
        return JsonResponse(
            {"success": False, "message": "Student not found"}, status=404
        )
    except Exception as e:
        logger.error(f"Quick image upload error: {str(e)}")
        return JsonResponse(
            {"success": False, "message": f"Error uploading image: {str(e)}"}, 
            status=500
        )


def save_student_profile_image(uploaded_file, student):
    """
    Save uploaded image directly to student profile picture location
    """
    try:
        # Generate permanent path
        file_ext = os.path.splitext(uploaded_file.name)[1]
        permanent_filename = (
            f"student_{student.id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}{file_ext}"
        )
        permanent_path = f"profile_pictures/students/{permanent_filename}"

        # Save file directly to permanent location
        saved_path = default_storage.save(permanent_path, uploaded_file)
        
        return saved_path
    except Exception as e:
        logger.error(f"Error saving student profile image: {str(e)}")
        return None

