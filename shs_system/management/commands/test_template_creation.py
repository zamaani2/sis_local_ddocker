
"""
Management command to test template creation and debug issues.
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
from shs_system.utils.template_utils import create_template_from_academic_year

User = get_user_model()


class Command(BaseCommand):
    help = "Test template creation and debug issues"

    def add_arguments(self, parser):
        parser.add_argument(
            "--academic-year-id", type=int, help="Academic year ID to test"
        )
        parser.add_argument(
            "--template-name", type=str, default="Test Template", help="Template name"
        )
        parser.add_argument(
            "--list-years", action="store_true", help="List available academic years"
        )

    def handle(self, *args, **options):
        if options["list_years"]:
            self.list_academic_years()
            return

        academic_year_id = options.get("academic_year_id")
        if not academic_year_id:
            self.stdout.write(self.style.ERROR("Please provide --academic-year-id"))
            return

        try:
            academic_year = AcademicYear.objects.get(id=academic_year_id)
            self.stdout.write(
                f"Testing template creation for academic year: {academic_year.name}"
            )

            # Check data availability
            classes_count = Class.objects.filter(academic_year=academic_year).count()
            class_subjects_count = ClassSubject.objects.filter(
                academic_year=academic_year, is_active=True
            ).count()
            teacher_assignments_count = TeacherSubjectAssignment.objects.filter(
                academic_year=academic_year
            ).count()
            class_teachers_count = ClassTeacher.objects.filter(
                academic_year=academic_year
            ).count()

            self.stdout.write(f"Classes: {classes_count}")
            self.stdout.write(f"Subject Assignments: {class_subjects_count}")
            self.stdout.write(f"Teacher Assignments: {teacher_assignments_count}")
            self.stdout.write(f"Class Teachers: {class_teachers_count}")

            if classes_count == 0:
                self.stdout.write(
                    self.style.ERROR("No classes found in this academic year")
                )
                return

            # Try to create template
            try:
                template = create_template_from_academic_year(
                    academic_year=academic_year,
                    template_name=options["template_name"],
                    description="Test template created via management command",
                    created_by=None,
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f'Template "{template.name}" created successfully with ID {template.id}'
                    )
                )

                # Show template statistics
                from shs_system.utils.template_utils import get_template_statistics

                stats = get_template_statistics(template)

                self.stdout.write(f"Template Statistics:")
                self.stdout.write(f"  Classes: {stats['total_classes']}")
                self.stdout.write(f"  Subjects: {stats['total_subjects']}")
                self.stdout.write(f"  Teachers: {stats['total_teachers']}")
                self.stdout.write(
                    f"  Subject Assignments: {stats['total_subject_assignments']}"
                )
                self.stdout.write(
                    f"  Teacher Assignments: {stats['total_teacher_assignments']}"
                )
                self.stdout.write(f"  Class Teachers: {stats['total_class_teachers']}")

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error creating template: {str(e)}")
                )
                import traceback

                self.stdout.write(traceback.format_exc())

        except AcademicYear.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"Academic year with ID {academic_year_id} not found")
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))

    def list_academic_years(self):
        """List all academic years with their data counts"""
        self.stdout.write("Available Academic Years:")
        self.stdout.write("-" * 50)

        for ay in AcademicYear.objects.all().order_by("-start_date"):
            classes_count = Class.objects.filter(academic_year=ay).count()
            class_subjects_count = ClassSubject.objects.filter(academic_year=ay, is_active=True).count()
            teacher_assignments_count = TeacherSubjectAssignment.objects.filter(
                academic_year=ay
            ).count()
            class_teachers_count = ClassTeacher.objects.filter(academic_year=ay).count()

            self.stdout.write(
                f"ID: {ay.id} | Name: {ay.name} | School: {ay.school.name}"
            )
            self.stdout.write(
                f"  Classes: {classes_count} | Subjects: {class_subjects_count} | Teachers: {teacher_assignments_count} | Class Teachers: {class_teachers_count}"
            )
            self.stdout.write("")

