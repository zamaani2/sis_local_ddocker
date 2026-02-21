from django import forms
from .models import User, Teacher, Student, TeacherSubjectAssignment
from .models import Form, LearningArea, Department
from datetime import datetime
from datetime import date
from django import forms
from .models import Teacher, Class, Subject, AcademicYear, Term
from django.core.exceptions import ValidationError
from django.utils import timezone


class TeacherForm(forms.ModelForm):
    email = forms.EmailField(required=False, help_text="Teacher's email address")
    password = forms.CharField(
        widget=forms.PasswordInput(),
        required=False,
        help_text="Required only if creating a new user account",
    )
    confirm_password = forms.CharField(widget=forms.PasswordInput(), required=False)

    class Meta:
        model = Teacher
        fields = [
            "full_name",
            "department",
            "gender",
            "contact_number",
            "email",
            "profile_picture",
        ]
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "form-control"}),
            "department": forms.Select(attrs={"class": "form-select"}),
            "gender": forms.Select(attrs={"class": "form-select"}),
            "contact_number": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "profile_picture": forms.FileInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        # Store whether this is for an existing user
        self.existing_user = kwargs.pop("existing_user", None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        create_account = self.data.get("create_account")
        email = cleaned_data.get("email")
        password = cleaned_data.get("password")

        # Only validate email and password if create_account is checked
        if create_account:
            if not email:
                self.add_error(
                    "email", "Email is required when creating a user account"
                )

            # Only require password when creating a new user account (not when editing existing)
            if not self.existing_user and not password:
                self.add_error(
                    "password", "Password is required when creating a new user account"
                )

        return cleaned_data


class TeacherAssignmentForm(forms.Form):
    # Get only current academic year classes
    def __init__(self, *args, **kwargs):
        school = kwargs.pop("school", None)  # Add school parameter
        super(TeacherAssignmentForm, self).__init__(*args, **kwargs)

        # Get current academic year for the school
        if school:
            current_academic_year = AcademicYear.objects.filter(
                school=school, is_current=True
            ).first()
        else:
            current_academic_year = AcademicYear.objects.filter(is_current=True).first()

        if current_academic_year:
            queryset = Class.objects.filter(academic_year=current_academic_year)
            # Filter by school for multi-tenancy if provided
            if school:
                queryset = queryset.filter(school=school)
            self.fields["class_obj"].queryset = queryset

    class_obj = forms.ModelChoiceField(
        queryset=Class.objects.none(),
        label="Class",
        widget=forms.Select(attrs={"class": "form-control"}),
        empty_label="Select a class",
    )


class TeacherSubjectAssignmentForm(forms.Form):
    # Get only current academic year classes and subjects
    def __init__(self, *args, **kwargs):
        school = kwargs.pop("school", None)  # Add school parameter
        super(TeacherSubjectAssignmentForm, self).__init__(*args, **kwargs)

        # Get current academic year for the school
        if school:
            current_academic_year = AcademicYear.objects.filter(
                school=school, is_current=True
            ).first()
        else:
            current_academic_year = AcademicYear.objects.filter(is_current=True).first()

        if current_academic_year:
            queryset = Class.objects.filter(academic_year=current_academic_year)
            # Filter by school for multi-tenancy if provided
            if school:
                queryset = queryset.filter(school=school)
            self.fields["class_assigned"].queryset = queryset

        # Filter subjects by school for multi-tenancy if provided
        if school:
            self.fields["subject"].queryset = Subject.objects.filter(school=school)

    subject = forms.ModelChoiceField(
        queryset=Subject.objects.all(),
        label="Subject",
        widget=forms.Select(attrs={"class": "form-control"}),
        empty_label="Select a subject",
    )

    class_assigned = forms.ModelChoiceField(
        queryset=Class.objects.none(),
        label="Class",
        widget=forms.Select(attrs={"class": "form-control"}),
        empty_label="Select a class",
    )


# forms.py
from django import forms
from .models import Student, Class, StudentClass, AcademicYear
from datetime import date


class StudentForm(forms.ModelForm):
    """Form for creating and editing student details"""

    class Meta:
        model = Student
        fields = [
            "full_name",
            "date_of_birth",
            "gender",
            "parent_contact",
            "admission_date",
            "form",
            "learning_area",
            "email",
            "profile_picture",
        ]
        widgets = {
            "full_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Enter full name"}
            ),
            "date_of_birth": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "gender": forms.Select(attrs={"class": "form-select"}),
            "parent_contact": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Enter parent contact"}
            ),
            "admission_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date", "value": date.today()}
            ),
            "form": forms.Select(attrs={"class": "form-select"}),
            "learning_area": forms.Select(attrs={"class": "form-select"}),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "Enter student email"}
            ),
            "profile_picture": forms.FileInput(attrs={"class": "form-control"}),
        }
        labels = {
            "full_name": "Full Name",
            "date_of_birth": "Date of Birth",
            "gender": "Gender",
            "parent_contact": "Parent Contact",
            "admission_date": "Admission Date",
            "form": "Form/Grade Level",
            "learning_area": "Learning Area",
            "email": "Email Address",
            "profile_picture": "Profile Picture",
        }

    def __init__(self, *args, **kwargs):
        """Initialize the form with optional school"""
        self.school = kwargs.pop("school", None)
        super(StudentForm, self).__init__(*args, **kwargs)

        # Filter form and learning area choices by school
        if self.school:
            self.fields["form"].queryset = Form.objects.filter(school=self.school)
            self.fields["learning_area"].queryset = LearningArea.objects.filter(
                school=self.school
            )

    def save(self, commit=True):
        """Save the student with the school if provided"""
        instance = super(StudentForm, self).save(commit=False)

        # Set the school if provided and not already set
        if self.school and not instance.school:
            instance.school = self.school

        if commit:
            instance.save()

        return instance


class StudentClassAssignmentForm(forms.Form):
    assigned_class = forms.ModelChoiceField(
        queryset=Class.objects.all(),
        label="Class",
        widget=forms.Select(attrs={"class": "form-select mb-3"}),
        empty_label="Select a class to assign",
    )

    def __init__(self, *args, **kwargs):
        # Get available classes based on student form and learning area if needed
        student = kwargs.pop("student", None)
        current_academic_year = kwargs.pop("current_academic_year", None)
        school = kwargs.pop("school", None)  # Add school parameter
        super(StudentClassAssignmentForm, self).__init__(*args, **kwargs)

        # Start with base queryset
        queryset = Class.objects.all()

        # Filter by school for multi-tenancy if provided
        if school:
            queryset = queryset.filter(school=school)
            print(f"Filtered by school: {school.name}, Class count: {queryset.count()}")

        # Filter by academic year if provided
        if current_academic_year:
            queryset = queryset.filter(academic_year=current_academic_year)
            # Print debug info
            print(
                f"Current academic year: {current_academic_year.name}, Class count: {queryset.count()}"
            )
        else:
            print("No current academic year provided to form")

        # Show all available classes for the academic year and school
        # Don't filter by student's form/learning area to allow flexibility in assignments
        if student:
            print(
                f"Student: {student.full_name} (Form: {student.form}, Learning Area: {student.learning_area})"
            )
            print(f"Available classes for assignment: {queryset.count()}")

            # List all available classes for debugging
            for cls in queryset:
                print(
                    f"  - {cls.name} (Form: {cls.form}, Learning Area: {cls.learning_area})"
                )

        # Update the queryset
        self.fields["assigned_class"].queryset = queryset

        # Update empty_label based on whether we have classes
        if not queryset.exists():
            if current_academic_year:
                self.fields["assigned_class"].empty_label = (
                    f"No classes available for {current_academic_year.name} academic year"
                )
            else:
                self.fields["assigned_class"].empty_label = (
                    "No current academic year set"
                )


from django import forms
from django.core.exceptions import ValidationError
from .models import AcademicYear, Term, AcademicYearTemplate


class AcademicYearForm(forms.ModelForm):
    """Form for creating and editing academic years"""

    class Meta:
        model = AcademicYear
        fields = ["name", "start_date", "end_date", "is_current"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "start_date": forms.DateInput(
                attrs={"class": "form-control datepicker", "type": "date"}
            ),
            "end_date": forms.DateInput(
                attrs={"class": "form-control datepicker", "type": "date"}
            ),
            "is_current": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        # Validate dates
        if start_date and end_date:
            if start_date >= end_date:
                raise ValidationError("End date must be after start date.")

        return cleaned_data

    def __init__(self, *args, **kwargs):
        """Initialize the form with optional school"""
        self.school = kwargs.pop("school", None)
        super().__init__(*args, **kwargs)

        # When saving the form, we'll use the school from the request


class TermForm(forms.ModelForm):
    """Form for creating and editing terms"""

    class Meta:
        model = Term
        fields = [
            "academic_year",
            "term_number",
            "start_date",
            "end_date",
            "is_current",
        ]
        widgets = {
            "academic_year": forms.Select(attrs={"class": "form-select"}),
            "term_number": forms.Select(attrs={"class": "form-select"}),
            "start_date": forms.DateInput(
                attrs={"class": "form-control datepicker", "type": "date"}
            ),
            "end_date": forms.DateInput(
                attrs={"class": "form-control datepicker", "type": "date"}
            ),
            "is_current": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        academic_year = cleaned_data.get("academic_year")
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        term_number = cleaned_data.get("term_number")

        # Validate dates
        if start_date and end_date:
            if start_date >= end_date:
                raise ValidationError("Term end date must be after start date.")

            # Validate term dates are within academic year
            if academic_year:
                if start_date < academic_year.start_date:
                    raise ValidationError(
                        "Term start date cannot be before academic year start date."
                    )
                if end_date > academic_year.end_date:
                    raise ValidationError(
                        "Term end date cannot be after academic year end date."
                    )

                # Check for term_number uniqueness in this academic year
                # This check is only for new terms or when changing term_number
                instance = getattr(self, "instance", None)
                if instance and instance.pk:
                    # Editing existing term
                    if instance.term_number != term_number:
                        # Term number changed, check for uniqueness
                        existing = (
                            Term.objects.filter(
                                academic_year=academic_year,
                                term_number=term_number,
                                school=academic_year.school,  # Add school filter for multi-tenancy
                            )
                            .exclude(pk=instance.pk)
                            .exists()
                        )

                        if existing:
                            raise ValidationError(
                                f"Term {term_number} already exists for this academic year."
                            )
                else:
                    # New term
                    existing = Term.objects.filter(
                        academic_year=academic_year,
                        term_number=term_number,
                        school=academic_year.school,  # Add school filter for multi-tenancy
                    ).exists()

                    if existing:
                        raise ValidationError(
                            f"Term {term_number} already exists for this academic year."
                        )

                # Check for overlapping terms in the same academic year
                overlapping_terms = Term.objects.filter(
                    academic_year=academic_year,
                    school=academic_year.school,  # Add school filter for multi-tenancy
                    start_date__lte=end_date,
                    end_date__gte=start_date,
                )

                # Exclude current instance when editing
                if instance and instance.pk:
                    overlapping_terms = overlapping_terms.exclude(pk=instance.pk)

                if overlapping_terms.exists():
                    overlap = overlapping_terms.first()
                    raise ValidationError(
                        f"Term dates overlap with {overlap.get_term_number_display()} "
                        f"({overlap.start_date.strftime('%d %b %Y')} to {overlap.end_date.strftime('%d %b %Y')})"
                    )

        return cleaned_data

    def __init__(self, *args, **kwargs):
        """Initialize the form with optional school"""
        self.school = kwargs.pop("school", None)
        super().__init__(*args, **kwargs)

        # Filter academic years by school if provided
        if self.school:
            self.fields["academic_year"].queryset = AcademicYear.objects.filter(
                school=self.school
            )


from django import forms
from .models import Subject


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ["subject_name", "learning_area", "department"]
        widgets = {
            "subject_name": forms.TextInput(attrs={"class": "form-control"}),
            "learning_area": forms.Select(attrs={"class": "form-select"}),
            "department": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        """Initialize the form with school context"""
        self.school = kwargs.pop("school", None)
        super().__init__(*args, **kwargs)

        # Filter learning_area and department options by school
        if self.school:
            self.fields["learning_area"].queryset = LearningArea.objects.filter(
                school=self.school
            ).order_by("name")

            self.fields["department"].queryset = Department.objects.filter(
                school=self.school
            ).order_by("name")

    def clean_subject_name(self):
        subject_name = self.cleaned_data.get("subject_name")
        instance_id = self.instance.id if self.instance else None

        # Check if subject name already exists in the same school
        query = Subject.objects.filter(subject_name=subject_name)
        if self.school:
            query = query.filter(school=self.school)

        if instance_id:
            query = query.exclude(id=instance_id)

        if query.exists():
            raise ValidationError(
                "A subject with this name already exists in this school."
            )

        return subject_name

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.school and not instance.school:
            instance.school = self.school
        if commit:
            instance.save()
        return instance


from django import forms
from .models import Class, Teacher, AcademicYear


class ClassForm(forms.ModelForm):
    class Meta:
        model = Class
        fields = [
            "name",
            "form",
            "learning_area",
            "academic_year",
            "maximum_students",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "form": forms.Select(attrs={"class": "form-select"}),
            "learning_area": forms.Select(attrs={"class": "form-select"}),
            "academic_year": forms.Select(attrs={"class": "form-select"}),
            "maximum_students": forms.NumberInput(
                attrs={"class": "form-control", "min": "0", "max": "100"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["academic_year"].queryset = AcademicYear.objects.all().order_by(
            "-name"
        )

        # Add helpful placeholders
        self.fields["name"].widget.attrs["placeholder"] = "e.g., 1Science, 2Art1"

    def clean(self):
        cleaned_data = super().clean()

        # If this is an existing class, check student count against maximum
        if self.instance.pk:
            current_count = self.instance.get_current_student_count()
            max_students = cleaned_data.get("maximum_students")

            if max_students and current_count > max_students:
                self.add_error(
                    "maximum_students",
                    f"Cannot set maximum below current student count ({current_count})",
                )

        return cleaned_data


from django import forms
from .models import SchoolInformation, SchoolAuthoritySignature


class SchoolInformationForm(forms.ModelForm):
    class Meta:
        model = SchoolInformation
        fields = [
            "name",
            "short_name",
            "address",
            "postal_code",
            "phone_number",
            "email",
            "website",
            "school_code",
            "logo",
            "school_stamp",
            "report_header",
            "report_footer",
            "motto",
            "vision",
            "mission",
            "grading_system_description",
            "current_academic_year",
            "current_term",
        ]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
            "report_header": forms.Textarea(attrs={"rows": 3}),
            "report_footer": forms.Textarea(attrs={"rows": 3}),
            "vision": forms.Textarea(attrs={"rows": 3}),
            "mission": forms.Textarea(attrs={"rows": 3}),
            "grading_system_description": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        # Get the user and school from kwargs if provided
        self.user = kwargs.pop("user", None)
        self.user_school = kwargs.pop("user_school", None)

        super().__init__(*args, **kwargs)

        # Store the initial current_term for reference
        self.initial_term = None
        if self.instance and self.instance.pk:
            self.initial_term = self.instance.current_term

        # Get form data if provided
        form_data = None
        if len(args) > 0:
            form_data = args[0]

        # Filter academic years by school for multi-tenancy (exclude archived)
        if self.user and not self.user.is_superadmin and self.user_school:
            self.fields["current_academic_year"].queryset = AcademicYear.objects.filter(
                school=self.user_school, is_archived=False
            ).order_by("-start_date")
        elif self.instance and self.instance.pk:
            # If editing an existing school, only show active academic years for that school
            self.fields["current_academic_year"].queryset = AcademicYear.objects.filter(
                school=self.instance, is_archived=False
            ).order_by("-start_date")

        # On form submission, we need ALL terms to be valid options
        # This is critical to allow validation to pass and then check in clean_current_term
        if self.is_bound:
            # For form submissions, include terms filtered by school
            if self.user and not self.user.is_superadmin and self.user_school:
                self.fields["current_term"].queryset = Term.objects.filter(
                    school=self.user_school
                ).order_by("academic_year__name", "start_date")
            elif self.instance and self.instance.pk:
                self.fields["current_term"].queryset = Term.objects.filter(
                    school=self.instance
                ).order_by("academic_year__name", "start_date")
            else:
                # For superadmins, include all terms
                self.fields["current_term"].queryset = Term.objects.all().order_by(
                    "academic_year__name", "start_date"
                )

        # For initial display only, filter terms by the selected academic year
        elif self.instance and self.instance.pk and self.instance.current_academic_year:
            # Filter terms by the selected academic year for initial display
            self.fields["current_term"].queryset = Term.objects.filter(
                academic_year=self.instance.current_academic_year
            ).order_by("start_date")
        else:
            # If no academic year is selected, show no terms initially
            self.fields["current_term"].queryset = Term.objects.none()

    def clean(self):
        """Overall form validation"""
        cleaned_data = super().clean()
        # Most validation is now handled in clean_current_term
        return cleaned_data

    def clean_current_term(self):
        """Custom validation for the current_term field to ensure it belongs to the selected academic year"""
        current_term = self.cleaned_data.get("current_term")
        current_academic_year = self.cleaned_data.get("current_academic_year")

        # Skip validation if either field is empty
        if not current_term or not current_academic_year:
            return current_term

        # Check if term belongs to the selected academic year
        if current_term.academic_year != current_academic_year:
            # Get all valid terms
            valid_terms = Term.objects.filter(
                academic_year=current_academic_year
            ).order_by("start_date")

            # Update queryset to include these valid terms
            self.fields["current_term"].queryset = valid_terms

            # Provide descriptive error message
            raise forms.ValidationError(
                f"Selected term '{current_term}' does not belong to academic year '{current_academic_year}'. "
                f"Please select a term from the academic year {current_academic_year}."
            )

        return current_term


class SchoolAuthoritySignatureForm(forms.ModelForm):
    class Meta:
        model = SchoolAuthoritySignature
        fields = [
            "authority_type",
            "name",
            "title",
            "signature",
            "is_active",
            "custom_title",
            "school",
        ]
        widgets = {
            # Make the school field hidden if you want to set it programmatically
            "school": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initially hide the custom_title field
        self.fields["custom_title"].widget.attrs["class"] = "hidden-field"

        # Add JavaScript to show/hide custom_title field based on authority_type
        self.fields["authority_type"].widget.attrs["onchange"] = (
            "document.getElementById('id_custom_title').parentNode.style.display = "
            "(this.value === 'other' ? 'block' : 'none');"
        )

    def clean(self):
        cleaned_data = super().clean()
        authority_type = cleaned_data.get("authority_type")
        custom_title = cleaned_data.get("custom_title")

        if authority_type == "other" and not custom_title:
            self.add_error(
                "custom_title",
                "Custom title is required when 'Other Authority' is selected.",
            )

        return cleaned_data


# forms.py
from django import forms
from .models import StudentTermRemarks


class StudentTermRemarksForm(forms.ModelForm):
    class Meta:
        model = StudentTermRemarks
        fields = [
            "interest_remarks",
            "conduct_remarks",
            "attitude_remarks",
            "general_remarks",
            "days_present",
            "days_absent",
            "total_school_days",
            "auto_calculate_attendance",
        ]
        widgets = {
            "interest_remarks": forms.TextInput(attrs={"class": "form-control"}),
            "conduct_remarks": forms.TextInput(attrs={"class": "form-control"}),
            "attitude_remarks": forms.TextInput(attrs={"class": "form-control"}),
            "general_remarks": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "days_present": forms.NumberInput(attrs={"class": "form-control"}),
            "days_absent": forms.NumberInput(attrs={"class": "form-control"}),
            "total_school_days": forms.NumberInput(attrs={"class": "form-control"}),
            "auto_calculate_attendance": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }


from django import forms
from django.contrib.auth.forms import PasswordResetForm
from .models import User


class UserCreationForm(forms.ModelForm):
    """Form for creating a new user by an admin"""

    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm Password", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ["username", "email", "full_name", "role"]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "full_name": forms.TextInput(attrs={"class": "form-control"}),
            "role": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to all fields
        for field in self.fields.values():
            if not isinstance(field.widget, forms.Select):
                field.widget.attrs.update({"class": "form-control"})

    def clean_password2(self):
        # Check that the two password entries match
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        # Save the provided password in hashed format
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


# Add these new forms for the new models
class FormForm(forms.ModelForm):
    class Meta:
        model = Form
        fields = ["form_number", "name", "description"]
        widgets = {
            "form_number": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter form/grade number",
                }
            ),
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Enter form/grade name"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Enter description (optional)",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        """Initialize the form with school context"""
        self.school = kwargs.pop("school", None)
        super().__init__(*args, **kwargs)

    def clean_form_number(self):
        form_number = self.cleaned_data.get("form_number")
        instance_id = self.instance.id if self.instance else None

        # Check if form number already exists in the same school
        query = Form.objects.filter(form_number=form_number)
        if self.school:
            query = query.filter(school=self.school)

        if instance_id:
            query = query.exclude(id=instance_id)

        if query.exists():
            raise ValidationError(
                "A form with this number already exists in this school."
            )

        return form_number

    def clean_name(self):
        name = self.cleaned_data.get("name")
        instance_id = self.instance.id if self.instance else None

        # Check if form name already exists in the same school
        query = Form.objects.filter(name=name)
        if self.school:
            query = query.filter(school=self.school)

        if instance_id:
            query = query.exclude(id=instance_id)

        if query.exists():
            raise ValidationError(
                "A form with this name already exists in this school."
            )

        return name

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.school and not instance.school:
            instance.school = self.school
        if commit:
            instance.save()
        return instance


class LearningAreaForm(forms.ModelForm):
    class Meta:
        model = LearningArea
        fields = ["code", "name", "description"]
        widgets = {
            "code": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter learning area code",
                }
            ),
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter learning area name",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Enter description (optional)",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        """Initialize the form with school context"""
        self.school = kwargs.pop("school", None)
        super().__init__(*args, **kwargs)

    def clean_code(self):
        code = self.cleaned_data.get("code")
        instance_id = self.instance.id if self.instance else None

        # Check if code already exists in the same school
        query = LearningArea.objects.filter(code=code)
        if self.school:
            query = query.filter(school=self.school)

        if instance_id:
            query = query.exclude(id=instance_id)

        if query.exists():
            raise ValidationError(
                "A learning area with this code already exists in this school."
            )

        return code

    def clean_name(self):
        name = self.cleaned_data.get("name")
        instance_id = self.instance.id if self.instance else None

        # Check if name already exists in the same school
        query = LearningArea.objects.filter(name=name)
        if self.school:
            query = query.filter(school=self.school)

        if instance_id:
            query = query.exclude(id=instance_id)

        if query.exists():
            raise ValidationError(
                "A learning area with this name already exists in this school."
            )

        return name

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.school and not instance.school:
            instance.school = self.school
        if commit:
            instance.save()
        return instance


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ["name", "code", "description", "head_of_department"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Enter department name"}
            ),
            "code": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Enter department code"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Enter description (optional)",
                }
            ),
            "head_of_department": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        """Initialize the form with school context"""
        self.school = kwargs.pop("school", None)
        super().__init__(*args, **kwargs)

        # Filter head_of_department options by school
        if self.school:
            self.fields["head_of_department"].queryset = Teacher.objects.filter(
                user__school=self.school
            ).order_by("full_name")

    def clean_code(self):
        code = self.cleaned_data.get("code")
        instance_id = self.instance.id if self.instance else None

        # Check if code already exists in the same school
        query = Department.objects.filter(code=code)
        if self.school:
            query = query.filter(school=self.school)

        if instance_id:
            query = query.exclude(id=instance_id)

        if query.exists():
            raise ValidationError(
                "A department with this code already exists in this school."
            )

        return code

    def clean_name(self):
        name = self.cleaned_data.get("name")
        instance_id = self.instance.id if self.instance else None

        # Check if name already exists in the same school
        query = Department.objects.filter(name=name)
        if self.school:
            query = query.filter(school=self.school)

        if instance_id:
            query = query.exclude(id=instance_id)

        if query.exists():
            raise ValidationError(
                "A department with this name already exists in this school."
            )

        return name

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.school and not instance.school:
            instance.school = self.school
        if commit:
            instance.save()
        return instance


# Teacher Activity Monitoring Forms
class TeacherActivityMonitoringFilterForm(forms.Form):
    """Form for filtering teacher activity monitoring data"""

    academic_year = forms.ModelChoiceField(
        queryset=AcademicYear.objects.all(),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
        empty_label="All Academic Years",
    )
    term = forms.ModelChoiceField(
        queryset=Term.objects.all(),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
        empty_label="All Terms",
    )
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
        empty_label="All Departments",
    )
    activity_type = forms.ChoiceField(
        choices=[
            ("", "All Activities"),
            ("scores", "Score Entry"),
            ("remarks", "Student Remarks"),
            ("attendance", "Attendance"),
            ("report_cards", "Report Cards"),
        ],
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    completion_status = forms.ChoiceField(
        choices=[
            ("", "All Statuses"),
            ("completed", "Completed"),
            ("in_progress", "In Progress"),
            ("not_started", "Not Started"),
            ("overdue", "Overdue"),
        ],
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, *args, **kwargs):
        """Initialize the form with optional school"""
        self.school = kwargs.pop("school", None)
        super().__init__(*args, **kwargs)

        # Filter querysets by school if provided
        if self.school:
            self.fields["academic_year"].queryset = AcademicYear.objects.filter(
                school=self.school
            ).order_by("-start_date")

            self.fields["department"].queryset = Department.objects.filter(
                school=self.school
            ).order_by("name")

            # Also filter terms by school
            self.fields["term"].queryset = Term.objects.filter(
                school=self.school
            ).order_by("academic_year", "start_date")

            # Get selected academic year from data or initial
            data = kwargs.get("data", None)
            initial = kwargs.get("initial", None)

            if data and data.get("academic_year"):
                try:
                    academic_year_id = int(data.get("academic_year"))
                    # Filter terms by academic year and school
                    self.fields["term"].queryset = Term.objects.filter(
                        academic_year_id=academic_year_id, school=self.school
                    ).order_by("start_date")
                except (ValueError, TypeError):
                    pass
            elif initial and initial.get("academic_year"):
                # Filter terms by initial academic year
                self.fields["term"].queryset = Term.objects.filter(
                    academic_year=initial.get("academic_year"), school=self.school
                ).order_by("start_date")


class BulkStudentClassAssignmentForm(forms.Form):
    """
    Form for bulk assignment of students to classes
    """

    students = forms.ModelMultipleChoiceField(
        queryset=Student.objects.none(),
        widget=forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
        label="Select Students",
    )
    assigned_class = forms.ModelChoiceField(
        queryset=Class.objects.none(),
        label="Assign to Class",
        widget=forms.Select(attrs={"class": "form-select"}),
        empty_label="Select a class",
    )

    def __init__(self, *args, **kwargs):
        current_academic_year = kwargs.pop("current_academic_year", None)
        school = kwargs.pop("school", None)
        super().__init__(*args, **kwargs)

        if school:
            # Filter students by school
            self.fields["students"].queryset = Student.objects.filter(
                school=school
            ).order_by("full_name")

            # Filter classes by school and academic year
            if current_academic_year:
                self.fields["assigned_class"].queryset = Class.objects.filter(
                    school=school, academic_year=current_academic_year
                ).order_by("name")


class StudentClassAssignmentFilterForm(forms.Form):
    """
    Form for filtering students in class assignment views
    """

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Search by name, admission number, or contact...",
            }
        ),
        label="Search",
    )

    form = forms.ModelChoiceField(
        queryset=Form.objects.none(),
        required=False,
        empty_label="All Forms",
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Form",
    )

    learning_area = forms.ModelChoiceField(
        queryset=LearningArea.objects.none(),
        required=False,
        empty_label="All Learning Areas",
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Learning Area",
    )

    gender = forms.ChoiceField(
        choices=[("", "All Genders"), ("M", "Male"), ("F", "Female")],
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Gender",
    )

    status = forms.ChoiceField(
        choices=[
            ("", "All Students"),
            ("assigned", "Assigned"),
            ("unassigned", "Unassigned"),
        ],
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Assignment Status",
    )

    assigned_class = forms.ModelChoiceField(
        queryset=Class.objects.none(),
        required=False,
        empty_label="All Classes",
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Current Class",
    )

    assignment_date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        label="Assignment Date From",
    )

    assignment_date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        label="Assignment Date To",
    )

    def __init__(self, *args, **kwargs):
        school = kwargs.pop("school", None)
        current_academic_year = kwargs.pop("current_academic_year", None)
        super().__init__(*args, **kwargs)

        if school:
            self.fields["form"].queryset = Form.objects.filter(school=school).order_by(
                "form_number"
            )
            self.fields["learning_area"].queryset = LearningArea.objects.filter(
                school=school
            ).order_by("name")

            if current_academic_year:
                self.fields["assigned_class"].queryset = Class.objects.filter(
                    school=school, academic_year=current_academic_year
                ).order_by("name")


class StudentClassAssignmentSearchForm(forms.Form):
    """
    Quick search form for student class assignment
    """

    query = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Search students...",
                "autocomplete": "off",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["query"].widget.attrs.update(
            {
                "data-toggle": "tooltip",
                "title": "Search by name, admission number, or contact",
            }
        )


# Academic Year Template Forms
class AcademicYearTemplateForm(forms.ModelForm):
    """Form for creating and editing academic year templates"""

    class Meta:
        model = AcademicYearTemplate
        fields = ["name", "description", "is_default"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "is_default": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        self.school = kwargs.pop("school", None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get("name")
        is_default = cleaned_data.get("is_default", False)

        if self.school and name:
            # Check for duplicate names within the same school
            existing = AcademicYearTemplate.objects.filter(
                name=name, school=self.school, is_active=True
            ).exclude(pk=self.instance.pk if self.instance.pk else None)

            if existing.exists():
                raise ValidationError(
                    "A template with this name already exists for your school."
                )

        return cleaned_data


class CreateTemplateFromAcademicYearForm(forms.Form):
    """Form for creating a template from an existing academic year"""

    academic_year = forms.ModelChoiceField(
        queryset=AcademicYear.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Select Academic Year",
        help_text="Choose the academic year to create a template from",
    )

    template_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control"}),
        label="Template Name",
        help_text="Enter a name for the new template",
    )

    description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        label="Description",
        help_text="Optional description for the template",
    )

    is_default = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        label="Set as Default Template",
        help_text="Make this the default template for new academic years",
    )

    def __init__(self, *args, **kwargs):
        self.school = kwargs.pop("school", None)
        super().__init__(*args, **kwargs)

        if self.school:
            # Filter academic years by school
            self.fields["academic_year"].queryset = AcademicYear.objects.filter(
                school=self.school
            ).order_by("-start_date")

    def clean_template_name(self):
        template_name = self.cleaned_data.get("template_name")

        if self.school and template_name:
            # Check for duplicate names within the same school
            existing = AcademicYearTemplate.objects.filter(
                name=template_name, school=self.school, is_active=True
            )

            if existing.exists():
                raise ValidationError(
                    "A template with this name already exists for your school."
                )

        return template_name


class ApplyTemplateForm(forms.Form):
    """Form for applying a template to create a new academic year"""

    template = forms.ModelChoiceField(
        queryset=AcademicYearTemplate.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Select Template",
        help_text="Choose the template to apply",
    )

    academic_year_name = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={"class": "form-control"}),
        label="Academic Year Name",
        help_text="e.g., 2024/2025",
    )

    start_date = forms.DateField(
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        label="Start Date",
    )

    end_date = forms.DateField(
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        label="End Date",
    )

    is_current = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        label="Set as Current Academic Year",
        help_text="Make this the current academic year",
    )

    # Customization options
    customize_class_names = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        label="Customize Class Names",
        help_text="Allow customization of class names during creation",
    )

    def __init__(self, *args, **kwargs):
        self.school = kwargs.pop("school", None)
        super().__init__(*args, **kwargs)

        if self.school:
            # Filter templates by school
            self.fields["template"].queryset = AcademicYearTemplate.objects.filter(
                school=self.school, is_active=True
            ).order_by("-is_default", "name")

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if start_date and end_date:
            if start_date >= end_date:
                raise ValidationError("End date must be after start date.")

        return cleaned_data


class TemplateCustomizationForm(forms.Form):
    """Form for customizing template application"""

    class_prefixes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 5}),
        label="Class Prefix Mappings",
        help_text="Enter class prefix mappings (one per line): old_prefix=new_prefix",
    )

    year_suffix = forms.CharField(
        required=False,
        max_length=20,
        widget=forms.TextInput(attrs={"class": "form-control"}),
        label="Year Suffix",
        help_text="Add a suffix to all class names (e.g., '2024')",
    )

    def clean_class_prefixes(self):
        class_prefixes = self.cleaned_data.get("class_prefixes", "")
        if not class_prefixes:
            return {}

        mappings = {}
        for line in class_prefixes.strip().split("\n"):
            line = line.strip()
            if "=" in line:
                old_prefix, new_prefix = line.split("=", 1)
                mappings[old_prefix.strip()] = new_prefix.strip()

        return mappings
