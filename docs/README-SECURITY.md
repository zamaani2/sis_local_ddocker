# SchoolApp Security Setup

This guide provides step-by-step instructions for setting up the security features in the SchoolApp project.

## Quick Setup

### Windows Users

1. Run the installation script:
   ```
   install_security.bat
   ```

2. Apply database migrations:
   ```
   python manage.py migrate
   ```

3. Run the security check:
   ```
   python security_check.py
   ```

### Linux/Mac Users

1. Run the installation script:
   ```
   chmod +x install_security.sh
   ./install_security.sh
   ```

2. Apply database migrations:
   ```
   python manage.py migrate
   ```

3. Run the security check:
   ```
   python security_check.py
   ```

## Manual Setup

If you prefer to set up security features manually, follow these steps:

1. Install required packages:
   ```
   pip install -r requirements.txt
   ```

   If you encounter package errors, install them individually:
   ```
   pip install django-axes
   pip install django-csp
   ```

2. Create a `.env` file with your database credentials and other settings:
   ```
   # Copy the example file
   cp .env.example .env
   
   # Edit the file with your settings
   # nano .env or use any text editor
   ```

3. Apply database migrations:
   ```
   python manage.py migrate
   python manage.py migrate axes
   ```

4. Create necessary directories:
   ```
   mkdir -p logs
   mkdir -p templates/account
   ```

5. Run the security check:
   ```
   python security_check.py
   ```

## Troubleshooting

### Common Issues

1. **ModuleNotFoundError: No module named 'X'**
   - Install the missing package: `pip install X`
   - For django-axes: `pip install django-axes`
   - For django-csp: `pip install django-csp`
   - After installing, run migrations if needed: `python manage.py migrate axes`

2. **Database Connection Issues**
   - Check your database credentials in the `.env` file
   - Ensure your database server is running
   - For MySQL, verify the port (default is 3306)

3. **Template Errors**
   - Make sure template directories exist: `mkdir -p templates/account`
   - Verify template files are in the correct location

4. **WSGI Application Error**
   - If you see "WSGI application could not be loaded", check for missing packages
   - Install all required packages listed in requirements.txt
   - Restart your server after installing packages

## Security Features

The SchoolApp includes the following security features:

1. **Account Protection**
   - Login attempt tracking and lockout (django-axes)
     - Configured with AXES_LOCKOUT_PARAMETERS to track by IP address and user agent
     - Note: AXES_USE_USER_AGENT is deprecated; use AXES_LOCKOUT_PARAMETERS instead
   - Rate limiting for login and password reset
   - Argon2 password hashing (stronger than PBKDF2)

2. **Web Security**
   - Content Security Policy (CSP) via django-csp
   - Secure cookies and session management
   - HTTPS enforcement in production
   - Protection against XSS, CSRF, and clickjacking

3. **Data Security**
   - Environment variables for sensitive information
   - Secure file upload handling
   - Database connection security

For more detailed information, please refer to the [SECURITY.md](SECURITY.md) file. 