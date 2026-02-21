from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.contrib.auth import get_user_model
import json

from shs_system.models import (
    SchoolInformation,
    AcademicYear,
    Term,
    Class,
    Subject,
    Student,
    StudentClass,
    Assessment,
    ClassSubject,
    Form,
    LearningArea,
)


class ScoreSheetTestCase(TestCase):
    def setUp(self):
        """Set up test data for score sheet functionality."""
        # Create test school
        self.school = SchoolInformation.objects.create(
            name="Test School",
            short_name="TS",
            slug="test-school",
            address="Test Address",
            phone_number="1234567890",
            email="test@school.com",
        )

        # Create test user
        self.user = get_user_model().objects.create_user(
            username="testadmin",
            email="admin@test.com",
            password="testpass123",
            school=self.school,
        )

        # Create academic year
        self.academic_year = AcademicYear.objects.create(
            name="2024/2025",
            start_date="2024-09-01",
            end_date="2025-08-31",
            school=self.school,
            is_current=True,
        )

        # Create term
        self.term = Term.objects.create(
            term_number=1,  # First Term
            start_date="2024-09-01",
            end_date="2024-12-15",
            academic_year=self.academic_year,
            school=self.school,
            is_current=True,
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
            name="1Science",
            form=self.form,
            learning_area=self.learning_area,
            academic_year=self.academic_year,
            school=self.school,
        )

        # Create subject
        self.subject = Subject.objects.create(
            subject_name="Mathematics",
            learning_area=self.learning_area,
            school=self.school,
        )

        # Create students
        self.student1 = Student.objects.create(
            admission_number="STU001",
            full_name="John Doe",
            date_of_birth="2010-01-01",
            gender="M",
            parent_contact="1234567890",
            admission_date="2024-09-01",
            school=self.school,
        )

        self.student2 = Student.objects.create(
            admission_number="STU002",
            full_name="Jane Smith",
            date_of_birth="2010-02-01",
            gender="F",
            parent_contact="1234567891",
            admission_date="2024-09-01",
            school=self.school,
        )

        # Assign students to class
        StudentClass.objects.create(
            student=self.student1,
            assigned_class=self.class_obj,
            is_active=True,
            school=self.school,
        )

        StudentClass.objects.create(
            student=self.student2,
            assigned_class=self.class_obj,
            is_active=True,
            school=self.school,
        )

        # Create class subject
        self.class_subject = ClassSubject.objects.create(
            class_name=self.class_obj,
            subject=self.subject,
            academic_year=self.academic_year,
            school=self.school,
        )

        # Create assessments
        Assessment.objects.create(
            class_subject=self.class_subject,
            student=self.student1,
            term=self.term,
            assessment_type="class_score",
            class_score=80.0,
            exam_score=85.0,
            total_score=82.5,
            grade="B",
            remarks="Good",
            recorded_by=self.user,
            school=self.school,
        )

        Assessment.objects.create(
            class_subject=self.class_subject,
            student=self.student2,
            term=self.term,
            assessment_type="class_score",
            class_score=90.0,
            exam_score=95.0,
            total_score=92.5,
            grade="A",
            remarks="Excellent",
            recorded_by=self.user,
            school=self.school,
        )

        # Set up client
        self.client = Client()

    def test_score_sheet_view_requires_login(self):
        """Test that score sheet view requires login."""
        response = self.client.get(reverse("score_sheet"))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_score_sheet_view_with_login(self):
        """Test score sheet view with authenticated user."""
        self.client.login(username="testadmin", password="testpass123")
        response = self.client.get(reverse("score_sheet"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Score Sheet")
        self.assertContains(response, "Test School")

    def test_score_sheet_ajax_data(self):
        """Test AJAX endpoint for score sheet data."""
        self.client.login(username="testadmin", password="testpass123")

        response = self.client.get(
            reverse("get_score_sheet_data_ajax"),
            {"class_id": self.class_obj.class_id, "subject_id": "all"},
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data["success"])
        self.assertIn("html_content", data)
        self.assertEqual(data["class_name"], self.class_obj.name)
        self.assertEqual(data["subject_name"], "All Subjects")

    def test_score_sheet_ajax_single_subject(self):
        """Test AJAX endpoint with single subject."""
        self.client.login(username="testadmin", password="testpass123")

        response = self.client.get(
            reverse("get_score_sheet_data_ajax"),
            {"class_id": self.class_obj.class_id, "subject_id": self.subject.id},
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data["success"])
        self.assertEqual(data["subject_name"], self.subject.subject_name)

    def test_score_sheet_ajax_no_class(self):
        """Test AJAX endpoint without class ID."""
        self.client.login(username="testadmin", password="testpass123")

        response = self.client.get(reverse("get_score_sheet_data_ajax"))

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn("error", data)

    def test_export_pdf(self):
        """Test PDF export functionality."""
        self.client.login(username="testadmin", password="testpass123")

        response = self.client.get(
            reverse("export_score_sheet_pdf"),
            {"class_id": self.class_obj.class_id, "subject_id": "all"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment", response["Content-Disposition"])

    def test_export_excel(self):
        """Test Excel export functionality."""
        self.client.login(username="testadmin", password="testpass123")

        response = self.client.get(
            reverse("export_score_sheet_excel"),
            {"class_id": self.class_obj.class_id, "subject_id": "all"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("spreadsheetml", response["Content-Type"])
        self.assertIn("attachment", response["Content-Disposition"])

    def test_score_sheet_template_context(self):
        """Test that score sheet template receives correct context."""
        self.client.login(username="testadmin", password="testpass123")
        response = self.client.get(reverse("score_sheet"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("classes", response.context)
        self.assertIn("subjects", response.context)
        self.assertIn("school", response.context)
        self.assertIn("current_academic_year", response.context)
        self.assertIn("current_term", response.context)
