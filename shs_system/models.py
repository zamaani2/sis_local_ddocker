from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils.text import slugify

from django.utils import timezone

import random
import string
from datetime import date
from django.db.models import Q
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse
import secrets
import logging
from django.apps import apps
from decimal import Decimal


def generate_unique_id(entity_type=None, length=5):
    """
    Generate a unique numeric ID based on entity type.

    Parameters:
    entity_type (str): Type of entity ('student', 'teacher', 'class', etc.)
    length (int): Length of the random part of the ID

    Returns:
    str: A unique ID with appropriate prefix and format
    """
    # Get current date components for potential use in IDs
    from datetime import datetime

    current_year = datetime.now().year
    year_short = str(current_year)[-2:]  # Last two digits of year

    # Generate random numeric component
    random_part = "".join(random.choices(string.digits, k=length))

    # Format based on entity type
    if entity_type == "student":
        prefix = f"ST-{year_short}"
        model_class = apps.get_model('shs_system', 'Student')
    elif entity_type == "teacher":
        prefix = "TE-"
        model_class = apps.get_model('shs_system', 'Teacher')
    elif entity_type == "class":
        prefix = "CL-"
        model_class = apps.get_model('shs_system', 'Class')
    elif entity_type == "subject":
        prefix = "SB-"
        model_class = apps.get_model('shs_system', 'Subject')
    elif entity_type == "assignment":
        prefix = "AS-"
        model_class = apps.get_model('shs_system', 'TeacherSubjectAssignment')
    elif entity_type == "assessment":
        prefix = "EV-"
        model_class = apps.get_model('shs_system', 'Assessment')
    elif entity_type == "class_subject":
        prefix = "CS-"
        model_class = apps.get_model('shs_system', 'ClassSubject')
    else:
        # Default format for other types
        return "".join(random.choices(string.digits, k=length))

    # Generate unique ID by checking for collisions
    if entity_type in ["student", "teacher", "class", "subject", "assignment", "assessment", "class_subject"]:
        # Determine the field name to check for uniqueness
        if entity_type == "student":
            field_name = "admission_number"
        elif entity_type == "teacher":
            field_name = "staff_id"
        elif entity_type == "assignment":
            field_name = "assignment_id"
        elif entity_type == "assessment":
            field_name = "assessment_id"
        elif entity_type == "class_subject":
            field_name = "class_subject_id"
        elif entity_type == "subject":
            field_name = "subject_code"
        else:
            field_name = f"{entity_type}_id"

        # Generate ID and check for uniqueness
        max_attempts = 100  # Prevent infinite loops
        attempts = 0
        
        while attempts < max_attempts:
            if entity_type == "student":
                candidate_id = f"{prefix}{random_part}"
            else:
                candidate_id = f"{prefix}{random_part}"
            
            # Check if ID already exists
            if not model_class.objects.filter(**{field_name: candidate_id}).exists():
                return candidate_id
            
            # Generate new random part for next attempt
            random_part = "".join(random.choices(string.digits, k=length))
            attempts += 1
        
        # If we couldn't generate a unique ID after max attempts, raise an error
        raise ValueError(f"Could not generate unique {entity_type} ID after {max_attempts} attempts")
    
    return f"{prefix}{random_part}"



def generate_secure_password(length=12):
    """Generate a secure password with minimum requirements."""
    # Define character sets
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    special_chars = "!@#$%^&*"

    # Ensure at least one character from each set
    password = [
        secrets.choice(lowercase),
        secrets.choice(uppercase),
        secrets.choice(digits),
        secrets.choice(special_chars),
    ]

    # Fill the rest with random characters from all sets
    all_chars = lowercase + uppercase + digits + special_chars
    password.extend(secrets.choice(all_chars) for _ in range(length - 4))

    # Shuffle the password characters
    password_list = list(password)
    secrets.SystemRandom().shuffle(password_list)

    return "".join(password_list)


def send_user_credentials_email(user, password):
    """
    Send email with login credentials to the user.
    """
    try:
        # Get school information
        school_info = SchoolInformation.get_active()

        # Build the login URL
        login_url = f"{settings.SITE_URL}{reverse('login')}"

        # Prepare context for email template
        context = {
            "user": user,
            "password": password,
            "school_name": (
                school_info.name if school_info else "School Management System"
            ),
            "school_address": school_info.address if school_info else "",
            "login_url": login_url,
        }

        # Render email template
        email_html = render_to_string("emails/user_credentials.html", context)

        # Send email
        send_mail(
            subject=f'Your {context["school_name"]} Account Credentials',
            message=f"Your username is {user.username} and password is {password}. Please login at {login_url}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=email_html,
            fail_silently=False,
        )

        return True
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        return False


class User(AbstractUser):
    ROLES = (
        ("admin", "Administrator"),
        ("teacher", "Teacher"),
        ("student", "Student"),
        ("superadmin", "Super Administrator"),
    )
    role = models.CharField(max_length=20, choices=ROLES)
    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    # Nullable foreign keys to Teacher and Student
    teacher_profile = models.OneToOneField(
        "Teacher", on_delete=models.SET_NULL, null=True, blank=True
    )
    student_profile = models.OneToOneField(
        "Student", on_delete=models.SET_NULL, null=True, blank=True
    )
    # School association for multi-tenancy
    school = models.ForeignKey(
        "SchoolInformation",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="users",
    )

    # For super admin users who manage multiple schools
    is_superadmin = models.BooleanField(default=False)

    # Last login tracking
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    last_active = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        if self.role == "teacher" and self.teacher_profile:
            return f"{self.teacher_profile.full_name} ({self.get_role_display()})"
        elif self.role == "student" and self.student_profile:
            return f"{self.student_profile.full_name} ({self.get_role_display()})"
        return f"{self.username} ({self.get_role_display()})"

    def is_school_admin(self):
        """Check if user is a school administrator"""
        return self.role == "admin" and self.school is not None

    def get_administered_schools(self):
        """Get schools administered by this user"""
        if self.is_superadmin:
            return SchoolInformation.objects.all()
        elif self.is_school_admin():
            return SchoolInformation.objects.filter(pk=self.school.pk)
        return SchoolInformation.objects.none()


class AcademicYear(models.Model):
    name = models.CharField(max_length=100)  # e.g., "2024/2025" or longer names
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)
    is_archived = models.BooleanField(
        default=False,
        help_text="Archived academic years are hidden but data is preserved",
    )
    archived_at = models.DateTimeField(
        null=True, blank=True, help_text="When this academic year was archived"
    )
    archived_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="User who archived this academic year",
        related_name="archived_academic_years",
    )
    # Add school relationship for multi-tenancy
    school = models.ForeignKey(
        "SchoolInformation",
        on_delete=models.CASCADE,
        related_name="academic_years",
        null=True,
    )

    class Meta:
        indexes = [
            models.Index(fields=["is_current"]),
            models.Index(fields=["school", "is_current"]),
            models.Index(fields=["is_archived"]),
            models.Index(fields=["school", "is_archived"]),
        ]
        # Ensure academic years are unique per school (excluding archived ones)
        unique_together = ["name", "school"]

    def clean(self):
        if self.start_date >= self.end_date:
            raise ValidationError("Start date must be before end date.")

    def save(self, *args, **kwargs):
        # If marked as current, make sure only one academic year is current per school
        if self.is_current:
            AcademicYear.objects.filter(school=self.school, is_current=True).exclude(
                pk=self.pk
            ).update(is_current=False)
        super().save(*args, **kwargs)

    def get_duration(self):
        return (self.end_date - self.start_date).days

    def archive(self, user=None):
        """Archive this academic year"""
        from django.utils import timezone

        self.is_archived = True
        self.archived_at = timezone.now()
        self.archived_by = user
        self.is_current = False  # Cannot be current if archived
        self.save()

    def unarchive(self):
        """Unarchive this academic year"""
        self.is_archived = False
        self.archived_at = None
        self.archived_by = None
        self.save()

    def is_archivable(self):
        """Check if this academic year can be archived"""
        return not self.is_archived

    def is_unarchivable(self):
        """Check if this academic year can be unarchived"""
        return self.is_archived

    def get_archive_status(self):
        """Get human-readable archive status"""
        if self.is_archived:
            return f"Archived on {self.archived_at.strftime('%Y-%m-%d %H:%M')} by {self.archived_by.full_name if self.archived_by else 'Unknown'}"
        return "Active"

    def __str__(self):
        school_name = self.school.name if self.school else "Unknown"
        status = " (Archived)" if self.is_archived else ""
        return f"{self.name} ({school_name}){status}"


class AcademicYearTemplate(models.Model):
    """
    Template for academic year setup to streamline the creation process.
    Stores the structure of classes, subjects, and teacher assignments
    that can be reused across academic years.
    """

    name = models.CharField(
        max_length=100, help_text="Template name (e.g., 'Standard SHS Template')"
    )
    description = models.TextField(blank=True, help_text="Description of this template")
    school = models.ForeignKey(
        "SchoolInformation",
        on_delete=models.CASCADE,
        related_name="academic_year_templates",
        null=True,
    )
    is_default = models.BooleanField(
        default=False, help_text="Default template for new academic years"
    )
    created_from_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Academic year this template was created from",
    )

    # Template data stored as JSON
    template_data = models.JSONField(
        default=dict,
        help_text="Structured data containing classes, subjects, and teacher assignments",
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="User who created this template",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["school", "is_active"]),
            models.Index(fields=["is_default"]),
            models.Index(fields=["created_at"]),
        ]
        unique_together = ["name", "school"]

    def clean(self):
        # Ensure only one default template per school
        if self.is_default and self.school:
            existing_default = AcademicYearTemplate.objects.filter(
                school=self.school, is_default=True, is_active=True
            ).exclude(pk=self.pk)
            if existing_default.exists():
                raise ValidationError(
                    "Only one default template is allowed per school."
                )

    def save(self, *args, **kwargs):
        # If setting as default, unset other defaults for this school
        if self.is_default and self.school:
            AcademicYearTemplate.objects.filter(
                school=self.school, is_default=True, is_active=True
            ).exclude(pk=self.pk).update(is_default=False)

        super().save(*args, **kwargs)

    def get_class_structures(self):
        """Get the class structures from template data"""
        return self.template_data.get("class_structures", [])

    def get_subject_assignments(self):
        """Get the subject assignments from template data"""
        return self.template_data.get("subject_assignments", [])

    def get_teacher_assignments(self):
        """Get the teacher assignments from template data"""
        return self.template_data.get("teacher_assignments", [])

    def get_form_learning_area_combinations(self):
        """Get unique form and learning area combinations from template"""
        combinations = set()
        for class_structure in self.get_class_structures():
            form_id = class_structure.get("form_id")
            learning_area_id = class_structure.get("learning_area_id")
            if form_id and learning_area_id:
                combinations.add((form_id, learning_area_id))
        return list(combinations)

    def create_academic_year_from_template(
        self, new_academic_year, customizations=None
    ):
        """
        Create a new academic year from this template with optional customizations.

        Args:
            new_academic_year: AcademicYear instance to populate
            customizations: Dict with customizations (e.g., {'class_prefixes': {...}})

        Returns:
            Dict with creation results and statistics
        """
        from .utils.template_utils import apply_template_to_academic_year

        return apply_template_to_academic_year(self, new_academic_year, customizations)

    def __str__(self):
        school_name = self.school.name if self.school else "Unknown"
        return f"{self.name} ({school_name})"


class Term(models.Model):
    TERMS = ((1, "First Term"), (2, "Second Term"), (3, "Third Term"))

    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    term_number = models.SmallIntegerField(choices=TERMS)
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)
    # School is referenced through academic_year, but add a direct link for queries
    school = models.ForeignKey(
        "SchoolInformation", on_delete=models.CASCADE, related_name="terms", null=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["academic_year", "term_number"], name="unique_term"
            )
        ]
        indexes = [
            models.Index(fields=["is_current"]),
            models.Index(fields=["academic_year", "is_current"]),
            models.Index(fields=["school", "is_current"]),
        ]

    def clean(self):
        if self.start_date >= self.end_date:
            raise ValidationError("Start date must be before end date.")

        # Make sure term belongs to the same school as its academic year
        if (
            self.academic_year
            and self.school
            and self.academic_year.school != self.school
        ):
            raise ValidationError(
                "Term's school must match its academic year's school."
            )

    def save(self, *args, **kwargs):
        # Set school from academic year if not explicitly provided
        if self.academic_year and not self.school:
            self.school = self.academic_year.school

        # If marked as current, ensure only one term is current per school
        if self.is_current:
            Term.objects.filter(school=self.school, is_current=True).exclude(
                pk=self.pk
            ).update(is_current=False)
        super().save(*args, **kwargs)

    def get_duration(self):
        return (self.end_date - self.start_date).days

    @property
    def name(self):
        """Return the term name for template compatibility"""
        return self.get_term_number_display()

    def __str__(self):
        return f"{self.academic_year} - {self.get_term_number_display()}"


class Form(models.Model):
    """Model to represent the different forms/grade levels in the school system."""

    form_number = models.PositiveSmallIntegerField()
    name = models.CharField(max_length=50)  # e.g., "SHS 1", "SHS 2", "SHS 3"
    description = models.TextField(blank=True, null=True)
    # Add school relationship for multi-tenancy
    school = models.ForeignKey(
        "SchoolInformation",
        on_delete=models.CASCADE,
        related_name="forms",
        null=True,
    )

    class Meta:
        ordering = ["form_number"]
        indexes = [
            models.Index(fields=["form_number"]),
            models.Index(fields=["school", "form_number"]),
        ]
        # Ensure form numbers are unique per school
        unique_together = ["form_number", "school"]

    def __str__(self):
        school_name = self.school.name if self.school else "Unknown"
        return f"{self.name} ({school_name})"


class LearningArea(models.Model):
    """Model to represent different learning areas/programs offered."""

    code = models.CharField(max_length=30)  # e.g., "general_arts"
    name = models.CharField(max_length=100)  # e.g., "General Arts"
    description = models.TextField(blank=True, null=True)
    # Add school relationship for multi-tenancy
    school = models.ForeignKey(
        "SchoolInformation",
        on_delete=models.CASCADE,
        related_name="learning_areas",
        null=True,
    )

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["school", "code"]),
        ]
        # Ensure codes are unique per school
        unique_together = ["code", "school"]

    def __str__(self):
        school_name = self.school.name if self.school else "Unknown"
        return f"{self.name} ({school_name})"


class Department(models.Model):
    """Model to represent different departments within the school."""

    name = models.CharField(max_length=100)  # e.g., "Mathematics Department"
    code = models.CharField(max_length=10)  # e.g., "MATH"
    description = models.TextField(blank=True, null=True)
    head_of_department = models.ForeignKey(
        "Teacher",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="headed_department",
    )
    # Add school relationship for multi-tenancy
    school = models.ForeignKey(
        "SchoolInformation",
        on_delete=models.CASCADE,
        related_name="departments",
        null=True,
    )

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["school", "code"]),
        ]
        # Ensure codes are unique per school
        unique_together = ["code", "school"]

    def __str__(self):
        school_name = self.school.name if self.school else "Unknown"
        return f"{self.name} ({school_name})"


class Teacher(models.Model):
    GENDER_CHOICES = (
        ("M", "Male"),
        ("F", "Female"),
    )

    full_name = models.CharField(max_length=100)
    staff_id = models.CharField(max_length=10, unique=True, editable=False)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True)
    gender = models.CharField(
        max_length=1, choices=GENDER_CHOICES, blank=True, null=True
    )
    contact_number = models.CharField(max_length=15)
    email = models.EmailField(max_length=100, blank=True, null=True)
    profile_picture = models.ImageField(
        upload_to="profile_pictures/teachers/", null=True, blank=True
    )
    skip_user_creation = models.BooleanField(
        default=False, editable=False
    )  # Flag to skip automatic user creation
    # Add school relationship for multi-tenancy
    school = models.ForeignKey(
        "SchoolInformation",
        on_delete=models.CASCADE,
        related_name="teachers",
        null=True,
    )

    class Meta:
        indexes = [
            models.Index(fields=["staff_id"]),
            models.Index(fields=["school"]),
            models.Index(fields=["department"]),
        ]

    def save(self, *args, **kwargs):
        if not self.staff_id:
            self.staff_id = generate_unique_id(entity_type="teacher", length=6)

        # Ensure teacher gets same school as its department if provided
        if not self.school and self.department and self.department.school:
            self.school = self.department.school

        super().save(*args, **kwargs)

    def get_assigned_classes(self, academic_year=None, term=None):

        # Get active assignments

        query = self.teachersubjectassignment_set.filter(is_active=True)
        if academic_year:
            query = query.filter(academic_year=academic_year)
        if term:
            query = query.filter(term=term)

        
        # Filter out assignments where ClassSubject is not active
        # Get active class-subject combinations
        active_class_subjects = ClassSubject.objects.filter(
            is_active=True
        )
        if academic_year:
            active_class_subjects = active_class_subjects.filter(academic_year=academic_year)
        
        active_class_subject_pairs = active_class_subjects.values_list('class_name_id', 'subject_id')
        
        # Filter assignments to only include those with active ClassSubject
        filtered_assignments = []
        for assignment in query:
            if (assignment.class_assigned.id, assignment.subject.id) in active_class_subject_pairs:
                filtered_assignments.append(assignment)
        
        return filtered_assignments

    def can_enter_scores(self, class_obj, subject):
        # Check if teacher has active assignment
        assignment_exists = self.teachersubjectassignment_set.filter(
            class_assigned=class_obj, subject=subject, is_active=True
        ).exists()
        
        if not assignment_exists:
            return False
        
        # Also check if ClassSubject is active
        class_subject_exists = ClassSubject.objects.filter(
            class_name=class_obj, subject=subject, is_active=True
        ).exists()
        
        return assignment_exists and class_subject_exists

    def total_assigned_classes(self):
        # Get active assignments
        active_assignments = self.teachersubjectassignment_set.filter(is_active=True)
        
        # Filter out assignments where ClassSubject is not active
        # Get active class-subject combinations
        active_class_subjects = ClassSubject.objects.filter(
            is_active=True
        ).values_list('class_name_id', 'subject_id')
        
        # Count assignments that have active ClassSubject
        count = 0
        for assignment in active_assignments:
            if (assignment.class_assigned.id, assignment.subject.id) in active_class_subjects:
                count += 1
        
        return count


    def __str__(self):
        school_name = self.school.name if self.school else "Unknown"
        return f"{self.full_name} ({self.staff_id}) - {school_name}"


class Student(models.Model):
    GENDER_CHOICES = (
        ("M", "Male"),
        ("F", "Female"),
    )

    admission_number = models.CharField(max_length=10, unique=True, editable=False)
    full_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    parent_contact = models.CharField(max_length=15)
    admission_date = models.DateField()
    profile_picture = models.ImageField(
        upload_to="profile_pictures/students/", null=True, blank=True
    )
    form = models.ForeignKey(Form, on_delete=models.SET_NULL, null=True, blank=True)
    learning_area = models.ForeignKey(
        LearningArea, on_delete=models.SET_NULL, null=True, blank=True
    )
    email = models.EmailField(max_length=100, blank=True, null=True)
    # Add school relationship for multi-tenancy
    school = models.ForeignKey(
        "SchoolInformation",
        on_delete=models.CASCADE,
        related_name="students",
        null=True,
    )

    class Meta:
        indexes = [
            models.Index(fields=["admission_number"]),
            models.Index(fields=["learning_area"]),
            models.Index(fields=["form"]),
            models.Index(fields=["school"]),
        ]

    def save(self, *args, **kwargs):
        if not self.admission_number:
            # Generate a unique admission number
            max_attempts = 10
            for attempt in range(max_attempts):
                admission_number = generate_unique_id(entity_type="student", length=5)
                # Check if this admission number already exists
                if not Student.objects.filter(
                    admission_number=admission_number
                ).exists():
                    self.admission_number = admission_number
                    break
            else:
                # If we couldn't generate a unique number after max_attempts, raise an error
                raise ValueError("Could not generate a unique admission number")

        # Ensure student gets same school as its form or learning area if provided
        if not self.school:
            if self.form and self.form.school:
                self.school = self.form.school
            elif self.learning_area and self.learning_area.school:
                self.school = self.learning_area.school

        super().save(*args, **kwargs)

    def get_current_class(self):
        # Filter by school for multi-tenancy
        current_class = self.studentclass_set.filter(
            is_active=True, school=self.school
        ).first()
        return current_class.assigned_class if current_class else None

    def get_class_history(self):
        return self.studentclass_set.all().order_by("-date_assigned")

    @property
    def current_form(self):
        current_class = self.get_current_class()
        return current_class.form if current_class else self.form

    @property
    def current_learning_area(self):
        current_class = self.get_current_class()
        return current_class.learning_area if current_class else self.learning_area

    @property
    def status(self):
        """Return student status: 'active', 'inactive', or 'graduated'"""
        # Check if student is graduated
        if hasattr(self, "archivedstudent"):
            return "graduated"

        # Check if student has active class assignment
        if self.studentclass_set.filter(is_active=True).exists():
            return "active"

        return "inactive"

    @property
    def age(self):
        """Return the calculated age of the student"""
        return self.calculate_age()

    @property
    def current_class(self):
        """Return the name of the current class or None if not assigned"""
        current_class_obj = self.get_current_class()
        return current_class_obj.name if current_class_obj else None

    def calculate_age(self):
        today = date.today()
        return (
            today.year
            - self.date_of_birth.year
            - (
                (today.month, today.day)
                < (self.date_of_birth.month, self.date_of_birth.day)
            )
        )

    def __str__(self):
        school_name = self.school.name if self.school else "Unknown"
        return f"{self.full_name} ({self.admission_number}) - {school_name}"

    # Add this method to the Student model class
    def debug_get_current_class(self):
        """Debug method to diagnose issues with get_current_class"""
        logger = logging.getLogger(__name__)

        logger.info(
            f"Debugging get_current_class for student: {self.full_name} (ID: {self.id})"
        )

        # Check if StudentClass model exists
        try:
            logger.info("StudentClass model exists")
        except LookupError:
            logger.error("StudentClass model does not exist")
            return None

        # Get all class assignments for this student
        all_assignments = StudentClass.objects.filter(student=self)
        logger.info(f"Total class assignments found: {all_assignments.count()}")

        # Get active class assignments
        active_assignments = all_assignments.filter(is_active=True)
        logger.info(f"Active class assignments found: {active_assignments.count()}")

        # Log details of each assignment
        for idx, assignment in enumerate(all_assignments):
            logger.info(f"Assignment {idx+1}:")
            logger.info(
                f"  - Class: {assignment.assigned_class.name if assignment.assigned_class else 'None'}"
            )
            logger.info(f"  - Active: {assignment.is_active}")
            logger.info(f"  - Date Assigned: {assignment.date_assigned}")
            logger.info(
                f"  - School: {assignment.school.name if assignment.school else 'None'}"
            )

        # Get the current class using the original method
        current_class = self.get_current_class()
        if current_class:
            logger.info(
                f"Current class found: {current_class.name} (ID: {current_class.id})"
            )
        else:
            logger.info("No current class found")

        return current_class


class Class(models.Model):
    class_id = models.CharField(max_length=10, unique=True, editable=False)
    name = models.CharField(max_length=20)  # e.g., "1Science", "2Art1"
    form = models.ForeignKey(Form, on_delete=models.SET_NULL, null=True)
    learning_area = models.ForeignKey(
        LearningArea, on_delete=models.SET_NULL, null=True
    )
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    maximum_students = models.SmallIntegerField(default=40)
    # Add school relationship for multi-tenancy
    school = models.ForeignKey(
        "SchoolInformation",
        on_delete=models.CASCADE,
        related_name="classes",
        null=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "academic_year"], name="unique_class_name_academic_year"
            )
        ]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["form"]),
            models.Index(fields=["learning_area"]),
            models.Index(fields=["academic_year"]),
            models.Index(fields=["school"]),
        ]

    def save(self, *args, **kwargs):
        if not self.class_id:

            self.class_id = generate_unique_id("class")


        # Ensure class gets same school as its form, learning area, or academic year
        if not self.school:
            if self.form and self.form.school:
                self.school = self.form.school
            elif self.learning_area and self.learning_area.school:
                self.school = self.learning_area.school
            elif self.academic_year and self.academic_year.school:
                self.school = self.academic_year.school

        super().save(*args, **kwargs)

    def get_current_student_count(self):
        return StudentClass.objects.filter(assigned_class=self, is_active=True).count()

    def is_class_full(self):
        return self.get_current_student_count() >= self.maximum_students

    def __str__(self):
        school_name = self.school.name if self.school else "Unknown"
        return f"{self.name} ({school_name})"


class ClassTeacher(models.Model):
    """
    Tracks the assignment of teachers to classes with history and status.
    Similar to TeacherSubjectAssignment but specifically for class teacher role.
    """

    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    class_assigned = models.ForeignKey(Class, on_delete=models.CASCADE)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    date_assigned = models.DateField(auto_now_add=True)
    assigned_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    is_active = models.BooleanField(default=True)
    # Add school relationship for multi-tenancy
    school = models.ForeignKey(
        "SchoolInformation",
        on_delete=models.CASCADE,
        related_name="class_teachers",
        null=True,
    )

    class Meta:
        indexes = [
            models.Index(fields=["teacher", "is_active"]),
            models.Index(fields=["class_assigned", "academic_year", "is_active"]),
            models.Index(fields=["academic_year", "is_active"]),
            models.Index(fields=["school", "is_active"]),
        ]

    def clean(self):
        super().clean()
        if self.is_active:
            existing = ClassTeacher.objects.filter(
                class_assigned=self.class_assigned,
                academic_year=self.academic_year,
                is_active=True,
                school=self.school,  # Add school filter for multi-tenancy
            ).exclude(pk=self.pk)

            if existing.exists():
                raise ValidationError(
                    f"There is already an active class teacher for {self.class_assigned} "
                    f"for {self.academic_year}."
                )

    def save(self, *args, **kwargs):
        # Ensure class teacher assignment gets school from teacher, class, or academic year
        if not self.school:
            if self.teacher and self.teacher.school:
                self.school = self.teacher.school
            elif self.class_assigned and self.class_assigned.school:
                self.school = self.class_assigned.school
            elif self.academic_year and self.academic_year.school:
                self.school = self.academic_year.school

        super().save(*args, **kwargs)

    def __str__(self):
        school_name = self.school.name if self.school else "Unknown"
        return f"{self.teacher.full_name} - Class Teacher for {self.class_assigned.name} ({school_name})"


class StudentClass(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    assigned_class = models.ForeignKey(Class, on_delete=models.CASCADE)
    date_assigned = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    assigned_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    # Add school relationship for multi-tenancy
    school = models.ForeignKey(
        "SchoolInformation",
        on_delete=models.CASCADE,
        related_name="student_classes",
        null=True,
    )

    class Meta:
        indexes = [
            models.Index(fields=["student", "is_active"]),
            models.Index(fields=["assigned_class", "is_active"]),
            models.Index(fields=["student", "assigned_class", "is_active"]),
            models.Index(fields=["school", "is_active"]),
        ]

    def clean(self):
        super().clean()
        if self.is_active:
            existing = StudentClass.objects.filter(
                student=self.student, is_active=True, school=self.school
            ).exclude(pk=self.pk)

            if existing.exists():
                raise ValidationError(
                    f"Student {self.student} is already assigned to an active class in this school."
                )

    def save(self, *args, **kwargs):
        # Ensure student class gets school from student, assigned class, or assigned_by
        if not self.school:
            if self.student and self.student.school:
                self.school = self.student.school
            elif self.assigned_class and self.assigned_class.school:
                self.school = self.assigned_class.school
            elif self.assigned_by and self.assigned_by.school:
                self.school = self.assigned_by.school

        super().save(*args, **kwargs)

    def __str__(self):
        school_name = self.school.name if self.school else "Unknown"
        return f"{self.student} - {self.assigned_class} ({school_name})"


class Subject(models.Model):
    subject_code = models.CharField(max_length=10, unique=True, editable=False)
    subject_name = models.CharField(max_length=100)
    learning_area = models.ForeignKey(
        LearningArea, on_delete=models.SET_NULL, null=True
    )  # Changed to ForeignKey
    department = models.ForeignKey(
        Department, on_delete=models.CASCADE, null=True, blank=True
    )
    # Add school relationship for multi-tenancy
    school = models.ForeignKey(
        "SchoolInformation",
        on_delete=models.CASCADE,
        related_name="subjects",
        null=True,
    )

    class Meta:
        indexes = [
            models.Index(fields=["learning_area"]),
            models.Index(fields=["department"]),
            models.Index(fields=["school"]),
        ]
        # Ensure subject codes are unique per school
        unique_together = ["subject_code", "school"]

    def save(self, *args, **kwargs):
        if not self.subject_code:
            self.subject_code = generate_unique_id(entity_type="subject", length=5)

        # Ensure subject gets same school as its department or learning area if provided
        if not self.school:
            if self.department and self.department.school:
                self.school = self.department.school
            elif self.learning_area and self.learning_area.school:
                self.school = self.learning_area.school

        super().save(*args, **kwargs)

    @property
    def name(self):
        """Return the subject name for template compatibility"""
        return self.subject_name

    def __str__(self):
        school_name = self.school.name if self.school else "Unknown"
        return f"{self.subject_code} - {self.subject_name} ({school_name})"


class TeacherSubjectAssignment(models.Model):
    assignment_id = models.CharField(max_length=10, unique=True, editable=False)
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    class_assigned = models.ForeignKey(Class, on_delete=models.CASCADE)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    date_assigned = models.DateField(auto_now_add=True)
    assigned_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    is_active = models.BooleanField(default=True)

    # Add new fields for tracking assignment history
    last_modified = models.DateTimeField(auto_now=True)
    previous_teacher = models.ForeignKey(
        Teacher,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="previous_assignments",
    )
    assignment_history = models.JSONField(default=list, blank=True)

    # Add school relationship for multi-tenancy
    school = models.ForeignKey(
        "SchoolInformation",
        on_delete=models.CASCADE,
        related_name="teacher_subject_assignments",
        null=True,
    )

    class Meta:
        indexes = [
            models.Index(fields=["teacher", "is_active"]),
            models.Index(fields=["class_assigned", "subject", "is_active"]),
            models.Index(fields=["academic_year", "is_active"]),
            models.Index(
                fields=["subject", "class_assigned", "academic_year", "is_active"]
            ),
            models.Index(fields=["school", "is_active"]),
        ]

    def clean(self):
        super().clean()
        if self.is_active:
            existing = TeacherSubjectAssignment.objects.filter(
                subject=self.subject,
                class_assigned=self.class_assigned,
                academic_year=self.academic_year,
                is_active=True,
                school=self.school,  # Add school filter for multi-tenancy
            ).exclude(pk=self.pk)

            if existing.exists():
                raise ValidationError(
                    f"There is already an active assignment for {self.subject} in {self.class_assigned} "
                    f"for {self.academic_year}."
                )

    def save(self, *args, **kwargs):
        if not self.assignment_id:
            self.assignment_id = generate_unique_id(entity_type="assignment", length=5)

        # Ensure assignment gets school from teacher, subject, class, or academic year
        if not self.school:
            if self.teacher and self.teacher.school:
                self.school = self.teacher.school
            elif self.subject and self.subject.school:
                self.school = self.subject.school
            elif self.class_assigned and self.class_assigned.school:
                self.school = self.class_assigned.school
            elif self.academic_year and self.academic_year.school:
                self.school = self.academic_year.school

        # Track assignment history when a teacher is changed
        if self.pk:  # If this is an update
            try:
                old_instance = TeacherSubjectAssignment.objects.get(pk=self.pk)
                if old_instance.teacher != self.teacher:
                    self.previous_teacher = old_instance.teacher

                    # Add to assignment history
                    history_entry = {
                        "date": date.today().isoformat(),
                        "previous_teacher_id": old_instance.teacher.staff_id,
                        "previous_teacher_name": old_instance.teacher.full_name,
                        "new_teacher_id": self.teacher.staff_id,
                        "new_teacher_name": self.teacher.full_name,
                        "action": "reassigned",
                    }

                    if isinstance(self.assignment_history, list):
                        self.assignment_history.append(history_entry)
                    else:
                        self.assignment_history = [history_entry]
            except TeacherSubjectAssignment.DoesNotExist:
                pass

        super().save(*args, **kwargs)

    @classmethod
    def get_teacher_workload(cls, teacher_id, academic_year=None, school=None):
        """
        Get a summary of a teacher's workload

        Args:
            teacher_id: The ID of the teacher
            academic_year: Optional academic year filter
            school: Optional school filter for multi-tenancy

        Returns:
            dict: Summary of teacher's workload
        """
        query = cls.objects.filter(teacher__staff_id=teacher_id, is_active=True)

        if academic_year:
            query = query.filter(academic_year=academic_year)

        if school:
            query = query.filter(school=school)

        # Group by class and count subjects
        class_summary = {}
        for assignment in query:
            class_name = assignment.class_assigned.name
            if class_name not in class_summary:
                class_summary[class_name] = {
                    "class_id": assignment.class_assigned.id,
                    "subjects": [],
                }

            class_summary[class_name]["subjects"].append(
                {
                    "subject_id": assignment.subject.id,
                    "subject_name": assignment.subject.subject_name,
                    "assignment_id": assignment.assignment_id,
                }
            )

        return {
            "total_classes": len(class_summary),
            "total_subjects": query.count(),
            "class_details": class_summary,
        }

    def __str__(self):
        school_name = self.school.name if self.school else "Unknown"
        return (
            f"{self.teacher} - {self.subject} - {self.class_assigned} ({school_name})"
        )


class Assessment(models.Model):
    ASSESSMENT_TYPES = (
        ("class_score", "FIRST SEMESTER"),  # Fixed typo in 'FIRST'
        ("exam_score", "SECOND SEMESTER"),

        ("mock_exam", "MOCK EXAM"),

    )

    assessment_id = models.CharField(max_length=10, unique=True, editable=False)
    class_subject = models.ForeignKey("ClassSubject", on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    term = models.ForeignKey(
        Term,
        on_delete=models.CASCADE,

        null=True,
        blank=True,
        help_text="Term for which this assessment is recorded (required for class_score and exam_score, optional for mock_exam)",
    )
    assessment_type = models.CharField(max_length=20, choices=ASSESSMENT_TYPES)
    
    # Reference to MockExam for mock exam assessments
    mock_exam = models.ForeignKey(
        "MockExam",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assessments",
        help_text="Mock exam this assessment belongs to (only for mock_exam type)"
    )


    # Individual score components for class work
    individual_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Raw individual assignment score",
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )

    class_test_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Raw class test score",
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )

    project_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Raw project score",
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )

    group_work_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Raw group work score",
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )

    # Calculated scores
    class_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Calculated weighted class score",
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )

    exam_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Scaled exam score (calculated from raw score)",
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )

    raw_exam_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Raw exam score (0-100) before scaling",
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    total_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        null=True,
        blank=True,
    )
    grade = models.CharField(max_length=2, blank=True, null=True)
    remarks = models.CharField(max_length=50, blank=True, null=True)
    position = models.PositiveSmallIntegerField(
        blank=True, null=True
    )  # Changed to SmallIntegerField
    date_recorded = models.DateTimeField(auto_now_add=True)
    recorded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    # Add school relationship for multi-tenancy
    school = models.ForeignKey(
        "SchoolInformation",
        on_delete=models.CASCADE,
        related_name="assessments",
        null=True,
    )

    class Meta:
        constraints = [

            # Unique constraint for term-based assessments (class_score, exam_score)
            models.UniqueConstraint(
                fields=["class_subject", "student", "term", "assessment_type"],
                condition=models.Q(assessment_type__in=["class_score", "exam_score"]),
                name="unique_term_assessment",
            ),
            # Unique constraint for mock exams (uses mock_exam instead of term)
            models.UniqueConstraint(
                fields=["class_subject", "student", "mock_exam"],
                condition=models.Q(assessment_type="mock_exam", mock_exam__isnull=False),
                name="unique_mock_exam_assessment",
            ),

        ]
        indexes = [
            models.Index(fields=["class_subject", "student"]),
            models.Index(fields=["date_recorded"]),
            models.Index(
                fields=["class_subject", "total_score"]
            ),  # Added for position calculations
            models.Index(fields=["student", "class_subject", "assessment_type"]),
            models.Index(fields=["term"]),  # Added for term-based queries
            models.Index(
                fields=["class_subject", "term"]
            ),  # Added for term-specific class queries
        ]

    def clean(self):
        if self.recorded_by.role == "teacher":
            try:
                teacher = Teacher.objects.get(user=self.recorded_by)
                if not teacher.can_enter_scores(
                    self.class_subject.class_name, self.class_subject.subject
                ):
                    raise ValidationError(
                        "You are not authorized to enter scores for this class and subject."
                    )
            except Teacher.DoesNotExist:
                raise ValidationError("Recorded by user is not a teacher.")

        if not StudentClass.objects.filter(
            student=self.student,
            assigned_class=self.class_subject.class_name,
            is_active=True,
        ).exists():
            raise ValidationError("Student is not in this class.")

        
        # Validate term requirement based on assessment type
        if self.assessment_type in ['class_score', 'exam_score']:
            if not self.term:
                raise ValidationError(
                    f"Term is required for {self.get_assessment_type_display()} assessments."
                )
        elif self.assessment_type == 'mock_exam':
            # For mock exams, term is optional but mock_exam is required
            if not self.mock_exam:
                raise ValidationError(
                    "Mock exam is required for mock_exam type assessments."
                )
        
        # For mock exams, ensure uniqueness per student and mock exam
        if self.assessment_type == 'mock_exam' and self.mock_exam:
            existing = Assessment.objects.filter(
                class_subject=self.class_subject,
                student=self.student,
                mock_exam=self.mock_exam,
                assessment_type='mock_exam'
            ).exclude(pk=self.pk if self.pk else None)
            
            if existing.exists():
                raise ValidationError(
                    f"An assessment already exists for this student in {self.mock_exam.name}."
                )


    def save(self, *args, **kwargs):
        if not self.assessment_id:
            self.assessment_id = generate_unique_id(entity_type="assessment", length=5)

        # Set school from related objects if not explicitly provided
        if not self.school:
            # Try to get school from term first (most reliable for term-specific data)
            if self.term and self.term.school:
                self.school = self.term.school
            # Then try from student
            elif self.student and self.student.school:
                self.school = self.student.school
            # Then try from class_subject's class_name
            elif (
                self.class_subject
                and self.class_subject.class_name
                and self.class_subject.class_name.school
            ):
                self.school = self.class_subject.class_name.school
            # Then try from recorded_by user
            elif self.recorded_by and self.recorded_by.school:
                self.school = self.recorded_by.school

        # Get the active scoring configuration for this school
        scoring_config = ScoringConfiguration.get_active_config(self.school)

        # Calculate class score from individual components if all are provided
        if (
            all(
                [
                    self.individual_score is not None,
                    self.class_test_score is not None,
                    self.project_score is not None,
                    self.group_work_score is not None,
                ]
            )
            and scoring_config
        ):
            self.class_score = scoring_config.calculate_class_score(
                self.individual_score,
                self.class_test_score,
                self.project_score,
                self.group_work_score,
            )


        # For mock exams, total_score is the same as raw_exam_score
        if self.assessment_type == 'mock_exam' and self.raw_exam_score is not None:
            self.total_score = Decimal(str(self.raw_exam_score))
        
        # Calculate total score if both class_score and exam_score are provided (for term-based assessments)
        elif self.class_score is not None and self.exam_score is not None:

            if scoring_config:
                # Both class_score and exam_score are already scaled
                # Total score is the sum of scaled class score and scaled exam score
                # Ensure both values are Decimal to avoid type mismatch
                class_score_decimal = Decimal(str(self.class_score))
                exam_score_decimal = Decimal(str(self.exam_score))
                self.total_score = class_score_decimal + exam_score_decimal
            else:
                # Fallback to simple addition if no configuration
                # Ensure both values are Decimal to avoid type mismatch
                class_score_decimal = Decimal(str(self.class_score))
                exam_score_decimal = Decimal(str(self.exam_score))
                self.total_score = class_score_decimal + exam_score_decimal

        # Automatically calculate grade and remarks based on total score using GradingSystem
        if self.total_score is not None:
            grade_info = GradingSystem.get_grade_for_score(
                self.total_score, self.school
            )
            if grade_info:
                self.grade = grade_info.grade_letter
                self.remarks = grade_info.remarks
            else:
                # Fallback if no grading system is configured
                self.grade = "N/A"
                self.remarks = "Not Graded"

        # Call the superclass save method to persist changes
        super().save(*args, **kwargs)

        # Calculate positions only if total_score has changed
        if self.total_score is not None:

            # For term-based assessments, calculate positions within the term
            if self.assessment_type in ['class_score', 'exam_score'] and self.term:
                Assessment.calculate_positions(self.class_subject, self.term)
            # For mock exams, calculate positions within the mock exam
            elif self.assessment_type == 'mock_exam' and self.mock_exam:
                Assessment.calculate_mock_exam_positions(self.class_subject, self.mock_exam)


    @classmethod
    def calculate_positions(cls, class_subject, term=None):
        """
        Calculate and update the position of all students in the given class_subject for a specific term.

        Only includes term-based assessments (class_score, exam_score), excluding mock exams.

        """
        filter_kwargs = {
            "class_subject": class_subject,
            "total_score__isnull": False,  # Only include assessments with valid total scores

            "assessment_type__in": ["class_score", "exam_score"],  # Exclude mock exams

        }
        if term:
            filter_kwargs["term"] = term

        assessments = cls.objects.filter(**filter_kwargs).order_by("-total_score")

        # Use bulk update to avoid recursive save() calls
        updated_assessments = []
        current_position = 1
        previous_score = None

        for index, assessment in enumerate(assessments):
            # Handle tied scores - same position for equal scores
            if previous_score is not None and assessment.total_score != previous_score:
                current_position = index + 1

            assessment.position = current_position
            updated_assessments.append(assessment)
            previous_score = assessment.total_score

        # Use batch processing for better MySQL performance
        batch_size = 100
        if updated_assessments:
            cls.objects.bulk_update(
                updated_assessments, ["position"], batch_size=batch_size
            )


    @classmethod
    def calculate_mock_exam_positions(cls, class_subject, mock_exam):
        """
        Calculate and update the position of all students in the given class_subject for a specific mock exam.
        Only includes mock exam assessments.
        """
        assessments = cls.objects.filter(
            class_subject=class_subject,
            mock_exam=mock_exam,
            assessment_type='mock_exam',
            total_score__isnull=False,  # Only include assessments with valid total scores
        ).order_by("-total_score")

        # Use bulk update to avoid recursive save() calls
        updated_assessments = []
        current_position = 1
        previous_score = None

        for index, assessment in enumerate(assessments):
            # Handle tied scores - same position for equal scores
            if previous_score is not None and assessment.total_score != previous_score:
                current_position = index + 1

            assessment.position = current_position
            updated_assessments.append(assessment)
            previous_score = assessment.total_score

        # Use batch processing for better MySQL performance
        batch_size = 100
        if updated_assessments:
            cls.objects.bulk_update(
                updated_assessments, ["position"], batch_size=batch_size
            )


    def __str__(self):
        return f"{self.student} - {self.class_subject} - {self.assessment_type}"



class MockExam(models.Model):
    """
    Model to manage mock exam scenarios/names.
    Allows creating named mock exams that can be activated/deactivated.
    Only active mock exams are displayed for score entry.
    """
    name = models.CharField(
        max_length=200,
        help_text="Name or scenario for this mock exam (e.g., 'Mock Exam 1', 'Mid-Term Practice', etc.)"
    )
    exam_date = models.DateField(
        help_text="Date when this mock exam was/will be conducted"
    )
    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.CASCADE,
        related_name="mock_exams",
        help_text="Academic year this mock exam belongs to"
    )
    school = models.ForeignKey(
        "SchoolInformation",
        on_delete=models.CASCADE,
        related_name="mock_exams",
        null=True,
        help_text="School this mock exam belongs to"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Only active mock exams are displayed for score entry"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Optional description or notes about this mock exam"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_mock_exams",
        help_text="User who created this mock exam"
    )
    
    class Meta:
        verbose_name = "Mock Exam"
        verbose_name_plural = "Mock Exams"
        ordering = ["-exam_date", "-created_at"]
        indexes = [
            models.Index(fields=["school", "academic_year", "is_active"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["exam_date"]),
        ]
        # Ensure unique names per school and academic year
        unique_together = ["name", "school", "academic_year"]
    
    def save(self, *args, **kwargs):
        # Set school from academic_year if not provided
        if not self.school and self.academic_year:
            self.school = self.academic_year.school
        super().save(*args, **kwargs)
    
    def __str__(self):
        school_name = self.school.name if self.school else "Unknown"
        status = " (Active)" if self.is_active else " (Inactive)"
        return f"{self.name} - {self.exam_date} ({school_name}){status}"



class ClassSubject(models.Model):
    class_subject_id = models.CharField(max_length=10, unique=True, editable=False)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    class_name = models.ForeignKey(Class, on_delete=models.CASCADE)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)

    is_active = models.BooleanField(default=True)
    date_assigned = models.DateField(auto_now_add=True)
    assigned_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )

    # Add direct school field for multi-tenancy
    school = models.ForeignKey(
        "SchoolInformation",
        on_delete=models.CASCADE,
        related_name="class_subjects",
        null=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(

                fields=["subject", "class_name", "academic_year", "is_active"],
                condition=models.Q(is_active=True),
                name="unique_active_class_subject",
            )
        ]
        indexes = [
            models.Index(fields=["subject", "is_active"]),
            models.Index(fields=["class_name", "is_active"]),
            models.Index(fields=["academic_year", "is_active"]),
            models.Index(fields=["school", "is_active"]),
            models.Index(fields=["is_active"]),

        ]

    def save(self, *args, **kwargs):
        if not self.class_subject_id:

            self.class_subject_id = generate_unique_id("class_subject")


        # Automatically set school from related models if not provided
        if not self.school:
            if self.class_name and self.class_name.school:
                self.school = self.class_name.school
            elif self.subject and self.subject.school:
                self.school = self.subject.school

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.subject.subject_name} in {self.class_name.name} ({self.academic_year.name})"


class AttendanceRecord(models.Model):
    ATTENDANCE_REASONS = (
        ("present", "Present"),
        ("absent", "Absent"),
        ("excused", "Excused Absence"),
        ("sick", "Sick Leave"),
    )

    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    date = models.DateField()
    is_present = models.BooleanField(default=True)
    reason = models.CharField(
        max_length=20, choices=ATTENDANCE_REASONS, default="present"
    )
    recorded_by = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    # Add school relationship for multi-tenancy
    school = models.ForeignKey(
        "SchoolInformation",
        on_delete=models.CASCADE,
        related_name="attendance_records",
        null=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "date", "school"], name="unique_attendance_record"
            )
        ]
        indexes = [
            models.Index(fields=["student", "term"]),
            models.Index(fields=["date"]),
            models.Index(fields=["student", "date"]),
            models.Index(fields=["school", "date"]),
        ]

    def save(self, *args, **kwargs):
        # Ensure attendance record gets school from student, term, or recorded_by
        if not self.school:
            if self.student and self.student.school:
                self.school = self.student.school
            elif self.term and self.term.school:
                self.school = self.term.school
            elif self.recorded_by and self.recorded_by.school:
                self.school = self.recorded_by.school

        super().save(*args, **kwargs)

    def __str__(self):
        school_name = self.school.name if self.school else "Unknown"
        return f"{self.student} - {self.date} ({school_name})"


class GradingSystem(models.Model):
    grade_letter = models.CharField(max_length=2)
    min_score = models.DecimalField(max_digits=5, decimal_places=2)
    max_score = models.DecimalField(max_digits=5, decimal_places=2)
    remarks = models.CharField(max_length=50)
    description = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    # Add school relationship for multi-tenancy
    school = models.ForeignKey(
        "SchoolInformation",
        on_delete=models.CASCADE,
        related_name="grading_systems",
        null=True,
    )

    class Meta:
        indexes = [
            models.Index(fields=["grade_letter"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["school", "grade_letter"]),
        ]
        ordering = ["-min_score"]
        # Ensure grade letters are unique per school
        unique_together = ["grade_letter", "school"]

    def __str__(self):
        school_name = self.school.name if self.school else "Global"
        return f"{self.grade_letter} ({self.min_score}-{self.max_score}): {self.remarks} ({school_name})"

    @classmethod
    def get_grade_for_score(cls, score, school=None):
        """
        Returns the appropriate grade object for a given score.

        Args:
            score: The numeric score to find a grade for
            school: Optional school filter for multi-tenancy

        Returns:
            GradingSystem: The grade object or None if no matching grade
        """
        if score is None:
            return None

        try:
            query = cls.objects.filter(
                min_score__lte=score, max_score__gte=score, is_active=True
            )

            # Filter by school if provided
            if school:
                query = query.filter(school=school)

            grade = query.first()

            return grade
        except Exception:
            return None

    @classmethod
    def get_all_active_grades(cls, school=None):
        """
        Returns all active grades ordered by min_score (descending).
        Used for populating grade tables in reports.

        Args:
            school: Optional school filter for multi-tenancy
        """
        query = cls.objects.filter(is_active=True)

        # Filter by school if provided
        if school:
            query = query.filter(school=school)

        return query.order_by("-min_score")


class PerformanceRequirement(models.Model):
    """
    Model to store academic performance requirements for student promotion and assessment.
    Contains settings for minimum average scores and other academic thresholds.
    """

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    # Promotion requirements
    min_average_score_for_promotion = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=40.00,
        help_text="Minimum average score required for a student to be promoted",
    )
    min_passing_grade = models.ForeignKey(
        GradingSystem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="min_passing_requirements",
        help_text="Minimum grade letter required to pass a subject",
    )
    max_failed_subjects = models.PositiveSmallIntegerField(
        default=3,
        help_text="Maximum number of subjects a student can fail and still be promoted",
    )

    # Calculation method
    CALCULATION_METHODS = (
        ("simple", "Simple Average"),
        ("weighted", "Weighted Average"),
    )
    calculation_method = models.CharField(
        max_length=20,
        choices=CALCULATION_METHODS,
        default="simple",
        help_text="Method used to calculate student averages",
    )

    # Term weighting (for weighted average)
    first_term_weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=30.00,
        help_text="Weight of first term scores (percentage)",
    )
    second_term_weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=30.00,
        help_text="Weight of second term scores (percentage)",
    )
    third_term_weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=40.00,
        help_text="Weight of third term scores (percentage)",
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Add school relationship for multi-tenancy
    school = models.ForeignKey(
        "SchoolInformation",
        on_delete=models.CASCADE,
        related_name="performance_requirements",
        null=True,
    )

    class Meta:
        indexes = [
            models.Index(fields=["is_active"]),
            models.Index(fields=["school", "is_active"]),
        ]
        verbose_name = "Performance Requirement"
        verbose_name_plural = "Performance Requirements"
        # Ensure names are unique per school
        unique_together = ["name", "school"]

    def clean(self):
        """Validate that weights sum to 100% for weighted calculation method"""
        if self.calculation_method == "weighted":
            total_weight = (
                self.first_term_weight
                + self.second_term_weight
                + self.third_term_weight
            )
            if abs(total_weight - 100) > 0.01:  # Allow small floating point differences
                raise ValidationError("Term weights must sum to 100%")

    @classmethod
    def get_active(cls, school=None):
        """
        Returns the active performance requirement configuration

        Args:
            school: Optional school filter for multi-tenancy
        """
        query = cls.objects.filter(is_active=True)

        # Filter by school if provided
        if school:
            query = query.filter(school=school)

        return query.first()

    def __str__(self):
        school_name = self.school.name if self.school else "Global"
        return f"{self.name} ({school_name})"


class Notification(models.Model):
    RECIPIENT_ROLE_CHOICES = (
        ("admin", "Admin"),
        ("teacher", "Teacher"),
        ("student", "Student"),
    )

    recipient_role = models.CharField(max_length=10, choices=RECIPIENT_ROLE_CHOICES)
    recipient = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=["recipient", "is_read"]),
            models.Index(fields=["timestamp"]),
        ]

    def __str__(self):
        return f"{self.recipient_role} - {self.message}"


class ArchivedStudent(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE)
    completion_date = models.DateField(auto_now_add=True)
    final_form = models.ForeignKey(Form, on_delete=models.PROTECT)
    final_learning_area = models.ForeignKey(LearningArea, on_delete=models.PROTECT)
    archived_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["completion_date"]),
            models.Index(fields=["final_form", "final_learning_area"]),
        ]

    def __str__(self):
        return f"{self.student.full_name} (Completed: {self.completion_date})"


class StudentTermRemarks(models.Model):
    """
    Model for class teachers to enter term/semester remarks for students.
    Includes attendance summaries and comments on interest, conduct, and attitude.
    """

    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    class_assigned = models.ForeignKey(Class, on_delete=models.CASCADE)
    class_teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    # Add school relationship for multi-tenancy
    school = models.ForeignKey(
        "SchoolInformation",
        on_delete=models.CASCADE,
        related_name="student_term_remarks",
        null=True,
    )

    # Attendance summary
    days_present = models.PositiveSmallIntegerField(default=0)
    days_absent = models.PositiveSmallIntegerField(default=0)
    total_school_days = models.PositiveSmallIntegerField(default=0)

    # Flag to determine if attendance should be auto-calculated
    auto_calculate_attendance = models.BooleanField(default=True)

    # Teacher remarks on different aspects

    interest_remarks = models.CharField(max_length=200, blank=True, null=True)
    conduct_remarks = models.CharField(max_length=200, blank=True, null=True)
    attitude_remarks = models.CharField(max_length=200, blank=True, null=True)


    # Overall remarks
    general_remarks = models.TextField(blank=True, null=True)

    # Metadata
    date_created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "academic_year", "term"],
                name="unique_student_term_remarks",
            )
        ]
        indexes = [
            models.Index(fields=["student", "academic_year", "term"]),
            models.Index(fields=["class_assigned", "term"]),
            models.Index(fields=["class_teacher"]),
        ]

    def clean(self):
        """Validate that the class teacher is assigned to this class."""
        # Skip validation if we don't have all the necessary fields populated yet
        if not all(
            [self.class_assigned, self.class_teacher, self.academic_year, self.student]
        ):
            return

        # Check if teacher is assigned to this class, but just provide a warning
        if not ClassTeacher.objects.filter(
            class_assigned=self.class_assigned,
            teacher=self.class_teacher,
            academic_year=self.academic_year,
            is_active=True,
        ).exists():
            from django.core.exceptions import ValidationError

            # Use warning level instead of a hard validation error
            from django.contrib import messages

            # This will show as a warning in the admin form but not prevent saving
            messages.warning(
                None,
                "Note: This teacher is not assigned as the class teacher for this class.",
            )

        # Validate that the student is in this class - only if both fields are set
        if self.student and self.class_assigned:
            if not StudentClass.objects.filter(
                student=self.student, assigned_class=self.class_assigned, is_active=True
            ).exists():
                from django.core.exceptions import ValidationError

                # This is still a critical validation error
                raise ValidationError("Student is not in this class.")

        # Validate attendance data if provided
        if not self.auto_calculate_attendance and all(
            [
                self.days_present is not None,
                self.days_absent is not None,
                self.total_school_days is not None,
            ]
        ):
            if self.total_school_days < (self.days_present + self.days_absent):
                from django.core.exceptions import ValidationError

                raise ValidationError(
                    "Total school days cannot be less than the sum of days present and absent."
                )

    def update_attendance_from_records(self):
        """Calculate attendance from AttendanceRecord model."""
        attendance = AttendanceRecord.objects.filter(
            student=self.student, term=self.term
        )
        self.days_present = attendance.filter(is_present=True).count()
        self.days_absent = attendance.filter(is_present=False).count()

        # Get term duration in days (or use default if needed)
        try:
            term_duration = (self.term.end_date - self.term.start_date).days + 1
            # Account for weekends - assuming 5 school days per week on average
            # Adjust this calculation based on your school's actual schedule
            self.total_school_days = max(
                round(term_duration * 5 / 7), self.days_present + self.days_absent
            )
        except:
            # Fallback to sum of present and absent days
            self.total_school_days = self.days_present + self.days_absent

    def save(self, *args, **kwargs):
        # Set school from related objects if not explicitly provided
        if not self.school:
            # Try to get school from student
            if self.student and hasattr(self.student, "school") and self.student.school:
                self.school = self.student.school
            # Then try from class_assigned
            elif (
                self.class_assigned
                and hasattr(self.class_assigned, "school")
                and self.class_assigned.school
            ):
                self.school = self.class_assigned.school
            # Then try from class_teacher
            elif (
                self.class_teacher
                and hasattr(self.class_teacher, "school")
                and self.class_teacher.school
            ):
                self.school = self.class_teacher.school
            # Then try from academic_year
            elif (
                self.academic_year
                and hasattr(self.academic_year, "school")
                and self.academic_year.school
            ):
                self.school = self.academic_year.school
            # Then try from term
            elif self.term and hasattr(self.term, "school") and self.term.school:
                self.school = self.term.school

        # Auto-calculate attendance totals if flag is set
        if self.auto_calculate_attendance:
            self.update_attendance_from_records()

        super().save(*args, **kwargs)

    def attendance_percentage(self):
        """Calculate attendance percentage."""
        if self.total_school_days > 0:
            return round((self.days_present / self.total_school_days) * 100, 1)
        return 0

    def __str__(self):
        return f"Remarks for {self.student.full_name} - {self.term}"


class SchoolAuthoritySignature(models.Model):
    """
    Model to store signatures of different school authorities that can appear on reports.
    """

    AUTHORITY_TYPES = (
        ("headmaster", "Headmaster/Principal"),
        ("academic_head", "Academic Headmaster"),
        ("deputy_head", "Deputy Headmaster"),
        ("exam_officer", "Examination Officer"),
        ("other", "Other Authority"),
    )

    authority_type = models.CharField(max_length=20, choices=AUTHORITY_TYPES)
    name = models.CharField(max_length=100)
    title = models.CharField(max_length=100)
    signature = models.ImageField(upload_to="static/signatures/")
    is_active = models.BooleanField(default=True)
    custom_title = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Custom title if 'Other Authority' is selected",
    )

    # Link to school information
    school = models.ForeignKey(
        "SchoolInformation",
        on_delete=models.CASCADE,
        related_name="authority_signatures",
    )

    # Metadata
    date_created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("school", "authority_type")
        verbose_name = "School Authority Signature"
        verbose_name_plural = "School Authority Signatures"

    def clean(self):
        if self.authority_type == "other" and not self.custom_title:
            raise ValidationError(
                "Custom title is required when 'Other Authority' is selected."
            )

    def display_title(self):
        """Return the appropriate title to display."""
        if self.authority_type == "other":
            return self.custom_title
        return self.get_authority_type_display()

    def __str__(self):
        return f"{self.name} - {self.display_title()}"


class SchoolInformation(models.Model):
    """
    Model to store school information that can be used in reports and official documents.
    Modified to support multiple schools in a multi-tenant architecture.
    """

    name = models.CharField(max_length=100)
    short_name = models.CharField(
        max_length=20, help_text="Abbreviation or short name of the school"
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        help_text="URL-friendly version of the school name, used in subdomains",
        default="default-school",  # Add a default value
    )
    address = models.TextField()
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    phone_number = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)

    # School identifiers
    school_code = models.CharField(
        max_length=20, blank=True, null=True, help_text="Official school code/ID"
    )

    # Visual elements

    logo = models.ImageField(upload_to="static/school_image/", blank=True, null=True)
    school_stamp = models.ImageField(
        upload_to="static/school_image/", blank=True, null=True
    )


    # Report card elements
    report_header = models.TextField(
        blank=True, null=True, help_text="Custom header text for reports"
    )
    report_footer = models.TextField(
        blank=True, null=True, help_text="Custom footer text for reports"
    )

    # School motto and vision
    motto = models.CharField(max_length=200, blank=True, null=True)
    vision = models.TextField(blank=True, null=True)
    mission = models.TextField(blank=True, null=True)

    # System settings
    grading_system_description = models.TextField(
        blank=True,
        null=True,
        help_text="Description of the grading system to appear on reports",
    )

    # Current Term and Academic Year Settings
    current_academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="current_for_school",
    )
    current_term = models.ForeignKey(
        Term,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="current_for_school",
    )

    # Active flag (now indicates if the school is active, not singleton pattern)
    is_active = models.BooleanField(default=True)

    # Metadata
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="created_school_info"
    )
    updated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="updated_school_info"
    )
    date_created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "School Information"
        verbose_name_plural = "School Information"

    def save(self, *args, **kwargs):
        """
        Update the active status of related academic year and term records.
        """
        # Generate slug if not provided
        if not self.slug:
            self.slug = slugify(self.name)

        # Save the object first
        super().save(*args, **kwargs)

        # Update current academic year status
        if self.current_academic_year:
            # Turn off is_current for all other academic years for this school
            AcademicYear.objects.filter(
                school=self,
                is_current=True,
            ).exclude(
                pk=self.current_academic_year.pk
            ).update(is_current=False)

            # Set the selected academic year as current
            AcademicYear.objects.filter(pk=self.current_academic_year.pk).update(
                is_current=True
            )

        # Update current term status
        if self.current_term:
            # Turn off is_current for all terms for this school
            Term.objects.filter(
                school=self,
                is_current=True,
            ).exclude(
                pk=self.current_term.pk
            ).update(is_current=False)

            # Set the selected term as current
            Term.objects.filter(pk=self.current_term.pk).update(is_current=True)

    def get_signature(self, authority_type):
        """Get the active signature for a specific authority type."""
        try:
            return self.authority_signatures.get(
                authority_type=authority_type, is_active=True
            )
        except SchoolAuthoritySignature.DoesNotExist:
            return None

    @property
    def headmaster_signature(self):
        """Convenience method to get the headmaster's signature."""
        return self.get_signature("headmaster")

    @property
    def academic_head_signature(self):
        """Convenience method to get the academic headmaster's signature."""
        return self.get_signature("academic_head")

    @classmethod
    def get_active(cls):
        """
        Get the active school information record.
        This method is maintained for backward compatibility.
        In multi-tenant context, it should be called with a school parameter.
        """
        try:
            return cls.objects.filter(is_active=True).first()
        except cls.DoesNotExist:
            # Return the most recently updated record if no active record exists
            return cls.objects.order_by("-last_updated").first()

    @classmethod
    def get_school_by_slug(cls, slug):
        """Get a school by its slug."""
        try:
            return cls.objects.get(slug=slug, is_active=True)
        except cls.DoesNotExist:
            return None

    @classmethod
    def get_current_academic_year(cls, school=None):
        """Get the current academic year for a specific school."""
        if school:
            # First check if the school has a current academic year set directly
            if school.current_academic_year:
                return school.current_academic_year

            # If not, look for an academic year marked as current for this school
            current_year = AcademicYear.objects.filter(
                school=school, is_current=True
            ).first()
            if current_year:
                return current_year

        # For superadmins or if no school-specific year is found
        if not school:
            # Return any academic year marked as current (for superadmins)
            return AcademicYear.objects.filter(is_current=True).first()

        # If we get here, there's no current academic year for this school
        return None

    @classmethod
    def get_current_term(cls, school=None):
        """Get the current term for a specific school."""
        if school:
            if school.current_term:
                return school.current_term
        # Fallback to the term marked as current
        return Term.objects.filter(is_current=True).first()

    def __str__(self):
        return self.name


# Helper functions for easy access to current settings
def get_current_academic_year():
    """Helper function to get the current academic year."""
    return SchoolInformation.get_current_academic_year()


def get_current_term():
    """Helper function to get the current term."""
    return SchoolInformation.get_current_term()


# Disable this signal receiver to prevent automatic user creation - we'll create users manually
# @receiver(post_save, sender=Teacher)
# def create_teacher_user(sender, instance, created, **kwargs):
#     if created and not instance.skip_user_creation:
#         # Generate username from staff_id
#         username = f"teacher_{instance.staff_id}"
#
#         # Generate secure password
#         password = generate_secure_password()
#
#         # Create user account
#         user = User.objects.create(
#             username=username,
#             email=instance.email or instance.contact_number,  # Use email if available, otherwise use contact_number
#             full_name=instance.full_name,
#             role='teacher',
#             password=make_password(password),
#             teacher_profile=instance
#         )
#
#         # Store the plain password temporarily for sending to the teacher
#         instance.temp_password = password
#
#         # Send credentials via email
#         send_user_credentials_email(user, password)


@receiver(post_save, sender=Student)
def create_student_user(sender, instance, created, **kwargs):
    """
    Create a user account for a newly created student.

    This function creates a user account when a new student is created,
    with username based on admission number and a secure random password.
    The credentials are sent to the student via email.
    """
    if created:
        # Check if a user already exists for this student
        if User.objects.filter(student_profile=instance).exists():
            return  # User already exists, don't create another one

        # Generate username from admission_number
        username = f"student_{instance.admission_number}"

        # Check if a user with this username already exists
        if User.objects.filter(username=username).exists():
            # Append a random string to ensure uniqueness
            username = f"{username}_{generate_unique_id(length=4)}"

        # Generate secure password
        password = generate_secure_password()

        # Create user account with school field set from student
        user = User.objects.create(
            username=username,
            email=instance.email
            or f"{instance.admission_number}@example.com",  # Use email if available or generate one
            full_name=instance.full_name,
            role="student",
            password=make_password(password),
            student_profile=instance,
            school=instance.school,  # Set the school from the student instance
        )

        # Store the plain password temporarily for sending to the student
        instance.temp_password = password

        # Send credentials via email if student has email (skip during bulk imports)
        if instance.email and not getattr(instance, "_skip_email", False):
            try:
                send_user_credentials_email(user, password)
            except Exception as e:
                # Log email failure but don't stop the process
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(
                    f"Failed to send welcome email to {instance.full_name}: {str(e)}"
                )
                print(f"Failed to send email: {str(e)}")


@receiver(pre_delete, sender=Student)
def delete_student_user(sender, instance, **kwargs):
    """
    Delete associated user account when a student is deleted.

    This signal handler ensures that when a student record is deleted,
    the corresponding user account is also deleted to maintain data integrity.
    """
    # Find and delete the associated user account
    User.objects.filter(student_profile=instance).delete()


class ReportCard(models.Model):
    """Model for generating and storing student report cards"""

    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE)
    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    class_assigned = models.ForeignKey(Class, on_delete=models.CASCADE)
    # Add school relationship for multi-tenancy
    school = models.ForeignKey(
        "SchoolInformation",
        on_delete=models.CASCADE,
        related_name="report_cards",
        null=True,
    )

    # Performance Summary
    position = models.PositiveIntegerField(null=True, blank=True)
    total_score = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    average_marks = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )

    # Form position (position in the entire form/grade level)
    form_position = models.PositiveIntegerField(null=True, blank=True)

    # Promotion information
    promoted_to = models.CharField(max_length=50, blank=True, null=True)
    next_term_begins = models.DateField(null=True, blank=True)

    # Attendance Summary (can be auto-calculated from AttendanceRecord)
    days_present = models.PositiveIntegerField(default=0)
    days_absent = models.PositiveIntegerField(default=0)
    total_school_days = models.PositiveIntegerField(default=0)

    # Remarks
    interest_remarks = models.CharField(max_length=100, blank=True, null=True)
    conduct_remarks = models.CharField(max_length=100, blank=True, null=True)
    attitude_remarks = models.CharField(max_length=100, blank=True, null=True)
    class_teacher_remarks = models.TextField(blank=True, null=True)
    principal_remarks = models.TextField(blank=True, null=True)

    # Metadata
    date_generated = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    generated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="generated_report_cards",
    )
    approved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="approved_report_cards"
    )
    is_approved = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "academic_year", "term"],
                name="unique_student_term_report",
            )
        ]
        indexes = [
            models.Index(fields=["student", "academic_year", "term"]),
            models.Index(fields=["class_assigned", "term"]),
        ]

    def calculate_totals(self):
        """Calculate total and average marks for the student in this term"""
        # Get all assessments for this student in this term
        try:
            print(
                f"Calculating totals for student {self.student.full_name} in term {self.term.get_term_number_display()}"
            )

            # Filter assessments by term directly (not by date_recorded)

            # Exclude mock exam assessments from report card calculations

            assessments = Assessment.objects.filter(
                student=self.student,
                term=self.term,  # Use the term field directly
                total_score__isnull=False,

            ).exclude(assessment_type='mock_exam')


            print(
                f"Found {assessments.count()} assessments for student {self.student.full_name}"
            )

            # Debug: List all assessments found
            for assessment in assessments:
                print(
                    f"  - Assessment: {assessment.class_subject.subject} = {assessment.total_score} (Term: {assessment.term.get_term_number_display()})"
                )

            total_points = sum(
                assessment.total_score or 0 for assessment in assessments
            )
            num_subjects = assessments.count()

            if num_subjects > 0:
                avg_score = total_points / num_subjects
                self.total_score = round(avg_score, 2)
                self.average_marks = self.total_score  # Keep both fields in sync
                print(
                    f"Calculated total score: {self.total_score} from {num_subjects} assessments"
                )
            else:
                # Try alternative approach: look for assessments by academic year and class
                print(
                    f"No assessments found for term {self.term.get_term_number_display()}, trying alternative approach..."
                )

                # Get all assessments for this student in this academic year
                all_assessments = Assessment.objects.filter(
                    student=self.student,
                    class_subject__academic_year=self.academic_year,
                    total_score__isnull=False,
                )

                print(
                    f"Found {all_assessments.count()} total assessments for student in academic year {self.academic_year}"
                )

                # If we have assessments but none for this specific term,
                # it might be that the term field wasn't set correctly
                if all_assessments.count() > 0:
                    print(
                        "Warning: Found assessments for the academic year but not for the specific term."
                    )
                    print(
                        "This might indicate that the term field in assessments is not set correctly."
                    )

                    # List all terms that have assessments
                    terms_with_assessments = set()
                    for assessment in all_assessments:
                        if assessment.term:
                            terms_with_assessments.add(
                                assessment.term.get_term_number_display()
                            )
                    print(
                        f"Terms with assessments: {', '.join(terms_with_assessments)}"
                    )

                self.total_score = 0
                self.average_marks = 0
                print(
                    f"Setting total score to 0 due to no assessments found for term {self.term.get_term_number_display()}"
                )

            # Make sure we never have None values
            if self.total_score is None:
                self.total_score = 0
            if self.average_marks is None:
                self.average_marks = 0
        except Exception as e:
            print(f"Error calculating totals for report card {self.id}: {str(e)}")
            self.total_score = 0
            self.average_marks = 0

        return

    def calculate_attendance(self):
        """Calculate attendance statistics for the student in this term"""
        print(
            f"Calculating attendance for student {self.student.full_name} in term {self.term.get_term_number_display()}"
        )

        # First try to get attendance from StudentTermRemarks
        try:
            teacher_remarks = StudentTermRemarks.objects.filter(
                student=self.student,
                term=self.term,
                academic_year=self.academic_year,
            ).first()

            if teacher_remarks:
                # Use values from teacher remarks
                self.days_present = teacher_remarks.days_present or 0
                self.days_absent = teacher_remarks.days_absent or 0
                self.total_school_days = teacher_remarks.total_school_days or 0
                print(
                    f"Using attendance from teacher remarks: {self.days_present}/{self.total_school_days}"
                )
                return
        except Exception as e:
            print(f"Error getting attendance from teacher remarks: {str(e)}")

        # If no teacher remarks, calculate from AttendanceRecord
        try:
            # Count days present
            self.days_present = AttendanceRecord.objects.filter(
                student=self.student, term=self.term, is_present=True
            ).count()

            # Count days absent
            self.days_absent = AttendanceRecord.objects.filter(
                student=self.student, term=self.term, is_present=False
            ).count()

            # Calculate total school days
            if self.term.start_date and self.term.end_date:
                # Calculate total weekdays in term (approximation of school days)
                term_duration = (self.term.end_date - self.term.start_date).days + 1
                # Account for weekends (5 school days per week)
                self.total_school_days = max(
                    round(term_duration * 5 / 7), self.days_present + self.days_absent
                )
            else:
                # Fallback to sum of present and absent days
                self.total_school_days = self.days_present + self.days_absent

            print(
                f"Calculated attendance from records: {self.days_present}/{self.total_school_days}"
            )

        except Exception as e:
            print(f"Error calculating attendance: {str(e)}")
            # Simple default values
            self.days_present = 0
            self.days_absent = 0
            self.total_school_days = 0

    def calculate_position(self):
        """Calculate the student's position in class for this term"""
        try:
            print(
                f"Calculating position for student {self.student.full_name} in class {self.class_assigned.name}"
            )

            # Get all report cards for students in the same class and term
            class_report_cards = ReportCard.objects.filter(
                class_assigned=self.class_assigned,
                term=self.term,
                academic_year=self.academic_year,
                total_score__isnull=False,
            ).exclude(
                id=self.id
            )  # Exclude the current report card

            print(
                f"Found {class_report_cards.count()} other report cards in the same class and term"
            )

            # Get their scores
            scores = [
                rc.total_score
                for rc in class_report_cards
                if rc.total_score is not None
            ]

            # Add current student's score if it exists
            if self.total_score is not None:
                scores.append(self.total_score)

            print(f"Total scores to consider: {scores}")

            # Sort scores in descending order and remove duplicates
            scores = sorted(set(scores), reverse=True)

            # Find the position of the current student's score
            if self.total_score is not None and scores:
                self.position = scores.index(self.total_score) + 1
                print(
                    f"Calculated position: {self.position} out of {len(scores)} students"
                )
            else:
                self.position = 1  # Default position if no scores are available
                print(f"No scores available, setting position to 1")

            # Calculate form position (across all classes in same form)
            if hasattr(self.class_assigned, "form") and self.class_assigned.form:
                # Get all report cards for students in the same form and term
                form_report_cards = ReportCard.objects.filter(
                    class_assigned__form=self.class_assigned.form,
                    term=self.term,
                    academic_year=self.academic_year,
                    total_score__isnull=False,
                ).exclude(id=self.id)

                # Get form scores
                form_scores = [
                    rc.total_score
                    for rc in form_report_cards
                    if rc.total_score is not None
                ]

                # Add current student's score if it exists
                if self.total_score is not None:
                    form_scores.append(self.total_score)

                # Sort form scores and remove duplicates
                form_scores = sorted(set(form_scores), reverse=True)

                # Find the form position
                if self.total_score is not None and form_scores:
                    self.form_position = form_scores.index(self.total_score) + 1
                else:
                    self.form_position = 1

        except Exception as e:
            print(f"Error calculating position: {str(e)}")
            self.position = 1
            self.form_position = 1

        return

    def set_next_term_date(self):
        """Set the next term beginning date based on the current term's end date"""
        try:
            # Find the next term if one exists
            current_term_number = self.term.term_number
            next_term_number = current_term_number + 1 if current_term_number < 3 else 1

            if next_term_number == 1:
                # Next term is in next academic year - find the CLOSEST next academic year
                try:
                    # Find the closest next academic year by looking for the one with the smallest gap
                    # between current academic year end and next academic year start
                    from django.db.models import F, ExpressionWrapper, DurationField
                    from datetime import timedelta

                    next_academic_year = (
                        AcademicYear.objects.filter(
                            start_date__gt=self.academic_year.end_date
                        )
                        .annotate(
                            gap_days=ExpressionWrapper(
                                F("start_date") - self.academic_year.end_date,
                                output_field=DurationField(),
                            )
                        )
                        .order_by("gap_days")  # Order by smallest gap (closest)
                        .first()
                    )

                    if next_academic_year:
                        print(
                            f"Found closest next academic year: {next_academic_year} (gap: {next_academic_year.gap_days})"
                        )
                        next_term = Term.objects.filter(
                            academic_year=next_academic_year,
                            term_number=next_term_number,
                        ).first()

                        if next_term:
                            self.next_term_begins = next_term.start_date
                            print(
                                f"Set next term start date to: {self.next_term_begins} (from {next_term})"
                            )
                        else:
                            print(
                                f"No Term {next_term_number} found in academic year {next_academic_year}"
                            )
                    else:
                        print("No next academic year found")
                except:
                    # Default to 2 weeks after current term ends
                    from datetime import timedelta

                    self.next_term_begins = self.term.end_date + timedelta(days=14)
            else:
                # Next term is in same academic year
                next_term = Term.objects.filter(
                    academic_year=self.academic_year, term_number=next_term_number
                ).first()

                if next_term:
                    self.next_term_begins = next_term.start_date
                else:
                    # Default to 2 weeks after current term ends
                    from datetime import timedelta

                    self.next_term_begins = self.term.end_date + timedelta(days=14)
        except Exception as e:
            print(f"Error setting next term date: {str(e)}")
            # Default to 2 weeks after current term ends
            from datetime import timedelta

            self.next_term_begins = self.term.end_date + timedelta(days=14)

    def __str__(self):
        return f"Report Card: {self.student} - {self.term} ({self.academic_year})"

    def save(self, *args, **kwargs):
        """
        Ensure the report card has a school associated with it based on related objects.
        This supports multi-tenancy by ensuring all report cards are associated with a school.
        """
        # Set school from related objects if not explicitly provided
        if not self.school:
            # Try to get school from student
            if self.student and hasattr(self.student, "school") and self.student.school:
                self.school = self.student.school
            # Then try from class_assigned
            elif (
                self.class_assigned
                and hasattr(self.class_assigned, "school")
                and self.class_assigned.school
            ):
                self.school = self.class_assigned.school
            # Then try from academic_year
            elif (
                self.academic_year
                and hasattr(self.academic_year, "school")
                and self.academic_year.school
            ):
                self.school = self.academic_year.school
            # Then try from term
            elif self.term and hasattr(self.term, "school") and self.term.school:
                self.school = self.term.school
            # Then try from generated_by user
            elif (
                self.generated_by
                and hasattr(self.generated_by, "school")
                and self.generated_by.school
            ):
                self.school = self.generated_by.school

        super().save(*args, **kwargs)


# Add model for centralized OAuth credentials storage
class OAuthCredentialStore(models.Model):
    """Store OAuth credentials for service accounts"""

    service_name = models.CharField(max_length=100, unique=True)
    client_id = models.CharField(max_length=255)
    client_secret = models.CharField(max_length=255)
    refresh_token = models.TextField()
    access_token = models.TextField(blank=True, null=True)
    token_uri = models.CharField(
        max_length=255, default="https://oauth2.googleapis.com/token"
    )
    scopes = models.JSONField(default=list)
    email = models.EmailField()
    is_active = models.BooleanField(default=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.service_name} - {self.email}"

    @classmethod
    def get_email_credentials(cls):
        """Get credentials for email service"""
        return cls.objects.filter(service_name="gmail", is_active=True).first()


# Add these models at the end of the file, before any closing comments


class ScheduledReminder(models.Model):
    """Model for scheduled email reminders"""

    school = models.ForeignKey(
        "SchoolInformation",
        on_delete=models.CASCADE,
        related_name="scheduled_reminders",
    )
    creator = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="created_reminders"
    )
    scheduled_time = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    executed = models.BooleanField(default=False)
    executed_at = models.DateTimeField(null=True, blank=True)
    reminder_type = models.CharField(
        max_length=50,
        choices=[
            ("activity", "Activity Reminder"),
            ("bulk_activity", "Bulk Activity Reminder"),
            ("general", "General Reminder"),
        ],
    )
    parameters = models.JSONField(default=dict)

    class Meta:
        ordering = ["scheduled_time", "-created_at"]
        verbose_name = "Scheduled Reminder"
        verbose_name_plural = "Scheduled Reminders"

    def __str__(self):
        return f"{self.get_reminder_type_display()} - {self.scheduled_time.strftime('%Y-%m-%d %H:%M')}"

    def execute(self):
        """Execute this scheduled reminder"""
        from django.utils import timezone
        from .utils import send_activity_reminder_email
        from .views.teacher_monitoring_activities import get_completion_status

        results = {
            "success_count": 0,
            "failure_count": 0,
            "skipped_count": 0,
            "messages": [],
        }

        # Handle different reminder types
        if self.reminder_type == "activity":
            # Single activity reminder
            assignment_id = self.parameters.get("assignment_id")
            activity_type = self.parameters.get("activity_type")

            if not assignment_id or not activity_type:
                results["messages"].append("Missing required parameters")
                return results

            try:
                assignment = TeacherSubjectAssignment.objects.get(id=assignment_id)
                teacher = assignment.teacher
                teacher_email = (
                    teacher.user.email
                    if hasattr(teacher, "user") and teacher.user
                    else None
                )

                if not teacher_email:
                    results["skipped_count"] += 1
                    results["messages"].append(
                        f"No email found for teacher {teacher.full_name}"
                    )
                    return results

                class_obj = assignment.class_assigned
                subject = assignment.subject
                term = Term.objects.filter(
                    academic_year=class_obj.academic_year,
                    school=self.school,
                    is_active=True,
                ).first()

                if not term:
                    results["skipped_count"] += 1
                    results["messages"].append("No active term found")
                    return results

                # Calculate completion
                student_count = StudentClass.objects.filter(
                    assigned_class=class_obj, is_active=True
                ).count()

                completion = {"total": student_count, "completed": 0, "percentage": 0}

                if activity_type == "scores":
                    activity_name = "Score Entry"
                    scores_entered = Assessment.objects.filter(
                        student__studentclass__assigned_class=class_obj,
                        class_subject__subject=subject,
                        class_subject__academic_year=term.academic_year,
                        student__studentclass__is_active=True,
                    ).count()
                    completion["completed"] = scores_entered
                    completion["percentage"] = round(
                        (scores_entered / student_count * 100)
                        if student_count > 0
                        else 0
                    )
                    completion["status"] = get_completion_status(
                        scores_entered, student_count
                    )

                elif activity_type == "remarks":
                    activity_name = "Student Remarks"
                    remarks_entered = StudentTermRemarks.objects.filter(
                        student__studentclass__assigned_class=class_obj,
                        term=term,
                        student__studentclass__is_active=True,
                    ).count()
                    completion["completed"] = remarks_entered
                    completion["percentage"] = round(
                        (remarks_entered / student_count * 100)
                        if student_count > 0
                        else 0
                    )
                    completion["status"] = get_completion_status(
                        remarks_entered, student_count
                    )

                elif activity_type == "report_cards":
                    activity_name = "Report Card Generation"
                    report_cards_generated = ReportCard.objects.filter(
                        student__studentclass__assigned_class=class_obj,
                        term=term,
                        student__studentclass__is_active=True,
                    ).count()
                    completion["completed"] = report_cards_generated
                    completion["percentage"] = round(
                        (report_cards_generated / student_count * 100)
                        if student_count > 0
                        else 0
                    )
                    completion["status"] = get_completion_status(
                        report_cards_generated, student_count
                    )

                else:
                    results["skipped_count"] += 1
                    results["messages"].append(
                        f"Invalid activity type: {activity_type}"
                    )
                    return results

                # Get school info for email
                school_name = (
                    self.school.name
                    if hasattr(self.school, "name")
                    else "School Management System"
                )
                from django.conf import settings

                site_url = getattr(settings, "SITE_URL", "http://localhost:8000")
                from django.urls import reverse_lazy

                # Add deadline if term end date is available
                deadline = term.end_date if hasattr(term, "end_date") else None

                # Prepare email context
                context = {
                    "teacher": teacher,
                    "class_obj": class_obj,
                    "subject": subject,
                    "term": term,
                    "activity_type": activity_type,
                    "activity_type_name": activity_name,
                    "completion": completion,
                    "school_name": school_name,
                    "login_url": f"{site_url}{reverse_lazy('login')}",
                    "deadline": deadline,
                    "direct_link": f"{site_url}/teacher/dashboard/",
                    "is_bulk_reminder": False,
                    "is_scheduled": True,
                    "scheduled_time": self.scheduled_time,
                }

                # Send the email
                success, message = send_activity_reminder_email(teacher_email, context)

                if success:
                    results["success_count"] += 1
                    # Log the reminder
                    ReminderLog.objects.create(
                        teacher=teacher,
                        class_assigned=class_obj,
                        subject=subject,
                        term=term,
                        activity_type=activity_type,
                        completion_percentage=completion["percentage"],
                        sent_by=self.creator,
                        status="sent" if "disabled" not in message else "disabled",
                        message=message,
                        scheduled_reminder=self,
                    )
                else:
                    results["failure_count"] += 1
                    results["messages"].append(
                        f"Failed to send email to {teacher.full_name}: {message}"
                    )

                    # Log the failure
                    ReminderLog.objects.create(
                        teacher=teacher,
                        class_assigned=class_obj,
                        subject=subject,
                        term=term,
                        activity_type=activity_type,
                        completion_percentage=completion["percentage"],
                        sent_by=self.creator,
                        status="failed",
                        message=message,
                        scheduled_reminder=self,
                    )

            except Exception as e:
                import traceback

                results["failure_count"] += 1
                results["messages"].append(f"Error processing reminder: {str(e)}")

                # Log the error
                import logging

                logger = logging.getLogger("shs_system.email")
                logger.error(
                    f"Scheduled reminder error: {str(e)}\n{traceback.format_exc()}"
                )

        elif self.reminder_type == "bulk_activity":
            # Bulk activity reminders
            activity_type = self.parameters.get("activity_type")
            filters = self.parameters.get("filters", {})
            term_id = self.parameters.get("term_id")
            completion_status = self.parameters.get("completion_status")

            if not activity_type:
                results["messages"].append("Missing required parameter: activity_type")
                return results

            # Get term
            if term_id:
                try:
                    term = Term.objects.get(id=term_id, school=self.school)
                except Term.DoesNotExist:
                    term = Term.objects.filter(
                        school=self.school, is_active=True
                    ).first()
            else:
                term = Term.objects.filter(school=self.school, is_active=True).first()

            if not term:
                results["skipped_count"] += 1
                results["messages"].append("No active term found")
                return results

            # Get all matching assignments
            try:
                assignments = TeacherSubjectAssignment.objects.filter(
                    teacher__user__school=self.school, **filters
                ).select_related("teacher", "class_assigned", "subject")

                # Process each assignment
                for assignment in assignments:
                    # Skip if no email
                    teacher = assignment.teacher
                    teacher_email = (
                        teacher.user.email
                        if hasattr(teacher, "user") and teacher.user
                        else None
                    )

                    if not teacher_email:
                        results["skipped_count"] += 1
                        continue

                    # Get class and subject
                    class_obj = assignment.class_assigned
                    subject = assignment.subject

                    # Calculate completion status
                    student_count = StudentClass.objects.filter(
                        assigned_class=class_obj, is_active=True
                    ).count()

                    # Skip if no students
                    if student_count == 0:
                        results["skipped_count"] += 1
                        continue

                    completion = {
                        "total": student_count,
                        "completed": 0,
                        "percentage": 0,
                    }

                    # Check completion based on activity type
                    if activity_type == "scores":
                        scores_entered = Assessment.objects.filter(
                            student__studentclass__assigned_class=class_obj,
                            class_subject__subject=subject,
                            class_subject__academic_year=term.academic_year,
                            student__studentclass__is_active=True,
                        ).count()
                        completion["completed"] = scores_entered
                        completion["percentage"] = round(
                            (scores_entered / student_count * 100)
                            if student_count > 0
                            else 0
                        )
                        completion["status"] = get_completion_status(
                            scores_entered, student_count
                        )
                        activity_name = "Score Entry"

                        # Skip if doesn't match filter criteria
                        if (
                            completion_status
                            and completion["status"] != completion_status
                        ):
                            results["skipped_count"] += 1
                            continue

                    elif activity_type == "remarks":
                        # Only process if teacher is class teacher
                        is_class_teacher = ClassTeacher.objects.filter(
                            class_assigned=class_obj,
                            teacher=teacher,
                            academic_year=class_obj.academic_year,
                            is_active=True,
                        ).exists()

                        if not is_class_teacher:
                            results["skipped_count"] += 1
                            continue

                        remarks_entered = StudentTermRemarks.objects.filter(
                            student__studentclass__assigned_class=class_obj,
                            term=term,
                            student__studentclass__is_active=True,
                        ).count()
                        completion["completed"] = remarks_entered
                        completion["percentage"] = round(
                            (remarks_entered / student_count * 100)
                            if student_count > 0
                            else 0
                        )
                        completion["status"] = get_completion_status(
                            remarks_entered, student_count
                        )
                        activity_name = "Student Remarks"

                        # Skip if doesn't match filter criteria
                        if (
                            completion_status
                            and completion["status"] != completion_status
                        ):
                            results["skipped_count"] += 1
                            continue

                    elif activity_type == "report_cards":
                        # Only process if teacher is class teacher
                        is_class_teacher = ClassTeacher.objects.filter(
                            class_assigned=class_obj,
                            teacher=teacher,
                            academic_year=class_obj.academic_year,
                            is_active=True,
                        ).exists()

                        if not is_class_teacher:
                            results["skipped_count"] += 1
                            continue

                        report_cards_generated = ReportCard.objects.filter(
                            student__studentclass__assigned_class=class_obj,
                            term=term,
                            student__studentclass__is_active=True,
                        ).count()
                        completion["completed"] = report_cards_generated
                        completion["percentage"] = round(
                            (report_cards_generated / student_count * 100)
                            if student_count > 0
                            else 0
                        )
                        completion["status"] = get_completion_status(
                            report_cards_generated, student_count
                        )
                        activity_name = "Report Card Generation"

                        # Skip if doesn't match filter criteria
                        if (
                            completion_status
                            and completion["status"] != completion_status
                        ):
                            results["skipped_count"] += 1
                            continue

                    # Get school info
                    school_name = (
                        self.school.name
                        if hasattr(self.school, "name")
                        else "School Management System"
                    )
                    from django.conf import settings

                    site_url = getattr(settings, "SITE_URL", "http://localhost:8000")
                    from django.urls import reverse_lazy

                    # Add deadline if term end date is available
                    deadline = term.end_date if hasattr(term, "end_date") else None

                    # Prepare email context
                    context = {
                        "teacher": teacher,
                        "class_obj": class_obj,
                        "subject": subject,
                        "term": term,
                        "activity_type": activity_type,
                        "activity_type_name": activity_name,
                        "completion": completion,
                        "school_name": school_name,
                        "login_url": f"{site_url}{reverse_lazy('login')}",
                        "deadline": deadline,
                        "direct_link": f"{site_url}/teacher/dashboard/",
                        "is_bulk_reminder": True,
                        "is_scheduled": True,
                        "scheduled_time": self.scheduled_time,
                    }

                    # Send the email
                    success, message = send_activity_reminder_email(
                        teacher_email, context
                    )

                    # Track results
                    if success:
                        results["success_count"] += 1

                        # Log the reminder
                        ReminderLog.objects.create(
                            teacher=teacher,
                            class_assigned=class_obj,
                            subject=subject,
                            term=term,
                            activity_type=activity_type,
                            completion_percentage=completion["percentage"],
                            sent_by=self.creator,
                            status="sent" if "disabled" not in message else "disabled",
                            message=message,
                            scheduled_reminder=self,
                        )
                    else:
                        results["failure_count"] += 1
                        results["messages"].append(
                            f"Failed to send email to {teacher.full_name}: {message}"
                        )

                        # Log the failure
                        ReminderLog.objects.create(
                            teacher=teacher,
                            class_assigned=class_obj,
                            subject=subject,
                            term=term,
                            activity_type=activity_type,
                            completion_percentage=completion["percentage"],
                            sent_by=self.creator,
                            status="failed",
                            message=message,
                            scheduled_reminder=self,
                        )

            except Exception as e:
                import traceback

                results["failure_count"] += 1
                results["messages"].append(f"Error processing bulk reminders: {str(e)}")

                # Log the error
                import logging

                logger = logging.getLogger("shs_system.email")
                logger.error(
                    f"Scheduled bulk reminder error: {str(e)}\n{traceback.format_exc()}"
                )

        # Mark as executed
        self.executed = True
        self.executed_at = timezone.now()
        self.save()

        return results


class ReminderLog(models.Model):
    """Model for tracking sent reminders"""

    teacher = models.ForeignKey(
        "Teacher", on_delete=models.CASCADE, related_name="reminders"
    )
    class_assigned = models.ForeignKey(
        "Class", on_delete=models.CASCADE, related_name="reminders"
    )
    subject = models.ForeignKey(
        "Subject", on_delete=models.CASCADE, related_name="reminders"
    )
    term = models.ForeignKey("Term", on_delete=models.CASCADE, related_name="reminders")
    activity_type = models.CharField(
        max_length=20,
        choices=[
            ("scores", "Score Entry"),
            ("remarks", "Student Remarks"),
            ("report_cards", "Report Cards"),
        ],
    )
    completion_percentage = models.IntegerField(default=0)
    sent_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="sent_reminders"
    )
    sent_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("sent", "Sent"),
            ("failed", "Failed"),
            ("disabled", "Disabled"),
        ],
        default="sent",
    )
    message = models.TextField(blank=True)
    scheduled_reminder = models.ForeignKey(
        "ScheduledReminder",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reminder_logs",
    )

    class Meta:
        ordering = ["-sent_at"]
        verbose_name = "Reminder Log"
        verbose_name_plural = "Reminder Logs"

    def __str__(self):
        return f"{self.get_activity_type_display()} reminder to {self.teacher.full_name} on {self.sent_at.strftime('%Y-%m-%d %H:%M')}"


class ScoringConfiguration(models.Model):
    """
    Model for configuring dynamic scoring weights and percentages for schools.
    Allows school admins to set custom scoring configurations.
    """

    exam_score_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=70.0,
        help_text="Percentage weight for exam scores (0-100)",
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )

    class_score_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=30.0,
        help_text="Percentage weight for class scores (0-100)",
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )

    # Maximum marks for each component (actual marks, not percentages)
    individual_max_mark = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=15.0,
        help_text="Maximum possible mark for individual assignments",
        validators=[MinValueValidator(0)],
    )

    class_test_max_mark = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=15.0,
        help_text="Maximum possible mark for class tests",
        validators=[MinValueValidator(0)],
    )

    project_max_mark = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=15.0,
        help_text="Maximum possible mark for projects",
        validators=[MinValueValidator(0)],
    )

    group_work_max_mark = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=15.0,
        help_text="Maximum possible mark for group work",
        validators=[MinValueValidator(0)],
    )

    # Maximum scores
    max_exam_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=70.0,
        help_text="Maximum possible exam score",
        validators=[MinValueValidator(0)],
    )

    max_class_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=30.0,
        help_text="Maximum possible class score",
        validators=[MinValueValidator(0)],
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # School relationship for multi-tenancy
    school = models.ForeignKey(
        "SchoolInformation",
        on_delete=models.CASCADE,
        related_name="scoring_configurations",
        null=True,
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_scoring_configs",
    )

    class Meta:
        verbose_name = "Scoring Configuration"
        verbose_name_plural = "Scoring Configurations"
        unique_together = ["school", "is_active"]
        indexes = [
            models.Index(fields=["school", "is_active"]),
            models.Index(fields=["is_active"]),
        ]

    def clean(self):
        """Validate that exam and class score percentages sum to 100%"""
        if self.exam_score_percentage + self.class_score_percentage != 100:
            raise ValidationError(
                "Exam score percentage and class score percentage must sum to 100%"
            )

        # Validate that class score component max marks are not all zero (to prevent division by zero)
        total_max_marks = (
            self.individual_max_mark
            + self.class_test_max_mark
            + self.project_max_mark
            + self.group_work_max_mark
        )
        if total_max_marks == 0:
            raise ValidationError("Class score component max marks cannot all be zero")

    def save(self, *args, **kwargs):
        # Ensure only one active configuration per school
        if self.is_active:
            ScoringConfiguration.objects.filter(
                school=self.school, is_active=True
            ).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_active_config(cls, school=None):
        """Get the active scoring configuration for a school"""
        query = cls.objects.filter(is_active=True)
        if school:
            query = query.filter(school=school)
        return query.first()

    def calculate_class_score(
        self, individual_score, class_test_score, project_score, group_work_score
    ):
        """
        Calculate the class score based on actual marks achieved vs maximum possible marks.
        Formula: (total_actual_score / total_max_possible_score) × class_score_percentage
        """
        # Convert None values to 0 for calculation and ensure all values are Decimal
        individual_score = Decimal(str(individual_score or 0))
        class_test_score = Decimal(str(class_test_score or 0))
        project_score = Decimal(str(project_score or 0))
        group_work_score = Decimal(str(group_work_score or 0))

        # Convert configuration values to Decimal
        individual_max = Decimal(str(self.individual_max_mark))
        class_test_max = Decimal(str(self.class_test_max_mark))
        project_max = Decimal(str(self.project_max_mark))
        group_work_max = Decimal(str(self.group_work_max_mark))
        class_score_percentage = Decimal(str(self.class_score_percentage))

        # Calculate total actual score achieved by student
        total_actual_score = (
            individual_score + class_test_score + project_score + group_work_score
        )

        # Calculate total maximum possible score
        total_max_possible_score = (
            individual_max + class_test_max + project_max + group_work_max
        )

        # If total max possible score is 0, return 0 to avoid division by zero
        if total_max_possible_score == 0:
            return Decimal("0")

        # Calculate the scaled class score
        # Formula: (total_actual_score / total_max_possible_score) × class_score_percentage
        scaled_score = (
            total_actual_score / total_max_possible_score
        ) * class_score_percentage

        return scaled_score

    def calculate_exam_score(self, exam_score):
        """
        Calculate the exam score based on raw marks out of 100.
        Formula: (exam_score / 100) × exam_score_percentage
        """
        if exam_score is None:
            return Decimal("0")

        # Convert to Decimal
        exam_score = Decimal(str(exam_score))
        exam_score_percentage = Decimal(str(self.exam_score_percentage))

        # Calculate the scaled exam score
        # Formula: (exam_score / 100) × exam_score_percentage
        scaled_score = (exam_score / Decimal("100")) * exam_score_percentage

        return scaled_score

    def __str__(self):
        school_name = self.school.name if self.school else "Global"
        return f"Scoring Config - {school_name} (Exam: {self.exam_score_percentage}%, Class: {self.class_score_percentage}%)"



class BackupOperation(models.Model):
    """
    Model to track backup operations for multi-tenant school management system.
    Each backup is associated with a specific school (tenant).
    """
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    )
    
    school = models.ForeignKey(
        'SchoolInformation',
        on_delete=models.CASCADE,
        related_name='backups',
        help_text="School (tenant) this backup belongs to"
    )
    created_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_backups',
        help_text="User who initiated the backup"
    )
    backup_name = models.CharField(
        max_length=255,
        help_text="Human-readable name for the backup"
    )
    backup_file_path = models.CharField(
        max_length=500,
        help_text="Full path to the backup file on local storage"
    )
    backup_size = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="Size of backup file in bytes"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(
        blank=True,
        null=True,
        help_text="Error message if backup failed"
    )
    
    # Backup metadata
    includes_database = models.BooleanField(default=True)
    includes_media_files = models.BooleanField(default=True)
    includes_static_files = models.BooleanField(default=False)
    
    # Backup statistics
    database_records_count = models.IntegerField(null=True, blank=True)
    media_files_count = models.IntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Backup Operation"
        verbose_name_plural = "Backup Operations"
    
    def __str__(self):
        return f"{self.backup_name} - {self.school.name} ({self.get_status_display()})"
    
    @property
    def backup_size_human(self):
        """Return human-readable backup size"""
        if not self.backup_size:
            return "Unknown"
        
        size = self.backup_size
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"
    
    @property
    def duration(self):
        """Return backup duration if completed"""
        if self.completed_at and self.created_at:
            return self.completed_at - self.created_at
        return None


class RestoreOperation(models.Model):
    """
    Model to track restore operations for multi-tenant school management system.
    Each restore operation is associated with a specific school (tenant).
    """
    
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    )
    
    school = models.ForeignKey(
        'SchoolInformation',
        on_delete=models.CASCADE,
        related_name='restores',
        help_text="School (tenant) this restore operation belongs to"
    )
    created_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_restores',
        help_text="User who initiated the restore"
    )
    backup_file_path = models.CharField(
        max_length=500,
        help_text="Full path to the backup file to restore from"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(
        blank=True,
        null=True,
        help_text="Error message if restore failed"
    )
    
    # Restore options
    restore_database = models.BooleanField(default=True)
    restore_media_files = models.BooleanField(default=True)
    restore_static_files = models.BooleanField(default=False)
    backup_existing_data = models.BooleanField(
        default=True,
        help_text="Create backup of existing data before restore"
    )
    
    # Restore statistics
    restored_records_count = models.IntegerField(null=True, blank=True)
    restored_files_count = models.IntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Restore Operation"
        verbose_name_plural = "Restore Operations"
    
    def __str__(self):
        return f"Restore - {self.school.name} ({self.get_status_display()})"
    
    @property
    def duration(self):
        """Return restore duration if completed"""
        if self.completed_at and self.created_at:
            return self.completed_at - self.created_at
        return None


class BackupSettings(models.Model):
    """
    Model to store backup and restore settings for each school.
    Allows users to save their preferred backup/restore configurations.
    """
    
    school = models.OneToOneField(
        'SchoolInformation',
        on_delete=models.CASCADE,
        related_name='backup_settings',
        help_text="School (tenant) these settings belong to"
    )
    
    # Backup settings
    default_backup_name = models.CharField(
        max_length=255,
        default="",
        blank=True,
        help_text="Default name template for backups"
    )
    default_includes_database = models.BooleanField(
        default=True,
        help_text="Default setting for including database in backups"
    )
    default_includes_media_files = models.BooleanField(
        default=True,
        help_text="Default setting for including media files in backups"
    )
    default_includes_static_files = models.BooleanField(
        default=False,
        help_text="Default setting for including static files in backups"
    )
    
    # Restore settings
    default_restore_database = models.BooleanField(
        default=True,
        help_text="Default setting for restoring database"
    )
    default_restore_media_files = models.BooleanField(
        default=True,
        help_text="Default setting for restoring media files"
    )
    default_restore_static_files = models.BooleanField(
        default=False,
        help_text="Default setting for restoring static files"
    )
    default_backup_existing_data = models.BooleanField(
        default=True,
        help_text="Default setting for backing up existing data before restore"
    )
    
    # Auto-cleanup settings
    auto_cleanup_temp_files = models.BooleanField(
        default=True,
        help_text="Automatically clean up temporary backup files after restore"
    )
    temp_file_retention_hours = models.IntegerField(
        default=24,
        validators=[MinValueValidator(1), MaxValueValidator(168)],  # 1 hour to 1 week
        help_text="Hours to retain temporary files before cleanup"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        'User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_backup_settings',
        help_text="User who last updated these settings"
    )
    
    class Meta:
        verbose_name = "Backup Settings"
        verbose_name_plural = "Backup Settings"
    
    def __str__(self):
        return f"Backup Settings - {self.school.name}"
    
    def save(self, *args, **kwargs):
        """Override save to ensure only one settings record per school"""
        super().save(*args, **kwargs)
    
    @classmethod
    def get_or_create_for_school(cls, school):
        """Get or create backup settings for a school"""
        settings, created = cls.objects.get_or_create(
            school=school,
            defaults={
                'default_backup_name': f"{school.name} Backup",
                'default_includes_database': True,
                'default_includes_media_files': True,
                'default_includes_static_files': False,
                'default_restore_database': True,
                'default_restore_media_files': True,
                'default_restore_static_files': False,
                'default_backup_existing_data': True,
                'auto_cleanup_temp_files': True,
                'temp_file_retention_hours': 24,
            }
        )
        return settings

