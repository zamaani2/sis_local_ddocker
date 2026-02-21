# SchoolApp Optimization Implementation Guide

## Table of Contents

1. [Quick Start Optimization](#quick-start-optimization)
2. [Database Optimization](#database-optimization)
3. [Caching Implementation](#caching-implementation)
4. [Background Tasks Setup](#background-tasks-setup)
5. [Load Balancing Configuration](#load-balancing-configuration)
6. [Monitoring Implementation](#monitoring-implementation)
7. [Performance Testing](#performance-testing)
8. [Deployment Checklist](#deployment-checklist)

---

## Quick Start Optimization

### Immediate Performance Gains (1-2 hours)

#### 1. Update Gunicorn Configuration

```dockerfile
# Update Dockerfile
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "8", "--worker-class", "gevent", "--worker-connections", "1000", "--timeout", "120", "SchoolApp.wsgi:application"]
```

#### 2. Optimize Session Settings

```python
# Update settings.py
SESSION_COOKIE_AGE = 3600  # 1 hour instead of 10 hours
SESSION_SAVE_EVERY_REQUEST = False  # Only save when session changes
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
```

#### 3. Add Database Indexes

```python
# Add to models.py
class Assessment(models.Model):
    class Meta:
        indexes = [
            models.Index(fields=['student', 'term', 'class_subject']),
            models.Index(fields=['class_subject', 'term', 'total_score']),
            models.Index(fields=['school', 'term', 'assessment_type']),
        ]

class Student(models.Model):
    class Meta:
        indexes = [
            models.Index(fields=['admission_number']),
            models.Index(fields=['learning_area']),
            models.Index(fields=['form']),
            models.Index(fields=['school']),
            models.Index(fields=['school', 'form']),
            models.Index(fields=['school', 'learning_area']),
        ]
```

#### 4. Implement Basic Caching

```python
# Add to settings.py
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
        'TIMEOUT': 300,  # 5 minutes
        'OPTIONS': {
            'MAX_ENTRIES': 1000,
        }
    }
}

# Update session engine
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
```

---

## Database Optimization

### Connection Pooling Setup

#### 1. Install Database Pooling

```bash
pip install django-db-pool
```

#### 2. Update Database Configuration

```python
# settings.py
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

### Query Optimization Implementation

#### 1. Optimize Student List View

```python
# views/student_management.py
@login_required
@user_passes_test(is_admin)
def student_list(request):
    school = request.user.school

    # Optimized queryset with proper joins
    students = (
        Student.objects.filter(school=school)
        .exclude(archivedstudent__isnull=False)
        .select_related("form", "learning_area", "school")
        .prefetch_related(
            "studentclass_set__assigned_class__form",
            "studentclass_set__assigned_class__learning_area",
        )
        .order_by("full_name")
    )

    # Apply filters efficiently
    search_query = request.GET.get("search", "")
    if search_query:
        students = students.filter(
            Q(full_name__icontains=search_query)
            | Q(admission_number__icontains=search_query)
        )

    # Pagination
    paginator = Paginator(students, 50)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    return render(request, "student/student_list.html", {"page_obj": page_obj})
```

#### 2. Optimize Assessment Queries

```python
# views/enhanced_scores.py
def get_class_assessments(class_subject, term):
    """Get assessments with optimized queries"""
    return Assessment.objects.filter(
        class_subject=class_subject,
        term=term
    ).select_related(
        'student',
        'student__form',
        'student__learning_area'
    ).prefetch_related(
        'student__studentclass_set__assigned_class'
    ).order_by('student__full_name')
```

#### 3. Implement Bulk Operations

```python
# utils/bulk_operations.py
from django.db import transaction
from django.db.models import F

def bulk_update_assessments(assessments_data):
    """Bulk update assessments with position calculation"""
    with transaction.atomic():
        # Update assessments
        Assessment.objects.bulk_update(
            assessments_data,
            ['individual_score', 'class_test_score', 'project_score', 'group_work_score', 'exam_score'],
            batch_size=100
        )

        # Recalculate positions
        for assessment in assessments_data:
            Assessment.calculate_positions(assessment.class_subject, assessment.term)

def bulk_create_students(students_data):
    """Bulk create students with proper validation"""
    with transaction.atomic():
        return Student.objects.bulk_create(
            students_data,
            batch_size=50,
            ignore_conflicts=False
        )
```

---

## Caching Implementation

### Redis Setup

#### 1. Install Redis Dependencies

```bash
pip install django-redis redis
```

#### 2. Update Docker Compose

```yaml
# docker-compose.yml
services:
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

volumes:
  redis_data:
```

#### 3. Configure Redis Cache

```python
# settings.py
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

### Cache Implementation Examples

#### 1. Cache Form Data

```python
# views/manage_class.py
from django.core.cache import cache

@login_required
def get_class_form_data(request):
    """API endpoint with caching"""
    school = get_user_school(request.user)
    cache_key = f"class_form_data_{school.id if school else 'no_school'}"

    # Try to get cached data first
    cached_data = cache.get(cache_key)
    if cached_data:
        return JsonResponse(cached_data)

    # Build data if not cached
    form_data = {
        'forms': [],
        'learning_areas': [],
        'academic_years': []
    }

    if school:
        forms = Form.objects.filter(school=school).only('id', 'name').order_by('name')
        learning_areas = LearningArea.objects.filter(school=school).only('id', 'name').order_by('name')
        academic_years = AcademicYear.objects.filter(school=school).only('id', 'name').order_by('-name')

        form_data['forms'] = [{'id': f.id, 'name': f.name} for f in forms]
        form_data['learning_areas'] = [{'id': la.id, 'name': la.name} for la in learning_areas]
        form_data['academic_years'] = [{'id': ay.id, 'name': ay.name} for ay in academic_years]

    # Cache for 5 minutes
    cache.set(cache_key, form_data, 300)

    return JsonResponse(form_data)
```

#### 2. Cache Student Statistics

```python
# utils/cache_utils.py
from django.core.cache import cache
from django.db.models import Count, Avg

def get_student_statistics(school_id):
    """Get cached student statistics"""
    cache_key = f'student_stats_{school_id}'
    stats = cache.get(cache_key)

    if stats is None:
        stats = {
            'total_students': Student.objects.filter(school_id=school_id).count(),
            'active_students': Student.objects.filter(
                school_id=school_id,
                studentclass__is_active=True
            ).distinct().count(),
            'by_form': list(Student.objects.filter(school_id=school_id).values(
                'form__name'
            ).annotate(count=Count('id'))),
            'by_gender': list(Student.objects.filter(school_id=school_id).values(
                'gender'
            ).annotate(count=Count('id'))),
        }

        # Cache for 10 minutes
        cache.set(cache_key, stats, 600)

    return stats

def invalidate_student_cache(school_id):
    """Invalidate student-related cache"""
    cache.delete(f'student_stats_{school_id}')
    cache.delete(f'class_form_data_{school_id}')
```

#### 3. Cache Report Card Calculations

```python
# models.py
class ReportCard(models.Model):
    # ... existing fields ...

    def calculate_totals(self):
        """Calculate totals with caching"""
        cache_key = f'report_totals_{self.student_id}_{self.term_id}'
        cached_totals = cache.get(cache_key)

        if cached_totals:
            self.total_score = cached_totals['total_score']
            self.average_marks = cached_totals['average_marks']
            return

        # Calculate if not cached
        assessments = Assessment.objects.filter(
            student=self.student,
            term=self.term,
            total_score__isnull=False,
        )

        total_points = sum(assessment.total_score or 0 for assessment in assessments)
        num_subjects = assessments.count()

        if num_subjects > 0:
            avg_score = total_points / num_subjects
            self.total_score = total_points
            self.average_marks = avg_score

            # Cache the results
            cache.set(cache_key, {
                'total_score': total_points,
                'average_marks': avg_score
            }, 1800)  # 30 minutes
```

---

## Background Tasks Setup

### Celery Implementation

#### 1. Install Celery

```bash
pip install celery redis
```

#### 2. Create Celery Configuration

```python
# SchoolApp/celery.py
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SchoolApp.settings')

app = Celery('SchoolApp')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Celery configuration
app.conf.update(
    broker_url='redis://redis:6379/0',
    result_backend='redis://redis:6379/0',
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)
```

#### 3. Update Settings

```python
# settings.py
CELERY_BROKER_URL = 'redis://redis:6379/0'
CELERY_RESULT_BACKEND = 'redis://redis:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
```

#### 4. Create Background Tasks

```python
# tasks/report_tasks.py
from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

@shared_task(bind=True)
def generate_report_cards_bulk(self, class_id, term_id, school_id, user_id):
    """Generate report cards for all students in background"""
    try:
        from shs_system.models import Class, Term, StudentClass, ReportCard, User

        class_obj = Class.objects.get(id=class_id, school_id=school_id)
        term = Term.objects.get(id=term_id, school_id=school_id)
        user = User.objects.get(id=user_id)

        # Get all students in the class
        student_classes = StudentClass.objects.filter(
            assigned_class=class_obj
        ).select_related('student')

        total_students = student_classes.count()
        processed = 0

        for student_class in student_classes:
            # Create or update report card
            report_card, created = ReportCard.objects.get_or_create(
                student=student_class.student,
                term=term,
                academic_year=term.academic_year,
                class_assigned=class_obj,
                school_id=school_id,
                defaults={'generated_by': user}
            )

            # Calculate totals
            report_card.calculate_totals()
            report_card.calculate_attendance()
            report_card.calculate_position()
            report_card.save()

            processed += 1

            # Update progress
            self.update_state(
                state='PROGRESS',
                meta={'processed': processed, 'total': total_students}
            )

        return {'processed': processed, 'total': total_students}

    except Exception as exc:
        self.update_state(
            state='FAILURE',
            meta={'error': str(exc)}
        )
        raise exc

@shared_task
def bulk_import_students_task(csv_data, school_id, user_id):
    """Bulk import students in background"""
    try:
        from shs_system.models import Student, User
        import csv
        from io import StringIO

        user = User.objects.get(id=user_id)
        school = user.school

        students_to_create = []
        errors = []

        csv_file = StringIO(csv_data)
        reader = csv.DictReader(csv_file)

        for row_num, row in enumerate(reader, 1):
            try:
                student = Student(
                    full_name=row['full_name'],
                    date_of_birth=row['date_of_birth'],
                    gender=row['gender'],
                    parent_contact=row['parent_contact'],
                    admission_date=row['admission_date'],
                    school=school
                )
                students_to_create.append(student)
            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")

        # Bulk create students
        if students_to_create:
            Student.objects.bulk_create(students_to_create, batch_size=50)

        return {
            'created': len(students_to_create),
            'errors': errors
        }

    except Exception as exc:
        raise exc

@shared_task
def send_notification_email(user_id, subject, message):
    """Send notification email in background"""
    try:
        from shs_system.models import User

        user = User.objects.get(id=user_id)

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        return f"Email sent to {user.email}"

    except Exception as exc:
        raise exc
```

#### 5. Update Views to Use Background Tasks

```python
# views/views_report_cards.py
from .tasks import generate_report_cards_bulk

@login_required
@user_passes_test(is_admin)
def bulk_generate_report_cards(request):
    """Generate report cards using background task"""
    if request.method == "POST":
        class_id = request.POST.get("class_id")
        term_id = request.POST.get("term_id")

        if class_id and term_id:
            # Start background task
            task = generate_report_cards_bulk.delay(
                class_id=class_id,
                term_id=term_id,
                school_id=request.user.school.id,
                user_id=request.user.id
            )

            return JsonResponse({
                'success': True,
                'message': 'Report generation started',
                'task_id': task.id
            })

    return render(request, "reports/bulk_generate_report_cards_form.html")

@login_required
def task_status(request, task_id):
    """Check background task status"""
    from celery.result import AsyncResult

    task_result = AsyncResult(task_id)

    if task_result.state == 'PENDING':
        response = {
            'state': task_result.state,
            'current': 0,
            'total': 1,
        }
    elif task_result.state != 'FAILURE':
        response = {
            'state': task_result.state,
            'current': task_result.info.get('processed', 0),
            'total': task_result.info.get('total', 1),
        }
    else:
        response = {
            'state': task_result.state,
            'error': str(task_result.info),
        }

    return JsonResponse(response)
```

#### 6. Add Celery Worker to Docker Compose

```yaml
# docker-compose.yml
services:
  celery:
    build: .
    container_name: schoolapp_celery
    restart: always
    command: celery -A SchoolApp worker --loglevel=info --concurrency=4
    environment:
      - DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY}
      - DJANGO_DEBUG=${DJANGO_DEBUG}
      - DB_NAME=${DB_NAME}
      - DB_USER=${DB_USER}
      - DB_PASSWORD=${DB_PASSWORD}
      - DB_HOST=db
      - DB_PORT=5432
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - media_files:/app/media
      - logs:/app/logs
    depends_on:
      - db
      - redis
    networks:
      - schoolapp_network

  celery-beat:
    build: .
    container_name: schoolapp_celery_beat
    restart: always
    command: celery -A SchoolApp beat --loglevel=info
    environment:
      - DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY}
      - DJANGO_DEBUG=${DJANGO_DEBUG}
      - DB_NAME=${DB_NAME}
      - DB_USER=${DB_USER}
      - DB_PASSWORD=${DB_PASSWORD}
      - DB_HOST=db
      - DB_PORT=5432
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - logs:/app/logs
    depends_on:
      - db
      - redis
    networks:
      - schoolapp_network
```

---

## Load Balancing Configuration

### Nginx Load Balancer Setup

#### 1. Update Docker Compose for Multiple Django Instances

```yaml
# docker-compose.yml
services:
  django1:
    build: .
    container_name: schoolapp_django_1
    restart: always
    environment:
      - WORKER_ID=1
      - DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY}
      - DJANGO_DEBUG=${DJANGO_DEBUG}
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
      - db
      - redis
    networks:
      - schoolapp_network

  django2:
    build: .
    container_name: schoolapp_django_2
    restart: always
    environment:
      - WORKER_ID=2
      - DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY}
      - DJANGO_DEBUG=${DJANGO_DEBUG}
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
      - db
      - redis
    networks:
      - schoolapp_network

  django3:
    build: .
    container_name: schoolapp_django_3
    restart: always
    environment:
      - WORKER_ID=3
      - DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY}
      - DJANGO_DEBUG=${DJANGO_DEBUG}
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
      - db
      - redis
    networks:
      - schoolapp_network
```

#### 2. Configure Nginx Load Balancer

```nginx
# nginx.conf
upstream django_backend {
    least_conn;
    server django1:8000 max_fails=3 fail_timeout=30s;
    server django2:8000 max_fails=3 fail_timeout=30s;
    server django3:8000 max_fails=3 fail_timeout=30s;
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

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;
    limit_req_zone $binary_remote_addr zone=api:10m rate=100r/m;

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

    # Login rate limiting
    location /login/ {
        limit_req zone=login burst=3 nodelay;
        proxy_pass http://django_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # API rate limiting
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://django_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Main application
    location / {
        proxy_pass http://django_backend;
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
        proxy_pass http://django_backend;
        access_log off;
    }
}
```

---

## Monitoring Implementation

### Prometheus & Grafana Setup

#### 1. Add Monitoring to Docker Compose

```yaml
# docker-compose.yml
services:
  prometheus:
    image: prom/prometheus:latest
    container_name: schoolapp_prometheus
    restart: always
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - "--config.file=/etc/prometheus/prometheus.yml"
      - "--storage.tsdb.path=/prometheus"
      - "--web.console.libraries=/etc/prometheus/console_libraries"
      - "--web.console.templates=/etc/prometheus/consoles"
      - "--storage.tsdb.retention.time=200h"
      - "--web.enable-lifecycle"
    networks:
      - schoolapp_network

  grafana:
    image: grafana/grafana:latest
    container_name: schoolapp_grafana
    restart: always
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./monitoring/grafana/datasources:/etc/grafana/provisioning/datasources
    networks:
      - schoolapp_network

volumes:
  prometheus_data:
  grafana_data:
```

#### 2. Configure Prometheus

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

scrape_configs:
  - job_name: "django"
    static_configs:
      - targets: ["django1:8000", "django2:8000", "django3:8000"]
    metrics_path: "/metrics"
    scrape_interval: 5s

  - job_name: "postgres"
    static_configs:
      - targets: ["db:5432"]

  - job_name: "redis"
    static_configs:
      - targets: ["redis:6379"]

  - job_name: "nginx"
    static_configs:
      - targets: ["nginx:80"]
```

#### 3. Add Django Prometheus

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

#### 4. Custom Metrics

```python
# utils/metrics.py
from django.core.cache import cache
from django.db import connection
import time

def track_request_metrics(view_func):
    """Decorator to track request metrics"""
    def wrapper(request, *args, **kwargs):
        start_time = time.time()

        response = view_func(request, *args, **kwargs)

        duration = time.time() - start_time

        # Track metrics
        cache.set(f'request_duration_{request.path}', duration, 300)
        cache.set(f'active_users', cache.get('active_users', 0) + 1, 60)

        return response
    return wrapper

def get_system_metrics():
    """Get system performance metrics"""
    return {
        'active_users': cache.get('active_users', 0),
        'db_connections': len(connection.queries),
        'cache_hit_rate': cache.get('cache_hit_rate', 0),
        'avg_response_time': cache.get('avg_response_time', 0),
        'memory_usage': cache.get('memory_usage', 0),
    }
```

---

## Performance Testing

### Load Testing Setup

#### 1. Install Locust

```bash
pip install locust
```

#### 2. Create Load Test Script

```python
# tests/load_test.py
from locust import HttpUser, task, between
import random

class SchoolAppUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """Login user"""
        response = self.client.post("/login/", {
            "username": "admin",
            "password": "admin123"
        })
        if response.status_code == 200:
            self.logged_in = True
        else:
            self.logged_in = False

    @task(3)
    def view_student_list(self):
        """View student list"""
        if self.logged_in:
            self.client.get("/students/")

    @task(2)
    def view_dashboard(self):
        """View dashboard"""
        if self.logged_in:
            self.client.get("/dashboard/")

    @task(1)
    def view_reports(self):
        """View reports"""
        if self.logged_in:
            self.client.get("/reports/")

    @task(1)
    def ajax_student_list(self):
        """AJAX student list"""
        if self.logged_in:
            self.client.get("/ajax/students/")

    @task(1)
    def bulk_operations(self):
        """Test bulk operations"""
        if self.logged_in:
            # Simulate bulk import
            self.client.post("/students/bulk-import/", {
                "csv_data": "test,data,here"
            })
```

#### 3. Run Load Tests

```bash
# Start load test
locust -f tests/load_test.py --host=http://localhost:8000

# Run with specific parameters
locust -f tests/load_test.py --host=http://localhost:8000 --users=100 --spawn-rate=10 --run-time=10m
```

### Performance Benchmarks

#### 1. Response Time Targets

```python
# tests/performance_benchmarks.py
PERFORMANCE_TARGETS = {
    'student_list': 2.0,  # seconds
    'dashboard': 1.0,     # seconds
    'report_generation': 5.0,  # seconds
    'bulk_import': 30.0,  # seconds
    'ajax_requests': 0.5,  # seconds
}

def test_response_times():
    """Test response times against targets"""
    import requests
    import time

    base_url = "http://localhost:8000"

    for endpoint, target in PERFORMANCE_TARGETS.items():
        start_time = time.time()
        response = requests.get(f"{base_url}/{endpoint}/")
        duration = time.time() - start_time

        if duration > target:
            print(f"❌ {endpoint}: {duration:.2f}s (target: {target}s)")
        else:
            print(f"✅ {endpoint}: {duration:.2f}s (target: {target}s)")
```

#### 2. Database Performance Tests

```python
# tests/database_performance.py
from django.test import TestCase
from django.db import connection
from django.test.utils import override_settings

class DatabasePerformanceTest(TestCase):
    def test_query_performance(self):
        """Test database query performance"""
        with override_settings(DEBUG=True):
            # Test student list query
            from shs_system.models import Student

            start_queries = len(connection.queries)

            students = Student.objects.select_related(
                'form', 'learning_area', 'school'
            ).prefetch_related(
                'studentclass_set__assigned_class'
            ).all()

            list(students)  # Execute query

            end_queries = len(connection.queries)
            query_count = end_queries - start_queries

            # Should use minimal queries due to select_related/prefetch_related
            self.assertLess(query_count, 5, f"Too many queries: {query_count}")
```

---

## Deployment Checklist

### Pre-Deployment Checklist

#### 1. Performance Optimizations

- [ ] Redis caching implemented
- [ ] Database indexes added
- [ ] Session management optimized
- [ ] Gunicorn workers increased
- [ ] Connection pooling configured
- [ ] Background tasks setup
- [ ] Load balancing configured

#### 2. Security Checklist

- [ ] SSL certificates installed
- [ ] Security headers configured
- [ ] Rate limiting implemented
- [ ] CSRF protection enabled
- [ ] File upload restrictions
- [ ] Database permissions set
- [ ] Environment variables secured

#### 3. Monitoring Setup

- [ ] Prometheus configured
- [ ] Grafana dashboards created
- [ ] Health checks implemented
- [ ] Logging configured
- [ ] Alerting rules set
- [ ] Performance metrics tracked

#### 4. Backup & Recovery

- [ ] Database backup script
- [ ] Media files backup
- [ ] Recovery procedures tested
- [ ] Backup retention policy
- [ ] Disaster recovery plan

### Deployment Commands

#### 1. Production Deployment

```bash
#!/bin/bash
# deploy.sh

# Stop existing containers
docker-compose down

# Pull latest images
docker-compose pull

# Build new images
docker-compose build

# Run migrations
docker-compose run --rm django python manage.py migrate

# Collect static files
docker-compose run --rm django python manage.py collectstatic --noinput

# Start services
docker-compose up -d

# Wait for services to be ready
sleep 30

# Run health checks
curl -f http://localhost/health/ || exit 1

echo "Deployment completed successfully"
```

#### 2. Performance Verification

```bash
#!/bin/bash
# verify_performance.sh

# Test response times
echo "Testing response times..."
curl -w "@curl-format.txt" -o /dev/null -s http://localhost/

# Test database connectivity
echo "Testing database connectivity..."
docker exec schoolapp_postgres psql -U postgres -d multi_sis_database -c "SELECT 1;"

# Test Redis connectivity
echo "Testing Redis connectivity..."
docker exec schoolapp_redis redis-cli ping

# Test load balancing
echo "Testing load balancing..."
for i in {1..10}; do
    curl -s http://localhost/health/ | grep -o "healthy"
done

echo "Performance verification completed"
```

#### 3. Monitoring Setup

```bash
#!/bin/bash
# setup_monitoring.sh

# Start monitoring services
docker-compose up -d prometheus grafana

# Wait for services
sleep 30

# Import Grafana dashboards
curl -X POST \
  http://admin:admin@localhost:3000/api/dashboards/db \
  -H 'Content-Type: application/json' \
  -d @monitoring/grafana/dashboard.json

echo "Monitoring setup completed"
```

### Post-Deployment Monitoring

#### 1. Key Metrics to Monitor

- **Response Time**: <2 seconds for 95% of requests
- **Error Rate**: <1% of requests
- **Database Connections**: <80% of max connections
- **Memory Usage**: <80% of available memory
- **CPU Usage**: <70% of available CPU
- **Disk Usage**: <80% of available disk space

#### 2. Alerting Rules

```yaml
# monitoring/alert_rules.yml
groups:
  - name: schoolapp_alerts
    rules:
      - alert: HighResponseTime
        expr: django_http_requests_duration_seconds{quantile="0.95"} > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High response time detected"

      - alert: HighErrorRate
        expr: rate(django_http_requests_total{status=~"5.."}[5m]) > 0.01
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"

      - alert: DatabaseConnectionsHigh
        expr: postgresql_stat_activity_count > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Database connections high"
```

---

## Conclusion

This implementation guide provides step-by-step instructions for optimizing the SchoolApp system for production deployment. Following these recommendations will significantly improve performance, scalability, and reliability.

### Expected Performance Improvements

- **Response Time**: 50-80% reduction
- **Concurrent Users**: 3-5x increase in capacity
- **Database Performance**: 60-90% improvement
- **Memory Usage**: 30-50% reduction
- **Error Rate**: 80-95% reduction

### Implementation Timeline

- **Week 1**: Basic optimizations (Redis, indexes, sessions)
- **Week 2**: Background tasks and caching
- **Week 3**: Load balancing and monitoring
- **Week 4**: Performance testing and tuning

### Success Metrics

- Support 200+ concurrent users
- Handle 10,000+ student records
- Maintain <2 second response times
- Achieve 99.9% uptime
- Keep error rate <1%

This guide ensures the SchoolApp system can scale effectively while maintaining performance and reliability.

---

_Document Version: 1.0_  
_Last Updated: [Current Date]_  
_Next Review: [Date + 3 months]_
