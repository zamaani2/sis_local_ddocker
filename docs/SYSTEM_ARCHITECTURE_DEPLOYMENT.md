# SchoolApp System Architecture & Deployment Guide

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Components](#architecture-components)
3. [Database Schema](#database-schema)
4. [API Endpoints](#api-endpoints)
5. [Deployment Configuration](#deployment-configuration)
6. [Performance Tuning](#performance-tuning)
7. [Security Configuration](#security-configuration)
8. [Monitoring Setup](#monitoring-setup)
9. [Troubleshooting Guide](#troubleshooting-guide)
10. [Maintenance Procedures](#maintenance-procedures)

---

## System Overview

### Technology Stack

```
Frontend:
├── HTML5, CSS3, JavaScript
├── Bootstrap 5.3.3
├── DataTables 1.13.7 (Server-side processing)
├── Chart.js 4.4.0
├── SweetAlert2 11.7.32
└── FontAwesome 6.5.1

Backend:
├── Django 5.0.3
├── Python 3.11
├── PostgreSQL 15
├── Gunicorn (WSGI Server)
└── Nginx (Reverse Proxy)

Infrastructure:
├── Docker & Docker Compose
├── Redis (Caching - Recommended)
├── Celery (Background Tasks - Recommended)
└── Prometheus (Monitoring - Recommended)
```

### System Capabilities

- **Multi-tenant Architecture**: School-based data isolation
- **User Management**: Role-based access control (Admin, Teacher, Student, Super Admin)
- **Student Management**: CRUD operations, bulk imports, class assignments
- **Assessment System**: Score entry, calculation, position ranking
- **Report Generation**: Individual and bulk report cards
- **Promotion Management**: Student promotion and graduation
- **Backup/Restore**: School-specific data backup and restoration

---

## Architecture Components

### Core Models

#### User Management

```python
class User(AbstractUser):
    ROLES = (
        ("admin", "Administrator"),
        ("teacher", "Teacher"),
        ("student", "Student"),
        ("superadmin", "Super Administrator"),
    )
    role = models.CharField(max_length=20, choices=ROLES)
    school = models.ForeignKey("SchoolInformation", on_delete=models.CASCADE)
    teacher_profile = models.OneToOneField("Teacher", on_delete=models.SET_NULL, null=True)
    student_profile = models.OneToOneField("Student", on_delete=models.SET_NULL, null=True)
```

#### Student Management

```python
class Student(models.Model):
    admission_number = models.CharField(max_length=10, unique=True)
    full_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    parent_contact = models.CharField(max_length=15)
    admission_date = models.DateField()
    form = models.ForeignKey(Form, on_delete=models.SET_NULL)
    learning_area = models.ForeignKey(LearningArea, on_delete=models.SET_NULL)
    school = models.ForeignKey("SchoolInformation", on_delete=models.CASCADE)
```

#### Assessment System

```python
class Assessment(models.Model):
    ASSESSMENT_TYPES = (
        ("class_score", "FIRST SEMESTER"),
        ("exam_score", "SECOND SEMESTER"),
    )
    class_subject = models.ForeignKey("ClassSubject", on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    assessment_type = models.CharField(max_length=20, choices=ASSESSMENT_TYPES)

    # Individual score components
    individual_score = models.DecimalField(max_digits=5, decimal_places=2)
    class_test_score = models.DecimalField(max_digits=5, decimal_places=2)
    project_score = models.DecimalField(max_digits=5, decimal_places=2)
    group_work_score = models.DecimalField(max_digits=5, decimal_places=2)

    # Calculated scores
    class_score = models.DecimalField(max_digits=5, decimal_places=2)
    exam_score = models.DecimalField(max_digits=5, decimal_places=2)
    total_score = models.DecimalField(max_digits=5, decimal_places=2)
    position = models.PositiveIntegerField()
```

### Multi-Tenant Architecture

#### School Isolation

```python
class SchoolInformation(models.Model):
    name = models.CharField(max_length=200)
    address = models.TextField()
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    website = models.URLField(blank=True)
    logo = models.ImageField(upload_to="school_logos/")
    is_active = models.BooleanField(default=True)

    # Multi-tenancy settings
    subdomain = models.CharField(max_length=100, unique=True)
    custom_domain = models.CharField(max_length=200, blank=True)
```

#### Data Segregation

All models include school foreign key for data isolation:

```python
school = models.ForeignKey(
    "SchoolInformation",
    on_delete=models.CASCADE,
    related_name="[model_name]s",
    null=True,
)
```

---

## Database Schema

### Key Relationships

#### Academic Structure

```
SchoolInformation
├── AcademicYear (1:N)
│   └── Term (1:N)
├── Form (1:N)
├── LearningArea (1:N)
├── Department (1:N)
└── Subject (1:N)
```

#### Student Management

```
Student (N:1) SchoolInformation
Student (N:1) Form
Student (N:1) LearningArea
Student (N:N) Class (through StudentClass)
```

#### Assessment System

```
Assessment (N:1) Student
Assessment (N:1) ClassSubject
Assessment (N:1) Term
Assessment (N:1) User (recorded_by)
```

### Database Indexes

#### Performance-Critical Indexes

```python
# Student model indexes
class Student(models.Model):
    class Meta:
        indexes = [
            models.Index(fields=["admission_number"]),
            models.Index(fields=["learning_area"]),
            models.Index(fields=["form"]),
            models.Index(fields=["school"]),
        ]

# Assessment model indexes
class Assessment(models.Model):
    class Meta:
        indexes = [
            models.Index(fields=["student", "term", "class_subject"]),
            models.Index(fields=["class_subject", "term", "total_score"]),
            models.Index(fields=["school", "term", "assessment_type"]),
        ]
```

### Database Configuration

#### Production Settings

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "multi_sis_database"),
        "USER": os.environ.get("DB_USER", "postgres"),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "5432"),
        "OPTIONS": {
            "connect_timeout": 60,
            "MAX_CONNS": 20,
            "MIN_CONNS": 5,
        },
        "CONN_MAX_AGE": 600,  # 10 minutes
        "CONN_HEALTH_CHECKS": True,
        "ATOMIC_REQUESTS": False,
    }
}
```

---

## API Endpoints

### Authentication Endpoints

```
POST /login/                    # User login
POST /logout/                   # User logout
GET  /dashboard/                # Dashboard redirect
POST /password-reset/           # Password reset
```

### Student Management

```
GET  /students/                 # Student list (paginated)
POST /students/                 # Create student
GET  /students/{id}/            # Student detail
PUT  /students/{id}/            # Update student
DELETE /students/{id}/           # Delete student
POST /students/bulk-import/     # Bulk import students
POST /students/bulk-delete/     # Bulk delete students
POST /students/bulk-assign/     # Bulk assign to class
```

### Assessment System

```
GET  /scores/                   # Score entry interface
POST /scores/submit/            # Submit scores
GET  /scores/class/{id}/        # Class scores
GET  /scores/student/{id}/      # Student scores
POST /scores/bulk-update/       # Bulk score update
```

### Report Generation

```
GET  /reports/generate/         # Generate report card
POST /reports/bulk-generate/    # Bulk report generation
GET  /reports/list/             # Report list
GET  /reports/{id}/pdf/         # PDF download
```

### AJAX Endpoints

```
GET  /ajax/students/            # Student list (DataTables)
GET  /ajax/class-form-data/     # Class form data (cached)
GET  /ajax/backup-status/{id}/  # Backup status
GET  /ajax/restore-status/{id}/ # Restore status
```

---

## Deployment Configuration

### Docker Configuration

#### Dockerfile

```dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=SchoolApp.settings

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev pkg-config curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create non-root user
RUN adduser --disabled-password --gecos '' django
RUN mkdir -p /app/staticfiles /app/media /app/logs \
    && chown -R django:django /app

USER django

# Collect static files
RUN python manage.py collectstatic --noinput

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Run application
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "8", "--worker-class", "gevent", "--worker-connections", "1000", "--timeout", "120", "SchoolApp.wsgi:application"]
```

#### Docker Compose

```yaml
version: "3.8"

services:
  # PostgreSQL Database
  db:
    image: postgres:15
    container_name: schoolapp_postgres
    restart: always
    environment:
      POSTGRES_DB: ${DB_NAME}
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    networks:
      - schoolapp_network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER} -d ${DB_NAME}"]
      timeout: 20s
      retries: 10

  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: schoolapp_redis
    restart: always
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - schoolapp_network

  # Django Application
  django:
    build: .
    container_name: schoolapp_django
    restart: always
    environment:
      - DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY}
      - DJANGO_DEBUG=${DJANGO_DEBUG}
      - ALLOWED_HOSTS=${ALLOWED_HOSTS}
      - DB_NAME=${DB_NAME}
      - DB_USER=${DB_USER}
      - DB_PASSWORD=${DB_PASSWORD}
      - DB_HOST=db
      - DB_PORT=5432
      - REDIS_URL=redis://redis:6379/1
    volumes:
      - media_files:/app/media
      - static_files:/app/staticfiles
      - logs:/app/logs
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    networks:
      - schoolapp_network

  # Nginx Web Server
  nginx:
    image: nginx:alpine
    container_name: schoolapp_nginx
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - static_files:/app/staticfiles:ro
      - media_files:/app/media:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - django
    networks:
      - schoolapp_network

volumes:
  postgres_data:
  redis_data:
  media_files:
  static_files:
  logs:

networks:
  schoolapp_network:
    driver: bridge
```

### Nginx Configuration

#### nginx.conf

```nginx
upstream django {
    server django:8000;
}

server {
    listen 80;
    server_name _;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name _;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Static files
    location /static/ {
        alias /app/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Media files
    location /media/ {
        alias /app/media/;
        expires 1M;
        add_header Cache-Control "public";
    }

    # Main application
    location / {
        proxy_pass http://django;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Health check
    location /health/ {
        proxy_pass http://django;
        access_log off;
    }
}
```

---

## Performance Tuning

### Gunicorn Configuration

#### Production Settings

```python
# gunicorn.conf.py
bind = "0.0.0.0:8000"
workers = 8
worker_class = "gevent"
worker_connections = 1000
timeout = 120
keepalive = 2
max_requests = 1000
max_requests_jitter = 100
preload_app = True
```

### Database Optimization

#### Connection Pooling

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'OPTIONS': {
            'MAX_CONNS': 20,
            'MIN_CONNS': 5,
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
        'CONN_MAX_AGE': 600,
    }
}
```

#### Query Optimization

```python
# Use select_related for foreign keys
students = Student.objects.select_related('form', 'learning_area', 'school')

# Use prefetch_related for many-to-many
students = Student.objects.prefetch_related('studentclass_set__assigned_class')

# Use only() to limit fields
students = Student.objects.only('id', 'full_name', 'admission_number')
```

### Caching Strategy

#### Redis Configuration

```python
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://redis:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            }
        }
    }
}

# Session configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
SESSION_COOKIE_AGE = 3600  # 1 hour
SESSION_SAVE_EVERY_REQUEST = False
```

#### Cache Usage Examples

```python
from django.core.cache import cache

# Cache expensive queries
def get_student_statistics(school_id):
    cache_key = f'student_stats_{school_id}'
    stats = cache.get(cache_key)

    if stats is None:
        stats = calculate_student_statistics(school_id)
        cache.set(cache_key, stats, 300)  # 5 minutes

    return stats

# Cache form data
def get_class_form_data(school_id):
    cache_key = f'class_form_data_{school_id}'
    data = cache.get(cache_key)

    if data is None:
        data = build_class_form_data(school_id)
        cache.set(cache_key, data, 300)  # 5 minutes

    return data
```

---

## Security Configuration

### Authentication & Authorization

#### User Roles & Permissions

```python
# Custom permission decorators
def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if request.user.role not in ['admin', 'superadmin']:
            return HttpResponseForbidden()
        return view_func(request, *args, **kwargs)
    return wrapper

def teacher_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if request.user.role not in ['teacher', 'admin', 'superadmin']:
            return HttpResponseForbidden()
        return view_func(request, *args, **kwargs)
    return wrapper
```

#### Rate Limiting

```python
from django_ratelimit.decorators import ratelimit

@ratelimit(key='user', rate='100/h', method='POST')
def bulk_import_students(request):
    # Rate limit bulk operations
    pass

@ratelimit(key='ip', rate='1000/h', method='GET')
def student_list(request):
    # Rate limit list views
    pass
```

### Security Headers

#### Django Security Settings

```python
# Security middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'axes.middleware.AxesMiddleware',
    'csp.middleware.CSPMiddleware',
]

# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# CSRF settings
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Strict'

# Session security
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Strict'
```

#### Content Security Policy

```python
CSP_DEFAULT_SRC = ("'self'",)
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'", "https:")
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'", "https:")
CSP_IMG_SRC = ("'self'", "data:", "https:")
CSP_FONT_SRC = ("'self'", "https:")
CSP_CONNECT_SRC = ("'self'", "https:")
```

### Data Protection

#### File Upload Security

```python
# File upload settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 52428800  # 50MB
FILE_UPLOAD_PERMISSIONS = 0o644
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o755

# Allowed file types
ALLOWED_FILE_TYPES = ['.jpg', '.jpeg', '.png', '.pdf', '.csv']
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def validate_file_upload(file):
    if file.size > MAX_FILE_SIZE:
        raise ValidationError("File too large")

    ext = os.path.splitext(file.name)[1].lower()
    if ext not in ALLOWED_FILE_TYPES:
        raise ValidationError("File type not allowed")
```

---

## Monitoring Setup

### Application Monitoring

#### Prometheus Configuration

```python
# settings.py
INSTALLED_APPS = [
    'django_prometheus',
    # ... other apps
]

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    # ... other middleware
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]
```

#### Custom Metrics

```python
from django.core.cache import cache
from django.db import connection
import time

def track_request_metrics(view_func):
    def wrapper(request, *args, **kwargs):
        start_time = time.time()

        response = view_func(request, *args, **kwargs)

        duration = time.time() - start_time

        # Track metrics
        cache.set(f'request_duration_{request.path}', duration, 300)
        cache.set(f'active_users', cache.get('active_users', 0) + 1, 60)

        return response
    return wrapper
```

### Database Monitoring

#### Query Logging

```python
LOGGING = {
    'version': 1,
    'handlers': {
        'db_log': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'logs/db_queries.log',
        },
        'performance_log': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/performance.log',
        },
    },
    'loggers': {
        'django.db.backends': {
            'level': 'DEBUG',
            'handlers': ['db_log'],
        },
        'performance': {
            'level': 'INFO',
            'handlers': ['performance_log'],
        },
    },
}
```

### Health Checks

#### Application Health Check

```python
# views/health.py
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache

def health_check(request):
    health_status = {
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'checks': {}
    }

    # Database check
    try:
        connection.ensure_connection()
        health_status['checks']['database'] = 'healthy'
    except Exception as e:
        health_status['checks']['database'] = f'unhealthy: {str(e)}'
        health_status['status'] = 'unhealthy'

    # Cache check
    try:
        cache.set('health_check', 'ok', 10)
        cache.get('health_check')
        health_status['checks']['cache'] = 'healthy'
    except Exception as e:
        health_status['checks']['cache'] = f'unhealthy: {str(e)}'
        health_status['status'] = 'unhealthy'

    return JsonResponse(health_status)
```

---

## Troubleshooting Guide

### Common Issues

#### 1. Database Connection Issues

```bash
# Check database connectivity
docker exec -it schoolapp_postgres psql -U postgres -d multi_sis_database

# Check connection pool
docker exec -it schoolapp_django python manage.py dbshell

# Reset database connections
docker restart schoolapp_django
```

#### 2. Memory Issues

```bash
# Check memory usage
docker stats schoolapp_django

# Check for memory leaks
docker exec -it schoolapp_django python -c "
import psutil
print(f'Memory usage: {psutil.virtual_memory().percent}%')
print(f'Available memory: {psutil.virtual_memory().available / 1024**3:.2f} GB')
"
```

#### 3. Performance Issues

```bash
# Check slow queries
docker exec -it schoolapp_postgres psql -U postgres -d multi_sis_database -c "
SELECT query, mean_time, calls
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
"

# Check active connections
docker exec -it schoolapp_postgres psql -U postgres -d multi_sis_database -c "
SELECT count(*) as active_connections
FROM pg_stat_activity
WHERE state = 'active';
"
```

#### 4. Cache Issues

```bash
# Check Redis connectivity
docker exec -it schoolapp_redis redis-cli ping

# Check cache keys
docker exec -it schoolapp_redis redis-cli keys "*"

# Clear cache
docker exec -it schoolapp_redis redis-cli flushall
```

### Performance Debugging

#### Enable Debug Toolbar

```python
# settings_debug.py
if DEBUG:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']

    INTERNAL_IPS = ['127.0.0.1', 'localhost']

    DEBUG_TOOLBAR_CONFIG = {
        'SHOW_TEMPLATE_CONTEXT': True,
        'SHOW_COLLAPSED': True,
    }
```

#### Query Analysis

```python
# Add to views for debugging
from django.db import connection

def debug_queries(view_func):
    def wrapper(request, *args, **kwargs):
        initial_queries = len(connection.queries)

        response = view_func(request, *args, **kwargs)

        final_queries = len(connection.queries)
        query_count = final_queries - initial_queries

        if query_count > 10:  # Log slow queries
            logger.warning(f"View {view_func.__name__} executed {query_count} queries")

        return response
    return wrapper
```

---

## Maintenance Procedures

### Regular Maintenance Tasks

#### Daily Tasks

```bash
#!/bin/bash
# daily_maintenance.sh

# Check system health
docker exec schoolapp_django python manage.py health_check

# Backup database
docker exec schoolapp_postgres pg_dump -U postgres multi_sis_database > backup_$(date +%Y%m%d).sql

# Clean up old logs
find logs/ -name "*.log" -mtime +7 -delete

# Check disk space
df -h
```

#### Weekly Tasks

```bash
#!/bin/bash
# weekly_maintenance.sh

# Update statistics
docker exec schoolapp_postgres psql -U postgres -d multi_sis_database -c "ANALYZE;"

# Clean up old backups
find backups/ -name "*.sql" -mtime +30 -delete

# Check for security updates
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.CreatedAt}}"
```

#### Monthly Tasks

```bash
#!/bin/bash
# monthly_maintenance.sh

# Full system backup
docker-compose down
tar -czf full_backup_$(date +%Y%m%d).tar.gz .
docker-compose up -d

# Performance analysis
docker exec schoolapp_django python manage.py analyze_performance

# Security audit
docker exec schoolapp_django python manage.py security_audit
```

### Database Maintenance

#### Index Maintenance

```sql
-- Reindex all tables
REINDEX DATABASE multi_sis_database;

-- Update table statistics
ANALYZE;

-- Check for unused indexes
SELECT schemaname, tablename, indexname, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE idx_tup_read = 0 AND idx_tup_fetch = 0;
```

#### Data Archiving

```python
# management/commands/archive_old_data.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

class Command(BaseCommand):
    help = 'Archive old data'

    def handle(self, *args, **options):
        # Archive old academic years
        cutoff_date = timezone.now() - timedelta(years=3)

        old_years = AcademicYear.objects.filter(
            created_at__lt=cutoff_date,
            is_archived=False
        )

        for year in old_years:
            year.is_archived = True
            year.save()

        self.stdout.write(f'Archived {old_years.count()} academic years')
```

### Backup & Recovery

#### Automated Backup Script

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="multi_sis_database"

# Create backup directory
mkdir -p $BACKUP_DIR

# Database backup
docker exec schoolapp_postgres pg_dump -U postgres $DB_NAME > $BACKUP_DIR/db_$DATE.sql

# Media files backup
tar -czf $BACKUP_DIR/media_$DATE.tar.gz media/

# Compress database backup
gzip $BACKUP_DIR/db_$DATE.sql

# Clean up old backups (keep 30 days)
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
```

#### Recovery Procedure

```bash
#!/bin/bash
# restore.sh

BACKUP_FILE=$1
BACKUP_DIR="/backups"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file>"
    exit 1
fi

# Stop application
docker-compose down

# Restore database
gunzip -c $BACKUP_DIR/$BACKUP_FILE | docker exec -i schoolapp_postgres psql -U postgres -d multi_sis_database

# Restore media files
tar -xzf $BACKUP_DIR/media_${BACKUP_FILE%.sql.gz}.tar.gz

# Start application
docker-compose up -d

echo "Recovery completed"
```

---

## Conclusion

This comprehensive documentation provides everything needed to understand, deploy, maintain, and scale the SchoolApp system. The architecture supports multi-tenant operations with proper data isolation, comprehensive user management, and scalable performance optimizations.

### Key Features Documented

- ✅ Complete system architecture overview
- ✅ Database schema and relationships
- ✅ API endpoints and usage
- ✅ Docker deployment configuration
- ✅ Performance tuning guidelines
- ✅ Security configuration
- ✅ Monitoring and health checks
- ✅ Troubleshooting procedures
- ✅ Maintenance and backup procedures

### Next Steps

1. Implement the recommended performance optimizations
2. Set up monitoring and alerting
3. Create automated backup procedures
4. Conduct load testing
5. Plan for horizontal scaling

This documentation serves as the definitive guide for system administrators, developers, and operations teams working with the SchoolApp system.

---

_Document Version: 1.0_  
_Last Updated: [Current Date]_  
_Next Review: [Date + 6 months]_
