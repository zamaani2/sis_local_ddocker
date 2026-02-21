# Environment Configuration Guide

## Overview

This guide explains how to configure the environment variables for the Django SchoolApp Docker deployment.

## Quick Setup

1. **Copy the example file**:

   ```bash
   copy env.example .env
   ```

2. **Edit the configuration**:
   ```bash
   notepad .env
   ```

## Required Configuration

### Django Settings

```bash
# Generate a new secret key (required)
DJANGO_SECRET_KEY=your-super-secret-key-change-this-in-production

# Set to False for production
DJANGO_DEBUG=False

# Add your server's IP addresses
ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.100,192.168.1.101

# Add your server's URLs (include http:// or https://)
CSRF_TRUSTED_ORIGINS=http://localhost,http://127.0.0.1,http://192.168.1.100,http://192.168.1.101
```

### Database Configuration

```bash
# MySQL root password (required)
DB_ROOT_PASSWORD=your-mysql-root-password

# Database name (can keep default)
DB_NAME=multi_sis_database

# Database user (can keep default)
DB_USER=sis_user

# Database user password (required)
DB_PASSWORD=your-database-password

# Database host (keep as 'db' for Docker)
DB_HOST=db

# Database port (keep as 3306)
DB_PORT=3306
```

## Optional Configuration

### Email Settings

```bash
# Email server (optional)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=465
EMAIL_USE_TLS=False
EMAIL_USE_SSL=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=your-email@gmail.com

# Set to True to disable email sending
DISABLE_EMAIL_SENDING=False
```

### Google OAuth2 (Optional)

```bash
# Google OAuth2 credentials (optional)
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY=your-google-oauth2-key
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET=your-google-oauth2-secret
```

### Session Settings

```bash
# Session timeout in seconds (10 hours default)
SESSION_COOKIE_AGE=36000000

# Admin email for error notifications
ADMIN_EMAIL=admin@example.com

# Site URL for email links
SITE_URL=http://localhost
```

## Security Best Practices

### 1. Generate Strong Secret Key

```python
# Run this in Python to generate a secret key
import secrets
print(secrets.token_urlsafe(50))
```

### 2. Use Strong Passwords

- **DB_ROOT_PASSWORD**: At least 16 characters with mixed case, numbers, and symbols
- **DB_PASSWORD**: At least 12 characters with mixed case and numbers

### 3. Configure Network Security

- **ALLOWED_HOSTS**: Only include IP addresses that will access the application
- **CSRF_TRUSTED_ORIGINS**: Only include URLs that will access the application

### 4. Email Configuration

- Use app-specific passwords for Gmail
- Consider using a dedicated email service for production
- Set `DISABLE_EMAIL_SENDING=True` if email is not needed

## Network Configuration Examples

### Local Development

```bash
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost,http://127.0.0.1
```

### Local Network (192.168.1.x)

```bash
ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.100,192.168.1.101
CSRF_TRUSTED_ORIGINS=http://localhost,http://127.0.0.1,http://192.168.1.100,http://192.168.1.101
```

### Multiple Networks

```bash
ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.100,192.168.2.100,10.0.0.100
CSRF_TRUSTED_ORIGINS=http://localhost,http://127.0.0.1,http://192.168.1.100,http://192.168.2.100,http://10.0.0.100
```

## Validation

After editing the `.env` file, validate your configuration:

1. **Check syntax**: Ensure no spaces around `=` signs
2. **Test deployment**: Run `docker-compose up -d`
3. **Check logs**: Run `docker-compose logs django`
4. **Test access**: Visit http://localhost

## Troubleshooting

### Common Issues

1. **Database Connection Failed**

   - Check `DB_PASSWORD` and `DB_ROOT_PASSWORD`
   - Ensure MySQL container is running: `docker-compose ps`

2. **Static Files Not Loading**

   - Run: `docker-compose exec django python manage.py collectstatic --noinput`
   - Check nginx logs: `docker-compose logs nginx`

3. **CSRF Token Errors**

   - Add your server's URL to `CSRF_TRUSTED_ORIGINS`
   - Include `http://` or `https://` prefix

4. **Email Not Working**
   - Check email credentials
   - Set `DISABLE_EMAIL_SENDING=True` to disable email features

### Environment Variable Reference

| Variable              | Required | Default             | Description            |
| --------------------- | -------- | ------------------- | ---------------------- |
| DJANGO_SECRET_KEY     | Yes      | -                   | Django secret key      |
| DJANGO_DEBUG          | Yes      | False               | Debug mode             |
| ALLOWED_HOSTS         | Yes      | localhost,127.0.0.1 | Allowed hostnames      |
| DB_ROOT_PASSWORD      | Yes      | -                   | MySQL root password    |
| DB_PASSWORD           | Yes      | -                   | Database user password |
| EMAIL_HOST            | No       | smtp.gmail.com      | Email server           |
| DISABLE_EMAIL_SENDING | No       | False               | Disable email features |


