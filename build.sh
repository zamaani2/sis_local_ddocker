#!/usr/bin/env bash
# exit on error
set -o errexit


pip install -r requirements.txt

python manage.py collectstatic --no-input --settings=SchoolApp.settings_production

python manage.py migrate --settings=SchoolApp.settings_production

# Create initial superuser if it doesn't exist
python create_initial_superuser.py

