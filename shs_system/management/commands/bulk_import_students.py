"""
Management command for bulk importing students from CSV files.
This command is useful for very large datasets that might timeout in the web interface.

Usage:
python manage.py bulk_import_students --csv-file path/to/students.csv --school-id 1 --class-id 2
"""

import csv
import logging
from datetime import datetime as dt
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.conf import settings
from shs_system.models import Student, School, Class, Form, LearningArea, StudentClass
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Bulk import students from CSV file"

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-file",
            type=str,
            required=True,
            help="Path to the CSV file containing student data",
        )
        parser.add_argument(
            "--school-id",
            type=int,
            required=True,
            help="ID of the school to import students to",
        )
        parser.add_argument(
            "--class-id",
            type=int,
            required=False,
            help="ID of the class to assign all students to (optional)",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=getattr(settings, "BULK_OPERATION_BATCH_SIZE", 100),
            help="Number of records to process in each batch",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Perform a dry run without actually importing data",
        )

    def handle(self, *args, **options):
        csv_file_path = options["csv_file"]
        school_id = options["school_id"]
        class_id = options["class_id"]
        batch_size = options["batch_size"]
        dry_run = options["dry_run"]

        # Validate school
        try:
            school = School.objects.get(id=school_id)
            self.stdout.write(f"Importing to school: {school.name}")
        except School.DoesNotExist:
            raise CommandError(f"School with ID {school_id} does not exist")

        # Validate class if provided
        assign_class = None
        if class_id:
            try:
                assign_class = Class.objects.get(id=class_id, school=school)
                self.stdout.write(f"Will assign students to class: {assign_class.name}")
            except Class.DoesNotExist:
                raise CommandError(
                    f"Class with ID {class_id} does not exist in school {school.name}"
                )

        # Load CSV file
        try:
            with open(csv_file_path, "r", encoding="utf-8") as file:
                csv_reader = csv.DictReader(file)
                rows = list(csv_reader)

            if not rows:
                raise CommandError("CSV file is empty or invalid")

            self.stdout.write(f"Found {len(rows)} records in CSV file")

        except FileNotFoundError:
            raise CommandError(f"CSV file not found: {csv_file_path}")
        except Exception as e:
            raise CommandError(f"Error reading CSV file: {str(e)}")

        # Get available forms and learning areas for validation
        forms_by_number = {
            form.form_number: form for form in Form.objects.filter(school=school)
        }
        learning_areas_by_name = {
            area.name.lower(): area
            for area in LearningArea.objects.filter(school=school)
        }

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No data will be imported")
            )

        imported_count = 0
        failed_count = 0
        errors = []

        # Process in batches
        for batch_start in range(0, len(rows), batch_size):
            batch_end = min(batch_start + batch_size, len(rows))
            batch_rows = rows[batch_start:batch_end]

            self.stdout.write(
                f"Processing batch {batch_start//batch_size + 1}: rows {batch_start + 1}-{batch_end}"
            )

            students_to_create = []

            # Process each row in the batch
            for row_index, row in enumerate(batch_rows, start=batch_start + 1):
                try:
                    # Extract required fields
                    full_name = row.get("full_name", "").strip()
                    date_of_birth_str = row.get("date_of_birth", "").strip()
                    gender = row.get("gender", "").strip().upper()
                    admission_date_str = row.get("admission_date", "").strip()

                    # Validate required fields
                    if not all(
                        [full_name, date_of_birth_str, gender, admission_date_str]
                    ):
                        raise ValueError(
                            "Missing required fields: full_name, date_of_birth, gender, admission_date"
                        )

                    # Parse dates
                    date_of_birth = None
                    admission_date = None

                    for date_format in ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"]:
                        try:
                            date_of_birth = dt.strptime(
                                date_of_birth_str, date_format
                            ).date()
                            break
                        except ValueError:
                            continue
                    else:
                        raise ValueError(
                            f"Invalid date_of_birth format: {date_of_birth_str}"
                        )

                    for date_format in ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"]:
                        try:
                            admission_date = dt.strptime(
                                admission_date_str, date_format
                            ).date()
                            break
                        except ValueError:
                            continue
                    else:
                        raise ValueError(
                            f"Invalid admission_date format: {admission_date_str}"
                        )

                    # Validate gender
                    if gender not in ["M", "F", "MALE", "FEMALE"]:
                        raise ValueError(
                            f"Invalid gender: {gender}. Use M/F or Male/Female"
                        )
                    gender = "M" if gender in ["M", "MALE"] else "F"

                     # Create student object
                     student = Student(
                         full_name=full_name,
                         date_of_birth=date_of_birth,
                         gender=gender,
                         admission_date=admission_date,
                         parent_contact=row.get("parent_contact", "").strip(),
                         email=row.get("email", "").strip(),
                         school=school,
                     )

                     # Set form if provided
                     form_str = row.get("form", "").strip()
                     if form_str:
                         try:
                             form_number = int(form_str)
                             if form_number in forms_by_number:
                                 student.form = forms_by_number[form_number]
                         except (ValueError, TypeError):
                             self.stdout.write(
                                 self.style.WARNING(
                                     f"Row {row_index}: Invalid form number: {form_str}"
                                 )
                             )

                     # Set learning area if provided
                     learning_area_str = row.get("learning_area", "").strip().lower()
                     if (
                         learning_area_str
                         and learning_area_str in learning_areas_by_name
                     ):
                         student.learning_area = learning_areas_by_name[
                             learning_area_str
                         ]

                     # Mark to skip email sending during bulk import (but keep user creation)
                     student._skip_email = True

                     # Validate the student data
                     student.full_clean()

                     # Add to batch for creation
                     students_to_create.append(student)

                except Exception as e:
                    failed_count += 1
                    error_msg = f"Row {row_index}: {str(e)}"
                    errors.append(error_msg)
                    self.stdout.write(self.style.ERROR(error_msg))

            # Bulk create students in this batch
            if students_to_create and not dry_run:
                try:
                    with transaction.atomic():
                        # Use bulk_create for better performance
                        created_students = Student.objects.bulk_create(
                            students_to_create, batch_size=50, ignore_conflicts=False
                        )

                        batch_imported_count = len(created_students)
                        imported_count += batch_imported_count

                        # Create class assignments if needed
                        if assign_class and created_students:
                            student_names = [s.full_name for s in students_to_create]
                            created_student_objects = Student.objects.filter(
                                full_name__in=student_names, school=school
                            ).order_by("-id")[:batch_imported_count]

                            student_class_assignments = [
                                StudentClass(
                                    student=student,
                                    assigned_class=assign_class,
                                    assigned_by=None,  # No user in management command
                                    school=school,
                                )
                                for student in created_student_objects
                            ]

                            StudentClass.objects.bulk_create(
                                student_class_assignments,
                                batch_size=50,
                                ignore_conflicts=True,
                            )

                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Successfully imported batch of {batch_imported_count} students"
                            )
                        )

                except Exception as batch_error:
                    self.stdout.write(
                        self.style.ERROR(f"Batch creation failed: {str(batch_error)}")
                    )
                    # Try individual creation for this batch
                    for student in students_to_create:
                        try:
                            with transaction.atomic():
                                # Ensure email skipping flag is set for individual saves too
                                student._skip_email = True
                                student.save()

                                # Assign to class if specified
                                if assign_class:
                                    StudentClass.objects.create(
                                        student=student,
                                        assigned_class=assign_class,
                                        assigned_by=None,
                                        school=school,
                                    )

                                imported_count += 1

                        except Exception as individual_error:
                            failed_count += 1
                            error_msg = (
                                f"Student {student.full_name}: {str(individual_error)}"
                            )
                            errors.append(error_msg)
                            self.stdout.write(self.style.ERROR(error_msg))

            elif dry_run and students_to_create:
                self.stdout.write(
                    f"Would import {len(students_to_create)} students in this batch"
                )
                imported_count += len(students_to_create)

        # Final summary
        self.stdout.write("\n" + "=" * 50)
        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"DRY RUN COMPLETE"))
            self.stdout.write(f"Would import: {imported_count} students")
        else:
            self.stdout.write(self.style.SUCCESS(f"IMPORT COMPLETE"))
            self.stdout.write(f"Successfully imported: {imported_count} students")

        if failed_count > 0:
            self.stdout.write(
                self.style.WARNING(f"Failed to import: {failed_count} students")
            )

        if errors:
            self.stdout.write(f"\nFirst 10 errors:")
            for error in errors[:10]:
                self.stdout.write(self.style.ERROR(f"  {error}"))

            if len(errors) > 10:
                self.stdout.write(f"... and {len(errors) - 10} more errors")
