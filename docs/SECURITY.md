# SchoolApp Security Guide

This document outlines security measures implemented in the SchoolApp project and provides guidelines for maintaining a secure application.

## Installation

1. **Windows Users**:

   - Run `install_security.bat` to set up security features
   - Follow the prompts to complete the installation

2. **Linux/Mac Users**:

   - Run `./install_security.sh` to set up security features
   - Follow the prompts to complete the installation

3. **Manual Installation**:
   - Install required packages: `pip install -r requirements.txt`
   - Run setup script: `python setup_security.py`
   - Apply migrations: `python manage.py migrate`
   - Run security check: `python security_check.py`

## Troubleshooting

1. **Missing Package Errors**:

   - If you see `ModuleNotFoundError: No module named 'X'`, run `pip install X`
   - For django-axes: `pip install django-axes`
   - For django-csp: `pip install django-csp`
   - After installing, run `python manage.py migrate axes`

2. **Database Connection Issues**:

   - Ensure your database credentials are correct in the `.env` file
   - Check that your database server is running
   - For MySQL, verify the port (default is 3306)

3. **Template Errors**:

   - Ensure all template directories exist: `mkdir -p templates/account`
   - Check that template files are in the correct location

4. **WSGI Application Error**:
   - If you see "WSGI application could not be loaded", check for missing packages
   - Make sure all middleware components are installed
   - Restart your server after installing packages

## Environment Setup

1. **Environment Variables**:

   - Copy `.env.example` to `.env` and update with your secure values
   - Never commit the `.env` file to version control
   - Use strong, unique values for all secrets

2. **Production Settings**:
   - Set `DJANGO_DEBUG=False` in production
   - Specify exact `ALLOWED_HOSTS` without wildcards
   - Use HTTPS in production with `SECURE_SSL_REDIRECT=True`

## Authentication Security

1. **Password Policies**:

   - Minimum length: 10 characters
   - Password similarity checks enabled
   - Common password checks enabled
   - Numeric password checks enabled

2. **Account Security**:

   - Account lockout after 5 failed attempts (using django-axes)
   - Lockout duration: 1 hour
   - Rate limiting on login and password reset attempts

3. **Session Security**:
   - Sessions expire after 1 hour of inactivity
   - Secure and HTTP-only cookies enabled
   - SameSite cookie policy set to 'Lax'

## Database Security

1. **Connection Security**:

   - Use environment variables for database credentials
   - Implement atomic requests to prevent partial transactions
   - Use connection health checks
   - Use strong, unique passwords for database users

2. **Query Security**:
   - Use Django's ORM to prevent SQL injection
   - Validate all user input
   - Implement proper data access controls

## Web Security Headers

1. **Content Security Policy (CSP)**:

   - Implemented using django-csp package
   - Restricts sources of executable scripts
   - Prevents XSS attacks
   - Configured in settings.py with CSP\_\* settings

2. **Other Security Headers**:
   - X-Content-Type-Options: nosniff
   - X-Frame-Options: DENY
   - HTTP Strict Transport Security (HSTS)
   - XSS Protection

## File Upload Security

1. **Upload Restrictions**:

   - Size limit: 5MB
   - Allowed extensions configured in settings
   - File permissions set to 0o644

2. **Storage Security**:
   - Use secure storage backends
   - Validate file content types
   - Scan uploads for malware when possible

## API Security

1. **Rate Limiting**:

   - Login: 5 attempts per minute
   - Password reset: 3 attempts per hour
   - Configure additional rate limits as needed

2. **Input Validation**:
   - Validate all API inputs
   - Use Django forms or serializers for validation
   - Sanitize HTML content with bleach

## Logging and Monitoring

1. **Security Logging**:

   - Security events logged to separate file
   - Critical security events emailed to admins
   - Log rotation enabled

2. **Audit Trail**:
   - Security audit enabled
   - Track user actions
   - Monitor for suspicious activity

## Regular Maintenance

1. **Dependency Updates**:

   - Regularly update all dependencies
   - Monitor security advisories
   - Run `pip list --outdated` regularly

2. **Security Scans**:
   - Run security scans on codebase
   - Use tools like Bandit for Python code
   - Consider using Django Security Check

## Incident Response

1. **Security Breaches**:
   - Document incident response procedures
   - Have contact information for security team
   - Know how to rotate compromised credentials

## Security Features Implemented

1. **Django-Axes**:

   - Tracks failed login attempts
   - Locks out users after too many failures
   - Provides custom lockout page
   - Uses IP address and user agent for lockout tracking (configured with AXES_LOCKOUT_PARAMETERS)
   - Configurable lockout duration and failure limits

2. **Content Security Policy**:

   - Implemented using django-csp package
   - Restricts which resources can be loaded
   - Prevents many XSS attacks
   - Configurable per resource type

3. **Rate Limiting**:

   - Prevents brute force attacks
   - Limits API abuse
   - Custom rate limit error pages

4. **Argon2 Password Hashing**:
   - Modern, secure password hashing algorithm
   - More resistant to brute force than PBKDF2
   - Configurable parameters for security/performance balance

## Additional Resources

- [Django Security Documentation](https://docs.djangoproject.com/en/5.0/topics/security/)
- [OWASP Top Ten](https://owasp.org/www-project-top-ten/)
- [Django Security Checklist](https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/)
- [Django-CSP Documentation](https://django-csp.readthedocs.io/)
