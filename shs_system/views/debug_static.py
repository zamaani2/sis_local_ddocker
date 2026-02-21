"""
Debug view to check static file serving
"""
from django.http import JsonResponse
from django.conf import settings
import os

def debug_static_files(request):
    """Debug view to check static file configuration"""
    static_info = {
        'STATIC_URL': settings.STATIC_URL,
        'STATIC_ROOT': settings.STATIC_ROOT,
        'STATICFILES_DIRS': list(settings.STATICFILES_DIRS) if hasattr(settings, 'STATICFILES_DIRS') else [],
        'STATICFILES_STORAGE': str(settings.STORAGES.get('staticfiles', {}).get('BACKEND', 'Not set')),
        'DEBUG': settings.DEBUG,
    }
    
    # Check if static files exist
    static_root = settings.STATIC_ROOT
    if os.path.exists(static_root):
        static_info['static_root_exists'] = True
        static_info['static_files_count'] = len([f for f in os.listdir(static_root) if os.path.isfile(os.path.join(static_root, f))])
    else:
        static_info['static_root_exists'] = False
    
    return JsonResponse(static_info)
