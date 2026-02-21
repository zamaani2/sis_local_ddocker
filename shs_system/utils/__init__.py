# utils package initialization

from decimal import Decimal

from ..models import PerformanceRequirement, Assessment, Term, SchoolInformation, ClassSubject



def is_admin_or_superadmin(user):
    """
    Check if the user is an admin or superadmin.

    Args:
        user: User object to check

    Returns:
        bool: True if user is admin or superadmin, False otherwise
    """
    return user.role == "admin" or user.is_superadmin


def get_user_school(user):
    """
    Get the school associated with the current user.
    For superadmins, this will return None (they can access all schools).
    For other users, it will return their associated school.

    Args:
        user: User object

    Returns:
        School object or None
    """
    if user.is_superadmin:
        return None  # Superadmins can access all schools
    return user.school


def get_current_academic_year(school=None):
    """
    Get the current academic year for a specific school.

    Args:
        school: Optional SchoolInformation object

    Returns:
        AcademicYear object or None
    """
    return SchoolInformation.get_current_academic_year(school)


def get_current_term(school=None):
    """
    Get the current term for a specific school.

    Args:
        school: Optional SchoolInformation object

    Returns:
        Term object or None
    """
    return SchoolInformation.get_current_term(school)


def calculate_student_average(student, academic_year, terms=None, school=None):
    """
    Calculate a student's average score based on the active performance requirements.

    Args:
        student: Student object
        academic_year: AcademicYear object
        terms: Optional list of Term objects to include (defaults to all terms in the academic year)
        school: Optional school to filter by for multi-tenancy support

    Returns:
        A dictionary containing:
        - average_score: The calculated average score
        - passed_subjects: Number of passed subjects
        - failed_subjects: Number of failed subjects
        - subject_averages: List of dictionaries with subject performance details
        - calculation_method: The method used for calculation
    """
    # Get active performance requirements for the specific school if provided
    requirements = PerformanceRequirement.get_active(school=school or student.school)
    if not requirements:
        # Default to simple average if no requirements exist
        calculation_method = "simple"
        min_average_score = Decimal("40.00")

        min_passing_grade = None
    else:
        calculation_method = requirements.calculation_method
        min_average_score = requirements.min_average_score_for_promotion
        min_passing_grade = requirements.min_passing_grade


    # Get terms if not provided, filtered by school if applicable
    if not terms:
        terms_filter = {"academic_year": academic_year}
        if school:
            terms_filter["school"] = school
        elif student.school:
            terms_filter["school"] = student.school
        terms = Term.objects.filter(**terms_filter)

    # Get all assessments for the student across the terms, filtered by school if applicable
    assessment_filter = {
        "student": student,
        "class_subject__academic_year": academic_year,
    }
    if school:
        assessment_filter["school"] = school
    elif student.school:
        assessment_filter["school"] = student.school


    # If specific terms are provided, filter by those terms
    if terms:
        term_ids = [term.id for term in terms]
        assessment_filter["term__id__in"] = term_ids

    # Exclude mock exam assessments from promotion calculations
    assessments = Assessment.objects.filter(**assessment_filter).exclude(assessment_type='mock_exam')


    # Group assessments by subject
    subject_data = {}

    for assessment in assessments:
        subject_id = assessment.class_subject.subject.id
        subject_name = assessment.class_subject.subject.subject_name

        term_number = assessment.term.term_number if assessment.term else 1


        if subject_id not in subject_data:
            subject_data[subject_id] = {
                "subject_name": subject_name,
                "scores": [],
                "terms": {},
                "term_scores": {},
            }

        # Store score by term for weighted calculation
        if assessment.total_score is not None:
            subject_data[subject_id]["terms"][term_number] = True
            subject_data[subject_id]["term_scores"][term_number] = float(
                assessment.total_score
            )
            subject_data[subject_id]["scores"].append(float(assessment.total_score))

    # Calculate averages based on the calculation method
    subject_averages = []
    total_average = 0

    # Process each subject
    for subject_id, data in subject_data.items():
        if calculation_method == "simple":
            # Simple average across all terms
            if data["scores"]:
                avg_score = sum(data["scores"]) / len(data["scores"])
            else:
                avg_score = 0
        else:
            # Weighted average based on term weights
            if not data["term_scores"]:
                avg_score = 0
            else:
                # Get term weights from requirements
                term_weights = {
                    1: float(requirements.first_term_weight) / 100,
                    2: float(requirements.second_term_weight) / 100,
                    3: float(requirements.third_term_weight) / 100,
                }

                # Calculate weighted average
                weighted_sum = 0
                total_weight = 0

                for term_num, score in data["term_scores"].items():
                    if term_num in term_weights:
                        weight = term_weights[term_num]
                        weighted_sum += score * weight
                        total_weight += weight

                if total_weight > 0:
                    avg_score = weighted_sum / total_weight
                else:
                    avg_score = 0

        # Round to 2 decimal places
        avg_score = round(avg_score, 2)


        # Determine if subject is passed based on minimum average score or minimum passing grade
        is_passed = False
        if min_passing_grade:
            # Use grade-based passing criteria
            is_passed = avg_score >= float(min_passing_grade.min_score)
        else:
            # Use average score-based passing criteria
            is_passed = avg_score >= float(min_average_score)


        # Add to subject averages list
        subject_averages.append(
            {

                "subject_id": subject_id,
                "subject_name": data["subject_name"],
                "avg_score": avg_score,
                "terms_count": len(data["terms"]),
                "term_scores": data["term_scores"],

                "status": "Pass" if is_passed else "Fail",
            }
        )

        # Add to total for overall average
        total_average += avg_score

    # Calculate overall average and count passed/failed subjects
    overall_avg = (
        round(total_average / len(subject_averages), 2) if subject_averages else 0
    )
    passed_subjects = sum(1 for s in subject_averages if s["status"] == "Pass")
    failed_subjects = sum(1 for s in subject_averages if s["status"] == "Fail")

    
    # Calculate incomplete subjects (subjects with missing assessments across required terms)
    incomplete_subjects = 0
    incomplete_subject_details = []
    
    # Get total subjects the student should have based on their class assignments
    student_class = student.get_current_class()
    if student_class and terms:
        # Count subjects that are assigned to the student's class and academic year
        required_subjects = ClassSubject.objects.filter(
            class_name=student_class,
            academic_year=academic_year,
            is_active=True
        )
        
        # Get all required subject names
        required_subject_names = list(required_subjects.values_list('subject__subject_name', flat=True))
        
        # Count subjects that actually have assessments (from subject_averages)
        assessed_subjects = len(subject_averages)
        
        # For each subject, check if it has assessments for ALL required terms
        term_count = len(terms)
        subjects_with_complete_assessments = 0
        
        for subject_data in subject_averages:
            subject_id = subject_data["subject_id"]
            # Count how many terms this subject has assessments for
            terms_with_assessments = len(subject_data.get("term_scores", {}))
            if terms_with_assessments >= term_count:
                subjects_with_complete_assessments += 1
        
        # Find subjects that are missing assessments
        assessed_subject_names = [s["subject_name"] for s in subject_averages]
        missing_subjects = [name for name in required_subject_names if name not in assessed_subject_names]
        
        # Find subjects with incomplete term assessments
        incomplete_term_subjects = []
        for subject_data in subject_averages:
            terms_with_assessments = len(subject_data.get("term_scores", {}))
            if terms_with_assessments < term_count:
                missing_terms = term_count - terms_with_assessments
                incomplete_term_subjects.append(f"{subject_data['subject_name']} (missing {missing_terms} term{'s' if missing_terms > 1 else ''})")
        
        # Combine all incomplete subjects
        incomplete_subject_details = missing_subjects + incomplete_term_subjects
        
        # Incomplete subjects = Required subjects - Subjects with complete assessments across all terms
        incomplete_subjects = max(0, len(required_subject_names) - subjects_with_complete_assessments)


    # Sort subjects by average score (highest first)
    subject_averages.sort(key=lambda x: x["avg_score"], reverse=True)

    return {
        "average_score": overall_avg,
        "passed_subjects": passed_subjects,
        "failed_subjects": failed_subjects,

        "incomplete_subjects": incomplete_subjects,
        "incomplete_subject_details": incomplete_subject_details,

        "subject_averages": subject_averages,
        "calculation_method": (
            "Simple Average" if calculation_method == "simple" else "Weighted Average"
        ),
    }


def check_promotion_eligibility(student, academic_year, terms=None, school=None):
    """
    Check if a student is eligible for promotion based on performance requirements.

    Args:
        student: Student object
        academic_year: AcademicYear object
        terms: Optional list of Term objects to include
        school: Optional school to filter by for multi-tenancy support

    Returns:
        A dictionary containing:
        - eligible: Boolean indicating if student is eligible for promotion
        - reason: String explaining the reason for the decision
        - performance: The performance data dictionary from calculate_student_average
    """
    # Get active performance requirements for the specific school if provided
    requirements = PerformanceRequirement.get_active(school=school or student.school)
    if not requirements:
        # Default requirements if none exist
        min_average_score = Decimal("40.00")
        max_failed_subjects = 3

        min_passing_grade = None
    else:
        min_average_score = requirements.min_average_score_for_promotion
        max_failed_subjects = requirements.max_failed_subjects
        min_passing_grade = requirements.min_passing_grade


    # Calculate student's performance
    performance = calculate_student_average(
        student, academic_year, terms, school=school
    )

    # Check eligibility
    eligible = True
    reason = "Meets all promotion requirements"


    # First check for incomplete subjects
    if performance["incomplete_subjects"] > 0:
        eligible = False
        term_count = len(terms) if terms else 1
        incomplete_details = performance.get("incomplete_subject_details", [])
        
        if incomplete_details:
            # Create detailed list of missing subjects
            missing_list = ", ".join(incomplete_details[:5])  # Show first 5 for readability
            if len(incomplete_details) > 5:
                missing_list += f" and {len(incomplete_details) - 5} more"
            
            reason = f"Missing assessments for {performance['incomplete_subjects']} subjects across {term_count} term{'s' if term_count > 1 else ''}. Missing: {missing_list}. Student needs assessments for all required subjects in all terms to be eligible for promotion."
        else:
            reason = f"Missing assessments for {performance['incomplete_subjects']} subjects across {term_count} term{'s' if term_count > 1 else ''}. Student needs assessments for all required subjects in all terms to be eligible for promotion."

    # Check average score (only if not incomplete)
    elif performance["average_score"] < float(min_average_score):
        eligible = False
        passing_criteria = f"minimum grade {min_passing_grade.grade_letter}" if min_passing_grade else f"minimum score {min_average_score}"
        reason = f"Average score ({performance['average_score']:.1f}) is below the {passing_criteria}. Student needs to improve performance to meet promotion requirements."

    # Check number of failed subjects (only if not incomplete)
    elif performance["failed_subjects"] > max_failed_subjects:
        eligible = False
        # Get list of failed subjects
        failed_subject_names = [s["subject_name"] for s in performance["subject_averages"] if s["status"] == "Fail"]
        failed_list = ", ".join(failed_subject_names[:5])  # Show first 5 for readability
        if len(failed_subject_names) > 5:
            failed_list += f" and {len(failed_subject_names) - 5} more"
        
        reason = f"Failed {performance['failed_subjects']} subjects, but maximum allowed is {max_failed_subjects}. Failed subjects: {failed_list}. Student needs to pass more subjects to be eligible for promotion."


    return {"eligible": eligible, "reason": reason, "performance": performance}


def check_demotion_eligibility(student, school):
    """
    Check if a student is eligible for demotion (has previous class assignments).

    Args:
        student: Student object
        school: SchoolInformation object for multi-tenancy

    Returns:
        A tuple containing:
        - eligible: Boolean indicating if student can be demoted
        - reason: String explaining the reason for the decision
        - previous_class: The previous class object if eligible, None otherwise
    """
    from ..models import StudentClass

    try:
        # Get the student's current class to exclude it from previous assignments
        current_assignment = StudentClass.objects.filter(
            student=student, is_active=True, school=school
        ).first()

        if not current_assignment:
            return False, "No current active assignment found", None

        current_class = current_assignment.assigned_class

        # Check if student has any previous (inactive) class assignments in a different class
        previous_assignments = (
            StudentClass.objects.filter(student=student, is_active=False, school=school)
            .exclude(
                assigned_class=current_class  # Exclude assignments to the same class
            )
            .order_by("-date_assigned")
        )

        if not previous_assignments.exists():
            return (
                False,
                "No previous class assignment found (excluding current class)",
                None,
            )

        # Get the most recent previous assignment in a different class
        previous_assignment = previous_assignments.first()
        previous_class = previous_assignment.assigned_class

        # Validate that the previous class still exists and is valid
        if not previous_class:
            return False, "Previous class no longer exists", None

        if not previous_class.academic_year:
            return False, "Previous class has no associated academic year", None

        return True, f"Can be demoted to {previous_class.name}", previous_class

    except Exception as e:
        import logging

        logger = logging.getLogger("shs_system.demotion")
        logger.error(
            f"Error checking demotion eligibility for {student.full_name}: {str(e)}"
        )
        return False, f"Error checking demotion eligibility: {str(e)}", None


def calculate_weekdays(start_date, end_date):
    """Calculate number of weekdays between two dates"""
    import numpy as np

    # Convert to numpy datetime for faster calculation
    start = np.datetime64(start_date)
    end = np.datetime64(end_date)

    # Create array of all days between start and end
    days = np.busday_count(start, end)
    return int(days)


def get_teacher_monitoring_data(
    academic_year=None, term=None, teachers=None, school=None
):
    """
    Get monitoring data on teacher activity for assessments, remarks, and attendance.

    This function collects statistics on whether teachers have entered:
    - Student scores (assessments)
    - Student remarks
    - Attendance records

    Args:
        academic_year: Optional specific AcademicYear to filter by
        term: Optional specific Term to filter by
        teachers: Optional list of Teacher objects to filter by
        school: Optional SchoolInformation object to filter by for multi-tenancy

    Returns:
        A dictionary containing monitoring statistics
    """
    from django.db.models import Count, Q, F, Case, When, IntegerField, Sum
    from django.db.models.functions import Coalesce
    from ..models import (
        TeacherSubjectAssignment,
        Assessment,
        StudentTermRemarks,
        AttendanceRecord,
        ClassTeacher,
        Teacher,
        SchoolInformation,
        StudentClass,
    )

    # Get current academic year and term if not provided
    if not academic_year:
        academic_year = SchoolInformation.get_current_academic_year(school=school)
    if not term:
        term = SchoolInformation.get_current_term(school=school)

    # Get all active teachers if not specified, filtered by school if provided
    if not teachers:
        if school:
            teachers = Teacher.objects.filter(school=school)
        else:
            teachers = Teacher.objects.all()

    # Initialize results
    monitoring_data = {
        "academic_year": academic_year,
        "term": term,
        "teacher_data": [],
        "summary": {
            "total_teachers": len(teachers),
            "scores_completed": 0,
            "remarks_completed": 0,
            "attendance_completed": 0,
        },
    }

    # For each teacher, gather monitoring data
    for teacher in teachers:
        teacher_info = {
            "teacher": teacher,
            "subject_assignments": [],
            "class_teacher_assignments": [],
            "scores_completion_rate": 0,
            "remarks_completion_rate": 0,
            "attendance_completion_rate": 0,
        }

        # Get subject assignments - filtered by school if provided
        subject_assignments_query = TeacherSubjectAssignment.objects.filter(
            teacher=teacher, academic_year=academic_year, is_active=True
        )
        if school:
            subject_assignments_query = subject_assignments_query.filter(school=school)
        subject_assignments = subject_assignments_query

        # Get class teacher assignments - filtered by school if provided
        class_teacher_query = ClassTeacher.objects.filter(
            teacher=teacher, academic_year=academic_year, is_active=True
        )
        if school:
            class_teacher_query = class_teacher_query.filter(school=school)
        class_teacher_assignments = class_teacher_query

        total_students = 0
        total_scores_entered = 0

        # Process subject assignments
        for assignment in subject_assignments:
            # Get enrolled students - filtered by school if provided
            students_query = StudentClass.objects.filter(
                assigned_class=assignment.class_assigned, is_active=True
            )
            if school:
                students_query = students_query.filter(student__user__school=school)
            students = students_query.count()

            # Count assessments entered - filtered by school if provided
            assessments_query = Assessment.objects.filter(
                class_subject__subject=assignment.subject,
                class_subject__class_name=assignment.class_assigned,
                class_subject__academic_year=academic_year,
                total_score__isnull=False,
            )
            if school:
                assessments_query = assessments_query.filter(
                    student__user__school=school
                )
            assessments = assessments_query.count()

            completion_rate = (assessments / students * 100) if students > 0 else 0

            assignment_info = {
                "assignment": assignment,
                "students_count": students,
                "assessments_count": assessments,
                "completion_rate": round(completion_rate, 2),
            }

            teacher_info["subject_assignments"].append(assignment_info)
            total_students += students
            total_scores_entered += assessments

        # Calculate overall scores completion rate
        if total_students > 0:
            teacher_info["scores_completion_rate"] = round(
                total_scores_entered / total_students * 100, 2
            )

        # Process class teacher assignments - remarks
        total_class_students = 0
        total_remarks_entered = 0

        for class_assignment in class_teacher_assignments:
            # Get students in class - filtered by school if provided
            students_query = StudentClass.objects.filter(
                assigned_class=class_assignment.class_assigned, is_active=True
            )
            if school:
                students_query = students_query.filter(student__user__school=school)
            students = students_query.count()

            # Count remarks entered - filtered by school if provided
            remarks_query = StudentTermRemarks.objects.filter(
                class_assigned=class_assignment.class_assigned,
                academic_year=academic_year,
                term=term,
                class_teacher=teacher,
            )
            if school:
                remarks_query = remarks_query.filter(student__user__school=school)
            remarks = remarks_query.count()

            remarks_completion_rate = (remarks / students * 100) if students > 0 else 0

            assignment_info = {
                "class_assigned": class_assignment.class_assigned,
                "students_count": students,
                "remarks_count": remarks,
                "completion_rate": round(remarks_completion_rate, 2),
            }

            teacher_info["class_teacher_assignments"].append(assignment_info)
            total_class_students += students
            total_remarks_entered += remarks

        # Calculate overall remarks completion rate
        if total_class_students > 0:
            teacher_info["remarks_completion_rate"] = round(
                total_remarks_entered / total_class_students * 100, 2
            )

        # Process attendance records (for class teachers)
        total_attendance_days = 0
        total_attendance_records = 0

        for class_assignment in class_teacher_assignments:
            # Get all students in the class - filtered by school if provided
            student_query = StudentClass.objects.filter(
                assigned_class=class_assignment.class_assigned, is_active=True
            )
            if school:
                student_query = student_query.filter(student__user__school=school)
            student_ids = student_query.values_list("student_id", flat=True)

            # Count school days in this term
            school_days = 0
            if term and term.start_date and term.end_date:
                school_days = calculate_weekdays(term.start_date, term.end_date)

            # Expected attendance records for the class
            expected_records = len(student_ids) * school_days

            # Actual attendance records - filtered by school if provided
            attendance_query = AttendanceRecord.objects.filter(
                student_id__in=student_ids, term=term, recorded_by=teacher
            )
            if school:
                attendance_query = attendance_query.filter(student__user__school=school)
            actual_records = attendance_query.count()

            attendance_completion_rate = (
                (actual_records / expected_records * 100) if expected_records > 0 else 0
            )

            class_assignment.attendance_data = {
                "expected_records": expected_records,
                "actual_records": actual_records,
                "completion_rate": round(attendance_completion_rate, 2),
            }

            total_attendance_days += expected_records
            total_attendance_records += actual_records

        # Calculate overall attendance completion rate
        if total_attendance_days > 0:
            teacher_info["attendance_completion_rate"] = round(
                total_attendance_records / total_attendance_days * 100, 2
            )

        monitoring_data["teacher_data"].append(teacher_info)

    # Calculate summary statistics
    if monitoring_data["teacher_data"]:
        monitoring_data["summary"]["scores_completed"] = sum(
            1
            for t in monitoring_data["teacher_data"]
            if t["scores_completion_rate"] >= 90
        )
        monitoring_data["summary"]["remarks_completed"] = sum(
            1
            for t in monitoring_data["teacher_data"]
            if t["remarks_completion_rate"] >= 90
        )
        monitoring_data["summary"]["attendance_completed"] = sum(
            1
            for t in monitoring_data["teacher_data"]
            if t["attendance_completion_rate"] >= 90
        )

    return monitoring_data


def filter_by_school(queryset, model_name, school=None):
    """
    Helper function to filter querysets by school, handling models without direct school fields.

    Args:
        queryset: The queryset to filter
        model_name: The name of the model (e.g., 'ClassSubject', 'Assessment')
        school: The school to filter by (can be None for superadmins, or a SchoolInformation object, or a school ID)

    Returns:
        A filtered queryset
    """
    from ..models import SchoolInformation

    if not school:
        # If no school provided (superadmin case), return unfiltered queryset
        return queryset

    # If school is a string (school name) or an integer (school ID), try to get the SchoolInformation object
    if isinstance(school, (str, int)):
        try:
            if isinstance(school, str):
                school = SchoolInformation.objects.get(name=school)
            else:
                school = SchoolInformation.objects.get(id=school)
        except SchoolInformation.DoesNotExist:
            # If school doesn't exist, return empty queryset
            return queryset.none()

    # Handle models without direct school fields
    if model_name == "ClassSubject":
        # Use direct school field if available, otherwise filter by related models
        try:
            # Check if model has school field
            if hasattr(queryset.model, "school"):
                return queryset.filter(school=school)
            else:
                # Fall back to filtering by related models
                return queryset.filter(
                    class_name__school=school, subject__school=school
                )
        except Exception:
            # If there's any error, fall back to filtering by related models
            return queryset.filter(class_name__school=school, subject__school=school)
    elif model_name == "Assessment":
        # For Assessment, filter by student's school
        return queryset.filter(student__user__school=school)
    elif model_name == "AttendanceRecord":
        # For Attendance, filter by student's school
        return queryset.filter(student__user__school=school)
    elif model_name == "StudentTermRemarks":
        # For StudentTermRemarks, filter by student's school
        return queryset.filter(student__user__school=school)
    else:
        # For models with direct school field, use standard filter
        return queryset.filter(school=school)


def send_activity_reminder_email(teacher_email, context):
    """
    Send activity reminder email to a teacher.

    Args:
        teacher_email (str): Email address of the recipient
        context (dict): Context data for the email template

    Returns:
        tuple: (success: bool, message: str)
    """
    from django.template.loader import render_to_string
    from django.utils.html import strip_tags
    from django.core.mail import send_mail
    from django.conf import settings
    import logging

    # Get logger
    logger = logging.getLogger("shs_system.email")

    # Check if email sending is disabled
    if hasattr(settings, "DISABLE_EMAIL_SENDING") and settings.DISABLE_EMAIL_SENDING:
        logger.info(f"Email sending is disabled. Would have sent to {teacher_email}")
        return (
            True,
            "Email sending is disabled in settings, but the request was processed",
        )

    try:
        # Check if we have the SystemEmailConfig model available
        system_email_config_available = False
        try:
            # Import from super_admin.models instead of ..models
            from super_admin.models import SystemEmailConfig

            system_email_config_available = True
            logger.debug(
                "SystemEmailConfig imported successfully from super_admin.models"
            )
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to import SystemEmailConfig: {str(e)}")
            system_email_config_available = False

        # If SystemEmailConfig is available, try to use it
        if system_email_config_available:
            email_config = SystemEmailConfig.objects.filter(is_active=True).first()
            if email_config:
                logger.info(
                    f"Found active email config: {email_config.name} ({email_config.service_type})"
                )
                # Import necessary functions
                try:
                    # Create a dummy user object with just the email
                    class DummyUser:
                        def __init__(self, email):
                            self.email = email

                    dummy_user = DummyUser(teacher_email)

                    # Use the appropriate method based on config
                    if email_config.service_type == "oauth":
                        # For OAuth, we need to use a different approach since the template is different
                        try:
                            from google.oauth2.credentials import Credentials
                            from googleapiclient.discovery import build
                            from email.mime.text import MIMEText
                            import base64

                            # Check if we have all required OAuth credentials
                            if not all(
                                [
                                    email_config.client_id,
                                    email_config.client_secret,
                                    email_config.refresh_token,
                                    email_config.token_uri,
                                ]
                            ):
                                logger.error(
                                    "OAuth credentials incomplete, falling back to standard email"
                                )
                                raise ValueError("Incomplete OAuth credentials")

                            # Render email template
                            html_message = render_to_string(
                                "emails/activity_reminder.html", context
                            )
                            subject = f"{context.get('school_name', 'School')} - {context.get('activity_type_name', 'Activity')} Reminder"

                            # Create credentials object
                            credentials = Credentials(
                                token=email_config.access_token,
                                refresh_token=email_config.refresh_token,
                                token_uri=email_config.token_uri,
                                client_id=email_config.client_id,
                                client_secret=email_config.client_secret,
                                scopes=email_config.scopes
                                or ["https://www.googleapis.com/auth/gmail.send"],
                            )

                            # Check if token is expired and needs refreshing
                            if not credentials.valid:
                                from google.auth.transport.requests import Request

                                try:
                                    credentials.refresh(Request())
                                    # Update the stored token
                                    email_config.access_token = credentials.token
                                    email_config.save()
                                    logger.info("OAuth token refreshed successfully")
                                except Exception as refresh_error:
                                    logger.error(
                                        f"Failed to refresh OAuth token: {str(refresh_error)}"
                                    )
                                    raise

                            # Build Gmail API service
                            gmail_service = build(
                                "gmail", "v1", credentials=credentials
                            )

                            # Create message
                            message = MIMEText(html_message, "html")
                            message["to"] = teacher_email
                            message["subject"] = subject

                            # Set the from name if provided
                            if email_config.from_name:
                                message["from"] = (
                                    f"{email_config.from_name} <{email_config.from_email}>"
                                )
                            else:
                                message["from"] = email_config.from_email

                            # Encode and send message
                            raw_message = base64.urlsafe_b64encode(
                                message.as_bytes()
                            ).decode("utf-8")
                            gmail_service.users().messages().send(
                                userId="me", body={"raw": raw_message}
                            ).execute()

                            # Update last used timestamp
                            from django.utils import timezone

                            email_config.last_used = timezone.now()
                            email_config.save()

                            return (
                                True,
                                "Email sent successfully via system OAuth configuration",
                            )
                        except Exception as oauth_error:
                            logger.error(f"OAuth email error: {str(oauth_error)}")
                            # Continue to next method

                    elif email_config.service_type == "smtp":
                        # For SMTP, we can use Django's EmailMultiAlternatives
                        try:
                            from django.core.mail import EmailMultiAlternatives
                            from django.core.mail.backends.smtp import EmailBackend

                            # Check if we have all required SMTP credentials
                            if not all(
                                [
                                    email_config.smtp_host,
                                    email_config.smtp_port,
                                    email_config.smtp_username,
                                    email_config.smtp_password,
                                ]
                            ):
                                logger.error(
                                    "SMTP credentials incomplete, falling back to standard email"
                                )
                                raise ValueError("Incomplete SMTP credentials")

                            # Render email template
                            html_message = render_to_string(
                                "emails/activity_reminder.html", context
                            )
                            plain_message = strip_tags(html_message)
                            subject = f"{context.get('school_name', 'School')} - {context.get('activity_type_name', 'Activity')} Reminder"

                            # Create custom email backend with our settings
                            email_backend = EmailBackend(
                                host=email_config.smtp_host,
                                port=email_config.smtp_port,
                                username=email_config.smtp_username,
                                password=email_config.smtp_password,
                                use_tls=email_config.smtp_use_tls,
                                use_ssl=email_config.smtp_use_ssl,
                                fail_silently=False,
                            )

                            # Set the from name if provided
                            if email_config.from_name:
                                from_email = f"{email_config.from_name} <{email_config.from_email}>"
                            else:
                                from_email = email_config.from_email

                            msg = EmailMultiAlternatives(
                                subject=subject,
                                body=plain_message,
                                from_email=from_email,
                                to=[teacher_email],
                                connection=email_backend,
                            )
                            msg.attach_alternative(html_message, "text/html")
                            msg.send()

                            # Update last used timestamp
                            from django.utils import timezone

                            email_config.last_used = timezone.now()
                            email_config.save()

                            return True, "Email sent successfully via SMTP"
                        except Exception as smtp_error:
                            error_message = str(smtp_error)
                            logger.error(f"SMTP email error: {error_message}")

                            # Check for specific Gmail authentication errors
                            if (
                                "535" in error_message
                                and "BadCredentials" in error_message
                            ):
                                return (
                                    False,
                                    "Gmail authentication failed. Please check your credentials or enable 'Less secure app access' in your Google account settings.",
                                )
                            elif "Authentication" in error_message:
                                return (
                                    False,
                                    "Email authentication failed. Please check your email credentials.",
                                )
                            # Continue to next method
                except Exception as e:
                    # Fall through to standard email if any error occurs
                    logger.error(f"Email config error: {str(e)}")

        # Check for legacy OAuth credentials in the shs_system app
        try:
            from shs_system.models import OAuthCredentialStore

            oauth_creds = OAuthCredentialStore.objects.filter(is_active=True).first()
            if oauth_creds and oauth_creds.refresh_token:
                try:
                    from google.oauth2.credentials import Credentials
                    from googleapiclient.discovery import build
                    from email.mime.text import MIMEText
                    import base64

                    # Render email template
                    html_message = render_to_string(
                        "emails/activity_reminder.html", context
                    )
                    subject = f"{context.get('school_name', 'School')} - {context.get('activity_type_name', 'Activity')} Reminder"

                    # Create credentials object
                    credentials = Credentials(
                        token=oauth_creds.access_token,
                        refresh_token=oauth_creds.refresh_token,
                        token_uri=oauth_creds.token_uri
                        or "https://oauth2.googleapis.com/token",
                        client_id=oauth_creds.client_id,
                        client_secret=oauth_creds.client_secret,
                        scopes=oauth_creds.scopes
                        or ["https://www.googleapis.com/auth/gmail.send"],
                    )

                    # Check if token is expired and needs refreshing
                    if not credentials.valid:
                        from google.auth.transport.requests import Request

                        credentials.refresh(Request())
                        # Update the stored token
                        oauth_creds.access_token = credentials.token
                        oauth_creds.save()

                    # Build Gmail API service
                    gmail_service = build("gmail", "v1", credentials=credentials)

                    # Create message
                    message = MIMEText(html_message, "html")
                    message["to"] = teacher_email
                    message["subject"] = subject
                    message["from"] = oauth_creds.email

                    # Encode and send message
                    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode(
                        "utf-8"
                    )
                    gmail_service.users().messages().send(
                        userId="me", body={"raw": raw_message}
                    ).execute()

                    return (
                        True,
                        "Email sent successfully via legacy OAuth configuration",
                    )
                except Exception as legacy_oauth_error:
                    logger.error(f"Legacy OAuth email error: {str(legacy_oauth_error)}")
        except (ImportError, Exception) as e:
            logger.debug(f"No legacy OAuth credentials available: {str(e)}")

        # Fall back to standard Django email
        try:
            html_message = render_to_string("emails/activity_reminder.html", context)
            plain_message = strip_tags(html_message)
            subject = f"{context.get('school_name', 'School')} - {context.get('activity_type_name', 'Activity')} Reminder"

            send_mail(
                subject,
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [teacher_email],
                html_message=html_message,
                fail_silently=False,
            )
            return True, "Email sent successfully via standard email"
        except Exception as django_mail_error:
            logger.error(f"Django email error: {str(django_mail_error)}")

            # If all email methods fail, try to save to a notification model if available
            try:
                # Check if the teacher has a user account
                from shs_system.models import User

                user = User.objects.filter(email=teacher_email).first()

                if user:
                    from shs_system.models import Notification

                    # Get class name safely - handle both Class objects and dictionaries
                    class_name = ""
                    if "class_obj" in context:
                        class_obj = context["class_obj"]
                        if isinstance(class_obj, dict):
                            class_name = class_obj.get("name", "your class")
                        else:
                            # It's a Class model instance
                            class_name = (
                                class_obj.name
                                if hasattr(class_obj, "name")
                                else "your class"
                            )

                    # Create notification with correct fields based on the Notification model
                    Notification.objects.create(
                        recipient=user,
                        recipient_role=user.role,  # Use the user's role
                        message=f"Please complete your {context.get('activity_type_name', 'activity')} for {class_name} class.",
                    )
                    return (
                        True,
                        "Email could not be sent, but a notification has been saved in the system",
                    )
                else:
                    logger.warning(
                        f"No user found for email {teacher_email}, cannot create notification"
                    )
            except Exception as notification_error:
                logger.error(f"Notification creation error: {str(notification_error)}")

                # Get class name safely for logging
                class_name = ""
                if "class_obj" in context:
                    class_obj = context["class_obj"]
                    if isinstance(class_obj, dict):
                        class_name = class_obj.get("name", "your class")
                    else:
                        # It's a Class model instance
                        class_name = (
                            class_obj.name
                            if hasattr(class_obj, "name")
                            else "your class"
                        )

                # Last resort - log the message
                logger.info(
                    f"REMINDER TO {teacher_email}: {context.get('activity_type_name', 'Activity')} for {class_name} class"
                )
                return (
                    False,
                    "Email delivery failed. The system administrator has been notified.",
                )

    except Exception as e:
        logger.error(f"Unexpected email error: {str(e)}")
        return False, f"Error sending email: {str(e)}"
