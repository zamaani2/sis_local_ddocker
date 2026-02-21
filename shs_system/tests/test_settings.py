"""
Test settings to override production settings for testing.
This file configures the test environment to bypass certain production features.
"""

from SchoolApp.settings import *

# Use standard Django authentication backend for tests
# This bypasses django-axes which requires request parameter
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
]

# Disable axes during testing
AXES_ENABLED = False

# Speed up password hashing in tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Use in-memory email backend for tests
EMAIL_BACKEND = "django.core.mail.backends.localmem.EmailBackend"

# Disable migrations for faster tests (optional)
# MIGRATION_MODULES = {
#     app: None for app in INSTALLED_APPS
# }
