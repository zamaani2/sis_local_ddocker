"""
Views for academic year archiving and deletion management.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db import transaction

from shs_system.models import AcademicYear


def is_admin(user):
    return user.is_authenticated and user.role == "admin"


@login_required
@user_passes_test(is_admin)
def archive_academic_year(request, academic_year_id):
    """
    Archive an academic year (safe option).
    """
    academic_year = get_object_or_404(
        AcademicYear, id=academic_year_id, school=request.user.school
    )

    if academic_year.is_archived:
        messages.warning(
            request, f"Academic year '{academic_year.name}' is already archived."
        )
        return redirect("academic_year_list")

    if request.method == "POST":
        try:
            with transaction.atomic():
                academic_year.archive(user=request.user)

                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse(
                        {
                            "success": True,
                            "message": f'Academic year "{academic_year.name}" has been archived successfully. All data is preserved and can be restored later.',
                            "redirect_url": "/school/academic-years/",
                        }
                    )
                else:
                    messages.success(
                        request,
                        f'Academic year "{academic_year.name}" has been archived successfully. '
                        "All data is preserved and can be restored later.",
                    )
                    return redirect("academic_year_list")

        except Exception as e:
            error_message = f"Error archiving academic year: {str(e)}"
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"success": False, "message": error_message})
            else:
                messages.error(request, error_message)
                return redirect("academic_year_list")

    # Show confirmation page
    context = {
        "academic_year": academic_year,
        "title": f"Archive Academic Year: {academic_year.name}",
        "active_menu": "academic_year",
        "school": request.user.school,
    }
    return render(request, "admin/academic_year_archive_confirm.html", context)


@login_required
@user_passes_test(is_admin)
def unarchive_academic_year(request, academic_year_id):
    """
    Unarchive an academic year.
    """
    academic_year = get_object_or_404(
        AcademicYear, id=academic_year_id, school=request.user.school
    )

    if not academic_year.is_archived:
        messages.warning(
            request, f"Academic year '{academic_year.name}' is not archived."
        )
        return redirect("academic_year_list")

    if request.method == "POST":
        try:
            with transaction.atomic():
                academic_year.unarchive()

                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse(
                        {
                            "success": True,
                            "message": f'Academic year "{academic_year.name}" has been restored successfully.',
                            "redirect_url": "/school/academic-years/",
                        }
                    )
                else:
                    messages.success(
                        request,
                        f'Academic year "{academic_year.name}" has been restored successfully.',
                    )
                    return redirect("academic_year_list")

        except Exception as e:
            error_message = f"Error unarchiving academic year: {str(e)}"
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"success": False, "message": error_message})
            else:
                messages.error(request, error_message)
                return redirect("academic_year_list")

    # Show confirmation page
    context = {
        "academic_year": academic_year,
        "title": f"Restore Academic Year: {academic_year.name}",
        "active_menu": "academic_year",
        "school": request.user.school,
    }
    return render(request, "admin/academic_year_unarchive_confirm.html", context)


@login_required
@user_passes_test(is_admin)
def academic_year_archive_list(request):
    """
    List archived academic years.
    """
    school = request.user.school
    archived_years = AcademicYear.objects.filter(
        school=school, is_archived=True
    ).order_by("-archived_at")

    context = {
        "archived_years": archived_years,
        "title": "Archived Academic Years",
        "active_menu": "academic_year",
        "school": school,
    }
    return render(request, "admin/academic_year_archive_list.html", context)
