from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
import logging

logger = logging.getLogger("django.request")


def landing_page_view(request):
    """Main landing page view that shows options to log in as different user types."""
    # If accessed via a school subdomain, redirect appropriately
    if hasattr(request, "school") and request.school:
        logger.info(f"School subdomain detected: {request.school.name}")

        # If user is authenticated, direct them to the appropriate dashboard
        if request.user.is_authenticated:
            # Check if user is a superadmin
            if request.user.is_superadmin:
                return HttpResponseRedirect("/super-admin/")

            # Check if user belongs to this school
            if request.user.school == request.school:
                # Redirect based on user role
                if request.user.role == "admin":
                    return HttpResponseRedirect("/dashboard/admin/")
                elif request.user.role == "teacher":
                    return HttpResponseRedirect("/dashboard/teacher/")
                elif request.user.role == "student":
                    return HttpResponseRedirect("/dashboard/student/")
                else:
                    return HttpResponseRedirect("/dashboard/")

        # If not authenticated or not belonging to this school, redirect to login
        return HttpResponseRedirect("/")

    # For the main domain, show our custom landing page
    logger.info("Main domain accessed, showing landing page")
    return render(request, "landing.html")
