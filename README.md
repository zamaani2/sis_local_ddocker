# SchoolApp - Comprehensive School Management System

A modern, feature-rich school management system built with Django, designed to streamline academic operations, student management, assessment tracking, and administrative tasks for educational institutions.

## 🎯 Overview

SchoolApp is a multi-tenant school management system that provides comprehensive solutions for managing all aspects of school operations. From student enrollment to report card generation, the system offers a complete suite of tools for administrators, teachers, and students.

## ✨ Key Features

### 🎓 Academic Management

- **Academic Year & Term Management**: Flexible academic calendar with customizable terms
- **Class & Subject Management**: Organize classes, subjects, and learning areas
- **Student Enrollment**: Comprehensive student registration with bulk import capabilities
- **Class Assignment**: Flexible class assignment and roster management

### 📊 Assessment & Grading

- **Enhanced Score Entry**: Individual score components (Assignments, Class Tests, Projects, Group Work)
- **Real-time Calculations**: Automatic score calculation, grading, and position ranking
- **Multiple Assessment Types**: Regular assessments, mock exams, and terminal reports
- **Configurable Grading System**: Customizable grading scales and performance requirements

### 📝 Report Generation

- **Individual Report Cards**: Detailed student performance reports
- **Bulk Report Generation**: Generate reports for entire classes or batches
- **PDF Export**: Professional report cards with school branding
- **Print-ready Formats**: Optimized for printing and digital distribution

### 👥 User Management

- **Role-Based Access Control**: Admin, Teacher, Student, and Super Admin roles
- **Multi-tenant Architecture**: School-specific data isolation and security
- **Google OAuth2 Integration**: Secure authentication with Google accounts
- **User Activity Monitoring**: Track and monitor user activities

### 📦 Backup & Restore

- **School-Specific Backups**: Independent backup for each school
- **Flexible Storage**: Save backups anywhere on your system
- **Restore Options**: Merge, Replace, or Create New school from backups
- **Media File Support**: Optional inclusion of images and documents

### 🎨 Additional Features

- **Teacher Activity Monitoring**: Track teacher engagement and activity
- **Student Promotion Management**: Handle student promotions and graduations
- **Alumni Management**: Maintain records of graduated students
- **Department & Form Management**: Organize school structure
- **Authority Signatures**: Customizable report card signatures
- **Multiple Themes**: Green, Red, Purple, and Academic Pro themes

## 🛠️ Technology Stack

### Backend

- **Framework**: Django 5.0.3
- **Language**: Python 3.11+
- **Database**: PostgreSQL 15
- **WSGI Server**: Gunicorn
- **Web Server**: Nginx (Reverse Proxy)

### Frontend

- **CSS Framework**: Bootstrap 5.3.3
- **JavaScript Libraries**:
  - jQuery 3.7.1
  - DataTables 1.13.7
  - SweetAlert2 11.7.32
  - FontAwesome 6.5.1
  - Select2 4.1.0

### Infrastructure

- **Containerization**: Docker & Docker Compose
- **Static Files**: WhiteNoise
- **PDF Generation**: WeasyPrint, ReportLab
- **Excel Processing**: openpyxl, xlsxwriter
- **Image Processing**: Pillow

### Security Features

- **Authentication**: Django Axes (Brute force protection)
- **Session Security**: Django Session Security
- **Rate Limiting**: Django Ratelimit
- **CSP**: Content Security Policy
- **Password Hashing**: Argon2
- **CORS Protection**: Django CORS Headers

## 📋 Prerequisites

- Python 3.11 or higher
- PostgreSQL 15 or higher
- pip (Python package manager)
- Git

### Optional (Recommended)

- Docker & Docker Compose (for containerized deployment)
- Redis (for caching)
- Celery (for background tasks)

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/zamaani2/SIS.git
cd SchoolApp
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment Configuration

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit `.env` and configure:

- Database settings (PostgreSQL)
- Secret keys
- Debug mode
- Allowed hosts
- Email configuration (for Google OAuth2)

### 5. Database Setup

```bash
# Create database migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

### 6. Collect Static Files

```bash
python manage.py collectstatic --noinput
```

### 7. Run Development Server

```bash
python manage.py runserver
```

Visit `http://localhost:8000` in your browser.

## ⚙️ Configuration

### Google OAuth2 Setup

1. **Create Google Cloud Project**:

   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Navigate to "APIs & Services" > "Credentials"

2. **Configure OAuth Consent Screen**:

   - Go to "OAuth consent screen"
   - Select "External" user type
   - Fill in app information
   - Add required scopes:
     - `https://www.googleapis.com/auth/userinfo.email`
     - `https://www.googleapis.com/auth/userinfo.profile`
     - `https://www.googleapis.com/auth/gmail.send`

3. **Create OAuth Client ID**:

   - Select "Web application"
   - Add JavaScript origins: `http://localhost:8000`
   - Add redirect URIs:
     - `http://localhost:8000/social-auth/complete/google-oauth2/`
     - `http://localhost:8000/login/`

4. **Configure Settings**:
   Add to your `.env` file:
   ```
   SOCIAL_AUTH_GOOGLE_OAUTH2_KEY=your-client-id
   SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET=your-client-secret
   ```

### Database Configuration

Configure PostgreSQL connection in `.env`:

```
DATABASE_URL=postgresql://user:password@localhost:5432/schoolapp_db
```

## 📚 Usage Guide

### For Administrators

1. **Login** with admin credentials
2. **Configure School Information**: Set up school details, logos, signatures
3. **Create Academic Year**: Set up academic years and terms
4. **Manage Classes**: Create classes and assign teachers
5. **Enroll Students**: Add students individually or bulk import
6. **Assign Classes**: Assign students to classes
7. **Configure Grading**: Set up grading systems and assessment weights

### For Teachers

1. **Login** with teacher credentials
2. **View Classes**: Access assigned classes and students
3. **Enter Scores**: Use enhanced score entry for assessments
4. **Generate Reports**: Create and print student report cards
5. **Monitor Performance**: Track student progress and performance

### For Students

1. **Login** with student credentials
2. **View Dashboard**: Access personal academic information
3. **View Reports**: Download and view report cards
4. **Track Performance**: Monitor grades and academic progress

## 🐳 Deployment

### Docker Deployment

#### Using Docker Compose

```bash
# Build and start containers
docker-compose up -d

# View logs
docker-compose logs -f

# Stop containers
docker-compose down
```

#### Manual Docker Build

```bash
# Build image
docker build -t schoolapp .

# Run container
docker run -d -p 8000:8000 --env-file .env schoolapp
```

### Fly.io Deployment

Deploy to Fly.io cloud platform:

```bash
# Install Fly.io CLI
curl -L https://fly.io/install.sh | sh

# Login to Fly.io
fly auth login

# Launch the app (first time)
fly launch

# Deploy
fly deploy
```

**See [Fly.io Deployment Guide](docs/FLY_IO_DEPLOYMENT_GUIDE.md) for detailed instructions.**

### Render Deployment

Deploy to Render:

```bash
# Connect your GitHub repository to Render
# Configure build command: ./build.sh
# Configure start command: gunicorn --bind 0.0.0.0:$PORT SchoolApp.wsgi:application
```

**See [Render Deployment Guide](docs/RENDER_DEPLOYMENT_GUIDE.md) for detailed instructions.**

## 📖 Documentation

Comprehensive documentation is available in the `docs/` directory:

- **[System Architecture & Deployment](docs/SYSTEM_ARCHITECTURE_DEPLOYMENT.md)**: Complete architecture overview
- **[Performance Analysis](docs/PERFORMANCE_ANALYSIS_COMPREHENSIVE.md)**: Performance benchmarks and optimization
- **[Backup & Restore System](docs/BACKUP_RESTORE_SYSTEM.md)**: Backup/restore operations guide
- **[Enhanced Score Entry](docs/ENHANCED_SCORE_ENTRY_SYSTEM.md)**: Score entry system documentation
- **[Fly.io Deployment Guide](docs/FLY_IO_DEPLOYMENT_GUIDE.md)**: Fly.io cloud deployment instructions
- **[Render Deployment Guide](docs/RENDER_DEPLOYMENT_GUIDE.md)**: Render deployment instructions
- **[General Deployment Guide](docs/DEPLOYMENT_GUIDE.md)**: Production deployment instructions

## 🔒 Security Features

- Multi-tenant data isolation
- Role-based access control (RBAC)
- CSRF protection
- SQL injection prevention
- XSS protection
- Rate limiting for login attempts
- Brute force protection
- Session security
- Content Security Policy (CSP)
- Password strength requirements

## 📊 System Capabilities

### Current Performance

- **Student Records**: 1,000-2,000 students comfortably
- **Concurrent Users**: 50-100 users without issues
- **Bulk Operations**: 50-100 records per batch
- **Response Time**: <2 seconds for most operations

### Recommended Infrastructure

- **Small (50-100 users)**: $90-170/month
- **Medium (100-300 users)**: $190-380/month
- **Large (300+ users)**: $400-1050/month

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is proprietary software. All rights reserved.

## 🆘 Support

For support and inquiries:

- **Documentation**: Check the `docs/` directory for detailed guides
- **Issues**: Open an issue on GitHub for bug reports or feature requests

## 📞 Contact

Project Repository: [https://github.com/zamaani2/SIS](https://github.com/zamaani2/SIS)

---

**SchoolApp** - Empowering Educational Excellence Through Technology
