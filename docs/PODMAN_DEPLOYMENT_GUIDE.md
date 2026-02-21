# Django SchoolApp Podman Deployment Guide

## Overview

This guide provides instructions for deploying the Django SchoolApp using Podman on a local network without internet access. Podman is a daemonless, rootless container engine that is a drop-in replacement for Docker.

## Prerequisites

- Podman installed on your system
  - **Linux**: `sudo dnf install podman` (RHEL/Fedora) or `sudo apt install podman` (Debian/Ubuntu)
  - **macOS**: `brew install podman` or download from [podman.io](https://podman.io)
  - **Windows**: Install via WSL2 or use Podman Desktop
- Podman Compose (optional, for docker-compose compatibility)
  - Install: `pip install podman-compose` or `sudo dnf install podman-compose`
- At least 4GB RAM available
- Port 8000 and 5432 available (PostgreSQL default port)

## Key Differences from Docker

1. **Daemonless**: Podman doesn't require a background daemon
2. **Rootless**: Containers run as your user by default (more secure)
3. **Compatibility**: Most Docker commands work with Podman via aliases
4. **Compose**: Use `podman-compose` instead of `docker-compose`

## Quick Start (Podman Compose - Recommended)

### 1. Environment Setup

**Linux/macOS:**

```bash
# Copy the example environment file
cp env.example .env

# Edit the .env file with your configuration
nano .env  # or vim, or your preferred editor
```

**Windows (PowerShell):**

```powershell
# Copy the example environment file
Copy-Item env.example .env

# Edit the .env file with your configuration
notepad .env
```

### 2. Configuration

Edit the `.env` file with your specific values:

- **DJANGO_SECRET_KEY**: Generate a new secret key
- **DB_PASSWORD**: Set a strong PostgreSQL database password
- **ALLOWED_HOSTS**: Add your server's IP addresses
- **CSRF_TRUSTED_ORIGINS**: Add your server's URLs

### 3. Build and Start

```bash
# Build and start all services
podman-compose up -d

# View logs
podman-compose logs -f

# Check service status
podman-compose ps
```

### 4. Database Migration

```bash
# Run database migrations
podman-compose exec django python manage.py migrate

# Create superuser
podman-compose exec django python manage.py createsuperuser

# Collect static files (if needed)
podman-compose exec django python manage.py collectstatic --noinput
```

### 5. Access the Application

- **Main Application**: <http://localhost:8000>
- **Admin Panel**: <http://localhost:8000/admin>
- **Database**: localhost:5432 (PostgreSQL)

## Manual Podman Deployment

### 1. Create Network

```bash
# Create a podman network
podman network create schoolapp_network
```

### 2. Create Volumes

```bash
# Create named volumes
podman volume create postgres_data
podman volume create media_files
podman volume create static_files
podman volume create logs
```

### 3. Start PostgreSQL Container

```bash
podman run -d \
  --name schoolapp_postgres \
  --network schoolapp_network \
  -e POSTGRES_DB=multi_sis_database \
  -e POSTGRES_USER=sis_user \
  -e POSTGRES_PASSWORD=your-password \
  -e POSTGRES_INITDB_ARGS="--encoding=UTF-8 --lc-collate=C --lc-ctype=C" \
  -p 5432:5432 \
  -v postgres_data:/var/lib/postgresql/data \
  -v ./scripts/init.sql:/docker-entrypoint-initdb.d/init.sql:ro \
  --health-cmd="pg_isready -U sis_user -d multi_sis_database" \
  --health-interval=10s \
  --health-timeout=5s \
  --health-retries=5 \
  postgres:15
```

### 4. Build Django Image

```bash
# Build the Django image
podman build -t schoolapp:latest .
```

### 5. Start Django Container

```bash
podman run -d \
  --name schoolapp_django \
  --network schoolapp_network \
  -e DJANGO_SECRET_KEY=your-secret-key \
  -e DJANGO_DEBUG=False \
  -e ALLOWED_HOSTS=localhost,127.0.0.1 \
  -e DB_NAME=multi_sis_database \
  -e DB_USER=sis_user \
  -e DB_PASSWORD=your-password \
  -e DB_HOST=schoolapp_postgres \
  -e DB_PORT=5432 \
  -e CSRF_TRUSTED_ORIGINS=http://localhost:8000 \
  -v media_files:/app/media \
  -v static_files:/app/staticfiles \
  -v logs:/app/logs \
  --health-cmd="curl -f http://localhost:8000/health/ || exit 1" \
  --health-interval=30s \
  --health-timeout=10s \
  --health-retries=3 \
  --health-start-period=40s \
  schoolapp:latest
```

### 6. Start Nginx Container

```bash
podman run -d \
  --name schoolapp_nginx \
  --network schoolapp_network \
  -p 8000:80 \
  -v ./nginx.conf:/etc/nginx/conf.d/default.conf:ro \
  -v static_files:/app/staticfiles:ro \
  -v media_files:/app/media:ro \
  nginx:alpine
```

## Using Pods (Podman Native Approach)

Podman supports pods, which group containers together. This is a more native Podman approach:

### 1. Create a Pod

```bash
# Create a pod with port mapping
podman pod create \
  --name schoolapp_pod \
  -p 8000:80 \
  -p 5432:5432
```

### 2. Start Containers in the Pod

```bash
# Start PostgreSQL in the pod
podman run -d \
  --pod schoolapp_pod \
  --name schoolapp_postgres \
  -e POSTGRES_DB=multi_sis_database \
  -e POSTGRES_USER=sis_user \
  -e POSTGRES_PASSWORD=your-password \
  -v postgres_data:/var/lib/postgresql/data \
  postgres:15

# Start Django in the pod
podman run -d \
  --pod schoolapp_pod \
  --name schoolapp_django \
  -e DB_HOST=localhost \
  -e DB_NAME=multi_sis_database \
  -e DB_USER=sis_user \
  -e DB_PASSWORD=your-password \
  -v media_files:/app/media \
  -v static_files:/app/staticfiles \
  schoolapp:latest

# Start Nginx in the pod
podman run -d \
  --pod schoolapp_pod \
  --name schoolapp_nginx \
  -v ./nginx.conf:/etc/nginx/conf.d/default.conf:ro \
  -v static_files:/app/staticfiles:ro \
  -v media_files:/app/media:ro \
  nginx:alpine
```

### 3. Manage the Pod

```bash
# Start the pod
podman pod start schoolapp_pod

# Stop the pod
podman pod stop schoolapp_pod

# Remove the pod
podman pod rm schoolapp_pod

# View pod status
podman pod ps
```

## Management Commands

### Start Services

```bash
# Using podman-compose
podman-compose up -d

# Using pods
podman pod start schoolapp_pod
```

### Stop Services

```bash
# Using podman-compose
podman-compose down

# Using pods
podman pod stop schoolapp_pod

# Stop and remove
podman pod rm -f schoolapp_pod
```

### View Logs

```bash
# Using podman-compose
podman-compose logs -f

# Specific service
podman-compose logs -f django
podman-compose logs -f nginx
podman-compose logs -f db

# Using podman directly
podman logs -f schoolapp_django
podman logs -f schoolapp_nginx
podman logs -f schoolapp_postgres

# Pod logs (all containers)
podman pod logs schoolapp_pod
```

### Restart Services

```bash
# Using podman-compose
podman-compose restart

# Using podman directly
podman restart schoolapp_django
podman restart schoolapp_nginx
podman restart schoolapp_postgres

# Restart entire pod
podman pod restart schoolapp_pod
```

### Update Application

```bash
# Using podman-compose
podman-compose down
podman-compose build --no-cache
podman-compose up -d

# Using podman directly
podman stop schoolapp_django
podman rm schoolapp_django
podman build -t schoolapp:latest .
podman run -d --name schoolapp_django [previous run options]
```

## Rootless vs Rootful Operation

### Rootless (Default - Recommended)

Podman runs containers as your user by default. This is more secure:

```bash
# Containers run as your user
podman run -d --name test alpine sleep 3600

# Check running containers
podman ps
```

### Rootful (Requires sudo)

For system-wide containers or specific requirements:

```bash
# Run with sudo for rootful mode
sudo podman run -d --name test alpine sleep 3600

# Check rootful containers
sudo podman ps
```

**Note**: Mixing rootless and rootful containers can cause confusion. Stick to one mode.

## Troubleshooting

### Check Service Health

```bash
# Using podman-compose
podman-compose ps
podman-compose exec django curl -f http://localhost:8000/health/

# Using podman directly
podman ps
podman exec schoolapp_django curl -f http://localhost:8000/health/

# Check pod health
podman pod inspect schoolapp_pod
```

### Access Container Shell

```bash
# Using podman-compose
podman-compose exec django bash
podman-compose exec db psql -U sis_user -d multi_sis_database

# Using podman directly
podman exec -it schoolapp_django bash
podman exec -it schoolapp_postgres psql -U sis_user -d multi_sis_database
```

### View Container Logs

```bash
# Using podman-compose
podman-compose logs django
podman-compose logs nginx
podman-compose logs db

# Using podman directly
podman logs schoolapp_django
podman logs schoolapp_nginx
podman logs schoolapp_postgres

# Follow logs in real-time
podman logs -f schoolapp_django
```

### Inspect Containers

```bash
# Inspect container configuration
podman inspect schoolapp_django

# Check container resource usage
podman stats

# Check specific container
podman stats schoolapp_django
```

### Reset Everything

```bash
# Using podman-compose
podman-compose down -v
podman-compose up -d

# Using podman directly
podman pod rm -f schoolapp_pod
podman volume rm postgres_data media_files static_files logs
# Then recreate as shown in manual deployment section
```

### Common Issues

#### Port Already in Use

```bash
# Check what's using the port
sudo lsof -i :8000  # Linux/macOS
netstat -ano | findstr :8000  # Windows

# Stop conflicting containers
podman ps
podman stop <container_id>
```

#### Permission Issues (Rootless)

```bash
# Check if running rootless
podman info | grep rootless

# If volumes have permission issues, adjust ownership
# For rootless Podman, volumes are stored in ~/.local/share/containers/storage
```

#### Network Issues

```bash
# List networks
podman network ls

# Inspect network
podman network inspect schoolapp_network

# Remove and recreate network
podman network rm schoolapp_network
podman network create schoolapp_network
```

#### Volume Issues

```bash
# List volumes
podman volume ls

# Inspect volume
podman volume inspect postgres_data

# Remove volume (WARNING: deletes data)
podman volume rm postgres_data
```

## Security Considerations

1. **Rootless by Default**: Podman runs containers as your user, reducing security risks
2. **No Daemon**: No background daemon means a smaller attack surface
3. **Change Default Passwords**: Always change default passwords in `.env`
4. **Firewall**: Configure firewall to only allow necessary ports
5. **SSL**: Consider adding SSL certificate for production use
6. **Regular Updates**: Keep Podman and container images updated
7. **SELinux/AppArmor**: Podman respects system security policies

## Performance Optimization

1. **Database**: Monitor PostgreSQL performance and adjust settings
2. **Static Files**: Ensure static files are properly cached
3. **Media Files**: Consider using external storage for large files
4. **Monitoring**: Set up monitoring for container health
5. **Resource Limits**: Set CPU and memory limits if needed:

```bash
podman run -d \
  --memory=2g \
  --cpus=2 \
  --name schoolapp_django \
  schoolapp:latest
```

## Podman Desktop (GUI Alternative)

For users who prefer a GUI:

1. **Install Podman Desktop**: Download from [podman-desktop.io](https://podman-desktop.io)
2. **Import docker-compose.yml**: Use the GUI to import and manage your compose file
3. **Container Management**: Use the GUI to start, stop, and monitor containers
4. **Logs and Terminal**: Access container logs and terminals through the GUI

## Migration from Docker

If you're migrating from Docker:

1. **Stop Docker containers**: `docker-compose down`
2. **Install Podman**: Follow installation instructions above
3. **Use podman-compose**: Most docker-compose commands work with podman-compose
4. **Rebuild images**: `podman-compose build`
5. **Start services**: `podman-compose up -d`

**Note**: Docker and Podman can coexist, but be careful not to use the same port mappings.

## Support

For issues or questions:

1. Check container logs: `podman-compose logs` or `podman logs <container>`
2. Verify environment variables in `.env`
3. Ensure all required ports are available
4. Check Podman is running: `podman info`
5. Verify network connectivity: `podman network inspect schoolapp_network`
6. Check volume mounts: `podman volume inspect <volume_name>`

## Additional Resources

- [Podman Documentation](https://docs.podman.io)
- [Podman Compose Documentation](https://github.com/containers/podman-compose)
- [Podman Desktop](https://podman-desktop.io)
- [Rootless Containers Guide](https://github.com/containers/podman/blob/main/docs/tutorials/rootless_tutorial.md)
