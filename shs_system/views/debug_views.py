import os
from django.shortcuts import render
from django.conf import settings
from django.contrib.auth.decorators import login_required
from shs_system.models import Student


@login_required
def test_media_serving(request):
    """Test view to check if media files are being served correctly."""
    # Get all students with profile pictures
    students_with_images = Student.objects.filter(
        profile_picture__isnull=False
    ).exclude(profile_picture="")

    # Get sample image paths from the media directory
    image_paths = []
    profile_pictures_path = os.path.join(
        settings.MEDIA_ROOT, "profile_pictures", "students"
    )

    if os.path.exists(profile_pictures_path):
        for filename in os.listdir(profile_pictures_path):
            if filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
                image_paths.append(
                    os.path.join("profile_pictures", "students", filename)
                )

    context = {
        "students": students_with_images,
        "image_paths": image_paths,
        "MEDIA_URL": settings.MEDIA_URL,
        "MEDIA_ROOT": settings.MEDIA_ROOT,
    }

    return render(request, "debug/media_test.html", context)
