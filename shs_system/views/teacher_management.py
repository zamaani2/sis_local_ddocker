import logging

# Django imports
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import (
    login_required,
    user_passes_test,
)
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse

# Local imports
from shs_system.forms import TeacherForm
from shs_system.models import (
    Teacher,
    Class,
    Subject,
    TeacherSubjectAssignment,
    AcademicYear,
    Term,
    User,
    ClassTeacher,
    Department,
    ClassSubject,

    SchoolInformation,

)

# Configure logger
logger = logging.getLogger(__name__)


def is_admin(user):
    return user.is_authenticated and user.role == "admin"


def generate_random_password(include_symbol=False):
    """
    Generate a password with format 'pas' + 6 random digits + optional symbol

    Args:
        include_symbol (bool): Whether to include a random symbol

    Returns:
        str: Generated password
    """
    # Start with 'pas' prefix
    password = "pas"

    # Add 6 random digits
    digits = "".join(random.choice(string.digits) for _ in range(6))
    password += digits

    # Add a random symbol if requested
    if include_symbol:
        password += random.choice(string.punctuation)

    return password


def generate_staff_id():
    import random
    import string

    prefix = "".join(random.choices(string.ascii_uppercase, k=2))
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=3))
    staff_id = f"{prefix}{suffix}"

    # Check if ID already exists and regenerate if necessary
    while Teacher.objects.filter(staff_id=staff_id).exists():
        prefix = "".join(random.choices(string.ascii_uppercase, k=2))
        suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=3))
        staff_id = f"{prefix}{suffix}"

    return staff_id


@login_required
@user_passes_test(is_admin)
def teacher_list(request):
    """
    View for displaying a list of all teachers with department filters.

    Handles AJAX requests for clearing session messages and regular GET requests
    for rendering the teacher list page.

    Args:
        request (HttpRequest): The request object

    Returns:
        HttpResponse: The rendered response or empty success response for AJAX
    """
    # Handle AJAX request to clear messages
    if request.headers.get("X-Requested-With") == "XMLHttpRequest" and request.GET.get(
        "clear_messages"
    ):
        # Clear all messages for this session
        storage = messages.get_messages(request)
        for _ in storage:
            # Iterating through messages marks them as processed
            pass
        storage.used = True
        return HttpResponse(status=204)  # Return empty success response

    # Get user's school for multi-tenancy
    school = request.user.school

    # Get all distinct departments for the filter dropdown, filtered by school
    departments = Department.objects.filter(school=school).order_by("name")

    # Optimize query with select_related for department to avoid N+1 query problem
    # Filter teachers by school for multi-tenancy
    teachers = (
        Teacher.objects.select_related("department")
        .filter(school=school)
        .order_by("full_name")
    )

    # Efficiently fetch associated user accounts in a single query
    teacher_ids = [teacher.id for teacher in teachers]
    user_map = {
        user.teacher_profile_id: user
        for user in User.objects.filter(teacher_profile_id__in=teacher_ids)
    }

    # Prepare teacher data with user accounts and classes
    for teacher in teachers:
        teacher.user = user_map.get(teacher.id)
        # Count assigned classes
        teacher.total_assigned_classes = teacher.total_assigned_classes()

    context = {
        "teachers": teachers,
        "departments": departments,
        "page_title": "Teacher Management",
        "school": school,  # Add school to context
    }

    return render(request, "teacher/teacher_list.html", context)


@login_required
@user_passes_test(is_admin)
def teacher_detail(request, staff_id):
    """
    Display detailed information about a specific teacher including their assignments.

    Shows the teacher's profile details, class assignments as class teacher,
    and subject teaching assignments for the current academic year.

    Args:
        request (HttpRequest): The request object
        staff_id (str): The staff ID of the teacher

    Returns:
        HttpResponse: The rendered teacher detail page
    """
    # Get user's school for multi-tenancy
    school = request.user.school

    # Get teacher with department information in a single query, ensure belongs to user's school
    teacher = get_object_or_404(
        Teacher.objects.select_related("department"), staff_id=staff_id, school=school
    )

    try:
        # Get current academic year and term for the school
        current_academic_year = AcademicYear.objects.filter(
            school=school, is_current=True
        ).first()
        if not current_academic_year:
            current_academic_year = AcademicYear.objects.filter(is_current=True).first()

        current_term = Term.objects.filter(school=school, is_current=True).first()
        if not current_term:
            current_term = Term.objects.filter(is_current=True).first()

        if not current_academic_year or not current_term:
            messages.error(request, "No active academic year or term found")
            return redirect("teacher_list")
    except Exception as e:
        messages.error(request, f"Error retrieving academic year or term: {str(e)}")
        return redirect("teacher_list")

    # Get teacher's class assignments using optimized query, filtered by school
    class_teacher_assignments = ClassTeacher.objects.filter(
        teacher=teacher,
        academic_year=current_academic_year,
        is_active=True,
        school=school,
    ).select_related("class_assigned")

    # Get classes the teacher is assigned to as class teacher
    class_teacher_of = [ct.class_assigned for ct in class_teacher_assignments]

    # Get teacher's subject assignments with optimized query, filtered by school

    subject_assignments_query = TeacherSubjectAssignment.objects.filter(

        teacher=teacher,
        academic_year=current_academic_year,
        is_active=True,
        school=school,
    ).select_related("class_assigned", "subject")


    # Filter out assignments where ClassSubject is not active
    # Get active class-subject combinations
    active_class_subjects = ClassSubject.objects.filter(
        academic_year=current_academic_year, is_active=True
    ).values_list('class_name_id', 'subject_id')
    
    # Filter assignments to only include those with active ClassSubject
    filtered_assignments = []
    for assignment in subject_assignments_query:
        if (assignment.class_assigned.id, assignment.subject.id) in active_class_subjects:
            filtered_assignments.append(assignment)
    
    subject_assignments = filtered_assignments


    # Get available classes and subjects for assignment, filtered by school
    available_classes = Class.objects.filter(
        academic_year=current_academic_year, school=school
    )
    available_subjects = Subject.objects.filter(school=school).order_by("subject_name")

    # Get user account associated with this teacher
    user_account = User.objects.filter(teacher_profile=teacher).first()

    context = {
        "teacher": teacher,
        "class_teacher_of": class_teacher_of,
        "subject_assignments": subject_assignments,
        "current_academic_year": current_academic_year,
        "current_term": current_term,
        "available_classes": available_classes,
        "available_subjects": available_subjects,
        "user_account": user_account,
        "page_title": f"Teacher Profile: {teacher.full_name}",
        "school": school,  # Add school to context
    }

    return render(request, "teacher/teacher_detail.html", context)


@login_required
@user_passes_test(is_admin)
def add_teacher(request):
    """
    View for adding a new teacher to the system.

    Handles both form submission and rendering the form.
    Creates a user account for the teacher if requested.

    Args:
        request (HttpRequest): The request object

    Returns:
        HttpResponse: Redirect to teacher list on success or rendered form with errors
        JsonResponse: JSON response for AJAX requests
    """
    # Get user's school for multi-tenancy
    school = request.user.school

    if request.method == "POST":
        form = TeacherForm(request.POST, request.FILES)
        if form.is_valid():
            # Create teacher but don't save yet
            teacher = form.save(commit=False)
            # Set the school
            teacher.school = school
            # Now save the teacher
            teacher.save()

            # Check if we should create a user account
            create_account = request.POST.get("create_account")
            user = None
            success_message = ""

            if create_account:
                email = form.cleaned_data.get("email")
                password = form.cleaned_data.get("password")

                if email and password:
                    try:
                        # Create user account
                        user = User.objects.create_user(
                            username=email,
                            email=email,
                            password=password,
                            role="teacher",
                            full_name=teacher.full_name,
                            school=school,  # Set the school for multi-tenancy
                        )
                        # Link teacher to user
                        user.teacher_profile = teacher
                        user.save()

                        success_message = f'Teacher "{teacher.full_name}" added successfully with user account.'
                    except Exception as e:
                        success_message = f"Error creating user account: {str(e)}. Teacher was added but without an account."
                else:
                    if not email:
                        success_message = "Teacher added but no user account was created due to missing email."
                    elif not password:
                        success_message = "Teacher added but no user account was created due to missing password."
                    else:
                        success_message = "Teacher added but no user account was created due to missing email or password."
            else:
                success_message = f'Teacher "{teacher.full_name}" added successfully.'

            # Add message for non-AJAX requests
            if not request.headers.get("X-Requested-With") == "XMLHttpRequest":
                messages.success(request, success_message)

            # Handle AJAX requests
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {
                        "success": True,
                        "message": success_message,
                        "redirect": reverse("teacher_list"),
                        "teacher": {
                            "staff_id": teacher.staff_id,
                            "full_name": teacher.full_name,
                            "department": (
                                teacher.department.name if teacher.department else ""
                            ),
                            "department_id": (
                                teacher.department.id if teacher.department else ""
                            ),
                            "gender": teacher.gender,
                            "contact_number": teacher.contact_number,
                            "email": email if email else "",
                            "total_assigned_classes": 0,
                            "user": bool(user),
                        },
                    }
                )

            return redirect("teacher_list")
        else:
            # Form is invalid
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                # Return form errors as JSON for AJAX requests
                errors_dict = {}
                for field, errors in form.errors.items():
                    errors_dict[field] = [str(error) for error in errors]

                return JsonResponse(
                    {
                        "success": False,
                        "errors": errors_dict,
                        "message": "There were errors in your submission. Please check the form.",
                    },
                    status=400,
                )
    else:
        form = TeacherForm()

    context = {
        "form": form,
        "title": "Add New Teacher",
        "school": school,  # Add school to context
    }

    return render(request, "teacher/teacher_form.html", context)


@login_required
@user_passes_test(is_admin)
def edit_teacher(request, staff_id):
    """
    View for editing an existing teacher's details.

    Handles both form submission and rendering the form with existing data.
    Updates the associated user account if it exists.

    Args:
        request (HttpRequest): The request object
        staff_id (str): The staff ID of the teacher to edit

    Returns:
        HttpResponse: Redirect to teacher list on success or rendered form with errors
        JsonResponse: JSON response for AJAX requests
    """
    # Get user's school for multi-tenancy
    school = request.user.school

    # Get teacher, ensuring they belong to user's school
    teacher = get_object_or_404(Teacher, staff_id=staff_id, school=school)

    # Get associated user account if it exists
    user = User.objects.filter(teacher_profile=teacher).first()

    if request.method == "POST":
        form = TeacherForm(
            request.POST, request.FILES, instance=teacher, existing_user=user
        )
        if form.is_valid():
            # Update teacher but don't save yet
            updated_teacher = form.save(commit=False)
            # Ensure school remains the same
            updated_teacher.school = school
            # Now save the teacher
            updated_teacher.save()

            # Update user account if it exists
            update_account = request.POST.get(
                "create_account"
            )  # Changed from update_account to create_account to match form
            email = request.POST.get("email")

            if update_account and user:
                if email:
                    user.email = email
                    user.username = email
                    user.full_name = updated_teacher.full_name
                    user.save()
                    success_message = f'Teacher "{updated_teacher.full_name}" and user account updated successfully.'
                else:
                    success_message = "Teacher updated but user account email could not be updated due to missing email."
            elif update_account and not user and email:
                # Create new user if requested and email provided
                try:
                    # Use provided password or generate a random one
                    password = request.POST.get("password")
                    if not password:
                        password = User.objects.make_random_password()

                    user = User.objects.create_user(
                        username=email,
                        email=email,
                        password=password,
                        full_name=updated_teacher.full_name,
                        role="teacher",
                        school=school,
                    )
                    user.teacher_profile = updated_teacher
                    user.save()

                    if request.POST.get("password"):
                        success_message = f'Teacher "{updated_teacher.full_name}" updated and new user account created with provided password.'
                    else:
                        success_message = f'Teacher "{updated_teacher.full_name}" updated and new user account created with random password.'
                except Exception as e:
                    success_message = (
                        f"Teacher updated but failed to create user account: {str(e)}"
                    )
            else:
                success_message = (
                    f'Teacher "{updated_teacher.full_name}" updated successfully.'
                )

            # Add message for non-AJAX requests
            if not request.headers.get("X-Requested-With") == "XMLHttpRequest":
                messages.success(request, success_message)

            # Handle AJAX requests
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {
                        "success": True,
                        "message": success_message,
                        "teacher": {
                            "staff_id": teacher.staff_id,
                            "full_name": teacher.full_name,
                            "department": (
                                teacher.department.name if teacher.department else ""
                            ),
                            "department_id": (
                                teacher.department.id if teacher.department else ""
                            ),
                            "gender": teacher.gender,
                            "contact_number": teacher.contact_number,
                            "email": email if email else (user.email if user else ""),
                            "user": bool(user),
                        },
                    }
                )

            # For regular form submissions, redirect to teacher list
            return redirect("teacher_list")
        else:
            # Form is invalid
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                # Return form errors as JSON for AJAX requests
                errors_dict = {}
                for field, errors in form.errors.items():
                    errors_dict[field] = [str(error) for error in errors]

                return JsonResponse(
                    {
                        "success": False,
                        "errors": errors_dict,
                        "message": "There were errors in your submission. Please check the form.",
                    },
                    status=400,
                )
    else:
        # Pre-populate email from user account if it exists
        initial_data = {}
        if user:
            initial_data["email"] = user.email

        form = TeacherForm(instance=teacher, initial=initial_data, existing_user=user)

    # For non-AJAX requests, render the full template
    context = {
        "form": form,
        "teacher": teacher,
        "user": user,
        "title": f"Edit Teacher: {teacher.full_name}",
        "school": school,  # Add school to context
    }

    # For AJAX GET requests, we could return form data as JSON
    if (
        request.method == "GET"
        and request.headers.get("X-Requested-With") == "XMLHttpRequest"
    ):
        return JsonResponse(
            {
                "teacher": {
                    "staff_id": teacher.staff_id,
                    "full_name": teacher.full_name,
                    "department": (
                        teacher.department.name if teacher.department else ""
                    ),
                    "department_id": (
                        teacher.department.id if teacher.department else ""
                    ),
                    "gender": teacher.gender,
                    "contact_number": teacher.contact_number,
                    "email": user.email if user else "",
                }
            }
        )

    return render(request, "teacher/edit_teacher.html", context)


@login_required
@user_passes_test(is_admin)
def delete_teacher(request, staff_id):
    """
    Delete a teacher and their associated user account if any.

    Validates that the teacher has no assigned classes before deletion.
    Uses a transaction to ensure both teacher and user are deleted together.

    Args:
        request (HttpRequest): The request object
        staff_id (str): The staff ID of the teacher to delete

    Returns:
        HttpResponse: Redirect to teacher list or JSON response for AJAX requests
    """
    # Get user's school for multi-tenancy
    school = request.user.school

    # Ensure teacher belongs to user's school
    teacher = get_object_or_404(Teacher, staff_id=staff_id, school=school)

    if request.method != "POST":
        # Non-POST requests - just redirect to teacher list
        return redirect("teacher_list")

    try:
        teacher_name = teacher.full_name

        # Check if teacher has assigned classes
        assigned_classes = teacher.total_assigned_classes()
        if assigned_classes > 0:
            raise ValidationError(
                f"Cannot delete teacher with {assigned_classes} assigned classes. "
                f"Please reassign or remove these classes first."
            )

        # Check if teacher has subject assignments, filtered by school
        subject_assignments = TeacherSubjectAssignment.objects.filter(
            teacher=teacher, is_active=True, school=school
        ).exists()

        if subject_assignments:
            raise ValidationError(
                "Cannot delete teacher with active subject assignments. "
                "Please remove all subject assignments first."
            )

        # Use transaction to ensure both operations succeed or fail together
        with transaction.atomic():
            # Find associated user account if it exists
            associated_user = User.objects.filter(teacher_profile=teacher).first()

            if associated_user:
                # Log user deletion for audit
                logger.info(
                    f"Admin {request.user.username} deleted user account for {associated_user.email}"
                )
                associated_user.delete()

                # Only add the message if this is not an AJAX request or if specifically requested
                if not request.headers.get(
                    "X-Requested-With"
                ) == "XMLHttpRequest" or request.POST.get("include_messages"):
                    messages.info(
                        request,
                        f"User account for {teacher_name} has been deleted.",
                    )

            # Log teacher deletion for audit
            logger.info(
                f"Admin {request.user.username} deleted teacher {teacher_name} ({staff_id})"
            )

            # Delete the teacher
            teacher.delete()

            success_message = f"Teacher {teacher_name} has been deleted successfully."
            messages.success(request, success_message)

        # Handle AJAX requests differently
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {
                    "status": "success",
                    "message": success_message,
                    "redirect": reverse("teacher_list"),
                }
            )

    except ValidationError as e:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
        messages.error(request, str(e))
    except Exception as e:
        # Log unexpected errors
        logger.error(f"Unexpected error in delete_teacher: {str(e)}", exc_info=True)
        error_message = f"Error deleting teacher: {str(e)}"
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {"status": "error", "message": error_message}, status=500
            )
        messages.error(request, error_message)

    # For non-AJAX requests
    return redirect("teacher_list")


@login_required
@user_passes_test(is_admin)
def assign_class_teacher(request, staff_id):
    """
    Assign a teacher as a class teacher to a specific class.

    Handles reassignment of class teachers and creation of new class teacher assignments.

    Args:
        request (HttpRequest): The request object
        staff_id (str): The staff ID of the teacher to assign

    Returns:
        HttpResponse: JSON response for API requests or rendered template for GET
    """
    # Get user's school for multi-tenancy
    school = request.user.school

    if request.method == "POST":
        try:
            # Ensure teacher belongs to user's school
            teacher = get_object_or_404(Teacher, staff_id=staff_id, school=school)
            class_id = request.POST.get("class_id")

            if not class_id:
                return JsonResponse(
                    {"success": False, "message": "Class ID is required."}
                )

            # Ensure class belongs to user's school
            class_obj = get_object_or_404(Class, id=class_id, school=school)

            try:
                # Get current academic year for the school
                current_academic_year = AcademicYear.objects.filter(
                    school=school, is_current=True
                ).first()
                if not current_academic_year:
                    current_academic_year = AcademicYear.objects.filter(
                        is_current=True
                    ).first()

                if not current_academic_year:
                    return JsonResponse(
                        {"success": False, "message": "No active academic year found."}
                    )
            except AcademicYear.DoesNotExist:
                return JsonResponse(
                    {"success": False, "message": "No active academic year found."}
                )

            # Use transaction for data consistency
            with transaction.atomic():
                # Check for existing active class teacher, filtered by school
                existing_class_teacher = ClassTeacher.objects.filter(
                    class_assigned=class_obj,
                    academic_year=current_academic_year,
                    is_active=True,
                    school=school,
                ).first()

                # Check for deactivated class teacher assignment, filtered by school
                deactivated_assignment = ClassTeacher.objects.filter(
                    class_assigned=class_obj,
                    academic_year=current_academic_year,
                    is_active=False,
                    school=school,
                ).first()

                if existing_class_teacher:
                    # If the class already has this teacher, do nothing
                    if existing_class_teacher.teacher == teacher:
                        return JsonResponse(
                            {
                                "success": True,
                                "message": f"{teacher.full_name} is already the class teacher for {class_obj.name}.",
                            }
                        )

                    # Update the class teacher assignment
                    previous_teacher = existing_class_teacher.teacher.full_name
                    existing_class_teacher.teacher = teacher
                    existing_class_teacher.assigned_by = request.user
                    existing_class_teacher.save()

                    # Log this change
                    logger.info(
                        f"Admin {request.user.username} changed class teacher for {class_obj.name} "
                        f"from {previous_teacher} to {teacher.full_name}"
                    )

                    return JsonResponse(
                        {
                            "success": True,
                            "message": f"Successfully changed class teacher for {class_obj.name} from {previous_teacher} to {teacher.full_name}.",
                        }
                    )
                elif deactivated_assignment:
                    # Reactivate the deactivated assignment and update teacher
                    previous_teacher = (
                        deactivated_assignment.teacher.full_name
                        if deactivated_assignment.teacher != teacher
                        else None
                    )
                    deactivated_assignment.teacher = teacher
                    deactivated_assignment.is_active = True
                    deactivated_assignment.assigned_by = request.user
                    deactivated_assignment.save()

                    # Log this reactivation
                    logger.info(
                        f"Admin {request.user.username} reactivated class teacher assignment for {class_obj.name} "
                        f"to {teacher.full_name}"
                    )

                    if previous_teacher:
                        message = f"Successfully reassigned class teacher for {class_obj.name} from {previous_teacher} to {teacher.full_name}."
                    else:
                        message = f"Successfully reactivated class teacher assignment for {class_obj.name} to {teacher.full_name}."

                    return JsonResponse({"success": True, "message": message})
                else:
                    # Create new class teacher assignment with school
                    class_teacher = ClassTeacher.objects.create(
                        teacher=teacher,
                        class_assigned=class_obj,
                        academic_year=current_academic_year,
                        assigned_by=request.user,
                        school=school,  # Set the school for multi-tenancy
                    )

                    # Log new assignment creation
                    logger.info(
                        f"Admin {request.user.username} assigned {teacher.full_name} as class teacher for {class_obj.name}"
                    )

                    return JsonResponse(
                        {
                            "success": True,
                            "message": f"Successfully assigned {teacher.full_name} as class teacher for {class_obj.name}.",
                        }
                    )
        except Teacher.DoesNotExist:
            return JsonResponse({"success": False, "message": "Teacher not found."})
        except Class.DoesNotExist:
            return JsonResponse({"success": False, "message": "Class not found."})
        except Exception as e:
            logger.error(f"Error assigning class teacher: {str(e)}", exc_info=True)
            return JsonResponse({"success": False, "message": str(e)})

    # GET request - show form
    teacher = get_object_or_404(Teacher, staff_id=staff_id, school=school)
    try:
        # Get current academic year for the school
        current_academic_year = AcademicYear.objects.filter(
            school=school, is_current=True
        ).first()
        if not current_academic_year:
            current_academic_year = AcademicYear.objects.filter(is_current=True).first()

        if not current_academic_year:
            messages.error(request, "No active academic year found")
            return redirect("teacher_list")

        # Filter available classes by school
        available_classes = Class.objects.filter(
            academic_year=current_academic_year, school=schoo
        )
    except AcademicYear.DoesNotExist:
        messages.error(request, "No active academic year found")
        return redirect("teacher_list")

    return render(
        request,
        "teacher/teacher_detail.html",
        {
            "teacher": teacher,
            "available_classes": available_classes,
            "current_academic_year": current_academic_year,
            "school": school,  # Add school to context
        },
    )


@login_required
@user_passes_test(is_admin)
def assign_subject(request, staff_id):
    """
    Assign a subject to a teacher for a specific class.

    Handles reassignment of subjects and creation of new subject assignments.

    Args:
        request (HttpRequest): The request object
        staff_id (str): The staff ID of the teacher to assign

    Returns:
        HttpResponse: JSON response for API requests or rendered template for GET
    """
    # Get user's school for multi-tenancy
    school = request.user.school

    if request.method == "POST":
        try:
            # Ensure teacher belongs to user's school
            teacher = get_object_or_404(Teacher, staff_id=staff_id, school=school)
            subject_id = request.POST.get("subject_id")
            class_id = request.POST.get("class_id")

            # Validate required fields
            if not subject_id:
                return JsonResponse(
                    {"success": False, "message": "Subject ID is required."}
                )

            if not class_id:
                return JsonResponse(
                    {"success": False, "message": "Class ID is required."}
                )

            # Ensure subject and class belong to user's school
            subject = get_object_or_404(Subject, id=subject_id, school=school)
            class_obj = get_object_or_404(Class, id=class_id, school=school)

            try:
                # Get current academic year for the school
                current_academic_year = AcademicYear.objects.filter(
                    school=school, is_current=True
                ).first()
                if not current_academic_year:
                    current_academic_year = AcademicYear.objects.filter(
                        is_current=True
                    ).first()

                if not current_academic_year:
                    return JsonResponse(
                        {"success": False, "message": "No active academic year found."}
                    )
            except AcademicYear.DoesNotExist:
                return JsonResponse(
                    {"success": False, "message": "No active academic year found."}
                )

            # Verify that the subject is assigned to the class
            subject_assigned_to_class = ClassSubject.objects.filter(
                subject=subject,
                class_name=class_obj,
                academic_year=current_academic_year,

                is_active=True

            ).exists()

            if not subject_assigned_to_class:
                return JsonResponse(
                    {
                        "success": False,
                        "message": f"The subject '{subject.subject_name}' is not assigned to class '{class_obj.name}'. Please assign the subject to the class first.",
                    }
                )

            # Use transaction for data consistency
            with transaction.atomic():
                # Check for existing active assignment, filtered by school
                existing_assignment = TeacherSubjectAssignment.objects.filter(
                    subject=subject,
                    class_assigned=class_obj,
                    academic_year=current_academic_year,
                    is_active=True,
                    school=school,
                ).first()

                # Check for existing deactivated assignment, filtered by school
                deactivated_assignment = TeacherSubjectAssignment.objects.filter(
                    subject=subject,
                    class_assigned=class_obj,
                    academic_year=current_academic_year,
                    is_active=False,
                    school=school,
                ).first()

                if existing_assignment:
                    # If existing assignment is to the same teacher, don't do anything
                    if existing_assignment.teacher == teacher:
                        return JsonResponse(
                            {
                                "success": True,
                                "message": f"{teacher.full_name} is already assigned to teach {subject.subject_name} for {class_obj.name}.",
                            }
                        )

                    # Update the existing assignment to the new teacher
                    previous_teacher = existing_assignment.teacher.full_name
                    existing_assignment.teacher = teacher
                    existing_assignment.assigned_by = request.user
                    existing_assignment.save()

                    # Log this change
                    logger.info(
                        f"Admin {request.user.username} reassigned {subject.subject_name} for {class_obj.name} "
                        f"from {previous_teacher} to {teacher.full_name}"
                    )

                    return JsonResponse(
                        {
                            "success": True,
                            "message": f"Successfully reassigned {subject.subject_name} from {previous_teacher} to {teacher.full_name} for {class_obj.name}.",
                        }
                    )
                elif deactivated_assignment:
                    # Reactivate the deactivated assignment and update teacher
                    previous_teacher = (
                        deactivated_assignment.teacher.full_name
                        if deactivated_assignment.teacher != teacher
                        else None
                    )
                    deactivated_assignment.teacher = teacher
                    deactivated_assignment.is_active = True
                    deactivated_assignment.assigned_by = request.user
                    deactivated_assignment.save()

                    # Log this reactivation
                    logger.info(
                        f"Admin {request.user.username} reactivated subject assignment of {subject.subject_name} "
                        f"to {teacher.full_name} for {class_obj.name}"
                    )

                    if previous_teacher:
                        message = f"Successfully reassigned {subject.subject_name} from {previous_teacher} to {teacher.full_name} for {class_obj.name}."
                    else:
                        message = f"Successfully reactivated assignment of {subject.subject_name} to {teacher.full_name} for {class_obj.name}."

                    return JsonResponse({"success": True, "message": message})
                else:
                    # Create new assignment with school
                    assignment = TeacherSubjectAssignment.objects.create(
                        teacher=teacher,
                        subject=subject,
                        class_assigned=class_obj,
                        academic_year=current_academic_year,
                        assigned_by=request.user,
                        school=school,  # Set the school for multi-tenancy
                    )

                    # Log new assignment creation
                    logger.info(
                        f"Admin {request.user.username} assigned {subject.subject_name} "
                        f"to {teacher.full_name} for {class_obj.name}"
                    )

                    return JsonResponse(
                        {
                            "success": True,
                            "message": f"Successfully assigned {subject.subject_name} to {teacher.full_name} for {class_obj.name}.",
                        }
                    )
        except Teacher.DoesNotExist:
            return JsonResponse({"success": False, "message": "Teacher not found."})
        except Subject.DoesNotExist:
            return JsonResponse({"success": False, "message": "Subject not found."})
        except Class.DoesNotExist:
            return JsonResponse({"success": False, "message": "Class not found."})
        except Exception as e:
            logger.error(f"Error assigning subject: {str(e)}", exc_info=True)
            return JsonResponse({"success": False, "message": str(e)})

    # GET request - show form
    # Ensure teacher belongs to user's school
    teacher = get_object_or_404(Teacher, staff_id=staff_id, school=school)
    try:
        # Get current academic year for the school
        current_academic_year = AcademicYear.objects.filter(
            school=school, is_current=True
        ).first()
        if not current_academic_year:
            current_academic_year = AcademicYear.objects.filter(is_current=True).first()

        # Get current term for the school
        current_term = Term.objects.filter(school=school, is_current=True).first()
        if not current_term:
            current_term = Term.objects.filter(is_current=True).first()

        # Filter subjects and classes by school
        available_subjects = Subject.objects.filter(school=school).order_by(
            "subject_name"
        )
        available_classes = Class.objects.filter(
            academic_year=current_academic_year, school=school
        )
    except AcademicYear.DoesNotExist:
        messages.error(request, "No active academic year found")
        return redirect("teacher_detail", staff_id=staff_id)
    except Term.DoesNotExist:
        messages.error(request, "No active term found")
        return redirect("teacher_detail", staff_id=staff_id)

    return render(
        request,
        "teacher/teacher_detail.html",
        {
            "teacher": teacher,
            "available_subjects": available_subjects,
            "available_classes": available_classes,
            "current_academic_year": current_academic_year,
            "current_term": current_term,
            "school": school,  # Add school to context
        },
    )


@login_required
@user_passes_test(is_admin)
def assign_multiple_subjects(request, staff_id):
    """
    Assign multiple subjects to a teacher for a specific class at once.

    Handles bulk assignment of subjects to a teacher, improving efficiency
    when assigning multiple subjects from the same class.

    Args:
        request (HttpRequest): The request object
        staff_id (str): The staff ID of the teacher to assign

    Returns:
        HttpResponse: JSON response with results of the assignments
    """
    # Get user's school for multi-tenancy
    school = request.user.school

    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid request method"})

    try:
        # Ensure teacher belongs to user's school
        teacher = get_object_or_404(Teacher, staff_id=staff_id, school=school)
        class_id = request.POST.get("class_id")
        subject_ids = request.POST.getlist("subject_ids[]")

        # Validate required fields
        if not class_id:
            return JsonResponse({"success": False, "message": "Class ID is required"})

        if not subject_ids:
            return JsonResponse(
                {"success": False, "message": "At least one subject must be selected"}
            )

        # Ensure class belongs to user's school
        class_obj = get_object_or_404(Class, id=class_id, school=school)

        try:
            # Get current academic year for the school
            current_academic_year = AcademicYear.objects.filter(
                school=school, is_current=True
            ).first()
            if not current_academic_year:
                current_academic_year = AcademicYear.objects.filter(
                    is_current=True
                ).first()

            if not current_academic_year:
                return JsonResponse(
                    {"success": False, "message": "No active academic year found"}
                )
        except AcademicYear.DoesNotExist:
            return JsonResponse(
                {"success": False, "message": "No active academic year found"}
            )

        # Process all subject assignments within a single transaction
        with transaction.atomic():
            results = []
            success_count = 0
            error_count = 0

            for subject_id in subject_ids:
                try:
                    # Ensure subject belongs to user's school
                    subject = get_object_or_404(Subject, id=subject_id, school=school)

                    # Verify subject is assigned to the class
                    subject_assigned_to_class = ClassSubject.objects.filter(
                        subject=subject,
                        class_name=class_obj,
                        academic_year=current_academic_year,

                        is_active=True

                    ).exists()

                    if not subject_assigned_to_class:
                        results.append(
                            {
                                "subject": subject.subject_name,
                                "success": False,
                                "message": f"Subject '{subject.subject_name}' is not assigned to class '{class_obj.name}'",
                            }
                        )
                        error_count += 1
                        continue

                    # Check for existing active assignment, filtered by school
                    existing_assignment = TeacherSubjectAssignment.objects.filter(
                        subject=subject,
                        class_assigned=class_obj,
                        academic_year=current_academic_year,
                        is_active=True,
                        school=school,
                    ).first()

                    # Check for existing deactivated assignment, filtered by school
                    deactivated_assignment = TeacherSubjectAssignment.objects.filter(
                        subject=subject,
                        class_assigned=class_obj,
                        academic_year=current_academic_year,
                        is_active=False,
                        school=school,
                    ).first()

                    if existing_assignment:
                        # If existing assignment is to the same teacher, skip
                        if existing_assignment.teacher == teacher:
                            results.append(
                                {
                                    "subject": subject.subject_name,
                                    "success": True,
                                    "message": f"Already assigned to teach {subject.subject_name}",
                                }
                            )
                            success_count += 1
                            continue

                        # Update the existing assignment to the new teacher
                        previous_teacher = existing_assignment.teacher.full_name
                        existing_assignment.teacher = teacher
                        existing_assignment.assigned_by = request.user
                        existing_assignment.save()

                        logger.info(
                            f"Admin {request.user.username} reassigned {subject.subject_name} for {class_obj.name} "
                            f"from {previous_teacher} to {teacher.full_name}"
                        )

                        results.append(
                            {
                                "subject": subject.subject_name,
                                "success": True,
                                "message": f"Reassigned from {previous_teacher}",
                            }
                        )
                        success_count += 1

                    elif deactivated_assignment:
                        # Reactivate the deactivated assignment and update teacher
                        previous_teacher = (
                            deactivated_assignment.teacher.full_name
                            if deactivated_assignment.teacher != teacher
                            else None
                        )
                        deactivated_assignment.teacher = teacher
                        deactivated_assignment.is_active = True
                        deactivated_assignment.assigned_by = request.user
                        deactivated_assignment.save()

                        logger.info(
                            f"Admin {request.user.username} reactivated subject assignment of {subject.subject_name} "
                            f"to {teacher.full_name} for {class_obj.name}"
                        )

                        results.append(
                            {
                                "subject": subject.subject_name,
                                "success": True,
                                "message": f"Reactivated assignment",
                            }
                        )
                        success_count += 1

                    else:
                        # Create new assignment with school
                        assignment = TeacherSubjectAssignment.objects.create(
                            teacher=teacher,
                            subject=subject,
                            class_assigned=class_obj,
                            academic_year=current_academic_year,
                            assigned_by=request.user,
                            school=school,  # Set the school for multi-tenancy
                        )

                        logger.info(
                            f"Admin {request.user.username} assigned {subject.subject_name} "
                            f"to {teacher.full_name} for {class_obj.name}"
                        )

                        results.append(
                            {
                                "subject": subject.subject_name,
                                "success": True,
                                "message": f"New assignment created",
                            }
                        )
                        success_count += 1

                except Subject.DoesNotExist:
                    results.append(
                        {
                            "subject": f"ID: {subject_id}",
                            "success": False,
                            "message": "Subject not found",
                        }
                    )
                    error_count += 1
                except Exception as e:
                    logger.error(
                        f"Error assigning subject {subject_id}: {str(e)}", exc_info=True
                    )
                    results.append(
                        {
                            "subject": f"ID: {subject_id}",
                            "success": False,
                            "message": str(e),
                        }
                    )
                    error_count += 1

            # Prepare summary message
            if success_count > 0 and error_count == 0:
                summary = f"Successfully assigned {success_count} subjects to {teacher.full_name} for {class_obj.name}."
                status = True
            elif success_count > 0 and error_count > 0:
                summary = f"Partially successful: {success_count} subjects assigned, {error_count} failed."
                status = True
            else:
                summary = f"Failed to assign any subjects. Please check the errors and try again."
                status = False

            return JsonResponse(
                {
                    "success": status,
                    "message": summary,
                    "results": results,
                    "success_count": success_count,
                    "error_count": error_count,
                }
            )

    except Teacher.DoesNotExist:
        return JsonResponse({"success": False, "message": "Teacher not found"})
    except Class.DoesNotExist:
        return JsonResponse({"success": False, "message": "Class not found"})
    except Exception as e:
        logger.error(f"Error in bulk subject assignment: {str(e)}", exc_info=True)
        return JsonResponse({"success": False, "message": str(e)})


@login_required
@user_passes_test(is_admin)
def remove_subject_assignment(request, assignment_id):
    """
    Remove a teacher's subject assignment by deactivating it rather than deleting.

    Handles both standard form submissions and AJAX requests.

    Args:
        request (HttpRequest): The request object
        assignment_id (str): The unique ID of the assignment to remove

    Returns:
        HttpResponse: Redirect to teacher detail or JSON response for AJAX requests
    """
    # Get user's school for multi-tenancy
    school = request.user.school

    # Ensure assignment belongs to user's school
    assignment = get_object_or_404(
        TeacherSubjectAssignment, assignment_id=assignment_id, school=school
    )
    teacher = assignment.teacher

    if request.method == "POST":
        try:
            with transaction.atomic():
                # Store information for response message
                teacher_name = assignment.teacher.full_name
                subject_name = assignment.subject.subject_name
                class_name = assignment.class_assigned.name

                # Deactivate the assignment instead of deleting it
                assignment.is_active = False
                assignment.save()

                # Log this action
                logger.info(
                    f"Admin {request.user.username} removed subject assignment: "
                    f"{subject_name} from {teacher_name} for {class_name}"
                )

                success_message = f"Successfully removed {subject_name} assignment from {teacher_name} for {class_name}."

                if not request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    messages.success(request, success_message)
                    return redirect("teacher_detail", staff_id=teacher.staff_id)
                else:
                    return JsonResponse({"success": True, "message": success_message})

        except Exception as e:
            logger.error(f"Error removing subject assignment: {str(e)}", exc_info=True)
            error_message = f"Error removing assignment: {str(e)}"

            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"success": False, "message": error_message})
            else:
                messages.error(request, error_message)
                return redirect("teacher_detail", staff_id=teacher.staff_id)

    # GET request - confirmation page
    context = {
        "assignment": assignment,
        "teacher": teacher,
        "school": school,  # Add school to context
    }

    return render(request, "teacher/remove_subject_assignment_confirm.html", context)


@login_required
def get_teacher_assignments(request):

    """API endpoint to get all subject assignments for the logged-in teacher or admin."""
    if request.user.role not in ["teacher", "admin"]:

        return JsonResponse(
            {"success": False, "error": "Permission denied"}, status=403
        )



    # Get user's school for multi-tenancy - use the same logic as scores view
    from shs_system.utils import get_user_school

    user_school = get_user_school(request.user)

    # Get current academic year for the school
    if user_school:
        current_academic_year = AcademicYear.objects.filter(
            school=user_school, is_current=True
        ).first()
    else:
        current_academic_year = AcademicYear.objects.filter(is_current=True).first()

    if not current_academic_year:
        return JsonResponse(
            {"success": False, "error": "No active academic year found"}, status=400
        )


    # Determine which teacher to filter by
    teacher_filter = None
    if request.user.role == "teacher":
        # For teachers, use their own teacher profile
        teacher_filter = request.user.teacher_profile
        if not teacher_filter:
            return JsonResponse(
                {"success": False, "error": "Teacher profile not found"}, status=400
            )
    elif request.user.role == "admin":
        # For admins, check if a teacher_id filter was provided
        teacher_id = request.GET.get("teacher_id")
        if teacher_id:
            try:
                teacher_filter = Teacher.objects.get(id=teacher_id, school=user_school)
            except Teacher.DoesNotExist:
                return JsonResponse(
                    {"success": False, "error": "Invalid teacher ID"}, status=400
                )
        # If no teacher_id provided, admin sees all assignments (will be filtered below)

    # Get all active assignments in the current academic year
    if teacher_filter:
        assignments_query = TeacherSubjectAssignment.objects.filter(
            teacher=teacher_filter,
            academic_year=current_academic_year,
            is_active=True,
        )
    elif request.user.role == "admin":
        # Admin without teacher filter sees all assignments in their school
        assignments_query = TeacherSubjectAssignment.objects.filter(
            academic_year=current_academic_year,
            is_active=True,
        )
    else:
        return JsonResponse(
            {"success": False, "error": "Invalid user role or configuration"}, status=400
        )


    # Apply school filter if user has a school
    if user_school:
        assignments_query = assignments_query.filter(school=user_school)


    # Filter out assignments where ClassSubject is not active
    # Get active class-subject combinations
    active_class_subjects = ClassSubject.objects.filter(
        academic_year=current_academic_year, is_active=True
    ).values_list('class_name_id', 'subject_id')
    
    # Filter assignments to only include those with active ClassSubject
    filtered_assignments = []
    for assignment in assignments_query.select_related("class_assigned", "subject"):
        if (assignment.class_assigned.id, assignment.subject.id) in active_class_subjects:
            filtered_assignments.append(assignment)
    
    assignments = filtered_assignments


    # Format the assignments for JSON response
    assignment_data = []
    for assignment in assignments:
        assignment_data.append(
            {
                "id": assignment.id,
                "class_name": assignment.class_assigned.name,
                "subject": assignment.subject.subject_name,
                "class_id": assignment.class_assigned.id,
                "subject_id": assignment.subject.id,
            }
        )

    if not assignment_data:
        # Enhanced logging for debugging
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(
            f"No assignments found for teacher ID: {teacher.id} ({teacher.first_name} {teacher.last_name}) "
            f"in school: {user_school.name if user_school else 'No school assigned'}, "
            f"academic year: {current_academic_year.name if current_academic_year else 'None'}"
        )

        # Return more detailed error message
        return JsonResponse(
            {
                "success": False,
                "error": f"No class assignments found for the current academic year ({current_academic_year.name if current_academic_year else 'None'}). Please contact your administrator to assign classes to your account.",
                "assignments": [],
            }
        )

    return JsonResponse({"success": True, "assignments": assignment_data})


@login_required
def teacher_profile(request):
    """
    View for displaying the teacher's profile page with options to update
    profile information and change password
    """
    if request.user.role != "teacher":
        return render(request, "errors/403.html", status=403)

    # Get teacher profile from user
    teacher = request.user.teacher_profile

    # Get user's school for multi-tenancy
    school = request.user.school


    # Get current academic year and term for this school
    current_academic_year = SchoolInformation.get_current_academic_year(school=school)
    current_term = SchoolInformation.get_current_term(school=school)

    # Get current teaching assignments, filtered by school and current academic year
    teaching_assignments_query = TeacherSubjectAssignment.objects.filter(
        teacher=teacher, is_active=True, school=school, academic_year=current_academic_year
    ).select_related("class_assigned", "subject", "academic_year")

    # Filter out assignments where ClassSubject is not active
    # Get active class-subject combinations
    active_class_subjects = ClassSubject.objects.filter(
        academic_year=current_academic_year, is_active=True
    ).values_list('class_name_id', 'subject_id')
    
    # Filter assignments to only include those with active ClassSubject
    filtered_assignments = []
    for assignment in teaching_assignments_query:
        if (assignment.class_assigned.id, assignment.subject.id) in active_class_subjects:
            filtered_assignments.append(assignment)
    
    teaching_assignments = filtered_assignments

    context = {
        "teacher": teacher,
        "teaching_assignments": teaching_assignments,
        "school": school,
        "current_academic_year": current_academic_year,
        "current_term": current_term,

    }

    return render(request, "teacher/teacher_profile.html", context)


@login_required
def teacher_update_profile(request):
    """
    View for teachers to update their own profile information.

    Handles both form submission and AJAX requests for updating profile details.
    Now includes support for profile picture uploads.
    """
    if request.user.role != "teacher" or not request.user.teacher_profile:
        return render(request, "errors/403.html", status=403)

    teacher = request.user.teacher_profile

    if request.method == "POST":
        try:
            # Extract form data
            full_name = request.POST.get("full_name", "").strip()
            contact_number = request.POST.get("contact_number", "").strip()
            email = request.POST.get("email", "").strip()

            # Validate required fields
            if not full_name:
                return JsonResponse(
                    {"status": "error", "message": "Full name is required"}, status=400
                )

            # Update teacher information
            teacher.full_name = full_name
            if contact_number:
                teacher.contact_number = contact_number

            # Handle profile picture upload
            if request.FILES and "profile_picture" in request.FILES:
                teacher.profile_picture = request.FILES["profile_picture"]

            # Save teacher model
            teacher.save()

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
            return redirect("teacher_profile")

        except Exception as e:
            # Log the error
            logger.error(f"Error updating teacher profile: {str(e)}", exc_info=True)

            # For AJAX requests
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {"status": "error", "message": f"Error updating profile: {str(e)}"},
                    status=500,
                )

            # For regular form submissions
            messages.error(request, f"Error updating profile: {str(e)}")
            return redirect("teacher_profile")

    # For GET requests
    return redirect("teacher_profile")


@login_required
def teacher_change_password(request):
    """
    AJAX view for changing teacher password
    """
    if request.user.role != "teacher" or request.method != "POST":
        return JsonResponse(
            {"status": "error", "message": "Invalid request"}, status=403
        )

    try:
        user = request.user

        # Get form data
        current_password = request.POST.get("current_password")
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        # Validate data
        if not current_password or not new_password or not confirm_password:
            return JsonResponse(
                {"status": "error", "message": "All password fields are required"},
                status=400,
            )

        if new_password != confirm_password:
            return JsonResponse(
                {
                    "status": "error",
                    "message": "New password and confirmation do not match",
                },
                status=400,
            )

        # Check current password
        if not user.check_password(current_password):
            return JsonResponse(
                {"status": "error", "message": "Current password is incorrect"},
                status=400,
            )

        # Password policy validation
        if len(new_password) < 8:
            return JsonResponse(
                {
                    "status": "error",
                    "message": "Password must be at least 8 characters long",
                },
                status=400,
            )

        # Check if password has at least one letter and one digit
        if not any(char.isalpha() for char in new_password) or not any(
            char.isdigit() for char in new_password
        ):
            return JsonResponse(
                {
                    "status": "error",
                    "message": "Password must include letters and numbers",
                },
                status=400,
            )

        # Change password
        user.set_password(new_password)
        user.save()

        # Update user's session to prevent logout
        update_session_auth_hash(request, user)

        return JsonResponse(
            {"status": "success", "message": "Password changed successfully"}
        )
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


import random
import string


@login_required
@user_passes_test(is_admin)
def remove_class_teacher(request, class_id):
    """
    Remove a class teacher assignment by deactivating it.

    Handles both standard form submissions and AJAX requests.

    Args:
        request (HttpRequest): The request object
        class_id (int): The ID of the class to remove teacher from

    Returns:
        HttpResponse: JSON response with result of operation
    """
    # Get user's school for multi-tenancy
    school = request.user.school

    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Invalid request method."})

    try:
        # Find the class, ensure it belongs to user's school
        class_obj = get_object_or_404(Class, id=class_id, school=school)

        try:
            # Get current academic year for the school
            current_academic_year = AcademicYear.objects.filter(
                school=school, is_current=True
            ).first()
            if not current_academic_year:
                current_academic_year = AcademicYear.objects.filter(
                    is_current=True
                ).first()

            if not current_academic_year:
                return JsonResponse(
                    {"success": False, "message": "No active academic year found."}
                )
        except AcademicYear.DoesNotExist:
            return JsonResponse(
                {"success": False, "message": "No active academic year found."}
            )

        # Find the class teacher assignment, filtered by school
        class_teacher = ClassTeacher.objects.filter(
            class_assigned=class_obj,
            academic_year=current_academic_year,
            is_active=True,
            school=school,
        ).first()

        if class_teacher:
            # Store information for response message
            teacher_name = class_teacher.teacher.full_name
            class_name = class_teacher.class_assigned.name

            # Use transaction for data consistency
            with transaction.atomic():
                # Deactivate instead of deleting
                class_teacher.is_active = False
                class_teacher.save()

                # Log this action
                logger.info(
                    f"Admin {request.user.username} removed {teacher_name} "
                    f"as class teacher for {class_name}"
                )

            return JsonResponse(
                {
                    "success": True,
                    "message": f"Successfully removed {teacher_name} as class teacher for {class_name}.",
                }
            )
        else:
            return JsonResponse(
                {
                    "success": False,
                    "message": "No active class teacher assignment found for this class.",
                }
            )
    except Class.DoesNotExist:
        return JsonResponse({"success": False, "message": "Class not found."})
    except Exception as e:
        logger.error(f"Error removing class teacher: {str(e)}", exc_info=True)
        return JsonResponse({"success": False, "message": str(e)})


@login_required
@user_passes_test(is_admin)
def get_class_subjects(request):
    """
    AJAX endpoint to get subjects assigned to a specific class.
    Returns a list of subjects in JSON format.
    """
    # Get user's school for multi-tenancy
    school = request.user.school

    class_id = request.GET.get("class_id")
    if not class_id:
        return JsonResponse({"success": False, "message": "Class ID is required"})

    try:
        # Ensure class belongs to user's school
        class_obj = get_object_or_404(Class, id=class_id, school=school)

        # Get current academic year for the school
        current_academic_year = AcademicYear.objects.filter(
            school=school, is_current=True
        ).first()
        if not current_academic_year:
            current_academic_year = AcademicYear.objects.filter(is_current=True).first()

        if not current_academic_year:
            return JsonResponse(
                {"success": False, "message": "No active academic year found"}
            )

        # Get subjects assigned to this class from ClassSubject model
        class_subjects = (
            ClassSubject.objects.filter(

                class_name=class_obj, academic_year=current_academic_year, is_active=True

            )
            .values_list("subject_id", flat=True)
            .distinct()
        )

        # Get subject details, filtered by school
        subjects = Subject.objects.filter(id__in=class_subjects, school=school).values(
            "id", "subject_name"
        )

        return JsonResponse({"success": True, "subjects": list(subjects)})
    except Class.DoesNotExist:
        return JsonResponse({"success": False, "message": "Class not found"})
    except AcademicYear.DoesNotExist:
        return JsonResponse(
            {"success": False, "message": "No active academic year found"}
        )
    except Exception as e:
        logger.error(f"Error fetching class subjects: {str(e)}", exc_info=True)
        return JsonResponse({"success": False, "message": str(e)})


@login_required
@user_passes_test(is_admin)
def bulk_subject_assignment(request):
    """
    View for displaying the bulk subject assignment page.

    Provides an interface for efficiently assigning teachers to subjects across different classes.

    Args:
        request (HttpRequest): The request object

    Returns:
        HttpResponse: The rendered bulk subject assignment page
    """
    # Get user's school for multi-tenancy
    school = request.user.school

    print(f"DEBUG: Accessed bulk_subject_assignment view with URL: {request.path}")

    # Get all teachers with department information, filtered by school
    teachers = (
        Teacher.objects.select_related("department")
        .filter(school=school)
        .order_by("full_name")
    )

    # Get all distinct departments for the filter dropdown, filtered by school
    departments = (
        Department.objects.filter(school=school)
        .values_list("name", flat=True)
        .distinct()
        .order_by("name")
    )

    # Get current academic year for the school
    try:
        current_academic_year = AcademicYear.objects.filter(
            school=school, is_current=True
        ).first()
        if not current_academic_year:
            current_academic_year = AcademicYear.objects.filter(is_current=True).first()

        # Get available classes for the current academic year, filtered by school
        available_classes = Class.objects.filter(
            academic_year=current_academic_year, school=school
        )
    except AcademicYear.DoesNotExist:
        current_academic_year = None
        available_classes = []
        messages.error(
            request,
            f"No active academic year found for school {school.name}. Please set an active academic year first.",
        )

    # Get available subjects, filtered by school
    available_subjects = Subject.objects.filter(school=school).order_by("subject_name")

    # Calculate total assignments for each teacher
    for teacher in teachers:
        teacher.total_assigned_classes = teacher.total_assigned_classes()

    context = {
        "teachers": teachers,
        "departments": departments,
        "available_classes": available_classes,
        "available_subjects": available_subjects,
        "current_academic_year": current_academic_year,
        "page_title": "Bulk Subject Assignment",
        "school": school,  # Add school to context
    }

    return render(request, "teacher/bulk_subject_assignment.html", context)
