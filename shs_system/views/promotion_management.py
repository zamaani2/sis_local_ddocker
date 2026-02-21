from django.db.models import Q, Avg, Count, Case, When, IntegerField, F
from django.contrib.auth.decorators import login_required, user_passes_test
from shs_system.models import (
    Student,
    Class,
    StudentClass,
    Assessment,
    ArchivedStudent,
    ClassSubject,
    AcademicYear,
    Term,
    Form,
    LearningArea,
    SchoolInformation,
    ClassTeacher,
    ScoringConfiguration,
)
from django.contrib.auth.decorators import login_required, user_passes_test
import logging
from django.contrib import messages
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from shs_system.utils import (
    check_promotion_eligibility,
    calculate_student_average,
    check_demotion_eligibility,
)


def is_admin(user):
    return user.is_authenticated and user.role == "admin"


logger = logging.getLogger(__name__)


@user_passes_test(is_admin)
def student_promotion(request):
    """Promote eligible students to specific target classes or archive completed students based on multiple terms"""
    import time
    from django.db.models import Avg, Count, Q, Prefetch
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    from django.core.cache import cache
    from shs_system.models import PerformanceRequirement

    from django.http import JsonResponse

    start_time = time.time()

    # Handle AJAX requests for loading class data
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return handle_ajax_class_data_request(request)


    # Get the current user's school
    user_school = request.user.school
    if not user_school:
        messages.error(
            request,
            "You are not associated with any school. Please contact the administrator.",
        )
        return redirect("student_list")

    # Get current academic year and term
    # Try to get from SchoolInformation first, which is more reliable
    school_info = SchoolInformation.objects.filter(id=user_school.id).first()
    if school_info and school_info.current_academic_year:
        current_academic_year = school_info.current_academic_year
        logger.info(
            f"Using academic year from school info: {current_academic_year.name}"
        )
    else:
        current_academic_year = AcademicYear.objects.filter(
            is_current=True, school=user_school
        ).first()
        logger.info(
            f"Using academic year with is_current=True: {current_academic_year.name if current_academic_year else 'None'}"
        )

    if school_info and school_info.current_term:
        current_term = school_info.current_term
        logger.info(
            f"Using term from school info: {current_term.term_number} of {current_term.academic_year.name}"
        )
    else:
        current_term = Term.objects.filter(is_current=True, school=user_school).first()
        logger.info(
            f"Using term with is_current=True: {current_term.term_number if current_term else 'None'}"
        )

    if not current_academic_year or not current_term:
        messages.error(
            request,
            "Current academic year or term is not set. Please set them in School Information settings.",
        )
        return redirect("student_list")

    # Log details about the current academic year and term for debugging
    logger.debug(
        f"Current academic year: {current_academic_year.name} (ID: {current_academic_year.id})"
    )
    logger.debug(
        f"Current academic year dates: {current_academic_year.start_date} to {current_academic_year.end_date}"
    )
    logger.debug(f"Current term: {current_term.term_number} (ID: {current_term.id})")
    logger.debug(
        f"Current term dates: {current_term.start_date} to {current_term.end_date}"
    )

    # Get active performance requirements for this school
    active_requirements = PerformanceRequirement.get_active(school=user_school)

    # If no active requirements exist, log it but don't show disruptive warning
    if not active_requirements:
        logger.info(
            "No active performance requirements found. Using default values for promotion evaluation."
        )

    # Get all available academic years for selection (excluding archived)
    available_academic_years = AcademicYear.objects.filter(
        school=user_school, is_archived=False
    ).order_by("start_date")

    # Get all available classes for target selection (excluding classes from archived academic years)
    available_classes = (
        Class.objects.filter(school=user_school, academic_year__is_archived=False)
        .select_related("form", "learning_area", "academic_year")
        .order_by(
            "academic_year__start_date",
            "form__form_number",
            "learning_area__name",
            "name",
        )
    )

    # Log for debugging
    logger.debug(
        f"Available academic years: {[year.name for year in available_academic_years]}"
    )
    logger.debug(f"Available classes: {available_classes.count()}")

    # Get search and filter parameters
    search_query = request.GET.get("search", "")
    form_filter = request.GET.get("form_filter", "")
    status_filter = request.GET.get("status_filter", "")
    learning_area_filter = request.GET.get("learning_area_filter", "")
    admission_filter = request.GET.get("admission", "")

    # New parameter to specify how many terms to consider
    terms_to_consider = int(request.GET.get("terms_to_consider", 3))


    # Get selected class ID for optimization
    selected_class_id = request.GET.get('selected_class_id')
    
    # Get active students - only for selected class if specified
    if selected_class_id:
        active_students = Student.objects.filter(
            studentclass__is_active=True,
            school=user_school,
            studentclass__assigned_class__academic_year=current_academic_year,
            studentclass__assigned_class_id=selected_class_id,
        ).distinct()
    else:
        # If no class selected, don't load any students initially
        active_students = Student.objects.none()

    # Apply search filter if provided
    if search_query and active_students.exists():

        active_students = active_students.filter(
            Q(full_name__icontains=search_query)
            | Q(admission_number__icontains=search_query)
        )

    # Get all terms for the current academic year, ordered by term number
    academic_terms = Term.objects.filter(
        academic_year=current_academic_year, school=user_school
    ).order_by("term_number")

    # Get latest terms up to the number of terms to consider
    term_ids = list(academic_terms.values_list("id", flat=True))

    # If not enough terms exist in current academic year, log it but don't show disruptive warning
    if len(term_ids) < terms_to_consider:
        logger.info(
            f"Only {len(term_ids)} terms exist in current academic year, but {terms_to_consider} terms requested. Using available terms."
        )

    # Get the latest N terms
    terms_to_use = term_ids[-min(terms_to_consider, len(term_ids)) :]
    terms_to_use_objects = Term.objects.filter(id__in=terms_to_use)

    # Prepare data structures
    promotion_data = []

    for student in active_students:
        current_class = student.get_current_class()
        if not current_class:
            continue

        # Get current form as an integer value
        current_form = current_class.form
        if not isinstance(current_form, int) and hasattr(current_form, "form_number"):
            current_form = current_form.form_number

        # Skip if student has no active class or form information is missing
        if not current_form:
            continue

        # Apply form filter if provided
        if form_filter and str(current_form) != form_filter:
            continue

        # Apply learning area filter if provided
        if (
            learning_area_filter
            and str(current_class.learning_area.id) != learning_area_filter
        ):
            continue

        # Get all subjects for student's class in the current term
        student_subjects = ClassSubject.objects.filter(
            class_name=current_class,
            academic_year=current_academic_year,

            is_active=True

        )

        # Get all required subjects count
        subject_count = student_subjects.count()

        # Use check_promotion_eligibility utility to determine promotion status
        eligibility_result = check_promotion_eligibility(
            student, current_academic_year, terms_to_use_objects, school=user_school
        )

        # Extract performance data
        performance = eligibility_result["performance"]
        eligible = eligibility_result["eligible"]
        # Note: reason will be set in the status determination logic below

        # Get student's assessments for the current year across all terms
        assessments = Assessment.objects.filter(
            student=student,
            class_subject__academic_year=current_academic_year,

            class_subject__is_active=True,

            school=user_school,
        )

        # Determine status based on assessments and form
        current_form = current_class.form
        if hasattr(current_form, "form_number"):
            current_form = current_form.form_number

        # Count the number of subjects for this class
        class_subject_count = ClassSubject.objects.filter(

            class_name=current_class, academic_year=current_academic_year, is_active=True

        ).count()

        # Debug logging for newly promoted students
        assessment_count = assessments.count()
        logger.debug(
            f"Student {student.full_name} in {current_class.name}: "
            f"assessments={assessment_count}, subjects={class_subject_count}, "
            f"academic_year={current_academic_year.name}"
        )

        # Determine status based on assessments and form
        # Use performance configuration settings instead of hardcoded values
        if class_subject_count == 0:
            # No subjects assigned to this class yet
            status = "incomplete"
            reason = f"No subjects assigned to class {current_class.name} for {current_academic_year.name}"
        elif assessment_count == 0:
            # Student has no assessments in current academic year (newly promoted)
            status = "incomplete"
            reason = f"No assessments recorded for {current_academic_year.name}"
        elif assessment_count < class_subject_count:
            # Student has some but not all assessments
            status = "incomplete"
            reason = f"Missing assessments for {class_subject_count - assessment_count} subjects"
        else:
            # Use the performance configuration to determine status
            # The check_promotion_eligibility function already calculated this correctly
            if eligible:
                # Check if student is in Form 3 (graduation eligible)
                if (
                    current_form is not None and current_form == 3
                ):  # Final form students graduate
                    status = "graduate"
                    reason = "Completed final form successfully"
                else:
                    # Student passed all subjects and is ready for promotion
                    status = "promote"
                    reason = "Ready for promotion to next form"
            else:
                # Student failed based on performance requirements
                status = "retained"
                reason = eligibility_result.get(
                    "reason", "Failed to meet promotion requirements"
                )

        # Apply status filter if provided
        if status_filter and status != status_filter:
            continue

        # Add to promotion data
        current_form_obj = Form.objects.filter(
            form_number=current_form, school=user_school
        ).first()
        current_form_name = (
            current_form_obj.name if current_form_obj else f"Form {current_form}"
        )

        # Make sure current_form is always an integer
        current_form_number = (
            current_form
            if isinstance(current_form, int)
            else getattr(current_form, "form_number", 0)
        )

        # Prepare failed subject details for display
        failed_subject_details = []
        for subject in performance["subject_averages"]:
            if subject["status"] == "Fail":
                failed_subject_details.append(
                    {"subject": subject["subject_name"], "score": subject["avg_score"]}
                )

        # Check demotion eligibility
        demotion_eligible, demotion_reason, previous_class = check_demotion_eligibility(
            student, user_school
        )

        promotion_data.append(
            {
                "student": student,
                "current_class": current_class,
                "current_form": current_form_number,  # Store as integer
                "form_name": current_form_name,
                "learning_area": current_class.learning_area,
                "learning_area_name": (
                    current_class.learning_area.name
                    if current_class.learning_area
                    else "N/A"
                ),
                "status": status,
                "reason": reason,
                "avg_score": performance["average_score"],
                "failed_subjects": performance["failed_subjects"],
                "failed_subject_details": failed_subject_details,
                "assessment_count": len(performance["subject_averages"]),
                "subject_count": subject_count,
                "terms_considered": terms_to_consider,
                "demotion_eligible": demotion_eligible,
                "demotion_reason": demotion_reason,
                "previous_class": previous_class,
            }
        )

    # Handle promotion action
    if request.method == "POST":
        action = request.POST.get("action")
        selected_students = request.POST.getlist("selected_students")
        target_academic_year_id = request.POST.get("target_academic_year_id")
        target_class_id = request.POST.get("target_class_id")

        if action and selected_students:
            # Process the selected action
            if action == "promote":
                try:
                    logger.info(
                        f"Promoting {len(selected_students)} students with action: {action}"
                    )

                    # Validate target selection
                    if not target_academic_year_id or not target_class_id:
                        messages.error(
                            request,
                            "Please select both target academic year and target class for promotion.",
                        )
                        return redirect("student_promotion")

                    # Get target academic year and class
                    try:
                        target_year = AcademicYear.objects.get(
                            id=target_academic_year_id, school=user_school
                        )
                        target_class = Class.objects.get(
                            id=target_class_id, school=user_school
                        )
                        logger.info(
                            f"Using target academic year: {target_year.name} and target class: {target_class.name}"
                        )
                    except (
                        AcademicYear.DoesNotExist,
                        Class.DoesNotExist,
                        ValueError,
                    ) as e:
                        logger.error(f"Invalid target selection: {str(e)}")
                        messages.error(
                            request,
                            "Invalid target academic year or class selected. Please try again.",
                        )
                        return redirect("student_promotion")

                    # Validate target class capacity
                    current_student_count = target_class.get_current_student_count()
                    if (
                        current_student_count + len(selected_students)
                        > target_class.maximum_students
                    ):
                        messages.warning(
                            request,
                            f"Warning: Target class {target_class.name} will exceed capacity. "
                            f"Current: {current_student_count}, Adding: {len(selected_students)}, "
                            f"Maximum: {target_class.maximum_students}",
                        )

                    for student_id in selected_students[
                        :5
                    ]:  # Log first 5 for debugging
                        student = Student.objects.get(id=student_id, school=user_school)
                        logger.info(
                            f"Student to promote: {student.full_name} (ID: {student_id}) to class {target_class.name}"
                        )

                    return perform_student_action(
                        request=request,
                        action_type="promote",
                        selected_students=selected_students,
                        current_academic_year=current_academic_year,
                        target_academic_year=target_year,
                        target_class=target_class,
                        terms_to_consider=terms_to_consider,
                        school=user_school,
                    )
                except Exception as e:
                    logger.error(
                        f"Error during promote action: {str(e)}", exc_info=True
                    )
                    messages.error(
                        request, f"Error processing promotion action: {str(e)}"
                    )
                    return redirect("student_promotion")

            # Handle graduation (archiving) of students
            if action == "archive":
                try:
                    logger.info(
                        f"Archiving {len(selected_students)} students with action: {action}"
                    )
                    for student_id in selected_students[
                        :5
                    ]:  # Log first 5 for debugging
                        student = Student.objects.get(id=student_id, school=user_school)
                        logger.info(
                            f"Student to archive: {student.full_name} (ID: {student_id})"
                        )

                    return perform_student_action(
                        request=request,
                        action_type="graduate",
                        selected_students=selected_students,
                        current_academic_year=current_academic_year,
                        school=user_school,
                    )
                except Exception as e:
                    logger.error(
                        f"Error during archive action: {str(e)}", exc_info=True
                    )
                    messages.error(
                        request, f"Error processing archive action: {str(e)}"
                    )
                    return redirect("student_promotion")

            # Handle demotion of students back to previous class
            if action == "demote":
                try:
                    logger.info(
                        f"Demoting {len(selected_students)} students with action: {action}"
                    )
                    for student_id in selected_students[
                        :5
                    ]:  # Log first 5 for debugging
                        student = Student.objects.get(id=student_id, school=user_school)
                        logger.info(
                            f"Student to demote: {student.full_name} (ID: {student_id})"
                        )

                    return perform_student_action(
                        request=request,
                        action_type="demote",
                        selected_students=selected_students,
                        current_academic_year=current_academic_year,
                        school=user_school,
                    )
                except Exception as e:
                    logger.error(
                        f"Error during demotion action: {str(e)}", exc_info=True
                    )
                    messages.error(
                        request, f"Error processing demotion action: {str(e)}"
                    )
                    return redirect("student_promotion")


    # Get all classes for the dropdown (but don't load student data for all)

    classes = (
        Class.objects.filter(school=user_school, academic_year=current_academic_year)
        .select_related("form", "learning_area")
        .order_by("form__form_number", "learning_area__name", "name")
    )

    # Get forms for backward compatibility (still used in some template filters)
    forms = Form.objects.filter(school=user_school).order_by("form_number")


    # Only load promotion data for a specific class if selected
    promotion_by_class = {}
    selected_class_id = request.GET.get('selected_class_id')
    
    if selected_class_id:
        try:
            selected_class = Class.objects.get(id=selected_class_id, school=user_school)
            promotion_by_class[selected_class.id] = {
                "class": selected_class,
                "students": [
                    item
                    for item in promotion_data
                    if item["current_class"] and item["current_class"].id == selected_class.id
                ],
            }
        except Class.DoesNotExist:
            pass


    # Get scoring configuration
    scoring_config = None
    if user_school:
        scoring_config = ScoringConfiguration.get_active_config(user_school)

    # Add available_academic_years and classes to the context
    context = {
        "current_academic_year": current_academic_year,
        "current_term": current_term,
        "promotion_data": promotion_data,
        "promotion_by_class": promotion_by_class,
        "classes": classes,
        "forms": [
            (int(form.form_number), form.name) for form in forms
        ],  # Ensure form_number is an integer
        "learning_areas": [
            (area.id, area.name)
            for area in LearningArea.objects.filter(school=user_school)
        ],
        "search_query": search_query,
        "form_filter": form_filter,
        "status_filter": status_filter,
        "learning_area_filter": learning_area_filter,
        "terms_to_consider": terms_to_consider,
        "available_terms": len(term_ids),
        "active_requirements": active_requirements,
        "available_academic_years": available_academic_years,
        "available_classes": available_classes,
        "scoring_config": scoring_config,

        "selected_class_id": selected_class_id,  # Pass selected class ID to template

    }

    return render(request, "student/student_promotion.html", context)


# Helper Functions for the new class-to-class promotion system


def validate_action_eligibility(student, action_type, student_status, school):
    """
    Validate if a student is eligible for a specific action based on their status.

    Args:
        student: Student object
        action_type: Type of action ('promote', 'graduate', 'demote')
        student_status: Current status of the student
        school: School object for multi-tenancy

    Returns:
        tuple: (is_eligible, reason_message)
    """

    if action_type == "promote":
        if student_status not in ["promote", "incomplete"]:
            return (
                False,
                f"Student status '{student_status}' is not eligible for promotion. Only students with 'promote' or 'incomplete' status can be promoted.",
            )
        return True, "Eligible for promotion"

    elif action_type == "graduate":
        if student_status != "graduate":
            return (
                False,
                f"Student status '{student_status}' is not eligible for graduation. Only students with 'graduate' status can be graduated.",
            )
        return True, "Eligible for graduation"

    elif action_type == "demote":
        eligible, reason, _ = check_demotion_eligibility(student, school)
        if not eligible:
            return False, f"Student is not eligible for demotion: {reason}"
        return True, "Eligible for demotion"

    return False, f"Unknown action type: {action_type}"


def pre_validate_action(
    selected_students, action_type, school, current_academic_year, terms_to_consider
):
    """
    Pre-validate all selected students before processing the action.

    Args:
        selected_students: List of student IDs
        action_type: Type of action to validate
        school: School object for multi-tenancy
        current_academic_year: Current academic year
        terms_to_consider: Number of terms to consider

    Returns:
        list: List of validation errors (empty if all valid)
    """

    validation_errors = []

    for student_id in selected_students:
        try:
            student = Student.objects.get(id=student_id, school=school)

            # Get student's current status
            performance_data = check_promotion_eligibility(
                student, current_academic_year, terms=terms_to_consider, school=school
            )

            # Determine status based on performance using the eligibility result
            eligible = performance_data["eligible"]
            if eligible:
                # Check if student is in Form 3 (graduation eligible)
                current_assignment = StudentClass.objects.filter(
                    student=student, is_active=True, school=school
                ).first()
                if (
                    current_assignment
                    and current_assignment.assigned_class.form
                    and current_assignment.assigned_class.form.form_number == 3
                ):
                    student_status = "graduate"
                else:
                    student_status = "promote"
            else:
                # Student failed based on performance requirements
                student_status = "retained"

            # Validate eligibility for the action
            eligible, reason = validate_action_eligibility(
                student, action_type, student_status, school
            )
            if not eligible:
                validation_errors.append(f"{student.full_name}: {reason}")

        except Student.DoesNotExist:
            validation_errors.append(f"Student with ID {student_id} not found")
        except Exception as e:
            validation_errors.append(f"Error validating student {student_id}: {str(e)}")

    return validation_errors


def perform_student_action(
    request,
    action_type,
    selected_students,
    current_academic_year=None,
    target_academic_year=None,
    target_class=None,
    terms_to_consider=None,
    school=None,
):
    """Unified function to handle student promotion or graduation actions with enhanced validation"""
    from django.db import transaction
    import logging
    import time

    # Get the logger
    logger = logging.getLogger(__name__)
    start_time = time.time()

    # Ensure current_academic_year is set
    if not current_academic_year:
        current_academic_year = AcademicYear.objects.filter(is_current=True).first()
        if not current_academic_year:
            messages.error(request, "No current academic year found.")
            return redirect("/students/promotion/")

    # Pre-validate all selected students before processing
    validation_errors = pre_validate_action(
        selected_students, action_type, school, current_academic_year, terms_to_consider
    )

    if validation_errors:
        error_message = (
            f"Validation failed for {len(validation_errors)} student(s):\n"
            + "\n".join(validation_errors[:5])
        )
        if len(validation_errors) > 5:
            error_message += f"\n... and {len(validation_errors) - 5} more errors"
        messages.error(request, error_message)
        return redirect("/students/promotion/")

    # Validate target selection for promotion
    if action_type == "promote":
        if not target_academic_year or not target_class:
            messages.error(
                request,
                "Target academic year and target class must be specified for promotion.",
            )
            return redirect("/students/promotion/")

        # Validate target class belongs to target academic year
        if target_class.academic_year != target_academic_year:
            messages.error(
                request,
                f"Target class {target_class.name} does not belong to academic year {target_academic_year.name}.",
            )
            return redirect("/students/promotion/")

    # Prepare for detailed reporting
    result = {
        "success": 0,
        "failed": 0,
        "errors": [],
        "warnings": [],
        "status_counts": {"promote": 0, "graduate": 0, "retained": 0, "incomplete": 0},
        "summary": "",
        "details": "",
        "processing_time": 0,
    }

    logger.info(f"Starting {action_type} action for {len(selected_students)} students")

    # Pre-fetch all students with their assessments to reduce database queries
    students = Student.objects.filter(id__in=selected_students).prefetch_related(
        "assessment_set__class_subject"
    )

    if not students.exists():
        messages.error(request, "No valid students found for the selected action.")
        return redirect("/students/promotion/")

    # Get all current active class assignments
    current_assignments = StudentClass.objects.filter(
        student__in=students, is_active=True
    ).select_related("student", "assigned_class", "assigned_class__learning_area")

    logger.info(
        f"Found {current_assignments.count()} active class assignments for {students.count()} students"
    )

    # Get terms to use for promotion eligibility checking
    # Get all terms for the current academic year, ordered by term number
    academic_terms = Term.objects.filter(
        academic_year=current_academic_year, school=school
    ).order_by("term_number")

    # Get latest terms up to the number of terms to consider
    term_ids = list(academic_terms.values_list("id", flat=True))

    # Ensure terms_to_consider has a default value if None
    if terms_to_consider is None:
        terms_to_consider = 3  # Default to 3 terms
        logger.info(f"terms_to_consider was None, defaulting to {terms_to_consider}")

    # If not enough terms exist in current academic year, log it but don't show disruptive warning
    if len(term_ids) < terms_to_consider:
        logger.info(
            f"Only {len(term_ids)} terms exist in current academic year, but {terms_to_consider} terms requested. Using available terms."
        )

    # Get the latest N terms
    terms_to_use = term_ids[-min(terms_to_consider, len(term_ids)) :]
    terms_to_use_objects = Term.objects.filter(id__in=terms_to_use)

    # Pre-fetch student statuses for validation
    student_statuses = {}

    for student in students:
        # Get student's current class
        current_assignment = current_assignments.filter(
            student=student, is_active=True
        ).first()
        if not current_assignment:
            result["errors"].append(f"No active class found for {student.full_name}")
            result["failed"] += 1
            logger.warning(
                f"No active class found for student {student.id} ({student.full_name})"
            )
            continue

        current_class = current_assignment.assigned_class

        # Get student's assessments for the current year across all terms
        assessments = Assessment.objects.filter(
            student=student,
            class_subject__academic_year=current_academic_year,

            class_subject__is_active=True,

            school=school,
        )

        # Determine status based on assessments and form
        current_form = current_class.form
        if hasattr(current_form, "form_number"):
            current_form = current_form.form_number

        # Count the number of subjects for this class
        class_subject_count = ClassSubject.objects.filter(

            class_name=current_class, academic_year=current_academic_year, is_active=True

        ).count()

        # Determine status based on assessments and form (consistent with main view)
        # Use performance configuration settings instead of hardcoded values
        assessment_count = assessments.count()
        if class_subject_count == 0:
            status = "incomplete"
        elif assessment_count == 0:
            status = "incomplete"
        elif assessment_count < class_subject_count:
            status = "incomplete"
        else:
            # Use check_promotion_eligibility to determine status based on performance requirements
            eligibility_result = check_promotion_eligibility(
                student, current_academic_year, terms_to_use_objects, school=school
            )
            eligible = eligibility_result["eligible"]

            if eligible:
                # Check if student is in Form 3 (graduation eligible)
                if (
                    current_form is not None and current_form == 3
                ):  # Final form students graduate
                    status = "graduate"
                else:
                    status = "promote"
            else:
                status = "retained"

        student_statuses[student.id] = {
            "status": status,
            "current_assignment": current_assignment,
        }

        # Count status for reporting
        if status in result["status_counts"]:
            result["status_counts"][status] += 1

    # Build a lookup for current assignments
    student_assignments = {
        assignment.student.id: assignment for assignment in current_assignments
    }

    # Prepare lists for batch operations
    new_student_classes = []
    new_archived_students = []
    assignments_to_deactivate = []

    # Log validation warnings if needed
    action_description = (
        "promotion"
        if action_type == "promote"
        else ("graduation" if action_type == "graduate" else "demotion")
    )
    if action_type == "promote" and result["status_counts"]["graduate"] > 0:
        warning_msg = f"{result['status_counts']['graduate']} students marked for graduation are selected for {action_description}"
        result["warnings"].append(warning_msg)
        logger.warning(warning_msg)

    if action_type == "graduate" and result["status_counts"]["promote"] > 0:
        warning_msg = f"{result['status_counts']['promote']} students marked for promotion are selected for {action_description}"
        result["warnings"].append(warning_msg)
        logger.warning(warning_msg)

    # Process students in batches to avoid memory issues with large selections
    batch_size = 100  # Adjust based on system capacity
    total_students = len(selected_students)
    processed = 0

    # For promotion, we already have the target class specified
    # No need for complex lookup logic since admin selects specific target class

    with transaction.atomic():
        for student in students:
            try:
                # Get current assignment
                current_assignment = student_assignments.get(student.id)
                if not current_assignment:
                    result["errors"].append(
                        f"No active class found for {student.full_name}"
                    )
                    result["failed"] += 1
                    continue

                current_class = current_assignment.assigned_class
                student_status = student_statuses.get(student.id, {}).get("status")

                # Validate action eligibility with stricter enforcement
                eligible, reason = validate_action_eligibility(
                    student, action_type, student_status, school
                )
                if not eligible:
                    result["errors"].append(f"{student.full_name}: {reason}")
                    result["failed"] += 1
                    continue

                if action_type == "promote":
                    # Handle promotion logic - use the admin-selected target class
                    current_form = current_class.form
                    if hasattr(current_form, "form_number"):
                        current_form = current_form.form_number

                    # Check if target class has capacity
                    if target_class.is_class_full():
                        result["warnings"].append(
                            f"Target class {target_class.name} is at capacity but will be used for {student.full_name}"
                        )

                    # Log the promotion details
                    logger.info(
                        f"Promoting {student.full_name} from {current_class.name} to {target_class.name} (School: {school.name if school else 'None'})"
                    )

                    # Immediately deactivate the current assignment to prevent duplicate active assignments
                    current_assignment.is_active = False
                    current_assignment.save()
                    logger.info(
                        f"Deactivated current assignment ID: {current_assignment.id} for promoted student {student.full_name}"
                    )

                    # Check if there's an existing inactive assignment to the target class
                    existing_assignment = StudentClass.objects.filter(
                        student=student,
                        assigned_class=target_class,
                        is_active=False,
                        school=school,
                    ).first()

                    if existing_assignment:
                        # Reactivate the existing assignment instead of creating a new one
                        existing_assignment.is_active = True
                        existing_assignment.assigned_by = request.user
                        existing_assignment.save()
                        logger.info(
                            f"Reactivated existing assignment ID: {existing_assignment.id} for promoted student {student.full_name} to {target_class.name}"
                        )
                    else:
                        # Create new assignment to target class only if no existing assignment exists
                        new_student_classes.append(
                            StudentClass(
                                student=student,
                                assigned_class=target_class,
                                is_active=True,
                                assigned_by=request.user,
                                school=school,  # Add school for multi-tenancy
                            )
                        )
                        logger.info(
                            f"Created new assignment for promoted student {student.full_name} to {target_class.name}"
                        )

                elif action_type == "graduate":
                    # Handle graduation logic
                    current_form = current_class.form
                    if hasattr(current_form, "form_number"):
                        current_form = current_form.form_number
                    else:
                        current_form = None

                    # Check if student is in Form 3 (graduation eligible)
                    if current_form is None:
                        result["errors"].append(
                            f"{student.full_name} has no form assigned, not eligible for graduation"
                        )
                        result["failed"] += 1
                        continue
                    elif current_form != 3:
                        result["errors"].append(
                            f"{student.full_name} is in Form {current_form}, not eligible for graduation"
                        )
                        result["failed"] += 1
                        continue

                    # Create archived student record with more detailed information
                    # Calculate overall performance metrics across all terms
                    student_assessments = Assessment.objects.filter(
                        student=student,
                        class_subject__academic_year=current_academic_year,

                        class_subject__is_active=True,

                    )

                    avg_score = (
                        student_assessments.aggregate(Avg("total_score"))[
                            "total_score__avg"
                        ]
                        or 0
                    )
                    passed_subjects = student_assessments.filter(
                        total_score__gte=40
                    ).count()
                    total_subjects = student_assessments.count()

                    remarks = (
                        f"Successfully completed senior high school education with "
                        f"average score of {avg_score:.1f}%. "
                        f"Passed {passed_subjects} out of {total_subjects} subjects."
                    )

                    # Get the Form object for Form 3 (prefer JHS 3 for junior high students)
                    form_3 = Form.objects.filter(
                        form_number=3, name__icontains="JHS"
                    ).first()
                    if not form_3:
                        # Fallback to any Form 3 if JHS 3 not found
                        form_3 = Form.objects.filter(form_number=3).first()
                    if not form_3:
                        result["errors"].append(f"Form 3 not found in the system")
                        result["failed"] += 1
                        continue

                    new_archived_students.append(
                        ArchivedStudent(
                            student=student,
                            final_form=form_3,  # Use Form object, not number
                            final_learning_area=current_class.learning_area,
                            archived_by=request.user,
                            remarks=remarks,
                        )
                    )

                    # Immediately deactivate the current assignment for graduation
                    current_assignment.is_active = False
                    current_assignment.save()
                    logger.info(
                        f"Deactivated current assignment ID: {current_assignment.id} for graduated student {student.full_name}"
                    )

                result["success"] += 1
                logger.info(f"Successfully graduated {student.full_name}")
                continue  # Skip the common deactivation logic below

                if action_type == "demote":
                    # Handle demotion logic - move student back to previous class
                    # Find the most recent inactive assignment for this student that's in a different class
                    previous_assignments = (
                        StudentClass.objects.filter(
                            student=student, is_active=False, school=school
                        )
                        .exclude(
                            assigned_class=current_class  # Exclude assignments to the same class
                        )
                        .order_by("-date_assigned")
                    )

                    if not previous_assignments.exists():
                        result["errors"].append(
                            f"{student.full_name} has no previous class assignment to demote to (excluding current class)"
                        )
                        result["failed"] += 1
                        continue

                    # Get the most recent previous assignment in a different class
                    previous_assignment = previous_assignments.first()
                    previous_class = previous_assignment.assigned_class

                    # Additional validation: Ensure the previous class still exists and is valid
                    if not previous_class:
                        result["errors"].append(
                            f"{student.full_name}'s previous class no longer exists"
                        )
                        result["failed"] += 1
                        continue

                    # Check if the previous class is in a valid academic year
                    if not previous_class.academic_year:
                        result["errors"].append(
                            f"{student.full_name}'s previous class has no associated academic year"
                        )
                        result["failed"] += 1
                        continue

                    # Log the demotion details
                    logger.info(
                        f"Demoting {student.full_name} from {current_class.name} (ID: {current_assignment.id}) back to {previous_class.name} (ID: {previous_assignment.id}) (School: {school.name if school else 'None'})"
                    )

                    # Reactivate the previous assignment
                    previous_assignment.is_active = True
                    previous_assignment.assigned_by = request.user
                    previous_assignment.save()
                    logger.info(
                        f"Reactivated previous assignment ID: {previous_assignment.id}"
                    )

                    # Immediately deactivate the current assignment to prevent duplicate active assignments
                    current_assignment.is_active = False
                    current_assignment.save()
                    logger.info(
                        f"Deactivated current assignment ID: {current_assignment.id}"
                    )

                    result["success"] += 1
                    logger.info(
                        f"Successfully demoted {student.full_name} to {previous_class.name}"
                    )
                    continue  # Skip the common deactivation logic below

                # Note: Promotion now uses immediate deactivation, so no batch deactivation needed

                # Update processed count
                processed += 1
                if processed % batch_size == 0:
                    logger.info(f"Processed {processed}/{total_students} students")

            except Exception as e:
                action_name = "promoting" if action_type == "promote" else "graduating"
                error_msg = f"Error {action_name} {student.full_name}: {str(e)}"
                result["errors"].append(error_msg)
                result["failed"] += 1
                logger.error(error_msg, exc_info=True)
                continue

        # Batch database operations
        # Note: All actions now use immediate deactivation, so batch deactivation is no longer needed
        if assignments_to_deactivate:
            logger.warning(
                f"Found {len(assignments_to_deactivate)} assignments marked for batch deactivation, but all actions now use immediate deactivation"
            )

        if new_student_classes and action_type == "promote":
            # Create new assignments in smaller batches
            batch_size = 200
            logger.info(
                f"About to create {len(new_student_classes)} new class assignments"
            )

            for i in range(0, len(new_student_classes), batch_size):
                batch = new_student_classes[i : i + batch_size]
                try:
                    # Additional safety check: Verify no duplicate active assignments exist
                    for assignment in batch:
                        existing_active = StudentClass.objects.filter(
                            student=assignment.student,
                            is_active=True,
                            school=assignment.school,
                        ).exists()
                        if existing_active:
                            logger.error(
                                f"CRITICAL: Found existing active assignment for student {assignment.student.full_name} before creating new one!"
                            )
                            raise Exception(
                                f"Duplicate active assignment detected for student {assignment.student.full_name}"
                            )

                    created = StudentClass.objects.bulk_create(batch)
                    logger.info(
                        f"Created {len(created)} new class assignments (batch {i//batch_size + 1})"
                    )
                    # Log some details of the first few created assignments for debugging
                    for idx, assignment in enumerate(created[:3]):
                        logger.info(
                            f"Assignment {idx+1}: Student: {assignment.student.full_name}, Class: {assignment.assigned_class.name}, Active: {assignment.is_active}, School: {assignment.school.name if assignment.school else 'None'}"
                        )
                except Exception as e:
                    error_msg = f"Error creating class assignments: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    result["errors"].append(error_msg)
                    result["failed"] += len(batch)  # Count these as failures

            result["summary"] = (
                f"Successfully promoted {result['success']} students to {target_class.name}"
            )
            if terms_to_consider:
                result["details"] = f"Based on {terms_to_consider} term evaluation"

        if new_archived_students and action_type == "graduate":
            # Archive students in smaller batches
            batch_size = 200
            logger.info(f"About to archive {len(new_archived_students)} students")

            for i in range(0, len(new_archived_students), batch_size):
                batch = new_archived_students[i : i + batch_size]
                try:
                    created = ArchivedStudent.objects.bulk_create(batch)
                    logger.info(
                        f"Archived {len(created)} students (batch {i//batch_size + 1})"
                    )
                    # Log some details of the first few created archives for debugging
                    for idx, archive in enumerate(created[:3]):
                        logger.info(
                            f"Archive {idx+1}: Student: {archive.student.full_name}, Final Form: {archive.final_form}, Final Learning Area: {archive.final_learning_area.name}"
                        )
                except Exception as e:
                    error_msg = f"Error archiving students: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    result["errors"].append(error_msg)
                    result["failed"] += len(batch)  # Count these as failures

            result["summary"] = f"Successfully graduated {result['success']} students"

        # Set summary for demotion
        if action_type == "demote":
            result["summary"] = (
                f"Successfully demoted {result['success']} students to their previous classes"
            )

    # Set appropriate messages based on results
    set_result_messages(request, result)

    # Calculate and record processing time
    elapsed_time = time.time() - start_time
    result["processing_time"] = elapsed_time
    logger.info(
        f"Completed {action_type} action in {elapsed_time:.2f} seconds. Success: {result['success']}, Failed: {result['failed']}"
    )

    # Redirect with success parameter to show appropriate notification
    if result.get("success", 0) > 0:
        return redirect(f"/students/promotion/?success=true&action={action_type}")
    elif result.get("warnings", []):
        return redirect(f"/students/promotion/?warning=true&action={action_type}")
    else:
        return redirect("/students/promotion/")


def set_result_messages(request, result):
    """Standardized function to set messages from operation results"""
    # Set success message if any operations succeeded
    if result.get("success", 0) > 0:
        success_message = result.get(
            "summary", f"Successfully completed operation for {result['success']} items"
        )
        if result.get("details"):
            success_message += f". {result['details']}"

        # Add performance metrics if available
        if result.get("processing_time"):
            success_message += (
                f" (completed in {result['processing_time']:.2f} seconds)"
            )

        # Add detailed breakdown for success message
        if "status_counts" in result:
            status_details = []
            if result["status_counts"].get("promote", 0) > 0:
                status_details.append(
                    f"{result['status_counts']['promote']} students promoted"
                )
            if result["status_counts"].get("graduate", 0) > 0:
                status_details.append(
                    f"{result['status_counts']['graduate']} students graduated"
                )

            if status_details:
                success_message += f"<br><br>Details: {', '.join(status_details)}"

        # Only set Django messages if we're not using URL parameters for notifications
        # (This prevents duplicate notifications)
        messages.success(request, success_message)

    # Set warning messages for mismatched statuses and class assignments
    if result.get("warnings", []):
        # Show a summary of warnings
        warning_count = len(result.get("warnings", []))
        status_counts = result.get("status_counts", {})

        if warning_count > 0:
            warning_summary = f"Operation completed with {warning_count} warnings"

            # Add status summary if available
            if status_counts:
                status_details = []
                if status_counts.get("promote", 0) > 0:
                    status_details.append(
                        f"{status_counts['promote']} ready to promote"
                    )
                if status_counts.get("graduate", 0) > 0:
                    status_details.append(
                        f"{status_counts['graduate']} ready to graduate"
                    )
                if status_counts.get("retained", 0) > 0:
                    status_details.append(f"{status_counts['retained']} retained")
                if status_counts.get("incomplete", 0) > 0:
                    status_details.append(f"{status_counts['incomplete']} incomplete")

                if status_details:
                    warning_summary += (
                        f"<br><br>Status summary: {', '.join(status_details)}"
                    )

            messages.warning(request, warning_summary)

        # Add detailed warning messages
        warnings = result.get("warnings", [])
        if warnings:
            warning_detail = "<ul>"
            for idx, warning in enumerate(warnings):
                if idx < 5:  # Show only the first 5 warnings
                    warning_detail += f"<li>{warning}</li>"
                else:
                    warning_detail += (
                        f"<li>... and {len(warnings) - 5} more warnings</li>"
                    )
                    break
            warning_detail += "</ul>"

            messages.warning(request, warning_detail)

    # Set error messages if any operations failed
    if result.get("failed", 0) > 0:
        error_message = f"Failed to complete operation for {result['failed']} items."

        # Add detailed error messages in HTML format for Sweet Alert
        errors = result.get("errors", [])
        if errors:
            error_message += "<br><br>Details:<ul>"
            for idx, error in enumerate(errors):
                if idx < 8:  # Show only first 8 errors
                    error_message += f"<li>{error}</li>"
                else:
                    error_message += f"<li>... and {len(errors) - 8} more errors</li>"
                    break
            error_message += "</ul>"

            error_message += "<br>Check the server logs for more details."

        messages.error(request, error_message)


@user_passes_test(is_admin)
def student_performance_detail(request, student_id):
    """Detailed view of student performance for promotion and graduation evaluation"""

    try:
        # Get the user's school for multi-tenancy
        user_school = request.user.school
        if not user_school:
            messages.error(request, "You are not associated with any school.")
            return redirect("student_list")

        # Get current academic year and term from SchoolInformation first (more reliable)
        school_info = SchoolInformation.objects.filter(id=user_school.id).first()

        if school_info and school_info.current_academic_year:
            current_academic_year = school_info.current_academic_year
            logger.debug(
                f"Using academic year from school info: {current_academic_year.name}"
            )
        else:
            current_academic_year = AcademicYear.objects.filter(
                is_current=True, school=user_school
            ).first()
            logger.debug(
                f"Using academic year with is_current=True: {current_academic_year.name if current_academic_year else 'None'}"
            )

        if school_info and school_info.current_term:
            current_term = school_info.current_term
            logger.debug(
                f"Using term from school info: {current_term.term_number} of {current_term.academic_year.name}"
            )
        else:
            current_term = Term.objects.filter(
                is_current=True, school=user_school
            ).first()
            logger.debug(
                f"Using term with is_current=True: {current_term.term_number if current_term else 'None'}"
            )

        if not current_academic_year or not current_term:
            messages.error(request, "Current academic year or term is not set.")
            return redirect("student_list")

        # Get student by ID
        try:
            student = Student.objects.get(id=student_id, school=user_school)
        except Student.DoesNotExist:
            messages.error(request, f"Student with ID {student_id} not found.")
            return redirect("student_promotion")

        # Get the student's current class
        current_class = student.get_current_class()
        if not current_class:
            messages.warning(
                request,
                f"Student {student.full_name} is not assigned to any class currently.",
            )

        # Terms to consider (default to 3 or get from request)
        try:
            terms_to_consider = int(request.GET.get("terms_to_consider", 3))
            if terms_to_consider <= 0:
                terms_to_consider = 3
                messages.warning(
                    request, "Invalid terms count. Using default of 3 terms."
                )
        except (ValueError, TypeError):
            terms_to_consider = 3
            messages.warning(
                request, "Invalid terms parameter. Using default of 3 terms."
            )

        # Get all terms for the current academic year, ordered by term number
        academic_terms = Term.objects.filter(
            academic_year=current_academic_year, school=user_school
        ).order_by("term_number")

        # Log the number of terms found for debugging
        logger.debug(
            f"Found {academic_terms.count()} terms for academic year {current_academic_year.name}"
        )
        for term in academic_terms:
            logger.debug(
                f"Term {term.term_number}: {term.start_date} to {term.end_date}"
            )

        # Get latest terms up to the number of terms to consider
        term_ids = list(academic_terms.values_list("id", flat=True))

        # If not enough terms exist in current academic year, log it but don't show disruptive warning
        if len(term_ids) < terms_to_consider:
            logger.info(
                f"Only {len(term_ids)} terms exist in current academic year, but {terms_to_consider} terms requested. Using available terms."
            )

        # Get the latest N terms (or all available if fewer than requested)
        terms_to_use = (
            term_ids[-min(terms_to_consider, len(term_ids)) :] if term_ids else []
        )
        terms_to_use_objects = Term.objects.filter(id__in=terms_to_use)

        # Use calculate_student_average for consistent calculation
        performance_data = calculate_student_average(
            student, current_academic_year, terms_to_use_objects, school=user_school
        )

        # Get all assessments for this student across selected terms
        student_assessments_by_term = {}
        overall_assessments = []

        for term_id in terms_to_use:
            term = Term.objects.get(id=term_id)

            # Exclude mock exam assessments from promotion management calculations
            term_assessments = Assessment.objects.filter(
                student=student,
                class_subject__academic_year=current_academic_year,
                class_subject__is_active=True,
                term=term,
                school=user_school,
            ).exclude(assessment_type='mock_exam').order_by("class_subject__subject__subject_name")


            student_assessments_by_term[term.term_number] = {
                "term_name": f"Term {term.term_number}",
                "assessments": term_assessments,
            }
            overall_assessments.extend(term_assessments)

        # Use performance_data directly
        student_performance = {
            "student": student,
            "assessments_by_term": student_assessments_by_term,
            "subject_averages": performance_data["subject_averages"],
            "top_subjects": (
                performance_data["subject_averages"][:3]
                if performance_data["subject_averages"]
                else []
            ),
            "bottom_subjects": (
                sorted(
                    performance_data["subject_averages"],
                    key=lambda x: x["avg_score"],
                )[:3]
                if performance_data["subject_averages"]
                else []
            ),
            "total_subjects": len(performance_data["subject_averages"]),
            "passed_subjects": performance_data["passed_subjects"],
            "failed_subjects": performance_data["failed_subjects"],
            "avg_score": performance_data["average_score"],
            "terms_considered": terms_to_consider,
            "terms_data": [
                Term.objects.get(id=term_id).term_number for term_id in terms_to_use
            ],
        }

        # Get current form and determine promotion status
        current_form = None
        if current_class:
            current_form = current_class.form
            if hasattr(current_form, "form_number"):
                current_form = current_form.form_number

        # Get all subjects for student's class in the current term (if current_class exists)
        subject_count = 0
        if current_class:
            # Check if subjects are assigned to this class
            student_subjects = ClassSubject.objects.filter(

                class_name=current_class, academic_year=current_academic_year, is_active=True

            )

            # Log the subjects found for debugging
            subject_count = student_subjects.count()
            logger.debug(
                f"Found {subject_count} subjects for class {current_class.name}"
            )

            for subject in student_subjects:
                logger.debug(f"Subject: {subject.subject.subject_name}")

            if subject_count == 0:
                messages.warning(
                    request,
                    f"No subjects are assigned to class {current_class.name} for the current term.",
                )

        # Determine student status using performance configuration
        if len(performance_data["subject_averages"]) < subject_count:
            status = "incomplete"
            reason = f"Missing assessments for {subject_count - len(performance_data['subject_averages'])} subjects across terms"
        else:
            # Use check_promotion_eligibility to determine status based on performance requirements
            eligibility_result = check_promotion_eligibility(
                student, current_academic_year, terms_to_use_objects, school=user_school
            )
            eligible = eligibility_result["eligible"]

            if eligible:
                # Student passed all subjects per performance requirements
                if (
                    current_form is not None and current_form == 3
                ):  # SHS 3 students graduate
                    status = "graduate"
                    reason = "Completed SHS 3 successfully"
                else:
                    next_form_number = current_form + 1 if current_form else 1
                    next_form = Form.objects.filter(
                        form_number=next_form_number, school=user_school
                    ).first()
                    next_form_name = (
                        next_form.name if next_form else f"Form {next_form_number}"
                    )
                    status = "promote"
                    reason = f"Ready for {next_form_name}"
            else:
                # Student failed based on performance requirements
                status = "retained"
                reason = eligibility_result.get(
                    "reason", "Failed to meet promotion requirements"
                )

        # Ensure terms_to_consider is an integer for template comparison
        terms_to_consider_int = int(terms_to_consider)

        # Get scoring configuration
        scoring_config = None
        if user_school:
            scoring_config = ScoringConfiguration.get_active_config(user_school)

        context = {
            "current_academic_year": current_academic_year,
            "current_term": current_term,
            "student_performance": student_performance,
            "terms_to_consider": terms_to_consider_int,  # Ensure this is an int
            "available_terms": len(term_ids),
            "status": status,
            "reason": reason,
            "current_class": current_class,
            "subject_count": subject_count,
            "school": user_school,
            "scoring_config": scoring_config,
        }

        return render(request, "student/student_performance_detail.html", context)

    except Exception as e:
        # Log the exception for debugging
        logger.error(f"Error in student_performance_detail: {str(e)}", exc_info=True)
        messages.error(
            request, f"An error occurred while processing student performance: {str(e)}"
        )
        return redirect("student_promotion")



def handle_ajax_class_data_request(request):
    """
    Handle AJAX requests for loading class-specific promotion data
    """
    from django.http import JsonResponse
    from django.db.models import Q
    
    try:
        # Get the current user's school
        user_school = request.user.school
        if not user_school:
            return JsonResponse({
                'success': False,
                'message': 'You are not associated with any school.'
            })

        # Get current academic year
        school_info = SchoolInformation.objects.filter(id=user_school.id).first()
        if school_info and school_info.current_academic_year:
            current_academic_year = school_info.current_academic_year
        else:
            current_academic_year = AcademicYear.objects.filter(
                is_current=True, school=user_school
            ).first()

        if not current_academic_year:
            return JsonResponse({
                'success': False,
                'message': 'Current academic year is not set.'
            })

        # Get request parameters
        class_id = request.POST.get('class_id')
        search_query = request.POST.get('search', '')
        form_filter = request.POST.get('form_filter', '')
        learning_area_filter = request.POST.get('learning_area_filter', '')
        status_filter = request.POST.get('status_filter', '')
        terms_to_consider = int(request.POST.get('terms_to_consider', 3))

        if not class_id:
            return JsonResponse({
                'success': False,
                'message': 'Class ID is required.'
            })

        # Get the selected class
        try:
            selected_class = Class.objects.get(id=class_id, school=user_school)
        except Class.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Selected class not found.'
            })

        # Get all terms for the current academic year
        academic_terms = Term.objects.filter(
            academic_year=current_academic_year, school=user_school
        ).order_by("term_number")

        # Get latest terms up to the number of terms to consider
        term_ids = list(academic_terms.values_list("id", flat=True))
        terms_to_use = term_ids[-min(terms_to_consider, len(term_ids)):]
        terms_to_use_objects = Term.objects.filter(id__in=terms_to_use)

        # Get students for the selected class
        active_students = Student.objects.filter(
            studentclass__is_active=True,
            school=user_school,
            studentclass__assigned_class=selected_class,
            studentclass__assigned_class__academic_year=current_academic_year,
        ).distinct()

        # Apply search filter if provided
        if search_query:
            active_students = active_students.filter(
                Q(full_name__icontains=search_query)
                | Q(admission_number__icontains=search_query)
            )

        # Apply form filter if provided
        if form_filter:
            active_students = active_students.filter(
                studentclass__assigned_class__form__form_number=form_filter
            )

        # Apply learning area filter if provided
        if learning_area_filter:
            active_students = active_students.filter(
                studentclass__assigned_class__learning_area_id=learning_area_filter
            )

        # Prepare student data
        students_data = []
        for student in active_students:
            current_class = student.get_current_class()
            if not current_class:
                continue

            # Use check_promotion_eligibility utility to determine promotion status
            eligibility_result = check_promotion_eligibility(
                student, current_academic_year, terms_to_use_objects, school=user_school
            )

            # Extract performance data
            performance = eligibility_result["performance"]
            eligible = eligibility_result["eligible"]
            reason = eligibility_result.get("reason", "")

            # Determine status
            if eligible:
                if current_class.form.form_number >= 4:  # Assuming 4 is the highest form
                    status = "graduate"
                else:
                    status = "promote"
            else:
                # Check if student has incomplete subjects first
                if performance["incomplete_subjects"] > 0:
                    status = "incomplete"
                else:
                    status = "retained"

            # Apply status filter if provided
            if status_filter and status != status_filter:
                continue

            # Get demotion eligibility
            demotion_eligible = False
            demotion_reason = "No previous class assignments found"
            previous_class = None

            # Check if student has previous class assignments
            previous_assignments = StudentClass.objects.filter(
                student=student,
                is_active=False
            ).order_by('-date_assigned').first()

            if previous_assignments:
                demotion_eligible = True
                demotion_reason = f"Can demote to {previous_assignments.assigned_class.name}"
                previous_class = previous_assignments.assigned_class.name

            student_data = {
                'student_id': student.id,
                'admission_number': student.admission_number,
                'full_name': student.full_name,
                'current_class_name': current_class.name,
                'learning_area_name': current_class.learning_area.name,
                'avg_score': round(float(performance["average_score"]), 1),  # Ensure it's a float
                'status': status,
                'reason': str(reason) if reason else '',  # Ensure it's a string
                'demotion_eligible': bool(demotion_eligible),  # Ensure it's a boolean
                'demotion_reason': str(demotion_reason) if demotion_reason else '',
                'previous_class': str(previous_class) if previous_class else None,
                'failed_subjects': int(performance["failed_subjects"]),  # Ensure it's an int
                'failed_subject_details': performance.get("failed_subject_details", [])
            }

            students_data.append(student_data)

        # Prepare class data
        class_data = {
            'id': selected_class.id,
            'name': selected_class.name,
            'form_name': selected_class.form.name,
            'learning_area': selected_class.learning_area.name,
            'academic_year_name': selected_class.academic_year.name,
            'current_students': selected_class.get_current_student_count(),
            'max_students': selected_class.maximum_students,
            'is_full': bool(selected_class.is_class_full)  # Convert to boolean explicitly
        }

        return JsonResponse({
            'success': True,
            'class_data': class_data,
            'students': students_data,
            'total_students': len(students_data)
        })

    except Exception as e:
        logger.error(f"Error in handle_ajax_class_data_request: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        })

