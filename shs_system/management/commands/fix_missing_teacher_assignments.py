"""
Management command to fix missing teacher assignments.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from shs_system.models import (
    AcademicYear,
    Class,
    ClassSubject,
    TeacherSubjectAssignment,
    Teacher,
    Subject,
)

User = get_user_model()


class Command(BaseCommand):
    help = "Fix missing teacher assignments for subjects"

    def add_arguments(self, parser):
        parser.add_argument(
            "--academic-year-id", type=int, help="Academic year ID to fix"
        )
        parser.add_argument(
            "--list-issues", action="store_true", help="List subjects without teachers"
        )
        parser.add_argument(
            "--auto-assign",
            action="store_true",
            help="Auto-assign teachers to subjects",
        )

    def handle(self, *args, **options):
        if options["list_issues"]:
            self.list_missing_assignments()
            return

        academic_year_id = options.get("academic_year_id")
        if not academic_year_id:
            self.stdout.write(self.style.ERROR("Please provide --academic-year-id"))
            return

        try:
            academic_year = AcademicYear.objects.get(id=academic_year_id)
            self.stdout.write(
                f"Fixing teacher assignments for academic year: {academic_year.name}"
            )

            # Find subjects without teachers
            missing_assignments = self.find_missing_assignments(academic_year)

            if not missing_assignments:
                self.stdout.write(
                    self.style.SUCCESS("No missing teacher assignments found!")
                )
                return

            self.stdout.write(
                f"Found {len(missing_assignments)} subjects without teachers:"
            )
            for assignment in missing_assignments:
                self.stdout.write(
                    f"  - {assignment['subject_name']} in {assignment['class_name']}"
                )

            if options["auto_assign"]:
                self.auto_assign_teachers(academic_year, missing_assignments)
            else:
                self.stdout.write(
                    self.style.WARNING(
                        "Use --auto-assign to automatically assign teachers to these subjects"
                    )
                )

        except AcademicYear.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"Academic year with ID {academic_year_id} not found")
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))

    def list_missing_assignments(self):
        """List all academic years with missing teacher assignments"""
        self.stdout.write("Academic Years with Missing Teacher Assignments:")
        self.stdout.write("-" * 60)

        for ay in AcademicYear.objects.all().order_by("-start_date"):
            missing_assignments = self.find_missing_assignments(ay)
            if missing_assignments:
                self.stdout.write(
                    f"ID: {ay.id} | Name: {ay.name} | School: {ay.school.name}"
                )
                self.stdout.write(f"  Missing assignments: {len(missing_assignments)}")
                for assignment in missing_assignments[:3]:  # Show first 3
                    self.stdout.write(
                        f"    - {assignment['subject_name']} in {assignment['class_name']}"
                    )
                if len(missing_assignments) > 3:
                    self.stdout.write(
                        f"    ... and {len(missing_assignments) - 3} more"
                    )
                self.stdout.write("")

    def find_missing_assignments(self, academic_year):
        """Find subjects without teacher assignments"""
        missing_assignments = []

        # Get all class-subject assignments
        class_subjects = ClassSubject.objects.filter(
            academic_year=academic_year, school=academic_year.school
        ).select_related("subject", "class_name")

        for cs in class_subjects:
            # Check if this subject has a teacher assignment
            has_teacher = TeacherSubjectAssignment.objects.filter(
                academic_year=academic_year,
                school=academic_year.school,
                subject=cs.subject,
                class_assigned=cs.class_name,
                is_active=True,
            ).exists()

            if not has_teacher:
                missing_assignments.append(
                    {
                        "class_name": cs.class_name.name,
                        "subject_name": cs.subject.subject_name,
                        "subject_id": cs.subject.id,
                        "class_id": cs.class_name.id,
                    }
                )

        return missing_assignments

    def auto_assign_teachers(self, academic_year, missing_assignments):
        """Auto-assign teachers to subjects without teachers"""
        # Get available teachers
        teachers = Teacher.objects.filter(school=academic_year.school)

        if not teachers.exists():
            self.stdout.write(self.style.ERROR("No teachers available for assignment"))
            return

        # Get the first available teacher (you can modify this logic)
        teacher = teachers.first()
        self.stdout.write(f"Using teacher: {teacher.full_name} (ID: {teacher.id})")

        assigned_count = 0
        for assignment in missing_assignments:
            try:
                # Get the class and subject objects
                from shs_system.models import Class, Subject

                class_obj = Class.objects.get(id=assignment["class_id"])
                subject = Subject.objects.get(id=assignment["subject_id"])

                # Create teacher assignment
                TeacherSubjectAssignment.objects.create(
                    teacher=teacher,
                    subject=subject,
                    class_assigned=class_obj,
                    academic_year=academic_year,
                    school=academic_year.school,
                    is_active=True,
                )

                self.stdout.write(
                    f"  ✓ Assigned {teacher.full_name} to {assignment['subject_name']} in {assignment['class_name']}"
                )
                assigned_count += 1

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"  ✗ Failed to assign {assignment['subject_name']}: {str(e)}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully assigned {assigned_count} teacher assignments"
            )
        )
