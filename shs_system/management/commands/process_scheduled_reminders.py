import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from shs_system.models import ScheduledReminder
from shs_system.views.teacher_monitoring_activities import send_bulk_activity_reminder

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Process scheduled reminders that are due to be sent"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate processing without actually sending emails",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        now = timezone.now()

        # Get all unexecuted reminders that are scheduled for now or earlier
        due_reminders = ScheduledReminder.objects.filter(
            executed=False, scheduled_time__lte=now
        )

        if not due_reminders.exists():
            self.stdout.write(self.style.SUCCESS("No scheduled reminders to process."))
            return

        self.stdout.write(f"Found {due_reminders.count()} reminders to process.")

        for reminder in due_reminders:
            try:
                self.stdout.write(
                    f"Processing reminder ID: {reminder.id}, Type: {reminder.reminder_type}"
                )

                if not dry_run:
                    # Process based on reminder type
                    if reminder.reminder_type == "activity":
                        parameters = reminder.parameters

                        # Extract parameters
                        teacher_ids = parameters.get("teacher_ids", [])
                        activity_type = parameters.get("activity_type")
                        class_id = parameters.get("class_id")
                        subject_id = parameters.get("subject_id")
                        term_id = parameters.get("term_id")
                        message = parameters.get("message", "")

                        # Call the appropriate function based on parameters
                        if teacher_ids and activity_type:
                            results = send_bulk_activity_reminder(
                                teacher_ids=teacher_ids,
                                activity_type=activity_type,
                                class_id=class_id,
                                subject_id=subject_id,
                                term_id=term_id,
                                message=message,
                                sender=reminder.creator,
                                scheduled_reminder=reminder,
                            )

                            self.stdout.write(
                                f"Results: Success: {results['success_count']}, Failed: {results['failure_count']}, Skipped: {results['skipped_count']}"
                            )
                            if results["messages"]:
                                for msg in results["messages"]:
                                    self.stdout.write(f"  - {msg}")
                        else:
                            logger.error(
                                f"Invalid parameters for activity reminder: {parameters}"
                            )
                            self.stdout.write(
                                self.style.ERROR(
                                    f"Invalid parameters for activity reminder: {parameters}"
                                )
                            )

                    # Mark as executed
                    reminder.executed = True
                    reminder.executed_at = timezone.now()
                    reminder.save()

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Successfully processed reminder ID: {reminder.id}"
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"DRY RUN: Would process reminder ID: {reminder.id}"
                        )
                    )

            except Exception as e:
                logger.error(f"Error processing reminder ID {reminder.id}: {str(e)}")
                self.stdout.write(
                    self.style.ERROR(
                        f"Error processing reminder ID {reminder.id}: {str(e)}"
                    )
                )

        processed_count = due_reminders.count()
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully processed {processed_count} reminders."
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN: Would have processed {processed_count} reminders."
                )
            )
