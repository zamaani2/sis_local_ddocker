from django.conf import settings
from django.urls import reverse


def get_school_url(school, path="", use_subdomain=None):
    """
    Generate a URL for a school based on the configured routing method.

    Args:
        school: The SchoolInformation object
        path: Optional path to append to the URL
        use_subdomain: Override the routing method (True for subdomain, False for path)

    Returns:
        str: The URL for the school
    """
    # Support for template filter call
    if isinstance(path, tuple):
        # If called with multiple parameters via the template filter
        if len(path) > 1:
            use_subdomain = path[1]
        path = path[0] if path else ""

    # Determine if we should use subdomain or path-based routing
    if use_subdomain is None:
        # In development, prefer path-based routing
        use_subdomain = (
            settings.MULTI_TENANT_SUBDOMAIN_ROUTING and not settings.DEVELOPMENT_MODE
        )

    # Normalize the path
    if path and not path.startswith("/"):
        path = "/" + path

    # Get the base URL
    if settings.DEBUG:
        protocol = "http"
        domain = "localhost:8000"  # Default for development
    else:
        protocol = "https"
        # Get your production domain from settings
        domain = getattr(settings, "PRODUCTION_DOMAIN", "schoolapp.com")

    # Generate the URL
    if use_subdomain:
        # Use subdomain routing
        return f"{protocol}://{school.slug}.{domain}{path}"
    else:
        # Use path-based routing
        return f"{protocol}://{domain}/{school.slug}{path}"


def school_context(request):
    """
    Add school context to all templates.

    This adds:
    - current_school: The current school (if any)
    - is_super_admin_site: Whether this is the super admin site
    - school_url: Function to generate URLs for schools
    """
    context = {
        "current_school": getattr(request, "school", None),
        "is_super_admin_site": getattr(request, "is_super_admin_site", False),
        "school_url": get_school_url,
    }

    return context
