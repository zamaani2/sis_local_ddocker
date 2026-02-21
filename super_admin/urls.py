from django.urls import path
from . import views

app_name = "super_admin"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("schools/", views.school_list, name="school_list"),
    path("schools/create/", views.school_create, name="school_create"),
    path("schools/<int:pk>/", views.school_detail, name="school_detail"),
    path("schools/<int:pk>/edit/", views.school_update, name="school_update"),
    path("schools/<int:pk>/delete/", views.school_delete, name="school_delete"),
    path(
        "schools/<int:pk>/impersonate/",
        views.impersonate_admin,
        name="impersonate_admin",
    ),
    path("stop-impersonating/", views.stop_impersonating, name="stop_impersonating"),
    # School administrator management
    path(
        "schools/<int:school_id>/administrators/create/",
        views.school_admin_create,
        name="school_admin_create",
    ),
    path(
        "administrators/<int:pk>/edit/",
        views.school_admin_update,
        name="school_admin_update",
    ),
    path(
        "administrators/<int:pk>/delete/",
        views.school_admin_delete,
        name="school_admin_delete",
    ),
    path(
        "administrators/<int:pk>/reset-password/",
        views.school_admin_reset_password,
        name="school_admin_reset_password",
    ),
    # Subscription management
    path("plans/", views.plan_list, name="plan_list"),
    path("plans/create/", views.plan_create, name="plan_create"),
    path("plans/<int:pk>/", views.plan_detail, name="plan_detail"),
    path("plans/<int:pk>/edit/", views.plan_update, name="plan_update"),
    path("plans/<int:pk>/delete/", views.plan_delete, name="plan_delete"),
    path("plans/<int:pk>/duplicate/", views.plan_duplicate, name="plan_duplicate"),
    path(
        "plans/<int:pk>/toggle-feature/",
        views.plan_toggle_feature,
        name="plan_toggle_feature",
    ),
    path("subscriptions/", views.subscription_list, name="subscription_list"),
    path(
        "subscriptions/create/", views.subscription_create, name="subscription_create"
    ),
    path(
        "subscriptions/<int:pk>/", views.subscription_detail, name="subscription_detail"
    ),
    path(
        "subscriptions/<int:pk>/edit/",
        views.subscription_update,
        name="subscription_update",
    ),
    path(
        "subscriptions/<int:pk>/cancel/",
        views.subscription_cancel,
        name="subscription_cancel",
    ),
    path(
        "subscriptions/<int:pk>/renew/",
        views.subscription_renew,
        name="subscription_renew",
    ),
    path(
        "subscriptions/<int:pk>/convert/",
        views.subscription_convert,
        name="subscription_convert",
    ),
    # Domain management
    path("domains/", views.domain_list, name="domain_list"),
    path("domains/create/", views.domain_create, name="domain_create"),
    path("domains/<int:pk>/edit/", views.domain_update, name="domain_update"),
    path("domains/<int:pk>/delete/", views.domain_delete, name="domain_delete"),
    path("domains/<int:pk>/verify/", views.domain_verify, name="domain_verify"),
    # Payment transactions
    path("transactions/", views.transaction_list, name="transaction_list"),
    path("transactions/<int:pk>/", views.transaction_detail, name="transaction_detail"),
    # Platform settings
    path("settings/", views.settings_update, name="settings_update"),
    # Email configuration
    path("settings/email/", views.email_config_list, name="email_config_list"),
    path(
        "settings/email/create/", views.email_config_create, name="email_config_create"
    ),
    path(
        "settings/email/<int:pk>/edit/",
        views.email_config_edit,
        name="email_config_edit",
    ),
    path(
        "settings/email/<int:pk>/delete/",
        views.email_config_delete,
        name="email_config_delete",
    ),
    path(
        "settings/email/<int:pk>/activate/",
        views.email_config_activate,
        name="email_config_activate",
    ),
    path(
        "settings/email/<int:pk>/test/",
        views.email_config_test,
        name="email_config_test",
    ),
    path(
        "settings/email/migrate/",
        views.email_config_migrate,
        name="email_config_migrate",
    ),
    # User management
    path("users/", views.user_list, name="user_list"),
    path("users/create/", views.user_create, name="user_create"),
    path("users/<int:pk>/", views.user_detail, name="user_detail"),
    path("users/<int:pk>/edit/", views.user_update, name="user_update"),
    path("users/<int:pk>/delete/", views.user_delete, name="user_delete"),
    path(
        "users/<int:pk>/reset-password/",
        views.user_reset_password,
        name="user_reset_password",
    ),

    # Backup and Restore management
    path("backup-restore/", views.backup_restore_dashboard, name="backup_restore_dashboard"),
    path("backup-restore/restore-existing/", views.restore_to_existing_school, name="restore_to_existing_school"),
    path("backup-restore/restore-new/", views.restore_to_new_school, name="restore_to_new_school"),
    path("backup-restore/restore/<int:restore_id>/status/", views.restore_status, name="restore_status"),
    path("backup-restore/validate/", views.validate_backup_file, name="validate_backup_file"),
    path("backup-restore/schools/<int:school_id>/backups/", views.school_backups, name="school_backups"),
    path("backup-restore/schools/<int:school_id>/restores/", views.school_restores, name="school_restores"),
    path("backup-restore/all-backups/", views.all_backups, name="all_backups"),
    path("backup-restore/all-restores/", views.all_restores, name="all_restores"),
    path("backup-restore/backup/<int:backup_id>/download/", views.download_backup, name="download_backup"),
    path("backup-restore/backup/<int:backup_id>/delete/", views.delete_backup, name="delete_backup"),

]
