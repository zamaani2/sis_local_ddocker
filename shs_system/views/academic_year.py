from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.urls import reverse
from django.http import HttpResponseRedirect, JsonResponse
from django.utils import timezone
from django.db import transaction
from django.core.paginator import Paginator
from django.db.models import Count

from shs_system.models import AcademicYear, Term
from shs_system.forms import AcademicYearForm, TermForm


def is_admin(user):
    return user.is_authenticated and user.role == "admin"


# New API endpoint to get academic year information
@login_required
def get_academic_year_info(request, year_id):
    """API endpoint to get academic year information by ID"""
    try:
        # Filter by user's school for multi-tenancy
        school = request.user.school
        academic_year = get_object_or_404(AcademicYear, pk=year_id, school=school)
        return JsonResponse(
            {
                "success": True,
                "id": academic_year.id,
                "name": academic_year.name,
                "start_date": academic_year.start_date.isoformat(),
                "end_date": academic_year.end_date.isoformat(),
                "is_current": academic_year.is_current,
                "school": academic_year.school.name if academic_year.school else None,
            }
        )
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=404)


# Academic Year Views
@login_required
@user_passes_test(is_admin)
def academic_year_list(request):
    """
    Display list of all academic years with search and filter options
    """
    # Filter by user's school for multi-tenancy and exclude archived years
    school = request.user.school
    academic_years = AcademicYear.objects.filter(
        school=school, is_archived=False
    ).order_by("-start_date")

    # Search functionality
    search_query = request.GET.get("search", "")
    if search_query:
        academic_years = academic_years.filter(name__icontains=search_query)

    # Filter by current status
    status_filter = request.GET.get("status", "")
    if status_filter == "current":
        academic_years = academic_years.filter(is_current=True)
    elif status_filter == "past":
        academic_years = academic_years.filter(is_current=False)

    # Pagination
    paginator = Paginator(academic_years, 10)  # Show 10 years per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Get stats for each academic year
    for year in page_obj:
        year.terms_count = Term.objects.filter(academic_year=year).count()

    context = {
        "page_obj": page_obj,
        "search_query": search_query,
        "status_filter": status_filter,
        "active_menu": "academic_year",
        "title": "Academic Years",
        "school": school,
    }

    return render(request, "admin/academic_year_list.html", context)


@login_required
@user_passes_test(is_admin)
def academic_year_create(request):
    """
    Create new academic year
    """
    # Get user's school for multi-tenancy
    school = request.user.school

    if request.method == "POST":
        form = AcademicYearForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                academic_year = form.save(commit=False)
                # Set the school for multi-tenancy
                academic_year.school = school

                # If marked as current, update other years for this school
                if academic_year.is_current:
                    AcademicYear.objects.filter(school=school, is_current=True).update(
                        is_current=False
                    )
                academic_year.save()

                messages.success(
                    request,
                    f'Academic year "{academic_year.name}" has been created successfully.',
                )
                request.session["sweet_alert"] = {
                    "title": "Success!",
                    "text": f'Academic year "{academic_year.name}" has been created successfully.',
                    "icon": "success",
                }
                return redirect("academic_year_list")
    else:
        # Default dates for new academic year (current year to next year)
        today = timezone.now().date()
        default_start = today.replace(month=9, day=1)  # September 1st
        default_end = default_start.replace(
            year=default_start.year + 1, month=7, day=31
        )  # July 31st next year

        form = AcademicYearForm(
            initial={
                "start_date": default_start,
                "end_date": default_end,
            }
        )

    context = {
        "form": form,
        "active_menu": "academic_year",
        "title": "Create Academic Year",
        "school": school,
    }

    return render(request, "admin/academic_year_form.html", context)


@login_required
@user_passes_test(is_admin)
def academic_year_edit(request, pk):
    """
    Edit existing academic year
    """
    # Filter by user's school for multi-tenancy
    school = request.user.school
    academic_year = get_object_or_404(AcademicYear, pk=pk, school=school)

    if request.method == "POST":
        form = AcademicYearForm(request.POST, instance=academic_year)
        if form.is_valid():
            with transaction.atomic():
                academic_year = form.save(commit=False)
                # Ensure school is set
                academic_year.school = school

                # If marked as current, update other years for this school
                if academic_year.is_current:
                    AcademicYear.objects.filter(school=school, is_current=True).exclude(
                        pk=pk
                    ).update(is_current=False)
                academic_year.save()

                messages.success(
                    request,
                    f'Academic year "{academic_year.name}" has been updated successfully.',
                )
                request.session["sweet_alert"] = {
                    "title": "Success!",
                    "text": f'Academic year "{academic_year.name}" has been updated successfully.',
                    "icon": "success",
                }
                return redirect("academic_year_list")
    else:
        form = AcademicYearForm(instance=academic_year)

    context = {
        "form": form,
        "academic_year": academic_year,
        "active_menu": "academic_year",
        "title": "Edit Academic Year",
        "school": school,
    }

    return render(request, "admin/academic_year_form.html", context)


@login_required
@user_passes_test(is_admin)
def academic_year_delete(request, pk):
    """
    Delete academic year after confirmation
    """
    # Filter by user's school for multi-tenancy
    school = request.user.school
    academic_year = get_object_or_404(AcademicYear, pk=pk, school=school)

    if request.method == "POST":
        try:
            # Check if the academic year has any associated terms
            terms_count = Term.objects.filter(academic_year=academic_year).count()

            if terms_count > 0:
                messages.error(
                    request,
                    f'Cannot delete "{academic_year.name}" because it has {terms_count} terms associated with it.',
                )
                request.session["sweet_alert"] = {
                    "title": "Error!",
                    "text": f'Cannot delete "{academic_year.name}" because it has {terms_count} terms associated with it.',
                    "icon": "error",
                }
                return redirect("academic_year_list")

            # Delete the academic year
            academic_year_name = academic_year.name
            academic_year.delete()
            messages.success(
                request,
                f'Academic year "{academic_year_name}" has been deleted successfully.',
            )
            request.session["sweet_alert"] = {
                "title": "Success!",
                "text": f'Academic year "{academic_year_name}" has been deleted successfully.',
                "icon": "success",
            }

        except Exception as e:
            messages.error(request, f"Error deleting academic year: {str(e)}")
            request.session["sweet_alert"] = {
                "title": "Error!",
                "text": f"Error deleting academic year: {str(e)}",
                "icon": "error",
            }

        return redirect("academic_year_list")

    context = {
        "academic_year": academic_year,
        "active_menu": "academic_year",
        "title": "Delete Academic Year",
        "school": school,
    }

    return render(request, "admin/academic_year_confirm_delete.html", context)


@login_required
@user_passes_test(is_admin)
def academic_year_detail(request, pk):
    """
    View academic year details including associated terms
    """
    # Filter by user's school for multi-tenancy
    school = request.user.school
    academic_year = get_object_or_404(AcademicYear, pk=pk, school=school)
    terms = Term.objects.filter(academic_year=academic_year, school=school).order_by(
        "term_number"
    )

    # Get term choices for the create term modal
    term_choices = [(1, "First Term"), (2, "Second Term"), (3, "Third Term")]

    # Find which terms already exist for this academic year
    existing_term_numbers = list(terms.values_list("term_number", flat=True))

    # Calculate available term choices (those that don't exist yet)
    available_term_choices = [
        (num, name) for num, name in term_choices if num not in existing_term_numbers
    ]

    # Add class count for each term
    for term in terms:
        # You can replace this with your actual class count query if you have a ClassSubject model with a term field
        term.class_count = 0  # Placeholder, replace with actual query
        # Example: term.class_count = ClassSubject.objects.filter(term=term).count()

    context = {
        "academic_year": academic_year,
        "terms": terms,
        "term_choices": term_choices,
        "available_term_choices": available_term_choices,
        "existing_term_numbers": existing_term_numbers,
        "active_menu": "academic_year",
        "title": f"Academic Year: {academic_year.name}",
        "school": school,
    }

    return render(request, "admin/academic_year_detail.html", context)


@login_required
@user_passes_test(is_admin)
def set_current_academic_year(request, pk):
    """
    Set an academic year as current
    """
    # Filter by user's school for multi-tenancy
    school = request.user.school
    academic_year = get_object_or_404(AcademicYear, pk=pk, school=school)

    with transaction.atomic():
        # Set all academic years for this school as not current
        AcademicYear.objects.filter(school=school, is_current=True).update(
            is_current=False
        )

        # Set the selected academic year as current
        academic_year.is_current = True
        academic_year.save()

        success_message = (
            f"{academic_year.name} has been set as the current academic year."
        )

        messages.success(request, success_message)
        request.session["sweet_alert"] = {
            "title": "Success!",
            "text": success_message,
            "icon": "success",
        }

        # Check if this is an AJAX request
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": True, "message": success_message})

    return redirect("academic_year_list")


# Term Views
@login_required
@user_passes_test(is_admin)
def term_list(request):
    """
    Display list of all terms with filter options
    """
    # Filter by user's school for multi-tenancy
    school = request.user.school
    terms = Term.objects.filter(school=school).order_by(
        "-academic_year__start_date", "term_number"
    )

    # Filter by academic year
    academic_year_id = request.GET.get("academic_year", "")
    if academic_year_id:
        terms = terms.filter(academic_year_id=academic_year_id)

    # Filter by current status
    status_filter = request.GET.get("status", "")
    if status_filter == "current":
        terms = terms.filter(is_current=True)

    # Search functionality
    search_query = request.GET.get("search", "")
    if search_query:
        terms = terms.filter(academic_year__name__icontains=search_query)

    # Pagination
    paginator = Paginator(terms, 10)  # Show 10 terms per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Get all academic years for the filter dropdown
    academic_years = AcademicYear.objects.filter(school=school).order_by("-start_date")

    context = {
        "page_obj": page_obj,
        "academic_years": academic_years,
        "academic_year_id": academic_year_id,
        "status_filter": status_filter,
        "search_query": search_query,
        "active_menu": "term",
        "title": "Terms",
        "school": school,
    }

    return render(request, "admin/term_list.html", context)


@login_required
@user_passes_test(is_admin)
def term_create(request):
    """
    Create new term
    """
    # Get user's school for multi-tenancy
    school = request.user.school

    # Get the academic year from query parameter if present
    academic_year_id = request.GET.get("academic_year", None)
    academic_year = None

    if academic_year_id:
        academic_year = get_object_or_404(
            AcademicYear, pk=academic_year_id, school=school
        )

    if request.method == "POST":
        form = TermForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                term = form.save(commit=False)

                # Make sure the academic year belongs to this school
                if term.academic_year.school != school:
                    messages.error(
                        request,
                        "The selected academic year does not belong to your school.",
                    )
                    return redirect("term_list")

                # Set the school for multi-tenancy
                term.school = school

                # If this term is marked as current, update other terms in the same school
                if term.is_current:
                    Term.objects.filter(school=school, is_current=True).update(
                        is_current=False
                    )

                term.save()
                success_message = f"Term {term.get_term_number_display()} has been created successfully."

                messages.success(request, success_message)
                request.session["sweet_alert"] = {
                    "title": "Success!",
                    "text": success_message,
                    "icon": "success",
                }

                # Check if this is an AJAX request
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse(
                        {
                            "success": True,
                            "message": success_message,
                            "term_id": term.id,
                            "term_name": term.get_term_number_display(),
                        }
                    )

                # Redirect back to the academic year detail page if came from there
                if "next" in request.GET:
                    return redirect(request.GET["next"])
                return redirect("term_list")
        elif request.headers.get("X-Requested-With") == "XMLHttpRequest":
            # Return form errors as JSON for AJAX requests
            return JsonResponse(
                {
                    "success": False,
                    "errors": form.errors,
                    "message": "There were errors in your submission.",
                },
                status=400,
            )
    else:
        initial_data = {}

        if academic_year:
            initial_data["academic_year"] = academic_year

            # Check which terms already exist for this academic year
            existing_terms = set(
                Term.objects.filter(academic_year=academic_year).values_list(
                    "term_number", flat=True
                )
            )
            available_terms = [t for t in range(1, 4) if t not in existing_terms]

            # If there are available terms, suggest the next one
            if available_terms:
                initial_data["term_number"] = min(available_terms)

                # Suggest dates based on the academic year and term number
                ay_start = academic_year.start_date
                ay_end = academic_year.end_date
                term_length = (ay_end - ay_start).days // 3

                if initial_data["term_number"] == 1:
                    initial_data["start_date"] = ay_start
                    initial_data["end_date"] = ay_start.replace(
                        day=1
                    ) + timezone.timedelta(days=term_length)
                elif initial_data["term_number"] == 2:
                    initial_data["start_date"] = ay_start.replace(
                        day=1
                    ) + timezone.timedelta(days=term_length + 1)
                    initial_data["end_date"] = ay_start.replace(
                        day=1
                    ) + timezone.timedelta(days=term_length * 2)
                elif initial_data["term_number"] == 3:
                    initial_data["start_date"] = ay_start.replace(
                        day=1
                    ) + timezone.timedelta(days=term_length * 2 + 1)
                    initial_data["end_date"] = ay_end

        form = TermForm(initial=initial_data)

        # Filter academic years by school for multi-tenancy
        form.fields["academic_year"].queryset = AcademicYear.objects.filter(
            school=school
        )

    context = {
        "form": form,
        "academic_year": academic_year,
        "active_menu": "term",
        "title": "Create Term",
        "school": school,
    }

    return render(request, "admin/term_form.html", context)


@login_required
@user_passes_test(is_admin)
def term_edit(request, pk):
    """
    Edit existing term
    """
    # Filter by user's school for multi-tenancy
    school = request.user.school
    term = get_object_or_404(Term, pk=pk, school=school)

    if request.method == "POST":
        form = TermForm(request.POST, instance=term)
        if form.is_valid():
            with transaction.atomic():
                updated_term = form.save(commit=False)

                # Make sure the academic year belongs to this school
                if updated_term.academic_year.school != school:
                    messages.error(
                        request,
                        "The selected academic year does not belong to your school.",
                    )
                    return redirect("term_list")

                # Set the school for multi-tenancy
                updated_term.school = school

                # If this term is marked as current, update other terms in the same school
                if updated_term.is_current:
                    Term.objects.filter(school=school, is_current=True).exclude(
                        pk=pk
                    ).update(is_current=False)

                updated_term.save()
                success_message = f"Term {updated_term.get_term_number_display()} has been updated successfully."

                messages.success(request, success_message)
                request.session["sweet_alert"] = {
                    "title": "Success!",
                    "text": success_message,
                    "icon": "success",
                }

                # Check if this is an AJAX request
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse(
                        {
                            "success": True,
                            "message": success_message,
                            "term_id": updated_term.id,
                            "term_name": updated_term.get_term_number_display(),
                        }
                    )

                # Redirect back to the academic year detail page if came from there
                if "next" in request.GET:
                    return redirect(request.GET["next"])
                return redirect("term_list")
        elif request.headers.get("X-Requested-With") == "XMLHttpRequest":
            # Return form errors as JSON for AJAX requests
            return JsonResponse(
                {
                    "success": False,
                    "errors": form.errors,
                    "message": "There were errors in your submission.",
                },
                status=400,
            )
    else:
        form = TermForm(instance=term)
        # Filter academic years by school for multi-tenancy
        form.fields["academic_year"].queryset = AcademicYear.objects.filter(
            school=school
        )

    context = {
        "form": form,
        "term": term,
        "active_menu": "term",
        "title": "Edit Term",
        "school": school,
    }

    return render(request, "admin/term_form.html", context)


@login_required
@user_passes_test(is_admin)
def term_delete(request, pk):
    """
    Delete term after confirmation
    """
    # Filter by user's school for multi-tenancy
    school = request.user.school
    term = get_object_or_404(Term, pk=pk, school=school)

    if request.method == "POST":
        try:
            # First check if the term has any assessments or other dependent records
            # If dependent records exist, don't allow deletion

            # Here you would add checks for any models that depend on Term
            # For example:
            # assessment_count = Assessment.objects.filter(term=term).count()
            # if assessment_count > 0:
            #     messages.error(request, f'Cannot delete term because it has {assessment_count} assessments.')
            #     request.session['sweet_alert'] = {
            #         'title': 'Error!',
            #         'text': f'Cannot delete term because it has {assessment_count} assessments.',
            #         'icon': 'error',
            #     }
            #     return redirect('term_list')

            # Delete the term
            academic_year = term.academic_year
            term_name = term.get_term_number_display()
            term.delete()

            success_message = (
                f"{term_name} for {academic_year.name} has been deleted successfully."
            )

            messages.success(request, success_message)
            request.session["sweet_alert"] = {
                "title": "Success!",
                "text": success_message,
                "icon": "success",
            }

            # Check if this is an AJAX request
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"success": True, "message": success_message})

            # Redirect back to the academic year detail page if came from there
            if "next" in request.GET:
                return redirect(request.GET["next"])

        except Exception as e:
            error_message = f"Error deleting term: {str(e)}"

            messages.error(request, error_message)
            request.session["sweet_alert"] = {
                "title": "Error!",
                "text": error_message,
                "icon": "error",
            }

            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {"success": False, "message": error_message}, status=400
                )

        return redirect("term_list")

    context = {
        "term": term,
        "active_menu": "term",
        "title": "Delete Term",
        "school": school,
    }

    return render(request, "admin/term_confirm_delete.html", context)


@login_required
@user_passes_test(is_admin)
def set_current_term(request, pk):
    """
    Set a term as current
    """
    # Filter by user's school for multi-tenancy
    school = request.user.school
    term = get_object_or_404(Term, pk=pk, school=school)

    with transaction.atomic():
        # Set all terms in the same school as not current
        Term.objects.filter(school=school, is_current=True).update(is_current=False)

        # Set the selected term as current
        term.is_current = True
        term.save()

        # Also set the academic year as current if it's not already
        if not term.academic_year.is_current:
            AcademicYear.objects.filter(school=school, is_current=True).update(
                is_current=False
            )
            term.academic_year.is_current = True
            term.academic_year.save()

        success_message = (
            f"{term.get_term_number_display()} has been set as the current term."
        )

        messages.success(request, success_message)
        request.session["sweet_alert"] = {
            "title": "Success!",
            "text": success_message,
            "icon": "success",
        }

        # Check if this is an AJAX request
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": True, "message": success_message})

    # Redirect back to the previous page if 'next' is provided
    next_url = request.POST.get("next") or request.GET.get("next")
    if next_url:
        return redirect(next_url)
    return redirect("term_list")


def api_get_terms(request):
    """
    API endpoint to get terms filtered by academic year and school.
    Used by the teacher monitoring dashboard for dynamic term filtering.
    """
    from django.http import JsonResponse
    from ..models import Term
    from ..utils import get_user_school

    academic_year_id = request.GET.get("academic_year")
    school_id = request.GET.get("school")

    # Get school context
    if school_id:
        from ..models import SchoolInformation

        try:
            school = SchoolInformation.objects.get(id=school_id)
        except SchoolInformation.DoesNotExist:
            school = get_user_school(request.user)
    else:
        school = get_user_school(request.user)

    # Base query
    terms_query = Term.objects.all()

    # Filter by academic year if provided
    if academic_year_id:
        terms_query = terms_query.filter(academic_year_id=academic_year_id)

    # Filter by school if not superadmin
    if school:
        terms_query = terms_query.filter(school=school)

    # Order by term number
    terms_query = terms_query.order_by("term_number")

    # Convert to list of dictionaries
    terms_data = [
        {
            "id": term.id,
            "name": f"Term {term.term_number}",
            "term_number": term.term_number,
            "start_date": (
                term.start_date.strftime("%Y-%m-%d") if term.start_date else None
            ),
            "end_date": term.end_date.strftime("%Y-%m-%d") if term.end_date else None,
        }
        for term in terms_query
    ]

    return JsonResponse(terms_data, safe=False)
