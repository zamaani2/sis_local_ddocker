"""
Management command to demonstrate the enhanced scoring system functionality.
This command creates sample data and shows how the individual score components work.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from decimal import Decimal
import random

from shs_system.models import (
    SchoolInformation,
    AcademicYear,
    Term,
    Form,
    LearningArea,
    Department,
    Teacher,
    Student,
    Class,
    Subject,
    TeacherSubjectAssignment,
    ClassSubject,
    Assessment,
    ScoringConfiguration,
    GradingSystem,
    StudentClass,
    User,
)


class Command(BaseCommand):
    help = "Demonstrate enhanced scoring system with sample data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--school-slug",
            type=str,
            default="demo-school",
            help="School slug to use for demonstration",
        )
        parser.add_argument(
            "--create-sample-data",
            action="store_true",
            help="Create sample school data for demonstration",
        )
        parser.add_argument(
            "--show-calculations",
            action="store_true",
            help="Show detailed score calculations",
        )

    def handle(self, *args, **options):
        school_slug = options["school_slug"]

        try:
            # Get or create school
            school, created = SchoolInformation.objects.get_or_create(
                slug=school_slug,
                defaults={
                    "name": "Demo High School",
                    "short_name": "DHS",
                    "address": "123 Education Street, Learning City",
                    "phone_number": "+1-555-0123",
                    "email": "admin@demo-school.edu",
                },
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"Created demo school: {school.name}")
                )
            else:
                self.stdout.write(f"Using existing school: {school.name}")

            if options["create_sample_data"]:
                self.create_sample_data(school)

            # Get or create scoring configuration
            scoring_config = self.setup_scoring_configuration(school)

            # Get or create grading system
            self.setup_grading_system(school)

            if options["show_calculations"]:
                self.demonstrate_calculations(school, scoring_config)

            self.stdout.write(
                self.style.SUCCESS(
                    f"\nEnhanced scoring system demonstration complete!\n"
                    f"Access the enhanced score entry at: /enhanced-enter-scores/\n"
                    f"School: {school.name} (slug: {school.slug})"
                )
            )

        except Exception as e:
            raise CommandError(f"Error during demonstration: {str(e)}")

    @transaction.atomic
    def create_sample_data(self, school):
        """Create sample data for demonstration."""
        self.stdout.write("Creating sample data...")

        # Create academic year and term
        academic_year, _ = AcademicYear.objects.get_or_create(
            name="2024/2025",
            school=school,
            defaults={
                "start_date": "2024-09-01",
                "end_date": "2025-06-30",
                "is_current": True,
            },
        )

        term, _ = Term.objects.get_or_create(
            academic_year=academic_year,
            term_number=1,
            school=school,
            defaults={
                "start_date": "2024-09-01",
                "end_date": "2024-12-20",
                "is_current": True,
            },
        )

        # Create form and learning area
        form, _ = Form.objects.get_or_create(
            form_number=1, school=school, defaults={"name": "Form 1"}
        )

        learning_area, _ = LearningArea.objects.get_or_create(
            code="general_arts", school=school, defaults={"name": "General Arts"}
        )

        # Create department
        department, _ = Department.objects.get_or_create(
            code="MATH", school=school, defaults={"name": "Mathematics Department"}
        )

        # Create subject
        subject, _ = Subject.objects.get_or_create(
            subject_name="Mathematics",
            school=school,
            department=department,
            defaults={"learning_area": learning_area},
        )

        # Create class
        class_obj, _ = Class.objects.get_or_create(
            name="1A",
            academic_year=academic_year,
            school=school,
            defaults={
                "form": form,
                "learning_area": learning_area,
                "maximum_students": 30,
            },
        )

        # Create teacher and user
        teacher_user, _ = User.objects.get_or_create(
            username="demo_teacher",
            defaults={
                "email": "teacher@demo-school.edu",
                "full_name": "Demo Teacher",
                "role": "teacher",
                "school": school,
            },
        )

        teacher, _ = Teacher.objects.get_or_create(
            full_name="Demo Teacher",
            school=school,
            defaults={
                "department": department,
                "gender": "M",
                "contact_number": "+1-555-0124",
                "email": "teacher@demo-school.edu",
            },
        )

        # Link teacher to user
        teacher_user.teacher_profile = teacher
        teacher_user.save()

        # Create teacher assignment
        assignment, _ = TeacherSubjectAssignment.objects.get_or_create(
            teacher=teacher,
            subject=subject,
            class_assigned=class_obj,
            academic_year=academic_year,
            school=school,
            defaults={"is_active": True},
        )

        # Create sample students
        students = []
        for i in range(5):
            student_user, _ = User.objects.get_or_create(
                username=f"demo_student_{i+1}",
                defaults={
                    "email": f"student{i+1}@demo-school.edu",
                    "full_name": f"Demo Student {i+1}",
                    "role": "student",
                    "school": school,
                },
            )

            student, _ = Student.objects.get_or_create(
                full_name=f"Demo Student {i+1}",
                school=school,
                defaults={
                    "date_of_birth": f"2008-0{(i%9)+1}-15",
                    "gender": "M" if i % 2 == 0 else "F",
                    "parent_contact": f"+1-555-{1000+i}",
                    "admission_date": "2024-09-01",
                    "form": form,
                    "learning_area": learning_area,
                    "email": f"student{i+1}@demo-school.edu",
                },
            )

            # Link student to user
            student_user.student_profile = student
            student_user.save()

            # Assign student to class
            StudentClass.objects.get_or_create(
                student=student,
                assigned_class=class_obj,
                school=school,
                defaults={"is_active": True},
            )

            students.append(student)

        self.stdout.write(
            self.style.SUCCESS(
                f"Created sample data: {len(students)} students, 1 teacher, 1 class"
            )
        )

    def setup_scoring_configuration(self, school):
        """Create or update scoring configuration."""
        config, created = ScoringConfiguration.objects.get_or_create(
            school=school,
            is_active=True,
            defaults={
                "exam_score_percentage": Decimal("70.0"),
                "class_score_percentage": Decimal("30.0"),
                "individual_score_weight": Decimal("25.0"),
                "class_test_weight": Decimal("25.0"),
                "project_weight": Decimal("25.0"),
                "group_work_weight": Decimal("25.0"),
                "max_exam_score": Decimal("70.0"),
                "max_class_score": Decimal("30.0"),
            },
        )

        if created:
            self.stdout.write(self.style.SUCCESS("Created scoring configuration"))
        else:
            self.stdout.write("Using existing scoring configuration")

        # Display configuration
        self.stdout.write(f"\nScoring Configuration for {school.name}:")
        self.stdout.write(f"  Exam Score Weight: {config.exam_score_percentage}%")
        self.stdout.write(f"  Class Score Weight: {config.class_score_percentage}%")
        self.stdout.write(
            f"  Individual Assignment Weight: {config.individual_score_weight}%"
        )
        self.stdout.write(f"  Class Test Weight: {config.class_test_weight}%")
        self.stdout.write(f"  Project Weight: {config.project_weight}%")
        self.stdout.write(f"  Group Work Weight: {config.group_work_weight}%")
        self.stdout.write(f"  Max Exam Score: {config.max_exam_score}")
        self.stdout.write(f"  Max Class Score: {config.max_class_score}")

        return config

    def setup_grading_system(self, school):
        """Create default grading system."""
        grades = [
            ("A", 80, 100, "Excellent"),
            ("B", 70, 79, "Very Good"),
            ("C", 60, 69, "Good"),
            ("D", 50, 59, "Average"),
            ("E", 40, 49, "Poor"),
            ("F", 0, 39, "Fail"),
        ]

        created_count = 0
        for grade_letter, min_score, max_score, remarks in grades:
            grade, created = GradingSystem.objects.get_or_create(
                grade_letter=grade_letter,
                school=school,
                defaults={
                    "min_score": Decimal(str(min_score)),
                    "max_score": Decimal(str(max_score)),
                    "remarks": remarks,
                    "is_active": True,
                },
            )
            if created:
                created_count += 1

        if created_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f"Created {created_count} grading system entries")
            )
        else:
            self.stdout.write("Using existing grading system")

    def demonstrate_calculations(self, school, scoring_config):
        """Demonstrate score calculations with sample data."""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("ENHANCED SCORING CALCULATION DEMONSTRATION")
        self.stdout.write("=" * 60)

        # Sample component scores
        sample_scores = [
            {
                "student": "Demo Student 1",
                "individual": 85,
                "class_test": 78,
                "project": 92,
                "group_work": 88,
                "exam": 65,
            },
            {
                "student": "Demo Student 2",
                "individual": 72,
                "class_test": 85,
                "project": 80,
                "group_work": 75,
                "exam": 58,
            },
            {
                "student": "Demo Student 3",
                "individual": 95,
                "class_test": 90,
                "project": 88,
                "group_work": 93,
                "exam": 68,
            },
        ]

        for score_data in sample_scores:
            self.stdout.write(f'\nStudent: {score_data["student"]}')
            self.stdout.write("-" * 40)

            # Component scores
            individual = Decimal(str(score_data["individual"]))
            class_test = Decimal(str(score_data["class_test"]))
            project = Decimal(str(score_data["project"]))
            group_work = Decimal(str(score_data["group_work"]))
            exam = Decimal(str(score_data["exam"]))

            self.stdout.write(f"Component Scores:")
            self.stdout.write(
                f"  Individual Assignment: {individual}/100 (weight: {scoring_config.individual_score_weight}%)"
            )
            self.stdout.write(
                f"  Class Test: {class_test}/100 (weight: {scoring_config.class_test_weight}%)"
            )
            self.stdout.write(
                f"  Project: {project}/100 (weight: {scoring_config.project_weight}%)"
            )
            self.stdout.write(
                f"  Group Work: {group_work}/100 (weight: {scoring_config.group_work_weight}%)"
            )

            # Calculate class score using the same method as the model
            class_score = scoring_config.calculate_class_score(
                individual, class_test, project, group_work
            )

            self.stdout.write(
                f"\nCalculated Class Score: {class_score:.2f}/{scoring_config.max_class_score}"
            )

            # Calculate total score
            class_weighted = (
                class_score / scoring_config.max_class_score
            ) * scoring_config.class_score_percentage
            exam_weighted = (
                exam / scoring_config.max_exam_score
            ) * scoring_config.exam_score_percentage
            total_score = class_weighted + exam_weighted

            self.stdout.write(f"Exam Score: {exam}/{scoring_config.max_exam_score}")
            self.stdout.write(f"\nTotal Score Calculation:")
            self.stdout.write(
                f"  Class Score Weighted: ({class_score}/{scoring_config.max_class_score}) × {scoring_config.class_score_percentage}% = {class_weighted:.2f}"
            )
            self.stdout.write(
                f"  Exam Score Weighted: ({exam}/{scoring_config.max_exam_score}) × {scoring_config.exam_score_percentage}% = {exam_weighted:.2f}"
            )
            self.stdout.write(
                f"  Total Score: {class_weighted:.2f} + {exam_weighted:.2f} = {total_score:.2f}/100"
            )

            # Get grade
            grade_info = GradingSystem.get_grade_for_score(total_score, school)
            if grade_info:
                self.stdout.write(
                    f"  Grade: {grade_info.grade_letter} ({grade_info.remarks})"
                )
            else:
                self.stdout.write(f"  Grade: Not available")

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("This demonstrates how the enhanced scoring system")
        self.stdout.write("calculates scores from individual components using")
        self.stdout.write("configurable weights and percentages.")
        self.stdout.write("=" * 60)
