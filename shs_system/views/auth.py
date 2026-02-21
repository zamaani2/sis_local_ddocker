# Django imports
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.urls import reverse
import logging
import traceback

logger = logging.getLogger("shs_system.auth")


def is_admin(user):
    return user.is_authenticated and user.role == "admin"


def login_view(request):
    # Enhanced logging for debugging routing issues
    logger.debug(
        f"Login view accessed. Host: {request.get_host()}, Path: {request.path}"
    )
    logger.debug(f"School context: {getattr(request, 'school', None)}")
    if hasattr(request, "school") and request.school:
        logger.debug(f"School name: {request.school.name}, slug: {request.school.slug}")

    # Get the next URL if provided
    next_url = request.GET.get("next", None)
    logger.debug(f"Next URL parameter: {next_url}")

    if request.method == "POST":
        try:
            username = request.POST.get("username")
            password = request.POST.get("password")
            logger.debug(f"Login attempt for username: {username}")

            # Validate input
            if not username or not password:
                logger.warning("Username or password missing in POST data")
                messages.error(request, "Username and password are required.")
                return render(request, "login.html")

            # Authenticate user
            logger.debug(f"Attempting to authenticate user: {username}")
            user = authenticate(request, username=username, password=password)

            if user is not None:
                logger.debug(f"User {username} authenticated successfully")
                logger.debug(
                    f"User role: {user.role}, School: {getattr(user, 'school', None)}"
                )

                # Log before login
                logger.debug(f"Before login - request.user: {request.user}")

                # Perform login
                login(request, user)

                # Log after login
                logger.debug(f"After login - request.user: {request.user}")
                logger.debug(f"Authentication successful for user: {username}")

                # If there's a next URL, prioritize it
                if next_url:
                    logger.debug(f"Redirecting to next URL: {next_url}")
                    return redirect(next_url)

                # Handle super admin users first
                if user.is_superadmin:
                    logger.debug("Redirecting superadmin to super admin dashboard")
                    # Use the correct URL for super admin dashboard
                    return redirect("/super-admin/")

                # Now handle regular users based on role
                school = getattr(request, "school", None)

                # Determine the appropriate dashboard URL based on user role
                if user.role == "admin":
                    dashboard_url = "/dashboard/admin/"
                    logger.debug(f"Admin user, dashboard URL: {dashboard_url}")
                elif user.role == "teacher":
                    dashboard_url = "/dashboard/teacher/"
                    logger.debug(f"Teacher user, dashboard URL: {dashboard_url}")
                elif user.role == "student":
                    dashboard_url = "/dashboard/student/"
                    logger.debug(f"Student user, dashboard URL: {dashboard_url}")
                else:
                    # Default fallback
                    dashboard_url = "/dashboard/"
                    logger.debug(
                        f"Unknown role, using default dashboard: {dashboard_url}"
                    )

                # For school context, ensure user belongs to this school
                if school:
                    if user.school == school or user.is_superadmin:
                        logger.debug(
                            f"User belongs to school {school.name}, redirecting to {dashboard_url}"
                        )
                        return redirect(dashboard_url)
                    else:
                        # User doesn't belong to this school
                        logger.warning(
                            f"User {user.username} tried to access school {school.name} but belongs to {user.school}"
                        )
                        messages.error(
                            request, "You don't have permission to access this school."
                        )
                        logout(request)
                        return redirect("login")

                # No school context, just redirect to the dashboard
                logger.debug(f"No school context, redirecting to {dashboard_url}")
                return redirect(dashboard_url)
            else:
                logger.warning(f"Failed login attempt for username: {username}")
                messages.error(request, "Invalid username or password.")
        except Exception as e:
            logger.error(f"Exception during login: {str(e)}")
            logger.error(traceback.format_exc())
            messages.error(request, f"Login error: {str(e)}")

    return render(request, "login.html", {"next": next_url})


def logout_view(request):
    logout(request)

    return redirect("landing_page")

