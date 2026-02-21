from django.shortcuts import render


def locked_out(request):
    """
    View to display when a user is locked out due to too many failed login attempts.
    This view is used by django-axes.
    """
    return render(request, "account/lockout.html")


def ratelimited_error(request, exception=None):
    """
    View to display when a user hits a rate limit.
    This view is used by django-ratelimit.
    """
    return render(request, "account/ratelimited.html", status=429)
