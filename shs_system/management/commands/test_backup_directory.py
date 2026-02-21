"""
Management command to test backup directory configuration.
This command verifies that the backup directory is properly configured and accessible.
"""

import os
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Test backup directory configuration and accessibility'

    def add_arguments(self, parser):
        parser.add_argument(
            '--create-test-file',
            action='store_true',
            help='Create a test file in the backup directory',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Testing backup directory configuration...'))
        
        # Get backup directory from settings
        backup_dir = getattr(settings, 'BACKUP_DIR', r'C:\backups')
        self.stdout.write(f'Backup directory: {backup_dir}')
        
        # Check if directory exists
        if os.path.exists(backup_dir):
            self.stdout.write(self.style.SUCCESS(f'✓ Backup directory exists: {backup_dir}'))
        else:
            self.stdout.write(self.style.WARNING(f'⚠ Backup directory does not exist: {backup_dir}'))
            try:
                os.makedirs(backup_dir, exist_ok=True)
                self.stdout.write(self.style.SUCCESS(f'✓ Created backup directory: {backup_dir}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ Failed to create backup directory: {e}'))
                return
        
        # Check if directory is writable
        try:
            test_file = os.path.join(backup_dir, 'test_write_permission.txt')
            with open(test_file, 'w') as f:
                f.write('Test write permission')
            os.remove(test_file)
            self.stdout.write(self.style.SUCCESS('✓ Backup directory is writable'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Backup directory is not writable: {e}'))
            return
        
        # Create test file if requested
        if options['create_test_file']:
            try:
                test_file = os.path.join(backup_dir, 'backup_test.txt')
                with open(test_file, 'w') as f:
                    f.write('This is a test file to verify backup directory functionality.\n')
                    f.write(f'Created at: {os.path.getctime(test_file)}\n')
                    f.write(f'Directory: {backup_dir}\n')
                self.stdout.write(self.style.SUCCESS(f'✓ Created test file: {test_file}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ Failed to create test file: {e}'))
        
        # Check temp uploads directory
        temp_uploads_dir = os.path.join(backup_dir, 'temp_uploads')
        if os.path.exists(temp_uploads_dir):
            self.stdout.write(self.style.SUCCESS(f'✓ Temp uploads directory exists: {temp_uploads_dir}'))
        else:
            try:
                os.makedirs(temp_uploads_dir, exist_ok=True)
                self.stdout.write(self.style.SUCCESS(f'✓ Created temp uploads directory: {temp_uploads_dir}'))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'⚠ Failed to create temp uploads directory: {e}'))
        
        self.stdout.write(self.style.SUCCESS('\nBackup directory configuration test completed!'))
        self.stdout.write(f'Backup files will be saved to: {backup_dir}')
        self.stdout.write(f'Uploaded restore files will be saved to: {temp_uploads_dir}')



