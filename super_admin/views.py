from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.utils.text import slugify
from datetime import date, datetime, timedelta
import random
import string
import logging
import json

from shs_system.models import (
    User,
    SchoolInformation,
    send_user_credentials_email,
    OAuthCredentialStore,
)
from .models import (
    Plan,
    Subscription,
    SchoolDomain,
    PaymentTransaction,
    SuperAdminSettings,
    SystemEmailConfig,
)
from .forms import (
    SchoolForm,
    PlanForm,
    SubscriptionForm,
    SchoolDomainForm,
    SuperAdminSettingsForm,
    SuperAdminUserForm,
    SchoolAdminForm,
    SystemEmailConfigForm,
)

from .backup_restore_views import *


# Optional imports for Google OAuth
GOOGLE_OAUTH_AVAILABLE = False
try:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from google.auth.transport.requests import Request
    from google.auth.exceptions import RefreshError
    from email.mime.text import MIMEText
    import base64

    GOOGLE_OAUTH_AVAILABLE = True
except ImportError:
    pass

logger = logging.getLogger(__name__)


# Helper function to check if user is a super admin
def is_superadmin(user):
    return user.is_authenticated and user.is_superadmin


# Landing page for the platform
def landing_page(request):
    """Landing page for the multi-school platform"""
    # Get platform settings
    try:
        settings = SuperAdminSettings.objects.first()
    except:
        settings = None

    # Check if we're in maintenance mode
    if settings and settings.is_maintenance_mode:
        return render(
            request,
            "super_admin/maintenance.html",
            {"message": settings.maintenance_message, "settings": settings},
        )

    return render(request, "super_admin/landing.html", {"settings": settings})


# Dashboard
@login_required
@user_passes_test(is_superadmin)
def dashboard(request):
    """Super admin dashboard"""
    # Get counts and statistics
    schools_count = SchoolInformation.objects.count()
    active_schools = SchoolInformation.objects.filter(is_active=True).count()
    active_subscriptions = Subscription.objects.filter(
        status="active", end_date__gte=timezone.now()
    ).count()
    trial_subscriptions = Subscription.objects.filter(
        status="trial", trial_ends_at__gte=timezone.now()
    ).count()
    expired_subscriptions = Subscription.objects.filter(
        status__in=["expired", "cancelled"]
    ).count()

    # Recent transactions
    recent_transactions = PaymentTransaction.objects.order_by("-payment_date")[:5]

    # Schools expiring soon
    expiring_soon = Subscription.objects.filter(
        status__in=["active", "trial"], end_date__lte=timezone.now() + timedelta(days=7)
    ).order_by("end_date")[:5]

    # New schools in the last 30 days
    new_schools = SchoolInformation.objects.filter(
        date_created__gte=timezone.now() - timedelta(days=30)
    ).order_by("-date_created")[:5]

    context = {
        "schools_count": schools_count,
        "active_schools": active_schools,
        "active_subscriptions": active_subscriptions,
        "trial_subscriptions": trial_subscriptions,
        "expired_subscriptions": expired_subscriptions,
        "recent_transactions": recent_transactions,
        "expiring_soon": expiring_soon,
        "new_schools": new_schools,
    }

    return render(request, "super_admin/dashboard.html", context)


# School management
@login_required
@user_passes_test(is_superadmin)
def school_list(request):
    """List all schools"""
    schools = SchoolInformation.objects.all().order_by("-is_active", "-date_created")
    return render(request, "super_admin/schools/list.html", {"schools": schools})


@login_required
@user_passes_test(is_superadmin)
def school_create(request):
    """Create a new school"""
    if request.method == "POST":
        form = SchoolForm(request.POST, request.FILES)
        if form.is_valid():
            # Create the school
            school = form.save(commit=False)
            school.created_by = request.user
            school.updated_by = request.user

            # Generate a unique slug from the school name
            base_slug = slugify(school.name)
            slug = base_slug
            counter = 1

            # Check if the slug already exists, if so, append a number
            while SchoolInformation.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            school.slug = slug
            school.short_name = (
                school.name[:20] if len(school.name) > 20 else school.name
            )
            school.save()

            # Get admin information from form
            admin_name = form.cleaned_data["admin_name"]
            admin_email = form.cleaned_data["admin_email"]
            domain_name = form.cleaned_data["domain"]

            # Create domain for the school (support various formats)
            if "." in domain_name:
                # If domain already has a dot, use it as is
                domain_value = domain_name
            else:
                # For development, use domain.localhost
                domain_value = f"{domain_name}.localhost"

            domain = SchoolDomain(school=school, domain=domain_value, is_primary=True)
            domain.save()

            # Create admin user for the school
            username = admin_email.split("@")[0]  # Use part of email as username

            # Generate a random password
            password = "".join(
                random.choices(string.ascii_letters + string.digits, k=10)
            )

            admin_user = User(
                username=username,
                email=admin_email,
                full_name=admin_name,
                role="admin",
                school=school,
            )
            admin_user.set_password(password)
            admin_user.save()

            # Send credentials to admin user
            try:
                send_user_credentials_email(admin_user, password)
                messages.success(request, f"Credentials sent to {admin_email}")
            except Exception as e:
                messages.warning(
                    request, f"School created but failed to send email: {str(e)}"
                )
                # Include the password in the message for development purposes
                messages.info(
                    request, f"Admin username: {username} | Password: {password}"
                )

            messages.success(request, f"School '{school.name}' created successfully.")
            return redirect("super_admin:school_detail", pk=school.pk)
    else:
        form = SchoolForm()

    return render(
        request,
        "super_admin/schools/form.html",
        {"form": form, "title": "Create School"},
    )


@login_required
@user_passes_test(is_superadmin)
def school_detail(request, pk):
    """View school details"""
    school = get_object_or_404(SchoolInformation, pk=pk)

    # Get subscription info
    try:
        subscription = school.subscription
    except:
        subscription = None

    # Get domains
    domains = school.domains.all()

    # Get school administrators
    administrators = User.objects.filter(school=school, role="admin")

    # Get user counts
    users = User.objects.filter(school=school)
    admin_count = users.filter(role="admin").count()
    teacher_count = users.filter(role="teacher").count()
    student_count = users.filter(role="student").count()

    context = {
        "school": school,
        "subscription": subscription,
        "domains": domains,
        "administrators": administrators,
        "admin_count": admin_count,
        "teacher_count": teacher_count,
        "student_count": student_count,
    }

    return render(request, "super_admin/schools/detail.html", context)


@login_required
@user_passes_test(is_superadmin)
def school_update(request, pk):
    """Update a school"""
    school = get_object_or_404(SchoolInformation, pk=pk)

    # Get primary domain for this school
    primary_domain = SchoolDomain.objects.filter(school=school, is_primary=True).first()

    # Extract domain prefix for the form
    domain_prefix = ""
    if primary_domain:
        # For domains with .localhost format
        if primary_domain.domain.endswith(".localhost"):
            domain_prefix = primary_domain.domain.split(".localhost")[0]
        else:
            # For custom domains, use the full domain
            domain_prefix = primary_domain.domain

    # Get admin user for this school
    admin_user = User.objects.filter(school=school, role="admin").first()

    if request.method == "POST":
        form = SchoolForm(request.POST, request.FILES, instance=school)
        if form.is_valid():
            # Update the school
            school = form.save(commit=False)
            school.updated_by = request.user

            # Update slug if the name has changed
            if "name" in form.changed_data:
                # Generate a unique slug from the school name
                base_slug = slugify(school.name)
                slug = base_slug
                counter = 1

                # Check if the slug already exists, if so, append a number
                while (
                    SchoolInformation.objects.filter(slug=slug)
                    .exclude(pk=school.pk)
                    .exists()
                ):
                    slug = f"{base_slug}-{counter}"
                    counter += 1

                school.slug = slug
                school.short_name = (
                    school.name[:20] if len(school.name) > 20 else school.name
                )

            # If is_featured is checked, add special treatment
            is_featured = form.cleaned_data.get("is_featured", False)
            # You might need to adjust this based on how featuring is implemented
            # For example, you might set a property or add to a featured group

            school.save()

            # Update domain if it changed
            domain_name = form.cleaned_data["domain"]

            # Process domain name
            if "." in domain_name:
                # If domain already has a dot, use it as is
                domain_value = domain_name
            else:
                # For development, use domain.localhost
                domain_value = f"{domain_name}.localhost"

            if primary_domain:
                if primary_domain.domain != domain_value:
                    primary_domain.domain = domain_value
                    primary_domain.save()
            else:
                # Create a new domain if one doesn't exist
                domain = SchoolDomain(
                    school=school, domain=domain_value, is_primary=True
                )
                domain.save()

            # If admin user exists, update their information
            admin_name = form.cleaned_data["admin_name"]
            admin_email = form.cleaned_data["admin_email"]

            if admin_user:
                admin_user.full_name = admin_name
                admin_user.email = admin_email
                admin_user.save()

            messages.success(request, f"School '{school.name}' updated successfully.")
            return redirect("super_admin:school_detail", pk=school.pk)
    else:
        # Pre-populate the form with existing data
        initial_data = {
            "admin_name": admin_user.full_name if admin_user else "",
            "admin_email": admin_user.email if admin_user else "",
            "domain": domain_prefix,
            "is_featured": False,  # Set based on your featuring implementation
        }
        form = SchoolForm(instance=school, initial=initial_data)

    return render(
        request,
        "super_admin/schools/form.html",
        {"form": form, "school": school, "title": "Update School"},
    )


@login_required
@user_passes_test(is_superadmin)
def school_delete(request, pk):
    """Delete a school"""
    school = get_object_or_404(SchoolInformation, pk=pk)

    if request.method == "POST":
        school_name = school.name
        school.delete()
        messages.success(request, f"School '{school_name}' deleted successfully.")
        return redirect("super_admin:school_list")

    return render(request, "super_admin/schools/delete.html", {"school": school})


@login_required
@user_passes_test(is_superadmin)
def impersonate_admin(request, pk):
    """Impersonate a school admin"""
    school = get_object_or_404(SchoolInformation, pk=pk)

    # Get the admin user for this school
    admin_user = User.objects.filter(school=school, role="admin").first()

    if not admin_user:
        messages.error(request, f"No admin user found for school '{school.name}'.")
        return redirect("super_admin:school_detail", pk=school.pk)

    # Store the superadmin's ID and role in the session to allow switching back
    request.session["impersonated_by"] = request.user.id
    request.session["impersonated_by_role"] = "superadmin"

    # Store original authentication information
    request.session["original_is_superadmin"] = request.user.is_superadmin

    # Log in as the admin user
    from django.contrib.auth import login

    login(request, admin_user)

    messages.success(
        request,
        f"You are now impersonating {admin_user.get_full_name()} (Admin of {school.name}).",
    )

    # Redirect to the school's admin dashboard
    return redirect("/dashboard/")


# Placeholder views for other endpoints - to be implemented as needed
@login_required
@user_passes_test(is_superadmin)
def plan_list(request):
    plans = Plan.objects.all().order_by("-is_active", "price")
    return render(request, "super_admin/plans/list.html", {"plans": plans})


@login_required
@user_passes_test(is_superadmin)
def plan_create(request):
    if request.method == "POST":
        form = PlanForm(request.POST)
        if form.is_valid():
            plan = form.save()
            messages.success(request, f"Plan '{plan.name}' created successfully.")
            return redirect("super_admin:plan_detail", pk=plan.pk)
    else:
        form = PlanForm()

    return render(
        request, "super_admin/plans/form.html", {"form": form, "title": "Create Plan"}
    )


@login_required
@user_passes_test(is_superadmin)
def plan_detail(request, pk):
    plan = get_object_or_404(Plan, pk=pk)
    return render(request, "super_admin/plans/detail.html", {"plan": plan})


@login_required
@user_passes_test(is_superadmin)
def plan_update(request, pk):
    plan = get_object_or_404(Plan, pk=pk)
    if request.method == "POST":
        form = PlanForm(request.POST, instance=plan)
        if form.is_valid():
            plan = form.save()
            messages.success(request, f"Plan '{plan.name}' updated successfully.")
            return redirect("super_admin:plan_detail", pk=plan.pk)
    else:
        form = PlanForm(instance=plan)

    return render(
        request,
        "super_admin/plans/form.html",
        {"form": form, "plan": plan, "title": "Update Plan"},
    )


@login_required
@user_passes_test(is_superadmin)
def plan_delete(request, pk):
    plan = get_object_or_404(Plan, pk=pk)
    # Placeholder - implement deletion confirmation
    return render(request, "super_admin/plans/delete.html", {"plan": plan})


# Similar placeholder views for subscriptions, domains, transactions, etc.
@login_required
@user_passes_test(is_superadmin)
def subscription_list(request):
    subscriptions = Subscription.objects.all().order_by("-start_date")
    return render(
        request, "super_admin/subscriptions/list.html", {"subscriptions": subscriptions}
    )


@login_required
@user_passes_test(is_superadmin)
def subscription_create(request):
    if request.method == "POST":
        form = SubscriptionForm(request.POST)
        if form.is_valid():
            subscription = form.save()
            messages.success(
                request,
                f"Subscription for {subscription.school.name} created successfully.",
            )
            return redirect("super_admin:subscription_detail", pk=subscription.pk)
    else:
        form = SubscriptionForm()

    return render(
        request,
        "super_admin/subscriptions/form.html",
        {"form": form, "title": "Create Subscription"},
    )


@login_required
@user_passes_test(is_superadmin)
def subscription_detail(request, pk):
    subscription = get_object_or_404(Subscription, pk=pk)

    # Get related transactions
    transactions = PaymentTransaction.objects.filter(
        subscription=subscription
    ).order_by("-payment_date")

    # Get available plans for renewal/conversion
    available_plans = Plan.objects.filter(is_active=True)

    # Calculate subscription progress and days remaining
    if subscription.status in ["active", "trial"]:
        # Convert datetime to date for consistent calculations
        start_date = (
            subscription.start_date.date()
            if hasattr(subscription.start_date, "date")
            else subscription.start_date
        )
        end_date = (
            subscription.end_date.date()
            if hasattr(subscription.end_date, "date")
            else subscription.end_date
        )
        current_date = timezone.now().date()

        total_days = (end_date - start_date).days
        days_elapsed = (current_date - start_date).days
        days_remaining = max(0, (end_date - current_date).days)

        if total_days > 0:
            subscription_progress = min(100, int((days_elapsed / total_days) * 100))
            trial_progress = subscription_progress  # Same calculation for trial
        else:
            subscription_progress = 100
            trial_progress = 100
    else:
        days_remaining = 0
        subscription_progress = 100
        trial_progress = 100

    context = {
        "subscription": subscription,
        "transactions": transactions,
        "available_plans": available_plans,
        "days_remaining": days_remaining,
        "subscription_progress": subscription_progress,
        "trial_progress": trial_progress,
        "trial_days_remaining": days_remaining if subscription.status == "trial" else 0,
    }

    return render(request, "super_admin/subscriptions/detail.html", context)


@login_required
@user_passes_test(is_superadmin)
def subscription_update(request, pk):
    subscription = get_object_or_404(Subscription, pk=pk)
    if request.method == "POST":
        form = SubscriptionForm(request.POST, instance=subscription)
        if form.is_valid():
            subscription = form.save()
            messages.success(
                request,
                f"Subscription for {subscription.school.name} updated successfully.",
            )
            return redirect("super_admin:subscription_detail", pk=subscription.pk)
    else:
        form = SubscriptionForm(instance=subscription)

    return render(
        request,
        "super_admin/subscriptions/form.html",
        {"form": form, "subscription": subscription, "title": "Update Subscription"},
    )


@login_required
@user_passes_test(is_superadmin)
def subscription_cancel(request, pk):
    """Cancel a subscription"""
    subscription = get_object_or_404(Subscription, pk=pk)

    if request.method == "POST":
        subscription.status = "cancelled"
        subscription.save()

        messages.success(
            request, f"Subscription for {subscription.school.name} has been cancelled."
        )
        return redirect("super_admin:subscription_list")

    return render(
        request, "super_admin/subscriptions/cancel.html", {"subscription": subscription}
    )


@login_required
@user_passes_test(is_superadmin)
def subscription_renew(request, pk):
    """Renew an expired or cancelled subscription"""
    subscription = get_object_or_404(Subscription, pk=pk)

    if request.method == "POST":
        try:
            plan_id = request.POST.get("plan")
            duration = int(request.POST.get("duration", 12))
            auto_renew = request.POST.get("auto_renew") == "on"

            plan = get_object_or_404(Plan, pk=plan_id)

            # Calculate new start and end dates
            start_date = timezone.now().date()
            end_date = start_date + timedelta(
                days=duration * 30
            )  # Approximate month to 30 days

            # Update subscription
            subscription.plan = plan
            subscription.start_date = start_date
            subscription.end_date = end_date
            subscription.status = "active"
            subscription.auto_renew = auto_renew
            subscription.save()

            # Create a payment transaction record
            PaymentTransaction.objects.create(
                school=subscription.school,
                subscription=subscription,
                amount=plan.price * duration,
                payment_method="manual",  # Default to manual since we're doing this from admin panel
                payment_date=timezone.now(),
                status="completed",
            )

            messages.success(
                request,
                f"Subscription for {subscription.school.name} has been renewed.",
            )
            return redirect("super_admin:subscription_detail", pk=subscription.id)
        except Exception as e:
            messages.error(request, f"Error renewing subscription: {str(e)}")
            return redirect("super_admin:subscription_detail", pk=subscription.id)

    # GET request, show form - though we're using a modal in the template
    return redirect("super_admin:subscription_detail", pk=subscription.id)


@login_required
@user_passes_test(is_superadmin)
def subscription_convert(request, pk):
    """Convert a trial subscription to a paid subscription"""
    subscription = get_object_or_404(Subscription, pk=pk)

    if request.method == "POST":
        try:
            plan_id = request.POST.get("plan")
            duration = int(request.POST.get("duration", 12))
            auto_renew = request.POST.get("auto_renew") == "on"
            payment_method = request.POST.get("payment_method", "manual")

            plan = get_object_or_404(Plan, pk=plan_id)

            # Calculate new end date (keep the current start date)
            end_date = timezone.now().date() + timedelta(
                days=duration * 30
            )  # Approximate month to 30 days

            # Update subscription
            subscription.plan = plan
            subscription.end_date = end_date
            subscription.status = "active"
            subscription.auto_renew = auto_renew
            subscription.save()

            # Create a payment transaction record
            PaymentTransaction.objects.create(
                school=subscription.school,
                subscription=subscription,
                amount=plan.price * duration,
                payment_method=payment_method,
                payment_date=timezone.now(),
                status="completed",
            )

            messages.success(
                request,
                f"Trial subscription for {subscription.school.name} has been converted to a paid subscription.",
            )
            return redirect("super_admin:subscription_detail", pk=subscription.id)
        except Exception as e:
            messages.error(request, f"Error converting subscription: {str(e)}")
            return redirect("super_admin:subscription_detail", pk=subscription.id)

    # GET request, show form - though we're using a modal in the template
    return redirect("super_admin:subscription_detail", pk=subscription.id)


# Domain management
@login_required
@user_passes_test(is_superadmin)
def domain_list(request):
    domains = SchoolDomain.objects.all().order_by("-is_verified", "domain")
    return render(request, "super_admin/domains/list.html", {"domains": domains})


@login_required
@user_passes_test(is_superadmin)
def domain_create(request):
    if request.method == "POST":
        form = SchoolDomainForm(request.POST)
        if form.is_valid():
            domain = form.save()
            messages.success(request, f"Domain '{domain.domain}' created successfully.")
            return redirect("super_admin:domain_list")
    else:
        form = SchoolDomainForm()

    return render(
        request,
        "super_admin/domains/form.html",
        {"form": form, "title": "Create Domain"},
    )


@login_required
@user_passes_test(is_superadmin)
def domain_update(request, pk):
    domain = get_object_or_404(SchoolDomain, pk=pk)
    if request.method == "POST":
        form = SchoolDomainForm(request.POST, instance=domain)
        if form.is_valid():
            domain = form.save()
            messages.success(request, f"Domain '{domain.domain}' updated successfully.")
            return redirect("super_admin:domain_list")
    else:
        form = SchoolDomainForm(instance=domain)

    return render(
        request,
        "super_admin/domains/form.html",
        {"form": form, "domain": domain, "title": "Update Domain"},
    )


@login_required
@user_passes_test(is_superadmin)
def domain_delete(request, pk):
    domain = get_object_or_404(SchoolDomain, pk=pk)
    return render(request, "super_admin/domains/delete.html", {"domain": domain})


@login_required
@user_passes_test(is_superadmin)
def domain_verify(request, pk):
    domain = get_object_or_404(SchoolDomain, pk=pk)
    # Placeholder - implement domain verification logic
    return render(request, "super_admin/domains/verify.html", {"domain": domain})


# Transaction management
@login_required
@user_passes_test(is_superadmin)
def transaction_list(request):
    transactions = PaymentTransaction.objects.all().order_by("-payment_date")
    return render(
        request, "super_admin/transactions/list.html", {"transactions": transactions}
    )


@login_required
@user_passes_test(is_superadmin)
def transaction_detail(request, pk):
    transaction = get_object_or_404(PaymentTransaction, pk=pk)
    return render(
        request, "super_admin/transactions/detail.html", {"transaction": transaction}
    )


# Platform settings
@login_required
@user_passes_test(is_superadmin)
def settings_update(request):
    try:
        settings = SuperAdminSettings.objects.first()
        if not settings:
            settings = SuperAdminSettings()
    except:
        settings = SuperAdminSettings()

    if request.method == "POST":
        form = SuperAdminSettingsForm(request.POST, instance=settings)
        if form.is_valid():
            settings = form.save()
            messages.success(request, "Platform settings updated successfully.")
            return redirect("super_admin:settings_update")
    else:
        form = SuperAdminSettingsForm(instance=settings)

    return render(
        request,
        "super_admin/settings/form.html",
        {"form": form, "settings": settings, "title": "Platform Settings"},
    )


# User management
@login_required
@user_passes_test(is_superadmin)
def user_list(request):
    users = User.objects.filter(is_superadmin=True).order_by("-date_joined")
    return render(request, "super_admin/users/list.html", {"users": users})


@login_required
@user_passes_test(is_superadmin)
def user_create(request):
    if request.method == "POST":
        form = SuperAdminUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(
                request, f"Super admin user '{user.username}' created successfully."
            )
            return redirect("super_admin:user_detail", pk=user.pk)
    else:
        form = SuperAdminUserForm()

    return render(
        request,
        "super_admin/users/form.html",
        {"form": form, "title": "Create Super Admin User"},
    )


@login_required
@user_passes_test(is_superadmin)
def user_detail(request, pk):
    user = get_object_or_404(User, pk=pk, is_superadmin=True)
    return render(request, "super_admin/users/detail.html", {"user": user})


@login_required
@user_passes_test(is_superadmin)
def user_update(request, pk):
    user = get_object_or_404(User, pk=pk, is_superadmin=True)
    if request.method == "POST":
        form = SuperAdminUserForm(request.POST, instance=user)
        if form.is_valid():
            user = form.save()
            messages.success(
                request, f"Super admin user '{user.username}' updated successfully."
            )
            return redirect("super_admin:user_detail", pk=user.pk)
    else:
        form = SuperAdminUserForm(instance=user)

    return render(
        request,
        "super_admin/users/form.html",
        {"form": form, "user": user, "title": "Update Super Admin User"},
    )


@login_required
@user_passes_test(is_superadmin)
def user_delete(request, pk):
    user = get_object_or_404(User, pk=pk, is_superadmin=True)
    return render(request, "super_admin/users/delete.html", {"user": user})


@login_required
@user_passes_test(is_superadmin)
def user_reset_password(request, pk):
    user = get_object_or_404(User, pk=pk, is_superadmin=True)
    if request.method == "POST":
        # Generate a random password
        new_password = "".join(
            random.choices(string.ascii_letters + string.digits, k=12)
        )

        # Set the new password
        user.set_password(new_password)
        user.save()

        messages.success(
            request,
            f"Password for {user.username} has been reset. New password: {new_password}",
        )
        return redirect("super_admin:user_detail", pk=user.pk)

    return redirect("super_admin:user_detail", pk=user.pk)


# School administrator management
@login_required
@user_passes_test(is_superadmin)
def school_admin_create(request, school_id):
    """Create a new school administrator"""
    school = get_object_or_404(SchoolInformation, pk=school_id)

    if request.method == "POST":
        form = SchoolAdminForm(request.POST, school=school)
        if form.is_valid():
            admin = form.save()

            # Send credentials email if requested
            if form.cleaned_data.get("send_credentials"):
                try:
                    send_user_credentials_email(admin, admin.temp_password)
                    messages.success(
                        request,
                        f"Administrator account created and login credentials sent to {admin.email}",
                    )
                except Exception as e:
                    messages.warning(
                        request,
                        f"Administrator created but there was an error sending the email: {str(e)}",
                    )
            else:
                messages.success(
                    request,
                    f"Administrator '{admin.full_name}' created successfully. "
                    f"Password: {admin.temp_password}",
                )

            return redirect("super_admin:school_detail", pk=school.pk)
    else:
        form = SchoolAdminForm(school=school)

    return render(
        request,
        "super_admin/schools/admin_form.html",
        {"form": form, "school": school, "title": "Add School Administrator"},
    )


@login_required
@user_passes_test(is_superadmin)
def school_admin_update(request, pk):
    """Update a school administrator"""
    admin = get_object_or_404(User, pk=pk, role="admin")
    school = admin.school

    if request.method == "POST":
        form = SchoolAdminForm(request.POST, instance=admin, school=school)
        if form.is_valid():
            admin = form.save()

            # Reset password and send credentials if requested
            if form.cleaned_data.get("password1"):
                if form.cleaned_data.get("send_credentials"):
                    try:
                        send_user_credentials_email(admin, admin.temp_password)
                        messages.success(
                            request,
                            f"Administrator updated and new login credentials sent to {admin.email}",
                        )
                    except Exception as e:
                        messages.warning(
                            request,
                            f"Administrator updated but there was an error sending the email: {str(e)}",
                        )
                else:
                    messages.success(
                        request,
                        f"Administrator '{admin.full_name}' updated successfully. "
                        f"New password: {admin.temp_password}",
                    )
            else:
                messages.success(
                    request, f"Administrator '{admin.full_name}' updated successfully."
                )

            return redirect("super_admin:school_detail", pk=school.pk)
    else:
        form = SchoolAdminForm(instance=admin, school=school)

    return render(
        request,
        "super_admin/schools/admin_form.html",
        {
            "form": form,
            "admin": admin,
            "school": school,
            "title": "Update School Administrator",
        },
    )


@login_required
@user_passes_test(is_superadmin)
def school_admin_delete(request, pk):
    """Delete a school administrator"""
    admin = get_object_or_404(User, pk=pk, role="admin")
    school = admin.school

    if request.method == "POST":
        try:
            from django.db import transaction

            with transaction.atomic():
                admin_name = admin.full_name

                # Now delete the admin
                admin.delete()
                messages.success(
                    request, f"Administrator '{admin_name}' deleted successfully."
                )

        except Exception as e:
            messages.error(request, f"Error deleting administrator: {str(e)}")
            return redirect("super_admin:school_detail", pk=school.pk)

        return redirect("super_admin:school_detail", pk=school.pk)

    context = {
        "admin": admin,
        "school": school,
    }

    return render(
        request,
        "super_admin/schools/admin_delete.html",
        context,
    )


@login_required
@user_passes_test(is_superadmin)
def school_admin_reset_password(request, pk):
    """Reset password for a school administrator"""
    admin = get_object_or_404(User, pk=pk, role="admin")

    if request.method == "POST":
        # Generate a random password
        new_password = "".join(
            random.choices(string.ascii_letters + string.digits, k=10)
        )
        admin.set_password(new_password)
        admin.save()

        # Send email with new credentials
        try:
            send_user_credentials_email(admin, new_password)
            messages.success(
                request,
                f"Password for {admin.full_name} has been reset and sent to {admin.email}",
            )
        except:
            messages.success(
                request,
                f"Password for {admin.full_name} has been reset. New password: {new_password}",
            )

        return redirect("super_admin:school_detail", pk=admin.school.pk)

    return redirect("super_admin:school_detail", pk=admin.school.pk)


def plan_duplicate(request, pk):
    """
    Duplicates a subscription plan with a new name.
    """
    # Get the original plan
    original_plan = get_object_or_404(Plan, pk=pk)

    if request.method == "POST":
        form = PlanForm(request.POST)
        if form.is_valid():
            # Create a new plan with the same attributes as the original
            new_plan = form.save(commit=False)
            new_plan.storage_limit = original_plan.storage_limit
            new_plan.bandwidth_limit = original_plan.bandwidth_limit
            new_plan.max_users = original_plan.max_users
            new_plan.api_request_limit = original_plan.api_request_limit
            new_plan.features = original_plan.features
            new_plan.is_active = original_plan.is_active
            new_plan.is_featured = False  # Don't duplicate featured status
            new_plan.save()

            messages.success(
                request,
                f"Plan '{new_plan.name}' has been created based on '{original_plan.name}'.",
            )
            return redirect("super_admin:plan_list")
    else:
        # Prefill the form with the original plan's data, but append "(Copy)" to the name
        initial_data = {
            "name": f"{original_plan.name} (Copy)",
            "price": original_plan.price,
            "billing_cycle": original_plan.billing_cycle,
            "trial_days": original_plan.trial_days,
            "description": original_plan.description,
        }
        form = PlanForm(initial=initial_data)

    context = {
        "form": form,
        "original_plan": original_plan,
        "is_duplicate": True,
    }
    return render(request, "super_admin/plans/form.html", context)


def plan_toggle_feature(request, pk):
    """
    Toggles the featured status of a subscription plan.
    """
    plan = get_object_or_404(Plan, pk=pk)

    # Toggle the featured status
    plan.is_featured = not plan.is_featured
    plan.save()

    if plan.is_featured:
        messages.success(request, f"'{plan.name}' is now a featured plan.")
    else:
        messages.success(request, f"'{plan.name}' is no longer a featured plan.")

    return redirect("super_admin:plan_list")


@login_required
def stop_impersonating(request):
    """Stop impersonating a user and return to original superadmin account"""
    # Check if there's an impersonated_by ID in the session
    impersonated_by_id = request.session.get("impersonated_by")

    if not impersonated_by_id:
        messages.warning(request, "You are not currently impersonating anyone.")
        return redirect("super_admin:dashboard")

    # The actual switching back is handled by the ImpersonationMiddleware
    # This view simply provides a named URL endpoint

    return redirect("/stop-impersonating/")


# Email configuration views
@login_required
@user_passes_test(is_superadmin)
def email_config_list(request):
    """List all email configurations"""
    configs = SystemEmailConfig.objects.all().order_by("-is_active", "-last_updated")

    # Check if there are old credentials to migrate
    has_old_credentials = False
    try:
        has_old_credentials = OAuthCredentialStore.objects.filter(
            service_name="gmail"
        ).exists()
    except:
        pass

    context = {"configs": configs, "has_old_credentials": has_old_credentials}
    return render(request, "super_admin/settings/email_config.html", context)


@login_required
@user_passes_test(is_superadmin)
def email_config_create(request):
    """Create a new email configuration"""
    if request.method == "POST":
        form = SystemEmailConfigForm(request.POST)
        if form.is_valid():
            config = form.save()

            # Test the configuration if requested
            if form.cleaned_data.get("test_connection"):
                success, message = test_email_config(
                    config, form.cleaned_data.get("test_email")
                )
                if success:
                    messages.success(
                        request,
                        f"Email configuration '{config.name}' created successfully and test email sent.",
                    )
                else:
                    messages.warning(
                        request,
                        f"Email configuration created but test failed: {message}",
                    )
            else:
                messages.success(
                    request,
                    f"Email configuration '{config.name}' created successfully.",
                )

            return redirect("super_admin:email_config_list")
    else:
        form = SystemEmailConfigForm()

    return render(
        request, "super_admin/settings/email_config_form.html", {"form": form}
    )


@login_required
@user_passes_test(is_superadmin)
def email_config_edit(request, pk):
    """Edit an email configuration"""
    config = get_object_or_404(SystemEmailConfig, pk=pk)

    if request.method == "POST":
        form = SystemEmailConfigForm(request.POST, instance=config)
        if form.is_valid():
            config = form.save()

            # Test the configuration if requested
            if form.cleaned_data.get("test_connection"):
                success, message = test_email_config(
                    config, form.cleaned_data.get("test_email")
                )
                if success:
                    messages.success(
                        request,
                        f"Email configuration '{config.name}' updated successfully and test email sent.",
                    )
                else:
                    messages.warning(
                        request,
                        f"Email configuration updated but test failed: {message}",
                    )
            else:
                messages.success(
                    request,
                    f"Email configuration '{config.name}' updated successfully.",
                )

            return redirect("super_admin:email_config_list")
    else:
        form = SystemEmailConfigForm(instance=config)

    return render(
        request, "super_admin/settings/email_config_form.html", {"form": form}
    )


@login_required
@user_passes_test(is_superadmin)
def email_config_delete(request, pk):
    """Delete an email configuration"""
    config = get_object_or_404(SystemEmailConfig, pk=pk)

    if config.is_active:
        messages.error(
            request, "Cannot delete an active email configuration. Deactivate it first."
        )
        return redirect("super_admin:email_config_list")

    name = config.name
    config.delete()
    messages.success(request, f"Email configuration '{name}' deleted successfully.")
    return redirect("super_admin:email_config_list")


@login_required
@user_passes_test(is_superadmin)
def email_config_activate(request, pk):
    """Activate an email configuration"""
    config = get_object_or_404(SystemEmailConfig, pk=pk)
    config.is_active = True
    config.save()  # This will deactivate all other configs due to the save method

    messages.success(request, f"Email configuration '{config.name}' is now active.")
    return redirect("super_admin:email_config_list")


@login_required
@user_passes_test(is_superadmin)
def email_config_test(request, pk):
    """Test an email configuration"""
    config = get_object_or_404(SystemEmailConfig, pk=pk)

    if request.method == "POST":
        test_email = request.POST.get("test_email")
        if not test_email:
            messages.error(request, "Test email address is required.")
            return redirect("super_admin:email_config_list")

        success, message = test_email_config(config, test_email)
        if success:
            messages.success(request, f"Test email sent successfully to {test_email}.")
        else:
            messages.error(request, f"Failed to send test email: {message}")

        return redirect("super_admin:email_config_list")

    # If GET, show a form to enter test email
    return render(
        request, "super_admin/settings/email_config_test.html", {"config": config}
    )


@login_required
@user_passes_test(is_superadmin)
def email_config_migrate(request):
    """Migrate existing OAuth credentials to the new system"""
    try:
        # Check if there are old credentials to migrate
        old_creds = OAuthCredentialStore.objects.filter(service_name="gmail").first()
        if not old_creds:
            messages.warning(request, "No legacy OAuth credentials found to migrate.")
            return redirect("super_admin:email_config_list")

        # Create new config from old credentials
        new_config = SystemEmailConfig(
            name=f"Migrated Gmail ({old_creds.email})",
            service_type="oauth",
            oauth_provider="google",
            client_id=old_creds.client_id,
            client_secret=old_creds.client_secret,
            refresh_token=old_creds.refresh_token,
            access_token=old_creds.access_token,
            token_uri=old_creds.token_uri,
            scopes=old_creds.scopes,
            from_email=old_creds.email,
            is_active=True,
        )
        new_config.save()

        messages.success(
            request, f"Successfully migrated OAuth credentials for {old_creds.email}."
        )

        # Optionally, mark the old credentials as migrated or delete them
        # old_creds.delete()  # Uncomment to delete old credentials

    except Exception as e:
        messages.error(request, f"Error migrating credentials: {str(e)}")

    return redirect("super_admin:email_config_list")


def test_email_config(config, test_email):
    """
    Test an email configuration by sending a test email
    Returns tuple: (success, message)
    """
    if not GOOGLE_OAUTH_AVAILABLE and config.service_type == "oauth":
        return (
            False,
            "Google OAuth libraries are not available. Please install required packages.",
        )

    try:
        if config.service_type == "oauth":
            return test_oauth_email(config, test_email)
        elif config.service_type == "smtp":
            return test_smtp_email(config, test_email)
        else:
            return False, f"Unsupported service type: {config.service_type}"

    except Exception as e:
        logger.error(f"Error testing email config: {str(e)}")
        return False, str(e)


def test_oauth_email(config, test_email):
    """Test OAuth email configuration"""
    try:
        # Create credentials object
        credentials = Credentials(
            token=config.access_token,
            refresh_token=config.refresh_token,
            token_uri=config.token_uri,
            client_id=config.client_id,
            client_secret=config.client_secret,
            scopes=config.scopes,
        )

        # Check if token is expired and needs refreshing
        if not credentials.valid:
            try:
                credentials.refresh(Request())
                # Update the stored token
                config.access_token = credentials.token
                config.save()
            except RefreshError as e:
                return False, f"Failed to refresh token: {str(e)}"

        # Build Gmail API service
        gmail_service = build("gmail", "v1", credentials=credentials)

        # Create message
        subject = "Test Email from SchoolApp Platform"
        body = f"""
        <html>
        <body>
            <h2>Test Email</h2>
            <p>This is a test email from the SchoolApp Platform.</p>
            <p>If you received this email, your email configuration is working correctly.</p>
            <p>Configuration: {config.name} ({config.get_service_type_display()})</p>
            <hr>
            <p><small>Sent at {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}</small></p>
        </body>
        </html>
        """

        message = MIMEText(body, "html")
        message["to"] = test_email
        message["subject"] = subject

        # Set the from name if provided
        if config.from_name:
            message["from"] = f"{config.from_name} <{config.from_email}>"
        else:
            message["from"] = config.from_email

        # Encode and send message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        gmail_service.users().messages().send(
            userId="me", body={"raw": raw_message}
        ).execute()

        # Update last used timestamp
        config.last_used = timezone.now()
        config.save()

        return True, "Email sent successfully via Google OAuth2"

    except Exception as e:
        logger.error(f"OAuth email error: {str(e)}")
        return False, f"Error sending OAuth email: {str(e)}"


def test_smtp_email(config, test_email):
    """Test SMTP email configuration"""
    try:
        from django.core.mail import EmailMultiAlternatives
        from django.core.mail.backends.smtp import EmailBackend
        import smtplib

        # Enable SMTP debugging
        smtplib.SMTP_PORT = config.smtp_port

        # Log detailed information
        logger.debug(
            f"Testing SMTP connection to: {config.smtp_host}:{config.smtp_port}"
        )
        logger.debug(f"Using username: {config.smtp_username}")
        logger.debug(
            f"SSL enabled: {config.smtp_use_ssl}, TLS enabled: {config.smtp_use_tls}"
        )

        # Create custom email backend with our settings
        email_backend = EmailBackend(
            host=config.smtp_host,
            port=config.smtp_port,
            username=config.smtp_username,
            password=config.smtp_password,
            use_tls=config.smtp_use_tls,
            use_ssl=config.smtp_use_ssl,
            fail_silently=False,
            timeout=30,  # Increase timeout
        )

        # Create email message
        subject = "Test Email from SchoolApp Platform"
        text_content = "This is a test email from the SchoolApp Platform."
        html_content = f"""
        <html>
        <body>
            <h2>Test Email</h2>
            <p>This is a test email from the SchoolApp Platform.</p>
            <p>If you received this email, your SMTP configuration is working correctly.</p>
            <p>Configuration: {config.name} ({config.get_service_type_display()})</p>
            <hr>
            <p><small>Sent at {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}</small></p>
        </body>
        </html>
        """

        # Set the from name if provided
        if config.from_name:
            from_email = f"{config.from_name} <{config.from_email}>"
        else:
            from_email = config.from_email

        logger.debug(f"Sending email from: {from_email} to: {test_email}")

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=[test_email],
            connection=email_backend,
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()

        # Update last used timestamp
        config.last_used = timezone.now()
        config.save()

        logger.debug("Email sent successfully via SMTP")
        return True, "Email sent successfully via SMTP"

    except Exception as e:
        logger.error(f"SMTP email error: {str(e)}")
        if hasattr(e, "smtp_error"):
            return (
                False,
                f"Error sending SMTP email: {str(e)} (SMTP error: {e.smtp_error})",
            )
        elif hasattr(e, "reason"):
            return False, f"Error sending SMTP email: {str(e)} (Reason: {e.reason})"
        else:
            return False, f"Error sending SMTP email: {str(e)}"
