from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
import json

from django.views.decorators.http import require_http_methods
from shs_system.models import Form, Department, LearningArea, Teacher, SchoolInformation
from shs_system.forms import FormForm, LearningAreaForm, DepartmentForm


# Form views
@login_required
@user_passes_test(lambda u: u.role == "admin")
def form_list(request):
    # Get user's school for multi-tenancy
    school = request.user.school
    forms = Form.objects.filter(school=school).order_by("form_number")

    context = {
        "forms": forms,
        "title": "Forms/Grade Levels",
        "school": school,
    }
    return render(request, "form/form_list.html", context)


@login_required
@user_passes_test(lambda u: u.role == "admin")
def form_create(request):
    # Get user's school for multi-tenancy
    school = request.user.school

    if request.method == "POST":
        form = FormForm(request.POST, school=school)
        if form.is_valid():
            form_obj = form.save(commit=False)
            form_obj.school = school
            form_obj.save()
            messages.success(request, "Form/Grade level created successfully.")
            return redirect("form_list")
    else:
        form = FormForm(school=school)

    context = {
        "form": form,
        "title": "Create Form/Grade Level",
        "school": school,
    }
    return render(request, "form/form_form.html", context)


@login_required
@user_passes_test(lambda u: u.role == "admin")
def form_update(request, pk):
    # Get user's school for multi-tenancy
    school = request.user.school

    # Ensure form belongs to user's school
    form_obj = get_object_or_404(Form, pk=pk, school=school)

    if request.method == "POST":
        form = FormForm(request.POST, instance=form_obj, school=school)
        if form.is_valid():
            form.save()
            messages.success(request, "Form/Grade level updated successfully.")
            return redirect("form_list")
    else:
        form = FormForm(instance=form_obj, school=school)

    context = {
        "form": form,
        "form_obj": form_obj,
        "title": "Update Form/Grade Level",
        "school": school,
    }
    return render(request, "form/form_form.html", context)


@login_required
@user_passes_test(lambda u: u.role == "admin")
def form_delete(request, pk):
    # Get user's school for multi-tenancy
    school = request.user.school

    # Ensure form belongs to user's school
    form_obj = get_object_or_404(Form, pk=pk, school=school)

    if request.method == "POST":
        try:
            form_obj.delete()
            messages.success(request, "Form/Grade level deleted successfully.")
            return redirect("form_list")
        except Exception as e:
            messages.error(request, f"Error deleting form: {str(e)}")
            return redirect("form_list")

    context = {
        "object": form_obj,
        "title": "Delete Form/Grade Level",
        "object_name": form_obj.name,
        "cancel_url": "form_list",
        "school": school,
    }
    return render(request, "generic_confirm_delete.html", context)


# New AJAX-based Form API views
@login_required
@user_passes_test(lambda u: u.role == "admin")
@require_http_methods(["GET", "POST"])
def form_api_list(request):
    """API endpoint for listing and creating forms with AJAX"""
    # Get user's school for multi-tenancy
    school = request.user.school

    if request.method == "GET":
        forms = Form.objects.filter(school=school).order_by("form_number")
        forms_data = [
            {
                "id": form.id,
                "form_number": form.form_number,
                "name": form.name,
                "description": form.description or "",
            }
            for form in forms
        ]
        return JsonResponse({"forms": forms_data})

    elif request.method == "POST":
        try:
            data = json.loads(request.body)
            form = FormForm(data, school=school)

            if form.is_valid():
                new_form = form.save(commit=False)
                new_form.school = school
                new_form.save()
                return JsonResponse(
                    {
                        "id": new_form.id,
                        "form_number": new_form.form_number,
                        "name": new_form.name,
                        "description": new_form.description or "",
                    },
                    status=201,
                )
            else:
                return JsonResponse(form.errors, status=400)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON data"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


@login_required
@user_passes_test(lambda u: u.role == "admin")
@require_http_methods(["GET", "PUT", "DELETE"])
def form_api_detail(request, pk):
    """API endpoint for retrieving, updating, and deleting a specific form with AJAX"""
    # Get user's school for multi-tenancy
    school = request.user.school

    try:
        # Ensure form belongs to user's school
        form_obj = get_object_or_404(Form, pk=pk, school=school)

        if request.method == "GET":
            data = {
                "id": form_obj.id,
                "form_number": form_obj.form_number,
                "name": form_obj.name,
                "description": form_obj.description or "",
            }
            return JsonResponse(data)

        elif request.method == "PUT":
            try:
                data = json.loads(request.body)
                form = FormForm(data, instance=form_obj, school=school)

                if form.is_valid():
                    updated_form = form.save()
                    return JsonResponse(
                        {
                            "id": updated_form.id,
                            "form_number": updated_form.form_number,
                            "name": updated_form.name,
                            "description": updated_form.description or "",
                        }
                    )
                else:
                    return JsonResponse(form.errors, status=400)
            except json.JSONDecodeError:
                return JsonResponse({"error": "Invalid JSON data"}, status=400)

        elif request.method == "DELETE":
            try:
                form_obj.delete()
                return JsonResponse({"message": "Form deleted successfully"})
            except Exception as e:
                return JsonResponse(
                    {"error": f"Error deleting form: {str(e)}"}, status=500
                )

    except Form.DoesNotExist:
        return JsonResponse({"error": "Form not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# Learning Area views
@login_required
@user_passes_test(lambda u: u.role == "admin")
def learning_area_list(request):
    # Get user's school for multi-tenancy
    school = request.user.school

    learning_areas = LearningArea.objects.filter(school=school).order_by("name")
    context = {
        "learning_areas": learning_areas,
        "title": "Learning Areas",
        "school": school,
    }
    return render(request, "learning_area/learning_area_list.html", context)


@login_required
@user_passes_test(lambda u: u.role == "admin")
def learning_area_create(request):
    # Get user's school for multi-tenancy
    school = request.user.school

    if request.method == "POST":
        form = LearningAreaForm(request.POST, school=school)
        if form.is_valid():
            learning_area = form.save(commit=False)
            learning_area.school = school
            learning_area.save()
            messages.success(request, "Learning area created successfully.")
            return redirect("learning_area_list")
    else:
        form = LearningAreaForm(school=school)

    context = {
        "form": form,
        "title": "Create Learning Area",
        "school": school,
    }
    return render(request, "learning_area/learning_area_form.html", context)


@login_required
@user_passes_test(lambda u: u.role == "admin")
def learning_area_update(request, pk):
    # Get user's school for multi-tenancy
    school = request.user.school

    # Ensure learning area belongs to user's school
    learning_area = get_object_or_404(LearningArea, pk=pk, school=school)

    if request.method == "POST":
        form = LearningAreaForm(request.POST, instance=learning_area, school=school)
        if form.is_valid():
            form.save()
            messages.success(request, "Learning area updated successfully.")
            return redirect("learning_area_list")
    else:
        form = LearningAreaForm(instance=learning_area, school=school)

    context = {
        "form": form,
        "learning_area": learning_area,
        "title": "Update Learning Area",
        "school": school,
    }
    return render(request, "learning_area/learning_area_form.html", context)


@login_required
@user_passes_test(lambda u: u.role == "admin")
def learning_area_delete(request, pk):
    # Get user's school for multi-tenancy
    school = request.user.school

    # Ensure learning area belongs to user's school
    learning_area = get_object_or_404(LearningArea, pk=pk, school=school)

    if request.method == "POST":
        try:
            learning_area.delete()
            messages.success(request, "Learning area deleted successfully.")
            return redirect("learning_area_list")
        except Exception as e:
            messages.error(request, f"Error deleting learning area: {str(e)}")
            return redirect("learning_area_list")

    context = {
        "object": learning_area,
        "title": "Delete Learning Area",
        "object_name": learning_area.name,
        "cancel_url": "learning_area_list",
        "school": school,
    }
    return render(request, "generic_confirm_delete.html", context)


# Learning Area API Views
@login_required
@user_passes_test(lambda u: u.role == "admin")
@require_http_methods(["GET", "POST"])
def learning_area_api_list(request):
    """API endpoint for listing and creating learning areas with AJAX"""
    # Get user's school for multi-tenancy
    school = request.user.school

    if request.method == "GET":
        learning_areas = LearningArea.objects.filter(school=school).order_by("name")
        learning_areas_data = [
            {
                "id": learning_area.id,
                "code": learning_area.code,
                "name": learning_area.name,
                "description": learning_area.description or "",
            }
            for learning_area in learning_areas
        ]
        return JsonResponse({"learning_areas": learning_areas_data})

    elif request.method == "POST":
        try:
            data = json.loads(request.body)
            form = LearningAreaForm(data, school=school)

            if form.is_valid():
                new_learning_area = form.save(commit=False)
                new_learning_area.school = school
                new_learning_area.save()
                return JsonResponse(
                    {
                        "id": new_learning_area.id,
                        "code": new_learning_area.code,
                        "name": new_learning_area.name,
                        "description": new_learning_area.description or "",
                    },
                    status=201,
                )
            else:
                return JsonResponse(form.errors, status=400)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON data"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


@login_required
@user_passes_test(lambda u: u.role == "admin")
@require_http_methods(["GET", "PUT", "DELETE"])
def learning_area_api_detail(request, pk):
    """API endpoint for retrieving, updating, and deleting a specific learning area with AJAX"""
    # Get user's school for multi-tenancy
    school = request.user.school

    try:
        # Ensure learning area belongs to user's school
        learning_area = get_object_or_404(LearningArea, pk=pk, school=school)

        if request.method == "GET":
            data = {
                "id": learning_area.id,
                "code": learning_area.code,
                "name": learning_area.name,
                "description": learning_area.description or "",
            }
            return JsonResponse(data)

        elif request.method == "PUT":
            try:
                data = json.loads(request.body)
                form = LearningAreaForm(data, instance=learning_area, school=school)

                if form.is_valid():
                    updated_learning_area = form.save()
                    return JsonResponse(
                        {
                            "id": updated_learning_area.id,
                            "code": updated_learning_area.code,
                            "name": updated_learning_area.name,
                            "description": updated_learning_area.description or "",
                        }
                    )
                else:
                    return JsonResponse(form.errors, status=400)
            except json.JSONDecodeError:
                return JsonResponse({"error": "Invalid JSON data"}, status=400)

        elif request.method == "DELETE":
            try:
                learning_area.delete()
                return JsonResponse({"message": "Learning area deleted successfully"})
            except Exception as e:
                return JsonResponse(
                    {"error": f"Error deleting learning area: {str(e)}"}, status=500
                )

    except LearningArea.DoesNotExist:
        return JsonResponse({"error": "Learning area not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# Department views
@login_required
@user_passes_test(lambda u: u.role == "admin")
def department_list(request):
    # Get user's school for multi-tenancy
    school = request.user.school

    departments = Department.objects.filter(school=school).order_by("name")
    # Get teachers for the dropdown menu, filtered by school
    teachers = Teacher.objects.filter(user__school=school).order_by("full_name")

    context = {
        "departments": departments,
        "teachers": teachers,
        "title": "Departments",
        "school": school,
    }
    return render(request, "department/department_list.html", context)


@login_required
@user_passes_test(lambda u: u.role == "admin")
def department_create(request):
    # Get user's school for multi-tenancy
    school = request.user.school

    if request.method == "POST":
        form = DepartmentForm(request.POST, school=school)
        if form.is_valid():
            department = form.save(commit=False)
            department.school = school
            department.save()
            messages.success(request, "Department created successfully.")
            return redirect("department_list")
    else:
        form = DepartmentForm(school=school)

    context = {
        "form": form,
        "title": "Create Department",
        "school": school,
    }
    return render(request, "department/department_form.html", context)


@login_required
@user_passes_test(lambda u: u.role == "admin")
def department_update(request, pk):
    # Get user's school for multi-tenancy
    school = request.user.school

    # Ensure department belongs to user's school
    department = get_object_or_404(Department, pk=pk, school=school)

    if request.method == "POST":
        form = DepartmentForm(request.POST, instance=department, school=school)
        if form.is_valid():
            form.save()
            messages.success(request, "Department updated successfully.")
            return redirect("department_list")
    else:
        form = DepartmentForm(instance=department, school=school)

    context = {
        "form": form,
        "department": department,
        "title": "Update Department",
        "school": school,
    }
    return render(request, "department/department_form.html", context)


@login_required
@user_passes_test(lambda u: u.role == "admin")
def department_delete(request, pk):
    # Get user's school for multi-tenancy
    school = request.user.school

    # Ensure department belongs to user's school
    department = get_object_or_404(Department, pk=pk, school=school)

    if request.method == "POST":
        try:
            department.delete()
            messages.success(request, "Department deleted successfully.")
            return redirect("department_list")
        except Exception as e:
            messages.error(request, f"Error deleting department: {str(e)}")
            return redirect("department_list")

    context = {
        "object": department,
        "title": "Delete Department",
        "object_name": department.name,
        "cancel_url": "department_list",
        "school": school,
    }
    return render(request, "generic_confirm_delete.html", context)


# Department API Views
@login_required
@user_passes_test(lambda u: u.role == "admin")
@require_http_methods(["GET", "POST"])
def department_api_list(request):
    """API endpoint for listing and creating departments with AJAX"""
    # Get user's school for multi-tenancy
    school = request.user.school

    if request.method == "GET":
        departments = Department.objects.filter(school=school).order_by("name")
        teachers = Teacher.objects.filter(user__school=school).order_by("full_name")

        departments_data = [
            {
                "id": department.id,
                "code": department.code,
                "name": department.name,
                "description": department.description or "",
                "head_of_department": (
                    department.head_of_department.id
                    if department.head_of_department
                    else None
                ),
                "head_of_department_name": (
                    str(department.head_of_department)
                    if department.head_of_department
                    else ""
                ),
            }
            for department in departments
        ]

        teachers_data = [
            {
                "id": teacher.id,
                "full_name": teacher.full_name,
            }
            for teacher in teachers
        ]

        return JsonResponse(
            {"departments": departments_data, "teachers": teachers_data}
        )

    elif request.method == "POST":
        try:
            data = json.loads(request.body)
            form = DepartmentForm(data, school=school)

            if form.is_valid():
                new_department = form.save(commit=False)
                new_department.school = school
                new_department.save()
                return JsonResponse(
                    {
                        "id": new_department.id,
                        "code": new_department.code,
                        "name": new_department.name,
                        "description": new_department.description or "",
                        "head_of_department": (
                            new_department.head_of_department.id
                            if new_department.head_of_department
                            else None
                        ),
                        "head_of_department_name": (
                            str(new_department.head_of_department)
                            if new_department.head_of_department
                            else ""
                        ),
                    },
                    status=201,
                )
            else:
                return JsonResponse(form.errors, status=400)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON data"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


@login_required
@user_passes_test(lambda u: u.role == "admin")
@require_http_methods(["GET", "PUT", "DELETE"])
def department_api_detail(request, pk):
    """API endpoint for retrieving, updating, and deleting a specific department with AJAX"""
    # Get user's school for multi-tenancy
    school = request.user.school

    try:
        # Ensure department belongs to user's school
        department = get_object_or_404(Department, pk=pk, school=school)

        if request.method == "GET":
            data = {
                "id": department.id,
                "code": department.code,
                "name": department.name,
                "description": department.description or "",
                "head_of_department": (
                    department.head_of_department.id
                    if department.head_of_department
                    else None
                ),
                "head_of_department_name": (
                    str(department.head_of_department)
                    if department.head_of_department
                    else ""
                ),
            }
            return JsonResponse(data)

        elif request.method == "PUT":
            try:
                data = json.loads(request.body)
                form = DepartmentForm(data, instance=department, school=school)

                if form.is_valid():
                    updated_department = form.save()
                    return JsonResponse(
                        {
                            "id": updated_department.id,
                            "code": updated_department.code,
                            "name": updated_department.name,
                            "description": updated_department.description or "",
                            "head_of_department": (
                                updated_department.head_of_department.id
                                if updated_department.head_of_department
                                else None
                            ),
                            "head_of_department_name": (
                                str(updated_department.head_of_department)
                                if updated_department.head_of_department
                                else ""
                            ),
                        }
                    )
                else:
                    return JsonResponse(form.errors, status=400)
            except json.JSONDecodeError:
                return JsonResponse({"error": "Invalid JSON data"}, status=400)

        elif request.method == "DELETE":
            try:
                department.delete()
                return JsonResponse({"message": "Department deleted successfully"})
            except Exception as e:
                return JsonResponse(
                    {"error": f"Error deleting department: {str(e)}"}, status=500
                )

    except Department.DoesNotExist:
        return JsonResponse({"error": "Department not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# Teacher API for dropdowns
@login_required
@user_passes_test(lambda u: u.role == "admin")
@require_http_methods(["GET"])
def get_teachers_api(request):
    """API endpoint for getting the list of teachers for dropdowns"""
    # Get user's school for multi-tenancy
    school = request.user.school

    teachers = Teacher.objects.filter(user__school=school).order_by("full_name")
    teachers_data = [
        {
            "id": teacher.id,
            "full_name": teacher.full_name,
        }
        for teacher in teachers
    ]
    return JsonResponse({"teachers": teachers_data})
