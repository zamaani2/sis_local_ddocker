from django.apps import AppConfig


class SuperAdminConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "super_admin"
    verbose_name = "Super Admin Platform"

    def ready(self):
        """
        Import signals when the app is ready.
        """
        import super_admin.signals
