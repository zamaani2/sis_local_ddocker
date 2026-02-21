#!/bin/bash

# Set the path to your Django project
PROJECT_PATH="/c/Django/SchoolApp"

# Activate the virtual environment if using one
# source /path/to/your/virtualenv/bin/activate

# Navigate to the project directory
cd $PROJECT_PATH

# Run the Django management command
python manage.py process_scheduled_reminders

# Log the execution
echo "$(date): Processed scheduled reminders" >> $PROJECT_PATH/logs/reminders.log

exit 0 