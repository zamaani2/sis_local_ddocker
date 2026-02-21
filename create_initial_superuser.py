"""
Script to create an initial superuser on first deployment
Run this during the build process
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SchoolApp.settings_production')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Check if any superuser exists
if not User.objects.filter(is_superuser=True).exists():
    # Create superuser with environment variables
    username = os.environ.get('SUPERUSER_USERNAME', 'admin')
    email = os.environ.get('SUPERUSER_EMAIL', 'admin@example.com')
    password = os.environ.get('SUPERUSER_PASSWORD', 'admin123')
    
    User.objects.create_superuser(
        username=username,
        email=email,
        password=password
    )
    print(f"✅ Superuser '{username}' created successfully!")
    print(f"📧 Email: {email}")
    print("⚠️  Please change the password after first login!")
else:
    print("ℹ️  Superuser already exists. Skipping creation.")

