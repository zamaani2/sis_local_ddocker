"""
Utility functions for Academic Year Template system.
Handles template creation from existing academic years and application to new academic years.
"""

from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from ..models import (
    AcademicYear,
    Class,
    ClassSubject,
    TeacherSubjectAssignment,
    ClassTeacher,
    Form,
    LearningArea,
    Subject,
    Teacher,
    AcademicYearTemplate,
)

User = get_user_model()


def create_template_from_academic_year(
    academic_year, template_name, description="", created_by=None
):
    """
    Create a template from an existing academic year.

    Args:
        academic_year: AcademicYear instance to create template from
        template_name: Name for the new template
        description: Description for the template
        created_by: User who created the template

    Returns:
        AcademicYearTemplate instance
    """
    if not academic_year:
        raise ValueError("Academic year is required")

    if not academic_year.school:
        raise ValueError("Academic year must have a school")

    with transaction.atomic():
        # Extract class structures
        classes = Class.objects.filter(
            academic_year=academic_year, school=academic_year.school
        )
        class_structures = []

        print(f"Found {classes.count()} classes for academic year {academic_year.name}")

        for class_obj in classes:
            try:
                class_structure = {
                    "name": class_obj.name,
                    "form_id": class_obj.form.id if class_obj.form else None,
                    "learning_area_id": (
                        class_obj.learning_area.id if class_obj.learning_area else None
                    ),
                    "maximum_students": class_obj.maximum_students,
                    "class_prefix": extract_class_prefix(class_obj.name),
                }
                class_structures.append(class_structure)
            except Exception as e:
                print(f"Error processing class {class_obj.name}: {str(e)}")
                raise

        # Extract subject assignments
        class_subjects = ClassSubject.objects.filter(

            academic_year=academic_year, school=academic_year.school, is_active=True

        ).select_related("subject", "class_name")

        subject_assignments = []
        print(f"Found {class_subjects.count()} class-subject assignments")

        for cs in class_subjects:
            try:
                subject_assignment = {
                    "class_name": cs.class_name.name,
                    "subject_id": cs.subject.id,
                    "subject_name": cs.subject.subject_name,
                    "subject_code": cs.subject.subject_code,
                }
                subject_assignments.append(subject_assignment)
            except Exception as e:
                print(f"Error processing class-subject assignment: {str(e)}")
                raise

        # Extract teacher assignments
        teacher_assignments = TeacherSubjectAssignment.objects.filter(
            academic_year=academic_year, school=academic_year.school, is_active=True
        ).select_related("teacher", "subject", "class_assigned")

        teacher_assignments_data = []
        print(f"Found {teacher_assignments.count()} teacher assignments")

        for ta in teacher_assignments:
            try:
                teacher_assignment = {
                    "class_name": ta.class_assigned.name,
                    "subject_id": ta.subject.id,
                    "teacher_id": ta.teacher.id,
                    "teacher_name": ta.teacher.full_name,
                    "staff_id": ta.teacher.staff_id,
                }
                teacher_assignments_data.append(teacher_assignment)
            except Exception as e:
                print(f"Error processing teacher assignment: {str(e)}")
                # Continue processing other assignments instead of failing
                continue

        # Extract class teacher assignments
        class_teachers = ClassTeacher.objects.filter(
            academic_year=academic_year, school=academic_year.school, is_active=True
        ).select_related("teacher", "class_assigned")

        class_teacher_assignments = []
        print(f"Found {class_teachers.count()} class teacher assignments")

        for ct in class_teachers:
            try:
                class_teacher_assignment = {
                    "class_name": ct.class_assigned.name,
                    "teacher_id": ct.teacher.id,
                    "teacher_name": ct.teacher.full_name,
                    "staff_id": ct.teacher.staff_id,
                }
                class_teacher_assignments.append(class_teacher_assignment)
            except Exception as e:
                print(f"Error processing class teacher assignment: {str(e)}")
                # Continue processing other assignments instead of failing
                continue

        # Create template data structure
        template_data = {
            "class_structures": class_structures,
            "subject_assignments": subject_assignments,
            "teacher_assignments": teacher_assignments_data,
            "class_teacher_assignments": class_teacher_assignments,
            "created_from_year_name": academic_year.name,
            "created_from_year_id": academic_year.id,
        }

        # Print summary
        print(f"Template creation summary:")
        print(f"  Classes: {len(class_structures)}")
        print(f"  Subject assignments: {len(subject_assignments)}")
        print(f"  Teacher assignments: {len(teacher_assignments_data)}")
        print(f"  Class teacher assignments: {len(class_teacher_assignments)}")

        # Check for subjects without teachers
        subjects_without_teachers = []
        for subject_assignment in subject_assignments:
            class_name = subject_assignment["class_name"]
            subject_name = subject_assignment["subject_name"]

            # Check if this subject has a teacher assignment
            has_teacher = any(
                ta["class_name"] == class_name
                and ta["subject_id"] == subject_assignment["subject_id"]
                for ta in teacher_assignments_data
            )

            if not has_teacher:
                subjects_without_teachers.append(f"{subject_name} in {class_name}")

        if subjects_without_teachers:
            print(
                f"  Warning: Subjects without teachers: {', '.join(subjects_without_teachers)}"
            )
            template_data["warnings"] = {
                "subjects_without_teachers": subjects_without_teachers
            }

        # Create the template
        try:
            template = AcademicYearTemplate.objects.create(
                name=template_name,
                description=description,
                school=academic_year.school,
                created_from_year=academic_year,
                template_data=template_data,
                created_by=created_by,
            )
            print(
                f"Template '{template_name}' created successfully with ID {template.id}"
            )
            return template
        except Exception as e:
            print(f"Error creating template '{template_name}': {str(e)}")
            raise ValueError(f"Failed to create template: {str(e)}")


def apply_template_to_academic_year(template, academic_year, customizations=None):
    """
    Apply a template to create classes, subjects, and teacher assignments for a new academic year.

    Args:
        template: AcademicYearTemplate instance
        academic_year: AcademicYear instance to populate
        customizations: Dict with customizations (optional)

    Returns:
        Dict with creation results and statistics
    """
    if customizations is None:
        customizations = {}

    results = {
        "classes_created": 0,
        "subjects_assigned": 0,
        "teacher_assignments_created": 0,
        "class_teachers_assigned": 0,
        "errors": [],
        "warnings": [],
    }

    with transaction.atomic():
        try:
            # Create classes from template
            class_structures = template.get_class_structures()
            class_name_mapping = {}  # Map template class names to new class IDs

            for class_structure in class_structures:
                try:
                    # Apply customizations if provided
                    class_name = apply_class_name_customization(
                        class_structure["name"], customizations
                    )

                    # Get form and learning area
                    form = None
                    learning_area = None

                    if class_structure.get("form_id"):
                        form = Form.objects.get(
                            id=class_structure["form_id"], school=academic_year.school
                        )

                    if class_structure.get("learning_area_id"):
                        learning_area = LearningArea.objects.get(
                            id=class_structure["learning_area_id"],
                            school=academic_year.school,
                        )

                    # Create the class
                    new_class = Class.objects.create(
                        name=class_name,
                        form=form,
                        learning_area=learning_area,
                        academic_year=academic_year,
                        school=academic_year.school,
                        maximum_students=class_structure.get("maximum_students", 40),
                    )

                    class_name_mapping[class_structure["name"]] = new_class
                    results["classes_created"] += 1

                except Exception as e:
                    error_msg = (
                        f"Failed to create class '{class_structure['name']}': {str(e)}"
                    )
                    results["errors"].append(error_msg)

            # Assign subjects to classes
            subject_assignments = template.get_subject_assignments()

            for subject_assignment in subject_assignments:
                try:
                    template_class_name = subject_assignment["class_name"]
                    if template_class_name not in class_name_mapping:
                        results["warnings"].append(
                            f"Class '{template_class_name}' not found for subject assignment"
                        )
                        continue

                    new_class = class_name_mapping[template_class_name]

                    # Get the subject
                    subject = Subject.objects.get(
                        id=subject_assignment["subject_id"], school=academic_year.school
                    )

                    # Create class-subject assignment
                    ClassSubject.objects.create(
                        subject=subject,
                        class_name=new_class,
                        academic_year=academic_year,
                        school=academic_year.school,
                    )

                    results["subjects_assigned"] += 1

                except Subject.DoesNotExist:
                    warning_msg = f"Subject '{subject_assignment.get('subject_name', 'Unknown')}' not found"
                    results["warnings"].append(warning_msg)
                except Exception as e:
                    error_msg = f"Failed to assign subject '{subject_assignment.get('subject_name', 'Unknown')}': {str(e)}"
                    results["errors"].append(error_msg)

            # Assign teachers to subjects
            teacher_assignments = template.get_teacher_assignments()
            print(f"Found {len(teacher_assignments)} teacher assignments in template")

            # Get all subject assignments to check for subjects without teachers
            subject_assignments = template.get_subject_assignments()
            subjects_with_teachers = set()

            # Track which subjects have teachers
            for teacher_assignment in teacher_assignments:
                class_name = teacher_assignment["class_name"]
                subject_id = teacher_assignment["subject_id"]
                subjects_with_teachers.add(f"{class_name}:{subject_id}")

            # Check for subjects without teachers
            subjects_without_teachers = []
            for subject_assignment in subject_assignments:
                class_name = subject_assignment["class_name"]
                subject_id = subject_assignment["subject_id"]
                subject_name = subject_assignment["subject_name"]

                if f"{class_name}:{subject_id}" not in subjects_with_teachers:
                    subjects_without_teachers.append(f"{subject_name} in {class_name}")

            if subjects_without_teachers:
                warning_msg = f"Some subjects don't have teachers assigned: {', '.join(subjects_without_teachers[:3])}"
                if len(subjects_without_teachers) > 3:
                    warning_msg += f" and {len(subjects_without_teachers) - 3} more"
                results["warnings"].append(warning_msg)
                print(f"Warning: {warning_msg}")

            for teacher_assignment in teacher_assignments:
                try:
                    template_class_name = teacher_assignment["class_name"]
                    if template_class_name not in class_name_mapping:
                        results["warnings"].append(
                            f"Class '{template_class_name}' not found for teacher assignment"
                        )
                        continue

                    new_class = class_name_mapping[template_class_name]

                    # Get teacher and subject
                    teacher = Teacher.objects.get(
                        id=teacher_assignment["teacher_id"], school=academic_year.school
                    )
                    subject = Subject.objects.get(
                        id=teacher_assignment["subject_id"], school=academic_year.school
                    )

                    # Create teacher-subject assignment
                    TeacherSubjectAssignment.objects.create(
                        teacher=teacher,
                        subject=subject,
                        class_assigned=new_class,
                        academic_year=academic_year,
                        school=academic_year.school,
                        is_active=True,
                    )

                    results["teacher_assignments_created"] += 1
                    print(
                        f"Created teacher assignment: {teacher.full_name} -> {subject.subject_name} in {new_class.name}"
                    )

                except (Teacher.DoesNotExist, Subject.DoesNotExist) as e:
                    warning_msg = (
                        f"Teacher or subject not found for assignment: {str(e)}"
                    )
                    results["warnings"].append(warning_msg)
                    print(f"Warning: {warning_msg}")
                except Exception as e:
                    error_msg = f"Failed to assign teacher: {str(e)}"
                    results["errors"].append(error_msg)
                    print(f"Error: {error_msg}")

            # Assign class teachers
            class_teacher_assignments = template.template_data.get(
                "class_teacher_assignments", []
            )

            for class_teacher_assignment in class_teacher_assignments:
                try:
                    template_class_name = class_teacher_assignment["class_name"]
                    if template_class_name not in class_name_mapping:
                        results["warnings"].append(
                            f"Class '{template_class_name}' not found for class teacher assignment"
                        )
                        continue

                    new_class = class_name_mapping[template_class_name]

                    # Get teacher
                    teacher = Teacher.objects.get(
                        id=class_teacher_assignment["teacher_id"],
                        school=academic_year.school,
                    )

                    # Create class teacher assignment
                    ClassTeacher.objects.create(
                        teacher=teacher,
                        class_assigned=new_class,
                        academic_year=academic_year,
                        school=academic_year.school,
                        is_active=True,
                    )

                    results["class_teachers_assigned"] += 1

                except Teacher.DoesNotExist:
                    warning_msg = f"Teacher not found for class teacher assignment"
                    results["warnings"].append(warning_msg)
                except Exception as e:
                    error_msg = f"Failed to assign class teacher: {str(e)}"
                    results["errors"].append(error_msg)

        except Exception as e:
            results["errors"].append(f"Template application failed: {str(e)}")
            raise

    return results


def extract_class_prefix(class_name):
    """
    Extract the prefix from a class name (e.g., '1Science A' -> '1Science')
    """
    # Simple extraction - take everything before the last space if it contains a letter
    parts = class_name.split()
    if len(parts) > 1:
        # Check if last part is likely a suffix (single letter or number)
        last_part = parts[-1]
        if len(last_part) == 1 and (last_part.isalpha() or last_part.isdigit()):
            return " ".join(parts[:-1])
    return class_name


def apply_class_name_customization(class_name, customizations):
    """
    Apply customizations to class names based on the customizations dict.

    Args:
        class_name: Original class name from template
        customizations: Dict with customization rules

    Returns:
        Modified class name
    """
    if not customizations:
        return class_name

    # Apply class prefix customizations
    class_prefixes = customizations.get("class_prefixes", {})
    if class_prefixes:
        for old_prefix, new_prefix in class_prefixes.items():
            if class_name.startswith(old_prefix):
                return class_name.replace(old_prefix, new_prefix, 1)

    # Apply year-specific customizations
    year_suffix = customizations.get("year_suffix", "")
    if year_suffix:
        # Add year suffix to class name
        return f"{class_name} {year_suffix}"

    return class_name


def get_template_statistics(template):
    """
    Get statistics about a template.

    Args:
        template: AcademicYearTemplate instance

    Returns:
        Dict with template statistics
    """
    class_structures = template.get_class_structures()
    subject_assignments = template.get_subject_assignments()
    teacher_assignments = template.get_teacher_assignments()
    class_teacher_assignments = template.template_data.get(
        "class_teacher_assignments", []
    )

    # Count unique forms and learning areas
    forms = set()
    learning_areas = set()
    for class_structure in class_structures:
        if class_structure.get("form_id"):
            forms.add(class_structure["form_id"])
        if class_structure.get("learning_area_id"):
            learning_areas.add(class_structure["learning_area_id"])

    # Count unique subjects and teachers
    subjects = set()
    teachers = set()
    for assignment in subject_assignments:
        subjects.add(assignment["subject_id"])

    for assignment in teacher_assignments:
        teachers.add(assignment["teacher_id"])

    for assignment in class_teacher_assignments:
        teachers.add(assignment["teacher_id"])

    return {
        "total_classes": len(class_structures),
        "total_subjects": len(subjects),
        "total_teachers": len(teachers),
        "total_subject_assignments": len(subject_assignments),
        "total_teacher_assignments": len(teacher_assignments),
        "total_class_teachers": len(class_teacher_assignments),
        "unique_forms": len(forms),
        "unique_learning_areas": len(learning_areas),
    }


def validate_template_data(template_data):
    """
    Validate template data structure.

    Args:
        template_data: Dict containing template data

    Returns:
        Tuple of (is_valid, errors)
    """
    errors = []

    # Check required keys
    required_keys = ["class_structures", "subject_assignments", "teacher_assignments"]
    for key in required_keys:
        if key not in template_data:
            errors.append(f"Missing required key: {key}")

    # Validate class structures
    if "class_structures" in template_data:
        for i, class_structure in enumerate(template_data["class_structures"]):
            if not isinstance(class_structure, dict):
                errors.append(f"Class structure {i} must be a dictionary")
                continue

            required_class_fields = ["name"]
            for field in required_class_fields:
                if field not in class_structure:
                    errors.append(
                        f"Class structure {i} missing required field: {field}"
                    )

    # Validate subject assignments
    if "subject_assignments" in template_data:
        for i, assignment in enumerate(template_data["subject_assignments"]):
            if not isinstance(assignment, dict):
                errors.append(f"Subject assignment {i} must be a dictionary")
                continue

            required_subject_fields = ["class_name", "subject_id"]
            for field in required_subject_fields:
                if field not in assignment:
                    errors.append(
                        f"Subject assignment {i} missing required field: {field}"
                    )

    return len(errors) == 0, errors
