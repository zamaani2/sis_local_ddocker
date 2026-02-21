from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password

User = get_user_model()


class Command(BaseCommand):
    help = "Create a superadmin user for the multi-school platform"

    def add_arguments(self, parser):
        parser.add_argument(
            "--username", required=True, help="Username for the superadmin"
        )
        parser.add_argument("--email", required=True, help="Email for the superadmin")
        parser.add_argument(
            "--password", required=True, help="Password for the superadmin"
        )
        parser.add_argument(
            "--full-name", required=True, help="Full name for the superadmin"
        )

    def handle(self, *args, **options):
        username = options["username"]
        email = options["email"]
        password = options["password"]
        full_name = options["full_name"]

        # Check if user already exists
        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(f'User with username "{username}" already exists')
            )
            return

        if User.objects.filter(email=email).exists():
            self.stdout.write(
                self.style.WARNING(f'User with email "{email}" already exists')
            )
            return

        # Create the superadmin user
        user = User.objects.create(
            username=username,
            email=email,
            password=make_password(password),
            full_name=full_name,
            role="superadmin",
            is_superadmin=True,
            is_staff=True,
            is_superuser=True,
        )

        self.stdout.write(
            self.style.SUCCESS(f"Successfully created superadmin user: {username}")
        )
