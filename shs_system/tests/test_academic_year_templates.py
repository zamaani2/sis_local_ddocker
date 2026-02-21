"""
Tests for Academic Year Template system.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from ..models import (
    AcademicYear,
    AcademicYearTemplate,
    Class,
    Subject,
    Teacher,
    Form,
    LearningArea,
    SchoolInformation,
    ClassSubject,
    TeacherSubjectAssignment,
    ClassTeacher,
)
from ..utils.template_utils import (
    create_template_from_academic_year,
    apply_template_to_academic_year,
    get_template_statistics,
    validate_template_data,
)

User = get_user_model()


class AcademicYearTemplateModelTest(TestCase):
    """Test AcademicYearTemplate model"""

    def setUp(self):
        self.school = SchoolInformation.objects.create(
            name="Test School", address="Test Address"
        )
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            school=self.school,
        )
        self.academic_year = AcademicYear.objects.create(
            name="2023/2024",
            start_date="2023-09-01",
            end_date="2024-07-31",
            school=self.school,
        )

    def test_template_creation(self):
        """Test creating a template"""
        template = AcademicYearTemplate.objects.create(
            name="Test Template",
            description="Test template description",
            school=self.school,
            created_by=self.user,
            template_data={"test": "data"},
        )

        self.assertEqual(template.name, "Test Template")
        self.assertEqual(template.school, self.school)
        self.assertEqual(template.created_by, self.user)
        self.assertFalse(template.is_default)
        self.assertTrue(template.is_active)

    def test_default_template_validation(self):
        """Test that only one default template is allowed per school"""
        # Create first default template
        template1 = AcademicYearTemplate.objects.create(
            name="Default Template 1",
            school=self.school,
            is_default=True,
            created_by=self.user,
        )

        # Try to create second default template
        template2 = AcademicYearTemplate(
            name="Default Template 2",
            school=self.school,
            is_default=True,
            created_by=self.user,
        )

        with self.assertRaises(ValidationError):
            template2.clean()

    def test_template_str(self):
        """Test template string representation"""
        template = AcademicYearTemplate.objects.create(
            name="Test Template", school=self.school, created_by=self.user
        )

        expected = "Test Template (Test School)"
        self.assertEqual(str(template), expected)


class TemplateUtilsTest(TestCase):
    """Test template utility functions"""

    def setUp(self):
        self.school = SchoolInformation.objects.create(
            name="Test School", address="Test Address"
        )
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            school=self.school,
        )
        self.academic_year = AcademicYear.objects.create(
            name="2023/2024",
            start_date="2023-09-01",
            end_date="2024-07-31",
            school=self.school,
        )

        # Create form and learning area
        self.form = Form.objects.create(
            form_number=1, name="Form 1", school=self.school
        )
        self.learning_area = LearningArea.objects.create(
            name="Science", school=self.school
        )

        # Create class
        self.class_obj = Class.objects.create(
            name="1Science A",
            form=self.form,
            learning_area=self.learning_area,
            academic_year=self.academic_year,
            school=self.school,
        )

        # Create subject
        self.subject = Subject.objects.create(
            subject_name="Mathematics", subject_code="MATH", school=self.school
        )

        # Create teacher
        self.teacher = Teacher.objects.create(
            staff_id="T001", full_name="John Doe", school=self.school
        )

        # Create class-subject assignment
        self.class_subject = ClassSubject.objects.create(
            subject=self.subject,
            class_name=self.class_obj,
            academic_year=self.academic_year,
            school=self.school,
        )

        # Create teacher assignment
        self.teacher_assignment = TeacherSubjectAssignment.objects.create(
            teacher=self.teacher,
            subject=self.subject,
            class_assigned=self.class_obj,
            academic_year=self.academic_year,
            school=self.school,
        )

        # Create class teacher
        self.class_teacher = ClassTeacher.objects.create(
            teacher=self.teacher,
            class_assigned=self.class_obj,
            academic_year=self.academic_year,
            school=self.school,
        )

    def test_create_template_from_academic_year(self):
        """Test creating template from academic year"""
        template = create_template_from_academic_year(
            academic_year=self.academic_year,
            template_name="Test Template",
            description="Test description",
            created_by=self.user,
        )

        self.assertEqual(template.name, "Test Template")
        self.assertEqual(template.school, self.school)
        self.assertEqual(template.created_by, self.user)

        # Check template data structure
        template_data = template.template_data
        self.assertIn("class_structures", template_data)
        self.assertIn("subject_assignments", template_data)
        self.assertIn("teacher_assignments", template_data)
        self.assertIn("class_teacher_assignments", template_data)

        # Check class structures
        class_structures = template_data["class_structures"]
        self.assertEqual(len(class_structures), 1)
        self.assertEqual(class_structures[0]["name"], "1Science A")

        # Check subject assignments
        subject_assignments = template_data["subject_assignments"]
        self.assertEqual(len(subject_assignments), 1)
        self.assertEqual(subject_assignments[0]["class_name"], "1Science A")
        self.assertEqual(subject_assignments[0]["subject_name"], "Mathematics")

    def test_apply_template_to_academic_year(self):
        """Test applying template to create new academic year"""
        # First create a template
        template = create_template_from_academic_year(
            academic_year=self.academic_year,
            template_name="Test Template",
            created_by=self.user,
        )

        # Create new academic year
        new_academic_year = AcademicYear.objects.create(
            name="2024/2025",
            start_date="2024-09-01",
            end_date="2025-07-31",
            school=self.school,
        )

        # Apply template
        results = apply_template_to_academic_year(template, new_academic_year)

        # Check results
        self.assertEqual(results["classes_created"], 1)
        self.assertEqual(results["subjects_assigned"], 1)
        self.assertEqual(results["teacher_assignments_created"], 1)
        self.assertEqual(results["class_teachers_assigned"], 1)
        self.assertEqual(len(results["errors"]), 0)

        # Verify classes were created
        new_classes = Class.objects.filter(academic_year=new_academic_year)
        self.assertEqual(new_classes.count(), 1)

        # Verify class-subject assignments were created
        new_class_subjects = ClassSubject.objects.filter(
            academic_year=new_academic_year
        )
        self.assertEqual(new_class_subjects.count(), 1)

        # Verify teacher assignments were created
        new_teacher_assignments = TeacherSubjectAssignment.objects.filter(
            academic_year=new_academic_year
        )
        self.assertEqual(new_teacher_assignments.count(), 1)

        # Verify class teachers were created
        new_class_teachers = ClassTeacher.objects.filter(
            academic_year=new_academic_year
        )
        self.assertEqual(new_class_teachers.count(), 1)

    def test_get_template_statistics(self):
        """Test getting template statistics"""
        template = create_template_from_academic_year(
            academic_year=self.academic_year,
            template_name="Test Template",
            created_by=self.user,
        )

        stats = get_template_statistics(template)

        self.assertEqual(stats["total_classes"], 1)
        self.assertEqual(stats["total_subjects"], 1)
        self.assertEqual(stats["total_teachers"], 1)
        self.assertEqual(stats["total_subject_assignments"], 1)
        self.assertEqual(stats["total_teacher_assignments"], 1)
        self.assertEqual(stats["total_class_teachers"], 1)

    def test_validate_template_data(self):
        """Test template data validation"""
        # Valid template data
        valid_data = {
            "class_structures": [{"name": "Test Class", "form_id": 1}],
            "subject_assignments": [{"class_name": "Test Class", "subject_id": 1}],
            "teacher_assignments": [
                {"class_name": "Test Class", "subject_id": 1, "teacher_id": 1}
            ],
        }

        is_valid, errors = validate_template_data(valid_data)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

        # Invalid template data
        invalid_data = {
            "class_structures": [{"name": "Test Class"}],  # Missing required fields
            "subject_assignments": [],  # Missing required key
        }

        is_valid, errors = validate_template_data(invalid_data)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)
