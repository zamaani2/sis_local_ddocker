"""
Management command to send credential emails to students who have user accounts but never received welcome emails.
This is useful after bulk imports where email sending was skipped for performance.

Usage:
python manage.py send_student_credentials --school-id 1
"""

import logging
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from shs_system.models import (
    Student,
    User,
    send_user_credentials_email,
    generate_secure_password,
)
from django.contrib.auth.hashers import make_password

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Send credential emails to students who have user accounts"

    def add_arguments(self, parser):
        parser.add_argument(
            "--school-id",
            type=int,
            required=True,
            help="ID of the school to process students for",
        )
        parser.add_argument(
            "--reset-passwords",
            action="store_true",
            help="Reset passwords and send new credentials (use if original passwords are lost)",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=50,
            help="Number of students to process in each batch",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Perform a dry run without actually sending emails",
        )

    def handle(self, *args, **options):
        school_id = options["school_id"]
        reset_passwords = options["reset_passwords"]
        batch_size = options["batch_size"]
        dry_run = options["dry_run"]

        # Validate school
        from shs_system.models import School

        try:
            school = School.objects.get(id=school_id)
            self.stdout.write(f"Processing students for school: {school.name}")
        except School.DoesNotExist:
            raise CommandError(f"School with ID {school_id} does not exist")

        # Find students with user accounts who have valid email addresses
        students_with_users = (
            Student.objects.filter(
                school=school,
                email__isnull=False,
                email__gt="",  # Non-empty email
            )
            .exclude(email__endswith="@example.com")  # Exclude generated emails
            .select_related("school")
            .prefetch_related("user_set")
        )

        # Filter to only students who have user accounts
        students_to_email = []
        for student in students_with_users:
            user = User.objects.filter(student_profile=student).first()
            if user:
                students_to_email.append((student, user))

        total_students = len(students_to_email)

        if total_students == 0:
            self.stdout.write(
                self.style.WARNING(
                    "No students found with user accounts and valid email addresses!"
                )
            )
            return

        self.stdout.write(
            f"Found {total_students} students with user accounts and valid emails"
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No emails will be sent")
            )

        if reset_passwords:
            self.stdout.write(
                self.style.WARNING(
                    "PASSWORD RESET MODE - New passwords will be generated"
                )
            )

        email_success_count = 0
        email_failed_count = 0
        password_reset_count = 0
        errors = []

        # Process in batches
        for batch_start in range(0, total_students, batch_size):
            batch_end = min(batch_start + batch_size, total_students)
            batch_students = students_to_email[batch_start:batch_end]

            self.stdout.write(
                f"Processing batch {batch_start//batch_size + 1}: students {batch_start + 1}-{batch_end}"
            )

            for student, user in batch_students:
                try:
                    # Generate new password if requested
                    if reset_passwords and not dry_run:
                        new_password = generate_secure_password()
                        user.password = make_password(new_password)
                        user.save()
                        password = new_password
                        password_reset_count += 1
                        self.stdout.write(f"Reset password for: {student.full_name}")
                    else:
                        # Use stored temp password or generate a new one for display
                        password = getattr(student, "temp_password", None)
                        if not password:
                            if reset_passwords:
                                password = "NEW_PASSWORD_WILL_BE_GENERATED"
                            else:
                                self.stdout.write(
                                    self.style.WARNING(
                                        f"No stored password for {student.full_name}. Use --reset-passwords to generate new credentials."
                                    )
                                )
                                continue

                    # Send email
                    if not dry_run:
                        try:
                            if send_user_credentials_email(user, password):
                                email_success_count += 1
                                self.stdout.write(
                                    self.style.SUCCESS(
                                        f"✓ Email sent to: {student.full_name} ({student.email})"
                                    )
                                )
                            else:
                                email_failed_count += 1
                                self.stdout.write(
                                    self.style.ERROR(
                                        f"✗ Failed to send email to: {student.full_name}"
                                    )
                                )
                        except Exception as e:
                            email_failed_count += 1
                            error_msg = f"{student.full_name}: {str(e)}"
                            errors.append(error_msg)
                            self.stdout.write(
                                self.style.ERROR(
                                    f"✗ Email error for {student.full_name}: {str(e)}"
                                )
                            )
                    else:
                        self.stdout.write(
                            f"Would send email to: {student.full_name} ({student.email})"
                        )
                        email_success_count += 1

                except Exception as e:
                    email_failed_count += 1
                    error_msg = f"{student.full_name}: {str(e)}"
                    errors.append(error_msg)
                    self.stdout.write(
                        self.style.ERROR(
                            f"Error processing {student.full_name}: {str(e)}"
                        )
                    )

        # Final summary
        self.stdout.write("\n" + "=" * 50)
        if dry_run:
            self.stdout.write(self.style.SUCCESS("DRY RUN COMPLETE"))
            self.stdout.write(f"Would send emails to: {email_success_count} students")
        else:
            self.stdout.write(self.style.SUCCESS("EMAIL SENDING COMPLETE"))
            self.stdout.write(f"Emails sent successfully: {email_success_count}")

            if password_reset_count > 0:
                self.stdout.write(f"Passwords reset: {password_reset_count}")

        if email_failed_count > 0:
            self.stdout.write(
                self.style.WARNING(f"Email failures: {email_failed_count}")
            )

        if errors:
            self.stdout.write(f"\nFirst 10 errors:")
            for error in errors[:10]:
                self.stdout.write(self.style.ERROR(f"  {error}"))

            if len(errors) > 10:
                self.stdout.write(f"... and {len(errors) - 10} more errors")

        # Provide helpful next steps
        if not dry_run and email_success_count > 0:
            self.stdout.write(f"\n" + "=" * 50)
            self.stdout.write(self.style.SUCCESS("NEXT STEPS:"))
            self.stdout.write(
                "• Students should receive their login credentials via email"
            )
            self.stdout.write(
                "• They can now log in to the system using their credentials"
            )
            if email_failed_count > 0:
                self.stdout.write("• Check email configuration for failed sends")
                self.stdout.write(
                    "• Verify email addresses are correct for failed students"
                )

        elif email_failed_count > 0:
            self.stdout.write(f"\n" + "=" * 50)
            self.stdout.write(self.style.WARNING("TROUBLESHOOTING:"))
            self.stdout.write("• Check your email configuration settings")
            self.stdout.write("• Verify SMTP credentials are correct")
            self.stdout.write("• Ensure firewall allows SMTP connections")
            self.stdout.write("• Check if email provider requires app passwords")
