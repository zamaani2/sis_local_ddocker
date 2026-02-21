from django.core.management.base import BaseCommand
from shs_system.models import SchoolInformation, ScoringConfiguration
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = "Create default scoring configurations for existing schools"

    def add_arguments(self, parser):
        parser.add_argument(
            "--school-id",
            type=int,
            help="Create configuration for a specific school ID",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force creation even if configuration already exists",
        )

    def handle(self, *args, **options):
        school_id = options.get("school_id")
        force = options.get("force")

        if school_id:
            # Create for specific school
            try:
                school = SchoolInformation.objects.get(id=school_id)
                self.create_config_for_school(school, force)
            except SchoolInformation.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"School with ID {school_id} does not exist.")
                )
        else:
            # Create for all schools
            schools = SchoolInformation.objects.filter(is_active=True)
            self.stdout.write(f"Found {schools.count()} active schools")

            for school in schools:
                self.create_config_for_school(school, force)

        self.stdout.write(
            self.style.SUCCESS("Default scoring configuration creation completed!")
        )

    def create_config_for_school(self, school, force=False):
        """Create default scoring configuration for a school"""
        # Check if configuration already exists
        existing_config = ScoringConfiguration.objects.filter(
            school=school, is_active=True
        ).first()

        if existing_config and not force:
            self.stdout.write(
                f'School "{school.name}" already has an active scoring configuration. '
                f"Use --force to overwrite."
            )
            return

        # Get a superuser or admin user for created_by field
        admin_user = User.objects.filter(
            role="admin", school=school, is_active=True
        ).first()

        if not admin_user:
            admin_user = User.objects.filter(is_superuser=True, is_active=True).first()

        # Create default configuration
        config_data = {
            "school": school,
            "exam_score_percentage": 70.0,
            "class_score_percentage": 30.0,
            "max_exam_score": 70.0,
            "max_class_score": 30.0,
            "individual_score_weight": 25.0,
            "class_test_weight": 25.0,
            "project_weight": 25.0,
            "group_work_weight": 25.0,
            "is_active": True,
        }

        if admin_user:
            config_data["created_by"] = admin_user

        if existing_config and force:
            # Update existing configuration
            for key, value in config_data.items():
                if key != "school":
                    setattr(existing_config, key, value)
            existing_config.save()
            self.stdout.write(
                self.style.WARNING(
                    f'Updated existing scoring configuration for "{school.name}"'
                )
            )
        else:
            # Create new configuration
            ScoringConfiguration.objects.create(**config_data)
            self.stdout.write(
                self.style.SUCCESS(
                    f'Created default scoring configuration for "{school.name}"'
                )
            )




