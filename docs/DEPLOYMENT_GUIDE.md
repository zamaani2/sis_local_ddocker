# Django SchoolApp Docker Deployment Guide

## Overview

This guide provides instructions for deploying the Django SchoolApp using Docker on a local network without internet access.

## Prerequisites

- Docker Desktop installed on Windows
- Docker Compose (included with Docker Desktop)
- At least 4GB RAM available
- Port 80 and 3306 available

## Quick Start (Docker Compose - Recommended)

### 1. Environment Setup

```bash
# Copy the example environment file
copy env.example .env

# Edit the .env file with your configuration
notepad .env
```

### 2. Configuration

Edit the `.env` file with your specific values:

- **DJANGO_SECRET_KEY**: Generate a new secret key
- **DB_ROOT_PASSWORD**: Set a strong MySQL root password
- **DB_PASSWORD**: Set a strong database user password
- **ALLOWED_HOSTS**: Add your server's IP addresses
- **CSRF_TRUSTED_ORIGINS**: Add your server's URLs

### 3. Build and Start

```bash
# Build and start all services
docker-compose up -d

# View logs
doc ker-compose logs -f

# Check service status
docker-compose ps
```

### 4. Database Migration

```bash
# Run database migrations
docker-compose exec django python manage.py migrate

# Create superuser
docker-compose exec django python manage.py createsuperuser

# Collect static files (if needed)
docker-compose exec django python manage.py collectstatic --noinput
```

### 5. Access the Application

- **Main Application**: http://localhost
- **Admin Panel**: http://localhost/admin
- **Database**: localhost:3306 (MySQL)

## Manual Docker Deployment

### 1. Build the Django Image

```bash
docker build -t schoolapp:latest .
```

### 2. Start MySQL Container

```bash
docker run -d \
  --name schoolapp_mysql \
  --network schoolapp_network \
  -e MYSQL_ROOT_PASSWORD=your-root-password \
  -e MYSQL_DATABASE=multi_sis_database \
  -e MYSQL_USER=sis_user \
  -e MYSQL_PASSWORD=your-password \
  -p 3306:3306 \
  -v mysql_data:/var/lib/mysql \
  mysql:8.0
```

### 3. Start Django Container

```bash
docker run -d \
  --name schoolapp_django \
  --network schoolapp_network \
  -e DJANGO_SECRET_KEY=your-secret-key \
  -e DB_HOST=schoolapp_mysql \
  -e DB_NAME=multi_sis_database \
  -e DB_USER=sis_user \
  -e DB_PASSWORD=your-password \
  -p 8000:8000 \
  -v media_files:/app/media \
  -v static_files:/app/staticfiles \
  schoolapp:latest
```

### 4. Start Nginx Container

```bash
docker run -d \
  --name schoolapp_nginx \
  --network schoolapp_network \
  -p 80:80 \
  -v nginx.conf:/etc/nginx/conf.d/default.conf:ro \
  -v static_files:/app/staticfiles:ro \
  -v media_files:/app/media:ro \
  nginx:alpine
```

## Management Commands

### Start Services

```bash
docker-compose up -d
```

### Stop Services

```bash
docker-compose down
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f django
docker-compose logs -f nginx
docker-compose logs -f db
```

### Restart Services

```bash
docker-compose restart
```

### Update Application

```bash
# Pull latest changes and rebuild
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## Troubleshooting

### Check Service Health

```bash
docker-compose ps
docker-compose exec django curl -f http://localhost:8000/health/
```

### Access Container Shell

```bash
docker-compose exec django bash
docker-compose exec db mysql -u root -p
```

### View Container Logs

```bash
docker-compose logs django
docker-compose logs nginx
docker-compose logs db
```

### Reset Everything

```bash
docker-compose down -v
docker-compose up -d
```

## Security Considerations

1. **Change Default Passwords**: Always change default passwords in `.env`
2. **Firewall**: Configure firewall to only allow necessary ports
3. **SSL**: Consider adding SSL certificate for production use
4. **Regular Updates**: Keep Docker images updated

## Performance Optimization

1. **Database**: Monitor MySQL performance and adjust settings
2. **Static Files**: Ensure static files are properly cached
3. **Media Files**: Consider using external storage for large files
4. **Monitoring**: Set up monitoring for container health

## Support

For issues or questions:

1. Check container logs: `docker-compose logs`
2. Verify environment variables in `.env`
3. Ensure all required ports are available
4. Check Docker Desktop is running properly
