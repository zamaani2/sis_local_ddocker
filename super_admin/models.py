from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid


class Plan(models.Model):
    """Subscription plans for schools"""

    BILLING_CYCLES = (
        ("monthly", "Monthly"),
        ("quarterly", "Quarterly"),
        ("annually", "Annually"),
    )

    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    billing_cycle = models.CharField(
        max_length=20, choices=BILLING_CYCLES, default="monthly"
    )
    max_students = models.PositiveIntegerField(default=500)
    max_teachers = models.PositiveIntegerField(default=50)
    max_storage_gb = models.PositiveIntegerField(default=5)
    features = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.get_billing_cycle_display()} (${self.price})"


class Subscription(models.Model):
    """School subscription information"""

    STATUS_CHOICES = (
        ("active", "Active"),
        ("trial", "Trial"),
        ("expired", "Expired"),
        ("cancelled", "Cancelled"),
        ("pending", "Pending"),
    )

    school = models.OneToOneField(
        "shs_system.SchoolInformation",
        on_delete=models.CASCADE,
        related_name="subscription",
    )
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="trial")
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    subscription_id = models.CharField(
        max_length=100, unique=True, blank=True, null=True
    )  # For payment gateway reference
    payment_method = models.CharField(max_length=100, blank=True, null=True)
    auto_renew = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.school.name} - {self.plan.name} ({self.status})"

    def is_valid(self):
        """Check if subscription is valid"""
        if self.status == "active":
            return timezone.now() <= self.end_date
        elif self.status == "trial":
            return timezone.now() <= self.trial_ends_at
        return False

    def days_remaining(self):
        """Calculate days remaining in subscription"""
        if self.status == "active":
            delta = self.end_date - timezone.now()
        elif self.status == "trial":
            delta = self.trial_ends_at - timezone.now()
        else:
            return 0
        return max(0, delta.days)


class SchoolDomain(models.Model):
    """Custom domains for schools"""

    school = models.ForeignKey(
        "shs_system.SchoolInformation", on_delete=models.CASCADE, related_name="domains"
    )
    domain = models.CharField(max_length=255, unique=True)
    is_primary = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    verification_token = models.UUIDField(default=uuid.uuid4)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.domain

    def save(self, *args, **kwargs):
        # Ensure only one primary domain per school
        if self.is_primary:
            SchoolDomain.objects.filter(school=self.school, is_primary=True).exclude(
                pk=self.pk
            ).update(is_primary=False)
        super().save(*args, **kwargs)


class PaymentTransaction(models.Model):
    """Payment transactions for subscriptions"""

    PAYMENT_STATUS = (
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    )

    subscription = models.ForeignKey(
        Subscription, on_delete=models.CASCADE, related_name="transactions"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    payment_method = models.CharField(max_length=100)
    transaction_id = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS)
    payment_date = models.DateTimeField(default=timezone.now)
    invoice_number = models.CharField(max_length=50, unique=True)
    receipt_url = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.invoice_number} - {self.amount} {self.currency} ({self.status})"


class SuperAdminSettings(models.Model):
    """Global settings for the super admin"""

    site_name = models.CharField(max_length=100, default="SchoolApp Platform")
    contact_email = models.EmailField()
    support_phone = models.CharField(max_length=20, blank=True, null=True)
    default_trial_days = models.PositiveIntegerField(default=30)
    allow_new_registrations = models.BooleanField(default=True)
    terms_and_conditions = models.TextField(blank=True, null=True)
    privacy_policy = models.TextField(blank=True, null=True)
    platform_fee_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    is_maintenance_mode = models.BooleanField(default=False)
    maintenance_message = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Super Admin Settings"
        verbose_name_plural = "Super Admin Settings"

    def __str__(self):
        return self.site_name


class SystemEmailConfig(models.Model):
    """Centralized email configuration for the entire platform"""

    # Service types
    SERVICE_TYPES = (
        ("smtp", "SMTP Server"),
        ("oauth", "OAuth2 (Google)"),
        ("api", "Email API Service"),
    )

    name = models.CharField(max_length=100, default="System Email")
    service_type = models.CharField(
        max_length=20, choices=SERVICE_TYPES, default="oauth"
    )
    is_active = models.BooleanField(default=True)

    # SMTP settings
    smtp_host = models.CharField(max_length=255, blank=True, null=True)
    smtp_port = models.PositiveIntegerField(blank=True, null=True)
    smtp_username = models.CharField(max_length=255, blank=True, null=True)
    smtp_password = models.CharField(max_length=255, blank=True, null=True)
    smtp_use_tls = models.BooleanField(default=False)
    smtp_use_ssl = models.BooleanField(default=True)

    # OAuth2 settings
    oauth_provider = models.CharField(max_length=50, default="google", blank=True)
    client_id = models.CharField(max_length=255, blank=True, null=True)
    client_secret = models.CharField(max_length=255, blank=True, null=True)
    refresh_token = models.TextField(blank=True, null=True)
    access_token = models.TextField(blank=True, null=True)
    token_uri = models.CharField(
        max_length=255, default="https://oauth2.googleapis.com/token", blank=True
    )
    scopes = models.JSONField(default=list)

    # Common email settings
    from_email = models.EmailField()
    from_name = models.CharField(max_length=100, blank=True, null=True)
    reply_to = models.EmailField(blank=True, null=True)

    # Tracking
    last_used = models.DateTimeField(blank=True, null=True)
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "System Email Configuration"
        verbose_name_plural = "System Email Configurations"

    def __str__(self):
        return f"{self.name} ({self.get_service_type_display()})"

    @classmethod
    def get_active_config(cls):
        """Get the active email configuration"""
        return cls.objects.filter(is_active=True).first()

    def save(self, *args, **kwargs):
        # If this config is being set as active, deactivate all others
        if self.is_active:
            SystemEmailConfig.objects.exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)
