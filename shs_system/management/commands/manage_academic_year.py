"""
Management command for academic year management with archiving and deletion options.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
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

User = get_user_model()


class Command(BaseCommand):
    help = "Manage academic years with archiving and deletion options"

    def add_arguments(self, parser):
        parser.add_argument(
            "--academic-year-id", type=int, help="Academic year ID to manage"
        )
        parser.add_argument(
            "--list-years", action="store_true", help="List all academic years"
        )
        parser.add_argument(
            "--archive", action="store_true", help="Archive the academic year"
        )
        parser.add_argument(
            "--unarchive", action="store_true", help="Unarchive the academic year"
        )
        parser.add_argument(
            "--delete", action="store_true", help="Permanently delete the academic year"
        )
        parser.add_argument(
            "--analyze", action="store_true", help="Analyze deletion impact"
        )
        parser.add_argument(
            "--user-id", type=int, help="User ID for archiving (optional)"
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

            if options["analyze"]:
                self.analyze_deletion_impact(academic_year)
            elif options["archive"]:
                self.archive_academic_year(academic_year, options.get("user_id"))
            elif options["unarchive"]:
                self.unarchive_academic_year(academic_year)
            elif options["delete"]:
                self.delete_academic_year(academic_year)
            else:
                self.show_academic_year_options(academic_year)

        except AcademicYear.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"Academic year with ID {academic_year_id} not found")
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))

    def list_academic_years(self):
        """List all academic years with their status"""
        self.stdout.write("Academic Years in System:")
        self.stdout.write("=" * 80)

        # Active academic years
        active_years = AcademicYear.objects.filter(is_archived=False).order_by(
            "-start_date"
        )
        self.stdout.write(f"\n📋 ACTIVE ACADEMIC YEARS ({active_years.count()}):")
        self.stdout.write("-" * 50)

        for ay in active_years:
            status = "🟢 CURRENT" if ay.is_current else "⚪ Active"
            self.stdout.write(f"ID: {ay.id} | {ay.name} | {status}")
            self.stdout.write(f"  School: {ay.school.name}")
            self.stdout.write(f"  Period: {ay.start_date} to {ay.end_date}")
            self.stdout.write("")

        # Archived academic years
        archived_years = AcademicYear.objects.filter(is_archived=True).order_by(
            "-archived_at"
        )
        self.stdout.write(f"\n📦 ARCHIVED ACADEMIC YEARS ({archived_years.count()}):")
        self.stdout.write("-" * 50)

        for ay in archived_years:
            archived_by = ay.archived_by.full_name if ay.archived_by else "Unknown"
            archived_date = (
                ay.archived_at.strftime("%Y-%m-%d %H:%M")
                if ay.archived_at
                else "Unknown"
            )
            self.stdout.write(f"ID: {ay.id} | {ay.name} | 🔒 Archived")
            self.stdout.write(f"  School: {ay.school.name}")
            self.stdout.write(f"  Archived: {archived_date} by {archived_by}")
            self.stdout.write("")

    def show_academic_year_options(self, academic_year):
        """Show available options for an academic year"""
        self.stdout.write(f"\n🎯 ACADEMIC YEAR: {academic_year.name}")
        self.stdout.write("=" * 50)

        # Show current status
        if academic_year.is_archived:
            self.stdout.write("Status: 🔒 ARCHIVED")
            self.stdout.write(f"Archived: {academic_year.get_archive_status()}")
        else:
            status = "🟢 CURRENT" if academic_year.is_current else "⚪ ACTIVE"
            self.stdout.write(f"Status: {status}")

        # Show data counts
        self.stdout.write(f"\n📊 DATA SUMMARY:")
        terms_count = Term.objects.filter(academic_year=academic_year).count()
        classes_count = Class.objects.filter(academic_year=academic_year).count()
        student_classes_count = StudentClass.objects.filter(
            assigned_class__academic_year=academic_year
        ).count()
        report_cards_count = ReportCard.objects.filter(
            academic_year=academic_year
        ).count()
        templates_count = AcademicYearTemplate.objects.filter(
            created_from_year=academic_year
        ).count()

        self.stdout.write(f"  Terms: {terms_count}")
        self.stdout.write(f"  Classes: {classes_count}")
        self.stdout.write(f"  Student Enrollments: {student_classes_count}")
        self.stdout.write(f"  Report Cards: {report_cards_count}")
        self.stdout.write(f"  Templates Created From: {templates_count}")

        # Show available actions
        self.stdout.write(f"\n🛠️  AVAILABLE ACTIONS:")
        if academic_year.is_archived:
            self.stdout.write("  --unarchive    Unarchive this academic year")
        else:
            self.stdout.write("  --archive      Archive this academic year (safe)")
            if not academic_year.is_current:
                self.stdout.write("  --delete       Permanently delete (DANGEROUS)")
            else:
                self.stdout.write("  ⚠️  Cannot delete current academic year")

        self.stdout.write("  --analyze      Analyze deletion impact")

    def archive_academic_year(self, academic_year, user_id=None):
        """Archive an academic year"""
        if academic_year.is_archived:
            self.stdout.write(self.style.WARNING("Academic year is already archived"))
            return

        # Get user if provided
        user = None
        if user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(
                        f"User with ID {user_id} not found, proceeding without user info"
                    )
                )

        # Show what will happen
        self.stdout.write(f"\n📦 ARCHIVING ACADEMIC YEAR: {academic_year.name}")
        self.stdout.write("-" * 50)

        # Count data that will be preserved
        terms_count = Term.objects.filter(academic_year=academic_year).count()
        classes_count = Class.objects.filter(academic_year=academic_year).count()
        student_classes_count = StudentClass.objects.filter(
            assigned_class__academic_year=academic_year
        ).count()
        report_cards_count = ReportCard.objects.filter(
            academic_year=academic_year
        ).count()

        self.stdout.write("✅ DATA THAT WILL BE PRESERVED:")
        self.stdout.write(f"  📚 {terms_count} terms")
        self.stdout.write(f"  🏫 {classes_count} classes")
        self.stdout.write(f"  👥 {student_classes_count} student enrollments")
        self.stdout.write(f"  📊 {report_cards_count} report cards")
        self.stdout.write(f"  🎯 All assessments, grades, and attendance records")

        self.stdout.write("\n🔒 ARCHIVING EFFECTS:")
        self.stdout.write("  ✅ All data is preserved")
        self.stdout.write("  ✅ Can be unarchived later")
        self.stdout.write("  ✅ Hidden from active lists")
        self.stdout.write("  ✅ Cannot be set as current")
        self.stdout.write("  ✅ Templates remain functional")

        # Confirm archiving
        confirm = input("\nArchive this academic year? (yes/no): ")
        if confirm.lower() == "yes":
            try:
                academic_year.archive(user=user)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ Academic year '{academic_year.name}' archived successfully!"
                    )
                )
                self.stdout.write("💡 Use --unarchive to restore it later")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error archiving: {str(e)}"))
        else:
            self.stdout.write("Archive cancelled.")

    def unarchive_academic_year(self, academic_year):
        """Unarchive an academic year"""
        if not academic_year.is_archived:
            self.stdout.write(self.style.WARNING("Academic year is not archived"))
            return

        self.stdout.write(f"\n📦 UNARCHIVING ACADEMIC YEAR: {academic_year.name}")
        self.stdout.write("-" * 50)

        self.stdout.write("✅ UNARCHIVING EFFECTS:")
        self.stdout.write("  ✅ Academic year becomes active again")
        self.stdout.write("  ✅ All data remains intact")
        self.stdout.write("  ✅ Can be set as current")
        self.stdout.write("  ✅ Appears in active lists")
        self.stdout.write("  ✅ Templates remain functional")

        # Confirm unarchiving
        confirm = input("\nUnarchive this academic year? (yes/no): ")
        if confirm.lower() == "yes":
            try:
                academic_year.unarchive()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ Academic year '{academic_year.name}' unarchived successfully!"
                    )
                )
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error unarchiving: {str(e)}"))
        else:
            self.stdout.write("Unarchive cancelled.")

    def delete_academic_year(self, academic_year):
        """Permanently delete an academic year"""
        if academic_year.is_current:
            self.stdout.write(
                self.style.ERROR("❌ Cannot delete current academic year!")
            )
            self.stdout.write("💡 Set another academic year as current first")
            return

        self.stdout.write(
            f"\n🗑️  PERMANENTLY DELETING ACADEMIC YEAR: {academic_year.name}"
        )
        self.stdout.write("=" * 60)

        # Analyze impact
        self.analyze_deletion_impact(academic_year, show_warnings=True)

        self.stdout.write("\n🚨 FINAL WARNING:")
        self.stdout.write("  ❌ This action CANNOT be undone!")
        self.stdout.write("  ❌ All data will be permanently lost!")
        self.stdout.write("  ❌ Templates will lose their reference!")

        # Double confirmation
        confirm1 = input(
            "\nAre you ABSOLUTELY SURE you want to permanently delete this academic year? (yes/no): "
        )
        if confirm1.lower() != "yes":
            self.stdout.write("Deletion cancelled.")
            return

        confirm2 = input("Type 'DELETE' to confirm permanent deletion: ")
        if confirm2 != "DELETE":
            self.stdout.write("Deletion cancelled.")
            return

        try:
            academic_year.delete()
            self.stdout.write(
                self.style.SUCCESS("✅ Academic year permanently deleted!")
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error deleting: {str(e)}"))

    def analyze_deletion_impact(self, academic_year, show_warnings=False):
        """Analyze what would be deleted"""
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

        templates_count = AcademicYearTemplate.objects.filter(
            created_from_year=academic_year
        ).count()

        if show_warnings:
            self.stdout.write("\n📊 DATA THAT WOULD BE DELETED:")
            self.stdout.write("-" * 40)

            total_records = 0
            for model_name, count in data_counts.items():
                if count > 0:
                    self.stdout.write(f"  ❌ {model_name}: {count} records")
                    total_records += count
                else:
                    self.stdout.write(f"  ✅ {model_name}: {count} records")

            self.stdout.write(f"\n📈 TOTAL RECORDS TO BE DELETED: {total_records}")

            if templates_count > 0:
                self.stdout.write(f"\n🎯 TEMPLATE IMPACT:")
                self.stdout.write(
                    f"  ⚠️  {templates_count} templates will lose their reference"
                )
                self.stdout.write("  ✅ Templates themselves will NOT be deleted")

            if academic_year.is_current:
                self.stdout.write(f"\n🚨 CRITICAL WARNING:")
                self.stdout.write("  ⚠️  This is the CURRENT academic year!")
                self.stdout.write("  ⚠️  Deleting it may cause system issues!")
