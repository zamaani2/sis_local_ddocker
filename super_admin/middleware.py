from django.conf import settings
from django.http import Http404
from django.urls import resolve, Resolver404
from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin
from shs_system.models import SchoolInformation, User
from django.db.models import Q
import logging
from django.contrib.auth import login
from django.contrib import messages

logger = logging.getLogger("super_admin.middleware")


class SchoolMiddleware(MiddlewareMixin):
    """
    Middleware to handle multi-tenancy based on subdomain or path prefix.

    This middleware:
    1. Extracts the school slug from the URL (either subdomain or path)
    2. Loads the corresponding school
    3. Makes the school available in the request object
    4. Handles permissions based on the school
    """

    def process_request(self, request):
        """Process each request to identify the school"""
        # Skip for admin, static, and media URLs
        if (
            request.path.startswith("/admin/")
            or request.path.startswith("/static/")
            or request.path.startswith("/media/")
        ):
            return None

        # Get the hostname
        host = request.get_host().split(":")[0]

        # Initialize school to None
        request.school = None
        request.is_super_admin_site = False
        school_found = False

        # Log detailed request info
        logger.debug(f"Processing request for host: {host}, path: {request.path}")

        # Check if we're using subdomain routing
        if settings.MULTI_TENANT_SUBDOMAIN_ROUTING:
            # Extract subdomain
            parts = host.split(".")
            logger.debug(f"Host parts: {parts}")

            # For development with .localhost domains
            if ".localhost" in host:
                # This is a subdomain in development like "school1.localhost"
                subdomain = parts[0]
                logger.debug(f"Detected subdomain: {subdomain}")

                # Check if this is the super admin subdomain
                if subdomain == settings.SUPER_ADMIN_SUBDOMAIN:
                    # This is the super admin site
                    logger.debug("This is the super admin site")
                    request.is_super_admin_site = True
                    return None

                # Try to find the school by slug
                try:
                    # Replace dashes with spaces and check if it matches a school name
                    potential_name = subdomain.replace("-", " ")
                    logger.debug(
                        f"Looking for school with slug or name: {potential_name}"
                    )

                    # Try to find by slug first, then by name
                    school = SchoolInformation.objects.get(
                        Q(slug=subdomain) | Q(name__iexact=potential_name),
                        is_active=True,
                    )

                    logger.debug(f"Found school: {school.name} (slug: {school.slug})")
                    request.school = school
                    request.is_super_admin_site = False
                    school_found = True

                    # Special handling for /school/ paths in subdomain context
                    if request.path.startswith("/school/"):
                        logger.debug(
                            f"School subdomain with /school/ path: {request.path}"
                        )
                        # Keep the school context but don't modify the path
                        # This ensures login and other school-specific views work correctly
                        return None

                except SchoolInformation.DoesNotExist:
                    logger.debug(f"No school found for subdomain: {subdomain}")
                    if not settings.DEVELOPMENT_MODE and settings.STRICT_TENANT_ROUTING:
                        raise Http404("School not found")

        # Check if we're using path-based routing and no school was found by subdomain
        if settings.MULTI_TENANT_PATH_ROUTING and not school_found:
            # Extract the first part of the path
            path_parts = request.path.strip("/").split("/")
            if path_parts and path_parts[0]:
                path_prefix = path_parts[0]
                logger.debug(f"Path prefix: {path_prefix}")

                # Skip for the main apps
                if path_prefix in ["school", "super-admin", "admin", "social-auth"]:
                    logger.debug(
                        f"Skipping path-based routing for reserved prefix: {path_prefix}"
                    )
                    return None

                # Check if this is the super admin path
                if path_prefix == settings.SUPER_ADMIN_PATH:
                    logger.debug("This is the super admin path")
                    request.is_super_admin_site = True
                    return None

                # Try to find the school by path prefix
                try:
                    # First try by slug
                    school = SchoolInformation.objects.get(
                        Q(slug=path_prefix) | Q(short_name__iexact=path_prefix),
                        is_active=True,
                    )
                    logger.debug(f"Found school by path: {school.name}")
                    request.school = school
                    request.is_super_admin_site = False

                    # Modify the path for this request
                    request.path_info = "/" + "/".join(path_parts[1:])
                    if not request.path_info:
                        request.path_info = "/"
                    logger.debug(f"Modified path_info: {request.path_info}")

                    return None
                except SchoolInformation.DoesNotExist:
                    logger.debug(f"No school found for path prefix: {path_prefix}")
                    if not settings.DEVELOPMENT_MODE and settings.STRICT_TENANT_ROUTING:
                        raise Http404("School not found")

        # Default to the main site (no specific school)
        logger.debug("Default routing: main site (no specific school)")
        return None

    def process_view(self, request, view_func, view_args, view_kwargs):
        """Process the view to enforce permissions"""
        # Skip for admin, static, and media URLs
        if (
            request.path.startswith("/admin/")
            or request.path.startswith("/static/")
            or request.path.startswith("/media/")
        ):
            return None

        # If this is the super admin site, ensure user has super admin permissions
        if getattr(request, "is_super_admin_site", False):
            logger.debug("Checking permissions for super admin site")
            if not request.user.is_authenticated:
                return redirect(settings.LOGIN_URL)

            if not request.user.is_superadmin:
                return redirect(settings.LOGIN_URL)

        # If we have a school context, ensure user has access to this school
        if getattr(request, "school", None) and request.user.is_authenticated:
            logger.debug(f"Checking permissions for school: {request.school.name}")
            # Super admins can access any school
            if request.user.is_superadmin:
                return None

            # School admins, teachers, and students must belong to this school
            if request.user.school != request.school:
                logger.debug(
                    f"User {request.user.username} belongs to school {request.user.school}, not {request.school.name}"
                )
                return redirect(settings.LOGIN_URL)

        return None


class ImpersonationMiddleware(MiddlewareMixin):
    """
    Middleware to handle admin impersonation functionality.

    This middleware:
    1. Detects requests to stop impersonating a user
    2. Restores the original superadmin user
    3. Redirects to the appropriate destination
    """

    def process_request(self, request):
        """Process each request to check for impersonation actions"""
        # Check if this is a request to stop impersonating
        if request.path == "/stop-impersonating/" and request.user.is_authenticated:
            # Check if there's an impersonated_by ID in the session
            impersonated_by_id = request.session.get("impersonated_by")
            impersonated_by_role = request.session.get("impersonated_by_role")

            if impersonated_by_id:
                try:
                    # Get the original superadmin user
                    original_user = User.objects.get(id=impersonated_by_id)

                    # Restore original is_superadmin state if it was stored
                    original_is_superadmin = request.session.get(
                        "original_is_superadmin", False
                    )
                    if original_is_superadmin:
                        original_user.is_superadmin = True

                    # Log in as the original user
                    login(request, original_user)

                    # Clean up session
                    if "impersonated_by" in request.session:
                        del request.session["impersonated_by"]
                    if "impersonated_by_role" in request.session:
                        del request.session["impersonated_by_role"]
                    if "original_is_superadmin" in request.session:
                        del request.session["original_is_superadmin"]

                    # Add success message
                    messages.success(
                        request, "You are no longer impersonating another user."
                    )

                    # Redirect to appropriate page based on the original role
                    if impersonated_by_role == "superadmin":
                        return redirect("/super-admin/dashboard/")
                    else:
                        return redirect("/dashboard/")

                except User.DoesNotExist:
                    # If the original user can't be found, just redirect to login
                    messages.error(
                        request, "Original user not found. Please log in again."
                    )
                    return redirect(settings.LOGIN_URL)

        # Add impersonation information to the request
        request.is_impersonating = "impersonated_by" in request.session

        return None
