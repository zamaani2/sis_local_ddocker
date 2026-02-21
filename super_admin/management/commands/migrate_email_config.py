from django.core.management.base import BaseCommand
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Migrates OAuth credentials from the old OAuthCredentialStore to the new SystemEmailConfig"

    def handle(self, *args, **options):
        try:
            # Import models
            from shs_system.models import OAuthCredentialStore
            from super_admin.models import SystemEmailConfig

            # Check if there are any old credentials
            old_creds = OAuthCredentialStore.objects.filter(
                service_name="gmail"
            ).first()
            if not old_creds:
                self.stdout.write(
                    self.style.WARNING("No legacy OAuth credentials found to migrate.")
                )
                return

            # Create new config from old credentials
            new_config = SystemEmailConfig(
                name=f"Migrated Gmail ({old_creds.email})",
                service_type="oauth",
                oauth_provider="google",
                client_id=old_creds.client_id,
                client_secret=old_creds.client_secret,
                refresh_token=old_creds.refresh_token,
                access_token=old_creds.access_token,
                token_uri=old_creds.token_uri,
                scopes=old_creds.scopes,
                from_email=old_creds.email,
                is_active=True,
            )
            new_config.save()

            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully migrated OAuth credentials for {old_creds.email}."
                )
            )

            # Optionally, mark the old credentials as migrated or delete them
            # Uncomment the next line to delete the old credentials
            # old_creds.delete()
            # self.stdout.write(self.style.SUCCESS('Old credentials deleted.'))

        except ImportError as e:
            self.stdout.write(self.style.ERROR(f"Import error: {str(e)}"))
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error migrating credentials: {str(e)}")
            )
