from django.contrib import admin
from .forms import UserCreationForm

# Register your models here.
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    User,
    AcademicYear,
    Term,
    Form,
    LearningArea,
    Department,
    Teacher,
    Student,
    Class,
    StudentClass,
    Subject,
    TeacherSubjectAssignment,
    ClassSubject,
    Assessment,

    MockExam,

    AttendanceRecord,
    ClassTeacher,
    PerformanceRequirement,
    OAuthCredentialStore,
    ScheduledReminder,
    ReminderLog,
    ScoringConfiguration,
    ArchivedStudent,
    AcademicYearTemplate,

    GradingSystem,
    Notification,
    ReportCard,
    BackupOperation,
    RestoreOperation,
    BackupSettings,

)

# Custom User Admin
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User


class CustomUserAdmin(UserAdmin):
    add_form = UserCreationForm
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "email",
                    "role",
                    "full_name",
                    "password1",
                    "password2",
                    "teacher_profile",
                    "student_profile",
                ),
            },
        ),
        (
            "Permissions",
            {
                "classes": ("wide",),
                "fields": ("is_active", "is_staff", "is_superuser", "is_superadmin"),
            },
        ),
    )
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (
            "Personal Info",
            {
                "fields": (
                    "full_name",
                    "email",
                    "role",
                    "teacher_profile",
                    "student_profile",
                )
            },
        ),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "is_superadmin")},
        ),
        ("Important Dates", {"fields": ("last_login", "date_joined")}),
    )
    list_display = (
        "username",
        "email",
        "role",
        "full_name",
        "is_active",
        "is_superadmin",
    )
    search_fields = ("username", "email", "full_name")
    list_filter = ("role", "is_active", "is_staff", "is_superadmin")

    @admin.display(description="Role")
    def role_display(self, obj):
        return obj.get_role_display()

    list_display = (
        "username",
        "email",
        "role_display",
        "full_name",
        "is_active",
        "is_superadmin",
    )


admin.site.register(User, CustomUserAdmin)


# Academic Year Admin
@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ("name", "start_date", "end_date", "is_current")
    list_filter = ("is_current",)
    search_fields = ("name",)


# Term Admin
@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    list_display = (
        "academic_year",
        "get_term_number_display",
        "start_date",
        "end_date",
        "is_current",
    )
    list_filter = ("academic_year", "is_current")
    search_fields = ("academic_year__name",)


# Form Admin
@admin.register(Form)
class FormAdmin(admin.ModelAdmin):
    list_display = ("form_number", "name", "description")
    search_fields = ("name", "description")
    ordering = ("form_number",)


# LearningArea Admin
@admin.register(LearningArea)
class LearningAreaAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "description")
    search_fields = ("code", "name", "description")
    ordering = ("name",)


# Department Admin
@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "head_of_department", "description")
    search_fields = ("name", "code", "description")
    list_filter = ("name",)


# Teacher Admin
@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "staff_id",
        "department",
        "contact_number",
        "get_username",
        "get_initial_password",
    )
    search_fields = ("full_name", "staff_id")
    list_filter = ("department",)
    readonly_fields = ("get_username", "get_initial_password")

    def get_username(self, obj):
        user = User.objects.filter(teacher_profile=obj).first()
        return user.username if user else "-"

    get_username.short_description = "Username"

    def get_initial_password(self, obj):
        if hasattr(obj, "temp_password"):
            return obj.temp_password
        return "(Hidden)"

    get_initial_password.short_description = "Initial Password"


# Student Admin
@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "admission_number",
        "gender",
        "parent_contact",
        "admission_date",
        "form",
        "learning_area",
        "get_username",
        "get_initial_password",
    )
    search_fields = ("full_name", "admission_number")
    list_filter = ("gender", "admission_date", "form", "learning_area")
    readonly_fields = ("get_username", "get_initial_password")

    def get_username(self, obj):
        user = User.objects.filter(student_profile=obj).first()
        return user.username if user else "-"

    get_username.short_description = "Username"

    def get_initial_password(self, obj):
        if hasattr(obj, "temp_password"):
            return obj.temp_password
        return "(Hidden)"

    get_initial_password.short_description = "Initial Password"


# Class Admin
@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = (
        "class_id",
        "name",
        "form",
        "learning_area",
        "academic_year",
    )
    list_filter = ("academic_year",)
    search_fields = ("name", "class_id")


# StudentClass Admin
@admin.register(StudentClass)
class StudentClassAdmin(admin.ModelAdmin):
    list_display = ("student", "assigned_class", "date_assigned", "is_active")
    list_filter = ("is_active", "date_assigned")
    search_fields = ("student__user__full_name", "assigned_class__name")


# Subject Admin
@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("subject_code", "subject_name", "learning_area", "department")
    list_filter = ("department",)
    search_fields = ("subject_code", "subject_name")


# TeacherSubjectAssignment Admin
@admin.register(TeacherSubjectAssignment)
class TeacherSubjectAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "assignment_id",
        "teacher",
        "subject",
        "class_assigned",
        "academic_year",
        "is_active",
    )
    list_filter = ("academic_year", "is_active")
    search_fields = (
        "teacher__user__full_name",
        "subject__subject_name",
        "class_assigned__name",
    )


# ClassTeacher Admin
@admin.register(ClassTeacher)
class ClassTeacherAdmin(admin.ModelAdmin):
    list_display = (
        "teacher",
        "class_assigned",
        "academic_year",
        "date_assigned",
        "is_active",
    )
    list_filter = ("academic_year", "is_active", "teacher")
    search_fields = ("teacher__full_name", "class_assigned__name")
    raw_id_fields = (
        "teacher",
        "class_assigned",
    )  # For better performance with many records
    date_hierarchy = "date_assigned"

    def get_queryset(self, request):
        # Order by active status, then academic year, then class
        return (
            super()
            .get_queryset(request)
            .order_by("-is_active", "-academic_year__name", "class_assigned__name")
        )


# ClassSubject Admin
@admin.register(ClassSubject)
class ClassSubjectAdmin(admin.ModelAdmin):
    list_display = (
        "class_subject_id",
        "subject",
        "class_name",
        "academic_year",
        "school",

        "is_active",
        "date_assigned",
        "assigned_by",

    )
    list_filter = (
        "academic_year",
        "school",

        "is_active",
        "date_assigned",
    )
    search_fields = ("subject__subject_name", "class_name__name", "assigned_by__username")
    readonly_fields = ("class_subject_id", "date_assigned")
    date_hierarchy = "date_assigned"
    
    fieldsets = (
        ("Assignment Information", {
            "fields": ("subject", "class_name", "academic_year", "school")
        }),
        ("Status & Tracking", {
            "fields": ("is_active", "date_assigned", "assigned_by")
        }),
        ("System Information", {
            "fields": ("class_subject_id",),
            "classes": ("collapse",)
        }),
    )
    
    def get_queryset(self, request):
        """Filter by school for non-superusers and order by active status"""
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            if hasattr(request.user, "school") and request.user.school:
                qs = qs.filter(school=request.user.school)
            else:
                qs = qs.none()
        return qs.order_by("-is_active", "-date_assigned")
    
    def save_model(self, request, obj, form, change):
        """Set assigned_by when creating new assignments"""
        if not change:  # If creating new assignment
            obj.assigned_by = request.user
        super().save_model(request, obj, form, change)


# Assessment Admin
@admin.register(MockExam)
class MockExamAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "exam_date",
        "academic_year",
        "school",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active", "academic_year", "exam_date", "school")
    search_fields = ("name", "description")
    date_hierarchy = "exam_date"
    fieldsets = (
        ("Basic Information", {
            "fields": ("name", "exam_date", "academic_year", "school", "is_active")
        }),
        ("Details", {
            "fields": ("description", "created_by")
        }),
    )
    readonly_fields = ("created_at", "updated_at")
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Filter by school for non-superusers
        if hasattr(request.user, 'school') and request.user.school:
            return qs.filter(school=request.user.school)
        return qs.none()
    
    def save_model(self, request, obj, form, change):
        if not change:  # Only set created_by on creation
            obj.created_by = request.user
        super().save_model(request, obj, form, change)



@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = (
        "assessment_id",
        "student",
        "class_subject",
        "assessment_type",

        "mock_exam",

        "total_score",
        "grade",
        "remarks",
        "date_recorded",
    )

    list_filter = ("assessment_type", "position", "date_recorded", "school", "mock_exam")
    search_fields = ("student__user__full_name", "class_subject__subject__subject_name")
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Filter by school for non-superusers
        if hasattr(request.user, 'school') and request.user.school:
            return qs.filter(school=request.user.school)
        return qs



# AttendanceRecord Admin
@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ("student", "date", "is_present", "reason", "term")
    list_filter = ("is_present", "reason", "term")
    search_fields = ("student__user__full_name",)


from django.contrib import admin
from django.utils.html import format_html
from django.forms import ModelForm, ModelChoiceField
from django import forms
from .models import (
    SchoolInformation,
    SchoolAuthoritySignature,
    StudentTermRemarks,
    Term,
    AcademicYear,
)


class SchoolAuthoritySignatureInline(admin.TabularInline):
    model = SchoolAuthoritySignature
    extra = 1
    fields = (
        "authority_type",
        "name",
        "title",
        "signature",
        "is_active",
        "custom_title",
    )

    def get_queryset(self, request):
        # Order signatures by authority type for better organization
        return super().get_queryset(request).order_by("authority_type")


class SchoolInformationAdminForm(ModelForm):
    class Meta:
        model = SchoolInformation
        fields = "__all__"

    # Override the current_term field to make it dynamically dependent on academic_year
    current_term = ModelChoiceField(
        queryset=Term.objects.all(), required=False, label="Current Term"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Get the current instance if it exists
        instance = kwargs.get("instance")

        # If we have an academic year selection from POST data
        if self.data.get("current_academic_year"):
            try:
                academic_year_id = int(self.data.get("current_academic_year"))
                # Filter terms to only show ones related to the selected academic year
                self.fields["current_term"].queryset = Term.objects.filter(
                    academic_year_id=academic_year_id
                )
            except (ValueError, TypeError):
                pass

        # If editing existing instance, filter terms by its academic year
        elif instance and instance.current_academic_year:
            self.fields["current_term"].queryset = Term.objects.filter(
                academic_year=instance.current_academic_year
            )
        else:
            # If no academic year is selected, show no terms initially
            self.fields["current_term"].queryset = Term.objects.none()

        # Filter academic years to exclude archived ones
        if hasattr(self, "fields") and "current_academic_year" in self.fields:
            # Get the current queryset and filter out archived academic years
            current_queryset = self.fields["current_academic_year"].queryset
            if current_queryset:
                self.fields["current_academic_year"].queryset = current_queryset.filter(
                    is_archived=False
                )

    def clean(self):
        cleaned_data = super().clean()
        current_academic_year = cleaned_data.get("current_academic_year")
        current_term = cleaned_data.get("current_term")

        # Validate that the selected term belongs to the selected academic year
        if current_academic_year and current_term:
            if current_term.academic_year != current_academic_year:
                self.add_error(
                    "current_term",
                    "This term doesn't belong to the selected academic year.",
                )

        return cleaned_data


@admin.register(SchoolInformation)
class SchoolInformationAdmin(admin.ModelAdmin):
    form = SchoolInformationAdminForm
    list_display = (
        "name",
        "is_active",
        "current_academic_year",
        "current_term",
        "last_updated",
    )
    list_filter = ("is_active",)
    search_fields = ("name", "short_name", "school_code")
    readonly_fields = ("date_created", "last_updated", "logo_preview", "stamp_preview")
    inlines = [SchoolAuthoritySignatureInline]

    fieldsets = (
        (
            "Basic Information",
            {"fields": ("name", "short_name", "school_code", "is_active")},
        ),
        (
            "Contact Details",
            {"fields": ("address", "postal_code", "phone_number", "email", "website")},
        ),
        (
            "Visual Elements",
            {"fields": ("logo", "logo_preview", "school_stamp", "stamp_preview")},
        ),
        ("School Identity", {"fields": ("motto", "vision", "mission")}),
        (
            "Report Settings",
            {
                "fields": (
                    "report_header",
                    "report_footer",
                    "grading_system_description",
                )
            },
        ),
        (
            "Current Settings",
            {
                "fields": ("current_academic_year", "current_term"),
                "description": "Selecting an academic year will filter the terms to only show those from that year.",
            },
        ),
        (
            "Metadata",
            {
                "fields": ("created_by", "updated_by", "date_created", "last_updated"),
                "classes": ("collapse",),
            },
        ),
    )

    class Media:
        # Add JavaScript to handle dynamic filtering of terms when academic year changes
        js = ("admin/dynamic_term_filter.js",)

    def logo_preview(self, obj):
        if obj.logo:
            return format_html(
                '<img src="{}" style="max-height: 100px; max-width: 300px;" />',
                obj.logo.url,
            )
        return "No logo uploaded"

    logo_preview.short_description = "Logo Preview"

    def stamp_preview(self, obj):
        if obj.school_stamp:
            return format_html(
                '<img src="{}" style="max-height: 100px; max-width: 300px;" />',
                obj.school_stamp.url,
            )
        return "No stamp uploaded"

    stamp_preview.short_description = "Stamp Preview"

    def save_model(self, request, obj, form, change):
        if not change:  # If creating a new object
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(SchoolAuthoritySignature)
class SchoolAuthoritySignatureAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "display_title",
        "authority_type",
        "school",
        "is_active",
        "signature_preview",
    )
    list_filter = ("authority_type", "is_active", "school")
    search_fields = ("name", "title", "custom_title")
    readonly_fields = ("signature_preview",)

    fieldsets = (
        (
            "Authority Information",
            {"fields": ("school", "authority_type", "name", "title", "custom_title")},
        ),
        ("Signature", {"fields": ("signature", "signature_preview", "is_active")}),
    )

    def signature_preview(self, obj):
        if obj.signature:
            return format_html(
                '<img src="{}" style="max-height: 100px; max-width: 300px;" />',
                obj.signature.url,
            )
        return "No signature uploaded"

    signature_preview.short_description = "Signature Preview"

    def display_title(self, obj):
        return obj.display_title()

    display_title.short_description = "Title"


@admin.register(StudentTermRemarks)
class StudentTermRemarksAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "class_assigned",
        "term",
        "academic_year",
        "attendance_summary",
        "last_updated",
    )
    list_filter = ("academic_year", "term", "class_assigned")
    search_fields = (
        "student__full_name",
        "student__admission_number",
        "general_remarks",
    )
    readonly_fields = ("date_created", "last_updated", "class_teacher")

    fieldsets = (
        (
            "Student Information",
            {
                "fields": (
                    "student",
                    "academic_year",
                    "term",
                    "class_assigned",
                    "class_teacher",
                )
            },
        ),
        (
            "Attendance",
            {
                "fields": (
                    "auto_calculate_attendance",
                    "days_present",
                    "days_absent",
                    "total_school_days",
                )
            },
        ),
        (
            "Remarks",
            {
                "fields": (
                    "interest_remarks",
                    "conduct_remarks",
                    "attitude_remarks",
                    "general_remarks",
                )
            },
        ),
        (
            "Metadata",
            {"fields": ("date_created", "last_updated"), "classes": ("collapse",)},
        ),
    )

    def get_queryset(self, request):
        # Use a custom queryset to avoid querying the class_teacher field directly
        return super().get_queryset(request)

    def attendance_summary(self, obj):
        percentage = obj.attendance_percentage()
        return f"{obj.days_present}/{obj.total_school_days} ({percentage}%)"

    attendance_summary.short_description = "Attendance"

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields["days_present"].widget.attrs["class"] = "attendance-field"
        form.base_fields["days_absent"].widget.attrs["class"] = "attendance-field"
        form.base_fields["total_school_days"].widget.attrs["class"] = "attendance-field"

        # Disable class_teacher field
        if "class_teacher" in form.base_fields:
            form.base_fields["class_teacher"].disabled = True

        return form

    def save_model(self, request, obj, form, change):
        # If creating a new record, try to get the class teacher
        if not change and not obj.class_teacher_id:
            # Find active class teacher for this class and academic year
            class_teacher = ClassTeacher.objects.filter(
                class_assigned=obj.class_assigned,
                academic_year=obj.academic_year,
                is_active=True,
            ).first()

            if class_teacher:
                obj.class_teacher = class_teacher.teacher

        super().save_model(request, obj, form, change)

    class Media:
        js = (
            "js/student_term_remarks.js",
        )  # Add custom JS to handle the auto_calculate toggle


@admin.register(PerformanceRequirement)
class PerformanceRequirementAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "min_average_score_for_promotion",
        "calculation_method",
        "max_failed_subjects",
        "is_active",
    )
    list_filter = ("is_active", "calculation_method")
    search_fields = ("name", "description")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("Basic Information", {"fields": ("name", "description", "is_active")}),
        (
            "Promotion Requirements",
            {
                "fields": (
                    "min_average_score_for_promotion",
                    "min_passing_grade",
                    "max_failed_subjects",
                )
            },
        ),
        ("Calculation Method", {"fields": ("calculation_method",)}),
        (
            "Term Weights (Weighted Average)",
            {
                "fields": (
                    "first_term_weight",
                    "second_term_weight",
                    "third_term_weight",
                ),
                "classes": ("collapse",),
                "description": 'These settings only apply when "Weighted Average" calculation method is selected. Values should add up to 100%.',
            },
        ),
        (
            "Metadata",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def save_model(self, request, obj, form, change):
        # If new active setting is being saved, deactivate other settings
        if obj.is_active:
            PerformanceRequirement.objects.exclude(pk=obj.pk).update(is_active=False)
        super().save_model(request, obj, form, change)


# OAuth Credential Store Admin
@admin.register(OAuthCredentialStore)
class OAuthCredentialStoreAdmin(admin.ModelAdmin):
    list_display = (
        "service_name",
        "email",
        "is_active",
        "last_updated",
        "masked_client_id",
    )
    list_filter = ("service_name", "is_active")
    search_fields = ("service_name", "email")
    readonly_fields = ("last_updated",)

    fieldsets = (
        (None, {"fields": ("service_name", "email", "is_active")}),
        (
            "OAuth Credentials",
            {
                "fields": (
                    "client_id",
                    "client_secret",
                    "refresh_token",
                    "access_token",
                ),
                "description": "Sensitive credentials for OAuth authentication.",
            },
        ),
        ("OAuth Settings", {"fields": ("token_uri", "scopes")}),
        ("Metadata", {"fields": ("last_updated",)}),
    )

    def masked_client_id(self, obj):
        """Display a masked version of the client ID for security"""
        if obj.client_id:
            visible_chars = 4
            return f"{obj.client_id[:visible_chars]}{'*' * 10}"
        return "-"

    masked_client_id.short_description = "Client ID"


@admin.register(ScheduledReminder)
class ScheduledReminderAdmin(admin.ModelAdmin):
    list_display = (
        "reminder_type",
        "school",
        "creator",
        "scheduled_time",
        "executed",
        "executed_at",
    )
    list_filter = ("reminder_type", "school", "executed", "scheduled_time")
    search_fields = ("creator__username", "creator__email")
    date_hierarchy = "scheduled_time"

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.executed:
            return (
                "school",
                "creator",
                "scheduled_time",
                "reminder_type",
                "parameters",
                "executed",
                "executed_at",
            )
        return ("executed", "executed_at")

    actions = ["mark_as_executed"]

    def mark_as_executed(self, request, queryset):
        from django.utils import timezone

        updated = queryset.update(executed=True, executed_at=timezone.now())
        self.message_user(request, f"{updated} reminders marked as executed.")

    mark_as_executed.short_description = "Mark selected reminders as executed"


@admin.register(ReminderLog)
class ReminderLogAdmin(admin.ModelAdmin):
    list_display = (
        "teacher",
        "class_assigned",
        "subject",
        "activity_type",
        "status",
        "sent_at",
    )
    list_filter = ("activity_type", "status", "sent_at")
    search_fields = (
        "teacher__full_name",
        "teacher__staff_id",
        "class_assigned__name",
        "subject__subject_name",
    )
    date_hierarchy = "sent_at"
    readonly_fields = (
        "teacher",
        "class_assigned",
        "subject",
        "term",
        "activity_type",
        "completion_percentage",
        "sent_by",
        "sent_at",
        "status",
        "message",
        "scheduled_reminder",
    )


# Scoring Configuration Admin
@admin.register(ScoringConfiguration)
class ScoringConfigurationAdmin(admin.ModelAdmin):
    list_display = (
        "school",
        "exam_score_percentage",
        "class_score_percentage",
        "max_exam_score",
        "max_class_score",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active", "school", "created_at")
    search_fields = ("school__name",)
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("School Information", {"fields": ("school", "is_active")}),
        (
            "Score Weighting",
            {
                "fields": (
                    "exam_score_percentage",
                    "class_score_percentage",
                    "max_exam_score",
                    "max_class_score",
                ),
                "description": "Configure the percentage weights for exam vs class scores. Total must equal 100%.",
            },
        ),
        (
            "Class Score Components",
            {
                "fields": (
                    "individual_score_weight",
                    "class_test_weight",
                    "project_weight",
                    "group_work_weight",
                ),
                "description": "Configure weights for different class score components. Total must equal 100%.",
            },
        ),
        (
            "Metadata",
            {
                "fields": ("created_by", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        if not change:  # Only set created_by for new objects
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        """Filter by school for non-superusers"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # For school admins, only show their school's configurations
        if hasattr(request.user, "school") and request.user.school:
            return qs.filter(school=request.user.school)
        return qs.none()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filter school field for non-superusers"""
        if db_field.name == "school" and not request.user.is_superuser:
            if hasattr(request.user, "school") and request.user.school:
                kwargs["queryset"] = db_field.related_model.objects.filter(
                    pk=request.user.school.pk
                )
            else:
                kwargs["queryset"] = db_field.related_model.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# Archived Student Admin
@admin.register(ArchivedStudent)
class ArchivedStudentAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "completion_date",
        "final_form",
        "final_learning_area",
        "archived_by",
    )
    list_filter = (
        "completion_date",
        "final_form",
        "final_learning_area",
        "archived_by",
    )
    search_fields = (
        "student__full_name",
        "student__admission_number",
        "final_form__name",
        "final_learning_area__name",
    )
    readonly_fields = ("completion_date",)
    date_hierarchy = "completion_date"

    fieldsets = (
        (
            "Student Information",
            {
                "fields": (
                    "student",
                    "completion_date",
                )
            },
        ),
        (
            "Final Academic Information",
            {
                "fields": (
                    "final_form",
                    "final_learning_area",
                )
            },
        ),
        (
            "Administrative Information",
            {
                "fields": (
                    "archived_by",
                    "remarks",
                )
            },
        ),
    )

    def get_queryset(self, request):
        """Filter by school for non-superusers"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # For school admins, only show archived students from their school
        if hasattr(request.user, "school") and request.user.school:
            return qs.filter(student__school=request.user.school)
        return qs.none()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filter fields for non-superusers"""
        if not request.user.is_superuser:
            if (
                db_field.name == "student"
                and hasattr(request.user, "school")
                and request.user.school
            ):
                kwargs["queryset"] = db_field.related_model.objects.filter(
                    school=request.user.school
                )
            elif (
                db_field.name == "final_form"
                and hasattr(request.user, "school")
                and request.user.school
            ):
                kwargs["queryset"] = db_field.related_model.objects.filter(
                    school=request.user.school
                )
            elif (
                db_field.name == "final_learning_area"
                and hasattr(request.user, "school")
                and request.user.school
            ):
                kwargs["queryset"] = db_field.related_model.objects.filter(
                    school=request.user.school
                )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(AcademicYearTemplate)
class AcademicYearTemplateAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "school",
        "is_default",
        "is_active",
        "created_at",
        "created_by",
    ]
    list_filter = ["school", "is_default", "is_active", "created_at"]
    search_fields = ["name", "description"]
    readonly_fields = ["created_at", "updated_at", "created_by"]

    fieldsets = (
        (
            "Basic Information",
            {"fields": ("name", "description", "school", "is_default", "is_active")},
        ),
        ("Template Data", {"fields": ("template_data",), "classes": ("collapse",)}),
        (
            "Metadata",
            {
                "fields": (
                    "created_from_year",
                    "created_by",
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        if not change:  # If creating new
            obj.created_by = request.user
        super().save_model(request, obj, form, change)



# Grading System Admin
@admin.register(GradingSystem)
class GradingSystemAdmin(admin.ModelAdmin):
    list_display = (
        "grade_letter",
        "min_score",
        "max_score",
        "remarks",
        "school",
        "is_active",
    )
    list_filter = ("is_active", "school")
    search_fields = ("grade_letter", "remarks", "description")
    ordering = ("-min_score",)
    
    fieldsets = (
        ("Grade Information", {"fields": ("grade_letter", "min_score", "max_score", "remarks", "description")}),
        ("Settings", {"fields": ("school", "is_active")}),
    )

    def get_queryset(self, request):
        """Filter by school for non-superusers"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # For school admins, only show their school's grading systems
        if hasattr(request.user, "school") and request.user.school:
            return qs.filter(school=request.user.school)
        return qs.none()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filter school field for non-superusers"""
        if db_field.name == "school" and not request.user.is_superuser:
            if hasattr(request.user, "school") and request.user.school:
                kwargs["queryset"] = db_field.related_model.objects.filter(
                    pk=request.user.school.pk
                )
            else:
                kwargs["queryset"] = db_field.related_model.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# Notification Admin
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "recipient",
        "recipient_role",
        "message_preview",
        "timestamp",
        "is_read",
    )
    list_filter = ("recipient_role", "is_read", "timestamp")
    search_fields = ("recipient__username", "recipient__email", "message")
    date_hierarchy = "timestamp"
    readonly_fields = ("timestamp",)
    
    def message_preview(self, obj):
        """Show first 50 characters of message"""
        return obj.message[:50] + "..." if len(obj.message) > 50 else obj.message
    
    message_preview.short_description = "Message Preview"


# Report Card Admin
@admin.register(ReportCard)
class ReportCardAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "academic_year",
        "term",
        "class_assigned",
        "position",
        "average_marks",
        "date_generated",
    )
    list_filter = ("academic_year", "term", "class_assigned", "date_generated")
    search_fields = (
        "student__full_name",
        "student__admission_number",
        "class_assigned__name",
    )
    readonly_fields = ("date_generated", "last_updated")
    date_hierarchy = "date_generated"
    
    fieldsets = (
        ("Student Information", {"fields": ("student", "academic_year", "term", "class_assigned")}),
        ("Performance", {"fields": ("position", "total_score", "average_marks", "form_position")}),
        ("Promotion", {"fields": ("promoted_to", "next_term_begins")}),
        ("Attendance", {"fields": ("days_present", "days_absent", "total_school_days")}),
        ("Remarks", {"fields": ("interest_remarks", "conduct_remarks", "attitude_remarks", "class_teacher_remarks", "principal_remarks")}),
        ("Metadata", {"fields": ("generated_by", "date_generated", "last_updated"), "classes": ("collapse",)}),
    )

    def get_queryset(self, request):
        """Filter by school for non-superusers"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # For school admins, only show report cards from their school
        if hasattr(request.user, "school") and request.user.school:
            return qs.filter(school=request.user.school)
        return qs.none()


# Backup Operation Admin
@admin.register(BackupOperation)
class BackupOperationAdmin(admin.ModelAdmin):
    list_display = (
        "backup_name",
        "school",
        "status",
        "backup_size_display",
        "created_at",
        "completed_at",
        "created_by",
    )
    list_filter = ("status", "school", "created_at")
    search_fields = ("backup_name", "school__name", "backup_file_path")
    readonly_fields = ("created_at", "completed_at", "backup_size")
    date_hierarchy = "created_at"
    
    fieldsets = (
        ("Backup Information", {"fields": ("school", "backup_name", "backup_file_path", "backup_size")}),
        ("Status", {"fields": ("status", "created_at", "completed_at", "error_message")}),
        ("Metadata", {"fields": ("created_by",), "classes": ("collapse",)}),
    )

    def backup_size_display(self, obj):
        """Display backup size in human readable format"""
        if obj.backup_size:
            size = obj.backup_size
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024.0:
                    return f"{size:.1f} {unit}"
                size /= 1024.0
            return f"{size:.1f} TB"
        return "Unknown"
    
    backup_size_display.short_description = "Size"

    def get_queryset(self, request):
        """Filter by school for non-superusers"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # For school admins, only show backups from their school
        if hasattr(request.user, "school") and request.user.school:
            return qs.filter(school=request.user.school)
        return qs.none()


# Restore Operation Admin
@admin.register(RestoreOperation)
class RestoreOperationAdmin(admin.ModelAdmin):
    list_display = (
        "school",
        "status",
        "backup_file_path",
        "created_at",
        "completed_at",
        "created_by",
    )
    list_filter = ("status", "school", "created_at")
    search_fields = ("school__name", "backup_file_path")
    readonly_fields = ("created_at", "completed_at")
    date_hierarchy = "created_at"
    
    fieldsets = (
        ("Restore Information", {"fields": ("school", "backup_file_path")}),
        ("Status", {"fields": ("status", "created_at", "completed_at", "error_message")}),
        ("Metadata", {"fields": ("created_by",), "classes": ("collapse",)}),
    )

    def get_queryset(self, request):
        """Filter by school for non-superusers"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # For school admins, only show restore operations from their school
        if hasattr(request.user, "school") and request.user.school:
            return qs.filter(school=request.user.school)
        return qs.none()


# Backup Settings Admin
@admin.register(BackupSettings)
class BackupSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "school",
        "default_backup_name",
        "default_includes_database",
        "default_includes_media_files",
        "default_includes_static_files",
    )
    list_filter = ("school",)
    search_fields = ("school__name", "default_backup_name")
    
    fieldsets = (
        ("School", {"fields": ("school",)}),
        ("Backup Defaults", {"fields": ("default_backup_name", "default_includes_database", "default_includes_media_files", "default_includes_static_files")}),
        ("Restore Defaults", {"fields": ("default_restore_database", "default_restore_media_files", "default_restore_static_files", "default_backup_existing_data")}),
    )

    def get_queryset(self, request):
        """Filter by school for non-superusers"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # For school admins, only show settings from their school
        if hasattr(request.user, "school") and request.user.school:
            return qs.filter(school=request.user.school)
        return qs.none()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filter school field for non-superusers"""
        if db_field.name == "school" and not request.user.is_superuser:
            if hasattr(request.user, "school") and request.user.school:
                kwargs["queryset"] = db_field.related_model.objects.filter(
                    pk=request.user.school.pk
                )
            else:
                kwargs["queryset"] = db_field.related_model.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

