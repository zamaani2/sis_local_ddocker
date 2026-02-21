"""
Comprehensive Student Class Assignment Views
Provides modern, feature-rich functionality for managing student class assignments
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.db.models import Q, Count, Case, When, IntegerField
from django.core.paginator import Paginator
from django.utils.decorators import method_decorator
from django.views.generic import View
from django.urls import reverse
from django.utils import timezone
import json
import logging

from ..models import (
    Student,
    Class,
    StudentClass,
    Form,
    LearningArea,
    AcademicYear,
    SchoolInformation,
    User,
)
from ..forms import StudentClassAssignmentForm, BulkStudentClassAssignmentForm
from .auth import is_admin

logger = logging.getLogger(__name__)


@login_required
@user_passes_test(is_admin)
def student_class_assignment_dashboard(request):
    """
    Main dashboard for student class assignment management
    """
    school = request.user.school
    current_academic_year = SchoolInformation.get_current_academic_year(school=school)

    if not current_academic_year:
        messages.error(
            request,
            "No current academic year is set. Please set one before managing class assignments.",
        )
        return redirect("admin_dashboard")

    # Get statistics - exclude graduated students
    total_students = (
        Student.objects.filter(school=school)
        .exclude(archivedstudent__isnull=False)
        .count()
    )

    # Count students assigned in current academic year
    assigned_students = (
        StudentClass.objects.filter(
            assigned_class__academic_year=current_academic_year,
            is_active=True,
            school=school,
        )
        .values("student")
        .distinct()
        .count()
    )

    # Count students with any active assignment (any academic year)
    students_with_any_assignment = (
        StudentClass.objects.filter(
            is_active=True,
            school=school,
        )
        .values("student")
        .distinct()
        .count()
    )

    # Count truly unassigned students (no active assignment anywhere)
    unassigned_students = total_students - students_with_any_assignment

    # Count students assigned in other academic years
    assigned_other_year = students_with_any_assignment - assigned_students

    # Get class statistics
    classes = (
        Class.objects.filter(academic_year=current_academic_year, school=school)
        .annotate(
            student_count=Count("studentclass", filter=Q(studentclass__is_active=True))
        )
        .order_by("name")
    )


    # Get form and learning area statistics - count students assigned to classes in current academic year
    form_stats = (
        Form.objects.filter(school=school)
        .annotate(
            student_count=Count(
                "class__studentclass",
                filter=Q(
                    class__studentclass__is_active=True,
                    class__academic_year=current_academic_year,
                    class__studentclass__school=school,
                )
            )
        )

        .order_by("form_number")
    )

    learning_area_stats = (
        LearningArea.objects.filter(school=school)

        .annotate(
            student_count=Count(
                "class__studentclass",
                filter=Q(
                    class__studentclass__is_active=True,
                    class__academic_year=current_academic_year,
                    class__studentclass__school=school,
                )
            )
        )

        .order_by("name")
    )

    context = {
        "current_academic_year": current_academic_year,
        "total_students": total_students,
        "assigned_students": assigned_students,
        "unassigned_students": unassigned_students,
        "assigned_other_year": assigned_other_year,
        "classes": classes,
        "form_stats": form_stats,
        "learning_area_stats": learning_area_stats,
    }

    return render(request, "student/class_assignment/dashboard.html", context)


@login_required
@user_passes_test(is_admin)
def student_class_assignment_list(request):
    """
    Advanced student class assignment list with filtering and search
    """
    school = request.user.school
    current_academic_year = SchoolInformation.get_current_academic_year(school=school)

    if not current_academic_year:
        messages.error(
            request,
            "No current academic year is set. Please set one before managing class assignments.",
        )
        return redirect("admin_dashboard")

    # Base queryset - exclude graduated students
    students_query = (
        Student.objects.filter(school=school)
        .exclude(archivedstudent__isnull=False)  # Exclude graduated students
        .select_related("form", "learning_area")
        .prefetch_related("studentclass_set")
    )

    # Apply filters
    search_query = request.GET.get("search", "")
    form_filter = request.GET.get("form", "")
    learning_area_filter = request.GET.get("learning_area", "")
    gender_filter = request.GET.get("gender", "")
    status_filter = request.GET.get("status", "")
    class_filter = request.GET.get("class", "")
    assignment_date_from = request.GET.get("assignment_date_from", "")
    assignment_date_to = request.GET.get("assignment_date_to", "")

    # Search functionality
    if search_query:
        students_query = students_query.filter(
            Q(full_name__icontains=search_query)
            | Q(admission_number__icontains=search_query)
            | Q(parent_contact__icontains=search_query)
            | Q(email__icontains=search_query)
        )

    # Form filter
    if form_filter:
        students_query = students_query.filter(form_id=form_filter)

    # Learning area filter
    if learning_area_filter:
        students_query = students_query.filter(learning_area_id=learning_area_filter)

    # Gender filter
    if gender_filter:
        students_query = students_query.filter(gender=gender_filter)

    # Status filter - Note: This will be applied after we add assignment status
    # We'll handle this in the post-processing step

    # Class filter
    if class_filter:
        if class_filter == "unassigned":
            students_query = students_query.exclude(
                studentclass__assigned_class__academic_year=current_academic_year,
                studentclass__is_active=True,
            )
        else:
            students_query = students_query.filter(
                studentclass__assigned_class_id=class_filter,
                studentclass__is_active=True,
            )

    # Assignment date filters
    if assignment_date_from:
        students_query = students_query.filter(
            studentclass__date_assigned__gte=assignment_date_from,
            studentclass__is_active=True,
        )
    if assignment_date_to:
        students_query = students_query.filter(
            studentclass__date_assigned__lte=assignment_date_to,
            studentclass__is_active=True,
        )

    # Get distinct students and add current class information
    students = students_query.distinct()

    # Add current class assignment information
    for student in students:
        # Check for assignment in current academic year
        current_assignment = (
            StudentClass.objects.filter(
                student=student,
                assigned_class__academic_year=current_academic_year,
                is_active=True,
                school=school,
            )
            .select_related(
                "assigned_class",
                "assigned_class__form",
                "assigned_class__learning_area",
            )
            .first()
        )

        # Check for any active assignment in any academic year
        any_active_assignment = (
            StudentClass.objects.filter(
                student=student,
                is_active=True,
                school=school,
            )
            .select_related(
                "assigned_class",
                "assigned_class__academic_year",
                "assigned_class__form",
                "assigned_class__learning_area",
            )
            .first()
        )

        student.current_class_assignment = (
            current_assignment.assigned_class if current_assignment else None
        )
        student.assignment_date = (
            current_assignment.date_assigned if current_assignment else None
        )
        student.assigned_by = (
            current_assignment.assigned_by if current_assignment else None
        )

        # Add information about active assignment in other academic years
        if not current_assignment and any_active_assignment:
            student.other_academic_year_assignment = any_active_assignment
            student.assignment_status = "assigned_other_year"
        elif current_assignment:
            student.assignment_status = "assigned_current_year"
        else:
            student.assignment_status = "unassigned"

    # Apply status filter after determining assignment status
    if status_filter == "assigned":
        students = [
            s for s in students if s.assignment_status == "assigned_current_year"
        ]
    elif status_filter == "unassigned":
        students = [s for s in students if s.assignment_status == "unassigned"]

    # Pagination
    paginator = Paginator(students, 25)
    page_number = request.GET.get("page")
    students_page = paginator.get_page(page_number)

    # Get filter options
    available_forms = Form.objects.filter(school=school).order_by("form_number")
    available_learning_areas = LearningArea.objects.filter(school=school).order_by(
        "name"
    )
    available_classes = Class.objects.filter(
        academic_year=current_academic_year, school=school
    ).order_by("name")

    context = {
        "students": students_page,
        "current_academic_year": current_academic_year,
        "available_forms": available_forms,
        "available_learning_areas": available_learning_areas,
        "available_classes": available_classes,
        "filters": {
            "search": search_query,
            "form": form_filter,
            "learning_area": learning_area_filter,
            "gender": gender_filter,
            "status": status_filter,
            "class": class_filter,
            "assignment_date_from": assignment_date_from,
            "assignment_date_to": assignment_date_to,
        },
    }

    return render(request, "student/class_assignment/list.html", context)


@login_required
@user_passes_test(is_admin)
def assign_student_class(request, student_id):
    """
    Assign a single student to a class
    """
    school = request.user.school
    student = get_object_or_404(Student, pk=student_id, school=school)
    current_academic_year = SchoolInformation.get_current_academic_year(school=school)

    if not current_academic_year:
        return JsonResponse(
            {"success": False, "message": "No current academic year is set."},
            status=400,
        )

    if request.method == "POST":
        form = StudentClassAssignmentForm(
            request.POST, current_academic_year=current_academic_year, school=school
        )

        if form.is_valid():
            assigned_class = form.cleaned_data["assigned_class"]

            try:
                with transaction.atomic():
                    # Check if student has any assignment to the same class (active or inactive)
                    existing_assignment = StudentClass.objects.filter(
                        student=student,
                        assigned_class=assigned_class,
                        school=school,
                    ).first()

                    if existing_assignment:
                        if existing_assignment.is_active:
                            # Student is already actively assigned to this class
                            if (
                                request.headers.get("X-Requested-With")
                                == "XMLHttpRequest"
                            ):
                                return JsonResponse(
                                    {
                                        "success": True,
                                        "message": f"{student.full_name} is already assigned to {assigned_class.name}.",
                                        "student_id": student.id,
                                        "class_name": assigned_class.name,
                                        "class_id": assigned_class.id,
                                    }
                                )
                            else:
                                messages.info(
                                    request,
                                    f"{student.full_name} is already assigned to {assigned_class.name}.",
                                )
                                return redirect("student_class_assignment_list")
                        else:
                            # Student has an inactive assignment to this class - reactivate it
                            # First deactivate any current active assignment
                            StudentClass.objects.filter(
                                student=student, is_active=True, school=school
                            ).update(is_active=False)

                            # Reactivate the existing assignment
                            existing_assignment.is_active = True
                            existing_assignment.assigned_by = request.user
                            existing_assignment.date_assigned = timezone.now().date()
                            existing_assignment.save()

                            action_message = f"{student.full_name} has been reassigned to {assigned_class.name}."
                    else:
                        # No previous assignment to this class - create new one
                        # Deactivate current assignment (if any)
                        StudentClass.objects.filter(
                            student=student, is_active=True, school=school
                        ).update(is_active=False)

                        # Create new assignment
                        new_assignment = StudentClass(
                            student=student,
                            assigned_class=assigned_class,
                            is_active=True,
                            assigned_by=request.user,
                            school=school,
                        )
                        new_assignment.clean()
                        new_assignment.save()

                        action_message = f"{student.full_name} has been assigned to {assigned_class.name}."

                    # Success response for both new assignment and reactivation
                    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                        return JsonResponse(
                            {
                                "success": True,
                                "message": action_message,
                                "student_id": student.id,
                                "class_name": assigned_class.name,
                                "class_id": assigned_class.id,
                            }
                        )
                    else:
                        messages.success(request, action_message)
                        return redirect("student_class_assignment_list")

            except Exception as e:
                logger.error(f"Error assigning student {student.id} to class: {str(e)}")
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse(
                        {
                            "success": False,
                            "message": f"Error assigning student: {str(e)}",
                        },
                        status=500,
                    )
                else:
                    messages.error(request, f"Error assigning student: {str(e)}")
        else:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {
                        "success": False,
                        "message": "Invalid form data",
                        "errors": form.errors,
                    },
                    status=400,
                )
            else:
                messages.error(request, "Invalid form data")

    # GET request - show form
    form = StudentClassAssignmentForm(
        current_academic_year=current_academic_year, school=school
    )

    context = {
        "student": student,
        "form": form,
        "current_academic_year": current_academic_year,
    }

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return render(request, "student/class_assignment/assign_modal.html", context)
    else:
        return render(request, "student/class_assignment/assign.html", context)


@login_required
@user_passes_test(is_admin)
@csrf_protect
@require_http_methods(["POST"])
def unassign_student_class(request, student_id):
    """
    Unassign a student from their current class
    """
    school = request.user.school
    student = get_object_or_404(Student, pk=student_id, school=school)

    try:
        with transaction.atomic():
            # Deactivate current assignment
            updated_count = StudentClass.objects.filter(
                student=student, is_active=True, school=school
            ).update(is_active=False)

            if updated_count > 0:
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse(
                        {
                            "success": True,
                            "message": f"{student.full_name} has been unassigned from their class.",
                        }
                    )
                else:
                    messages.success(
                        request,
                        f"{student.full_name} has been unassigned from their class.",
                    )
            else:
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse(
                        {
                            "success": False,
                            "message": "Student is not currently assigned to any class.",
                        },
                        status=400,
                    )
                else:
                    messages.warning(
                        request, "Student is not currently assigned to any class."
                    )

    except Exception as e:
        logger.error(f"Error unassigning student {student.id}: {str(e)}")
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {"success": False, "message": f"Error unassigning student: {str(e)}"},
                status=500,
            )
        else:
            messages.error(request, f"Error unassigning student: {str(e)}")

    return redirect("student_class_assignment_list")


@login_required
@user_passes_test(is_admin)
def bulk_assign_students(request):
    """
    Bulk assign multiple students to classes
    """
    school = request.user.school
    current_academic_year = SchoolInformation.get_current_academic_year(school=school)

    if not current_academic_year:
        messages.error(
            request,
            "No current academic year is set. Please set one before managing class assignments.",
        )
        return redirect("admin_dashboard")

    if request.method == "POST":
        form = BulkStudentClassAssignmentForm(
            request.POST, current_academic_year=current_academic_year, school=school
        )

        if form.is_valid():
            students = form.cleaned_data[
                "students"
            ]  # This returns Student objects, not IDs
            assigned_class = form.cleaned_data["assigned_class"]

            success_count = 0
            error_count = 0
            skipped_count = 0
            skipped_reasons = []
            errors = []

            try:
                with transaction.atomic():
                    for student in students:
                        try:
                            # student is already a Student object, no need to query again

                            # Check if student has any assignment to the same class (active or inactive)
                            existing_assignment = StudentClass.objects.filter(
                                student=student,
                                assigned_class=assigned_class,
                                school=school,
                            ).first()

                            if existing_assignment:
                                if existing_assignment.is_active:
                                    # Student is already actively assigned to this class - skip
                                    skipped_count += 1
                                    skipped_reasons.append(
                                        f"{student.full_name} ({student.admission_number}) is already assigned to {assigned_class.name}"
                                    )
                                    continue
                                else:
                                    # Student has an inactive assignment to this class - reactivate it
                                    # First deactivate any current active assignment
                                    StudentClass.objects.filter(
                                        student=student, is_active=True, school=school
                                    ).update(is_active=False)

                                    # Reactivate the existing assignment
                                    existing_assignment.is_active = True
                                    existing_assignment.assigned_by = request.user
                                    existing_assignment.date_assigned = (
                                        timezone.now().date()
                                    )
                                    existing_assignment.save()

                                    success_count += 1
                            else:
                                # No previous assignment to this class - create new one
                                # Deactivate current assignment (if any)
                                StudentClass.objects.filter(
                                    student=student, is_active=True, school=school
                                ).update(is_active=False)

                                # Create new assignment
                                new_assignment = StudentClass(
                                    student=student,
                                    assigned_class=assigned_class,
                                    is_active=True,
                                    assigned_by=request.user,
                                    school=school,
                                )
                                new_assignment.clean()
                                new_assignment.save()

                                success_count += 1

                        except Exception as e:
                            error_count += 1
                            error_msg = f"Error assigning student {student.full_name} ({student.admission_number}): {str(e)}"
                            errors.append(error_msg)
                            logger.error(
                                f"Bulk assignment error for student {student.full_name} ({student.admission_number}): {str(e)}",
                                exc_info=True,
                            )

                            # Log student details for debugging
                            try:
                                logger.error(
                                    f"Student details: {student.full_name}, Form: {student.form}, Learning Area: {student.learning_area}"
                                )

                                # Check for existing assignments
                                existing = StudentClass.objects.filter(
                                    student=student, is_active=True, school=school
                                )
                                if existing.exists():
                                    logger.error(
                                        f"Student {student.full_name} already has active assignment: {existing.first().assigned_class.name}"
                                    )
                            except Exception as detail_error:
                                logger.error(
                                    f"Error getting student details: {detail_error}"
                                )

                total_selected = len(students)
                # skipped_count is now calculated during the loop

                if success_count > 0:
                    messages.success(
                        request,
                        f"Successfully assigned {success_count} students to {assigned_class.name}.",
                    )

                if skipped_count > 0:
                    messages.info(
                        request,
                        f"{skipped_count} students were already assigned to {assigned_class.name} and were skipped.",
                    )

                if error_count > 0:
                    messages.warning(
                        request,
                        f"{error_count} students could not be assigned. Check the logs for details.",
                    )

            except Exception as e:
                logger.error(f"Error in bulk assignment: {str(e)}")
                messages.error(request, f"Error in bulk assignment: {str(e)}")

            # Handle AJAX requests
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                if success_count > 0:
                    message = f"Successfully assigned {success_count} students to {assigned_class.name}."
                    if skipped_count > 0:
                        message += f" {skipped_count} students were skipped (already assigned)."
                    return JsonResponse(
                        {
                            "success": True,
                            "message": message,
                            "success_count": success_count,
                            "error_count": error_count,
                            "skipped_count": skipped_count,
                            "skipped_reasons": skipped_reasons,
                        }
                    )
                else:
                    if skipped_count > 0 and error_count == 0:
                        # All students were skipped, no errors
                        message = f"No students were assigned. {skipped_count} students were skipped (already assigned to this class)."
                        return JsonResponse(
                            {
                                "success": False,
                                "message": message,
                                "success_count": success_count,
                                "error_count": error_count,
                                "skipped_count": skipped_count,
                                "skipped_reasons": skipped_reasons,
                                "detailed_message": f"Success: {success_count}, Errors: {error_count}, Skipped: {skipped_count}. Skipped reasons: {'; '.join(skipped_reasons)}",
                            }
                        )
                    else:
                        # There were errors
                        return JsonResponse(
                            {
                                "success": False,
                                "message": f"Failed to assign students. {error_count} errors occurred.",
                                "success_count": success_count,
                                "error_count": error_count,
                                "skipped_count": skipped_count,
                                "errors": errors,
                                "skipped_reasons": skipped_reasons,
                                "detailed_message": f"Success: {success_count}, Errors: {error_count}, Skipped: {skipped_count}. Error details: {'; '.join(errors)}",
                            }
                        )

            return redirect("student_class_assignment_list")
        else:
            # Form validation failed
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {
                        "success": False,
                        "message": "Invalid form data. Please check your selections.",
                        "errors": form.errors,
                    },
                    status=400,
                )
            else:
                messages.error(request, "Invalid form data")

    else:
        form = BulkStudentClassAssignmentForm(
            current_academic_year=current_academic_year, school=school
        )

    # Get students for selection - exclude graduated students
    students = (
        Student.objects.filter(school=school)
        .exclude(archivedstudent__isnull=False)
        .select_related("form", "learning_area")
    )


    # Add current class information and calculate age
    for student in students:
        # Calculate age
        age = "Not set"
        if student.date_of_birth:
            from datetime import date
            today = date.today()
            age = today.year - student.date_of_birth.year
            if (today.month, today.day) < (student.date_of_birth.month, student.date_of_birth.day):
                age -= 1
        student.calculated_age = age


        # Check for assignment in current academic year
        current_assignment = (
            StudentClass.objects.filter(
                student=student,
                assigned_class__academic_year=current_academic_year,
                is_active=True,
                school=school,
            )
            .select_related(
                "assigned_class",
                "assigned_class__form",
                "assigned_class__learning_area",
            )
            .first()
        )

        # Check for any active assignment in any academic year
        any_active_assignment = (
            StudentClass.objects.filter(
                student=student,
                is_active=True,
                school=school,
            )
            .select_related(
                "assigned_class",
                "assigned_class__academic_year",
                "assigned_class__form",
                "assigned_class__learning_area",
            )
            .first()
        )

        student.current_class_assignment = (
            current_assignment.assigned_class if current_assignment else None
        )

        # Add information about active assignment in other academic years
        if not current_assignment and any_active_assignment:
            student.other_academic_year_assignment = any_active_assignment
            student.assignment_status = "assigned_other_year"
        elif current_assignment:
            student.assignment_status = "assigned_current_year"
        else:
            student.assignment_status = "unassigned"

    context = {
        "form": form,
        "students": students,
        "current_academic_year": current_academic_year,
    }

    return render(request, "student/class_assignment/bulk_assign.html", context)


@login_required
@user_passes_test(is_admin)
@csrf_protect
@require_http_methods(["POST"])
def bulk_unassign_students(request):
    """
    Bulk unassign multiple students from their classes
    """
    school = request.user.school

    try:
        data = json.loads(request.body)
        student_ids = data.get("student_ids", [])

        if not student_ids:
            return JsonResponse(
                {"success": False, "message": "No students selected."}, status=400
            )

        success_count = 0
        error_count = 0

        with transaction.atomic():
            for student_id in student_ids:
                try:
                    student = Student.objects.get(id=student_id, school=school)

                    # Deactivate current assignment
                    updated_count = StudentClass.objects.filter(
                        student=student, is_active=True, school=school
                    ).update(is_active=False)

                    if updated_count > 0:
                        success_count += 1
                    else:
                        error_count += 1

                except Student.DoesNotExist:
                    error_count += 1
                except Exception as e:
                    logger.error(f"Error unassigning student {student_id}: {str(e)}")
                    error_count += 1

        return JsonResponse(
            {
                "success": True,
                "message": f"Successfully unassigned {success_count} students.",
                "success_count": success_count,
                "error_count": error_count,
            }
        )

    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "message": "Invalid JSON data."}, status=400
        )
    except Exception as e:
        logger.error(f"Error in bulk unassignment: {str(e)}")
        return JsonResponse(
            {"success": False, "message": f"Error in bulk unassignment: {str(e)}"},
            status=500,
        )


@login_required
@user_passes_test(is_admin)
def class_assignment_history(request, student_id):
    """
    View assignment history for a specific student
    """
    school = request.user.school
    student = get_object_or_404(Student, pk=student_id, school=school)

    # Get all assignments for this student
    assignments = (
        StudentClass.objects.filter(student=student, school=school)
        .select_related("assigned_class", "assigned_by")
        .order_by("-date_assigned")
    )

    context = {"student": student, "assignments": assignments}

    return render(request, "student/class_assignment/history.html", context)


@login_required
@user_passes_test(is_admin)
def class_roster(request, class_id):
    """
    View all students assigned to a specific class
    """
    school = request.user.school
    class_obj = get_object_or_404(Class, pk=class_id, school=school)

    # Get all students in this class - exclude graduated students
    students = (
        Student.objects.filter(
            studentclass__assigned_class=class_obj,
            studentclass__is_active=True,
            school=school,
        )
        .exclude(archivedstudent__isnull=False)  # Exclude graduated students
        .select_related("form", "learning_area")
        .order_by("full_name")
    )

    # Get assignment details
    assignments = (
        StudentClass.objects.filter(
            assigned_class=class_obj, is_active=True, school=school
        )
        .select_related("student", "assigned_by")
        .order_by("student__full_name")
    )


    # Calculate gender statistics
    male_count = students.filter(gender="M").count()
    female_count = students.filter(gender="F").count()

    context = {
        "class_obj": class_obj, 
        "students": students, 
        "assignments": assignments,
        "male_count": male_count,
        "female_count": female_count
    }


    return render(request, "student/class_assignment/roster.html", context)


@login_required
@user_passes_test(is_admin)
def get_students_for_assignment(request):
    """
    AJAX endpoint to get students based on filters for assignment
    """
    school = request.user.school
    current_academic_year = SchoolInformation.get_current_academic_year(school=school)

    if not current_academic_year:
        return JsonResponse({"error": "No current academic year set"}, status=400)

    # Get filter parameters
    form_id = request.GET.get("form_id")
    learning_area_id = request.GET.get("learning_area_id")
    status = request.GET.get("status", "unassigned")
    search = request.GET.get("search", "")

    # Build queryset - exclude graduated students
    students_query = Student.objects.filter(school=school).exclude(
        archivedstudent__isnull=False
    )

    if form_id:
        students_query = students_query.filter(form_id=form_id)

    if learning_area_id:
        students_query = students_query.filter(learning_area_id=learning_area_id)

    if search:
        students_query = students_query.filter(
            Q(full_name__icontains=search) | Q(admission_number__icontains=search)
        )

    if status == "assigned":
        students_query = students_query.filter(
            studentclass__assigned_class__academic_year=current_academic_year,
            studentclass__is_active=True,
        )
    elif status == "unassigned":
        students_query = students_query.exclude(
            studentclass__assigned_class__academic_year=current_academic_year,
            studentclass__is_active=True,
        )

    # Get students with current class info
    students = students_query.distinct()[:50]  # Limit for performance

    student_data = []
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

        student_data.append(
            {
                "id": student.id,
                "full_name": student.full_name,
                "admission_number": student.admission_number,
                "form": student.form.name if student.form else "Not set",
                "learning_area": (
                    student.learning_area.name if student.learning_area else "Not set"
                ),
                "current_class": (
                    current_assignment.assigned_class.name
                    if current_assignment
                    else None
                ),
                "is_assigned": current_assignment is not None,
            }
        )

    return JsonResponse({"students": student_data})


@login_required
@user_passes_test(is_admin)
def get_class_statistics(request):
    """
    AJAX endpoint to get class statistics
    """
    school = request.user.school
    current_academic_year = SchoolInformation.get_current_academic_year(school=school)

    if not current_academic_year:
        return JsonResponse({"error": "No current academic year set"}, status=400)

    # Get class statistics
    classes = (
        Class.objects.filter(academic_year=current_academic_year, school=school)
        .annotate(
            student_count=Count("studentclass", filter=Q(studentclass__is_active=True)),
            max_capacity=Case(
                When(maximum_students__isnull=False, then="maximum_students"),
                default=40,
                output_field=IntegerField(),
            ),
        )
        .order_by("name")
    )

    class_data = []
    for class_obj in classes:
        class_data.append(
            {
                "id": class_obj.id,
                "name": class_obj.name,
                "form": class_obj.form.name if class_obj.form else "Not set",
                "learning_area": (
                    class_obj.learning_area.name
                    if class_obj.learning_area
                    else "Not set"
                ),
                "student_count": class_obj.student_count,
                "max_capacity": class_obj.max_capacity,
                "capacity_percentage": (
                    round((class_obj.student_count / class_obj.max_capacity) * 100, 1)
                    if class_obj.max_capacity > 0
                    else 0
                ),
            }
        )

    return JsonResponse({"classes": class_data})



@login_required
@user_passes_test(is_admin)
def get_class_roster_export(request, class_id):
    """
    AJAX endpoint to get complete class roster data for export
    """
    school = request.user.school
    class_obj = get_object_or_404(Class, pk=class_id, school=school)

    # Get all students in this class - exclude graduated students
    students = (
        Student.objects.filter(
            studentclass__assigned_class=class_obj,
            studentclass__is_active=True,
            school=school,
        )
        .exclude(archivedstudent__isnull=False)  # Exclude graduated students
        .select_related("form", "learning_area")
        .order_by("full_name")
    )

    # Get assignment details
    assignments = (
        StudentClass.objects.filter(
            assigned_class=class_obj, is_active=True, school=school
        )
        .select_related("student", "assigned_by")
        .order_by("student__full_name")
    )

    # Create assignment lookup for easier access
    assignment_lookup = {assignment.student.id: assignment for assignment in assignments}

    student_data = []
    for student in students:
        # Calculate age
        age = "Not set"
        if student.date_of_birth:
            from datetime import date
            today = date.today()
            age = today.year - student.date_of_birth.year
            if (today.month, today.day) < (student.date_of_birth.month, student.date_of_birth.day):
                age -= 1
        
        student_data.append({
            "full_name": student.full_name,
            "admission_number": student.admission_number,
            "parent_contact": student.parent_contact or "Not provided",
            "age": age,
            "gender": student.gender,
        })

    return JsonResponse({"students": student_data})

