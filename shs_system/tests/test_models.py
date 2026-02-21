"""
Tests for SHS System models.
This includes tests for data models, validations, and model methods.
"""

from django.test import TestCase
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from datetime import date, timedelta

from shs_system.models import (
    User,
    AcademicYear,
    Term,
    Form,
    LearningArea,
    Department,
    Teacher,
    Student,
    Class,
    ClassTeacher,
    StudentClass,
    Subject,
    TeacherSubjectAssignment,
    Assessment,
    ClassSubject,
    GradingSystem,
    SchoolInformation,
)


class UserModelTest(TestCase):
    def setUp(self):
        # Create basic user with admin role
        self.admin_user = User.objects.create_user(
            username="admin_test",
            email="admin@test.com",
            password="password123",
            role="admin",
            full_name="Admin Test User",
        )

    def test_user_creation(self):
        # Test user was properly created
        self.assertEqual(User.objects.count(), 1)
        user = User.objects.get(username="admin_test")
        self.assertEqual(user.role, "admin")
        self.assertEqual(user.full_name, "Admin Test User")

    def test_str_representation(self):
        # Test string representation
        self.assertEqual(str(self.admin_user), "admin_test (Administrator)")


class AcademicYearModelTest(TestCase):
    def setUp(self):
        self.academic_year = AcademicYear.objects.create(
            name="2023/2024",
            start_date=date(2023, 9, 1),
            end_date=date(2024, 7, 31),
            is_current=True,
        )

    def test_academic_year_creation(self):
        self.assertEqual(AcademicYear.objects.count(), 1)

    def test_get_duration(self):
        # Test the get_duration method
        duration = self.academic_year.get_duration()
        expected_duration = (date(2024, 7, 31) - date(2023, 9, 1)).days
        self.assertEqual(duration, expected_duration)

    def test_is_current_uniqueness(self):
        # Test that only one academic year can be current
        second_year = AcademicYear.objects.create(
            name="2024/2025",
            start_date=date(2024, 9, 1),
            end_date=date(2025, 7, 31),
            is_current=True,
        )

        # Refresh the first academic year from the database
        self.academic_year.refresh_from_db()

        # The first academic year should no longer be current
        self.assertFalse(self.academic_year.is_current)
        self.assertTrue(second_year.is_current)

    def test_invalid_dates(self):
        # Test validation prevents end date before start date
        invalid_year = AcademicYear(
            name="Invalid Year",
            start_date=date(2023, 9, 1),
            end_date=date(2023, 8, 31),  # End date before start date
        )

        with self.assertRaises(ValidationError):
            invalid_year.full_clean()


class TermModelTest(TestCase):
    def setUp(self):
        self.academic_year = AcademicYear.objects.create(
            name="2023/2024",
            start_date=date(2023, 9, 1),
            end_date=date(2024, 7, 31),
        )

        self.term = Term.objects.create(
            academic_year=self.academic_year,
            term_number=1,
            start_date=date(2023, 9, 1),
            end_date=date(2023, 12, 20),
            is_current=True,
        )

    def test_term_creation(self):
        self.assertEqual(Term.objects.count(), 1)
        self.assertEqual(self.term.term_number, 1)

    def test_term_uniqueness(self):
        # Test unique constraint on academic year and term number
        with self.assertRaises(IntegrityError):
            Term.objects.create(
                academic_year=self.academic_year,
                term_number=1,  # Same term number for the same academic year
                start_date=date(2023, 9, 1),
                end_date=date(2023, 12, 20),
            )


class FormModelTest(TestCase):
    def setUp(self):
        self.school = SchoolInformation.objects.create(
            name="Test School",
            short_name="TS",
            address="123 Test St",
            phone_number="1234567890",
        )
        self.form = Form.objects.create(
            form_number=1,
            name="SHS 1",
            description="Senior High School - First Year",
            school=self.school,
        )

    def test_form_creation(self):
        self.assertEqual(Form.objects.count(), 1)

    def test_str_representation(self):
        self.assertEqual(str(self.form), "SHS 1 (Test School)")


class GradingSystemTest(TestCase):
    def setUp(self):
        # Create multiple grade entries
        self.grade_a = GradingSystem.objects.create(
            grade_letter="A",
            min_score=80,
            max_score=100,
            remarks="Excellent",
            is_active=True,
        )

        self.grade_b = GradingSystem.objects.create(
            grade_letter="B",
            min_score=70,
            max_score=79.99,
            remarks="Very Good",
            is_active=True,
        )

        self.grade_c = GradingSystem.objects.create(
            grade_letter="C",
            min_score=60,
            max_score=69.99,
            remarks="Good",
            is_active=True,
        )

    def test_get_grade_for_score(self):
        # Test the class method for getting grade based on score
        result = GradingSystem.get_grade_for_score(85)
        self.assertIsInstance(result, GradingSystem)
        self.assertEqual(result.grade_letter, "A")

        result = GradingSystem.get_grade_for_score(75)
        self.assertIsInstance(result, GradingSystem)
        self.assertEqual(result.grade_letter, "B")

        result = GradingSystem.get_grade_for_score(65)
        self.assertIsInstance(result, GradingSystem)
        self.assertEqual(result.grade_letter, "C")


class TeacherModelTest(TestCase):
    def setUp(self):
        self.school = SchoolInformation.objects.create(
            name="Test School",
            short_name="TS",
            address="123 Test St",
            phone_number="1234567890",
        )
        self.department = Department.objects.create(
            name="Mathematics Department",
            code="MATH",
            description="Department of Mathematics",
            school=self.school,
        )

        self.teacher = Teacher.objects.create(
            full_name="John Smith",
            contact_number="1234567890",
            email="john@example.com",
            department=self.department,
            gender="M",
            school=self.school,
        )

    def test_teacher_creation(self):
        self.assertEqual(Teacher.objects.count(), 1)
        self.assertIsNotNone(self.teacher.staff_id)  # Staff ID should be generated

    def test_str_representation(self):
        expected = f"John Smith ({self.teacher.staff_id}) - Test School"
        self.assertEqual(str(self.teacher), expected)


class StudentModelTest(TestCase):
    def setUp(self):
        self.form = Form.objects.create(form_number=1, name="SHS 1")

        self.learning_area = LearningArea.objects.create(
            code="general_arts", name="General Arts"
        )

        self.student = Student.objects.create(
            full_name="Jane Doe",
            date_of_birth=date(2005, 5, 15),
            gender="F",
            parent_contact="0987654321",
            admission_date=date(2023, 9, 1),
            form=self.form,
            learning_area=self.learning_area,
            email="jane@example.com",
        )

    def test_student_creation(self):
        self.assertEqual(Student.objects.count(), 1)
        self.assertIsNotNone(
            self.student.admission_number
        )  # Admission number should be generated

    def test_calculate_age(self):
        # Test the age calculation
        expected_age = (date.today() - date(2005, 5, 15)).days // 365
        self.assertEqual(self.student.calculate_age(), expected_age)


class ClassModelTest(TestCase):
    def setUp(self):
        self.school = SchoolInformation.objects.create(
            name="Test School",
            short_name="TS",
            address="123 Test St",
            phone_number="1234567890",
        )
        self.form = Form.objects.create(form_number=1, name="SHS 1", school=self.school)

        self.learning_area = LearningArea.objects.create(
            code="general_arts", name="General Arts", school=self.school
        )

        self.academic_year = AcademicYear.objects.create(
            name="2023/2024",
            start_date=date(2023, 9, 1),
            end_date=date(2024, 7, 31),
            school=self.school,
        )

        self.class_obj = Class.objects.create(
            name="1Science A",
            form=self.form,
            learning_area=self.learning_area,
            academic_year=self.academic_year,
            maximum_students=40,
            school=self.school,
        )

    def test_class_creation(self):
        self.assertEqual(Class.objects.count(), 1)
        self.assertIsNotNone(self.class_obj.class_id)  # Class ID should be generated

    def test_str_representation(self):
        self.assertEqual(str(self.class_obj), "1Science A (Test School)")
