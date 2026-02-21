# Docker Auto-Start Configuration Guide

This guide explains how to configure your SchoolApp Docker containers to start automatically on system boot.

## Overview

Your SchoolApp is already configured with Docker Compose and includes:

- PostgreSQL database
- Django application
- Nginx web server
- Automatic restart policies (`restart: always`)

## Quick Setup

### Option 1: Using Docker Compose (Recommended)

Your containers are already configured to restart automatically. Simply run:

```bash
# Start containers
docker-compose up -d

# Verify they're running
docker-compose ps
```

The containers will automatically restart when:

- Docker daemon starts
- System reboots
- Container crashes

### Option 2: Using Provided Scripts

#### Windows (PowerShell)

```powershell
# Start containers
.\scripts\docker-auto-start.ps1 start

# Check status
.\scripts\docker-auto-start.ps1 status

# Stop containers
.\scripts\docker-auto-start.ps1 stop
```

#### Windows (Batch)

```cmd
# Start containers
scripts\docker-auto-start.bat start

# Check status
scripts\docker-auto-start.bat status
```

#### Linux/macOS

```bash
# Make script executable
chmod +x scripts/docker-auto-start.sh

# Start containers
./scripts/docker-auto-start.sh start

# Check status
./scripts/docker-auto-start.sh status
```

## Advanced Configuration

### Linux: Systemd Service (Production)

For production Linux servers, use the systemd service:

1. **Copy the service file:**

   ```bash
   sudo cp scripts/schoolapp-docker.service /etc/systemd/system/
   ```

2. **Edit the service file:**

   ```bash
   sudo nano /etc/systemd/system/schoolapp-docker.service
   ```

   Update the paths:

   ```
   WorkingDirectory=/path/to/your/SchoolApp
   ExecStart=/path/to/your/SchoolApp/scripts/docker-auto-start.sh start
   ExecStop=/path/to/your/SchoolApp/scripts/docker-auto-start.sh stop
   ```

3. **Enable and start the service:**

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable schoolapp-docker.service
   sudo systemctl start schoolapp-docker.service
   ```

4. **Check service status:**
   ```bash
   sudo systemctl status schoolapp-docker.service
   ```

### Windows: Task Scheduler

To start containers automatically on Windows boot:

1. **Open Task Scheduler** (taskschd.msc)

2. **Create Basic Task:**

   - Name: "SchoolApp Docker Auto-Start"
   - Trigger: "When the computer starts"
   - Action: "Start a program"
   - Program: `powershell.exe`
   - Arguments: `-ExecutionPolicy Bypass -File "C:\path\to\your\SchoolApp\scripts\docker-auto-start.ps1" start`

3. **Configure additional settings:**
   - Run whether user is logged on or not
   - Run with highest privileges
   - Start in: `C:\path\to\your\SchoolApp`

### Docker Desktop Auto-Start

Ensure Docker Desktop starts automatically:

#### Windows:

1. Open Docker Desktop
2. Go to Settings → General
3. Enable "Start Docker Desktop when you log in"

#### macOS:

1. Open Docker Desktop
2. Go to Preferences → General
3. Enable "Start Docker Desktop when you log in"

#### Linux:

Docker daemon typically starts automatically with systemd.

## Verification

### Check Container Status

```bash
# Using Docker Compose
docker-compose ps

# Using Docker directly
docker ps --filter "name=schoolapp"
```

### Check Logs

```bash
# View all service logs
docker-compose logs

# View specific service logs
docker-compose logs django
docker-compose logs db
docker-compose logs nginx
```

### Test Auto-Restart

```bash
# Stop a container manually
docker stop schoolapp_django

# Check if it restarts automatically
docker ps --filter "name=schoolapp_django"
```

## Troubleshooting

### Common Issues

1. **Docker not starting:**

   - Ensure Docker Desktop is installed and running
   - Check Docker daemon status: `docker info`

2. **Containers not starting:**

   - Check environment variables in `.env` file
   - Verify database connection settings
   - Check logs: `docker-compose logs`

3. **Permission issues (Linux):**

   - Ensure user is in docker group: `sudo usermod -aG docker $USER`
   - Log out and log back in

4. **Port conflicts:**
   - Ensure port 8000 is not in use by another application
   - Check: `netstat -tulpn | grep :8000`

### Log Files

- **Linux/macOS:** `/var/log/schoolapp-startup.log`
- **Windows:** `%TEMP%\schoolapp-startup.log`

### Health Checks

Your containers include health checks:

- **Database:** Checks PostgreSQL connectivity
- **Django:** Checks HTTP endpoint at `/health/`
- **Nginx:** Depends on Django health

## Security Considerations

1. **Firewall:** Ensure port 8000 is accessible
2. **SSL/TLS:** Configure HTTPS for production
3. **Environment Variables:** Keep sensitive data in `.env` file
4. **Updates:** Regularly update Docker images and dependencies

## Production Recommendations

1. **Use reverse proxy:** Configure Nginx for SSL termination
2. **Backup strategy:** Implement regular database backups
3. **Monitoring:** Set up container monitoring and alerting
4. **Resource limits:** Configure memory and CPU limits
5. **Log rotation:** Implement log rotation for container logs

## Support

For issues or questions:

1. Check the logs first
2. Verify Docker and Docker Compose versions
3. Ensure all environment variables are set correctly
4. Test with a fresh clone of the repository

## Environment Variables Required

Make sure your `.env` file contains:

```env
DJANGO_SECRET_KEY=your-secret-key
DJANGO_DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com
DB_NAME=schoolapp_db
DB_USER=schoolapp_user
DB_PASSWORD=your-db-password
CSRF_TRUSTED_ORIGINS=http://localhost:8000,https://your-domain.com
# ... other variables as needed
```
