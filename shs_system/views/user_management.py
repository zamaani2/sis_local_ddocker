from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
import base64
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.views.generic import ListView
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect, get_object_or_404
import random
import string
from django.contrib import messages
from django.urls import reverse, reverse_lazy
from email.mime.text import MIMEText
from django.utils import timezone

from shs_system.models import (
    OAuthCredentialStore,
    SchoolInformation,
    generate_unique_id,
    Student,
    send_user_credentials_email,
)

# Import the SystemEmailConfig from super_admin app
try:
    from super_admin.models import SystemEmailConfig

    SYSTEM_EMAIL_CONFIG_AVAILABLE = True
except ImportError:
    SYSTEM_EMAIL_CONFIG_AVAILABLE = False

# Optional imports for Google OAuth
GOOGLE_OAUTH_AVAILABLE = False
try:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from google.auth.transport.requests import Request
    from google.auth.exceptions import RefreshError
    from social_django.models import UserSocialAuth

    GOOGLE_OAUTH_AVAILABLE = True
except ImportError:
    pass

User = get_user_model()


def is_admin(user):
    """Check if user has admin role"""
    return user.is_authenticated and user.role == "admin"


def generate_random_password(include_symbol=False):
    """
    Generate a password with format 'pas' + 6 random digits + optional symbol
    """
    password = "pas"
    digits = "".join(random.choice(string.digits) for _ in range(6))
    password += digits
    if include_symbol:
        password += random.choice(string.punctuation)
    return password


def get_oauth_credentials():
    """
    Helper function to get OAuth2 credentials for email sending
    Returns tuple: (credentials, error_message)
    """
    if not GOOGLE_OAUTH_AVAILABLE:
        return None, "Google OAuth is not available. Please install required packages."

    try:
        # First try to get credentials from the centralized SystemEmailConfig
        if SYSTEM_EMAIL_CONFIG_AVAILABLE:
            email_config = SystemEmailConfig.get_active_config()

            if email_config and email_config.service_type == "oauth":
                # Create credential object from stored data
                credentials = Credentials(
                    token=email_config.access_token,
                    refresh_token=email_config.refresh_token,
                    token_uri=email_config.token_uri,
                    client_id=email_config.client_id,
                    client_secret=email_config.client_secret,
                    scopes=email_config.scopes,
                )

                # Check if token is expired and needs refreshing
                if not credentials.valid:
                    try:
                        # Refresh the token
                        credentials.refresh(Request())

                        # Update the stored token
                        email_config.access_token = credentials.token
                        email_config.save()
                    except RefreshError as e:
                        return None, f"Failed to refresh token: {str(e)}"

                # Verify scopes for Gmail API
                required_scopes = ["https://www.googleapis.com/auth/gmail.send"]
                if not all(scope in email_config.scopes for scope in required_scopes):
                    return (
                        None,
                        f"Insufficient scopes for Gmail API. Required: {required_scopes}",
                    )

                return credentials, email_config.from_email

        # Fall back to admin user method if no system configuration is available
        admins_with_google = User.objects.filter(role="admin")
        social_user = UserSocialAuth.objects.filter(
            provider="google-oauth2", user__in=admins_with_google
        ).first()

        if not social_user:
            return None, "No admin users with connected Google accounts found"

        access_token = social_user.extra_data.get("access_token")
        refresh_token = social_user.extra_data.get("refresh_token")

        if not access_token:
            return None, "No access token available for connected Google account"

        # Create credentials object
        credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY,
            client_secret=settings.SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET,
            scopes=settings.SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE,
        )

        # Check if token is expired and needs refreshing
        if not credentials.valid:
            try:
                credentials.refresh(Request())
                # Update the stored token in the social auth model
                social_user.extra_data["access_token"] = credentials.token
                social_user.save()
            except RefreshError as e:
                return None, f"Failed to refresh token: {str(e)}"

        # Verify scopes for Gmail API
        required_scopes = ["https://www.googleapis.com/auth/gmail.send"]
        if not all(scope in credentials.scopes for scope in required_scopes):
            return (
                None,
                f"Insufficient scopes for Gmail API. Required: {required_scopes}",
            )

        return credentials, social_user.user.email

    except Exception as e:
        return None, f"Error getting OAuth credentials: {str(e)}"


def send_user_credentials(user, password):
    """
    Send user credentials via email using Google OAuth2 if available,
    falling back to standard Django email if not.

    Returns:
        tuple: (success: bool, message: str)
    """
    # Check if we have a system email configuration
    if SYSTEM_EMAIL_CONFIG_AVAILABLE:
        email_config = SystemEmailConfig.get_active_config()
        if email_config:
            # Use the system email configuration
            try:
                if email_config.service_type == "oauth" and GOOGLE_OAUTH_AVAILABLE:
                    return send_credentials_via_oauth(user, password, email_config)
                elif email_config.service_type == "smtp":
                    return send_credentials_via_smtp(user, password, email_config)
            except Exception as e:
                print(f"Error using system email config: {str(e)}")
                # Fall through to legacy methods

    # Get school info and site URL
    school_info = user.school if user.school else SchoolInformation.get_active()
    school_name = school_info.name if school_info else "School Management System"
    site_url = getattr(settings, "SITE_URL", "http://localhost:8000")

    # Prepare email content
    context = {
        "user": user,
        "password": password,
        "school_name": school_name,
        "login_url": f"{site_url}{reverse_lazy('login')}",
    }

    html_message = render_to_string("emails/user_credentials.html", context)
    plain_message = strip_tags(html_message)
    subject = f"Your {school_name} Account Credentials"

    # Try OAuth2 first if available (legacy method)
    if GOOGLE_OAUTH_AVAILABLE:
        try:
            credentials, sender_email = get_oauth_credentials()
            if not credentials:
                print(
                    f"OAuth unavailable: {sender_email}"
                )  # sender_email contains error message
                # Fall back to standard email
                raise Exception(sender_email)

            # Build Gmail API service
            gmail_service = build("gmail", "v1", credentials=credentials)

            # Create message
            message = MIMEText(html_message, "html")
            message["to"] = user.email
            message["subject"] = subject
            message["from"] = sender_email

            # Encode and send message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
            gmail_service.users().messages().send(
                userId="me", body={"raw": raw_message}
            ).execute()

            return True, "Email sent successfully via Google OAuth2"

        except Exception as e:
            print(f"OAuth email failed, falling back to standard method: {str(e)}")

    # Fall back to standard Django email
    try:
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True, "Email sent successfully via standard email"

    except Exception as e:
        return False, f"Error sending email: {str(e)}"


def send_credentials_via_oauth(user, password, email_config):
    """Send credentials using OAuth2 configuration"""
    if not GOOGLE_OAUTH_AVAILABLE:
        return False, "Google OAuth libraries not available"

    try:
        # Get school info and site URL
        school_info = user.school if user.school else SchoolInformation.get_active()
        school_name = school_info.name if school_info else "School Management System"
        site_url = getattr(settings, "SITE_URL", "http://localhost:8000")

        # Prepare email content
        context = {
            "user": user,
            "password": password,
            "school_name": school_name,
            "login_url": f"{site_url}{reverse_lazy('login')}",
        }

        html_message = render_to_string("emails/user_credentials.html", context)
        subject = f"Your {school_name} Account Credentials"

        # Create credentials object
        credentials = Credentials(
            token=email_config.access_token,
            refresh_token=email_config.refresh_token,
            token_uri=email_config.token_uri,
            client_id=email_config.client_id,
            client_secret=email_config.client_secret,
            scopes=email_config.scopes,
        )

        # Check if token is expired and needs refreshing
        if not credentials.valid:
            credentials.refresh(Request())
            # Update the stored token
            email_config.access_token = credentials.token
            email_config.save()

        # Build Gmail API service
        gmail_service = build("gmail", "v1", credentials=credentials)

        # Create message
        message = MIMEText(html_message, "html")
        message["to"] = user.email
        message["subject"] = subject

        # Set the from name if provided
        if email_config.from_name:
            message["from"] = f"{email_config.from_name} <{email_config.from_email}>"
        else:
            message["from"] = email_config.from_email

        # Encode and send message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        gmail_service.users().messages().send(
            userId="me", body={"raw": raw_message}
        ).execute()

        # Update last used timestamp
        email_config.last_used = timezone.now()
        email_config.save()

        return True, "Email sent successfully via system OAuth configuration"

    except Exception as e:
        return False, f"Error sending email via OAuth: {str(e)}"


def send_credentials_via_smtp(user, password, email_config):
    """Send credentials using SMTP configuration"""
    try:
        from django.core.mail import EmailMultiAlternatives
        from django.core.mail.backends.smtp import EmailBackend

        # Get school info and site URL
        school_info = user.school if user.school else SchoolInformation.get_active()
        school_name = school_info.name if school_info else "School Management System"
        site_url = getattr(settings, "SITE_URL", "http://localhost:8000")

        # Prepare email content
        context = {
            "user": user,
            "password": password,
            "school_name": school_name,
            "login_url": f"{site_url}{reverse_lazy('login')}",
        }

        html_message = render_to_string("emails/user_credentials.html", context)
        plain_message = strip_tags(html_message)
        subject = f"Your {school_name} Account Credentials"

        # Create custom email backend with our settings
        email_backend = EmailBackend(
            host=email_config.smtp_host,
            port=email_config.smtp_port,
            username=email_config.smtp_username,
            password=email_config.smtp_password,
            use_tls=email_config.smtp_use_tls,
            use_ssl=email_config.smtp_use_ssl,
            fail_silently=False,
        )

        # Set the from name if provided
        if email_config.from_name:
            from_email = f"{email_config.from_name} <{email_config.from_email}>"
        else:
            from_email = email_config.from_email

        msg = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=from_email,
            to=[user.email],
            connection=email_backend,
        )
        msg.attach_alternative(html_message, "text/html")
        msg.send()

        # Update last used timestamp
        email_config.last_used = timezone.now()
        email_config.save()

        return True, "Email sent successfully via SMTP"

    except Exception as e:
        return False, f"Error sending email via SMTP: {str(e)}"


@login_required
@user_passes_test(is_admin)
def user_management(request):
    """View for displaying user list and handling CRUD operations"""
    # Get the current user's school
    school = request.user.school

    # Filter users by the current user's school
    users = User.objects.filter(school=school).order_by("-date_joined")

    # Check if the current user has connected their Google account
    google_connected = False
    system_email_configured = False

    if GOOGLE_OAUTH_AVAILABLE:
        try:
            google_connected = UserSocialAuth.objects.filter(
                user=request.user, provider="google-oauth2"
            ).exists()
        except Exception as e:
            print(f"Error checking Google connection: {str(e)}")

    # Check if system email is configured
    if SYSTEM_EMAIL_CONFIG_AVAILABLE:
        system_email_configured = SystemEmailConfig.objects.filter(
            is_active=True
        ).exists()

    context = {
        "users": users,
        "roles": User.ROLES,
        "google_connected": google_connected,
        "system_email_configured": system_email_configured,
        "school": school,
    }
    return render(request, "users/user_management.html", context)


@login_required
@user_passes_test(is_admin)
def create_user(request):
    """API endpoint for creating a new user"""
    if request.method == "POST":
        try:
            username = request.POST.get("username")
            email = request.POST.get("email")
            role = request.POST.get("role")
            full_name = request.POST.get("full_name")

            # Generate random password
            password = generate_random_password()

            # Create user and associate with the current user's school
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                role=role,
                full_name=full_name,
                school=request.user.school,  # Associate with current user's school
            )

            # Send credentials via email
            success, message = send_user_credentials(user, password)

            # Prepare response data
            response_data = {
                "status": "success",
                "message": "User created successfully.",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": user.get_role_display(),
                    "full_name": user.full_name,
                },
            }

            # Add email status to message
            if success:
                response_data["message"] += f" {message}"
            else:
                response_data["message"] += f" Warning: {message}"

            return JsonResponse(response_data)

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
    return JsonResponse(
        {"status": "error", "message": "Invalid request method"}, status=405
    )


@login_required
@user_passes_test(is_admin)
def update_user(request, user_id):
    """API endpoint for updating a user"""
    if request.method == "POST":
        try:
            # Ensure the user being updated belongs to the current user's school
            user = User.objects.get(id=user_id, school=request.user.school)

            user.username = request.POST.get("username", user.username)
            user.email = request.POST.get("email", user.email)
            user.role = request.POST.get("role", user.role)
            user.full_name = request.POST.get("full_name", user.full_name)
            user.save()

            return JsonResponse(
                {
                    "status": "success",
                    "message": "User updated successfully",
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "role": user.get_role_display(),
                        "full_name": user.full_name,
                    },
                }
            )
        except User.DoesNotExist:
            return JsonResponse(
                {
                    "status": "error",
                    "message": "User not found or you don't have permission to update this user",
                },
                status=404,
            )
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
    return JsonResponse(
        {"status": "error", "message": "Invalid request method"}, status=405
    )


@login_required
@user_passes_test(is_admin)
def delete_user(request, user_id):
    """API endpoint for deleting a user"""
    if request.method == "POST":
        try:
            # Ensure the user being deleted belongs to the current user's school
            user = User.objects.get(id=user_id, school=request.user.school)
            user.delete()
            return JsonResponse(
                {"status": "success", "message": "User deleted successfully"}
            )
        except User.DoesNotExist:
            return JsonResponse(
                {
                    "status": "error",
                    "message": "User not found or you don't have permission to delete this user",
                },
                status=404,
            )
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)
    return JsonResponse(
        {"status": "error", "message": "Invalid request method"}, status=405
    )


@login_required
@user_passes_test(is_admin)
@require_POST
def resend_credentials(request, user_id):
    """Resend user credentials via Google OAuth2"""
    try:
        # Ensure the user belongs to the current user's school
        user = User.objects.get(id=user_id, school=request.user.school)

        # Generate new secure password
        new_password = generate_random_password()

        # Update user's password
        user.set_password(new_password)
        user.save()

        # Send new credentials via email
        success, message = send_user_credentials(user, new_password)

        if success:
            return JsonResponse(
                {
                    "status": "success",
                    "message": f"New credentials have been sent to {user.email}",
                }
            )
        else:
            return JsonResponse(
                {
                    "status": "error",
                    "message": f"Failed to send credentials: {message}",
                },
                status=500,
            )

    except User.DoesNotExist:
        return JsonResponse(
            {
                "status": "error",
                "message": "User not found or you don't have permission to reset credentials for this user",
            },
            status=404,
        )
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@login_required
@user_passes_test(is_admin)

@require_POST
def reset_password_default(request, user_id):
    """Reset user password to default password (0000) without sending email"""
    try:
        # Ensure the user belongs to the current user's school
        user = User.objects.get(id=user_id, school=request.user.school)

        # Set default password
        default_password = "0000"
        user.set_password(default_password)
        user.save()

        return JsonResponse(
            {
                "status": "success",
                "message": f"Password for {user.full_name} has been reset to default password (0000). User can now login with username: {user.username} and password: 0000",
            }
        )

    except User.DoesNotExist:
        return JsonResponse(
            {
                "status": "error",
                "message": "User not found or you don't have permission to reset password for this user",
            },
            status=404,
        )
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@login_required
@user_passes_test(is_admin)
@require_POST
def bulk_reset_password_default(request):
    """Bulk reset multiple users' passwords to default password (0000) without sending emails"""
    try:
        # Get user IDs from request
        user_ids = request.POST.getlist('user_ids[]')
        
        if not user_ids:
            return JsonResponse(
                {
                    "status": "error",
                    "message": "No users selected for password reset",
                },
                status=400,
            )

        # Ensure all users belong to the current user's school
        users = User.objects.filter(
            id__in=user_ids, 
            school=request.user.school
        )
        
        if not users.exists():
            return JsonResponse(
                {
                    "status": "error",
                    "message": "No valid users found for password reset",
                },
                status=404,
            )

        # Set default password for all users
        default_password = "0000"
        reset_count = 0
        reset_users = []
        
        for user in users:
            user.set_password(default_password)
            user.save()
            reset_count += 1
            reset_users.append({
                'id': user.id,
                'username': user.username,
                'full_name': user.full_name,
                'email': user.email
            })

        return JsonResponse(
            {
                "status": "success",
                "message": f"Successfully reset passwords for {reset_count} user(s) to default password (0000). Users can now login with their username and password: 0000",
                "reset_count": reset_count,
                "reset_users": reset_users,
            }
        )

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@login_required
@user_passes_test(is_admin)

def configure_service_account(request):
    """View for configuring OAuth2 service account for system emails"""
    if request.method == "POST":
        try:
            client_id = request.POST.get("client_id")
            client_secret = request.POST.get("client_secret")
            refresh_token = request.POST.get("refresh_token")
            email = request.POST.get("email")
            scopes = ["https://www.googleapis.com/auth/gmail.send"]

            print(f"Attempting to save service account with email: {email}")

            # Create or update the service account
            try:
                cred_store, created = OAuthCredentialStore.objects.update_or_create(
                    service_name="gmail",
                    defaults={
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "refresh_token": refresh_token,
                        "email": email,
                        "scopes": scopes,
                        "is_active": True,
                    },
                )
                print(
                    f"Service account {'created' if created else 'updated'} with ID: {cred_store.id}"
                )
            except Exception as db_error:
                print(f"Database error when saving service account: {str(db_error)}")
                messages.error(request, f"Database error: {str(db_error)}")
                return render(request, "users/configure_service_account.html")

            # Test the credentials
            try:
                if not GOOGLE_OAUTH_AVAILABLE:
                    print("Google OAuth libraries not available")
                    messages.warning(
                        request,
                        "Service account saved, but couldn't validate credentials because Google OAuth libraries are not installed.",
                    )
                    return redirect("user_management")

                credentials = Credentials(
                    token=None,  # Will be obtained during refresh
                    refresh_token=refresh_token,
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=client_id,
                    client_secret=client_secret,
                    scopes=scopes,
                )

                # Force refresh to validate credentials
                credentials.refresh(Request())
                cred_store.access_token = credentials.token
                cred_store.save()

                print(f"Service account validated and access token saved")

                messages.success(request, "Service account configured successfully!")

                # Verify it's in the database before redirecting
                verification = OAuthCredentialStore.objects.filter(
                    service_name="gmail"
                ).exists()
                print(f"Service account verification: {verification}")

                return redirect("user_management")

            except Exception as e:
                print(f"Error validating credentials: {str(e)}")
                # Don't delete on validation failure - keep the record but warn the user
                messages.warning(
                    request,
                    f"Service account saved but we couldn't validate the credentials: {str(e)}",
                )
                return redirect("user_management")

        except Exception as e:
            print(f"General error in configure_service_account: {str(e)}")
            messages.error(request, f"Error configuring service account: {str(e)}")

    # Add current user's school to context
    context = {"school": request.user.school}
    return render(request, "users/configure_service_account.html", context)
