from django.shortcuts import redirect
from django.urls import reverse
from .models import User


def save_profile(backend, user, response, *args, **kwargs):
    """
    Custom pipeline function to save additional profile data from social auth
    """
    if backend.name == "google-oauth2":
        if not user.email:
            user.email = response.get("email", "")

        if not user.full_name and response.get("name"):
            user.full_name = response.get("name", "")

        # If user is new and doesn't have a role, set default role
        # You may want to modify this based on your application logic
        if not hasattr(user, "role") or not user.role:
            user.role = "admin"  # default role - adjust as needed

        user.save()

    return None


def set_default_role(backend, user, response, *args, **kwargs):
    """
    Custom pipeline function to set default role for new users.
    This function ensures all users authenticated via social auth have a role.
    """
    if not user.role:
        # Set default role to admin for users authenticating via social auth
        # You might want to adjust this logic based on your requirements
        user.role = "admin"
        user.save()

    return None
