def sweet_alert(request):
    """
    Context processor to handle SweetAlert notifications and clean up session
    """
    sweet_alert = request.session.pop("sweet_alert", None)
    return {"sweet_alert": sweet_alert}


def session_expiry(request):
    """
    Context processor to provide session expiry time to templates
    """
    from django.conf import settings

    if request.user.is_authenticated:
        # Get session expiry time in seconds
        session_cookie_age = request.session.get_expiry_age()
        return {
            "session_expiry_seconds": session_cookie_age,
            "session_cookie_age": settings.SESSION_COOKIE_AGE,
        }
    return {
        "session_expiry_seconds": 0,
        "session_cookie_age": settings.SESSION_COOKIE_AGE,
    }


def school_context(request):
    """
    Context processor to add the current school to all templates.
    This is essential for multi-tenancy support across the application.
    """
    if not request.user.is_authenticated:
        return {"current_school": None}

    # Get the user's school
    school = getattr(request.user, "school", None)

    # For superadmins who don't have a specific school assigned
    is_superadmin = getattr(request.user, "is_superadmin", False)

    # If there's a school in the session (for superadmins switching between schools)
    school_id = request.session.get("selected_school_id")
    if is_superadmin and school_id:
        from .models import SchoolInformation

        try:
            school = SchoolInformation.objects.get(id=school_id)
        except SchoolInformation.DoesNotExist:
            pass

    return {
        "current_school": school,
        "is_superadmin": is_superadmin,
    }


def current_academic_context(request):
    """
    Context processor to provide current academic year and term information
    to all templates. This is essential for academic year and term management.
    """
    if not request.user.is_authenticated:
        return {
            "current_academic_year": None,
            "current_term": None,
        }

    try:
        # Get the user's school for multi-tenancy
        school = request.user.school
        if not school:
            return {
                "current_academic_year": None,
                "current_term": None,
            }

        from .models import SchoolInformation

        # Get school information with current academic year and term
        school_info = SchoolInformation.objects.filter(id=school.id).first()

        if school_info:
            return {
                "current_academic_year": school_info.current_academic_year,
                "current_term": school_info.current_term,
            }
        else:
            return {
                "current_academic_year": None,
                "current_term": None,
            }
    except Exception as e:
        # Log error but don't break the page
        print(f"Error getting current academic context: {str(e)}")
        return {
            "current_academic_year": None,
            "current_term": None,
        }


def teacher_monitoring_summary(request):
    """
    Context processor to provide teacher activity monitoring summary data
    for the admin dashboard and other admin pages.
    """
    if not request.user.is_authenticated or request.user.role != "admin":
        return {}

    # Don't calculate on every request, which could be expensive
    # Only calculate on the admin dashboard

    if "admin-dashboard" in request.path or "dashboard/admin" in request.path or "admin_dashboard" in request.path:

        from .utils import get_teacher_monitoring_data

        try:
            # Get the user's school for multi-tenancy
            school = request.user.school

            # Get simplified monitoring data (just for summary), filtered by school
            monitoring_data = get_teacher_monitoring_data(school=school)

            return {
                "teacher_monitoring_summary": {
                    "total_teachers": monitoring_data["summary"]["total_teachers"],
                    "scores_completed": monitoring_data["summary"]["scores_completed"],
                    "remarks_completed": monitoring_data["summary"][
                        "remarks_completed"
                    ],
                    "attendance_completed": monitoring_data["summary"][
                        "attendance_completed"
                    ],
                    "scores_completion_percent": round(
                        (
                            monitoring_data["summary"]["scores_completed"]
                            / max(monitoring_data["summary"]["total_teachers"], 1)
                        )
                        * 100
                    ),
                    "remarks_completion_percent": round(
                        (
                            monitoring_data["summary"]["remarks_completed"]
                            / max(monitoring_data["summary"]["total_teachers"], 1)
                        )
                        * 100
                    ),
                    "attendance_completion_percent": round(
                        (
                            monitoring_data["summary"]["attendance_completed"]
                            / max(monitoring_data["summary"]["total_teachers"], 1)
                        )
                        * 100
                    ),
                }
            }
        except Exception as e:
            # Log error but don't break the page
            print(f"Error calculating teacher monitoring summary: {str(e)}")
            return {}

    return {}
