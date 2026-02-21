"""
Management command to analyze what happens when an academic year is deleted.
"""

from django.core.management.base import BaseCommand
from django.db import models
from shs_system.models import (
    AcademicYear,
    Term,
    Class,
    ClassSubject,
    TeacherSubjectAssignment,
    ClassTeacher,
    StudentClass,
    StudentTermRemarks,
    ReportCard,
    AcademicYearTemplate,
)


class Command(BaseCommand):
    help = "Analyze the impact of deleting an academic year"

    def add_arguments(self, parser):
        parser.add_argument(
            "--academic-year-id", type=int, help="Academic year ID to analyze"
        )
        parser.add_argument(
            "--list-years", action="store_true", help="List all academic years"
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without actually deleting",
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
            self.analyze_deletion_impact(academic_year, options.get("dry_run", False))
        except AcademicYear.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"Academic year with ID {academic_year_id} not found")
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))

    def list_academic_years(self):
        """List all academic years with their data counts"""
        self.stdout.write("Academic Years in System:")
        self.stdout.write("-" * 60)

        for ay in AcademicYear.objects.all().order_by("-start_date"):
            # Count related data
            terms_count = Term.objects.filter(academic_year=ay).count()
            classes_count = Class.objects.filter(academic_year=ay).count()

            class_subjects_count = ClassSubject.objects.filter(academic_year=ay, is_active=True).count()

            teacher_assignments_count = TeacherSubjectAssignment.objects.filter(
                academic_year=ay
            ).count()
            class_teachers_count = ClassTeacher.objects.filter(academic_year=ay).count()
            # StudentClass doesn't have academic_year field, get through assigned_class
            student_classes_count = StudentClass.objects.filter(
                assigned_class__academic_year=ay
            ).count()
            student_remarks_count = StudentTermRemarks.objects.filter(
                academic_year=ay
            ).count()
            report_cards_count = ReportCard.objects.filter(academic_year=ay).count()

            # Check if templates reference this academic year
            templates_count = AcademicYearTemplate.objects.filter(
                created_from_year=ay
            ).count()

            self.stdout.write(
                f"ID: {ay.id} | Name: {ay.name} | School: {ay.school.name}"
            )
            self.stdout.write(f"  Terms: {terms_count} | Classes: {classes_count}")
            self.stdout.write(
                f"  Class-Subjects: {class_subjects_count} | Teacher Assignments: {teacher_assignments_count}"
            )
            self.stdout.write(
                f"  Class Teachers: {class_teachers_count} | Student Classes: {student_classes_count}"
            )
            self.stdout.write(
                f"  Student Remarks: {student_remarks_count} | Report Cards: {report_cards_count}"
            )
            self.stdout.write(f"  Templates Created From: {templates_count}")
            self.stdout.write("")

    def analyze_deletion_impact(self, academic_year, dry_run=False):
        """Analyze what would be deleted if this academic year is removed"""
        self.stdout.write(f"Analyzing deletion impact for: {academic_year.name}")
        self.stdout.write("=" * 60)

        # Get all related data counts
        data_counts = {
            "Terms": Term.objects.filter(academic_year=academic_year).count(),
            "Classes": Class.objects.filter(academic_year=academic_year).count(),
            "Class-Subject Assignments": ClassSubject.objects.filter(
                academic_year=academic_year
            ).count(),
            "Teacher Subject Assignments": TeacherSubjectAssignment.objects.filter(
                academic_year=academic_year
            ).count(),
            "Class Teacher Assignments": ClassTeacher.objects.filter(
                academic_year=academic_year
            ).count(),
            "Student Class Assignments": StudentClass.objects.filter(
                assigned_class__academic_year=academic_year
            ).count(),
            "Student Term Remarks": StudentTermRemarks.objects.filter(
                academic_year=academic_year
            ).count(),
            "Report Cards": ReportCard.objects.filter(
                academic_year=academic_year
            ).count(),
        }

        # Check templates that reference this academic year
        templates_referencing = AcademicYearTemplate.objects.filter(
            created_from_year=academic_year
        )
        templates_count = templates_referencing.count()

        # Display impact analysis
        self.stdout.write("📊 DATA THAT WOULD BE DELETED:")
        self.stdout.write("-" * 40)

        total_records = 0
        for model_name, count in data_counts.items():
            if count > 0:
                self.stdout.write(f"  ❌ {model_name}: {count} records")
                total_records += count
            else:
                self.stdout.write(f"  ✅ {model_name}: {count} records")

        self.stdout.write(f"\n📈 TOTAL RECORDS TO BE DELETED: {total_records}")

        # Template impact
        self.stdout.write("\n🎯 TEMPLATE IMPACT:")
        self.stdout.write("-" * 20)
        if templates_count > 0:
            self.stdout.write(
                f"  ⚠️  {templates_count} templates were created from this academic year"
            )
            self.stdout.write(
                "  ⚠️  Templates will have 'created_from_year' set to NULL"
            )
            self.stdout.write("  ✅ Templates themselves will NOT be deleted")
            for template in templates_referencing:
                self.stdout.write(f"    - {template.name} (ID: {template.id})")
        else:
            self.stdout.write("  ✅ No templates reference this academic year")

        # Cascade effects
        self.stdout.write("\n🔄 CASCADE EFFECTS:")
        self.stdout.write("-" * 20)

        if data_counts["Classes"] > 0:
            self.stdout.write("  ❌ All classes in this academic year will be deleted")
            self.stdout.write(
                "  ❌ All student enrollments in these classes will be deleted"
            )
            self.stdout.write(
                "  ❌ All teacher assignments to these classes will be deleted"
            )

        if data_counts["Terms"] > 0:
            self.stdout.write("  ❌ All terms in this academic year will be deleted")
            self.stdout.write(
                "  ❌ All assessments and grades for these terms will be deleted"
            )
            self.stdout.write(
                "  ❌ All attendance records for these terms will be deleted"
            )

        # Safety recommendations
        self.stdout.write("\n⚠️  SAFETY RECOMMENDATIONS:")
        self.stdout.write("-" * 30)

        if total_records > 0:
            self.stdout.write(
                "  🚨 HIGH IMPACT: This academic year has significant data"
            )
            self.stdout.write("  💾 RECOMMENDATION: Create a backup before deletion")
            self.stdout.write("  📋 RECOMMENDATION: Export important data first")

            if data_counts["Report Cards"] > 0:
                self.stdout.write(
                    "  📊 WARNING: Report cards will be permanently deleted"
                )
            if data_counts["Student Class Assignments"] > 0:
                self.stdout.write(
                    "  👥 WARNING: Student enrollment records will be deleted"
                )
        else:
            self.stdout.write("  ✅ LOW IMPACT: This academic year has minimal data")
            self.stdout.write("  ✅ SAFE TO DELETE: No significant data loss expected")

        # Current academic year check
        if academic_year.is_current:
            self.stdout.write("\n🚨 CRITICAL WARNING:")
            self.stdout.write("  ⚠️  This is the CURRENT academic year!")
            self.stdout.write("  ⚠️  Deleting it may cause system issues")
            self.stdout.write(
                "  💡 RECOMMENDATION: Set another academic year as current first"
            )

        # Dry run vs actual deletion
        if dry_run:
            self.stdout.write(f"\n🔍 DRY RUN: No actual deletion performed")
            self.stdout.write("  Use without --dry-run to actually delete")
        else:
            self.stdout.write(f"\n⚠️  ACTUAL DELETION:")
            self.stdout.write(
                "  This will permanently delete all the data listed above"
            )
            self.stdout.write("  This action cannot be undone!")

            # Ask for confirmation
            confirm = input(
                "\nAre you sure you want to delete this academic year? (yes/no): "
            )
            if confirm.lower() == "yes":
                try:
                    academic_year.delete()
                    self.stdout.write(
                        self.style.SUCCESS("Academic year deleted successfully!")
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"Error deleting academic year: {str(e)}")
                    )
            else:
                self.stdout.write("Deletion cancelled.")
