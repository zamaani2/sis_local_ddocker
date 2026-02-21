
"""
Diagnostic views for Academic Year Template system.
Helps debug template creation issues.
"""

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from ..models import (
    AcademicYear,
    Class,
    ClassSubject,
    TeacherSubjectAssignment,
    ClassTeacher,
    Subject,
    Teacher,
)
from .auth import is_admin


@login_required
@user_passes_test(is_admin)
def academic_year_diagnostics(request, academic_year_id):
    """
    Diagnostic view to check what data is available in an academic year.
    """
    school = request.user.school
    academic_year = get_object_or_404(AcademicYear, id=academic_year_id, school=school)

    # Get all related data
    classes = Class.objects.filter(academic_year=academic_year, school=school)
    class_subjects = ClassSubject.objects.filter(
        academic_year=academic_year, school=school, is_active=True
    )
    teacher_assignments = TeacherSubjectAssignment.objects.filter(
        academic_year=academic_year, school=school, is_active=True
    )
    class_teachers = ClassTeacher.objects.filter(
        academic_year=academic_year, school=school, is_active=True
    )

    # Get unique subjects and teachers
    subjects = Subject.objects.filter(school=school)
    teachers = Teacher.objects.filter(school=school)

    # Check for potential issues
    issues = []

    if classes.count() == 0:
        issues.append("No classes found in this academic year")

    if class_subjects.count() == 0:
        issues.append("No subject assignments found")

    if teacher_assignments.count() == 0:
        issues.append("No teacher assignments found")

    if class_teachers.count() == 0:
        issues.append("No class teachers assigned")

    # Check for classes without subjects
    classes_without_subjects = []
    for class_obj in classes:
        if not class_subjects.filter(class_name=class_obj).exists():
            classes_without_subjects.append(class_obj.name)

    if classes_without_subjects:
        issues.append(
            f"Classes without subjects: {', '.join(classes_without_subjects)}"
        )

    # Check for subjects without teachers
    subjects_without_teachers = []
    for cs in class_subjects:
        if not teacher_assignments.filter(
            subject=cs.subject, class_assigned=cs.class_name
        ).exists():
            subjects_without_teachers.append(
                f"{cs.subject.subject_name} in {cs.class_name.name}"
            )

    if subjects_without_teachers:
        issues.append(
            f"Subjects without teachers: {', '.join(subjects_without_teachers[:5])}"
        )  # Limit to 5

    context = {
        "academic_year": academic_year,
        "classes": classes,
        "class_subjects": class_subjects,
        "teacher_assignments": teacher_assignments,
        "class_teachers": class_teachers,
        "subjects": subjects,
        "teachers": teachers,
        "issues": issues,
        "title": f"Diagnostics for {academic_year.name}",
        "active_menu": "academic_year",
        "school": school,
    }

    return render(request, "admin/academic_year_diagnostics.html", context)


@login_required
@user_passes_test(is_admin)
def academic_year_diagnostics_json(request, academic_year_id):
    """
    JSON API for academic year diagnostics.
    """
    school = request.user.school
    academic_year = get_object_or_404(AcademicYear, id=academic_year_id, school=school)

    # Get counts
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

    # Get class details
    classes = []
    for class_obj in Class.objects.filter(academic_year=academic_year, school=school):
        class_data = {
            "id": class_obj.id,
            "name": class_obj.name,
            "form": class_obj.form.name if class_obj.form else None,
            "learning_area": (
                class_obj.learning_area.name if class_obj.learning_area else None
            ),
            "subjects_count": class_subjects_count,
            "teachers_count": teacher_assignments_count,
        }
        classes.append(class_data)

    return JsonResponse(
        {
            "academic_year": {
                "id": academic_year.id,
                "name": academic_year.name,
                "school": academic_year.school.name,
            },
            "counts": {
                "classes": classes_count,
                "class_subjects": class_subjects_count,
                "teacher_assignments": teacher_assignments_count,
                "class_teachers": class_teachers_count,
            },
            "classes": classes,
        }
    )

