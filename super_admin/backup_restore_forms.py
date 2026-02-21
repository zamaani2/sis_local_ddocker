"""
Super Admin Backup and Restore Forms

This module provides forms for Super Admin backup and restore operations.
"""

from django import forms
from django.core.exceptions import ValidationError
from shs_system.models import SchoolInformation


class SuperAdminRestoreForm(forms.Form):
    """Form for restoring backup to an existing school"""
    
    target_school = forms.ModelChoiceField(
        queryset=SchoolInformation.objects.all().order_by('name'),
        empty_label="Select a school to restore to",
        help_text="Choose the school to restore the backup data to"
    )
    
    backup_file = forms.FileField(
        label="Backup File",
        help_text="Select the backup file to restore",
        widget=forms.FileInput(attrs={
            'accept': '.zip',
            'class': 'form-control'
        })
    )
    
    restore_database = forms.BooleanField(
        required=False,
        initial=True,
        label="Restore Database Records",
        help_text="Restore all database records (students, teachers, classes, etc.)"
    )
    
    restore_media_files = forms.BooleanField(
        required=False,
        initial=True,
        label="Restore Media Files",
        help_text="Restore images, documents, and other media files"
    )
    
    restore_static_files = forms.BooleanField(
        required=False,
        initial=False,
        label="Restore Static Files",
        help_text="Restore static files (usually not needed)"
    )
    
    backup_existing_data = forms.BooleanField(
        required=False,
        initial=True,
        label="Backup Existing Data",
        help_text="Create a backup of existing data before restoring (recommended)"
    )
    
    def clean_backup_file(self):
        """Validate the backup file"""
        backup_file = self.cleaned_data.get('backup_file')
        
        if not backup_file:
            raise ValidationError("Please select a backup file")
        
        # Check file extension
        if not backup_file.name.lower().endswith('.zip'):
            raise ValidationError("Backup file must be a ZIP file")
        
        # Check file size (limit to 500MB)
        if backup_file.size > 500 * 1024 * 1024:
            raise ValidationError("Backup file is too large (maximum 500MB)")
        
        return backup_file


class SuperAdminNewSchoolRestoreForm(forms.Form):
    """Form for creating a new school from backup"""
    
    backup_file = forms.FileField(
        label="Backup File",
        help_text="Select the backup file to create a new school from",
        widget=forms.FileInput(attrs={
            'accept': '.zip',
            'class': 'form-control'
        })
    )
    
    new_school_name = forms.CharField(
        max_length=200,
        label="New School Name",
        help_text="Enter the name for the new school",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter school name'
        })
    )
    
    new_school_domain = forms.CharField(
        max_length=100,
        label="School Domain",
        help_text="Enter the domain for the new school (e.g., 'myschool' or 'myschool.com')",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter domain name'
        })
    )
    
    admin_name = forms.CharField(
        max_length=100,
        label="Admin Name",
        help_text="Enter the full name of the school administrator",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter admin full name'
        })
    )
    
    admin_email = forms.EmailField(
        label="Admin Email",
        help_text="Enter the email address for the school administrator",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter admin email'
        })
    )
    
    restore_database = forms.BooleanField(
        required=False,
        initial=True,
        label="Restore Database Records",
        help_text="Restore all database records (students, teachers, classes, etc.)"
    )
    
    restore_media_files = forms.BooleanField(
        required=False,
        initial=True,
        label="Restore Media Files",
        help_text="Restore images, documents, and other media files"
    )
    
    restore_static_files = forms.BooleanField(
        required=False,
        initial=False,
        label="Restore Static Files",
        help_text="Restore static files (usually not needed)"
    )
    
    def clean_backup_file(self):
        """Validate the backup file"""
        backup_file = self.cleaned_data.get('backup_file')
        
        if not backup_file:
            raise ValidationError("Please select a backup file")
        
        # Check file extension
        if not backup_file.name.lower().endswith('.zip'):
            raise ValidationError("Backup file must be a ZIP file")
        
        # Check file size (limit to 500MB)
        if backup_file.size > 500 * 1024 * 1024:
            raise ValidationError("Backup file is too large (maximum 500MB)")
        
        return backup_file
    
    def clean_new_school_name(self):
        """Validate the new school name"""
        school_name = self.cleaned_data.get('new_school_name')
        
        if not school_name:
            raise ValidationError("Please enter a school name")
        
        # Check if school name already exists
        if SchoolInformation.objects.filter(name__iexact=school_name).exists():
            raise ValidationError("A school with this name already exists")
        
        return school_name
    
    def clean_new_school_domain(self):
        """Validate the new school domain"""
        domain = self.cleaned_data.get('new_school_domain')
        
        if not domain:
            raise ValidationError("Please enter a domain")
        
        # Process domain name
        if "." in domain:
            domain_value = domain
        else:
            domain_value = f"{domain}.localhost"
        
        # Check if domain already exists
        from super_admin.models import SchoolDomain
        if SchoolDomain.objects.filter(domain=domain_value).exists():
            raise ValidationError("A school with this domain already exists")
        
        return domain
    
    def clean_admin_email(self):
        """Validate the admin email"""
        email = self.cleaned_data.get('admin_email')
        
        if not email:
            raise ValidationError("Please enter an admin email")
        
        # Check if email already exists
        from shs_system.models import User
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("A user with this email already exists")
        
        return email
