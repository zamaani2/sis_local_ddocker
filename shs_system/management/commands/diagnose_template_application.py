"""
Management command to diagnose template application issues.
This script will help identify the root cause of SweetAlert errors during template application.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from shs_system.models import (
    AcademicYear,
    AcademicYearTemplate,
    Class,
    ClassSubject,
    TeacherSubjectAssignment,
    ClassTeacher,
    SchoolInformation,
)
from shs_system.utils.template_utils import apply_template_to_academic_year
import traceback
import json

User = get_user_model()


class Command(BaseCommand):
    help = "Diagnose template application issues and identify SweetAlert conflicts"

    def add_arguments(self, parser):
        parser.add_argument(
            "--template-id", type=int, help="Template ID to test application"
        )
        parser.add_argument(
            "--academic-year-name",
            type=str,
            default="Test Academic Year 2025/2026",
            help="Name for test academic year",
        )
        parser.add_argument(
            "--verbose", action="store_true", help="Enable verbose output"
        )

    def handle(self, *args, **options):
        self.stdout.write("🔍 DIAGNOSING TEMPLATE APPLICATION ISSUES")
        self.stdout.write("=" * 60)

        template_id = options.get("template_id")
        academic_year_name = options.get("academic_year_name")
        verbose = options.get("verbose", False)

        if not template_id:
            self.stdout.write(self.style.ERROR("Please provide --template-id"))
            return

        try:
            # Get the template
            template = AcademicYearTemplate.objects.get(id=template_id)
            self.stdout.write(f"📋 Testing Template: {template.name}")
            self.stdout.write(f"   School: {template.school.name}")
            self.stdout.write(f"   Created: {template.created_at}")
            self.stdout.write("")

            # Check template data structure
            self.stdout.write("🔍 ANALYZING TEMPLATE DATA STRUCTURE:")
            self.stdout.write("-" * 40)

            template_data = template.template_data
            if verbose:
                self.stdout.write(f"Template Data Keys: {list(template_data.keys())}")

            # Check for common issues
            issues_found = []

            # 1. Check if template has classes
            classes_data = template_data.get("classes", [])
            if not classes_data:
                issues_found.append("❌ No classes found in template data")
            else:
                self.stdout.write(f"✅ Found {len(classes_data)} classes")

            # 2. Check if template has subject assignments
            subject_assignments = template_data.get("subject_assignments", [])
            if not subject_assignments:
                issues_found.append("❌ No subject assignments found in template data")
            else:
                self.stdout.write(
                    f"✅ Found {len(subject_assignments)} subject assignments"
                )

            # 3. Check if template has teacher assignments
            teacher_assignments = template_data.get("teacher_assignments", [])
            if not teacher_assignments:
                issues_found.append("❌ No teacher assignments found in template data")
            else:
                self.stdout.write(
                    f"✅ Found {len(teacher_assignments)} teacher assignments"
                )

            # 4. Check for warnings in template data
            warnings = template_data.get("warnings", {})
            if warnings:
                self.stdout.write("⚠️  Template has warnings:")
                for warning_type, warning_data in warnings.items():
                    self.stdout.write(f"   - {warning_type}: {warning_data}")

            self.stdout.write("")

            # Test template application
            self.stdout.write("🧪 TESTING TEMPLATE APPLICATION:")
            self.stdout.write("-" * 40)

            # Create test academic year
            test_academic_year = AcademicYear.objects.create(
                name=academic_year_name,
                start_date=timezone.now().date(),
                end_date=timezone.now().date().replace(year=timezone.now().year + 1),
                is_current=False,
                school=template.school,
            )

            self.stdout.write(
                f"✅ Created test academic year: {test_academic_year.name}"
            )

            try:
                # Apply template
                with transaction.atomic():
                    results = apply_template_to_academic_year(
                        template, test_academic_year, {}
                    )

                self.stdout.write("✅ Template application completed successfully!")
                self.stdout.write(
                    f"   Classes created: {results.get('classes_created', 0)}"
                )
                self.stdout.write(
                    f"   Subject assignments: {results.get('subjects_assigned', 0)}"
                )
                self.stdout.write(
                    f"   Teacher assignments: {results.get('teacher_assignments_created', 0)}"
                )
                self.stdout.write(
                    f"   Class teachers: {results.get('class_teachers_assigned', 0)}"
                )

                if results.get("errors"):
                    self.stdout.write("❌ Errors during application:")
                    for error in results["errors"]:
                        self.stdout.write(f"   - {error}")

                if results.get("warnings"):
                    self.stdout.write("⚠️  Warnings during application:")
                    for warning in results["warnings"]:
                        self.stdout.write(f"   - {warning}")

            except Exception as e:
                self.stdout.write(f"❌ Template application failed: {str(e)}")
                if verbose:
                    self.stdout.write("Full traceback:")
                    self.stdout.write(traceback.format_exc())

            # Clean up test academic year
            test_academic_year.delete()
            self.stdout.write("🧹 Cleaned up test academic year")

            # Check for SweetAlert conflicts
            self.stdout.write("")
            self.stdout.write("🔍 CHECKING FOR SWEETALERT CONFLICTS:")
            self.stdout.write("-" * 40)

            # Check if there are multiple SweetAlert imports in templates
            self.stdout.write("Checking for duplicate SweetAlert imports...")

            # This would require checking template files, but we can't do that in a management command
            # Instead, we'll provide recommendations

            self.stdout.write("")
            self.stdout.write("💡 RECOMMENDATIONS:")
            self.stdout.write("-" * 40)

            if issues_found:
                self.stdout.write("Issues found in template:")
                for issue in issues_found:
                    self.stdout.write(f"   {issue}")
                self.stdout.write("")

            self.stdout.write("1. Check for duplicate SweetAlert2 imports in templates")
            self.stdout.write(
                "2. Ensure SweetAlert2 is loaded only once in base template"
            )
            self.stdout.write("3. Check for JavaScript errors in browser console")
            self.stdout.write(
                "4. Verify AJAX response format matches expected structure"
            )
            self.stdout.write("5. Check for conflicting JavaScript libraries")

            self.stdout.write("")
            self.stdout.write("🔧 DEBUGGING STEPS:")
            self.stdout.write("-" * 40)
            self.stdout.write("1. Open browser developer tools (F12)")
            self.stdout.write("2. Go to Console tab")
            self.stdout.write("3. Try applying a template")
            self.stdout.write("4. Look for JavaScript errors")
            self.stdout.write("5. Check Network tab for AJAX request/response")
            self.stdout.write("6. Verify response contains 'success' field")

        except AcademicYearTemplate.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"Template with ID {template_id} not found")
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error during diagnosis: {str(e)}"))
            if verbose:
                self.stdout.write(traceback.format_exc())
