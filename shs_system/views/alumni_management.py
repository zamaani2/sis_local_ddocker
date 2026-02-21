"""
Views for managing graduated students (alumni)
"""

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from shs_system.models import (
    Student,
    ArchivedStudent,
    Form,
    LearningArea,
    SchoolInformation,
)
from shs_system.views.auth import is_admin
from shs_system.utils import get_user_school


@login_required
@user_passes_test(is_admin)
def alumni_list(request):
    """
    Display list of graduated students (alumni)
    """
    # Get user's school for multi-tenancy
    user_school = get_user_school(request.user)

    # Get filter parameters
    search_query = request.GET.get("search", "")
    form_filter = request.GET.get("form", "")
    learning_area_filter = request.GET.get("learning_area", "")
    graduation_year_filter = request.GET.get("graduation_year", "")

    # Build queryset for graduated students
    alumni = (
        ArchivedStudent.objects.filter(student__school=user_school)
        .select_related("student", "final_form", "final_learning_area", "archived_by")
        .order_by("-completion_date")
    )

    # Apply search filter
    if search_query:
        alumni = alumni.filter(
            Q(student__full_name__icontains=search_query)
            | Q(student__admission_number__icontains=search_query)
        )

    # Apply form filter
    if form_filter:

        alumni = alumni.filter(final_form_id=form_filter)


    # Apply learning area filter
    if learning_area_filter:
        alumni = alumni.filter(final_learning_area_id=learning_area_filter)

    # Apply graduation year filter
    if graduation_year_filter:
        alumni = alumni.filter(completion_date__year=graduation_year_filter)

    # Get available forms and learning areas for filters
    forms = Form.objects.filter(school=user_school).order_by("form_number")
    learning_areas = LearningArea.objects.filter(school=user_school).order_by("name")

    # Get available graduation years
    graduation_years = (
        ArchivedStudent.objects.filter(student__school=user_school)
        .values_list("completion_date__year", flat=True)
        .distinct()
        .order_by("-completion_date__year")
    )

    # Paginate results
    paginator = Paginator(alumni, 25)
    page = request.GET.get("page")
    try:
        alumni = paginator.page(page)
    except:
        alumni = paginator.page(1)

    context = {
        "alumni": alumni,
        "forms": forms,
        "learning_areas": learning_areas,
        "graduation_years": graduation_years,
        "search_query": search_query,
        "form_filter": form_filter,
        "learning_area_filter": learning_area_filter,
        "graduation_year_filter": graduation_year_filter,
        "total_count": paginator.count,
        "user_school": user_school,
    }

    return render(request, "student/alumni_list.html", context)


@login_required
@user_passes_test(is_admin)
def alumni_detail(request, student_id):
    """
    Display detailed information about a graduated student
    """
    # Get user's school for multi-tenancy
    user_school = get_user_school(request.user)

    # Get the archived student record
    archived_student = get_object_or_404(
        ArchivedStudent, student_id=student_id, student__school=user_school
    )

    # Get student's report cards
    from shs_system.models import ReportCard

    report_cards = ReportCard.objects.filter(
        student=archived_student.student, school=user_school
    ).order_by("-term__academic_year", "-term__term_number")

    context = {
        "archived_student": archived_student,
        "report_cards": report_cards,
        "user_school": user_school,
    }

    return render(request, "student/alumni_detail.html", context)


@login_required
@user_passes_test(is_admin)
def alumni_list_ajax(request):
    """
    AJAX endpoint for DataTables server-side processing of alumni
    """
    # Get user's school for multi-tenancy
    school = request.user.school

    # Get DataTables parameters
    draw = int(request.GET.get("draw", 1))
    start = int(request.GET.get("start", 0))
    length = int(request.GET.get("length", 25))
    search_value = request.GET.get("search[value]", "")

    # Get column ordering
    order_column = int(request.GET.get("order[0][column]", 0))
    order_dir = request.GET.get("order[0][dir]", "desc")

    # Column mapping for ordering
    columns = [
        "completion_date",
        "student__admission_number",
        "student__full_name",
        "final_form__name",
        "final_learning_area__name",
        "remarks",
    ]

    # Get filters from request
    form_filter = request.GET.get("form", "")
    learning_area_filter = request.GET.get("learning_area", "")
    graduation_year_filter = request.GET.get("graduation_year", "")

    # Build queryset
    alumni = ArchivedStudent.objects.filter(student__school=school).select_related(
        "student", "final_form", "final_learning_area", "archived_by"
    )

    # Apply search
    if search_value:
        alumni = alumni.filter(
            Q(student__full_name__icontains=search_value)
            | Q(student__admission_number__icontains=search_value)
            | Q(remarks__icontains=search_value)
        )

    # Apply filters
    if form_filter:

        alumni = alumni.filter(final_form_id=form_filter)


    if learning_area_filter:
        alumni = alumni.filter(final_learning_area_id=learning_area_filter)

    if graduation_year_filter:
        alumni = alumni.filter(completion_date__year=graduation_year_filter)

    # Apply ordering
    if order_column < len(columns):
        order_field = columns[order_column]
        if order_dir == "desc":
            order_field = f"-{order_field}"
        alumni = alumni.order_by(order_field)

    # Get total count before pagination
    total_records = alumni.count()

    # Apply pagination
    alumni = alumni[start : start + length]

    # Prepare data for DataTables
    data = []
    for archived_student in alumni:
        data.append(
            {
                "completion_date": archived_student.completion_date.strftime(
                    "%Y-%m-%d"
                ),
                "admission_number": archived_student.student.admission_number,
                "full_name": archived_student.student.full_name,
                "final_form": (
                    archived_student.final_form.name
                    if archived_student.final_form
                    else "N/A"
                ),
                "final_learning_area": (
                    archived_student.final_learning_area.name
                    if archived_student.final_learning_area
                    else "N/A"
                ),
                "remarks": (
                    archived_student.remarks[:50] + "..."
                    if archived_student.remarks and len(archived_student.remarks) > 50
                    else archived_student.remarks or ""
                ),
                "actions": f"""
                <div class="btn-group" role="group">
                    <button type="button" class="btn btn-sm btn-outline-primary action-btn-view" 
                            data-id="{archived_student.student.id}" title="View Details">
                        <i class="bi bi-eye"></i>
                    </button>
                </div>
            """,
            }
        )

    return JsonResponse(
        {
            "draw": draw,
            "recordsTotal": total_records,
            "recordsFiltered": total_records,
            "data": data,
        }
    )
