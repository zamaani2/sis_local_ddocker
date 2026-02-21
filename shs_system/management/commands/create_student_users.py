"""
Management command to create user accounts for students who don't have them.
This is useful after bulk imports where user creation was skipped for performance.

Usage:
python manage.py create_student_users --school-id 1 --send-emails
"""

import logging
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.contrib.auth.hashers import make_password
from shs_system.models import Student, User
from shs_system.models import (
    generate_secure_password,
    generate_unique_id,
    send_user_credentials_email,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Create user accounts for students who don't have them"

    def add_arguments(self, parser):
        parser.add_argument(
            "--school-id",
            type=int,
            required=True,
            help="ID of the school to process students for",
        )
        parser.add_argument(
            "--send-emails",
            action="store_true",
            help="Send welcome emails with credentials to students",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=50,
            help="Number of users to process in each batch",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Perform a dry run without actually creating users",
        )

    def handle(self, *args, **options):
        school_id = options["school_id"]
        send_emails = options["send_emails"]
        batch_size = options["batch_size"]
        dry_run = options["dry_run"]

        # Validate school
        from shs_system.models import School

        try:
            school = School.objects.get(id=school_id)
            self.stdout.write(f"Processing students for school: {school.name}")
        except School.DoesNotExist:
            raise CommandError(f"School with ID {school_id} does not exist")

        # Find students without user accounts
        students_without_users = (
            Student.objects.filter(school=school)
            .exclude(
                id__in=User.objects.filter(student_profile__isnull=False).values_list(
                    "student_profile_id", flat=True
                )
            )
            .select_related("school")
        )

        total_students = students_without_users.count()

        if total_students == 0:
            self.stdout.write(
                self.style.SUCCESS("All students already have user accounts!")
            )
            return

        self.stdout.write(f"Found {total_students} students without user accounts")

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No users will be created")
            )

        created_count = 0
        failed_count = 0
        email_success_count = 0
        email_failed_count = 0
        errors = []

        # Process in batches
        for batch_start in range(0, total_students, batch_size):
            batch_end = min(batch_start + batch_size, total_students)
            batch_students = students_without_users[batch_start:batch_end]

            self.stdout.write(
                f"Processing batch {batch_start//batch_size + 1}: students {batch_start + 1}-{batch_end}"
            )

            users_to_create = []
            student_passwords = {}  # Store passwords for email sending

            # Prepare batch data
            for student in batch_students:
                try:
                    # Generate username from admission_number
                    username = f"student_{student.admission_number}"

                    # Check if a user with this username already exists
                    if User.objects.filter(username=username).exists():
                        # Append a random string to ensure uniqueness
                        username = f"{username}_{generate_unique_id(length=4)}"

                    # Generate secure password
                    password = generate_secure_password()

                    # Create user object (but don't save yet)
                    user = User(
                        username=username,
                        email=student.email
                        or f"{student.admission_number}@example.com",
                        full_name=student.full_name,
                        role="student",
                        password=make_password(password),
                        student_profile=student,
                        school=student.school,
                    )

                    users_to_create.append(user)
                    student_passwords[student.id] = password

                except Exception as e:
                    failed_count += 1
                    error_msg = f"Student {student.full_name}: {str(e)}"
                    errors.append(error_msg)
                    self.stdout.write(self.style.ERROR(error_msg))

            # Bulk create users in this batch
            if users_to_create and not dry_run:
                try:
                    with transaction.atomic():
                        # Use bulk_create for better performance
                        created_users = User.objects.bulk_create(
                            users_to_create, batch_size=25, ignore_conflicts=False
                        )

                        batch_created_count = len(created_users)
                        created_count += batch_created_count

                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Successfully created {batch_created_count} user accounts"
                            )
                        )

                        # Send emails if requested
                        if send_emails:
                            # Get the created users with their student profiles
                            created_usernames = [u.username for u in users_to_create]
                            created_user_objects = User.objects.filter(
                                username__in=created_usernames, school=school
                            ).select_related("student_profile")

                            for user in created_user_objects:
                                if (
                                    user.student_profile
                                    and user.student_profile.id in student_passwords
                                ):
                                    password = student_passwords[
                                        user.student_profile.id
                                    ]
                                    if (
                                        user.email
                                        and user.email
                                        != f"{user.student_profile.admission_number}@example.com"
                                    ):
                                        try:
                                            if send_user_credentials_email(
                                                user, password
                                            ):
                                                email_success_count += 1
                                            else:
                                                email_failed_count += 1
                                        except Exception as e:
                                            email_failed_count += 1
                                            self.stdout.write(
                                                self.style.WARNING(
                                                    f"Failed to send email to {user.full_name}: {str(e)}"
                                                )
                                            )
                                    else:
                                        self.stdout.write(
                                            self.style.WARNING(
                                                f"Skipping email for {user.full_name}: no valid email address"
                                            )
                                        )

                except Exception as batch_error:
                    self.stdout.write(
                        self.style.ERROR(f"Batch creation failed: {str(batch_error)}")
                    )
                    # Try individual creation for this batch
                    for i, user in enumerate(users_to_create):
                        try:
                            with transaction.atomic():
                                user.save()
                                created_count += 1

                                # Send email if requested
                                if send_emails and user.student_profile:
                                    password = student_passwords[
                                        user.student_profile.id
                                    ]
                                    if (
                                        user.email
                                        and user.email
                                        != f"{user.student_profile.admission_number}@example.com"
                                    ):
                                        try:
                                            if send_user_credentials_email(
                                                user, password
                                            ):
                                                email_success_count += 1
                                            else:
                                                email_failed_count += 1
                                        except Exception as e:
                                            email_failed_count += 1
                                            self.stdout.write(
                                                self.style.WARNING(
                                                    f"Failed to send email to {user.full_name}: {str(e)}"
                                                )
                                            )

                        except Exception as individual_error:
                            failed_count += 1
                            error_msg = (
                                f"User {user.full_name}: {str(individual_error)}"
                            )
                            errors.append(error_msg)
                            self.stdout.write(self.style.ERROR(error_msg))

            elif dry_run and users_to_create:
                self.stdout.write(
                    f"Would create {len(users_to_create)} user accounts in this batch"
                )
                created_count += len(users_to_create)

        # Final summary
        self.stdout.write("\n" + "=" * 50)
        if dry_run:
            self.stdout.write(self.style.SUCCESS("DRY RUN COMPLETE"))
            self.stdout.write(f"Would create: {created_count} user accounts")
        else:
            self.stdout.write(self.style.SUCCESS("USER CREATION COMPLETE"))
            self.stdout.write(f"Successfully created: {created_count} user accounts")

        if failed_count > 0:
            self.stdout.write(
                self.style.WARNING(f"Failed to create: {failed_count} user accounts")
            )

        if send_emails and not dry_run:
            self.stdout.write(f"Emails sent successfully: {email_success_count}")
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
        if not dry_run and created_count > 0:
            self.stdout.write(f"\n" + "=" * 50)
            self.stdout.write(self.style.SUCCESS("NEXT STEPS:"))
            if not send_emails:
                self.stdout.write(
                    "• Run with --send-emails to send welcome emails to students"
                )
            self.stdout.write("• Students can now log in with their credentials")
            self.stdout.write(
                "• Check the admin panel to verify user accounts were created correctly"
            )
