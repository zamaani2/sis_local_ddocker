# Teacher Activity Monitoring Views

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Q, F, Case, When, Value, IntegerField, Sum
from django.utils import timezone
from django.contrib import messages
from django.core.paginator import Paginator
from django.urls import reverse
from django.conf import settings
from django.urls import reverse_lazy

from ..models import (
    Teacher,
    TeacherSubjectAssignment,
    Class,
    Subject,
    Student,
    StudentClass,
    Assessment,
    StudentTermRemarks,
    AcademicYear,
    Term,
    Department,
    ReportCard,
    ClassTeacher,

    ClassSubject,

    SchoolInformation,
    ScheduledReminder,
    ReminderLog,
)
from ..forms import TeacherActivityMonitoringFilterForm
from ..utils import (
    is_admin_or_superadmin,
    get_current_academic_year,
    get_current_term,
    get_user_school,
    send_activity_reminder_email,
)

import datetime
import csv
from io import StringIO


@login_required
@user_passes_test(is_admin_or_superadmin)
def teacher_activity_monitoring(request):
    """View for monitoring teacher activities"""
    school = get_user_school(request.user)

    # Get current academic year and term
    current_academic_year = get_current_academic_year(school)
    current_term = get_current_term(school)

    # Initialize filter form
    form = TeacherActivityMonitoringFilterForm(
        request.GET or None,
        school=school,
        initial={"academic_year": current_academic_year, "term": current_term},
    )

    # Update term choices based on selected academic year
    if request.GET.get("academic_year"):
        selected_academic_year = get_object_or_404(
            AcademicYear, id=request.GET.get("academic_year")
        )
        form.fields["term"].queryset = Term.objects.filter(
            academic_year=selected_academic_year, school=school
        ).order_by("start_date")


    # Base queryset for teacher assignments - filter by active assignments
    teacher_assignments_query = TeacherSubjectAssignment.objects.filter(
        teacher__user__school=school,
        is_active=True

    ).select_related(
        "teacher",
        "subject",
        "class_assigned",
        "class_assigned__academic_year",
        "class_assigned__form",
    )


    # Apply filters first

    if form.is_valid():
        filters = {}

        if form.cleaned_data["academic_year"]:
            filters["class_assigned__academic_year"] = form.cleaned_data[
                "academic_year"
            ]

        if form.cleaned_data["term"]:
            # We'll use this for activity tracking, not filtering assignments
            selected_term = form.cleaned_data["term"]
        else:
            selected_term = current_term

        if form.cleaned_data["department"]:
            filters["teacher__department"] = form.cleaned_data["department"]

        if filters:

            teacher_assignments_query = teacher_assignments_query.filter(**filters)
    else:
        # Default to current academic year and term
        selected_term = current_term

    # Filter out assignments where ClassSubject is not active
    # Get active class-subject combinations
    active_class_subjects = ClassSubject.objects.filter(
        is_active=True
    ).values_list('class_name_id', 'subject_id')
    
    # Filter assignments to only include those with active ClassSubject
    filtered_assignments = []
    for assignment in teacher_assignments_query:
        if (assignment.class_assigned.id, assignment.subject.id) in active_class_subjects:
            filtered_assignments.append(assignment)
    
    teacher_assignments = filtered_assignments


    # Process each assignment to add activity status
    activities_data = []

    for assignment in teacher_assignments:
        # Get class and subject details
        class_obj = assignment.class_assigned
        subject = assignment.subject
        teacher = assignment.teacher

        # Skip if no term is selected (needed for activity tracking)
        if not selected_term:
            continue

        # Get student count for this class
        student_count = StudentClass.objects.filter(
            assigned_class=class_obj, is_active=True
        ).count()

        # Calculate activity completion rates

        # 1. Score Entry Status

        # Exclude mock exam assessments from score entry monitoring

        scores_entered = Assessment.objects.filter(
            student__studentclass__assigned_class=class_obj,
            class_subject__subject=subject,
            class_subject__academic_year=selected_term.academic_year,

            class_subject__is_active=True,
            term=selected_term,
            student__studentclass__is_active=True,
        ).exclude(assessment_type='mock_exam').count()


        score_completion = {
            "total": student_count,
            "completed": scores_entered,
            "percentage": round(
                (scores_entered / student_count * 100) if student_count > 0 else 0
            ),
            "status": get_completion_status(scores_entered, student_count),
        }

        # 2. Remarks Status (if teacher is class teacher)
        is_class_teacher = ClassTeacher.objects.filter(
            class_assigned=class_obj,
            teacher=teacher,
            academic_year=class_obj.academic_year,
            is_active=True,
        ).exists()

        if is_class_teacher:
            remarks_entered = StudentTermRemarks.objects.filter(
                student__studentclass__assigned_class=class_obj,
                term=selected_term,
                student__studentclass__is_active=True,
            ).count()

            remarks_completion = {
                "total": student_count,
                "completed": remarks_entered,
                "percentage": round(
                    (remarks_entered / student_count * 100) if student_count > 0 else 0
                ),
                "status": get_completion_status(remarks_entered, student_count),
            }
        else:
            remarks_completion = None

        # 3. Report Card Status (if teacher is class teacher)
        if is_class_teacher:
            report_cards_generated = ReportCard.objects.filter(
                student__studentclass__assigned_class=class_obj,
                term=selected_term,
                student__studentclass__is_active=True,
            ).count()

            report_cards_completion = {
                "total": student_count,
                "completed": report_cards_generated,
                "percentage": round(
                    (report_cards_generated / student_count * 100)
                    if student_count > 0
                    else 0
                ),
                "status": get_completion_status(report_cards_generated, student_count),
            }
        else:
            report_cards_completion = None

        # Filter based on activity type if specified
        activity_type = (
            form.cleaned_data.get("activity_type") if form.is_valid() else None
        )
        completion_status = (
            form.cleaned_data.get("completion_status") if form.is_valid() else None
        )

        # Check if this assignment should be included based on filters
        include_assignment = True

        if activity_type:
            if (
                activity_type == "scores"
                and score_completion["status"] != completion_status
                and completion_status
            ):
                include_assignment = False
            elif (
                activity_type == "remarks"
                and (
                    not remarks_completion
                    or remarks_completion["status"] != completion_status
                )
                and completion_status
            ):
                include_assignment = False
            elif (
                activity_type == "report_cards"
                and (
                    not report_cards_completion
                    or report_cards_completion["status"] != completion_status
                )
                and completion_status
            ):
                include_assignment = False

        if include_assignment:
            # Create activity data object
            activity_data = {
                "assignment_id": assignment.id,
                "teacher": {
                    "id": teacher.id,
                    "name": teacher.full_name,
                    "staff_id": teacher.staff_id,
                    "department": (
                        teacher.department.name if teacher.department else "N/A"
                    ),
                },
                "class": {
                    "id": class_obj.id,
                    "name": class_obj.name,
                    "form": class_obj.form.name if class_obj.form else "N/A",
                    "academic_year": class_obj.academic_year.name,
                    "student_count": student_count,
                },
                "subject": {"id": subject.id, "name": subject.subject_name},
                "is_class_teacher": is_class_teacher,
                "scores": score_completion,
                "remarks": remarks_completion,
                "report_cards": report_cards_completion,
                "last_activity": get_last_activity_date(
                    teacher, class_obj, subject, selected_term
                ),
            }

            activities_data.append(activity_data)

    # Paginate results
    paginator = Paginator(activities_data, 20)  # Show 20 assignments per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Handle export to CSV if requested
    if request.GET.get("export") == "csv":
        return export_monitoring_csv(activities_data, selected_term)

    context = {
        "form": form,
        "page_obj": page_obj,
        "current_academic_year": current_academic_year,
        "current_term": current_term,
        "selected_term": selected_term,
        "total_assignments": len(activities_data),
        "school": school,
    }

    return render(
        request,
        "teacher_activity_monitoring/monitoring_dashboard.html",
        context,
    )


@login_required
@user_passes_test(is_admin_or_superadmin)
def teacher_activity_detail(request, teacher_id):
    """View for detailed activity monitoring for a specific teacher"""
    school = get_user_school(request.user)
    teacher = get_object_or_404(Teacher, id=teacher_id, user__school=school)

    # Get current academic year and term
    current_academic_year = get_current_academic_year(school)
    current_term = get_current_term(school)

    # Get selected academic year and term from query parameters
    academic_year_id = request.GET.get(
        "academic_year", current_academic_year.id if current_academic_year else None
    )
    term_id = request.GET.get("term", current_term.id if current_term else None)

    if academic_year_id:
        selected_academic_year = get_object_or_404(
            AcademicYear, id=academic_year_id, school=school
        )
    else:
        selected_academic_year = current_academic_year

    if term_id:
        selected_term = get_object_or_404(Term, id=term_id, school=school)
    else:
        selected_term = current_term

    # Get all assignments for this teacher in the selected academic year
    assignments = TeacherSubjectAssignment.objects.filter(
        teacher=teacher, class_assigned__academic_year=selected_academic_year
    ).select_related("subject", "class_assigned")

    # Process each assignment to add detailed activity status
    detailed_activities = []

    for assignment in assignments:
        class_obj = assignment.class_assigned
        subject = assignment.subject

        # Get students in this class
        students = Student.objects.filter(
            studentclass__assigned_class=class_obj, studentclass__is_active=True
        ).select_related("form", "learning_area")

        # Check if teacher is class teacher
        is_class_teacher = ClassTeacher.objects.filter(
            class_assigned=class_obj,
            teacher=teacher,
            academic_year=class_obj.academic_year,
            is_active=True,
        ).exists()

        # Get activity details for each student
        student_activities = []

        for student in students:
            # Score entry status

            # Exclude mock exam assessments from score entry monitoring

            score_entry = Assessment.objects.filter(
                student=student,
                class_subject__subject=subject,
                class_subject__academic_year=selected_term.academic_year,

                class_subject__is_active=True,
                term=selected_term,
            ).exclude(assessment_type='mock_exam').first()


            # Remarks status (if class teacher)
            if is_class_teacher:
                remarks_entry = StudentTermRemarks.objects.filter(
                    student=student, term=selected_term
                ).first()

                report_card = ReportCard.objects.filter(
                    student=student, term=selected_term
                ).first()
            else:
                remarks_entry = None
                report_card = None

            student_activity = {
                "student": {
                    "id": student.id,
                    "name": student.full_name,
                    "form": student.form.name if student.form else "N/A",
                },
                "score_entry": {
                    "status": "completed" if score_entry else "not_started",
                    "score": score_entry.total_score if score_entry else None,
                    "date": score_entry.date_recorded if score_entry else None,
                },
                "remarks": (
                    {
                        "status": "completed" if remarks_entry else "not_started",
                        "date": remarks_entry.last_updated if remarks_entry else None,
                    }
                    if is_class_teacher
                    else None
                ),
                "report_card": (
                    {
                        "status": "completed" if report_card else "not_started",
                        "date": report_card.last_updated if report_card else None,
                        "approved": report_card.is_approved if report_card else False,
                    }
                    if is_class_teacher
                    else None
                ),
            }

            student_activities.append(student_activity)

        # Calculate summary statistics
        total_students = len(students)
        scores_completed = sum(
            1 for sa in student_activities if sa["score_entry"]["status"] == "completed"
        )

        if is_class_teacher:
            remarks_completed = sum(
                1
                for sa in student_activities
                if sa["remarks"] and sa["remarks"]["status"] == "completed"
            )
            report_cards_completed = sum(
                1
                for sa in student_activities
                if sa["report_card"] and sa["report_card"]["status"] == "completed"
            )
            report_cards_approved = sum(
                1
                for sa in student_activities
                if sa["report_card"] and sa["report_card"]["approved"]
            )
        else:
            remarks_completed = 0
            report_cards_completed = 0
            report_cards_approved = 0

        activity_detail = {
            "assignment": {
                "id": assignment.id,
                "class": class_obj.name,
                "subject": subject.subject_name,
                "is_class_teacher": is_class_teacher,
            },
            "students": student_activities,
            "summary": {
                "total_students": total_students,
                "scores_completed": scores_completed,
                "scores_percentage": round(
                    (scores_completed / total_students * 100)
                    if total_students > 0
                    else 0
                ),
                "remarks_completed": remarks_completed,
                "remarks_percentage": (
                    round(
                        (remarks_completed / total_students * 100)
                        if total_students > 0
                        else 0
                    )
                    if is_class_teacher
                    else 0
                ),
                "report_cards_completed": report_cards_completed,
                "report_cards_percentage": (
                    round(
                        (report_cards_completed / total_students * 100)
                        if total_students > 0
                        else 0
                    )
                    if is_class_teacher
                    else 0
                ),
                "report_cards_approved": report_cards_approved,
                "report_cards_approved_percentage": (
                    round(
                        (report_cards_approved / report_cards_completed * 100)
                        if report_cards_completed > 0
                        else 0
                    )
                    if is_class_teacher
                    else 0
                ),
            },
        }

        detailed_activities.append(activity_detail)

    # Get available academic years and terms for filtering
    academic_years = AcademicYear.objects.filter(school=school).order_by("-start_date")
    terms = Term.objects.filter(
        academic_year=selected_academic_year, school=school
    ).order_by("start_date")

    context = {
        "teacher": teacher,
        "detailed_activities": detailed_activities,
        "academic_years": academic_years,
        "terms": terms,
        "selected_academic_year": selected_academic_year,
        "selected_term": selected_term,
    }

    return render(request, "teacher_activity_monitoring/teacher_detail.html", context)


@login_required
@user_passes_test(is_admin_or_superadmin)
def class_activity_detail(request, class_id):
    """View for detailed activity monitoring for a specific class"""
    school = get_user_school(request.user)
    class_obj = get_object_or_404(Class, id=class_id, school=school)

    # Get current term and academic year
    current_term = get_current_term(school)
    current_academic_year = get_current_academic_year(school)

    # Get selected academic year from query parameters
    academic_year_id = request.GET.get("academic_year", class_obj.academic_year.id)
    if academic_year_id:
        selected_academic_year = get_object_or_404(AcademicYear, id=academic_year_id)
    else:
        selected_academic_year = class_obj.academic_year

    # Get selected term from query parameters
    term_id = request.GET.get("term", current_term.id if current_term else None)

    if term_id:
        selected_term = get_object_or_404(Term, id=term_id, school=school)
    else:
        selected_term = current_term

    # Get class teacher from ClassTeacher model
    class_teacher_obj = (
        ClassTeacher.objects.filter(
            class_assigned=class_obj,
            academic_year=class_obj.academic_year,
            is_active=True,
        )
        .select_related("teacher")
        .first()
    )

    class_teacher = class_teacher_obj.teacher if class_teacher_obj else None

    # Get all subject assignments for this class
    subject_assignments = TeacherSubjectAssignment.objects.filter(
        class_assigned=class_obj
    ).select_related("teacher", "subject")

    # Get students in this class
    students = Student.objects.filter(
        studentclass__assigned_class=class_obj, studentclass__is_active=True
    ).select_related("form", "learning_area")

    # Process activity data for each subject
    subject_activities = []

    for assignment in subject_assignments:
        subject = assignment.subject
        teacher = assignment.teacher

        # Calculate score entry completion

        # Exclude mock exam assessments from score entry monitoring

        scores_entered = Assessment.objects.filter(
            student__in=students,
            class_subject__subject=subject,
            class_subject__academic_year=selected_term.academic_year,

            class_subject__is_active=True,
            term=selected_term,
        ).exclude(assessment_type='mock_exam').count()


        subject_activity = {
            "subject": {"id": subject.id, "name": subject.subject_name},
            "teacher": {
                "id": teacher.id,
                "name": teacher.full_name,
                "staff_id": teacher.staff_id,
            },
            "scores": {
                "total": len(students),
                "completed": scores_entered,
                "percentage": round(
                    (scores_entered / len(students) * 100) if len(students) > 0 else 0
                ),
                "status": get_completion_status(scores_entered, len(students)),
            },
            "last_activity": get_last_activity_date(
                teacher, class_obj, subject, selected_term
            ),
        }

        subject_activities.append(subject_activity)

    # Calculate class teacher activities (remarks and report cards)
    if class_teacher:
        remarks_entered = StudentTermRemarks.objects.filter(
            student__in=students, term=selected_term
        ).count()

        report_cards_generated = ReportCard.objects.filter(
            student__in=students, term=selected_term
        ).count()

        report_cards_approved = ReportCard.objects.filter(
            student__in=students, term=selected_term, is_approved=True
        ).count()

        class_teacher_activities = {
            "remarks": {
                "total": len(students),
                "completed": remarks_entered,
                "percentage": round(
                    (remarks_entered / len(students) * 100) if len(students) > 0 else 0
                ),
                "status": get_completion_status(remarks_entered, len(students)),
            },
            "report_cards": {
                "total": len(students),
                "completed": report_cards_generated,
                "percentage": round(
                    (report_cards_generated / len(students) * 100)
                    if len(students) > 0
                    else 0
                ),
                "approved": report_cards_approved,
                "approved_percentage": round(
                    (report_cards_approved / report_cards_generated * 100)
                    if report_cards_generated > 0
                    else 0
                ),
                "status": get_completion_status(report_cards_generated, len(students)),
            },
        }
    else:
        class_teacher_activities = None

    # Get all available academic years
    academic_years = AcademicYear.objects.filter(school=school).order_by("-start_date")

    # Get available terms for filtering - make sure to filter by both academic year and school
    terms = Term.objects.filter(
        academic_year=selected_academic_year, school=school
    ).order_by("start_date")

    context = {
        "class": class_obj,
        "class_teacher": class_teacher,
        "subject_activities": subject_activities,
        "class_teacher_activities": class_teacher_activities,
        "students": students,
        "student_count": len(students),
        "academic_years": academic_years,
        "selected_academic_year": selected_academic_year,
        "terms": terms,
        "selected_term": selected_term,
    }

    return render(request, "teacher_activity_monitoring/class_detail.html", context)


@login_required
@user_passes_test(is_admin_or_superadmin)
def send_activity_reminder(request, assignment_id=None):
    """Send reminder to teacher about pending activities"""
    if request.method == "POST":
        school = get_user_school(request.user)

        # Check if we're sending bulk reminders
        is_bulk = (
            "bulk_send" in request.POST and request.POST.get("bulk_send") == "true"
        )
        activity_type = request.POST.get("activity_type")

        # Validate activity type
        if activity_type not in ["scores", "remarks", "report_cards"]:
            messages.error(request, "Invalid activity type specified")
            return redirect("teacher_activity_monitoring")

        # Get redirect URL - either monitoring dashboard or specific detail page
        redirect_url = request.POST.get("redirect_url", "teacher_activity_monitoring")

        # Handle scheduling if enabled
        scheduled_date = request.POST.get("scheduled_date")
        if scheduled_date:
            try:
                from django.utils.dateparse import parse_datetime

                # Parse the scheduled date
                scheduled_datetime = parse_datetime(scheduled_date)
                if not scheduled_datetime:
                    # If only date was provided, set time to 8:00 AM
                    from datetime import datetime

                    date_obj = datetime.strptime(scheduled_date, "%Y-%m-%d").date()
                    from django.utils import timezone

                    scheduled_datetime = timezone.make_aware(
                        datetime.combine(date_obj, datetime.min.time().replace(hour=8))
                    )

                if is_bulk:
                    # Schedule bulk reminders
                    filter_params = {}

                    # Get filter parameters from the request
                    academic_year_id = request.POST.get("academic_year")
                    term_id = request.POST.get("term")
                    department_id = request.POST.get("department")
                    completion_status = request.POST.get("completion_status")

                    if academic_year_id:
                        filter_params["class_assigned__academic_year_id"] = (
                            academic_year_id
                        )

                    if department_id:
                        filter_params["teacher__department_id"] = department_id

                    # Create a scheduled reminder for bulk sending
                    ScheduledReminder.objects.create(
                        school=school,
                        creator=request.user,
                        scheduled_time=scheduled_datetime,
                        reminder_type="bulk_activity",
                        parameters={
                            "activity_type": activity_type,
                            "filters": filter_params,
                            "term_id": term_id,
                            "completion_status": completion_status,
                        },
                    )

                    messages.success(
                        request,
                        f"Bulk {activity_type.replace('_', ' ')} reminders scheduled for {scheduled_date}",
                    )
                else:
                    # Schedule single reminder
                    assignment = get_object_or_404(
                        TeacherSubjectAssignment,
                        id=assignment_id,
                        teacher__user__school=school,
                    )

                    ScheduledReminder.objects.create(
                        school=school,
                        creator=request.user,
                        scheduled_time=scheduled_datetime,
                        reminder_type="activity",
                        parameters={
                            "assignment_id": assignment_id,
                            "activity_type": activity_type,
                        },
                    )

                    messages.success(
                        request,
                        f"Reminder for {assignment.teacher.full_name} scheduled for {scheduled_date}",
                    )

                return redirect(redirect_url)

            except Exception as e:
                messages.error(request, f"Failed to schedule reminder: {str(e)}")
                return redirect(redirect_url)

        # Process immediate sending
        if is_bulk:
            # Handle bulk sending
            filter_params = {}

            # Get filter parameters from the request
            academic_year_id = request.POST.get("academic_year")
            term_id = request.POST.get("term")
            department_id = request.POST.get("department")
            completion_status = request.POST.get("completion_status")

            if academic_year_id:
                filter_params["class_assigned__academic_year_id"] = academic_year_id

            if department_id:
                filter_params["teacher__department_id"] = department_id

            # Get all matching assignments
            assignments = TeacherSubjectAssignment.objects.filter(
                teacher__user__school=school, **filter_params
            ).select_related("teacher", "class_assigned", "subject")

            # Get term
            if term_id:
                term = get_object_or_404(Term, id=term_id, school=school)
            else:
                term = get_current_term(school)

            if not term:
                messages.error(request, "No active term found")
                return redirect(redirect_url)

            # Track success and failures
            success_count = 0
            failure_count = 0
            skipped_count = 0

            # Process each assignment
            for assignment in assignments:
                # Skip if no email
                teacher = assignment.teacher
                teacher_email = (
                    teacher.user.email
                    if hasattr(teacher, "user") and teacher.user
                    else None
                )

                if not teacher_email:
                    skipped_count += 1
                    continue

                # Get class and subject
                class_obj = assignment.class_assigned
                subject = assignment.subject

                # Calculate completion status
                student_count = StudentClass.objects.filter(
                    assigned_class=class_obj, is_active=True
                ).count()

                # Skip if no students
                if student_count == 0:
                    skipped_count += 1
                    continue

                completion = {"total": student_count, "completed": 0, "percentage": 0}

                # Check completion based on activity type
                if activity_type == "scores":

                    # Exclude mock exam assessments from score entry monitoring

                    scores_entered = Assessment.objects.filter(
                        student__studentclass__assigned_class=class_obj,
                        class_subject__subject=subject,
                        class_subject__academic_year=term.academic_year,

                        class_subject__is_active=True,
                        term=term,
                        student__studentclass__is_active=True,
                    ).exclude(assessment_type='mock_exam').count()

                    completion["completed"] = scores_entered
                    completion["percentage"] = round(
                        (scores_entered / student_count * 100)
                        if student_count > 0
                        else 0
                    )
                    completion["status"] = get_completion_status(
                        scores_entered, student_count
                    )
                    activity_name = "Score Entry"

                    # Skip if doesn't match filter criteria
                    if completion_status and completion["status"] != completion_status:
                        skipped_count += 1
                        continue

                elif activity_type == "remarks":
                    # Only process if teacher is class teacher
                    is_class_teacher = ClassTeacher.objects.filter(
                        class_assigned=class_obj,
                        teacher=teacher,
                        academic_year=class_obj.academic_year,
                        is_active=True,
                    ).exists()

                    if not is_class_teacher:
                        skipped_count += 1
                        continue

                    remarks_entered = StudentTermRemarks.objects.filter(
                        student__studentclass__assigned_class=class_obj,
                        term=term,
                        student__studentclass__is_active=True,
                    ).count()
                    completion["completed"] = remarks_entered
                    completion["percentage"] = round(
                        (remarks_entered / student_count * 100)
                        if student_count > 0
                        else 0
                    )
                    completion["status"] = get_completion_status(
                        remarks_entered, student_count
                    )
                    activity_name = "Student Remarks"

                    # Skip if doesn't match filter criteria
                    if completion_status and completion["status"] != completion_status:
                        skipped_count += 1
                        continue

                elif activity_type == "report_cards":
                    # Only process if teacher is class teacher
                    is_class_teacher = ClassTeacher.objects.filter(
                        class_assigned=class_obj,
                        teacher=teacher,
                        academic_year=class_obj.academic_year,
                        is_active=True,
                    ).exists()

                    if not is_class_teacher:
                        skipped_count += 1
                        continue

                    report_cards_generated = ReportCard.objects.filter(
                        student__studentclass__assigned_class=class_obj,
                        term=term,
                        student__studentclass__is_active=True,
                    ).count()
                    completion["completed"] = report_cards_generated
                    completion["percentage"] = round(
                        (report_cards_generated / student_count * 100)
                        if student_count > 0
                        else 0
                    )
                    completion["status"] = get_completion_status(
                        report_cards_generated, student_count
                    )
                    activity_name = "Report Card Generation"

                    # Skip if doesn't match filter criteria
                    if completion_status and completion["status"] != completion_status:
                        skipped_count += 1
                        continue

                # Get school info
                school_info = school if school else SchoolInformation.get_active()
                school_name = (
                    school_info.name
                    if hasattr(school_info, "name")
                    else "School Management System"
                )
                site_url = getattr(settings, "SITE_URL", "http://localhost:8000")

                # Add deadline if term end date is available
                deadline = term.end_date if hasattr(term, "end_date") else None

                # Prepare email context
                context = {
                    "teacher": teacher,
                    "class_obj": class_obj,
                    "subject": subject,
                    "term": term,
                    "activity_type": activity_type,
                    "activity_type_name": activity_name,
                    "completion": completion,
                    "school_name": school_name,
                    "login_url": f"{site_url}{reverse_lazy('login')}",
                    "deadline": deadline,
                    "direct_link": f"{site_url}/teacher/dashboard/",
                    "is_bulk_reminder": True,
                }

                # Send the email
                success, message = send_activity_reminder_email(teacher_email, context)

                # Track results
                if success:
                    success_count += 1

                    # Log the reminder in ReminderLog if model exists
                    try:
                        ReminderLog.objects.create(
                            teacher=teacher,
                            class_assigned=class_obj,
                            subject=subject,
                            term=term,
                            activity_type=activity_type,
                            completion_percentage=completion["percentage"],
                            sent_by=request.user,
                            status="sent" if "disabled" not in message else "disabled",
                            message=message,
                        )
                    except (ImportError, Exception):
                        pass  # Model doesn't exist, skip logging
                else:
                    failure_count += 1

            # Show summary message
            if success_count > 0:
                messages.success(
                    request,
                    f"Successfully sent {success_count} reminders. Failed: {failure_count}. Skipped: {skipped_count}.",
                )
            else:
                messages.warning(
                    request,
                    f"No reminders were sent. Failed: {failure_count}. Skipped: {skipped_count}.",
                )

            return redirect(redirect_url)
        else:
            # Single reminder processing (original functionality)
            assignment = get_object_or_404(
                TeacherSubjectAssignment, id=assignment_id, teacher__user__school=school
            )

            # Get teacher email
            teacher = assignment.teacher
            teacher_email = (
                teacher.user.email
                if hasattr(teacher, "user") and teacher.user
                else None
            )

            if not teacher_email:
                messages.error(
                    request, f"No email found for teacher {teacher.full_name}"
                )
                return redirect(redirect_url)

            # Get activity details
            class_obj = assignment.class_assigned
            subject = assignment.subject
            term = get_current_term(school)

            # Calculate completion status based on activity type
            student_count = StudentClass.objects.filter(
                assigned_class=class_obj, is_active=True
            ).count()

            completion = {"total": student_count, "completed": 0, "percentage": 0}

            # Set activity name and calculate completion data
            if activity_type == "scores":
                activity_name = "Score Entry"

                # Exclude mock exam assessments from score entry monitoring

                scores_entered = Assessment.objects.filter(
                    student__studentclass__assigned_class=class_obj,
                    class_subject__subject=subject,
                    class_subject__academic_year=term.academic_year,

                    class_subject__is_active=True,
                    term=term,
                    student__studentclass__is_active=True,
                ).exclude(assessment_type='mock_exam').count()

                completion["completed"] = scores_entered
                completion["percentage"] = round(
                    (scores_entered / student_count * 100) if student_count > 0 else 0
                )
                completion["status"] = get_completion_status(
                    scores_entered, student_count
                )

            elif activity_type == "remarks":
                activity_name = "Student Remarks"
                remarks_entered = StudentTermRemarks.objects.filter(
                    student__studentclass__assigned_class=class_obj,
                    term=term,
                    student__studentclass__is_active=True,
                ).count()
                completion["completed"] = remarks_entered
                completion["percentage"] = round(
                    (remarks_entered / student_count * 100) if student_count > 0 else 0
                )
                completion["status"] = get_completion_status(
                    remarks_entered, student_count
                )

            elif activity_type == "report_cards":
                activity_name = "Report Card Generation"
                report_cards_generated = ReportCard.objects.filter(
                    student__studentclass__assigned_class=class_obj,
                    term=term,
                    student__studentclass__is_active=True,
                ).count()
                completion["completed"] = report_cards_generated
                completion["percentage"] = round(
                    (report_cards_generated / student_count * 100)
                    if student_count > 0
                    else 0
                )
                completion["status"] = get_completion_status(
                    report_cards_generated, student_count
                )

            else:
                messages.error(request, "Invalid activity type specified")
                return redirect(redirect_url)

            # Get school info
            school_info = school if school else SchoolInformation.get_active()
            school_name = (
                school_info.name
                if hasattr(school_info, "name")
                else "School Management System"
            )
            site_url = getattr(settings, "SITE_URL", "http://localhost:8000")

            # Add deadline if term end date is available
            deadline = term.end_date if hasattr(term, "end_date") else None

            # Prepare email context
            context = {
                "teacher": teacher,
                "class_obj": class_obj,
                "subject": subject,
                "term": term,
                "activity_type": activity_type,
                "activity_type_name": activity_name,
                "completion": completion,
                "school_name": school_name,
                "login_url": f"{site_url}{reverse_lazy('login')}",
                "deadline": deadline,
                "direct_link": f"{site_url}/teacher/dashboard/",
                "is_bulk_reminder": False,
            }

            # Send the email
            success, message = send_activity_reminder_email(teacher_email, context)

            # Log the reminder in ReminderLog if model exists
            try:
                ReminderLog.objects.create(
                    teacher=teacher,
                    class_assigned=class_obj,
                    subject=subject,
                    term=term,
                    activity_type=activity_type,
                    completion_percentage=completion["percentage"],
                    sent_by=request.user,
                    status=(
                        "sent"
                        if success and "disabled" not in message
                        else "failed" if not success else "disabled"
                    ),
                    message=message,
                )
            except (ImportError, Exception):
                pass  # Model doesn't exist, skip logging

            # Show appropriate message
            if success:
                if "disabled" in message:
                    messages.info(
                        request,
                        f"Email sending is disabled. A reminder for {teacher.full_name} about {activity_name} was processed but not sent.",
                    )
                elif "notification" in message:
                    messages.info(
                        request,
                        f"Email could not be sent to {teacher.full_name}, but an in-system notification was created.",
                    )
                else:
                    messages.success(
                        request,
                        f"Reminder sent to {teacher.full_name} about {activity_name} for {class_obj.name} {subject.subject_name}",
                    )
            else:
                # Check for common error patterns and provide helpful messages
                if "Gmail authentication" in message or "BadCredentials" in message:
                    messages.warning(
                        request,
                        f"Failed to send email to {teacher.full_name}: Gmail authentication failed. Please check the email settings and ensure 'Less secure app access' is enabled or use an App Password.",
                    )
                elif "Authentication" in message:
                    messages.warning(
                        request,
                        f"Failed to send email to {teacher.full_name}: Email authentication failed. Please check the email credentials in the system settings.",
                    )
                else:
                    messages.warning(
                        request,
                        f"Failed to send email to {teacher.full_name}: {message}",
                    )

                # Log the error for administrators
                import logging

                logger = logging.getLogger("shs_system.email")
                logger.error(f"Email send failure to {teacher_email}: {message}")

        return redirect(redirect_url)

    return redirect("teacher_activity_monitoring")


@login_required
@user_passes_test(is_admin_or_superadmin)
def view_reminder_logs(request):
    """View for displaying reminder logs"""
    school = get_user_school(request.user)

    # Get filter parameters
    teacher_id = request.GET.get("teacher")
    activity_type = request.GET.get("activity_type")
    status = request.GET.get("status")
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")

    # Base queryset
    reminder_logs = (
        ReminderLog.objects.filter(teacher__user__school=school)
        .select_related(
            "teacher",
            "class_assigned",
            "subject",
            "term",
            "sent_by",
            "scheduled_reminder",
        )
        .order_by("-sent_at")
    )

    # Apply filters
    if teacher_id:
        reminder_logs = reminder_logs.filter(teacher_id=teacher_id)

    if activity_type:
        reminder_logs = reminder_logs.filter(activity_type=activity_type)

    if status:
        reminder_logs = reminder_logs.filter(status=status)

    if date_from:
        from django.utils.dateparse import parse_date

        date_from_obj = parse_date(date_from)
        if date_from_obj:
            from django.utils import timezone
            from datetime import datetime, time

            date_from_dt = timezone.make_aware(
                datetime.combine(date_from_obj, time.min)
            )
            reminder_logs = reminder_logs.filter(sent_at__gte=date_from_dt)

    if date_to:
        from django.utils.dateparse import parse_date

        date_to_obj = parse_date(date_to)
        if date_to_obj:
            from django.utils import timezone
            from datetime import datetime, time

            date_to_dt = timezone.make_aware(datetime.combine(date_to_obj, time.max))
            reminder_logs = reminder_logs.filter(sent_at__lte=date_to_dt)

    # Pagination
    paginator = Paginator(reminder_logs, 20)  # Show 20 logs per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Get teachers for filter dropdown
    teachers = Teacher.objects.filter(user__school=school).order_by("full_name")

    context = {
        "page_obj": page_obj,
        "teachers": teachers,
        "activity_types": [
            ("scores", "Score Entry"),
            ("remarks", "Student Remarks"),
            ("report_cards", "Report Cards"),
        ],
        "statuses": [
            ("sent", "Sent"),
            ("failed", "Failed"),
            ("disabled", "Disabled"),
        ],
        "filters": {
            "teacher_id": teacher_id,
            "activity_type": activity_type,
            "status": status,
            "date_from": date_from,
            "date_to": date_to,
        },
    }

    return render(request, "teacher_activity_monitoring/reminder_logs.html", context)


# Helper functions
def get_completion_status(completed, total):
    """Determine completion status based on completed vs total items"""
    if total == 0:
        return "not_started"

    percentage = (completed / total) * 100

    if percentage == 0:
        return "not_started"
    elif percentage < 100:
        return "in_progress"
    else:
        return "completed"


def get_last_activity_date(teacher, class_obj, subject, term):
    """Get the date of last activity for this teacher-class-subject combination"""
    # Check for score entry activity

    # Exclude mock exam assessments from activity monitoring

    latest_score = (
        Assessment.objects.filter(
            student__studentclass__assigned_class=class_obj,
            class_subject__subject=subject,
            class_subject__academic_year=term.academic_year,

            class_subject__is_active=True,
            term=term,
            student__studentclass__is_active=True,
        ).exclude(assessment_type='mock_exam')

        .order_by("-date_recorded")
        .first()
    )

    # Check for remarks activity if teacher is class teacher
    is_class_teacher = ClassTeacher.objects.filter(
        class_assigned=class_obj,
        teacher=teacher,
        academic_year=class_obj.academic_year,
        is_active=True,
    ).exists()

    if is_class_teacher:
        latest_remarks = (
            StudentTermRemarks.objects.filter(
                student__studentclass__assigned_class=class_obj,
                term=term,
                student__studentclass__is_active=True,
            )
            .order_by("-last_updated")
            .first()
        )

        latest_report_card = (
            ReportCard.objects.filter(
                student__studentclass__assigned_class=class_obj,
                term=term,
                student__studentclass__is_active=True,
            )
            .order_by("-last_updated")
            .first()
        )
    else:
        latest_remarks = None
        latest_report_card = None

    # Find the most recent activity
    dates = []

    if latest_score:
        dates.append(latest_score.date_recorded)

    if latest_remarks:
        dates.append(latest_remarks.last_updated)

    if latest_report_card:
        dates.append(latest_report_card.last_updated)

    if dates:
        return max(dates)
    else:
        return None


def export_monitoring_csv(activities_data, term):
    """Export monitoring data to CSV"""
    # Create CSV file
    csv_buffer = StringIO()
    writer = csv.writer(csv_buffer)

    # Write header
    header = [
        "Teacher Name",
        "Staff ID",
        "Department",
        "Class",
        "Form/Grade",
        "Academic Year",
        "Subject",
        "Student Count",
        "Scores Completed",
        "Scores Percentage",
        "Scores Status",
        "Remarks Completed",
        "Remarks Percentage",
        "Remarks Status",
        "Report Cards Completed",
        "Report Cards Percentage",
        "Report Cards Status",
        "Last Activity Date",
    ]
    writer.writerow(header)

    # Write data rows
    for activity in activities_data:
        teacher = activity["teacher"]
        class_info = activity["class"]
        subject = activity["subject"]
        scores = activity["scores"]
        remarks = activity["remarks"]
        report_cards = activity["report_cards"]

        row = [
            teacher["name"],
            teacher["staff_id"],
            teacher["department"],
            class_info["name"],
            class_info["form"],
            class_info["academic_year"],
            subject["name"],
            class_info["student_count"],
            scores["completed"],
            f"{scores['percentage']}%",
            scores["status"],
            remarks["completed"] if remarks else "N/A",
            f"{remarks['percentage']}%" if remarks else "N/A",
            remarks["status"] if remarks else "N/A",
            report_cards["completed"] if report_cards else "N/A",
            f"{report_cards['percentage']}%" if report_cards else "N/A",
            report_cards["status"] if report_cards else "N/A",
            (
                activity["last_activity"].strftime("%Y-%m-%d %H:%M")
                if activity["last_activity"]
                else "Never"
            ),
        ]
        writer.writerow(row)

    # Create response
    response = HttpResponse(csv_buffer.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="teacher_activities_{term}_{timezone.now().strftime("%Y%m%d")}.csv"'
    )

    return response


def send_bulk_activity_reminder(
    teacher_ids=None,
    activity_type=None,
    class_id=None,
    subject_id=None,
    term_id=None,
    message="",
    sender=None,
    scheduled_reminder=None,
):
    """
    Send bulk activity reminders to multiple teachers

    Args:
        teacher_ids (list): List of teacher IDs to send reminders to
        activity_type (str): Type of activity (scores, remarks, report_cards)
        class_id (int, optional): Filter by class ID
        subject_id (int, optional): Filter by subject ID
        term_id (int, optional): Term ID for the reminders
        message (str, optional): Custom message to include in the reminder
        sender (User, optional): User who initiated the reminder
        scheduled_reminder (ScheduledReminder, optional): The scheduled reminder object

    Returns:
        dict: Results with success, failure and skipped counts
    """
    from django.conf import settings
    from django.urls import reverse_lazy
    from ..utils import send_activity_reminder_email

    results = {
        "success_count": 0,
        "failure_count": 0,
        "skipped_count": 0,
        "messages": [],
    }

    # Validate activity type
    if activity_type not in ["scores", "remarks", "report_cards"]:
        results["messages"].append(f"Invalid activity type: {activity_type}")
        return results

    # Get teachers
    teachers = Teacher.objects.filter(id__in=teacher_ids) if teacher_ids else []
    if not teachers:
        results["messages"].append("No teachers specified for reminders")
        return results

    # Get term
    if term_id:
        try:
            term = Term.objects.get(id=term_id)
        except Term.DoesNotExist:
            results["messages"].append(f"Term with ID {term_id} not found")
            return results
    else:
        # Try to get current term from first teacher's school
        school = teachers.first().user.school if teachers.first().user else None
        term = get_current_term(school)
        if not term:
            results["messages"].append("No active term found")
            return results

    # Get class and subject if specified
    class_obj = None
    subject = None

    if class_id:
        try:
            class_obj = Class.objects.get(id=class_id)
        except Class.DoesNotExist:
            results["messages"].append(f"Class with ID {class_id} not found")
            return results

    if subject_id:
        try:
            subject = Subject.objects.get(id=subject_id)
        except Subject.DoesNotExist:
            results["messages"].append(f"Subject with ID {subject_id} not found")
            return results

    # Process each teacher
    for teacher in teachers:
        # Skip if no email
        teacher_email = (
            teacher.user.email if hasattr(teacher, "user") and teacher.user else None
        )
        if not teacher_email:
            results["skipped_count"] += 1
            continue

        # Get assignments for this teacher
        query = Q(teacher=teacher)
        if class_obj:
            query &= Q(class_assigned=class_obj)
        if subject:
            query &= Q(subject=subject)

        assignments = TeacherSubjectAssignment.objects.filter(query)
        if not assignments.exists():
            results["skipped_count"] += 1
            continue

        # Use the first assignment for the email context
        assignment = assignments.first()
        class_obj = assignment.class_assigned
        subject = assignment.subject

        # Calculate completion status
        student_count = StudentClass.objects.filter(
            assigned_class=class_obj, is_active=True
        ).count()

        # Skip if no students
        if student_count == 0:
            results["skipped_count"] += 1
            continue

        completion = {"total": student_count, "completed": 0, "percentage": 0}

        # Check completion based on activity type
        if activity_type == "scores":

            # Exclude mock exam assessments from score entry monitoring

            scores_entered = Assessment.objects.filter(
                student__studentclass__assigned_class=class_obj,
                class_subject__subject=subject,
                class_subject__academic_year=term.academic_year,

                class_subject__is_active=True,
                term=term,
                student__studentclass__is_active=True,
            ).exclude(assessment_type='mock_exam').count()

            completion["completed"] = scores_entered
            completion["percentage"] = round(
                (scores_entered / student_count * 100) if student_count > 0 else 0
            )
            completion["status"] = get_completion_status(scores_entered, student_count)
            activity_name = "Score Entry"

        elif activity_type == "remarks":
            # Only process if teacher is class teacher
            is_class_teacher = ClassTeacher.objects.filter(
                class_assigned=class_obj,
                teacher=teacher,
                academic_year=class_obj.academic_year,
                is_active=True,
            ).exists()

            if not is_class_teacher:
                results["skipped_count"] += 1
                continue

            remarks_entered = StudentTermRemarks.objects.filter(
                student__studentclass__assigned_class=class_obj,
                term=term,
                student__studentclass__is_active=True,
            ).count()
            completion["completed"] = remarks_entered
            completion["percentage"] = round(
                (remarks_entered / student_count * 100) if student_count > 0 else 0
            )
            completion["status"] = get_completion_status(remarks_entered, student_count)
            activity_name = "Student Remarks"

        elif activity_type == "report_cards":
            # Only process if teacher is class teacher
            is_class_teacher = ClassTeacher.objects.filter(
                class_assigned=class_obj,
                teacher=teacher,
                academic_year=class_obj.academic_year,
                is_active=True,
            ).exists()

            if not is_class_teacher:
                results["skipped_count"] += 1
                continue

            report_cards_generated = ReportCard.objects.filter(
                student__studentclass__assigned_class=class_obj,
                term=term,
                student__studentclass__is_active=True,
            ).count()
            completion["completed"] = report_cards_generated
            completion["percentage"] = round(
                (report_cards_generated / student_count * 100)
                if student_count > 0
                else 0
            )
            completion["status"] = get_completion_status(
                report_cards_generated, student_count
            )
            activity_name = "Report Card Generation"

        # Get school info
        school = (
            teacher.user.school if hasattr(teacher, "user") and teacher.user else None
        )
        school_info = school if school else SchoolInformation.get_active()
        school_name = (
            school_info.name
            if hasattr(school_info, "name")
            else "School Management System"
        )
        site_url = getattr(settings, "SITE_URL", "http://localhost:8000")

        # Add deadline if term end date is available
        deadline = term.end_date if hasattr(term, "end_date") else None

        # Prepare email context
        context = {
            "teacher": teacher,
            "class_obj": class_obj,
            "subject": subject,
            "term": term,
            "activity_type": activity_type,
            "activity_type_name": activity_name,
            "completion": completion,
            "school_name": school_name,
            "login_url": f"{site_url}{reverse_lazy('login')}",
            "deadline": deadline,
            "direct_link": f"{site_url}/teacher/dashboard/",
            "is_bulk_reminder": True,
            "custom_message": message if message else None,
            "scheduled": scheduled_reminder is not None,
            "scheduled_time": (
                scheduled_reminder.scheduled_time if scheduled_reminder else None
            ),
        }

        # Send the email
        success, message_result = send_activity_reminder_email(teacher_email, context)

        # Track results
        if success:
            results["success_count"] += 1

            # Log the reminder
            try:
                ReminderLog.objects.create(
                    teacher=teacher,
                    class_assigned=class_obj,
                    subject=subject,
                    term=term,
                    activity_type=activity_type,
                    completion_percentage=completion["percentage"],
                    sent_by=sender,
                    status="sent" if "disabled" not in message_result else "disabled",
                    message=message_result,
                    scheduled_reminder=scheduled_reminder,
                )
            except Exception as e:
                results["messages"].append(f"Failed to log reminder: {str(e)}")
        else:
            results["failure_count"] += 1
            results["messages"].append(
                f"Failed to send to {teacher.full_name}: {message_result}"
            )

    return results
