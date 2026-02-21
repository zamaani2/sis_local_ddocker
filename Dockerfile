# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=SchoolApp.settings

# Set work directory
WORKDIR /app

# Install system dependencies (Debian trixie)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        pkg-config \
        curl \
        libxml2 \
        libxslt1.1 \
        libffi8 \
        libjpeg62-turbo \
        libpng16-16 \
        libfreetype6 \
        liblcms2-2 \
        libwebp7 \
        libharfbuzz0b \
        libfribidi0 \
        libxcb1 \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libcairo2 \
        fonts-dejavu-core \
        fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Install Python build deps temporarily for wheels, then remove
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Copy startup script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Create non-root user for security
RUN adduser --disabled-password --gecos '' django

# Create necessary directories and set permissions
RUN mkdir -p /app/staticfiles /app/media /app/logs \
    && chown -R django:django /app

# Switch to non-root user
USER django

# Collect static files (allow failure for build-time, will collect at runtime)
# Set minimal environment to avoid database dependencies during build
# Note: Using base settings for build, but runtime will use settings_railway
RUN DJANGO_SETTINGS_MODULE=SchoolApp.settings \
    python manage.py collectstatic --noinput --verbosity 1 || \
    echo "Warning: collectstatic failed during build, will collect at runtime"

# Expose port (Railway will set PORT env var, default to 8000)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Use startup script which handles PORT correctly
ENTRYPOINT ["/app/start.sh"]
