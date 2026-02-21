from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.utils import timezone

from shs_system.models import AcademicYear, Term, SchoolInformation


def is_admin(user):
    return user.is_authenticated and user.role == "admin"


@login_required
@user_passes_test(is_admin)
def current_settings_dashboard(request):
    """
    Dashboard for managing current academic year and term settings
    """
    school = request.user.school

    # Get current settings
    school_info = SchoolInformation.objects.filter(id=school.id).first()
    current_academic_year = school_info.current_academic_year if school_info else None
    current_term = school_info.current_term if school_info else None

    # Get all active academic years for the school (exclude archived)
    academic_years = AcademicYear.objects.filter(
        school=school, is_archived=False
    ).order_by("-start_date")

    # Get all terms for the current academic year
    terms = []
    if current_academic_year:
        terms = Term.objects.filter(
            academic_year=current_academic_year, school=school
        ).order_by("term_number")

    # Get terms for all active academic years (for the dropdown)
    all_terms = (
        Term.objects.filter(school=school, academic_year__is_archived=False)
        .select_related("academic_year")
        .order_by("-academic_year__start_date", "term_number")
    )

    context = {
        "current_academic_year": current_academic_year,
        "current_term": current_term,
        "academic_years": academic_years,
        "terms": terms,
        "all_terms": all_terms,
        "school": school,
        "title": "Current Academic Settings",
    }

    return render(request, "admin/current_settings_dashboard.html", context)


@login_required
@user_passes_test(is_admin)
@csrf_protect
@require_http_methods(["POST"])
def set_current_academic_year(request):
    """
    Set the current academic year for the school
    """
    school = request.user.school

    try:
        academic_year_id = request.POST.get("academic_year_id")

        if not academic_year_id:
            return JsonResponse(
                {"success": False, "message": "Academic year ID is required"},
                status=400,
            )

        # Get the academic year
        try:
            academic_year = AcademicYear.objects.get(id=academic_year_id, school=school)
        except AcademicYear.DoesNotExist:
            return JsonResponse(
                {"success": False, "message": "Academic year not found"}, status=404
            )

        with transaction.atomic():
            # Update school information
            school_info, created = SchoolInformation.objects.get_or_create(
                id=school.id, defaults={"name": school.name}
            )

            # Set the current academic year
            school_info.current_academic_year = academic_year
            school_info.save()

            # Clear current term if it doesn't belong to the new academic year
            if (
                school_info.current_term
                and school_info.current_term.academic_year != academic_year
            ):
                school_info.current_term = None
                school_info.save()

        return JsonResponse(
            {
                "success": True,
                "message": f"Current academic year set to {academic_year.name}",
                "academic_year": {
                    "id": academic_year.id,
                    "name": academic_year.name,
                    "start_date": academic_year.start_date.strftime("%Y-%m-%d"),
                    "end_date": academic_year.end_date.strftime("%Y-%m-%d"),
                },
            }
        )

    except Exception as e:
        return JsonResponse(
            {
                "success": False,
                "message": f"Error setting current academic year: {str(e)}",
            },
            status=500,
        )


@login_required
@user_passes_test(is_admin)
@csrf_protect
@require_http_methods(["POST"])
def set_current_term(request):
    """
    Set the current term for the school
    """
    school = request.user.school

    try:
        term_id = request.POST.get("term_id")

        if not term_id:
            return JsonResponse(
                {"success": False, "message": "Term ID is required"}, status=400
            )

        # Get the term
        try:
            term = Term.objects.get(id=term_id, school=school)
        except Term.DoesNotExist:
            return JsonResponse(
                {"success": False, "message": "Term not found"}, status=404
            )

        with transaction.atomic():
            # Update school information
            school_info, created = SchoolInformation.objects.get_or_create(
                id=school.id, defaults={"name": school.name}
            )

            # Set the current term
            school_info.current_term = term
            school_info.save()

            # Also set the academic year if it's not set
            if not school_info.current_academic_year:
                school_info.current_academic_year = term.academic_year
                school_info.save()

        return JsonResponse(
            {
                "success": True,
                "message": f"Current term set to {term.get_term_number_display()} - {term.academic_year.name}",
                "term": {
                    "id": term.id,
                    "name": term.get_term_number_display(),
                    "academic_year": term.academic_year.name,
                    "start_date": term.start_date.strftime("%Y-%m-%d"),
                    "end_date": term.end_date.strftime("%Y-%m-%d"),
                },
            }
        )

    except Exception as e:
        return JsonResponse(
            {"success": False, "message": f"Error setting current term: {str(e)}"},
            status=500,
        )


@login_required
@user_passes_test(is_admin)
@csrf_protect
@require_http_methods(["POST"])
def set_current_settings_both(request):
    """
    Set both current academic year and term at once
    """
    school = request.user.school

    try:
        academic_year_id = request.POST.get("academic_year_id")
        term_id = request.POST.get("term_id")

        if not academic_year_id or not term_id:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Both academic year and term are required",
                },
                status=400,
            )

        # Get the academic year and term
        try:
            academic_year = AcademicYear.objects.get(id=academic_year_id, school=school)
            term = Term.objects.get(id=term_id, school=school)
        except (AcademicYear.DoesNotExist, Term.DoesNotExist):
            return JsonResponse(
                {"success": False, "message": "Academic year or term not found"},
                status=404,
            )

        # Verify term belongs to the academic year
        if term.academic_year != academic_year:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Term does not belong to the selected academic year",
                },
                status=400,
            )

        with transaction.atomic():
            # Update school information
            school_info, created = SchoolInformation.objects.get_or_create(
                id=school.id, defaults={"name": school.name}
            )

            # Set both current academic year and term
            school_info.current_academic_year = academic_year
            school_info.current_term = term
            school_info.save()

        return JsonResponse(
            {
                "success": True,
                "message": f"Current settings updated: {academic_year.name} - {term.get_term_number_display()}",
                "academic_year": {"id": academic_year.id, "name": academic_year.name},
                "term": {"id": term.id, "name": term.get_term_number_display()},
            }
        )

    except Exception as e:
        return JsonResponse(
            {"success": False, "message": f"Error setting current settings: {str(e)}"},
            status=500,
        )


@login_required
@user_passes_test(is_admin)
def get_terms_for_academic_year(request, academic_year_id):
    """
    Get terms for a specific academic year (AJAX endpoint)
    """
    school = request.user.school

    try:
        academic_year = AcademicYear.objects.get(id=academic_year_id, school=school)
        terms = Term.objects.filter(
            academic_year=academic_year, school=school
        ).order_by("term_number")

        terms_data = []
        for term in terms:
            terms_data.append(
                {
                    "id": term.id,
                    "name": term.get_term_number_display(),
                    "start_date": term.start_date.strftime("%Y-%m-%d"),
                    "end_date": term.end_date.strftime("%Y-%m-%d"),
                }
            )

        return JsonResponse({"success": True, "terms": terms_data})

    except AcademicYear.DoesNotExist:
        return JsonResponse(
            {"success": False, "message": "Academic year not found"}, status=404
        )
    except Exception as e:
        return JsonResponse(
            {"success": False, "message": f"Error fetching terms: {str(e)}"}, status=500
        )
