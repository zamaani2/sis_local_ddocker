from django.db import transaction
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from shs_system.models import (
    SchoolInformation,
    SchoolAuthoritySignature,
    AcademicYear,
    Term,
    ScoringConfiguration,
)
from shs_system.forms import SchoolInformationForm, SchoolAuthoritySignatureForm

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.http import JsonResponse
from decimal import Decimal, InvalidOperation


# Helper function to get user's school
def get_user_school(user):
    """
    Get the school associated with the current user.
    For superadmins, this will return None (they can access all schools).
    For other users, it will return their associated school.
    """
    if user.is_superadmin:
        return None  # Superadmins can access all schools
    return user.school


# Helper mixin for admin permissions
class SchoolAdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        # Allow access if user is a superadmin or school admin
        return self.request.user.is_superadmin or self.request.user.role == "admin"

    def get_permission_denied_message(self):
        return "You must be a school administrator to access this page."


# Helper mixin for school-specific access
class SchoolSpecificAccessMixin:
    """Mixin to filter queryset based on user's school"""

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        # If user is superadmin, they can see all schools
        if user.is_superadmin:
            return queryset

        # Otherwise, filter by user's school
        return queryset.filter(id=user.school.id if user.school else None)


# Helper function for setting SweetAlert notifications
def set_sweet_alert(request, title, text, icon="success"):
    """
    Store SweetAlert notification data in the session
    """
    request.session["sweet_alert"] = {
        "title": title,
        "text": text,
        "icon": icon,  # Can be 'success', 'error', 'warning', 'info', or 'question'
    }


# School Information Views
class SchoolInformationListView(
    SchoolAdminRequiredMixin, SchoolSpecificAccessMixin, ListView
):
    model = SchoolInformation
    template_name = "school/school_information_list.html"
    context_object_name = "schools"


class SchoolInformationDetailView(
    SchoolAdminRequiredMixin, SchoolSpecificAccessMixin, DetailView
):
    model = SchoolInformation
    template_name = "school/school_information_detail.html"
    context_object_name = "school"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add authority signatures to the context
        context["authority_signatures"] = SchoolAuthoritySignature.objects.filter(
            school=self.object
        )
        return context


class SchoolInformationCreateView(SchoolAdminRequiredMixin, CreateView):
    model = SchoolInformation
    form_class = SchoolInformationForm
    template_name = "school/school_information_form.html"
    success_url = reverse_lazy("school_information_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Add user and user_school to form kwargs
        kwargs["user"] = self.request.user
        kwargs["user_school"] = get_user_school(self.request.user)
        return kwargs

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user

        # Set the school for non-superadmins
        if not self.request.user.is_superadmin and self.request.user.school:
            form.instance = self.request.user.school

        # Use SweetAlert instead of regular Django messages
        set_sweet_alert(
            self.request,
            "Success!",
            "School information created successfully.",
            "success",
        )

        return super().form_valid(form)


class SchoolInformationUpdateView(
    SchoolAdminRequiredMixin, SchoolSpecificAccessMixin, UpdateView
):
    model = SchoolInformation
    form_class = SchoolInformationForm
    template_name = "school/school_information_form.html"

    def get_success_url(self):
        return reverse_lazy("school_information_detail", kwargs={"pk": self.object.pk})

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Add user and user_school to form kwargs
        kwargs["user"] = self.request.user
        kwargs["user_school"] = get_user_school(self.request.user)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add debug information to context
        if self.object.current_academic_year:
            context["available_terms"] = Term.objects.filter(
                academic_year=self.object.current_academic_year
            ).order_by("start_date")
            context["current_term"] = self.object.current_term
            # Enable debug info in template
            context["debug"] = True

        # Add user's school to context
        context["user_school"] = get_user_school(self.request.user)
        return context

    def form_valid(self, form):
        form.instance.updated_by = self.request.user

        # Ensure user has permission to update this school
        user = self.request.user
        if not user.is_superadmin and user.school and user.school.id != self.object.id:
            # Return form invalid if user doesn't have access
            form.add_error(
                None, "You don't have permission to update information for this school."
            )
            return self.form_invalid(form)

        # Use SweetAlert instead of regular Django messages
        set_sweet_alert(
            self.request,
            "Success!",
            "School information updated successfully.",
            "success",
        )

        return super().form_valid(form)

    def form_invalid(self, form):
        """Handle form validation errors with more detailed information"""
        # Debug: Log form errors
        for field, errors in form.errors.items():
            print(f"Field error {field}: {', '.join(errors)}")

        if "current_term" in form.errors:
            # Check submitted data
            form_data = self.request.POST
            academic_year_id = form_data.get("current_academic_year")
            term_id = form_data.get("current_term")

            if academic_year_id and term_id:
                try:
                    # Check if term exists
                    term = Term.objects.get(id=term_id)
                    academic_year = AcademicYear.objects.get(id=academic_year_id)
                    print(
                        f"Term belongs to academic year: {term.academic_year.id == academic_year.id}"
                    )
                    print(f"Term: {term}, Academic Year: {academic_year}")
                except (Term.DoesNotExist, AcademicYear.DoesNotExist) as e:
                    print(f"Error finding term or academic year: {str(e)}")

        return super().form_invalid(form)


class SchoolInformationDeleteView(
    SchoolAdminRequiredMixin, SchoolSpecificAccessMixin, DeleteView
):
    model = SchoolInformation
    template_name = "school/school_information_confirm_delete.html"
    success_url = reverse_lazy("school_information_list")

    def delete(self, request, *args, **kwargs):
        school = self.get_object()
        response = super().delete(request, *args, **kwargs)

        # Use SweetAlert instead of regular Django messages
        set_sweet_alert(
            request,
            "Deleted!",
            f"School information for {school.name} has been deleted successfully.",
            "success",
        )

        return response


class SetActiveSchoolView(
    SchoolAdminRequiredMixin, SchoolSpecificAccessMixin, UpdateView
):
    model = SchoolInformation
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        school = self.get_object()

        # Deactivate all other schools
        with transaction.atomic():
            # If superadmin, deactivate all schools; otherwise, just make this one active
            if request.user.is_superadmin:
                SchoolInformation.objects.all().update(is_active=False)
            school.is_active = True
            school.save()

        # Use SweetAlert instead of regular Django messages
        set_sweet_alert(
            request,
            "Active School Set!",
            f"{school.name} has been set as the active school.",
            "success",
        )

        return redirect("school_information_list")


# School Authority Signature Views
class SchoolAuthoritySignatureListView(SchoolAdminRequiredMixin, ListView):
    model = SchoolAuthoritySignature
    template_name = "school/authority_signature_list.html"
    context_object_name = "signatures"

    def get_queryset(self):
        school_id = self.kwargs.get("school_id")
        user = self.request.user

        # Ensure the user has access to this school
        if (
            not user.is_superadmin
            and user.school
            and str(user.school.id) != str(school_id)
        ):
            return SchoolAuthoritySignature.objects.none()

        return SchoolAuthoritySignature.objects.filter(school_id=school_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        school_id = self.kwargs.get("school_id")

        # Verify user has access to this school
        user = self.request.user
        if (
            not user.is_superadmin
            and user.school
            and str(user.school.id) != str(school_id)
        ):
            # Return empty context if user doesn't have access
            context["school"] = None
            return context

        context["school"] = get_object_or_404(SchoolInformation, pk=school_id)
        return context


class SchoolAuthoritySignatureCreateView(SchoolAdminRequiredMixin, CreateView):
    model = SchoolAuthoritySignature
    form_class = SchoolAuthoritySignatureForm
    template_name = "school/authority_signature_form.html"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        school_id = self.kwargs.get("school_id")

        # Verify user has access to this school
        user = self.request.user
        if (
            not user.is_superadmin
            and user.school
            and str(user.school.id) != str(school_id)
        ):
            # Return form with no initial data if user doesn't have access
            return form

        form.initial["school"] = school_id
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        school_id = self.kwargs.get("school_id")

        # Verify user has access to this school
        user = self.request.user
        if (
            not user.is_superadmin
            and user.school
            and str(user.school.id) != str(school_id)
        ):
            # Return empty context if user doesn't have access
            context["school"] = None
            return context

        context["school"] = get_object_or_404(SchoolInformation, pk=school_id)
        return context

    def get_success_url(self):
        return reverse_lazy(
            "authority_signature_list", kwargs={"school_id": self.object.school.id}
        )

    def form_valid(self, form):
        # Verify user has access to this school
        school_id = self.kwargs.get("school_id")
        user = self.request.user

        if (
            not user.is_superadmin
            and user.school
            and str(user.school.id) != str(school_id)
        ):
            # Return form invalid if user doesn't have access
            form.add_error(
                None, "You don't have permission to create signatures for this school."
            )
            return self.form_invalid(form)

        response = super().form_valid(form)

        # Use SweetAlert instead of regular Django messages
        set_sweet_alert(
            self.request,
            "Success!",
            f"Authority signature for {self.object.name} added successfully.",
            "success",
        )

        return response


class SchoolAuthoritySignatureUpdateView(SchoolAdminRequiredMixin, UpdateView):
    model = SchoolAuthoritySignature
    form_class = SchoolAuthoritySignatureForm
    template_name = "school/authority_signature_form.html"

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        # If user is superadmin, they can see all signatures
        if user.is_superadmin:
            return queryset

        # Otherwise, filter by user's school
        return queryset.filter(school=user.school if user.school else None)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["school"] = self.object.school
        return context

    def get_success_url(self):
        return reverse_lazy(
            "authority_signature_list", kwargs={"school_id": self.object.school.id}
        )

    def form_valid(self, form):
        # Verify user has access to this signature's school
        user = self.request.user
        if not user.is_superadmin and user.school != self.object.school:
            # Return form invalid if user doesn't have access
            form.add_error(
                None, "You don't have permission to update signatures for this school."
            )
            return self.form_invalid(form)

        response = super().form_valid(form)

        # Use SweetAlert instead of regular Django messages
        set_sweet_alert(
            self.request,
            "Updated!",
            f"Authority signature for {self.object.name} updated successfully.",
            "success",
        )

        return response


class SchoolAuthoritySignatureDeleteView(SchoolAdminRequiredMixin, DeleteView):
    model = SchoolAuthoritySignature
    template_name = "school/authority_signature_confirm_delete.html"

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        # If user is superadmin, they can see all signatures
        if user.is_superadmin:
            return queryset

        # Otherwise, filter by user's school
        return queryset.filter(school=user.school if user.school else None)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["school"] = self.object.school
        return context

    def get_success_url(self):
        school_id = self.object.school.id
        return reverse_lazy("authority_signature_list", kwargs={"school_id": school_id})

    def delete(self, request, *args, **kwargs):
        signature = self.get_object()

        # Verify user has access to this signature's school
        user = self.request.user
        if not user.is_superadmin and user.school != signature.school:
            # Return to list view if user doesn't have access
            return redirect(
                "authority_signature_list",
                school_id=user.school.id if user.school else 0,
            )

        school_id = signature.school.id
        response = super().delete(request, *args, **kwargs)

        # Use SweetAlert instead of regular Django messages
        set_sweet_alert(
            request,
            "Deleted!",
            f"Authority signature for {signature.name} has been deleted successfully.",
            "success",
        )

        return response


class SetActiveSignatureView(SchoolAdminRequiredMixin, UpdateView):
    model = SchoolAuthoritySignature
    http_method_names = ["post"]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        # If user is superadmin, they can see all signatures
        if user.is_superadmin:
            return queryset

        # Otherwise, filter by user's school
        return queryset.filter(school=user.school if user.school else None)

    def post(self, request, *args, **kwargs):
        signature = self.get_object()

        # Verify user has access to this signature's school
        user = self.request.user
        if not user.is_superadmin and user.school != signature.school:
            # Return to list view if user doesn't have access
            return redirect(
                "authority_signature_list",
                school_id=user.school.id if user.school else 0,
            )

        # Get all signatures of the same type for this school
        same_type_signatures = SchoolAuthoritySignature.objects.filter(
            school=signature.school, authority_type=signature.authority_type
        )

        # Set them all to inactive
        same_type_signatures.update(is_active=False)

        # Set the current one to active
        signature.is_active = True
        signature.save()

        # Use SweetAlert instead of regular Django messages
        set_sweet_alert(
            request,
            "Active Signature Set!",
            f"{signature.name} set as the active {signature.display_title()}.",
            "success",
        )

        return redirect("authority_signature_list", school_id=signature.school.id)


@login_required
def get_terms_by_academic_year(request, academic_year_id):
    """
    AJAX view to get terms for a specific academic year.
    Returns terms as JSON for dynamic loading in the form.
    """
    try:
        # Verify user has access to this academic year's school
        academic_year = get_object_or_404(AcademicYear, pk=academic_year_id)
        user = request.user
        user_school = get_user_school(user)

        # Check permissions for non-superadmins
        if (
            not user.is_superadmin
            and user_school
            and academic_year.school
            and user_school != academic_year.school
        ):
            return JsonResponse(
                {
                    "error": "You don't have permission to access terms for this academic year."
                },
                status=403,
            )

        # Get terms for this academic year (only if academic year is not archived)
        if academic_year.is_archived:
            return JsonResponse(
                {
                    "error": "Cannot access terms for archived academic year.",
                    "terms": [],
                },
                status=400,
            )

        terms = Term.objects.filter(academic_year=academic_year).order_by("start_date")

        # Get current term ID from the request if provided
        current_term_id = request.GET.get("current_term_id")

        # Create a list of terms in JSON format with better formatting
        terms_data = [
            {
                "id": term.id,
                "name": f"{term.get_term_number_display()}",
            }
            for term in terms
        ]

        response_data = {"terms": terms_data, "current_term_id": current_term_id}

        return JsonResponse(response_data)
    except Exception as e:
        import traceback

        print(f"ERROR in get_terms_by_academic_year: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({"error": str(e)}, status=400)


@login_required
def manage_scoring_config(request):
    """Manage scoring configuration for the school."""
    # Ensure only school admins can access this view
    if request.user.role != "admin":
        messages.error(
            request, "Only school administrators can manage scoring configurations."
        )
        return redirect("dashboard")

    # Get user's school
    user_school = get_user_school(request.user)
    if not user_school:
        messages.error(request, "No school associated with your account.")
        return redirect("dashboard")

    # Get current configuration
    current_config = ScoringConfiguration.get_active_config(user_school)

    if request.method == "POST":
        try:
            # Get form data
            exam_score_percentage = Decimal(
                request.POST.get("exam_score_percentage", 70)
            )
            class_score_percentage = Decimal(
                request.POST.get("class_score_percentage", 30)
            )
            max_class_score = Decimal(request.POST.get("max_class_score", 30))

            # Class score component max marks
            individual_max_mark = Decimal(request.POST.get("individual_max_mark", 15))
            class_test_max_mark = Decimal(request.POST.get("class_test_max_mark", 15))
            project_max_mark = Decimal(request.POST.get("project_max_mark", 15))
            group_work_max_mark = Decimal(request.POST.get("group_work_max_mark", 15))

            # Validate percentages sum to 100%
            if abs((exam_score_percentage + class_score_percentage) - 100) > 0.01:
                messages.error(
                    request, "Exam and class score percentages must sum to 100%."
                )
                return redirect("manage_scoring_config")

            # Validate class score component max marks are not all zero (to prevent division by zero)
            total_max_marks = (
                individual_max_mark
                + class_test_max_mark
                + project_max_mark
                + group_work_max_mark
            )
            if total_max_marks == 0:
                messages.error(
                    request, "Class score component max marks cannot all be zero."
                )
                return redirect("manage_scoring_config")

            # Create or update configuration
            if current_config:
                # Update existing configuration
                current_config.exam_score_percentage = exam_score_percentage
                current_config.class_score_percentage = class_score_percentage
                current_config.max_class_score = max_class_score
                current_config.individual_max_mark = individual_max_mark
                current_config.class_test_max_mark = class_test_max_mark
                current_config.project_max_mark = project_max_mark
                current_config.group_work_max_mark = group_work_max_mark
                current_config.save()
                messages.success(request, "Scoring configuration updated successfully!")
            else:
                # Create new configuration
                ScoringConfiguration.objects.create(
                    school=user_school,
                    exam_score_percentage=exam_score_percentage,
                    class_score_percentage=class_score_percentage,
                    max_class_score=max_class_score,
                    individual_max_mark=individual_max_mark,
                    class_test_max_mark=class_test_max_mark,
                    project_max_mark=project_max_mark,
                    group_work_max_mark=group_work_max_mark,
                    created_by=request.user,
                    is_active=True,
                )
                messages.success(request, "Scoring configuration created successfully!")
            return redirect("manage_scoring_config")

        except (ValueError, InvalidOperation) as e:
            messages.error(request, f"Invalid input: {str(e)}")
        except Exception as e:
            messages.error(request, f"Error saving configuration: {str(e)}")

    context = {
        "current_config": current_config,
        "user_school": user_school,
    }

    return render(request, "school/manage_scoring_config.html", context)
