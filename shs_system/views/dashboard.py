from shs_system.models import (
    SchoolInformation,
    Assessment,
    Teacher,
    Class,
    Subject,
    AcademicYear,
    Term,
    ClassTeacher,
    Form,
    Student,
    AttendanceRecord,
    SchoolInformation,
    Department,
    LearningArea,
    StudentClass,
    Assessment,
    ClassSubject,
    ReportCard,
)
from django.db.models import Q, Avg, Count, Case, When, IntegerField, F

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout, authenticate, login, update_session_auth_hash
from django.contrib.auth.decorators import (
    login_required,
    user_passes_test,
    permission_required,
)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta, datetime
import json
from ..utils import get_teacher_monitoring_data
import logging
from django.urls import reverse, NoReverseMatch
from django.http import HttpResponse
import traceback
from django.http import JsonResponse

logger = logging.getLogger("shs_system.dashboard")


# Add this new function to debug URL resolution
def debug_dashboard_urls(request):
    """Debug view to test URL resolution for dashboard URLs"""
    info = []

    # Test resolving all dashboard URLs
    dashboard_urls = [
        "dashboard",
        "admin_dashboard",
        "teacher_dashboard",
        "student_dashboard",
    ]

    info.append("<h2>URL Resolution Test</h2>")

    for url_name in dashboard_urls:
        try:
            resolved_url = reverse(url_name)
            info.append(f"✅ URL '{url_name}' resolves to: {resolved_url}")
        except NoReverseMatch as e:
            info.append(f"❌ URL '{url_name}' failed to resolve: {str(e)}")

    # Add request information
    info.append("<h2>Request Information</h2>")
    info.append(f"Host: {request.get_host()}")
    info.append(f"Path: {request.path}")
    info.append(f"User: {request.user}")
    info.append(f"Authenticated: {request.user.is_authenticated}")

    if request.user.is_authenticated:
        info.append(f"Username: {request.user.username}")
        info.append(f"Role: {request.user.role}")
        info.append(f"School: {getattr(request.user, 'school', None)}")

    # Add school context information
    info.append("<h2>School Context</h2>")
    info.append(f"School context: {getattr(request, 'school', None)}")

    if hasattr(request, "school") and request.school:
        info.append(f"School name: {request.school.name}")
        info.append(f"School slug: {request.school.slug}")

    return HttpResponse("<br>".join(info))


# Admin Dashboard
@login_required
def admin_dashboard(request):
    if request.user.role != "admin":
        return render(request, "errors/403.html", status=403)

    # Get the current school information based on the user's school
    school_info = request.user.school
    if not school_info:
        messages.error(request, "No school associated with your account.")
        return redirect("login")

    # Get the current academic year and term for this school
    current_academic_year = SchoolInformation.get_current_academic_year(
        school=school_info
    )
    current_term = SchoolInformation.get_current_term(school=school_info)

    # Calculate term progress if current term exists
    term_progress = 0
    if current_term:
        today = timezone.now().date()

        # Make sure we don't go beyond 100% even if current date is past end date
        if today >= current_term.end_date:
            term_progress = 100
        elif today <= current_term.start_date:
            term_progress = 0
        else:
            term_duration = (current_term.end_date - current_term.start_date).days
            days_passed = (today - current_term.start_date).days
            term_progress = min(round((days_passed / term_duration) * 100), 100)

    # Student Statistics - filtered by school directly
    students = Student.objects.filter(school=school_info)
    total_students = students.count()

    # Get all forms from the Form model - filtered by school
    forms = Form.objects.filter(school=school_info)

    # Get all learning areas for distribution chart - filtered by school
    learning_areas = LearningArea.objects.filter(school=school_info)

    # Organize students by form
    students_by_form = {}
    for form in forms:
        count = students.filter(
            studentclass__assigned_class__form=form, studentclass__is_active=True
        ).count()
        students_by_form[form.form_number] = count

    # Organize students by learning area
    students_by_learning_area = {}
    for area in learning_areas:
        count = students.filter(
            studentclass__assigned_class__learning_area=area,
            studentclass__is_active=True,
        ).count()
        students_by_learning_area[area.name] = count

    # Class Statistics - filtered by school's current academic year and school
    classes = Class.objects.filter(
        academic_year=current_academic_year, school=school_info
    )
    total_classes = classes.count()

    classes_by_form = {}
    for form in forms:
        count = classes.filter(form=form).count()
        classes_by_form[form.form_number] = count

    # Teacher Statistics - filtered by school directly
    teachers = Teacher.objects.filter(school=school_info)
    total_teachers = teachers.count()

    # Subject Statistics - filtered by school
    subjects = Subject.objects.filter(school=school_info)
    total_subjects = subjects.count()
    subjects_by_area = subjects.values("learning_area__name").annotate(
        count=Count("id")
    )

    # Academic Performance - filtered by school
    performance_data = {"avg_score": 0, "passing_count": 0, "total_count": 0}
    passing_rate = 0
    failing_rate = 0

    if current_term:
        # Filter by academic year, term and school

        # Exclude mock exam assessments from dashboard performance data
        performance_data = Assessment.objects.filter(
            class_subject__academic_year=current_term.academic_year,
            class_subject__is_active=True,
            term=current_term,
            student__school=school_info,
            class_subject__class_name__school=school_info,
        ).exclude(assessment_type='mock_exam').aggregate(

            avg_score=Avg("total_score"),
            passing_count=Count("id", filter=Q(total_score__gte=40)),
            total_count=Count("id"),
        )

        if performance_data["total_count"] > 0:
            passing_rate = (
                performance_data["passing_count"]
                / performance_data["total_count"]
                * 100
            )
            failing_rate = 100 - passing_rate

    # Attendance Statistics - filtered by school directly
    attendance_rate = 0
    if current_term:
        attendance_data = AttendanceRecord.objects.filter(
            term=current_term, student__school=school_info, school=school_info
        ).aggregate(
            present_count=Count("id", filter=Q(is_present=True)),
            total_count=Count("id"),
        )

        if attendance_data["total_count"] > 0:
            attendance_rate = (
                attendance_data["present_count"] / attendance_data["total_count"] * 100
            )

    # Get recent activities - filtered by school directly
    recent_activities = []
    try:
        # Try to get the last 5 assessments as a proxy for recent activities
        recent_assessments = (
            Assessment.objects.select_related("student", "class_subject", "recorded_by")

            .filter(student__school=school_info, school=school_info, term=current_term, class_subject__is_active=True)

            .order_by("-date_recorded")[:5]
        )

        for assessment in recent_assessments:
            recent_activities.append(
                {
                    "action": "Assessment Recorded",
                    "description": f"{assessment.student.full_name} - {assessment.class_subject.subject.subject_name}",
                    "user": assessment.recorded_by.username,
                    "timestamp": assessment.date_recorded,
                }
            )
    except Exception as e:
        # Log the error but continue
        logger.error(f"Error fetching recent activities: {str(e)}")
        # If Assessment model doesn't exist or has issues, provide empty list
        pass

    context = {
        "title": "Admin Dashboard",
        "school_info": school_info,
        "current_academic_year": current_academic_year,
        "current_term": current_term,
        "term_progress": term_progress,
        "total_students": total_students,
        "total_teachers": total_teachers,
        "total_classes": total_classes,
        "total_subjects": total_subjects,
        "students_by_form": students_by_form,
        "students_by_learning_area": students_by_learning_area,
        "classes_by_form": classes_by_form,
        "subjects_by_area": subjects_by_area,
        "avg_score": round(performance_data["avg_score"] or 0, 2),
        "passing_rate": round(passing_rate, 2),
        "failing_rate": round(failing_rate, 2),
        "attendance_rate": round(attendance_rate, 2),
        "user": request.user,
        "recent_activities": recent_activities,
    }
    return render(request, "dashboard/admin_dashboard.html", context)


# Teacher Dashboard
@login_required
def teacher_dashboard(request):
    if request.user.role != "teacher":
        return render(request, "errors/403.html", status=403)
    # Fetch teacher-specific data (e.g., assigned classes)
    teacher = request.user.teacher_profile

    # Get the current school information based on the user's school
    school_info = request.user.school
    if not school_info:
        messages.error(request, "No school associated with your account.")
        return redirect("login")

    # Get current academic year and term for this school
    current_academic_year = SchoolInformation.get_current_academic_year(
        school=school_info
    )
    current_term = SchoolInformation.get_current_term(school=school_info)

    # Calculate term progress if current term exists
    term_progress = 0
    if current_term:
        today = timezone.now().date()

        # Make sure we don't go beyond 100% even if current date is past end date
        if today >= current_term.end_date:
            term_progress = 100
        elif today <= current_term.start_date:
            term_progress = 0
        else:
            term_duration = (current_term.end_date - current_term.start_date).days
            days_passed = (today - current_term.start_date).days
            term_progress = min(round((days_passed / term_duration) * 100), 100)

    # Get all teacher's subject assignments - filtered by teacher's school directly
    assigned_classes = teacher.teachersubjectassignment_set.filter(
        is_active=True,
        academic_year=current_academic_year,
        teacher__school=school_info,
        school=school_info,
    ).select_related("class_assigned", "subject")

    # Get class teacher assignments - filtered by school directly
    class_teacher_assignments = ClassTeacher.objects.filter(
        teacher=teacher,
        is_active=True,
        academic_year=current_academic_year,
        teacher__school=school_info,
        school=school_info,
    ).select_related("class_assigned")

    # Calculate statistics from assignments and assessments
    class_count = assigned_classes.values("class_assigned").distinct().count()
    subject_count = assigned_classes.values("subject").distinct().count()
    student_count = 0

    # Get unique classes taught by the teacher
    unique_classes = assigned_classes.values_list(
        "class_assigned", flat=True
    ).distinct()

    # Count students in all classes taught by this teacher - filtered by school directly
    if unique_classes:
        student_count = StudentClass.objects.filter(
            assigned_class__in=unique_classes,
            is_active=True,
            student__school=school_info,
            school=school_info,
        ).count()

    # Get assessment statistics - filtered by school
    assessment_data = {}
    recent_assessments = []

    # We still check for current_term for other parts of the dashboard even though ClassSubject no longer has a term field
    if current_term:
        # Get class subjects through TeacherSubjectAssignment
        # First get the teacher's assignments - filtered by school directly

        teacher_assignments_query = teacher.teachersubjectassignment_set.filter(

            academic_year=current_academic_year,
            is_active=True,
            teacher__school=school_info,
            school=school_info,
        ).select_related("class_assigned", "subject")


        # Filter out assignments where ClassSubject is not active
        # Get active class-subject combinations
        active_class_subjects = ClassSubject.objects.filter(
            academic_year=current_academic_year, is_active=True
        ).values_list('class_name_id', 'subject_id')
        
        # Filter assignments to only include those with active ClassSubject
        filtered_assignments = []
        for assignment in teacher_assignments_query:
            if (assignment.class_assigned.id, assignment.subject.id) in active_class_subjects:
                filtered_assignments.append(assignment)
        
        teacher_assignments = filtered_assignments


        # Then find class subjects matching those assignments
        class_subject_mappings = []
        for assignment in teacher_assignments:
            # Note: No longer filtering by term since the field has been removed
            # Add school filter to ClassSubject query
            class_subject = ClassSubject.objects.filter(
                class_name=assignment.class_assigned,
                subject=assignment.subject,
                academic_year=current_academic_year,
                school=school_info,

                is_active=True,

            ).first()

            if class_subject:
                class_subject_mappings.append(class_subject)

        # Now process each class subject for assessment data
        for class_subject in class_subject_mappings:

            # Exclude mock exam assessments from dashboard recent assessments

            assessments = Assessment.objects.filter(
                class_subject=class_subject,
                term=current_term,
                student__school=school_info,
                school=school_info,

            ).exclude(assessment_type='mock_exam').select_related("student")


            # Get the latest 5 assessments across all subjects
            if len(recent_assessments) < 5:
                latest = assessments.order_by("-date_recorded")[
                    : 5 - len(recent_assessments)
                ]
                for assessment in latest:
                    recent_assessments.append(
                        {
                            "student_name": assessment.student.full_name,
                            "class_name": class_subject.class_name.name,
                            "subject_name": class_subject.subject.subject_name,
                            "total_score": assessment.total_score,
                            "date": assessment.date_recorded,
                        }
                    )

            # Get grade distribution
            total_assessments = assessments.count()
            if total_assessments > 0:
                excellent = assessments.filter(total_score__gte=75).count()
                very_good = assessments.filter(
                    total_score__gte=70, total_score__lt=75
                ).count()
                good = assessments.filter(
                    total_score__gte=60, total_score__lt=70
                ).count()
                pass_count = assessments.filter(
                    total_score__gte=40, total_score__lt=60
                ).count()
                fail = assessments.filter(total_score__lt=40).count()

                # Calculate average score
                avg_score = assessments.aggregate(avg=Avg("total_score"))["avg"] or 0

                # Store data for this class subject
                assessment_data[class_subject.id] = {
                    "class_name": class_subject.class_name.name,
                    "subject_name": class_subject.subject.subject_name,
                    "total_assessments": total_assessments,
                    "excellent": excellent,
                    "very_good": very_good,
                    "good": good,
                    "pass": pass_count,
                    "fail": fail,
                    "avg_score": round(avg_score, 2),
                }

    # Sort recent assessments by date
    recent_assessments = sorted(
        recent_assessments, key=lambda x: x["date"], reverse=True
    )[:5]

    # Get upcoming or active terms - filtered by school's academic year and school
    upcoming_terms = Term.objects.filter(
        academic_year=current_academic_year,
        start_date__gte=timezone.now().date(),
        school=school_info,
    ).order_by("start_date")

    context = {
        "title": "Teacher Dashboard",
        "user": request.user,
        "teacher": teacher,
        "school_info": school_info,
        "assigned_classes": assigned_classes,
        "class_teacher_assignments": class_teacher_assignments,
        "class_count": class_count,
        "subject_count": subject_count,
        "student_count": student_count,
        "assessment_data": assessment_data,
        "recent_assessments": recent_assessments,
        "current_academic_year": current_academic_year,
        "current_term": current_term,
        "upcoming_terms": upcoming_terms,
        "term_progress": term_progress,
    }
    return render(request, "dashboard/teacher_dashboard.html", context)


# Student Dashboard
@login_required
def student_dashboard(request):
    if request.user.role != "student":
        return render(request, "errors/403.html", status=403)  # Forbidden page

    # Fetch student-specific data (e.g., current class, scores)
    student = request.user.student_profile

    # Get the student's school
    school_info = request.user.school
    if not school_info:
        messages.error(request, "No school associated with your account.")
        return redirect("login")

    current_class = student.get_current_class()

    # Get current term for filtering assessments
    current_term = SchoolInformation.get_current_term(school=school_info)

    # Filter assessments by student's school and current term

    # Exclude mock exam assessments from student dashboard

    assessments = Assessment.objects.filter(
        student=student,
        student__school=school_info,
        school=school_info,
        term=current_term,

        class_subject__is_active=True,
    ).exclude(assessment_type='mock_exam').select_related("class_subject")


    # Get report cards for this student - filtered by school directly
    report_cards = ReportCard.objects.filter(
        student=student, student__school=school_info, school=school_info
    ).order_by("-academic_year", "-term__term_number")[
        :5
    ]  # Limit to the 5 most recent report cards

    context = {
        "title": "Student Dashboard",
        "user": request.user,
        "student": student,  # Ensure student profile is in context
        "current_class": current_class,
        "assessments": assessments,
        "recent_report_cards": report_cards,
        "school_info": school_info,
    }
    return render(request, "dashboard/student_dashboard.html", context)


@login_required
def student_profile(request):
    """
    View for displaying the student's profile page with options to update
    profile information
    """
    if request.user.role != "student":
        return render(request, "errors/403.html", status=403)  # Forbidden page

    # Get student profile from user
    student = request.user.student_profile

    # Get the student's school
    school_info = request.user.school
    if not school_info:
        messages.error(request, "No school associated with your account.")
        return redirect("login")

    current_class = student.get_current_class()

    # Get report cards for this student - filtered by school directly
    report_cards = ReportCard.objects.filter(
        student=student, student__school=school_info, school=school_info
    ).order_by("-academic_year", "-term__term_number")[
        :5
    ]  # Limit to the 5 most recent report cards

    context = {
        "title": "Student Profile",
        "user": request.user,
        "student": student,
        "current_class": current_class,
        "recent_report_cards": report_cards,
        "school_info": school_info,
    }

    return render(request, "student/student_profile.html", context)


@login_required
def student_update_profile(request):
    """
    View for students to update their own profile information.

    Handles both form submission and AJAX requests for updating profile details.
    Includes support for profile picture uploads.
    """
    if request.user.role != "student" or not request.user.student_profile:
        return render(request, "errors/403.html", status=403)

    student = request.user.student_profile

    if request.method == "POST":
        try:
            # Extract form data
            full_name = request.POST.get("full_name", "").strip()
            email = request.POST.get("email", "").strip()

            # Validate required fields
            if not full_name:
                return JsonResponse(
                    {"status": "error", "message": "Full name is required"}, status=400
                )

            # Update student information
            student.full_name = full_name

            # Handle profile picture upload
            if request.FILES and "profile_picture" in request.FILES:
                student.profile_picture = request.FILES["profile_picture"]

            # Save student model
            student.save()

            # Update user account if email is provided
            if email and request.user.email != email:
                request.user.email = email
                request.user.username = email  # Keep username in sync with email
                request.user.save()

            # For AJAX requests
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {
                        "status": "success",
                        "message": "Profile updated successfully.",
                    }
                )

            # For regular form submissions
            messages.success(request, "Your profile has been updated successfully.")
            return redirect("student_profile")

        except Exception as e:
            # Log the error
            logger = logging.getLogger(__name__)
            logger.error(f"Error updating student profile: {str(e)}", exc_info=True)

            # For AJAX requests
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {"status": "error", "message": f"Error updating profile: {str(e)}"},
                    status=500,
                )

            # For regular form submissions
            messages.error(request, f"Error updating profile: {str(e)}")
            return redirect("student_profile")

    # For GET requests
    return redirect("student_profile")


def is_admin(user):
    return user.is_authenticated and user.role == "admin"


@login_required
@user_passes_test(is_admin)
def dashboard(request):
    """
    Admin dashboard with academic year and term overview
    """
    # Get user's school
    school_info = request.user.school
    if not school_info:
        messages.error(request, "No school associated with your account.")
        return redirect("login")

    # Get current academic year and terms for this school
    current_academic_year = SchoolInformation.get_current_academic_year(
        school=school_info
    )
    current_term = (
        SchoolInformation.get_current_term(school=school_info)
        if current_academic_year
        else None
    )

    # Get counts for quick stats - filtered by school directly
    academic_years_count = (
        AcademicYear.objects.filter(school=school_info).distinct().count()
    )

    terms_count = Term.objects.filter(school=school_info).distinct().count()

    # Recent academic years - filtered by school directly
    recent_academic_years = (
        AcademicYear.objects.filter(school=school_info)
        .distinct()
        .order_by("-start_date")[:5]
    )

    context = {
        "current_academic_year": current_academic_year,
        "current_term": current_term,
        "academic_years_count": academic_years_count,
        "terms_count": terms_count,
        "recent_academic_years": recent_academic_years,
        "active_menu": "dashboard",
        "title": "Academic Admin Dashboard",
        "school_info": school_info,
    }

    return render(request, "dashboard/admin_dashboard.html", context)


@login_required
def teacher_monitoring(request):
    """
    Admin view for monitoring teacher activities related to:
    - Score entry
    - Remarks entry
    - Attendance recording

    This view is multi-tenant aware and filters all data by the user's school.
    """
    logger = logging.getLogger("shs_system.teacher_monitoring")
    logger.info(f"Teacher monitoring view accessed by {request.user.username}")

    if request.user.role != "admin":
        logger.warning(
            f"Non-admin user {request.user.username} attempted to access teacher monitoring"
        )
        messages.error(request, "You do not have permission to access this page.")
        return redirect("dashboard")

    # Get user's school for multi-tenancy
    school_info = request.user.school
    if not school_info:
        logger.error(f"User {request.user.username} has no school assignment")
        messages.error(
            request,
            "No school associated with your account. Multi-tenancy requires a school assignment.",
        )
        return redirect("login")

    logger.info(
        f"Processing teacher monitoring for school: {school_info.name} (ID: {school_info.id})"
    )

    # Get filter parameters
    academic_year_id = request.GET.get("academic_year")
    term_id = request.GET.get("term")
    teacher_id = request.GET.get("teacher")
    debug_mode = request.GET.get("debug") == "1"  # Check if debug mode is enabled

    logger.debug(
        f"Filter parameters - Academic Year: {academic_year_id}, Term: {term_id}, Teacher: {teacher_id}, Debug: {debug_mode}"
    )

    # Set up filters based on parameters - all filtered by school
    academic_year = None
    term = None
    teachers = None
    debug_info = None

    if academic_year_id:
        try:
            # Filter academic year by school
            academic_year = AcademicYear.objects.get(
                id=academic_year_id, school=school_info
            )
            logger.debug(f"Found academic year: {academic_year.name}")
        except AcademicYear.DoesNotExist:
            logger.warning(
                f"Academic year ID {academic_year_id} not found for school {school_info.name}"
            )
            messages.error(request, "Selected academic year not found for your school.")

    if term_id:
        try:
            # Filter term by school
            term = Term.objects.get(id=term_id, school=school_info)
            logger.debug(f"Found term: {term}")

            # Ensure term belongs to selected academic year if both are specified
            if academic_year and term.academic_year != academic_year:
                logger.warning(
                    f"Term {term.id} does not belong to academic year {academic_year.id}"
                )
                messages.warning(
                    request,
                    "Selected term does not belong to the selected academic year.",
                )
                term = None
        except Term.DoesNotExist:
            logger.warning(f"Term ID {term_id} not found for school {school_info.name}")
            messages.error(request, "Selected term not found for your school.")

    if teacher_id:
        try:
            # Filter teacher by the user's school
            teacher = Teacher.objects.get(id=teacher_id, school=school_info)
            teachers = [teacher]
            logger.debug(f"Found teacher: {teacher.full_name}")

            # If debug mode is enabled and a specific teacher is selected, get detailed debug info
            if debug_mode:
                from ..utils import debug_teacher_relationships

                debug_info = debug_teacher_relationships(
                    teacher, school=school_info, academic_year=academic_year, term=term
                )
                logger.debug(f"Debug info generated for teacher {teacher.full_name}")
        except Teacher.DoesNotExist:
            logger.warning(
                f"Teacher ID {teacher_id} not found for school {school_info.name}"
            )
            messages.error(request, "Selected teacher not found in your school.")

    try:
        # Get monitoring data - pass school_info to the utility function
        # This ensures all data is filtered by school
        logger.info(
            f"Calling get_teacher_monitoring_data with school {school_info.name}"
        )
        monitoring_data = get_teacher_monitoring_data(
            academic_year=academic_year,
            term=term,
            teachers=teachers,
            school=school_info,
        )

        # Log summary information
        logger.info(
            f"Teacher monitoring summary for school {school_info.name}: {monitoring_data['summary']}"
        )

        # Check if we have any teacher data
        if not monitoring_data["teacher_data"]:
            logger.warning(
                f"No teacher data found for school {school_info.name} with the selected filters"
            )
            messages.warning(
                request,
                "No teacher data found for the selected filters in your school.",
            )
    except Exception as e:
        logger.error(
            f"Error generating teacher monitoring data for school {school_info.name}: {str(e)}"
        )
        logger.error(traceback.format_exc())
        messages.error(request, f"Error generating monitoring data: {str(e)}")
        monitoring_data = {
            "academic_year": academic_year,
            "term": term,
            "teacher_data": [],
            "summary": {
                "total_teachers": 0,
                "scores_completed": 0,
                "remarks_completed": 0,
                "attendance_completed": 0,
            },
        }

    # Prepare context for template - filter all querysets by school directly
    try:
        academic_years = list(
            AcademicYear.objects.filter(school=school_info)
            .distinct()
            .order_by("-start_date")
        )

        terms = list(
            Term.objects.filter(school=school_info)
            .distinct()
            .order_by("-academic_year__start_date", "term_number")
        )

        teachers_list = list(
            Teacher.objects.filter(school=school_info).order_by("full_name")
        )

        logger.debug(
            f"Found {len(academic_years)} academic years, {len(terms)} terms, {len(teachers_list)} teachers"
        )

        context = {
            "monitoring_data": monitoring_data,
            "academic_years": academic_years,
            "terms": terms,
            "teachers": teachers_list,
            "selected_academic_year": academic_year,
            "selected_term": term,
            "selected_teacher": teacher_id,
            "active_link": "teacher_monitoring",
            "school_info": school_info,
            "debug_mode": debug_mode,
            "debug_info": debug_info,
        }
    except Exception as e:
        logger.error(f"Error preparing context data: {str(e)}")
        logger.error(traceback.format_exc())
        messages.error(request, f"Error loading filter options: {str(e)}")
        # Provide minimal context if there's an error
        context = {
            "monitoring_data": monitoring_data,
            "academic_years": [],
            "terms": [],
            "teachers": [],
            "selected_academic_year": None,
            "selected_term": None,
            "selected_teacher": None,
            "active_link": "teacher_monitoring",
            "school_info": school_info,
            "debug_mode": debug_mode,
            "debug_info": debug_info,
        }

    return render(request, "teacher_monitoring.html", context)
