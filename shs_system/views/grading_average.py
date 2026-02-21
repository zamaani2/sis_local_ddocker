from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.template.loader import render_to_string
from django.db.models import Count, Q
from shs_system.models import Class, Teacher, GradingSystem, PerformanceRequirement
from shs_system.forms import ClassForm


def get_user_school(user):
    """
    Get the school associated with the current user.
    For superadmins, this will return None (they can access all schools).
    For other users, it will return their associated school.
    """
    if user.is_superadmin:
        return None  # Superadmins can access all schools
    return user.school


@login_required
@user_passes_test(lambda u: u.role == "admin")
def grading_system_list(request):
    """Display list of grading criteria."""
    # Get the user's school
    school = get_user_school(request.user)

    # Get grades, filtering by school if user is not a superadmin
    grades_query = GradingSystem.objects.all()
    if school:
        grades_query = grades_query.filter(Q(school=school) | Q(school__isnull=True))
    grades = grades_query.order_by("-min_score")

    return render(
        request,
        "grading/grading_system_list.html",
        {"grades": grades, "active_tab": "grades", "school": school},
    )


@login_required
@user_passes_test(lambda u: u.role == "admin")
def grading_system_create(request):
    """Create a new grading criterion."""
    # Get the user's school
    school = get_user_school(request.user)

    data = {}
    if request.method == "POST":
        # Extract form data
        grade_letter = request.POST.get("grade_letter")
        min_score = request.POST.get("min_score")
        max_score = request.POST.get("max_score")
        remarks = request.POST.get("remarks")
        description = request.POST.get("description")
        is_active = request.POST.get("is_active") == "on"

        # Validate data
        errors = []
        if not grade_letter:
            errors.append("Grade letter is required")
        if not min_score:
            errors.append("Minimum score is required")
        if not max_score:
            errors.append("Maximum score is required")
        if not remarks:
            errors.append("Remarks are required")

        # Check for overlap in score ranges
        if not errors:
            try:
                min_score = float(min_score)
                max_score = float(max_score)

                if min_score >= max_score:
                    errors.append("Minimum score must be less than maximum score")

                # Check for overlap with existing grades, filtering by school
                overlapping_query = GradingSystem.objects.filter(
                    (Q(min_score__lte=min_score) & Q(max_score__gte=min_score))
                    | (Q(min_score__lte=max_score) & Q(max_score__gte=max_score))
                    | (Q(min_score__gte=min_score) & Q(max_score__lte=max_score))
                )

                # Filter by school if user is not a superadmin
                if school:
                    overlapping_query = overlapping_query.filter(
                        Q(school=school) | Q(school__isnull=True)
                    )

                overlapping = overlapping_query.exists()

                if overlapping:
                    errors.append("This score range overlaps with an existing grade")
            except ValueError:
                errors.append("Scores must be valid numbers")

        if errors:
            data = {"success": False, "errors": errors}
        else:
            # Create the grade
            grade = GradingSystem.objects.create(
                grade_letter=grade_letter,
                min_score=min_score,
                max_score=max_score,
                remarks=remarks,
                description=description,
                is_active=is_active,
                school=school,  # Associate with the user's school
            )

            # If AJAX request, return JSON response
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                data = {
                    "success": True,
                    "message": f"Grade {grade.grade_letter} created successfully",
                    "grade": {
                        "id": grade.id,
                        "grade_letter": grade.grade_letter,
                        "min_score": float(grade.min_score),
                        "max_score": float(grade.max_score),
                        "remarks": grade.remarks,
                        "description": grade.description or "-",
                        "is_active": grade.is_active,
                    },
                }
            else:
                messages.success(
                    request, f"Grade {grade.grade_letter} created successfully"
                )
                return redirect("grading_system_list")

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        html_form = render_to_string(
            "grading/includes/partial_grade_form.html",
            {"grade": {}, "school": school},
            request=request,
        )
        data["html_form"] = html_form
        return JsonResponse(data)

    return render(request, "grading/grading_system_form.html", {"school": school})


@login_required
@user_passes_test(lambda u: u.role == "admin")
def grading_system_update(request, pk):
    """Update an existing grading criterion."""
    # Get the user's school
    school = get_user_school(request.user)

    data = {}
    try:
        # Get the grade, filtering by school if user is not a superadmin
        grade_query = GradingSystem.objects
        if school:
            grade_query = grade_query.filter(Q(school=school) | Q(school__isnull=True))
        grade = grade_query.get(pk=pk)
    except GradingSystem.DoesNotExist:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": False, "errors": ["Grade not found"]})
        messages.error(request, "Grade not found")
        return redirect("grading_system_list")

    if request.method == "POST":
        # Extract form data
        grade_letter = request.POST.get("grade_letter")
        min_score = request.POST.get("min_score")
        max_score = request.POST.get("max_score")
        remarks = request.POST.get("remarks")
        description = request.POST.get("description")
        is_active = request.POST.get("is_active") == "on"

        # Validate data
        errors = []
        if not grade_letter:
            errors.append("Grade letter is required")
        if not min_score:
            errors.append("Minimum score is required")
        if not max_score:
            errors.append("Maximum score is required")
        if not remarks:
            errors.append("Remarks are required")

        # Check for overlap in score ranges
        if not errors:
            try:
                min_score = float(min_score)
                max_score = float(max_score)

                if min_score >= max_score:
                    errors.append("Minimum score must be less than maximum score")

                # Check for overlap with existing grades (excluding this one), filtering by school
                overlapping_query = GradingSystem.objects.filter(
                    (Q(min_score__lte=min_score) & Q(max_score__gte=min_score))
                    | (Q(min_score__lte=max_score) & Q(max_score__gte=max_score))
                    | (Q(min_score__gte=min_score) & Q(max_score__lte=max_score))
                ).exclude(pk=pk)

                # Filter by school if user is not a superadmin
                if school:
                    overlapping_query = overlapping_query.filter(
                        Q(school=school) | Q(school__isnull=True)
                    )

                overlapping = overlapping_query.exists()

                if overlapping:
                    errors.append("This score range overlaps with an existing grade")
            except ValueError:
                errors.append("Scores must be valid numbers")

        if errors:
            data = {"success": False, "errors": errors}
        else:
            # Update the grade
            grade.grade_letter = grade_letter
            grade.min_score = min_score
            grade.max_score = max_score
            grade.remarks = remarks
            grade.description = description
            grade.is_active = is_active

            # Only update school if the grade doesn't have one already
            if school and not grade.school:
                grade.school = school

            grade.save()

            # If AJAX request, return JSON response
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                data = {
                    "success": True,
                    "message": f"Grade {grade.grade_letter} updated successfully",
                    "grade": {
                        "id": grade.id,
                        "grade_letter": grade.grade_letter,
                        "min_score": float(grade.min_score),
                        "max_score": float(grade.max_score),
                        "remarks": grade.remarks,
                        "description": grade.description or "-",
                        "is_active": grade.is_active,
                    },
                }
            else:
                messages.success(
                    request, f"Grade {grade.grade_letter} updated successfully"
                )
                return redirect("grading_system_list")

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        html_form = render_to_string(
            "grading/includes/partial_grade_form.html",
            {"grade": grade, "school": school},
            request=request,
        )
        data["html_form"] = html_form
        return JsonResponse(data)

    return render(
        request, "grading/grading_system_form.html", {"grade": grade, "school": school}
    )


@login_required
@user_passes_test(lambda u: u.role == "admin")
def grading_system_delete(request, pk):
    """Delete a grading criterion."""
    # Get the user's school
    school = get_user_school(request.user)

    try:
        # Get the grade, filtering by school if user is not a superadmin
        grade_query = GradingSystem.objects
        if school:
            grade_query = grade_query.filter(Q(school=school) | Q(school__isnull=True))
        grade = grade_query.get(pk=pk)
    except GradingSystem.DoesNotExist:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": False, "errors": ["Grade not found"]})
        messages.error(request, "Grade not found")
        return redirect("grading_system_list")

    data = {}
    if request.method == "POST":
        grade_letter = grade.grade_letter
        grade.delete()

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            data = {
                "success": True,
                "message": f"Grade {grade_letter} deleted successfully",
            }
            return JsonResponse(data)

        messages.success(request, f"Grade {grade_letter} deleted successfully")
        return redirect("grading_system_list")

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        html_form = render_to_string(
            "grading/includes/partial_grade_confirm_delete.html",
            {"grade": grade, "school": school},
            request=request,
        )
        data = {"html_form": html_form}
        return JsonResponse(data)

    return render(
        request,
        "grading/grading_system_confirm_delete.html",
        {"grade": grade, "school": school},
    )


@login_required
@user_passes_test(lambda u: u.role == "admin")
def initialize_default_grades(request):
    """Initialize default grades if none exist."""
    # Get the user's school
    school = get_user_school(request.user)

    # Check if grades already exist for this school
    grades_query = GradingSystem.objects
    if school:
        grades_query = grades_query.filter(Q(school=school) | Q(school__isnull=True))

    if grades_query.exists():
        messages.info(request, "Grades already exist in the system.")
        return redirect("grading_system_list")

    # Create default grades
    default_grades = [
        {
            "grade_letter": "A1",
            "min_score": 75.0,
            "max_score": 100.0,
            "remarks": "EXCELLENT",
            "description": "Excellent performance",
        },
        {
            "grade_letter": "B2",
            "min_score": 70.0,
            "max_score": 74.99,
            "remarks": "VERY GOOD",
            "description": "Very good performance",
        },
        {
            "grade_letter": "B3",
            "min_score": 65.0,
            "max_score": 69.99,
            "remarks": "GOOD",
            "description": "Good performance",
        },
        {
            "grade_letter": "C4",
            "min_score": 60.0,
            "max_score": 64.99,
            "remarks": "CREDIT",
            "description": "Credit performance",
        },
        {
            "grade_letter": "C5",
            "min_score": 55.0,
            "max_score": 59.99,
            "remarks": "PASS",
            "description": "Pass performance",
        },
        {
            "grade_letter": "C6",
            "min_score": 50.0,
            "max_score": 54.99,
            "remarks": "WEAK PASS",
            "description": "Weak pass performance",
        },
        {
            "grade_letter": "D7",
            "min_score": 45.0,
            "max_score": 49.99,
            "remarks": "Needs Improvement",
            "description": "Needs improvement",
        },
        {
            "grade_letter": "E8",
            "min_score": 40.0,
            "max_score": 44.99,
            "remarks": "Poor",
            "description": "Poor performance",
        },
        {
            "grade_letter": "F9",
            "min_score": 0.0,
            "max_score": 39.99,
            "remarks": "FAIL",
            "description": "Failed performance",
        },
    ]

    for grade_data in default_grades:
        # Add school to each grade if user is not a superadmin
        if school:
            grade_data["school"] = school
        GradingSystem.objects.create(**grade_data)

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse(
            {
                "success": True,
                "message": f"Successfully initialized {len(default_grades)} default grades.",
            }
        )

    messages.success(
        request, f"Successfully initialized {len(default_grades)} default grades."
    )
    return redirect("grading_system_list")


@login_required
def get_grade_for_score(request):
    """API to get grade letter and remarks for a score."""
    # Get the user's school
    school = get_user_school(request.user)

    try:
        score = float(request.GET.get("score", 0))
        grade_info = GradingSystem.get_grade_for_score(score, school)

        if grade_info:
            return JsonResponse(
                {
                    "success": True,
                    "grade_letter": grade_info.grade_letter,
                    "remarks": grade_info.remarks,
                    "description": grade_info.description,
                }
            )
        else:
            return JsonResponse(
                {"success": False, "error": "No grade found for this score"}
            )
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


# Performance Requirements Views
@login_required
@user_passes_test(lambda u: u.role == "admin")
def performance_requirement_list(request):
    """Display list of performance requirements."""
    # Get the user's school
    school = get_user_school(request.user)

    # Get requirements, filtering by school if user is not a superadmin
    requirements_query = PerformanceRequirement.objects.all()
    if school:
        requirements_query = requirements_query.filter(
            Q(school=school) | Q(school__isnull=True)
        )
    requirements = requirements_query.order_by("-is_active", "-updated_at")

    return render(
        request,
        "grading/performance_requirement_list.html",
        {
            "requirements": requirements,
            "active_tab": "performance_requirements",
            "school": school,
        },
    )


@login_required
@user_passes_test(lambda u: u.role == "admin")
def performance_requirement_create(request):
    """Create a new performance requirement."""
    # Get the user's school
    school = get_user_school(request.user)

    data = {}
    if request.method == "POST":
        # Extract form data
        name = request.POST.get("name")
        description = request.POST.get("description")
        min_average_score = request.POST.get("min_average_score_for_promotion")
        min_passing_grade_id = request.POST.get("min_passing_grade")
        max_failed_subjects = request.POST.get("max_failed_subjects")
        calculation_method = request.POST.get("calculation_method")
        first_term_weight = request.POST.get("first_term_weight")
        second_term_weight = request.POST.get("second_term_weight")
        third_term_weight = request.POST.get("third_term_weight")
        is_active = request.POST.get("is_active") == "on"

        # Validate data
        errors = []
        if not name:
            errors.append("Name is required")
        if not min_average_score:
            errors.append("Minimum average score is required")
        if not max_failed_subjects:
            errors.append("Maximum failed subjects is required")

        # Create the performance requirement if no errors
        if not errors:
            try:
                # Get minimum passing grade if provided, filtering by school
                min_passing_grade = None
                if min_passing_grade_id:
                    grade_query = GradingSystem.objects
                    if school:
                        grade_query = grade_query.filter(
                            Q(school=school) | Q(school__isnull=True)
                        )
                    min_passing_grade = grade_query.get(id=min_passing_grade_id)

                # Create the performance requirement
                requirement = PerformanceRequirement(
                    name=name,
                    description=description,
                    min_average_score_for_promotion=min_average_score,
                    min_passing_grade=min_passing_grade,
                    max_failed_subjects=max_failed_subjects,
                    calculation_method=calculation_method,
                    first_term_weight=first_term_weight,
                    second_term_weight=second_term_weight,
                    third_term_weight=third_term_weight,
                    is_active=is_active,
                    school=school,  # Associate with the user's school
                )

                # If this is active, deactivate all others for this school
                if is_active:
                    if school:
                        PerformanceRequirement.objects.filter(school=school).update(
                            is_active=False
                        )
                    else:
                        PerformanceRequirement.objects.update(is_active=False)

                requirement.save()

                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    data = {
                        "success": True,
                        "message": f"Performance requirement '{name}' created successfully.",
                        "requirement": {
                            "id": requirement.id,
                            "name": requirement.name,
                            "min_average_score_for_promotion": float(
                                requirement.min_average_score_for_promotion
                            ),
                            "max_failed_subjects": requirement.max_failed_subjects,
                            "min_passing_grade": (
                                requirement.min_passing_grade.grade_letter
                                if requirement.min_passing_grade
                                else "-"
                            ),
                            "calculation_method": requirement.get_calculation_method_display(),
                            "is_active": requirement.is_active,
                        },
                    }
                    return JsonResponse(data)

                messages.success(
                    request, f"Performance requirement '{name}' created successfully."
                )
                return redirect("performance_requirement_list")

            except Exception as e:
                errors.append(f"Error creating performance requirement: {str(e)}")

        if errors:
            data = {"success": False, "errors": errors}
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(data)
            for error in errors:
                messages.error(request, error)

    # GET request - display form
    # Get grades, filtering by school if user is not a superadmin
    grades_query = GradingSystem.objects.filter(is_active=True)
    if school:
        grades_query = grades_query.filter(Q(school=school) | Q(school__isnull=True))
    grades = grades_query.order_by("-min_score")

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        html_form = render_to_string(
            "grading/includes/partial_performance_requirement_form.html",
            {"grades": grades, "school": school},
            request=request,
        )
        data["html_form"] = html_form
        return JsonResponse(data)

    return render(
        request,
        "grading/performance_requirement_form.html",
        {"grades": grades, "active_tab": "performance_requirements", "school": school},
    )


@login_required
@user_passes_test(lambda u: u.role == "admin")
def performance_requirement_update(request, pk):
    """Update an existing performance requirement."""
    # Get the user's school
    school = get_user_school(request.user)

    data = {}
    try:
        # Get requirement, filtering by school if user is not a superadmin
        requirement_query = PerformanceRequirement.objects
        if school:
            requirement_query = requirement_query.filter(
                Q(school=school) | Q(school__isnull=True)
            )
        requirement = requirement_query.get(pk=pk)
    except PerformanceRequirement.DoesNotExist:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {"success": False, "errors": ["Performance requirement not found"]}
            )
        messages.error(request, "Performance requirement not found.")
        return redirect("performance_requirement_list")

    if request.method == "POST":
        # Extract form data
        name = request.POST.get("name")
        description = request.POST.get("description")
        min_average_score = request.POST.get("min_average_score_for_promotion")
        min_passing_grade_id = request.POST.get("min_passing_grade")
        max_failed_subjects = request.POST.get("max_failed_subjects")
        calculation_method = request.POST.get("calculation_method")
        first_term_weight = request.POST.get("first_term_weight")
        second_term_weight = request.POST.get("second_term_weight")
        third_term_weight = request.POST.get("third_term_weight")
        is_active = request.POST.get("is_active") == "on"

        # Validate data
        errors = []
        if not name:
            errors.append("Name is required")
        if not min_average_score:
            errors.append("Minimum average score is required")
        if not max_failed_subjects:
            errors.append("Maximum failed subjects is required")

        # Update the performance requirement if no errors
        if not errors:
            try:
                # Get minimum passing grade if provided, filtering by school
                min_passing_grade = None
                if min_passing_grade_id:
                    grade_query = GradingSystem.objects
                    if school:
                        grade_query = grade_query.filter(
                            Q(school=school) | Q(school__isnull=True)
                        )
                    min_passing_grade = grade_query.get(id=min_passing_grade_id)

                # Update the performance requirement
                requirement.name = name
                requirement.description = description
                requirement.min_average_score_for_promotion = min_average_score
                requirement.min_passing_grade = min_passing_grade
                requirement.max_failed_subjects = max_failed_subjects
                requirement.calculation_method = calculation_method
                requirement.first_term_weight = first_term_weight
                requirement.second_term_weight = second_term_weight
                requirement.third_term_weight = third_term_weight
                requirement.is_active = is_active

                # Only update school if the requirement doesn't have one already
                if school and not requirement.school:
                    requirement.school = school

                # If this is active, deactivate all others for this school
                if is_active:
                    if school:
                        PerformanceRequirement.objects.filter(school=school).exclude(
                            pk=pk
                        ).update(is_active=False)
                    else:
                        PerformanceRequirement.objects.exclude(pk=pk).update(
                            is_active=False
                        )

                requirement.save()

                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    data = {
                        "success": True,
                        "message": f"Performance requirement '{name}' updated successfully.",
                        "requirement": {
                            "id": requirement.id,
                            "name": requirement.name,
                            "min_average_score_for_promotion": float(
                                requirement.min_average_score_for_promotion
                            ),
                            "max_failed_subjects": requirement.max_failed_subjects,
                            "min_passing_grade": (
                                requirement.min_passing_grade.grade_letter
                                if requirement.min_passing_grade
                                else "-"
                            ),
                            "calculation_method": requirement.get_calculation_method_display(),
                            "is_active": requirement.is_active,
                        },
                    }
                    return JsonResponse(data)

                messages.success(
                    request, f"Performance requirement '{name}' updated successfully."
                )
                return redirect("performance_requirement_list")

            except Exception as e:
                errors.append(f"Error updating performance requirement: {str(e)}")

        if errors:
            data = {"success": False, "errors": errors}
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(data)
            for error in errors:
                messages.error(request, error)

    # GET request - display form with existing data
    # Get grades, filtering by school if user is not a superadmin
    grades_query = GradingSystem.objects.filter(is_active=True)
    if school:
        grades_query = grades_query.filter(Q(school=school) | Q(school__isnull=True))
    grades = grades_query.order_by("-min_score")

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        html_form = render_to_string(
            "grading/includes/partial_performance_requirement_form.html",
            {
                "requirement": requirement,
                "requirement_id": pk,
                "grades": grades,
                "school": school,
            },
            request=request,
        )
        data["html_form"] = html_form
        return JsonResponse(data)

    return render(
        request,
        "grading/performance_requirement_form.html",
        {
            "requirement": requirement,
            "requirement_id": pk,
            "grades": grades,
            "active_tab": "performance_requirements",
            "school": school,
        },
    )


@login_required
@user_passes_test(lambda u: u.role == "admin")
def performance_requirement_delete(request, pk):
    """Delete a performance requirement."""
    # Get the user's school
    school = get_user_school(request.user)

    data = {}
    try:
        # Get requirement, filtering by school if user is not a superadmin
        requirement_query = PerformanceRequirement.objects
        if school:
            requirement_query = requirement_query.filter(
                Q(school=school) | Q(school__isnull=True)
            )
        requirement = requirement_query.get(pk=pk)
    except PerformanceRequirement.DoesNotExist:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {"success": False, "errors": ["Performance requirement not found"]}
            )
        messages.error(request, "Performance requirement not found.")
        return redirect("performance_requirement_list")

    if request.method == "POST":
        is_active = requirement.is_active
        name = requirement.name

        requirement.delete()

        # If this was the active requirement, activate the next available one for this school
        if is_active:
            next_requirement_query = PerformanceRequirement.objects
            if school:
                next_requirement_query = next_requirement_query.filter(school=school)

            if next_requirement_query.exists():
                next_requirement = next_requirement_query.first()
                next_requirement.is_active = True
                next_requirement.save()

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            data = {
                "success": True,
                "message": f"Performance requirement '{name}' deleted successfully.",
            }
            return JsonResponse(data)

        messages.success(
            request, f"Performance requirement '{name}' deleted successfully."
        )
        return redirect("performance_requirement_list")

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        html_form = render_to_string(
            "grading/includes/partial_performance_requirement_confirm_delete.html",
            {"requirement": requirement, "school": school},
            request=request,
        )
        data = {"html_form": html_form}
        return JsonResponse(data)

    return render(
        request,
        "grading/performance_requirement_confirm_delete.html",
        {
            "requirement": requirement,
            "active_tab": "performance_requirements",
            "school": school,
        },
    )


@login_required
@user_passes_test(lambda u: u.role == "admin")
def initialize_default_performance_requirements(request):
    """Initialize default performance requirements if none exist."""
    # Get the user's school
    school = get_user_school(request.user)

    # Check if requirements already exist for this school
    requirements_query = PerformanceRequirement.objects
    if school:
        requirements_query = requirements_query.filter(
            Q(school=school) | Q(school__isnull=True)
        )

    if requirements_query.exists():
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {
                    "success": False,
                    "message": "Performance requirements already exist in the system.",
                }
            )
        messages.info(request, "Performance requirements already exist in the system.")
        return redirect("performance_requirement_list")

    # Get the minimum passing grade (F9), filtering by school
    min_passing_grade_query = GradingSystem.objects.filter(grade_letter="F9")
    if school:
        min_passing_grade_query = min_passing_grade_query.filter(
            Q(school=school) | Q(school__isnull=True)
        )
    min_passing_grade = min_passing_grade_query.first()

    # Create default requirement
    requirement = PerformanceRequirement.objects.create(
        name="Standard Promotion Requirements",
        description="Default promotion requirements for students",
        min_average_score_for_promotion=40.0,
        min_passing_grade=min_passing_grade,
        max_failed_subjects=3,
        calculation_method="weighted",
        first_term_weight=30.0,
        second_term_weight=30.0,
        third_term_weight=40.0,
        is_active=True,
        school=school,  # Associate with the user's school
    )

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse(
            {
                "success": True,
                "message": "Default performance requirements initialized successfully.",
            }
        )

    messages.success(
        request, "Default performance requirements initialized successfully."
    )
    return redirect("performance_requirement_list")
