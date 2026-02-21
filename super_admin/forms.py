from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone
from datetime import timedelta
from shs_system.models import User, SchoolInformation
from .models import (
    Plan,
    Subscription,
    SchoolDomain,
    PaymentTransaction,
    SuperAdminSettings,
    SystemEmailConfig,
)


class SchoolForm(forms.ModelForm):
    """Form for creating and updating schools"""

    # Add non-model fields for admin creation
    admin_name = forms.CharField(
        max_length=255, required=True, help_text="Name of the school administrator"
    )
    admin_email = forms.EmailField(
        required=True, help_text="Email of the school administrator"
    )
    domain = forms.CharField(
        max_length=255,
        required=True,
        help_text="The subdomain for the school (e.g., 'school1' for local development)",
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        required=False,
        help_text="Description of the school",
    )
    is_featured = forms.BooleanField(
        required=False, initial=False, help_text="Feature this school on the platform"
    )

    class Meta:
        model = SchoolInformation
        fields = [
            "name",
            "address",
            "phone_number",
            "email",
            "website",
            "logo",
            "is_active",
        ]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
        }
        help_texts = {
            "is_active": "Inactive schools cannot be accessed by users.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If we're editing an existing school, prefill the description field
        if self.instance and self.instance.pk:
            self.fields["description"].initial = (
                self.instance.vision
            )  # Using vision field for description
            # You can check if the school is featured by checking for it in a list of featured schools
            # or checking a specific property if implemented

    def clean_domain(self):
        """Validate that the domain is unique"""
        domain = self.cleaned_data.get("domain")
        if domain:
            # Support various domain formats for development
            # If the domain already contains a dot, use it as is
            if "." in domain:
                full_domain = domain
            else:
                # For development, we'll use domain.localhost format
                full_domain = f"{domain}.localhost"

            # Exclude current domain if updating
            if self.instance and self.instance.pk:
                domain_query = SchoolDomain.objects.filter(domain__iexact=full_domain)
                # If this domain belongs to the current school, it's fine
                if domain_query.filter(school=self.instance).exists():
                    return domain

            if SchoolDomain.objects.filter(domain__iexact=full_domain).exists():
                raise forms.ValidationError(
                    "This domain is already in use by another school."
                )
        return domain

    def save(self, commit=True):
        school = super().save(commit=False)

        # Save the description to the vision field (using vision as description)
        school.vision = self.cleaned_data.get("description")

        # Handle is_featured (implementation depends on how featuring is tracked)
        # For example, you might add it to a special group or set a property

        if commit:
            school.save()

        return school


class SchoolAdminForm(forms.ModelForm):
    """Form for creating and updating school administrators"""

    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        required=False,
        help_text="Leave blank to generate a random password.",
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        required=False,
        help_text="Enter the same password as above, for verification.",
    )

    send_credentials = forms.BooleanField(
        label="Send login credentials via email",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    class Meta:
        model = User
        fields = ["username", "email", "full_name"]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "full_name": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        self.school = kwargs.pop("school", None)
        super().__init__(*args, **kwargs)

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)

        # Set role and school
        user.role = "admin"
        if self.school:
            user.school = self.school

        # Handle password
        password = self.cleaned_data.get("password1")
        if not password:
            # Generate a random password
            import random
            import string

            password = "".join(
                random.choices(string.ascii_letters + string.digits, k=10)
            )

        user.set_password(password)

        # Store the generated password temporarily for sending email
        user.temp_password = password

        if commit:
            user.save()

        return user


class PlanForm(forms.ModelForm):
    """Form for creating and updating subscription plans"""

    class Meta:
        model = Plan
        fields = [
            "name",
            "description",
            "price",
            "billing_cycle",
            "max_students",
            "max_teachers",
            "max_storage_gb",
            "features",
            "is_active",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "features": forms.Textarea(attrs={"rows": 5}),
        }
        help_texts = {
            "features": 'Enter features as a JSON object, e.g., {"feature1": true, "feature2": false}',
        }


class SubscriptionForm(forms.ModelForm):
    """Form for creating and updating subscriptions"""

    trial_days = forms.IntegerField(
        min_value=0,
        max_value=365,
        required=False,
        help_text="Number of trial days (leave empty for no trial)",
    )

    class Meta:
        model = Subscription
        fields = [
            "school",
            "plan",
            "status",
            "start_date",
            "end_date",
            "payment_method",
            "auto_renew",
        ]
        widgets = {
            "start_date": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "end_date": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active plans
        self.fields["plan"].queryset = Plan.objects.filter(is_active=True)

        # If this is a new subscription (not an update)
        if not self.instance.pk:
            # Set default start date to now
            self.fields["start_date"].initial = timezone.now()

            # Set default end date to 1 year from now
            self.fields["end_date"].initial = timezone.now() + timedelta(days=365)

    def save(self, commit=True):
        subscription = super().save(commit=False)

        # Handle trial period
        trial_days = self.cleaned_data.get("trial_days")
        if trial_days:
            subscription.status = "trial"
            subscription.trial_ends_at = timezone.now() + timedelta(days=trial_days)

        if commit:
            subscription.save()

        return subscription


class SchoolDomainForm(forms.ModelForm):
    """Form for creating and updating school domains"""

    class Meta:
        model = SchoolDomain
        fields = ["school", "domain", "is_primary"]
        help_texts = {
            "domain": "Enter the domain name without http:// or https://, e.g., school.example.com",
            "is_primary": "The primary domain is used as the default for this school.",
        }


class SuperAdminSettingsForm(forms.ModelForm):
    """Form for updating platform settings"""

    class Meta:
        model = SuperAdminSettings
        fields = [
            "site_name",
            "contact_email",
            "support_phone",
            "default_trial_days",
            "allow_new_registrations",
            "terms_and_conditions",
            "privacy_policy",
            "platform_fee_percentage",
            "is_maintenance_mode",
            "maintenance_message",
        ]
        widgets = {
            "terms_and_conditions": forms.Textarea(attrs={"rows": 10}),
            "privacy_policy": forms.Textarea(attrs={"rows": 10}),
            "maintenance_message": forms.Textarea(attrs={"rows": 3}),
        }


class SuperAdminUserForm(UserCreationForm):
    """Form for creating and updating super admin users"""

    class Meta:
        model = User
        fields = ["username", "email", "full_name", "is_superadmin", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set is_superadmin to True by default
        self.fields["is_superadmin"].initial = True

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = "superadmin"
        user.is_superadmin = True
        user.is_staff = True

        if commit:
            user.save()

        return user


class SystemEmailConfigForm(forms.ModelForm):
    """Form for configuring system email settings"""

    # Add a test connection button
    test_connection = forms.BooleanField(
        required=False,
        label="Test connection after saving",
        initial=True,
        help_text="Send a test email to verify the configuration",
    )

    # Add a test email field
    test_email = forms.EmailField(
        required=False,
        label="Test email recipient",
        help_text="Email address to send the test email to",
    )

    class Meta:
        model = SystemEmailConfig
        fields = [
            "name",
            "service_type",
            "is_active",
            "from_email",
            "from_name",
            "reply_to",
            "smtp_host",
            "smtp_port",
            "smtp_username",
            "smtp_password",
            "smtp_use_tls",
            "smtp_use_ssl",
            "oauth_provider",
            "client_id",
            "client_secret",
            "refresh_token",
            "test_connection",
            "test_email",
        ]
        widgets = {
            "smtp_password": forms.PasswordInput(render_value=True),
            "client_secret": forms.PasswordInput(render_value=True),
            "smtp_use_ssl": forms.CheckboxInput(),
            "smtp_use_tls": forms.CheckboxInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Make some fields required based on service type
        if self.data.get("service_type") == "smtp":
            self.fields["smtp_host"].required = True
            self.fields["smtp_port"].required = True
            self.fields["smtp_username"].required = True
            self.fields["smtp_password"].required = True
        elif self.data.get("service_type") == "oauth":
            self.fields["client_id"].required = True
            self.fields["client_secret"].required = True
            self.fields["refresh_token"].required = True

        # If testing connection, require test email
        if self.data.get("test_connection"):
            self.fields["test_email"].required = True

        # Ensure boolean fields are properly handled
        if "smtp_use_ssl" in self.data:
            self.fields["smtp_use_ssl"].initial = self.data.get("smtp_use_ssl") == "on"
        if "smtp_use_tls" in self.data:
            self.fields["smtp_use_tls"].initial = self.data.get("smtp_use_tls") == "on"

    def clean(self):
        cleaned_data = super().clean()
        service_type = cleaned_data.get("service_type")

        # Validate SMTP settings
        if service_type == "smtp":
            if not cleaned_data.get("smtp_host"):
                self.add_error("smtp_host", "SMTP host is required for SMTP service")
            if not cleaned_data.get("smtp_port"):
                self.add_error("smtp_port", "SMTP port is required for SMTP service")
            if not cleaned_data.get("smtp_username"):
                self.add_error(
                    "smtp_username", "SMTP username is required for SMTP service"
                )
            if not cleaned_data.get("smtp_password"):
                self.add_error(
                    "smtp_password", "SMTP password is required for SMTP service"
                )

            # Validate port and SSL/TLS settings
            port = cleaned_data.get("smtp_port")
            use_ssl = cleaned_data.get("smtp_use_ssl")
            use_tls = cleaned_data.get("smtp_use_tls")

            if port == 465 and not use_ssl:
                cleaned_data["smtp_use_ssl"] = True
                cleaned_data["smtp_use_tls"] = False
            elif port == 587 and not use_tls:
                cleaned_data["smtp_use_ssl"] = False
                cleaned_data["smtp_use_tls"] = True

        # Validate OAuth settings
        elif service_type == "oauth":
            if not cleaned_data.get("client_id"):
                self.add_error("client_id", "Client ID is required for OAuth service")
            if not cleaned_data.get("client_secret"):
                self.add_error(
                    "client_secret", "Client secret is required for OAuth service"
                )
            if not cleaned_data.get("refresh_token"):
                self.add_error(
                    "refresh_token", "Refresh token is required for OAuth service"
                )

        # If test connection is checked, test email is required
        if cleaned_data.get("test_connection") and not cleaned_data.get("test_email"):
            self.add_error(
                "test_email",
                "Test email is required if you want to test the connection",
            )

        return cleaned_data
