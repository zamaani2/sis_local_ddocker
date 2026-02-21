from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.conf import settings
from unittest.mock import patch, MagicMock

from shs_system.utils import send_activity_reminder_email
from shs_system.models import (
    Teacher,
    Class,
    Subject,
    Term,
    AcademicYear,
    SchoolInformation,
)

User = get_user_model()


class EmailSendingTest(TestCase):
    """Test the email sending functionality"""

    def setUp(self):
        # Create test data
        self.school = SchoolInformation.objects.create(
            name="Test School",
            short_name="TS",
            slug="test-school",
            address="123 Test St",
        )

        self.academic_year = AcademicYear.objects.create(
            name="2025/2026",
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timezone.timedelta(days=365),
            is_current=True,
            school=self.school,
        )

        self.term = Term.objects.create(
            academic_year=self.academic_year,
            term_number=1,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timezone.timedelta(days=90),
            is_current=True,
            school=self.school,
        )

        self.teacher = Teacher.objects.create(
            full_name="Test Teacher", contact_number="1234567890", school=self.school
        )

        self.user = User.objects.create(
            username="testteacher",
            email="test@example.com",
            role="teacher",
            teacher_profile=self.teacher,
            school=self.school,
        )

        self.teacher.user = self.user

        self.class_obj = Class.objects.create(
            name="Test Class", academic_year=self.academic_year, school=self.school
        )

        self.subject = Subject.objects.create(
            subject_name="Test Subject", school=self.school
        )

        # Create test context for email
        self.context = {
            "teacher": self.teacher,
            "class_obj": self.class_obj,
            "subject": self.subject,
            "term": self.term,
            "activity_type": "scores",
            "activity_type_name": "Score Entry",
            "completion": {
                "total": 10,
                "completed": 5,
                "percentage": 50,
                "status": "in_progress",
            },
            "school_name": self.school.name,
            "login_url": "http://example.com/login/",
            "direct_link": "http://example.com/dashboard/",
            "is_bulk_reminder": False,
        }

    @patch("super_admin.models.SystemEmailConfig")
    @patch("django.core.mail.send_mail")
    def test_email_sending_with_system_config_not_available(
        self, mock_send_mail, mock_system_email_config
    ):
        """Test email sending when SystemEmailConfig is not available"""
        # Mock SystemEmailConfig to simulate it not being available
        mock_system_email_config.get_active_config.return_value = None

        # Call the function
        success, message = send_activity_reminder_email(
            "test@example.com", self.context
        )

        # Check that send_mail was called
        self.assertTrue(mock_send_mail.called)
        self.assertTrue(success)
        self.assertEqual(message, "Email sent successfully via standard email")

    @patch("super_admin.models.SystemEmailConfig")
    @patch("django.core.mail.send_mail")
    def test_email_sending_fallback_to_django_email(
        self, mock_send_mail, mock_system_email_config
    ):
        """Test fallback to Django's send_mail when SystemEmailConfig is not available"""
        # Configure the mock to raise ImportError
        mock_system_email_config.side_effect = ImportError(
            "No module named 'super_admin.models'"
        )

        # Call the function
        success, message = send_activity_reminder_email(
            "test@example.com", self.context
        )

        # Check that send_mail was called
        self.assertTrue(mock_send_mail.called)
        self.assertTrue(success)
        self.assertEqual(message, "Email sent successfully via standard email")

    @patch("shs_system.models.OAuthCredentialStore")
    @patch("super_admin.models.SystemEmailConfig")
    @patch("django.core.mail.send_mail")
    def test_email_sending_with_legacy_oauth(
        self, mock_send_mail, mock_system_email_config, mock_oauth_store
    ):
        """Test email sending with legacy OAuth credentials"""
        # Mock SystemEmailConfig to simulate it not being available
        mock_system_email_config.objects.filter.return_value.first.return_value = None

        # Mock OAuthCredentialStore
        mock_oauth_creds = MagicMock()
        mock_oauth_creds.email = "oauth@example.com"
        mock_oauth_creds.client_id = "client_id"
        mock_oauth_creds.client_secret = "client_secret"
        mock_oauth_creds.refresh_token = "refresh_token"
        mock_oauth_creds.access_token = "access_token"
        mock_oauth_creds.token_uri = "https://oauth2.googleapis.com/token"
        mock_oauth_creds.scopes = ["https://www.googleapis.com/auth/gmail.send"]

        mock_oauth_store.objects.filter.return_value.first.return_value = (
            mock_oauth_creds
        )

        # Mock the gmail service
        with patch("google.oauth2.credentials.Credentials") as mock_credentials:
            mock_cred_instance = MagicMock()
            mock_cred_instance.valid = True
            mock_credentials.return_value = mock_cred_instance

            with patch("googleapiclient.discovery.build") as mock_build:
                mock_gmail = MagicMock()
                mock_users = MagicMock()
                mock_messages = MagicMock()
                mock_send = MagicMock()
                mock_execute = MagicMock()

                mock_gmail.users.return_value = mock_users
                mock_users.messages.return_value = mock_messages
                mock_messages.send.return_value = mock_send
                mock_send.execute.return_value = mock_execute

                mock_build.return_value = mock_gmail

                # Call the function
                success, message = send_activity_reminder_email(
                    "test@example.com", self.context
                )

                # Since we're mocking the OAuth functionality, it should succeed with OAuth
                self.assertTrue(success)
                self.assertIn("OAuth", message)

    @patch("shs_system.models.Notification")
    @patch("django.core.mail.send_mail")
    def test_notification_fallback(self, mock_send_mail, mock_notification):
        """Test fallback to notification when email sending fails"""
        # Configure send_mail to raise an exception
        mock_send_mail.side_effect = Exception("Email sending failed")

        # Mock the Notification.objects.create method
        mock_notification.objects.create.return_value = MagicMock()

        # Call the function
        success, message = send_activity_reminder_email(
            "test@example.com", self.context
        )

        # Check that Notification.objects.create was called
        self.assertTrue(mock_notification.objects.create.called)
        self.assertTrue(success)
        self.assertIn("notification has been saved", message)
