"""
AJAX views for optimized student list with server-side processing
"""

import json
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q, Case, When, Value, CharField
from django.core.paginator import Paginator
from shs_system.models import Student, Form, LearningArea, Class, SchoolInformation
from shs_system.views.auth import is_admin
from shs_system.forms import StudentForm, StudentClassAssignmentForm


@login_required
@user_passes_test(is_admin)
def student_list_ajax(request):
    """
    AJAX endpoint for DataTables server-side processing
    Handles pagination, search, and filtering on the server side
    """
    # Get user's school for multi-tenancy
    school = request.user.school

    # Get DataTables parameters
    draw = int(request.GET.get("draw", 1))
    start = int(request.GET.get("start", 0))
    length = int(request.GET.get("length", 25))
    search_value = request.GET.get("search[value]", "")

    # Get column ordering
    order_column = int(
        request.GET.get("order[0][column]", 1)
    )  # Default to admission number
    order_dir = request.GET.get("order[0][dir]", "asc")

    # Column mapping for ordering
    columns = [
        "",  # Checkbox column
        "admission_number",
        "full_name",
        "date_of_birth",  # For age calculation
        "gender",
        "parent_contact",
        "current_class",  # Custom field


        "status",  # Custom field
        "",  # Actions column
    ]

    # Get filters from request
    form_filter = request.GET.get("form", "")
    learning_area_filter = request.GET.get("learning_area", "")
    gender_filter = request.GET.get("gender", "")
    status_filter = request.GET.get("status", "")
    class_filter = request.GET.get("class_id", "")

    # Build optimized queryset - exclude graduated students
    students = (
        Student.objects.filter(school=school)
        .exclude(archivedstudent__isnull=False)  # Exclude graduated students
        .select_related("form", "learning_area", "school")
        .prefetch_related(
            "studentclass_set__assigned_class__form",
            "studentclass_set__assigned_class__learning_area",
        )
    )

    # Apply search
    if search_value:
        students = students.filter(
            Q(full_name__icontains=search_value)
            | Q(admission_number__icontains=search_value)
            | Q(parent_contact__icontains=search_value)
            | Q(email__icontains=search_value)
        )

    # Apply filters
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
            # Include students who have no active class assignments (but exclude graduated)
            students = (
                students.filter(
                    Q(studentclass__is_active=False) | Q(studentclass__isnull=True)
                )
                .exclude(archivedstudent__isnull=False)
                .distinct()
            )

    if class_filter:
        # Include both active and archived students who were/are in this class
        students = students.filter(studentclass__assigned_class_id=class_filter)

    # Apply ordering
    if order_column < len(columns) and columns[order_column]:
        order_field = columns[order_column]
        if order_dir == "desc":
            order_field = "-" + order_field

        # Handle special cases for ordering
        if columns[order_column] == "current_class":
            # Order by current class name
            students = students.order_by(
                f"{'- ' if order_dir == 'desc' else ''}studentclass__assigned_class__name"
            )
        elif columns[order_column] == "status":
            # Order by active status
            students = students.annotate(
                status_order=Case(
                    When(studentclass__is_active=True, then=Value("active")),
                    default=Value("inactive"),
                    output_field=CharField(),
                )
            ).order_by(f"{'- ' if order_dir == 'desc' else ''}status_order")
        else:
            students = students.order_by(order_field)
    else:
        students = students.order_by("full_name")

    # Get total count before pagination
    total_records = students.count()

    # Apply pagination
    students_page = students[start : start + length]

    # Prepare data for DataTables
    data = []
    for student in students_page:
        # Calculate age
        from datetime import date

        age = ""
        if student.date_of_birth:
            today = date.today()
            age = (
                today.year
                - student.date_of_birth.year
                - (
                    (today.month, today.day)
                    < (student.date_of_birth.month, student.date_of_birth.day)
                )
            )

        # Get current class and its form/learning area
        current_class = ""
        current_form = ""
        current_learning_area = ""
        active_assignment = student.studentclass_set.filter(is_active=True).first()
        if active_assignment:
            current_class = active_assignment.assigned_class.name
            # Get form and learning area from the assigned class
            if active_assignment.assigned_class.form:
                current_form = active_assignment.assigned_class.form.name
            if active_assignment.assigned_class.learning_area:
                current_learning_area = (
                    active_assignment.assigned_class.learning_area.name
                )

        # Profile picture
        profile_pic_html = ""
        if student.profile_picture:
            profile_pic_html = f'<img src="{student.profile_picture.url}" alt="{student.full_name}" class="rounded-circle me-2" width="40" height="40">'
        else:
            profile_pic_html = f'<div class="bg-secondary rounded-circle text-white d-flex align-items-center justify-content-center me-2" style="width: 40px; height: 40px;">{student.full_name[:1]}</div>'

        # Status badge
        status = "active" if active_assignment else "inactive"
        status_badge = f'<span class="modern-badge {"modern-badge-success" if status == "active" else "modern-badge-secondary"}">{status}</span>'

        # Action buttons - updated to match class list template structure
        actions_html = f"""
         <div class="btn-group btn-group-sm">
             <a href="/school/student/{student.id}/detail/" class="btn btn-outline-info" title="View Full Details">
                 <i class="fas fa-eye"></i>
             </a>
             <button type="button" class="btn btn-outline-primary edit-student-btn" data-id="{student.id}" title="Edit Student">
                 <i class="fas fa-edit"></i>
             </button>

             <button type="button" class="btn btn-outline-success quick-image-upload-btn" data-id="{student.id}" data-name="{student.full_name}" title="Quick Upload Image">
                 <i class="fas fa-camera"></i>
             </button>

             <button type="button" class="btn btn-outline-danger delete-student" data-id="{student.id}" data-name="{student.full_name}" title="Delete Student">
                 <i class="fas fa-trash"></i>
             </button>
         </div>
         """

        data.append(
            [
                f'<div class="form-check"><input class="form-check-input student-checkbox" type="checkbox" value="{student.id}" data-student-name="{student.full_name}"></div>',
                student.admission_number,
                f'<div class="d-flex align-items-center">{profile_pic_html}<span>{student.full_name}</span></div>',
                str(age),
                student.gender,
                student.parent_contact or "",
                current_class or "-",


                status_badge,
                actions_html,
            ]
        )

    # Return JSON response for DataTables
    response = {
        "draw": draw,
        "recordsTotal": total_records,
        "recordsFiltered": total_records,
        "data": data,
    }

    return JsonResponse(response)


@login_required
@user_passes_test(is_admin)
def get_student_view_modal(request):
    """
    AJAX endpoint to get view modal HTML for a specific student
    """
    student_id = request.GET.get("student_id")
    if not student_id:
        return JsonResponse({"error": "Student ID is required"}, status=400)

    try:
        student = (
            Student.objects.select_related("form", "learning_area", "school")
            .prefetch_related("studentclass_set__assigned_class")
            .get(id=student_id, school=request.user.school)
        )
    except Student.DoesNotExist:
        return JsonResponse({"error": "Student not found"}, status=404)

    # Get current class and its form/learning area
    current_class = ""
    current_form = ""
    current_learning_area = ""
    active_assignment = student.studentclass_set.filter(is_active=True).first()
    if active_assignment:
        current_class = active_assignment.assigned_class.name
        # Get form and learning area from the assigned class
        if active_assignment.assigned_class.form:
            current_form = active_assignment.assigned_class.form.name
        if active_assignment.assigned_class.learning_area:
            current_learning_area = active_assignment.assigned_class.learning_area.name

    # Calculate age
    from datetime import date

    age = ""
    if student.date_of_birth:
        today = date.today()
        age = (
            today.year
            - student.date_of_birth.year
            - (
                (today.month, today.day)
                < (student.date_of_birth.month, student.date_of_birth.day)
            )
        )

    context = {
        "student": student,
        "current_class": current_class,
        "current_form": current_form,
        "current_learning_area": current_learning_area,
        "age": age,
        "status": "active" if active_assignment else "inactive",
    }

    from django.template.loader import render_to_string

    try:
        modal_html = render_to_string(
            "student/student_view_modal.html", context, request=request
        )
        return JsonResponse({"html": modal_html})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@user_passes_test(is_admin)
def get_student_edit_modal(request):
    """
    AJAX endpoint to get edit modal HTML for a specific student
    """
    student_id = request.GET.get("student_id")
    if not student_id:
        return JsonResponse({"error": "Student ID is required"}, status=400)

    try:
        student = (
            Student.objects.select_related("form", "learning_area", "school")
            .prefetch_related("studentclass_set__assigned_class")
            .get(id=student_id, school=request.user.school)
        )
    except Student.DoesNotExist:
        return JsonResponse({"error": "Student not found"}, status=404)

    # Create form for this student
    student_form = StudentForm(instance=student, school=request.user.school)

    # Get current class and its form/learning area
    current_class = ""
    current_form = ""
    current_learning_area = ""
    active_assignment = student.studentclass_set.filter(is_active=True).first()
    if active_assignment:
        current_class = active_assignment.assigned_class.name
        # Get form and learning area from the assigned class
        if active_assignment.assigned_class.form:
            current_form = active_assignment.assigned_class.form.name
        if active_assignment.assigned_class.learning_area:
            current_learning_area = active_assignment.assigned_class.learning_area.name

    context = {
        "student": student,
        "student_form": student_form,
        "current_class": current_class,
        "current_form": current_form,
        "current_learning_area": current_learning_area,
        "status": "active" if active_assignment else "inactive",
    }

    from django.template.loader import render_to_string

    try:
        modal_html = render_to_string(
            "student/student_edit_modal.html", context, request=request
        )
        return JsonResponse({"html": modal_html})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@user_passes_test(is_admin)
def get_student_assign_modal(request):
    """
    AJAX endpoint to get class assignment modal HTML for a specific student
    """
    student_id = request.GET.get("student_id")
    if not student_id:
        return JsonResponse({"error": "Student ID is required"}, status=400)

    try:
        student = Student.objects.select_related("form", "learning_area", "school").get(
            id=student_id, school=request.user.school
        )
    except Student.DoesNotExist:
        return JsonResponse({"error": "Student not found"}, status=404)

    # Get current academic year
    current_academic_year = SchoolInformation.get_current_academic_year(
        school=request.user.school
    )

    if not current_academic_year:
        return JsonResponse({"error": "No current academic year set"}, status=400)

    # Create assignment form
    assignment_form = StudentClassAssignmentForm(
        student=student,
        current_academic_year=current_academic_year,
        school=request.user.school,
    )

    context = {
        "student": student,
        "assignment_form": assignment_form,
        "current_academic_year": current_academic_year,
    }

    from django.template.loader import render_to_string

    try:
        modal_html = render_to_string(
            "student/student_assign_modal.html", context, request=request
        )
        return JsonResponse({"html": modal_html})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
