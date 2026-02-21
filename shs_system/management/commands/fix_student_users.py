from django.core.management.base import BaseCommand
from shs_system.models import Student, User, SchoolInformation
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Fix student users by ensuring they have a school association"

    def handle(self, *args, **options):
        self.stdout.write("Starting to fix student users...")

        # Get all student users without school association
        student_users = User.objects.filter(role="student", school__isnull=True)
        self.stdout.write(
            f"Found {student_users.count()} student users without school association"
        )

        fixed_count = 0

        for user in student_users:
            try:
                # If user has a student_profile, use its school
                if user.student_profile and user.student_profile.school:
                    user.school = user.student_profile.school
                    user.save()
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Fixed user {user.username} - assigned to school: {user.school.name}"
                        )
                    )
                    fixed_count += 1
                else:
                    # If no student profile or no school on student profile, try to find a default school
                    default_school = SchoolInformation.get_active()
                    if default_school:
                        user.school = default_school
                        user.save()
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Fixed user {user.username} - assigned to default school: {default_school.name}"
                            )
                        )
                        fixed_count += 1
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Could not fix user {user.username} - no default school found"
                            )
                        )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error fixing user {user.username}: {str(e)}")
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Fixed {fixed_count} out of {student_users.count()} student users"
            )
        )
