
"""
Debug views for template creation issues.
"""

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.contrib import messages
from django.shortcuts import redirect
from ..models import (
    AcademicYear,
    AcademicYearTemplate,
    Class,
    ClassSubject,
    TeacherSubjectAssignment,
    ClassTeacher,
)
from ..utils.template_utils import create_template_from_academic_year
from .auth import is_admin


@login_required
@user_passes_test(is_admin)
def debug_template_creation(request, academic_year_id):
    """
    Debug template creation for a specific academic year.
    """
    school = request.user.school
    academic_year = get_object_or_404(AcademicYear, id=academic_year_id, school=school)

    if request.method == "POST":
        template_name = request.POST.get("template_name", "Debug Template")
        description = request.POST.get("description", "Debug template creation")

        try:
            # Create template
            template = create_template_from_academic_year(
                academic_year=academic_year,
                template_name=template_name,
                description=description,
                created_by=request.user,
            )

            messages.success(
                request,
                f'Template "{template.name}" created successfully! ID: {template.id}',
            )
            return redirect("template_list")

        except Exception as e:
            import traceback

            error_details = traceback.format_exc()
            messages.error(request, f"Error: {str(e)}")
            messages.error(request, f"Details: {error_details}")

    # Get data counts
    classes_count = Class.objects.filter(
        academic_year=academic_year, school=school
    ).count()
    class_subjects_count = ClassSubject.objects.filter(
        academic_year=academic_year, school=school, is_active=True
    ).count()
    teacher_assignments_count = TeacherSubjectAssignment.objects.filter(
        academic_year=academic_year, school=school, is_active=True
    ).count()
    class_teachers_count = ClassTeacher.objects.filter(
        academic_year=academic_year, school=school, is_active=True
    ).count()

    context = {
        "academic_year": academic_year,
        "classes_count": classes_count,
        "class_subjects_count": class_subjects_count,
        "teacher_assignments_count": teacher_assignments_count,
        "class_teachers_count": class_teachers_count,
        "title": f"Debug Template Creation - {academic_year.name}",
        "active_menu": "academic_year",
        "school": school,
    }

    return render(request, "admin/template_debug.html", context)

