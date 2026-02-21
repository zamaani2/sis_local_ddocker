# Django SchoolApp - Render Deployment Guide

This guide will walk you through deploying your Django SchoolApp to Render.com.

## Prerequisites

1. **Render Account**: Sign up at [render.com](https://render.com)
2. **Git Repository**: Your code should be in a Git repository (GitHub, GitLab, or Bitbucket)
3. **Domain (Optional)**: If you want a custom domain

## Step-by-Step Deployment Process

### 1. Prepare Your Repository

Ensure your repository contains all the necessary files:

- `render.yaml` - Render configuration file
- `requirements.txt` - Python dependencies
- `build.sh` - Build script
- `SchoolApp/settings_production.py` - Production settings
- `render.env.example` - Environment variables template

### 2. Create a Render Account and Connect Repository

1. Go to [render.com](https://render.com) and sign up
2. Click "New +" and select "Blueprint"
3. Connect your Git repository
4. Render will automatically detect the `render.yaml` file

### 3. Configure Services

The `render.yaml` file will create two services:

#### Web Service

- **Type**: Web Service
- **Name**: schoolapp-web
- **Environment**: Python
- **Plan**: Starter (Free tier)

#### Database Service

- **Type**: PostgreSQL
- **Name**: schoolapp-db
- **Plan**: Starter (Free tier)
- **Region**: Oregon

### 4. Set Environment Variables

In your Render dashboard, go to your web service and add these environment variables:

#### Required Variables

```
DJANGO_SECRET_KEY=your-super-secret-key-here
DJANGO_DEBUG=False
DJANGO_SETTINGS_MODULE=SchoolApp.settings_production
ALLOWED_HOSTS=your-app-name.onrender.com
CSRF_TRUSTED_ORIGINS=https://your-app-name.onrender.com
SITE_URL=https://your-app-name.onrender.com
ADMIN_EMAIL=admin@yourdomain.com
DISABLE_EMAIL_SENDING=True
```

#### Optional Variables (for email functionality)

```
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=465
EMAIL_USE_TLS=False
EMAIL_USE_SSL=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=your-email@gmail.com
```

#### Optional Variables (for Google OAuth)

```
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY=your-google-oauth2-key
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET=your-google-oauth2-secret
```

### 5. Deploy Your Application

1. Click "Apply" in the Blueprint view
2. Render will automatically:
   - Create the PostgreSQL database
   - Build your web service
   - Run migrations
   - Deploy your application

### 6. Post-Deployment Setup

#### Create a Superuser

1. Go to your web service in Render dashboard
2. Click on "Shell" tab
3. Run: `python manage.py createsuperuser --settings=SchoolApp.settings_production`
4. Follow the prompts to create an admin user

#### Access Your Application

- Your app will be available at: `https://your-app-name.onrender.com`
- Admin panel: `https://your-app-name.onrender.com/admin/`

### 7. Custom Domain (Optional)

1. In your Render dashboard, go to your web service
2. Click on "Settings" tab
3. Scroll down to "Custom Domains"
4. Add your domain and follow the DNS configuration instructions

## Important Notes

### Free Tier Limitations

- **Sleep Mode**: Free services sleep after 15 minutes of inactivity
- **Cold Start**: First request after sleep may take 30+ seconds
- **Database**: PostgreSQL free tier has limited storage and connections

### Production Considerations

- **Upgrade Plan**: Consider upgrading to paid plans for production use
- **Backup**: Set up regular database backups
- **Monitoring**: Monitor your application performance
- **SSL**: SSL certificates are automatically provided by Render

### Security

- **Secret Key**: Use a strong, unique secret key
- **Environment Variables**: Never commit sensitive data to your repository
- **HTTPS**: All traffic is automatically secured with HTTPS

## Troubleshooting

### Common Issues

#### Build Failures

- Check that all dependencies are in `requirements.txt`
- Ensure `build.sh` has execute permissions
- Verify Python version compatibility

#### Database Connection Issues

- Ensure PostgreSQL service is running
- Check database environment variables
- Verify database credentials

#### Static Files Not Loading

- Check `STATIC_ROOT` and `STATIC_URL` settings
- Ensure `collectstatic` runs during build
- Verify whitenoise configuration

#### Application Errors

- Check Render logs for detailed error messages
- Verify all environment variables are set
- Test locally with production settings

### Getting Help

1. **Render Documentation**: [render.com/docs](https://render.com/docs)
2. **Django Deployment**: [docs.djangoproject.com/en/stable/howto/deployment/](https://docs.djangoproject.com/en/stable/howto/deployment/)
3. **Render Community**: [community.render.com](https://community.render.com)

## File Structure

```
SchoolApp/
├── render.yaml                 # Render configuration
├── build.sh                    # Build script
├── requirements.txt            # Python dependencies
├── render.env.example          # Environment variables template
├── SchoolApp/
│   ├── settings.py            # Development settings
│   ├── settings_production.py  # Production settings
│   └── ...
└── ...
```

## Environment Variables Reference

| Variable                           | Required | Description                            |
| ---------------------------------- | -------- | -------------------------------------- |
| `DJANGO_SECRET_KEY`                | Yes      | Django secret key for security         |
| `DJANGO_DEBUG`                     | Yes      | Set to `False` for production          |
| `DJANGO_SETTINGS_MODULE`           | Yes      | Set to `SchoolApp.settings_production` |
| `ALLOWED_HOSTS`                    | Yes      | Your Render app URL                    |
| `CSRF_TRUSTED_ORIGINS`             | Yes      | Your Render app URL with https         |
| `SITE_URL`                         | Yes      | Your Render app URL                    |
| `ADMIN_EMAIL`                      | Yes      | Admin email for error notifications    |
| `DISABLE_EMAIL_SENDING`            | No       | Set to `True` to disable emails        |
| `EMAIL_HOST`                       | No       | SMTP server for emails                 |
| `EMAIL_PORT`                       | No       | SMTP port (usually 465)                |
| `EMAIL_USE_TLS`                    | No       | Use TLS for SMTP                       |
| `EMAIL_USE_SSL`                    | No       | Use SSL for SMTP                       |
| `EMAIL_HOST_USER`                  | No       | SMTP username                          |
| `EMAIL_HOST_PASSWORD`              | No       | SMTP password                          |
| `DEFAULT_FROM_EMAIL`               | No       | Default sender email                   |
| `SOCIAL_AUTH_GOOGLE_OAUTH2_KEY`    | No       | Google OAuth2 client ID                |
| `SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET` | No       | Google OAuth2 client secret            |

## Next Steps

After successful deployment:

1. **Test Your Application**: Verify all features work correctly
2. **Set Up Monitoring**: Monitor application performance and errors
3. **Configure Backups**: Set up regular database backups
4. **Update DNS**: If using custom domain, update DNS records
5. **Security Review**: Review security settings and access controls
6. **Performance Optimization**: Optimize for production load

Your Django SchoolApp is now successfully deployed on Render! 🎉
