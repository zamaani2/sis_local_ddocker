from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from shs_system.models import Subject, ClassSubject, LearningArea, Department
from shs_system.forms import SubjectForm


@login_required
def subject_list(request):
    """
    Display a list of all subjects ordered by learning area and subject name.
    Also provides the form for creating a new subject.
    """
    # Get user's school for multi-tenancy
    school = request.user.school

    # Filter subjects by school
    subjects = Subject.objects.filter(school=school).order_by(
        "learning_area", "subject_name"
    )
    form = SubjectForm(school=school)

    context = {
        "subjects": subjects,
        "form": form,
        "page_title": "Subjects Management",
        "school": school,
    }
    return render(request, "subject/subject_list.html", context)


@login_required
@require_POST
def subject_create(request):
    """
    Handle the creation of a new subject.
    Returns JSON response when request is AJAX, otherwise redirects.
    """
    # Get user's school for multi-tenancy
    school = request.user.school

    form = SubjectForm(request.POST, school=school)
    if form.is_valid():
        subject = form.save(commit=False)
        subject.school = school
        subject.save()
        messages.success(request, "Subject created successfully.")

        # Check if this is an AJAX request
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {
                    "status": "success",
                    "message": f'Subject "{subject.subject_name}" created successfully.',
                    "subject": {
                        "id": subject.id,
                        "subject_code": subject.subject_code,
                        "subject_name": subject.subject_name,
                        "learning_area": (
                            str(subject.learning_area) if subject.learning_area else ""
                        ),
                    },
                }
            )
        return redirect("subject_list")
    else:
        # Return form errors if validation fails
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {"status": "error", "errors": form.errors.as_json()}, status=400
            )

    # If not AJAX or validation failed, render the form again
    subjects = Subject.objects.filter(school=school).order_by(
        "learning_area", "subject_name"
    )
    context = {"subjects": subjects, "form": form, "school": school}
    return render(request, "subject/subject_list.html", context)


@login_required
def subject_update(request, pk):
    """
    Handle the updating of an existing subject.
    Returns JSON response when request is AJAX, otherwise redirects.
    """
    # Get user's school for multi-tenancy
    school = request.user.school

    # Ensure subject belongs to user's school
    subject = get_object_or_404(Subject, pk=pk, school=school)

    if request.method == "POST":
        form = SubjectForm(request.POST, instance=subject, school=school)
        if form.is_valid():
            updated_subject = form.save()
            messages.success(
                request,
                f'Subject "{updated_subject.subject_name}" updated successfully.',
            )

            # Check if this is an AJAX request
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {
                        "status": "success",
                        "message": f'Subject "{updated_subject.subject_name}" updated successfully.',
                        "subject": {
                            "id": updated_subject.id,
                            "subject_code": updated_subject.subject_code,
                            "subject_name": updated_subject.subject_name,
                            "learning_area": (
                                str(updated_subject.learning_area)
                                if updated_subject.learning_area
                                else ""
                            ),
                        },
                    }
                )
            return redirect("subject_list")
        else:
            # Return form errors if validation fails
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {"status": "error", "errors": form.errors.as_json()}, status=400
                )
    else:
        form = SubjectForm(instance=subject, school=school)

    subjects = Subject.objects.filter(school=school).order_by(
        "learning_area", "subject_name"
    )
    context = {
        "subjects": subjects,
        "form": form,
        "subject": subject,
        "is_update": True,
        "school": school,
    }
    return render(request, "subject/subject_list.html", context)


@login_required
def subject_delete(request, pk):
    """
    Handle the deletion of an existing subject.
    Checks for dependencies before deletion.
    Returns JSON response when request is AJAX, otherwise redirects.
    """
    # Get user's school for multi-tenancy
    school = request.user.school

    # Ensure subject belongs to user's school
    subject = get_object_or_404(Subject, pk=pk, school=school)
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    # Check for existing dependencies before deletion
    if ClassSubject.objects.filter(subject=subject).exists():
        error_message = f'Cannot delete subject "{subject.subject_name}" because it is assigned to one or more classes.'
        messages.error(request, error_message)

        if is_ajax:
            return JsonResponse(
                {"status": "error", "message": error_message}, status=400
            )
        return redirect("subject_list")

    if request.method == "POST":
        try:
            subject_name = subject.subject_name
            subject.delete()
            success_message = f'Subject "{subject_name}" deleted successfully.'
            messages.success(request, success_message)

            if is_ajax:
                return JsonResponse({"status": "success", "message": success_message})
        except Exception as e:
            error_message = f"Error deleting subject: {str(e)}"
            messages.error(request, error_message)

            if is_ajax:
                return JsonResponse(
                    {"status": "error", "message": error_message}, status=500
                )

        if not is_ajax:
            return redirect("subject_list")

    # For GET requests or non-AJAX POSTs that didn't get caught above
    context = {
        "subject": subject,
        "subjects": Subject.objects.filter(school=school).order_by(
            "learning_area", "subject_name"
        ),
        "is_delete": True,
        "school": school,
    }
    return render(request, "subject/subject_list.html", context)
