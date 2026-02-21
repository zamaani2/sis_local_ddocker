# Email Configuration System

## Overview

This document explains the changes made to the email configuration system in the SchoolApp platform. The email configuration has been moved from individual schools to a centralized super admin control, ensuring consistent email delivery across the platform.

## Changes Made

1. **New SystemEmailConfig Model**
   - Created a new model in the `super_admin` app to store email configuration settings
   - Supports both OAuth2 (Google) and SMTP email configurations
   - Allows for multiple configurations with one active at a time

2. **Super Admin Interface**
   - Added a new section in the super admin interface to manage email configurations
   - Provides ability to create, edit, test, and delete email configurations
   - Includes a migration tool to move existing OAuth credentials to the new system

3. **Updated Email Sending Logic**
   - Modified the email sending functions to use the centralized configuration
   - Maintains backward compatibility with legacy methods as fallback
   - Improved error handling and logging

## How It Works

The system now follows this hierarchy for sending emails:

1. First tries to use the active SystemEmailConfig from the super admin app
2. If that fails or doesn't exist, falls back to legacy OAuth methods (if available)
3. As a last resort, uses standard Django email settings

## Migration Instructions

To migrate existing OAuth credentials to the new system:

1. **Option 1: Use the Super Admin Interface**
   - Log in as a super admin
   - Go to Settings > Email Configuration
   - If legacy credentials are detected, a migration button will appear
   - Click "Migrate Existing Credentials" to transfer them to the new system

2. **Option 2: Use the Management Command**
   - Run the following command:

   python manage.py migrate_email_config

## Setting Up a New Email Configuration

### OAuth2 (Google) Configuration

1. Log in as a super admin
2. Go to Settings > Email Configuration
3. Click "Create New Configuration"
4. Select "OAuth2 (Google)" as the service type
5. Fill in the required fields:
   - Client ID
   - Client Secret
   - Refresh Token
   - From Email
6. Save the configuration

### SMTP Configuration

1. Log in as a super admin
2. Go to Settings > Email Configuration
3. Click "Create New Configuration"
4. Select "SMTP Server" as the service type
5. Fill in the required fields:
   - SMTP Host
   - SMTP Port
   - SMTP Username
   - SMTP Password
   - From Email
6. Save the configuration

## Testing the Configuration

After creating or updating an email configuration, you can test it by:

1. Checking the "Test connection after saving" option when creating/editing
2. Clicking the "Test" button next to an existing configuration
3. Creating a new user, which will automatically send a test email

## Troubleshooting

### Common SMTP Issues

If you encounter SMTP connection issues:

#### "Connection unexpectedly closed" Error

This usually indicates one of the following issues:

1. **Incorrect Password**:
   - For Gmail, you need to use an App Password instead of your regular password
   - Go to Google Account > Security > 2-Step Verification > App passwords
   - Create a new app password for "Mail" and use that instead

2. **Port/SSL/TLS Configuration Mismatch**:
   - For Gmail:
     - Port 465 requires SSL enabled, TLS disabled
     - Port 587 requires TLS enabled, SSL disabled
   - Make sure your configuration matches one of these combinations

3. **Network/Firewall Issues**:
   - Check if your network blocks outgoing connections on ports 465 or 587
   - Try from a different network if possible

4. **Gmail Security Settings**:
   - Check if your Google account has security restrictions
   - Look for security alerts in your Gmail account

#### "Authentication Failed" Error

1. **Check Username and Password**:
   - Verify the email address is correct
   - For Gmail, use an App Password as mentioned above

2. **Account Security Settings**:
   - Make sure "Less secure app access" is enabled (for older Gmail accounts)
   - Check if your account requires 2FA

#### "Timeout" Error

1. **Network Connectivity**:
   - Check your internet connection
   - Verify the SMTP server hostname is correct

2. **Server Availability**:
   - The email server might be temporarily down
   - Try again later or contact your email provider

### Testing SMTP Connection Manually

You can test your SMTP connection manually using Python:

```python
import smtplib

# Replace with your settings
smtp_host = "smtp.gmail.com"
smtp_port = 465
username = "your-email@gmail.com"
password = "your-app-password"
use_ssl = True

try:
    if use_ssl:
        server = smtplib.SMTP_SSL(smtp_host, smtp_port)
    else:
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()
    
    server.login(username, password)
    print("Connection successful!")
    server.quit()
except Exception as e:
    print(f"Connection failed: {str(e)}")
```

### Checking Debug Logs

The system now creates detailed logs for email-related issues:

1. Check the console output for error messages
2. Look at the `debug.log` file in the project root directory

If emails are not being sent:

1. Check that a configuration is marked as active
2. Verify the credentials are correct
3. Test the configuration using the test button
4. Check the server logs for any error messages

## Technical Details

The implementation includes:

- `SystemEmailConfig` model in `super_admin/models.py`
- Email configuration views in `super_admin/views.py`
- Templates for managing configurations
- Migration command in `super_admin/management/commands/migrate_email_config.py`
- Updated email sending functions in `shs_system/views/user_management.py`
