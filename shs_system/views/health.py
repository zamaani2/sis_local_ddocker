from django.http import JsonResponse
from django.db import connection
from django.conf import settings


def health_check(request):
    """Simple health check endpoint for Docker"""
    try:
        # Test database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")

        return JsonResponse(
            {"status": "healthy", "database": "connected", "debug": settings.DEBUG}
        )
    except Exception as e:
        return JsonResponse({"status": "unhealthy", "error": str(e)}, status=500)

