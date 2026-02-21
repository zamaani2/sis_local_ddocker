#!/usr/bin/env python
"""
Management command to easily manage super admin users.
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()


class Command(BaseCommand):
    help = "Manage super admin users - create, update, or list super admins"

    def add_arguments(self, parser):
        parser.add_argument(
            "--action",
            choices=["create", "update", "list", "remove"],
            required=True,
            help="Action to perform: create, update, list, or remove",
        )
        parser.add_argument(
            "--username",
            help="Username for the super admin (required for create/update/remove)",
        )
        parser.add_argument(
            "--email", help="Email for the super admin (required for create/update)"
        )
        parser.add_argument(
            "--password",
            help="Password for the super admin (required for create/update)",
        )
        parser.add_argument(
            "--full-name",
            help="Full name for the super admin (required for create/update)",
        )
        parser.add_argument(
            "--set-superadmin",
            action="store_true",
            help="Set is_superadmin=True for existing user",
        )
        parser.add_argument(
            "--unset-superadmin",
            action="store_true",
            help="Set is_superadmin=False for existing user",
        )

    def handle(self, *args, **options):
        action = options["action"]

        if action == "list":
            self.list_super_admins()
        elif action == "create":
            self.create_super_admin(options)
        elif action == "update":
            self.update_super_admin(options)
        elif action == "remove":
            self.remove_super_admin(options)

    def list_super_admins(self):
        """List all super admin users"""
        super_admins = User.objects.filter(is_superadmin=True)

        if not super_admins.exists():
            self.stdout.write(self.style.WARNING("No super admin users found."))
            return

        self.stdout.write(
            self.style.SUCCESS(f"Found {super_admins.count()} super admin user(s):")
        )
        self.stdout.write("")

        for user in super_admins:
            self.stdout.write(f"  Username: {user.username}")
            self.stdout.write(f"  Email: {user.email}")
            self.stdout.write(f"  Full Name: {user.full_name}")
            self.stdout.write(f"  Role: {user.get_role_display()}")
            self.stdout.write(f"  Is Active: {user.is_active}")
            self.stdout.write(f"  Is Staff: {user.is_staff}")
            self.stdout.write(f"  Is Superuser: {user.is_superuser}")
            self.stdout.write("  " + "-" * 50)

    def create_super_admin(self, options):
        """Create a new super admin user"""
        username = options.get("username")
        email = options.get("email")
        password = options.get("password")
        full_name = options.get("full_name")

        if not all([username, email, password, full_name]):
            raise CommandError(
                "All fields (username, email, password, full_name) are required for creating a super admin."
            )

        # Check if user already exists
        if User.objects.filter(username=username).exists():
            raise CommandError(f'User with username "{username}" already exists.')

        if User.objects.filter(email=email).exists():
            raise CommandError(f'User with email "{email}" already exists.')

        try:
            with transaction.atomic():
                user = User.objects.create(
                    username=username,
                    email=email,
                    full_name=full_name,
                    role="superadmin",
                    is_superadmin=True,
                    is_staff=True,
                    is_superuser=True,
                )
                user.set_password(password)
                user.save()

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully created super admin user: {username}"
                    )
                )
                self.stdout.write(f"  Username: {username}")
                self.stdout.write(f"  Email: {email}")
                self.stdout.write(f"  Full Name: {full_name}")
                self.stdout.write(f"  Password: {password}")

        except Exception as e:
            raise CommandError(f"Error creating super admin user: {str(e)}")

    def update_super_admin(self, options):
        """Update an existing super admin user"""
        username = options.get("username")

        if not username:
            raise CommandError("Username is required for updating a user.")

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f'User with username "{username}" not found.')

        try:
            with transaction.atomic():
                # Update basic fields if provided
                if options.get("email"):
                    user.email = options["email"]
                if options.get("full_name"):
                    user.full_name = options["full_name"]
                if options.get("password"):
                    user.set_password(options["password"])

                # Handle super admin status
                if options.get("set_superadmin"):
                    user.is_superadmin = True
                    user.is_staff = True
                    user.is_superuser = True
                    user.role = "superadmin"
                elif options.get("unset_superadmin"):
                    user.is_superadmin = False
                    # Don't change is_staff and is_superuser as they might be needed for Django admin

                user.save()

                self.stdout.write(
                    self.style.SUCCESS(f"Successfully updated user: {username}")
                )
                self.stdout.write(f"  Is Superadmin: {user.is_superadmin}")
                self.stdout.write(f"  Is Staff: {user.is_staff}")
                self.stdout.write(f"  Is Superuser: {user.is_superuser}")

        except Exception as e:
            raise CommandError(f"Error updating user: {str(e)}")

    def remove_super_admin(self, options):
        """Remove super admin status from a user"""
        username = options.get("username")

        if not username:
            raise CommandError("Username is required for removing super admin status.")

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f'User with username "{username}" not found.')

        if not user.is_superadmin:
            self.stdout.write(
                self.style.WARNING(f"User {username} is not a super admin.")
            )
            return

        try:
            with transaction.atomic():
                user.is_superadmin = False
                user.save()

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully removed super admin status from: {username}"
                    )
                )

        except Exception as e:
            raise CommandError(f"Error removing super admin status: {str(e)}")




