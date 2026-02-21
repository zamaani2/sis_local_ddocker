from django.contrib import admin
from .models import (
    Plan,
    Subscription,
    SchoolDomain,
    PaymentTransaction,
    SuperAdminSettings,
    SystemEmailConfig,
)


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "price",
        "billing_cycle",
        "max_students",
        "max_teachers",
        "is_active",
    )
    list_filter = ("billing_cycle", "is_active")
    search_fields = ("name", "description")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "school",
        "plan",
        "status",
        "start_date",
        "end_date",
        "days_remaining",
    )
    list_filter = ("status", "plan", "auto_renew")
    search_fields = ("school__name", "subscription_id")
    date_hierarchy = "start_date"


@admin.register(SchoolDomain)
class SchoolDomainAdmin(admin.ModelAdmin):
    list_display = ("domain", "school", "is_primary", "is_verified", "created_at")
    list_filter = ("is_primary", "is_verified")
    search_fields = ("domain", "school__name")
    date_hierarchy = "created_at"


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "invoice_number",
        "subscription",
        "amount",
        "currency",
        "status",
        "payment_date",
    )
    list_filter = ("status", "payment_date")
    search_fields = ("invoice_number", "transaction_id", "subscription__school__name")
    date_hierarchy = "payment_date"
    readonly_fields = ("invoice_number", "transaction_id", "payment_date", "created_at")


@admin.register(SuperAdminSettings)
class SuperAdminSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "site_name",
        "contact_email",
        "allow_new_registrations",
        "is_maintenance_mode",
    )
    fieldsets = (
        ("Basic Settings", {"fields": ("site_name", "contact_email", "support_phone")}),
        (
            "Registration Settings",
            {"fields": ("allow_new_registrations", "default_trial_days")},
        ),
        ("Financial Settings", {"fields": ("platform_fee_percentage",)}),
        (
            "Legal Documents",
            {
                "fields": ("terms_and_conditions", "privacy_policy"),
                "classes": ("collapse",),
            },
        ),
        (
            "Maintenance",
            {
                "fields": ("is_maintenance_mode", "maintenance_message"),
                "classes": ("collapse",),
            },
        ),
    )

    def has_add_permission(self, request):
        # Only allow one instance of SuperAdminSettings
        return SuperAdminSettings.objects.count() == 0


@admin.register(SystemEmailConfig)
class SystemEmailConfigAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "service_type",
        "from_email",
        "is_active",
        "last_updated",
    )
    list_filter = ("service_type", "is_active")
    search_fields = ("name", "from_email")
    readonly_fields = ("last_updated", "created_at", "last_used")

    fieldsets = (
        (None, {"fields": ("name", "service_type", "is_active")}),
        (
            "Email Settings",
            {
                "fields": ("from_email", "from_name", "reply_to"),
            },
        ),
        (
            "SMTP Configuration",
            {
                "fields": (
                    "smtp_host",
                    "smtp_port",
                    "smtp_username",
                    "smtp_password",
                    "smtp_use_tls",
                    "smtp_use_ssl",
                ),
                "classes": ("collapse",),
                "description": "Settings for SMTP server configuration",
            },
        ),
        (
            "OAuth2 Configuration",
            {
                "fields": (
                    "oauth_provider",
                    "client_id",
                    "client_secret",
                    "refresh_token",
                    "access_token",
                    "token_uri",
                    "scopes",
                ),
                "classes": ("collapse",),
                "description": "Settings for OAuth2 authentication (Google)",
            },
        ),
        (
            "Metadata",
            {
                "fields": ("last_updated", "created_at", "last_used"),
            },
        ),
    )

    def get_readonly_fields(self, request, obj=None):
        """Make certain fields readonly if object already exists"""
        if obj:  # Editing an existing object
            return self.readonly_fields
        return self.readonly_fields
