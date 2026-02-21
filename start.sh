#!/bin/bash
# Railway startup script
# This script ensures PORT is set correctly for Railway deployment

# Set default PORT if not provided by Railway
# Railway automatically sets PORT, but we provide a fallback
export PORT=${PORT:-8000}

echo "=========================================="
echo "Starting SchoolApp..."
echo "=========================================="
echo "PORT is set to: $PORT"
echo "DJANGO_SETTINGS_MODULE: ${DJANGO_SETTINGS_MODULE:-NOT SET}"
echo ""
echo "All DATABASE-related environment variables:"
env | grep -i database || echo "  (none found)"
echo ""
echo "Verifying DJANGO_SETTINGS_MODULE..."
if [ -z "$DJANGO_SETTINGS_MODULE" ]; then
    echo "❌ CRITICAL: DJANGO_SETTINGS_MODULE is NOT SET!"
    echo "❌ Setting it to SchoolApp.settings now..."
    export DJANGO_SETTINGS_MODULE=SchoolApp.settings
    echo "✅ Set to: $DJANGO_SETTINGS_MODULE"
elif [ "$DJANGO_SETTINGS_MODULE" != "SchoolApp.settings" ]; then
    echo "⚠️  WARNING: DJANGO_SETTINGS_MODULE is set to: $DJANGO_SETTINGS_MODULE"
    echo "⚠️  Should be: SchoolApp.settings"
    echo "⚠️  Overriding to correct value..."
    export DJANGO_SETTINGS_MODULE=SchoolApp.settings
    echo "✅ Now set to: $DJANGO_SETTINGS_MODULE"
else
    echo "✅ DJANGO_SETTINGS_MODULE is correctly set to: $DJANGO_SETTINGS_MODULE"
fi
echo ""

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "❌ WARNING: DATABASE_URL is not set!"
    echo "❌ Please ensure:"
    echo "   1. PostgreSQL service is added in Railway"
    echo "   2. Services are linked (check Railway dashboard)"
    echo "   3. DATABASE_URL appears in Variables tab"
    echo "❌ Migrations and superuser creation will be skipped."
else
    echo "✅ DATABASE_URL is configured"
    echo "   DATABASE_URL starts with: ${DATABASE_URL:0:30}..."
    # Wait a moment for database to be ready
    echo "Waiting for database connection..."
    sleep 2
    
    # Run database migrations
    echo "Running migrations..."
    python manage.py migrate --noinput || {
        echo "ERROR: Migrations failed!"
        echo "This might be due to:"
        echo "  1. Database service not ready yet"
        echo "  2. Database credentials incorrect"
        echo "  3. Database service not linked to this service"
        echo "Continuing anyway, but app may not work correctly..."
    }

    # Create initial superuser if none exists (non-interactive)
    echo "Checking for existing superuser..."
    python manage.py shell -c "
from django.contrib.auth import get_user_model
import os

User = get_user_model()
if not User.objects.filter(is_superuser=True).exists():
    username = os.environ.get('SUPERUSER_USERNAME') or os.environ.get('SUPERUSER_EMAIL') or 'admin'
    email = os.environ.get('SUPERUSER_EMAIL', 'admin@example.com')
    password = os.environ.get('SUPERUSER_PASSWORD', 'admin123')

    print(f'No superuser found. Creating initial superuser: {username} ({email})')
    User.objects.create_superuser(username=username, email=email, password=password)
    print('✅ Initial superuser created successfully.')
else:
    print('ℹ️ Superuser already exists. Skipping creation.')
" || {
        echo "WARNING: Automatic superuser creation failed (this is non-fatal)."
    }
fi

# IMPORTANT: Set DJANGO_SETTINGS_MODULE before collectstatic and Gunicorn
export DJANGO_SETTINGS_MODULE=SchoolApp.settings
echo "DJANGO_SETTINGS_MODULE set to: $DJANGO_SETTINGS_MODULE"

# Collect static files
echo "Collecting static files..."
echo "Checking if staticfiles directory exists..."
if [ ! -d "staticfiles" ]; then
    echo "Creating staticfiles directory..."
    mkdir -p staticfiles
fi

# Clean and collect static files to avoid duplicate warnings
# Use --clear to remove old files first (helps with duplicate path issues)
# Use --ignore to skip problematic files if needed
echo "Running collectstatic with --clear to ensure clean state..."
python manage.py collectstatic --noinput --clear --verbosity 2 --ignore "*.map" || {
    echo "ERROR: collectstatic failed!"
    echo "This might cause static files (CSS, JS, images) to not load."
    echo "Attempting to continue, but static files may not be available..."
}

# Verify that static files were collected
echo "Verifying collected static files..."
if [ -d "staticfiles" ]; then
    FILE_COUNT=$(find staticfiles -type f | wc -l)
    echo "✅ Found $FILE_COUNT static files in staticfiles directory"
    
    # Check for specific critical files (search for them instead of exact path)
    ADMINLTE_CSS=$(find staticfiles -name "adminlte.css" -type f | head -1)
    if [ -n "$ADMINLTE_CSS" ]; then
        echo "✅ adminlte.css found at: $ADMINLTE_CSS"
    else
        echo "❌ WARNING: adminlte.css NOT found!"
        echo "   Searching in staticfiles directory..."
        find staticfiles -name "*adminlte*" -type f | head -5
    fi
    
    SWEETALERT_CSS=$(find staticfiles -path "*/sweetalert2*/*.min.css" -type f | head -1)
    if [ -n "$SWEETALERT_CSS" ]; then
        echo "✅ sweetalert2.min.css found at: $SWEETALERT_CSS"
    else
        echo "❌ WARNING: sweetalert2.min.css NOT found!"
        echo "   Searching in staticfiles directory..."
        find staticfiles -name "*sweetalert*" -type f | head -5
    fi
    
    ADMINLTE_JS=$(find staticfiles -name "adminlte.js" -type f | head -1)
    if [ -n "$ADMINLTE_JS" ]; then
        echo "✅ adminlte.js found at: $ADMINLTE_JS"
    else
        echo "❌ WARNING: adminlte.js NOT found!"
        echo "   Searching in staticfiles directory..."
        find staticfiles -name "*adminlte*.js" -type f | head -5
    fi
    
    # List top-level directories to help debug
    echo "Top-level directories in staticfiles:"
    ls -la staticfiles/ | head -10
else
    echo "❌ ERROR: staticfiles directory does not exist after collectstatic!"
    exit 1
fi

echo "Static files collection completed."

# Start Gunicorn with the PORT from environment
echo "Starting Gunicorn on 0.0.0.0:$PORT..."
echo "Final DJANGO_SETTINGS_MODULE: $DJANGO_SETTINGS_MODULE"
exec gunicorn --bind 0.0.0.0:$PORT --workers 3 --timeout 120 SchoolApp.wsgi:application

