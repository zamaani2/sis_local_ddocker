"""
Management command to check data integrity
"""

from django.core.management.base import BaseCommand
from shs_system.models import User
from shs_system.models import SchoolInformation, Student, Teacher
from django.db import connection
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Check data integrity"

    def add_arguments(self, parser):
        parser.add_argument(
            "--check-duplicates",
            action="store_true",
            help="Check for duplicate users, emails, etc.",
        )
        parser.add_argument(
            "--check-orphans",
            action="store_true",
            help="Check for orphaned records",
        )
        parser.add_argument(
            "--show-stats",
            action="store_true",
            help="Show basic data statistics",
        )

    def handle(self, *args, **options):
        self.stdout.write("Checking data integrity...")

        if options["show_stats"]:
            self._show_data_stats()

        if options["check_duplicates"]:
            self._check_duplicates()

        if options["check_orphans"]:
            self._check_orphans()

        if not any(
            [
                options["show_stats"],
                options["check_duplicates"],
                options["check_orphans"],
            ]
        ):
            # Run all checks by default
            self._show_data_stats()
            self._check_duplicates()
            self._check_orphans()

    def _show_data_stats(self):
        """Show basic data statistics"""
        self.stdout.write("\n=== DATA STATISTICS ===")

        # User statistics
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        self.stdout.write(f"Users: {total_users} total, {active_users} active")

        # School statistics
        schools = SchoolInformation.objects.count()
        self.stdout.write(f"Schools: {schools}")

        # Student statistics
        students = Student.objects.count()
        self.stdout.write(f"Students: {students}")

        # Teacher statistics
        teachers = Teacher.objects.count()
        self.stdout.write(f"Teachers: {teachers}")

    def _check_duplicates(self):
        """Check for duplicate records"""
        self.stdout.write("\n=== DUPLICATE CHECK ===")

        # Check for duplicate emails
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT email, COUNT(*) as count 
                FROM shs_system_user 
                WHERE email IS NOT NULL AND email != ''
                GROUP BY email 
                HAVING COUNT(*) > 1
            """
            )
            duplicate_emails = cursor.fetchall()

            if duplicate_emails:
                self.stdout.write(
                    self.style.WARNING(
                        f"Found {len(duplicate_emails)} duplicate emails:"
                    )
                )
                for email, count in duplicate_emails:
                    self.stdout.write(f"  - {email}: {count} users")
            else:
                self.stdout.write(self.style.SUCCESS("No duplicate emails found"))

            # Check for duplicate usernames
            cursor.execute(
                """
                SELECT username, COUNT(*) as count 
                FROM shs_system_user 
                GROUP BY username 
                HAVING COUNT(*) > 1
            """
            )
            duplicate_usernames = cursor.fetchall()

            if duplicate_usernames:
                self.stdout.write(
                    self.style.WARNING(
                        f"Found {len(duplicate_usernames)} duplicate usernames:"
                    )
                )
                for username, count in duplicate_usernames:
                    self.stdout.write(f"  - {username}: {count} users")
            else:
                self.stdout.write(self.style.SUCCESS("No duplicate usernames found"))

    def _check_orphans(self):
        """Check for orphaned records"""
        self.stdout.write("\n=== ORPHAN CHECK ===")

        # Check for students without users
        students_without_users = Student.objects.filter(user__isnull=True).count()
        if students_without_users > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"Found {students_without_users} students without user accounts"
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS("All students have user accounts"))

        # Check for teachers without users
        teachers_without_users = Teacher.objects.filter(user__isnull=True).count()
        if teachers_without_users > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"Found {teachers_without_users} teachers without user accounts"
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS("All teachers have user accounts"))

        # Check for users without profiles
        users_without_students = User.objects.filter(
            student_profile__isnull=True
        ).count()
        users_without_teachers = User.objects.filter(
            teacher_profile__isnull=True
        ).count()

        if users_without_students > 0 or users_without_teachers > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"Found {users_without_students} users without student profiles, "
                    f"{users_without_teachers} users without teacher profiles"
                )
            )
        else:
            self.stdout.write(self.style.SUCCESS("All users have appropriate profiles"))
