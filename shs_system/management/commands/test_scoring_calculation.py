from django.core.management.base import BaseCommand
from shs_system.models import SchoolInformation, ScoringConfiguration
from decimal import Decimal


class Command(BaseCommand):
    help = "Test scoring calculation with different configurations"

    def add_arguments(self, parser):
        parser.add_argument(
            "--school-id",
            type=int,
            help="Test with a specific school ID",
        )

    def handle(self, *args, **options):
        school_id = options.get("school_id")

        if school_id:
            try:
                school = SchoolInformation.objects.get(id=school_id)
                self.test_school_config(school)
            except SchoolInformation.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"School with ID {school_id} does not exist.")
                )
        else:
            # Test with first available school
            school = SchoolInformation.objects.filter(is_active=True).first()
            if school:
                self.test_school_config(school)
            else:
                self.stdout.write(self.style.ERROR("No active schools found."))

    def test_school_config(self, school):
        """Test scoring configuration for a school"""
        self.stdout.write(f"\nTesting scoring configuration for: {school.name}")
        self.stdout.write("=" * 60)

        # Get current configuration
        config = ScoringConfiguration.get_active_config(school)

        if not config:
            self.stdout.write(
                self.style.WARNING(
                    "No scoring configuration found. Creating default..."
                )
            )
            # Create default config for testing
            config = ScoringConfiguration.objects.create(
                school=school,
                exam_score_percentage=70.0,
                class_score_percentage=30.0,
                max_exam_score=70.0,
                max_class_score=30.0,
                individual_score_weight=25.0,
                class_test_weight=25.0,
                project_weight=25.0,
                group_work_weight=25.0,
                is_active=True,
            )

        # Display current configuration
        self.stdout.write("\nCurrent Configuration:")
        self.stdout.write(
            f"  Exam Score: {config.exam_score_percentage}% (max: {config.max_exam_score})"
        )
        self.stdout.write(
            f"  Class Score: {config.class_score_percentage}% (max: {config.max_class_score})"
        )
        self.stdout.write(f"  Individual Weight: {config.individual_score_weight}%")
        self.stdout.write(f"  Class Test Weight: {config.class_test_weight}%")
        self.stdout.write(f"  Project Weight: {config.project_weight}%")
        self.stdout.write(f"  Group Work Weight: {config.group_work_weight}%")

        # Test different scenarios
        self.test_scenarios(config)

    def test_scenarios(self, config):
        """Test various scoring scenarios"""
        self.stdout.write("\nTest Scenarios:")
        self.stdout.write("=" * 40)

        # Scenario 1: Perfect scores
        self.stdout.write("\n1. Perfect Scores:")
        class_score = config.max_class_score
        exam_score = config.max_exam_score
        total = self.calculate_total_score(config, class_score, exam_score)
        self.stdout.write(f"   Class: {class_score}/{config.max_class_score}")
        self.stdout.write(f"   Exam: {exam_score}/{config.max_exam_score}")
        self.stdout.write(f"   Total: {total:.2f}/100")

        # Scenario 2: Average scores
        self.stdout.write("\n2. Average Scores:")
        class_score = config.max_class_score * Decimal("0.7")  # 70% of max
        exam_score = config.max_exam_score * Decimal("0.75")  # 75% of max
        total = self.calculate_total_score(config, class_score, exam_score)
        self.stdout.write(f"   Class: {class_score:.2f}/{config.max_class_score}")
        self.stdout.write(f"   Exam: {exam_score:.2f}/{config.max_exam_score}")
        self.stdout.write(f"   Total: {total:.2f}/100")

        # Scenario 3: Low scores
        self.stdout.write("\n3. Low Scores:")
        class_score = config.max_class_score * Decimal("0.4")  # 40% of max
        exam_score = config.max_exam_score * Decimal("0.35")  # 35% of max
        total = self.calculate_total_score(config, class_score, exam_score)
        self.stdout.write(f"   Class: {class_score:.2f}/{config.max_class_score}")
        self.stdout.write(f"   Exam: {exam_score:.2f}/{config.max_exam_score}")
        self.stdout.write(f"   Total: {total:.2f}/100")

        # Scenario 4: Class score components
        self.stdout.write("\n4. Class Score Components:")
        individual = Decimal("8.0")  # Out of 10
        class_test = Decimal("7.5")  # Out of 10
        project = Decimal("9.0")  # Out of 10
        group_work = Decimal("6.5")  # Out of 10

        # Calculate weighted class score
        weighted_score = (
            (individual * config.individual_score_weight / Decimal("100"))
            + (class_test * config.class_test_weight / Decimal("100"))
            + (project * config.project_weight / Decimal("100"))
            + (group_work * config.group_work_weight / Decimal("100"))
        )

        # Convert to the configured class score percentage
        class_score = (weighted_score / Decimal("10")) * config.max_class_score

        self.stdout.write(f"   Individual: {individual}/10")
        self.stdout.write(f"   Class Test: {class_test}/10")
        self.stdout.write(f"   Project: {project}/10")
        self.stdout.write(f"   Group Work: {group_work}/10")
        self.stdout.write(
            f"   Weighted Class Score: {class_score:.2f}/{config.max_class_score}"
        )

        # Test with different configurations
        self.test_different_configs()

    def test_different_configs(self):
        """Test with different configuration scenarios"""
        self.stdout.write("\n5. Different Configuration Scenarios:")
        self.stdout.write("=" * 50)

        # Test 50/50 split
        self.stdout.write("\n   A. 50/50 Split (Exam/Class):")
        config_50_50 = ScoringConfiguration(
            exam_score_percentage=50.0,
            class_score_percentage=50.0,
            max_exam_score=50.0,
            max_class_score=50.0,
        )
        total = self.calculate_total_score(config_50_50, 40.0, 35.0)
        self.stdout.write(f"      Class: 40/50, Exam: 35/50, Total: {total:.2f}/100")

        # Test 80/20 split
        self.stdout.write("\n   B. 80/20 Split (Exam/Class):")
        config_80_20 = ScoringConfiguration(
            exam_score_percentage=80.0,
            class_score_percentage=20.0,
            max_exam_score=80.0,
            max_class_score=20.0,
        )
        total = self.calculate_total_score(config_80_20, 15.0, 60.0)
        self.stdout.write(f"      Class: 15/20, Exam: 60/80, Total: {total:.2f}/100")

        # Test 60/40 split
        self.stdout.write("\n   C. 60/40 Split (Exam/Class):")
        config_60_40 = ScoringConfiguration(
            exam_score_percentage=60.0,
            class_score_percentage=40.0,
            max_exam_score=60.0,
            max_class_score=40.0,
        )
        total = self.calculate_total_score(config_60_40, 30.0, 45.0)
        self.stdout.write(f"      Class: 30/40, Exam: 45/60, Total: {total:.2f}/100")

    def calculate_total_score(self, config, class_score, exam_score):
        """Calculate total score using the configuration"""
        if config:
            # Use dynamic configuration to calculate total score
            # Convert all values to Decimal to avoid type mismatches
            class_score_decimal = Decimal(str(class_score))
            exam_score_decimal = Decimal(str(exam_score))
            max_class_score_decimal = Decimal(str(config.max_class_score))
            max_exam_score_decimal = Decimal(str(config.max_exam_score))
            class_score_percentage_decimal = Decimal(str(config.class_score_percentage))
            exam_score_percentage_decimal = Decimal(str(config.exam_score_percentage))

            class_score_weighted = (
                class_score_decimal / max_class_score_decimal
            ) * class_score_percentage_decimal
            exam_score_weighted = (
                exam_score_decimal / max_exam_score_decimal
            ) * exam_score_percentage_decimal
            return float(class_score_weighted + exam_score_weighted)
        else:
            # Fallback to simple addition
            return float(class_score + exam_score)
