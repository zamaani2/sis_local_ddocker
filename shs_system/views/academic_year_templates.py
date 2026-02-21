"""
Views for Academic Year Template management.
Handles CRUD operations for templates and template application.
"""

import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone

from ..models import (
    AcademicYear,
    AcademicYearTemplate,
    Class,
    ClassSubject,
    TeacherSubjectAssignment,
    ClassTeacher,
    SchoolInformation,
)
from ..forms import (
    AcademicYearTemplateForm,
    CreateTemplateFromAcademicYearForm,
    ApplyTemplateForm,
    TemplateCustomizationForm,
)
from ..utils.template_utils import (
    create_template_from_academic_year,
    apply_template_to_academic_year,
    get_template_statistics,
    validate_template_data,
)
from .auth import is_admin


@login_required
@user_passes_test(is_admin)
def template_list(request):
    """
    List all academic year templates for the user's school.
    """
    school = request.user.school

    # Get templates for the school (only active templates since we do hard deletes)
    templates = AcademicYearTemplate.objects.filter(
        school=school, is_active=True
    ).order_by("-is_default", "-created_at")

    # Get statistics for each template
    template_stats = []
    for template in templates:
        stats = get_template_statistics(template)
        template_stats.append({"template": template, "stats": stats})

    context = {
        "templates": template_stats,
        "title": "Academic Year Templates",
        "active_menu": "academic_year",
        "school": school,
    }

    return render(request, "admin/academic_year_template_list.html", context)


@login_required
@user_passes_test(is_admin)
def template_detail(request, template_id):
    """
    View detailed information about a template.
    """
    school = request.user.school
    template = get_object_or_404(
        AcademicYearTemplate, id=template_id, school=school, is_active=True
    )

    # Get template statistics
    stats = get_template_statistics(template)

    # Get class structures
    class_structures = template.get_class_structures()

    # Get subject assignments
    subject_assignments = template.get_subject_assignments()

    # Get teacher assignments
    teacher_assignments = template.get_teacher_assignments()

    # Get class teacher assignments
    class_teacher_assignments = template.template_data.get(
        "class_teacher_assignments", []
    )

    context = {
        "template": template,
        "stats": stats,
        "class_structures": class_structures,
        "subject_assignments": subject_assignments,
        "teacher_assignments": teacher_assignments,
        "class_teacher_assignments": class_teacher_assignments,
        "title": f"Template: {template.name}",
        "active_menu": "academic_year",
        "school": school,
    }

    return render(request, "admin/academic_year_template_detail.html", context)


@login_required
@user_passes_test(is_admin)
def template_create(request):
    """
    Create a new template manually.
    """
    school = request.user.school

    if request.method == "POST":
        form = AcademicYearTemplateForm(request.POST, school=school)
        if form.is_valid():
            template = form.save(commit=False)
            template.school = school
            template.created_by = request.user
            template.save()

            messages.success(
                request, f'Template "{template.name}" created successfully.'
            )
            return redirect("template_detail", template_id=template.id)
    else:
        form = AcademicYearTemplateForm(school=school)

    context = {
        "form": form,
        "title": "Create New Template",
        "active_menu": "academic_year",
        "school": school,
    }

    return render(request, "admin/academic_year_template_form.html", context)


@login_required
@user_passes_test(is_admin)
def template_create_from_academic_year(request):
    """
    Create a template from an existing academic year.
    """
    school = request.user.school

    if request.method == "POST":
        form = CreateTemplateFromAcademicYearForm(request.POST, school=school)
        if form.is_valid():
            academic_year = form.cleaned_data["academic_year"]
            template_name = form.cleaned_data["template_name"]
            description = form.cleaned_data["description"]
            is_default = form.cleaned_data["is_default"]

            # Check if academic year has any classes
            classes_count = Class.objects.filter(
                academic_year=academic_year, school=academic_year.school
            ).count()

            if classes_count == 0:
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse(
                        {
                            "success": False,
                            "message": f"The academic year '{academic_year.name}' has no classes. Please create classes first before creating a template.",
                        }
                    )
                else:
                    messages.error(
                        request,
                        f"The academic year '{academic_year.name}' has no classes. "
                        "Please create classes first before creating a template.",
                    )
                    return render(
                        request,
                        "admin/academic_year_template_create_from_year.html",
                        {
                            "form": form,
                            "title": "Create Template from Academic Year",
                            "active_menu": "academic_year",
                            "school": school,
                        },
                    )

            # Create template from academic year
            try:
                template = create_template_from_academic_year(
                    academic_year=academic_year,
                    template_name=template_name,
                    description=description,
                    created_by=request.user,
                )

                # Check if template was created successfully and has data
                if not template or not template.template_data:
                    raise Exception("Template creation failed - no data generated")

                # Check if template has essential data
                template_data = template.template_data
                if not template_data.get("class_structures") and not template_data.get(
                    "classes"
                ):
                    raise Exception(
                        "Template creation failed - no class structures found"
                    )

                # Set as default if requested
                if is_default:
                    template.is_default = True
                    template.save()

                # Success - template created
                success_message = f'Template "{template.name}" created successfully from {academic_year.name}.'

                # Check for warnings in template data
                if (
                    hasattr(template, "template_data")
                    and "warnings" in template.template_data
                ):
                    warnings = template.template_data["warnings"]
                    if "subjects_without_teachers" in warnings:
                        subjects_without_teachers = warnings[
                            "subjects_without_teachers"
                        ]
                        success_message += f" Note: Some subjects don't have teachers assigned: {', '.join(subjects_without_teachers[:3])}"
                        if len(subjects_without_teachers) > 3:
                            success_message += (
                                f" and {len(subjects_without_teachers) - 3} more."
                            )

                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse(
                        {
                            "success": True,
                            "message": success_message,
                            "redirect_url": reverse("template_list"),
                        }
                    )
                else:
                    messages.success(request, success_message)
                    return redirect("template_list")

            except Exception as e:
                import traceback

                error_details = traceback.format_exc()
                print(f"Template creation error: {error_details}")

                # Check if template was actually created despite the error
                existing_template = AcademicYearTemplate.objects.filter(
                    name=template_name, school=school, created_by=request.user
                ).first()

                if existing_template:
                    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                        return JsonResponse(
                            {
                                "success": True,
                                "message": f'Template "{existing_template.name}" was created successfully! You can view it in the templates list.',
                                "redirect_url": reverse("template_list"),
                            }
                        )
                    else:
                        messages.success(
                            request,
                            f'Template "{existing_template.name}" was created successfully! '
                            f"You can view it in the templates list.",
                        )
                        return redirect("template_list")
                else:
                    # Only show error if template was not created
                    error_message = f"Error creating template: {str(e)}. Please try again or contact support if the issue persists."

                    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                        return JsonResponse(
                            {"success": False, "message": error_message}
                        )
                    else:
                        messages.error(request, error_message)
                        return render(
                            request,
                            "admin/academic_year_template_create_from_year.html",
                            {
                                "form": form,
                                "title": "Create Template from Academic Year",
                                "active_menu": "academic_year",
                                "school": school,
                            },
                        )
        else:
            # Form validation errors
            error_messages = []
            for field, errors in form.errors.items():
                for error in errors:
                    error_messages.append(f"{field}: {error}")

            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {"success": False, "message": "; ".join(error_messages)}
                )
            else:
                for error in error_messages:
                    messages.error(request, error)
    else:
        form = CreateTemplateFromAcademicYearForm(school=school)

    context = {
        "form": form,
        "title": "Create Template from Academic Year",
        "active_menu": "academic_year",
        "school": school,
    }

    return render(
        request, "admin/academic_year_template_create_from_year.html", context
    )


@login_required
@user_passes_test(is_admin)
def template_edit(request, template_id):
    """
    Edit an existing template.
    """
    school = request.user.school
    template = get_object_or_404(
        AcademicYearTemplate, id=template_id, school=school, is_active=True
    )

    if request.method == "POST":
        form = AcademicYearTemplateForm(request.POST, instance=template, school=school)
        if form.is_valid():
            form.save()
            messages.success(
                request, f'Template "{template.name}" updated successfully.'
            )
            return redirect("template_detail", template_id=template.id)
    else:
        form = AcademicYearTemplateForm(instance=template, school=school)

    context = {
        "form": form,
        "template": template,
        "title": f"Edit Template: {template.name}",
        "active_menu": "academic_year",
        "school": school,
    }

    return render(request, "admin/academic_year_template_form.html", context)


@login_required
@user_passes_test(is_admin)
def template_delete(request, template_id):
    """
    Permanently delete a template to manage storage.
    """
    school = request.user.school
    template = get_object_or_404(
        AcademicYearTemplate, id=template_id, school=school, is_active=True
    )

    if request.method == "POST":
        # Get template name before deletion for success message
        template_name = template.name

        # Check if template is being used by any academic years
        from shs_system.models import AcademicYear

        used_by_years = AcademicYear.objects.filter(
            school=school, name__icontains=template_name
        ).count()

        if used_by_years > 0:
            messages.warning(
                request,
                f'Template "{template_name}" is referenced by {used_by_years} academic year(s). '
                "Consider archiving instead of deleting to preserve data integrity.",
            )
            return redirect("template_list")

        # Perform hard delete
        template.delete()
        messages.success(request, f'Template "{template_name}" permanently deleted.')
        return redirect("template_list")

    context = {
        "template": template,
        "title": f"Delete Template: {template.name}",
        "active_menu": "academic_year",
        "school": school,
    }

    return render(request, "admin/academic_year_template_confirm_delete.html", context)


@login_required
@user_passes_test(is_admin)
def template_apply(request, template_id):
    """
    Apply a template to create a new academic year.
    """
    school = request.user.school
    template = get_object_or_404(
        AcademicYearTemplate, id=template_id, school=school, is_active=True
    )

    if request.method == "POST":
        form = ApplyTemplateForm(request.POST, school=school)
        if form.is_valid():
            try:
                # Validate template has data before proceeding
                template_data = template.template_data
                if not template_data:
                    raise Exception("Template has no data - cannot be applied")

                if not template_data.get("class_structures") and not template_data.get(
                    "classes"
                ):
                    raise Exception(
                        "Template has no class structures - cannot be applied"
                    )

                with transaction.atomic():
                    # Create new academic year
                    academic_year = AcademicYear.objects.create(
                        name=form.cleaned_data["academic_year_name"],
                        start_date=form.cleaned_data["start_date"],
                        end_date=form.cleaned_data["end_date"],
                        is_current=form.cleaned_data["is_current"],
                        school=school,
                    )

                    # Apply template
                    customizations = {}
                    if form.cleaned_data.get("customize_class_names"):
                        # Get customization form data if provided
                        customization_form = TemplateCustomizationForm(request.POST)
                        if customization_form.is_valid():
                            customizations = {
                                "class_prefixes": customization_form.cleaned_data.get(
                                    "class_prefixes", {}
                                ),
                                "year_suffix": customization_form.cleaned_data.get(
                                    "year_suffix", ""
                                ),
                            }

                    results = apply_template_to_academic_year(
                        template, academic_year, customizations
                    )

                    # Show results
                    if results["errors"]:
                        for error in results["errors"]:
                            messages.error(request, error)

                    if results["warnings"]:
                        for warning in results["warnings"]:
                            messages.warning(request, warning)

                    if not results["errors"]:
                        success_message = (
                            f'Academic year "{academic_year.name}" created successfully with '
                            f'{results["classes_created"]} classes, '
                            f'{results["subjects_assigned"]} subject assignments, '
                            f'{results["teacher_assignments_created"]} teacher assignments, and '
                            f'{results["class_teachers_assigned"]} class teachers.'
                        )

                        # Handle AJAX requests
                        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                            return JsonResponse(
                                {
                                    "success": True,
                                    "message": success_message,
                                    "redirect_url": reverse(
                                        "academic_year_detail",
                                        kwargs={"pk": academic_year.id},
                                    ),
                                }
                            )
                        else:
                            messages.success(request, success_message)
                            return redirect("academic_year_detail", pk=academic_year.id)
                    else:
                        # If there were errors, delete the academic year
                        academic_year.delete()
                        error_message = "Template application failed due to errors. Please check the template data."

                        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                            return JsonResponse(
                                {"success": False, "message": error_message}
                            )
                        else:
                            messages.error(request, error_message)
                            return redirect("template_apply", template_id=template_id)

            except Exception as e:
                error_message = f"Error applying template: {str(e)}"

                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse({"success": False, "message": error_message})
                else:
                    messages.error(request, error_message)
    else:
        form = ApplyTemplateForm(school=school)
        # Pre-select this template
        form.fields["template"].initial = template.id

    # Get template statistics for preview
    stats = get_template_statistics(template)

    context = {
        "form": form,
        "template": template,
        "stats": stats,
        "title": f"Apply Template: {template.name}",
        "active_menu": "academic_year",
        "school": school,
    }

    return render(request, "admin/academic_year_template_apply.html", context)


@login_required
@user_passes_test(is_admin)
def template_preview(request, template_id):
    """
    Preview template structure as JSON.
    """
    school = request.user.school
    template = get_object_or_404(
        AcademicYearTemplate, id=template_id, school=school, is_active=True
    )

    # Get template data
    template_data = {
        "template_info": {
            "name": template.name,
            "description": template.description,
            "created_at": template.created_at,
            "created_from_year": (
                template.created_from_year.name if template.created_from_year else None
            ),
        },
        "statistics": get_template_statistics(template),
        "template_data": template.template_data,
    }

    return JsonResponse(template_data, json_dumps_params={"indent": 2})


@login_required
@user_passes_test(is_admin)
def template_duplicate(request, template_id):
    """
    Duplicate an existing template.
    """
    school = request.user.school
    template = get_object_or_404(
        AcademicYearTemplate, id=template_id, school=school, is_active=True
    )

    if request.method == "POST":
        new_name = request.POST.get("new_name")
        if new_name:
            try:
                # Create duplicate template
                duplicate = AcademicYearTemplate.objects.create(
                    name=new_name,
                    description=template.description,
                    school=school,
                    created_by=request.user,
                    template_data=template.template_data,
                    is_default=False,
                )

                messages.success(
                    request, f'Template "{duplicate.name}" created successfully.'
                )
                return redirect("template_detail", template_id=duplicate.id)

            except Exception as e:
                messages.error(request, f"Error duplicating template: {str(e)}")
        else:
            messages.error(request, "Template name is required.")

    context = {
        "template": template,
        "title": f"Duplicate Template: {template.name}",
        "active_menu": "academic_year",
        "school": school,
    }

    return render(request, "admin/academic_year_template_duplicate.html", context)


@login_required
@user_passes_test(is_admin)
def template_set_default(request, template_id):
    """
    Set a template as the default template.
    """
    school = request.user.school
    template = get_object_or_404(
        AcademicYearTemplate, id=template_id, school=school, is_active=True
    )

    if request.method == "POST":
        template.is_default = True
        template.save()
        messages.success(request, f'Template "{template.name}" set as default.')

    return redirect("template_list")


@login_required
@user_passes_test(is_admin)
def template_export(request, template_id):
    """
    Export template data as JSON file.
    """
    school = request.user.school
    template = get_object_or_404(
        AcademicYearTemplate, id=template_id, school=school, is_active=True
    )

    # Prepare export data
    export_data = {
        "template_info": {
            "name": template.name,
            "description": template.description,
            "created_at": template.created_at.isoformat(),
            "created_from_year": (
                template.created_from_year.name if template.created_from_year else None
            ),
        },
        "template_data": template.template_data,
    }

    # Create JSON response
    response = HttpResponse(
        json.dumps(export_data, indent=2), content_type="application/json"
    )
    response["Content-Disposition"] = (
        f'attachment; filename="{template.name}_template.json"'
    )

    return response
