# Scheduled Reminders for Teacher Activity Monitoring

This document provides instructions on how to set up and use the scheduled reminders feature for teacher activity monitoring.

## Overview

The scheduled reminders feature allows administrators to:

1. Send immediate reminders to teachers about pending activities
2. Schedule reminders to be sent at a later time
3. Send bulk reminders to multiple teachers based on criteria
4. Track reminder history and effectiveness

## Setting Up Scheduled Tasks

### Windows (Task Scheduler)

1. Open Task Scheduler (search for it in the Start menu)
2. Click "Create Basic Task"
3. Name it "SchoolApp - Process Scheduled Reminders"
4. Set the trigger (e.g., Daily at 8:00 AM)
5. Select "Start a program" as the action
6. Browse to PowerShell executable (`C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe`)
7. Add arguments: `-ExecutionPolicy Bypass -File "C:\Django\SchoolApp\scripts\process_scheduled_reminders.ps1"`
8. Complete the wizard and check "Open the Properties dialog" before finishing
9. In the Properties dialog, go to the "Settings" tab
10. Check "Run task as soon as possible after a scheduled start is missed"
11. Click OK to save

### Linux/Mac (Cron)

1. Open a terminal
2. Edit the crontab file:
   ```
   crontab -e
   ```
3. Add a line to run the script every hour:
   ```
   0 * * * * /path/to/SchoolApp/scripts/process_scheduled_reminders.sh
   ```
4. Save and exit

## Using the Scheduled Reminders Feature

### Sending Immediate Reminders

1. Navigate to "Teacher Activity Monitoring"
2. Find the teacher/class/subject combination you want to remind
3. Click the "Actions" dropdown and select "Send Reminder"
4. Choose the activity type (scores, remarks, report cards)
5. Click "Send Now"

### Scheduling Future Reminders

1. Follow steps 1-4 above
2. Instead of "Send Now", click "Schedule"
3. Select the date and time for the reminder
4. Click "Schedule Reminder"

### Sending Bulk Reminders

1. Navigate to "Teacher Activity Monitoring"
2. Apply filters to select the target group (e.g., specific department, completion status)
3. Click "Send Bulk Reminders"
4. Choose the activity type
5. Choose to send immediately or schedule for later
6. Click "Send" or "Schedule"

### Viewing Reminder History

1. Navigate to "Teacher Activity Monitoring"
2. Click "View Reminder Logs"
3. Use the filters to find specific reminders
4. Review the status and effectiveness of sent reminders

## Troubleshooting

### Reminders Not Being Processed

1. Check the logs in `C:\Django\SchoolApp\logs\reminders.log`
2. Verify the scheduled task/cron job is running correctly
3. Make sure the Django management command has proper permissions

### Email Delivery Issues

1. Check your email settings in the Django settings file
2. Verify SMTP server settings or OAuth credentials
3. Check if the email service is blocking automated emails

## Models and Database

The scheduled reminders feature uses two main models:

1. `ScheduledReminder`: Stores information about scheduled reminders
2. `ReminderLog`: Tracks the history of sent reminders

You can access these through the Django admin interface or through the reminder logs page.

## Command Line Usage

You can manually process scheduled reminders using the management command:

```
python manage.py process_scheduled_reminders
```

Add `--dry-run` to simulate processing without actually sending emails:

```
python manage.py process_scheduled_reminders --dry-run
``` 