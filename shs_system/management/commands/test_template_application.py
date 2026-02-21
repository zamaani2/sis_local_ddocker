"""
Management command to test template application.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from shs_system.models import (
    AcademicYear,
    AcademicYearTemplate,
    Class,
    ClassSubject,
    TeacherSubjectAssignment,
    ClassTeacher,
)
from shs_system.utils.template_utils import apply_template_to_academic_year

User = get_user_model()


class Command(BaseCommand):
    help = "Test template application to create new academic year"

    def add_arguments(self, parser):
        parser.add_argument("--template-id", type=int, help="Template ID to apply")
        parser.add_argument(
            "--list-templates", action="store_true", help="List available templates"
        )
        parser.add_argument(
            "--academic-year-name",
            type=str,
            default="Test Academic Year",
            help="Name for new academic year",
        )

    def handle(self, *args, **options):
        if options["list_templates"]:
            self.list_templates()
            return

        template_id = options.get("template_id")
        if not template_id:
            self.stdout.write(self.style.ERROR("Please provide --template-id"))
            return

        try:
            template = AcademicYearTemplate.objects.get(id=template_id)
            self.stdout.write(f"Testing template application for: {template.name}")

            # Create a test academic year
            academic_year = AcademicYear.objects.create(
                name=options["academic_year_name"],
                start_date="2025-09-01",
                end_date="2026-07-31",
                school=template.school,
                is_current=False,
            )

            self.stdout.write(f"Created test academic year: {academic_year.name}")

            # Apply template
            try:
                results = apply_template_to_academic_year(template, academic_year)

                self.stdout.write(self.style.SUCCESS("Template application completed!"))
                self.stdout.write(f"Results:")
                self.stdout.write(f"  Classes created: {results['classes_created']}")
                self.stdout.write(
                    f"  Subjects assigned: {results['subjects_assigned']}"
                )
                self.stdout.write(
                    f"  Teacher assignments created: {results['teacher_assignments_created']}"
                )
                self.stdout.write(
                    f"  Class teachers assigned: {results['class_teachers_assigned']}"
                )

                if results["warnings"]:
                    self.stdout.write(self.style.WARNING("Warnings:"))
                    for warning in results["warnings"]:
                        self.stdout.write(f"  - {warning}")

                if results["errors"]:
                    self.stdout.write(self.style.ERROR("Errors:"))
                    for error in results["errors"]:
                        self.stdout.write(f"  - {error}")

                # Clean up test academic year
                academic_year.delete()
                self.stdout.write("Test academic year deleted.")

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error applying template: {str(e)}")
                )
                import traceback

                self.stdout.write(traceback.format_exc())

                # Clean up test academic year
                academic_year.delete()
                self.stdout.write("Test academic year deleted.")

        except AcademicYearTemplate.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"Template with ID {template_id} not found")
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))

    def list_templates(self):
        """List all available templates"""
        self.stdout.write("Available Templates:")
        self.stdout.write("-" * 50)

        for template in AcademicYearTemplate.objects.filter(is_active=True).order_by(
            "-created_at"
        ):
            self.stdout.write(
                f"ID: {template.id} | Name: {template.name} | School: {template.school.name}"
            )

            # Get template statistics
            from shs_system.utils.template_utils import get_template_statistics

            stats = get_template_statistics(template)

            self.stdout.write(
                f"  Classes: {stats['total_classes']} | Subjects: {stats['total_subjects']} | Teachers: {stats['total_teachers']}"
            )
            self.stdout.write(
                f"  Subject Assignments: {stats['total_subject_assignments']} | Teacher Assignments: {stats['total_teacher_assignments']}"
            )
            self.stdout.write("")
