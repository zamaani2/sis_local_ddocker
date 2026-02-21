from django.core.management.base import BaseCommand
from shs_system.models import Student, StudentClass
from django.db.models import Count
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Fix student class assignments by ensuring students have an active class if they have any assignments"

    def handle(self, *args, **options):
        self.stdout.write("Starting to fix student class assignments...")

        # Get all students
        students = Student.objects.all()
        self.stdout.write(f"Found {students.count()} students")

        fixed_count = 0
        error_count = 0

        for student in students:
            try:
                # Get all class assignments for this student
                assignments = StudentClass.objects.filter(student=student)

                # If student has assignments but none are active, activate the most recent one
                if (
                    assignments.exists()
                    and not assignments.filter(is_active=True).exists()
                ):
                    # Get the most recent assignment
                    most_recent = assignments.order_by("-date_assigned").first()
                    most_recent.is_active = True
                    most_recent.save()

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Fixed student {student.full_name} - activated class: {most_recent.assigned_class.name}"
                        )
                    )
                    fixed_count += 1

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"Error fixing student {student.full_name}: {str(e)}"
                    )
                )
                error_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Fixed {fixed_count} out of {students.count()} students with class assignment issues"
            )
        )

        if error_count > 0:
            self.stdout.write(
                self.style.WARNING(f"Encountered errors with {error_count} students")
            )
