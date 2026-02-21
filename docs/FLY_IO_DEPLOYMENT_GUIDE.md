# Fly.io Deployment Guide

Complete guide for deploying SchoolApp to Fly.io.

## Prerequisites

1. **Fly.io CLI**: Install from [fly.io/docs/hands-on/install-flyctl/](https://fly.io/docs/hands-on/install-flyctl/)
2. **Fly.io Account**: Sign up at [fly.io](https://fly.io)
3. **PostgreSQL Database**: Either use Fly.io PostgreSQL or external database

## Initial Setup

### 1. Install Fly.io CLI

**Windows (PowerShell):**

```powershell
powershell -Command "iwr https://fly.io/install.ps1 -useb | iex"
```

**macOS/Linux:**

```bash
curl -L https://fly.io/install.sh | sh
```

### 2. Login to Fly.io

```bash
fly auth login
```

### 3. Initialize Fly.io App

```bash
cd SchoolApp
fly launch
```

When prompted:

- **App name**: Choose a name or use the suggested one (e.g., `schoolapp`)
- **Region**: Choose closest region (e.g., `iad` for US East)
- **PostgreSQL**: Choose whether to set up a PostgreSQL database now
- **Redis**: Optional, but recommended for caching

### 4. Configure App

Edit `fly.toml` if needed (already configured in this project):

```toml
app = "your-app-name"
primary_region = "iad"  # Your preferred region
```

## Database Setup

### Option 1: Fly.io PostgreSQL (Recommended)

Create a PostgreSQL database:

```bash
fly postgres create --name schoolapp-db --region iad
```

Attach the database to your app:

```bash
fly postgres attach --app schoolapp schoolapp-db
```

This automatically sets the `DATABASE_URL` environment variable.

### Option 2: External PostgreSQL

If using an external PostgreSQL database:

```bash
fly secrets set DATABASE_URL="postgresql://user:password@host:port/dbname"
```

## Environment Variables

Set all required environment variables:

```bash
# Secret Key (Generate a new one for production)
fly secrets set DJANGO_SECRET_KEY="your-secret-key-here"

# Debug Mode (Set to False for production)
fly secrets set DEBUG="False"

# Allowed Hosts (Automatically set if using Fly.io domain)
fly secrets set ALLOWED_HOSTS="your-app-name.fly.dev"

# Email Configuration
fly secrets set EMAIL_HOST="smtp.gmail.com"
fly secrets set EMAIL_PORT="465"
fly secrets set EMAIL_USE_SSL="True"
fly secrets set EMAIL_HOST_USER="your-email@gmail.com"
fly secrets set EMAIL_HOST_PASSWORD="your-app-password"
fly secrets set DEFAULT_FROM_EMAIL="your-email@gmail.com"

# Site URL
fly secrets set SITE_URL="https://your-app-name.fly.dev"

# Admin Email
fly secrets set ADMIN_EMAIL="admin@yourdomain.com"

# Google OAuth2 (if using)
fly secrets set SOCIAL_AUTH_GOOGLE_OAUTH2_KEY="your-client-id"
fly secrets set SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET="your-client-secret"
```

**View all secrets:**

```bash
fly secrets list
```

## Deployment

### First Deployment

```bash
# Deploy the app
fly deploy

# Check deployment status
fly status

# View logs
fly logs
```

### Updating the App

```bash
# Deploy updates
fly deploy

# Deploy with remote builder (if local build fails)
fly deploy --remote-only
```

## Post-Deployment Setup

### 1. Run Migrations

```bash
# SSH into the app
fly ssh console

# Run migrations
python manage.py migrate --settings=SchoolApp.settings_fly

# Create superuser
python manage.py createsuperuser --settings=SchoolApp.settings_fly

# Exit SSH
exit
```

Or use fly SSH command:

```bash
fly ssh console -C "python manage.py migrate --settings=SchoolApp.settings_fly"
```

### 2. Collect Static Files

Static files are collected during Docker build, but if needed:

```bash
fly ssh console -C "python manage.py collectstatic --noinput --settings=SchoolApp.settings_fly"
```

## Scaling

### Scale Vertically (More Resources)

```bash
# Scale VM resources
fly scale vm shared-cpu-2x --memory 2048
```

### Scale Horizontally (More Instances)

```bash
# Scale to 2 instances
fly scale count 2

# Check current scale
fly scale show
```

## Volume Setup (for Media Files)

Fly.io volumes persist data. For media files:

```bash
# Create a volume
fly volumes create media_data --size 10 --region iad

# Update fly.toml to mount the volume
```

Add to `fly.toml`:

```toml
[[mounts]]
  source = "media_data"
  destination = "/app/media"
```

**Note**: Volumes are region-specific. Make sure your app and volume are in the same region.

## Custom Domain Setup

### 1. Add Domain

```bash
fly certs add yourdomain.com
```

### 2. Update DNS

Follow the instructions provided by Fly.io to update your DNS records.

### 3. Update Environment Variables

```bash
fly secrets set CUSTOM_DOMAIN="yourdomain.com"
fly secrets set SITE_URL="https://yourdomain.com"
```

## Monitoring & Logs

### View Logs

```bash
# Real-time logs
fly logs

# Specific app logs
fly logs -a schoolapp

# Filter logs
fly logs | grep ERROR
```

### Monitoring

Fly.io provides built-in metrics:

```bash
# View metrics
fly metrics

# View status
fly status
```

## Health Checks

The app includes a health check endpoint at `/health/`. Configured in `fly.toml`:

```toml
[[services.http_checks]]
  interval = "15s"
  grace_period = "5s"
  method = "GET"
  path = "/health/"
  protocol = "http"
  timeout = "10s"
```

## Troubleshooting

### Common Issues

#### 1. Database Connection Issues

```bash
# Check database status
fly postgres status -a schoolapp-db

# Test connection
fly ssh console -C "python manage.py dbshell --settings=SchoolApp.settings_fly"
```

#### 2. Static Files Not Loading

```bash
# Verify static files collection
fly ssh console -C "ls -la staticfiles/"

# Recollect static files
fly ssh console -C "python manage.py collectstatic --noinput --settings=SchoolApp.settings_fly"
```

#### 3. Memory Issues

```bash
# Check memory usage
fly status

# Scale up memory
fly scale vm shared-cpu-2x --memory 2048
```

#### 4. Build Failures

```bash
# Deploy with remote builder
fly deploy --remote-only

# Check build logs
fly logs | grep build
```

### SSH Access

```bash
# SSH into running instance
fly ssh console

# Run Django management commands
fly ssh console -C "python manage.py shell --settings=SchoolApp.settings_fly"
```

## Backup & Restore

### Database Backup

```bash
# Backup PostgreSQL database
fly postgres backup create -a schoolapp-db

# List backups
fly postgres backup list -a schoolapp-db
```

### Restore Database

```bash
# Restore from backup
fly postgres backup restore <backup-id> -a schoolapp-db
```

## Cost Optimization

### Free Tier Limits

- **3 shared-cpu-1x VMs** with 256MB RAM each
- **3GB persistent volume** storage
- **160GB outbound data transfer** per month

### Recommended Production Setup

- **VM**: shared-cpu-1x with 1GB RAM ($5.70/month)
- **PostgreSQL**: Development plan ($15/month) or Production plan
- **Volume**: As needed ($0.15/GB/month)

## Environment Variables Reference

See `fly.env.example` for a complete list of environment variables.

## Useful Commands

```bash
# App management
fly apps list
fly status
fly open                    # Open app in browser

# Secrets management
fly secrets list
fly secrets set KEY=value
fly secrets unset KEY

# Scaling
fly scale show
fly scale count 2
fly scale vm shared-cpu-2x --memory 2048

# Logs and monitoring
fly logs
fly metrics
fly status

# SSH access
fly ssh console
fly ssh console -C "command"

# Database
fly postgres status -a schoolapp-db
fly postgres connect -a schoolapp-db

# Deployment
fly deploy
fly deploy --remote-only
fly releases list
fly releases rollback
```

## Additional Resources

- [Fly.io Documentation](https://fly.io/docs/)
- [Django on Fly.io](https://fly.io/docs/django/)
- [PostgreSQL on Fly.io](https://fly.io/docs/postgres/)
- [Redis on Fly.io](https://fly.io/docs/redis/)

---

**Note**: Always test your deployment in a staging environment before deploying to production.
