from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required


@login_required
@require_POST
def extend_session(request):
    """
    View to extend the current user's session.
    Called via AJAX when a user clicks to extend their session.
    """
    # Set the session to expire according to settings.SESSION_COOKIE_AGE
    request.session.set_expiry(None)  # This will use SESSION_COOKIE_AGE from settings

    return JsonResponse({"success": True, "message": "Session extended successfully"})
