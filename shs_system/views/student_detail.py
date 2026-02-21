"""
Views for comprehensive student detail pages
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q, Avg, Count
from shs_system.models import (
    Student,
    ReportCard,
    Assessment,
    StudentClass,
    Term,
    AcademicYear,
    SchoolInformation,
    AttendanceRecord,
    StudentTermRemarks,
)
from shs_system.views.auth import is_admin
from shs_system.utils import get_user_school


@login_required
@user_passes_test(is_admin)
def student_detail(request, student_id):
    """
    Comprehensive student detail view with all academic records
    """
    # Get user's school for multi-tenancy
    user_school = get_user_school(request.user)

    # Get the student
    student = get_object_or_404(Student, id=student_id, school=user_school)

    # Get current academic year and term
    school_info = SchoolInformation.objects.filter(id=user_school.id).first()
    current_academic_year = None
    current_term = None

    if school_info:
        current_academic_year = school_info.current_academic_year
        current_term = school_info.current_term

    if not current_academic_year:
        current_academic_year = AcademicYear.objects.filter(
            is_current=True, school=user_school
        ).first()

    if not current_term:
        current_term = Term.objects.filter(is_current=True, school=user_school).first()

    # Get student's current class assignment
    current_assignment = StudentClass.objects.filter(
        student=student, is_active=True, school=user_school
    ).first()

    # Get all class assignments (history)
    class_assignments = (
        StudentClass.objects.filter(student=student, school=user_school)
        .select_related(
            "assigned_class", "assigned_class__form", "assigned_class__learning_area"
        )
        .order_by("-date_assigned")
    )

    # Get all report cards
    report_cards = (
        ReportCard.objects.filter(student=student, school=user_school)
        .select_related("term", "term__academic_year", "class_assigned")
        .order_by("-term__academic_year", "-term__term_number")
    )

    # Get all assessments
    assessments = (
        Assessment.objects.filter(student=student, school=user_school)
        .select_related(
            "class_subject",
            "class_subject__subject",
            "class_subject__academic_year",
            "term",
        )
        .order_by("-date_recorded")
    )

    # Get attendance records
    attendance_records = (
        AttendanceRecord.objects.filter(student=student, school=user_school)
        .select_related("term", "term__academic_year")
        .order_by("-term__academic_year", "-term__term_number")
    )

    # Get term remarks
    term_remarks = (
        StudentTermRemarks.objects.filter(student=student, school=user_school)
        .select_related("term", "term__academic_year")
        .order_by("-term__academic_year", "-term__term_number")
    )

    # Calculate academic statistics
    academic_stats = calculate_academic_statistics(student, user_school)

    # Get performance data for current academic year
    current_performance = None
    if current_academic_year:
        from shs_system.utils import check_promotion_eligibility

        current_performance = check_promotion_eligibility(
            student, current_academic_year, school=user_school
        )

    # Get all academic years the student has been enrolled
    academic_years = (
        AcademicYear.objects.filter(reportcard__student=student, school=user_school)
        .distinct()
        .order_by("-name")
    )

    context = {
        "student": student,
        "current_assignment": current_assignment,
        "class_assignments": class_assignments,
        "report_cards": report_cards,
        "assessments": assessments,
        "attendance_records": attendance_records,
        "term_remarks": term_remarks,
        "academic_stats": academic_stats,
        "current_performance": current_performance,
        "academic_years": academic_years,
        "current_academic_year": current_academic_year,
        "current_term": current_term,
        "user_school": user_school,
    }

    return render(request, "student/student_detail.html", context)


def calculate_academic_statistics(student, school):
    """
    Calculate comprehensive academic statistics for a student
    """
    stats = {
        "total_report_cards": 0,
        "average_score": 0,
        "best_score": 0,
        "worst_score": 0,
        "total_assessments": 0,
        "average_attendance": 0,
        "total_days_present": 0,
        "total_school_days": 0,
        "academic_years_enrolled": 0,
        "forms_completed": [],
        "subjects_taken": [],
        "performance_trend": [],
    }

    # Report card statistics
    report_cards = ReportCard.objects.filter(student=student, school=school)
    stats["total_report_cards"] = report_cards.count()

    if report_cards.exists():
        scores = report_cards.exclude(total_score__isnull=True).values_list(
            "total_score", flat=True
        )
        if scores:
            stats["average_score"] = round(sum(scores) / len(scores), 2)
            stats["best_score"] = max(scores)
            stats["worst_score"] = min(scores)

            # Performance trend (last 5 report cards)
            recent_cards = report_cards.exclude(total_score__isnull=True).order_by(
                "-term__academic_year", "-term__term_number"
            )[:5]
            stats["performance_trend"] = [
                {
                    "term": f"{card.term.academic_year.name} - {card.term.get_term_number_display()}",
                    "score": card.total_score,
                    "position": card.position,
                }
                for card in recent_cards
            ]

    # Assessment statistics

    # Exclude mock exam assessments from assessment count statistics
    assessments = Assessment.objects.filter(student=student, school=school).exclude(assessment_type='mock_exam')

    stats["total_assessments"] = assessments.count()

    # Attendance statistics
    attendance_records = AttendanceRecord.objects.filter(student=student, school=school)
    if attendance_records.exists():
        total_present = sum(record.days_present or 0 for record in attendance_records)
        total_days = sum(record.total_school_days or 0 for record in attendance_records)
        stats["total_days_present"] = total_present
        stats["total_school_days"] = total_days
        if total_days > 0:
            stats["average_attendance"] = round((total_present / total_days) * 100, 2)

    # Academic years and forms
    academic_years = AcademicYear.objects.filter(
        reportcard__student=student, school=school
    ).distinct()
    stats["academic_years_enrolled"] = academic_years.count()

    # Forms completed
    forms = set()
    for assignment in StudentClass.objects.filter(student=student, school=school):
        if assignment.assigned_class and assignment.assigned_class.form:
            forms.add(assignment.assigned_class.form.name)
    stats["forms_completed"] = list(forms)

    # Subjects taken
    subjects = set()
    for assessment in assessments:
        if assessment.class_subject and assessment.class_subject.subject:
            subjects.add(assessment.class_subject.subject.subject_name)
    stats["subjects_taken"] = list(subjects)

    return stats


# Removed duplicate terminal report function - using existing system instead
