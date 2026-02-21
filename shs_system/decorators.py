
"""
Decorators for access control in the School Management System.
"""

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def admin_required(view_func):
    """
    Decorator that ensures only administrators can access the view.
    Redirects non-admin users to the appropriate dashboard.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        # Check if user is admin or superadmin
        if request.user.role not in ['admin', 'superadmin']:
            messages.error(request, 'You do not have permission to access this page.')
            if request.user.role == 'teacher':
                return redirect('teacher_dashboard')
            elif request.user.role == 'student':
                return redirect('student_dashboard')
            else:
                return redirect('login')
        
        return view_func(request, *args, **kwargs)
    return wrapper


def teacher_required(view_func):
    """
    Decorator that ensures only teachers and administrators can access the view.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        # Check if user is teacher, admin, or superadmin
        if request.user.role not in ['teacher', 'admin', 'superadmin']:
            messages.error(request, 'You do not have permission to access this page.')
            if request.user.role == 'student':
                return redirect('student_dashboard')
            else:
                return redirect('login')
        
        return view_func(request, *args, **kwargs)
    return wrapper


def school_required(view_func):
    """
    Decorator that ensures the user has an associated school.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        if not request.user.school:
            messages.error(request, 'No school associated with your account.')
            return redirect('login')
        
        return view_func(request, *args, **kwargs)
    return wrapper

