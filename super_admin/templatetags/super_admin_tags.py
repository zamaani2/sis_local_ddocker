
from django import template
from django.conf import settings
import os

register = template.Library()


@register.filter
def basename(value):
    """Get the basename of a file path"""
    return os.path.basename(value)


@register.simple_tag
def school_url(school, path="", use_subdomain=None):
    """
    Generate a URL for a school based on the configured routing method.

    Usage:
    {% school_url school %}
    {% school_url school '/dashboard/' %}
    {% school_url school '/admin/' True %}
    """
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

