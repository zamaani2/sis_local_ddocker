"""
URL configuration for SchoolApp project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.shortcuts import render, redirect
from django.urls import path, include, get_resolver
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse, HttpResponseRedirect
import logging
from shs_system.views.security import locked_out, ratelimited_error
from shs_system.views.health import health_check

from .views import landing_page_view

logger = logging.getLogger("django.request")

# Set the admin site namespace
admin.site.site_header = "SchoolApp Admin"
admin.site.site_title = "SchoolApp Admin Portal"
admin.site.index_title = "Welcome to SchoolApp Admin Portal"


# A simple view for testing subdomain routing
def debug_view(request):
    # Return information about the request, including host and school
    info = [
        f"Host: {request.get_host()}",
        f"Path: {request.path}",
        f"School: {getattr(request, 'school', None)}",
        f"Is Super Admin Site: {getattr(request, 'is_super_admin_site', False)}",
    ]

    if hasattr(request, "school") and request.school:
        info.append(f"School Name: {request.school.name}")
        info.append(f"School Slug: {request.school.slug}")

    # Add authentication information
    info.append(f"User Authenticated: {request.user.is_authenticated}")
    if request.user.is_authenticated:
        info.append(f"Username: {request.user.username}")
        info.append(f"User Role: {request.user.role}")
        info.append(f"Is Superadmin: {getattr(request.user, 'is_superadmin', False)}")
        info.append(f"User School: {getattr(request.user, 'school', None)}")
        if hasattr(request.user, "school") and request.user.school:
            info.append(f"User School Name: {request.user.school.name}")

    # Add session information
    info.append(f"Session Keys: {list(request.session.keys())}")

    # Add request META information
    info.append(f"HTTP_HOST: {request.META.get('HTTP_HOST', 'Not available')}")
    info.append(f"HTTP_REFERER: {request.META.get('HTTP_REFERER', 'Not available')}")

    # Add media URL information
    info.append(f"MEDIA_URL: {settings.MEDIA_URL}")
    info.append(f"MEDIA_ROOT: {settings.MEDIA_ROOT}")

    return HttpResponse("<br>".join(info))


# View to list all available URL patterns
def url_list_view(request):
    resolver = get_resolver()
    url_patterns = {}

    def extract_patterns(resolver, namespace=None):
        for pattern in resolver.url_patterns:
            if hasattr(pattern, "url_patterns"):
                # This pattern includes other patterns (like include)
                pattern_namespace = namespace
                if hasattr(pattern, "namespace") and pattern.namespace:
                    if namespace:
                        pattern_namespace = f"{namespace}:{pattern.namespace}"
                    else:
                        pattern_namespace = pattern.namespace
                extract_patterns(pattern, pattern_namespace)
            else:
                # This is a URL pattern
                url_name = getattr(pattern, "name", "")
                if url_name:
                    if namespace:
                        full_name = f"{namespace}:{url_name}"
                    else:
                        full_name = url_name

                    url_patterns[full_name] = {
                        "pattern": str(pattern.pattern),
                        "name": url_name,
                        "namespace": namespace or "",
                        "view": str(
                            pattern.callback.__name__
                            if callable(pattern.callback)
                            else pattern.callback
                        ),
                    }

    extract_patterns(resolver)

    # Generate HTML output
    lines = ["<h1>Available URL Patterns</h1>"]
    lines.append(
        "<style>table { border-collapse: collapse; width: 100%; } th, td { border: 1px solid #ddd; padding: 8px; text-align: left; } tr:nth-child(even) { background-color: #f2f2f2; } th { background-color: #4CAF50; color: white; }</style>"
    )
    lines.append("<table>")
    lines.append(
        "<tr><th>Full Name</th><th>Pattern</th><th>Name</th><th>Namespace</th><th>View</th></tr>"
    )

    for name, info in sorted(url_patterns.items()):
        lines.append(
            f'<tr><td>{name}</td><td>{info["pattern"]}</td><td>{info["name"]}</td><td>{info["namespace"]}</td><td>{info["view"]}</td></tr>'
        )

    lines.append("</table>")

    return HttpResponse("".join(lines))


urlpatterns = [
    # Health check endpoint for Docker
    path("health/", health_check, name="health_check"),
    # Standard Django admin URL with automatic namespace
    path("admin/", admin.site.urls),
    # Debug views for testing
    path("debug/", debug_view, name="debug_view"),
    path("debug/routing/", debug_view, name="debug_routing"),  # Alias for easier access
    path("debug/urls/", url_list_view, name="url_list_view"),  # URL pattern debugging
    # Root URL handling - shows landing page or redirects for school subdomains
    path("", landing_page_view, name="landing_page"),
    # Add home URL alias for compatibility
    path("home/", landing_page_view, name="home"),
    # School app URLs
    # Important: Include the shs_system URLs at the root level to catch all dashboard paths
    path("", include("shs_system.urls")),
    # Include the /school/ prefix as an alternative route to the login page
    path("school/", include("shs_system.urls")),
    # Super admin URLs
    path("super-admin/", include("super_admin.urls", namespace="super_admin")),
    # Social auth URLs
    path("social-auth/", include("social_django.urls", namespace="social")),
    path("locked-out/", locked_out, name="locked_out"),
    path("rate-limited/", ratelimited_error, name="rate_limited"),
]


# Serve media files during development
if settings.DEBUG:
    print(f"Adding media URL patterns: {settings.MEDIA_URL} -> {settings.MEDIA_ROOT}")
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

