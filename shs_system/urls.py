from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.views.decorators.csrf import csrf_exempt

# Import modularized views
from .views import (
    views_report_cards,
)  # Add this import to reference the module directly
from .views.views_report_cards import (
    view_student_report_cards,
    bulk_generate_report_cards,
    approve_report_card,
    report_card_list,
    view_report_card_details,
    delete_report_card,
    batch_print_report_cards,
    bulk_approve_report_cards,
    bulk_delete_report_cards,
    get_classes_by_term,
    get_terms_for_bulk_generate,
    get_terms_by_academic_year,
)

from .views.views_auto_terminal_reports import (
    auto_terminal_reports_dashboard,
    auto_generate_terminal_reports,
    auto_terminal_reports_list,
    auto_terminal_report_detail,
    auto_bulk_print_terminal_reports,
    auto_terminal_reports_analytics,
    auto_terminal_reports_export,
    get_terms_for_auto_generation,
    get_classes_for_auto_generation,
    recalculate_report_card,
)

from .views.promotion_management import (
    student_promotion,
    student_performance_detail,
)

from .views.teacher_promotion import (
    teacher_student_promotion,
    teacher_student_performance_detail,
)

from .views.alumni_management import (
    alumni_list,
    alumni_detail,
    alumni_list_ajax,
)
from .views.student_detail import (
    student_detail,
)
from .views.auth import login_view, logout_view

# Import teacher activity monitoring views from the new file
from .views.teacher_monitoring_activities import (
    teacher_activity_monitoring,
    teacher_activity_detail,
    class_activity_detail,
    send_activity_reminder,
    view_reminder_logs,
)

from .views.grading_average import (
    performance_requirement_list,
    performance_requirement_delete,
    performance_requirement_update,
    grading_system_list,
    grading_system_create,
    grading_system_delete,
    grading_system_update,
    get_grade_for_score,
    initialize_default_grades,
    initialize_default_performance_requirements,
    performance_requirement_create,
)

# Import enhanced score entry views
from .views.enhanced_scores import (
    enhanced_enter_scores,
    save_individual_student_scores,
    get_grading_info,
    import_enhanced_scores,
    import_enhanced_scores_batch,
    export_enhanced_scores,
    export_enhanced_scores_batch,
)


# Import mock exam views
from .views.mock_exams import (
    mock_exam_entry_view,
    save_mock_exam_scores,
    mock_exam_dashboard,
)

# Import mock exam management views
from .views.mock_exam_management import (
    mock_exam_list,
    mock_exam_create,
    mock_exam_update,
    mock_exam_delete,
    mock_exam_toggle_active,
)

# Import mock exam export views
from .views.mock_exam_exports import (
    export_mock_exam_scores,
    export_mock_exam_scores_batch,
    import_mock_exam_scores,
    import_mock_exam_scores_batch,
)


from .views.dashboard import (
    admin_dashboard,
    teacher_dashboard,
    student_dashboard,
    dashboard,
    teacher_monitoring,
    debug_dashboard_urls,
)
from .views.teacher_management import (
    teacher_profile,
    teacher_update_profile,
    teacher_change_password,
    get_teacher_assignments,
    teacher_list,
    teacher_detail,
    add_teacher,
    edit_teacher,
    delete_teacher,
    assign_class_teacher,
    assign_subject,
    assign_multiple_subjects,
    remove_subject_assignment,
    remove_class_teacher,
    get_class_subjects,
    bulk_subject_assignment,
)
from .views.form_manage import (
    form_create,
    form_delete,
    form_update,
    form_list,
    form_api_list,
    form_api_detail,
    learning_area_create,
    learning_area_delete,
    learning_area_list,
    learning_area_update,
    department_create,
    department_delete,
    department_list,
    department_update,
    department_api_list,
    department_api_detail,
    learning_area_api_detail,
    learning_area_api_list,
    get_teachers_api,
)
from .views.student_management import (
    student_list,
    student_class_assignment,
    student_enrollment,
    add_student,
    edit_student,
    delete_student,
    assign_student_class,
    student_class_history,
    student_profile,
    student_update_profile,
    debug_student_images,
    bulk_delete_students,
    bulk_import_preview,
    bulk_import_students,
    bulk_operation_progress,
    bulk_assign_students_to_class,
    bulk_unassign_students_from_class,
    assign_student_class_ajax,
    bulk_upload_student_images,
    apply_bulk_student_images,

    download_student_csv_template,
    quick_upload_student_image,

)
from .views.student_class_assignment import (
    student_class_assignment_dashboard,
    student_class_assignment_list,
    assign_student_class as assign_student_class_new,
    unassign_student_class,
    bulk_assign_students,
    bulk_unassign_students,
    class_assignment_history,
    class_roster,
    get_students_for_assignment,
    get_class_statistics,

    get_class_roster_export,

)
from .views.student_list_ajax import (
    student_list_ajax,
    get_student_view_modal,
    get_student_edit_modal,
    get_student_assign_modal,
)
from .views.teacher_remarks import (
    class_teacher_remarks,
    save_student_remarks_ajax,
    save_all_remarks_ajax,
    print_class_list,
    student_term_performance,
    auto_generate_remarks,

    export_remarks,
    import_remarks,

)
from .views.manage_class import (
    class_list,
    create_class,
    class_detail,
    update_class,
    delete_class,
    generate_class_report,
    get_terms_for_academic_year,
    assign_class_subject,
    update_class_subject,
    delete_class_subject,
    print_class_list,
    get_subjects,

    get_teachers_available,
    get_class_form_data,
    bulk_assign_subjects,
    bulk_assign_class_teacher,
    assign_class_teacher_api,
    test_class_teacher_api,
    class_teacher_list,
    remove_class_teacher_api,

)
from .views.academic_year import (
    academic_year_list,
    academic_year_create,
    academic_year_detail,
    academic_year_edit,
    academic_year_delete,
    set_current_academic_year,
    term_list,
    term_create,
    term_edit,
    term_delete,
    set_current_term,
    get_academic_year_info,
    api_get_terms,
)
from .views.academic_year_templates import (
    template_list,
    template_detail,
    template_create,
    template_create_from_academic_year,
    template_edit,
    template_delete,
    template_apply,
    template_preview,
    template_duplicate,
    template_set_default,
    template_export,
)
from .views.academic_year_archive import (
    archive_academic_year,
    unarchive_academic_year,
    academic_year_archive_list,
)
from .views.academic_year_diagnostics import (
    academic_year_diagnostics,
    academic_year_diagnostics_json,
)
from .views.template_debug import debug_template_creation

from .views.backup_restore_views import (
    backup_dashboard,
    create_backup,
    backup_status,
    download_backup,
    delete_backup,
    restore_dashboard,
    upload_backup_file,
    restore_from_backup,
    restore_status,
    backup_restore_settings,
    validate_backup_file,
    backup_settings,
    save_backup_settings,
    reset_backup_settings,
    cleanup_temp_files,
)

from .views.subject_manage import (
    subject_list,
    subject_create,
    subject_update,
    subject_delete,
)
from .views.school_info import (
    SchoolInformationListView,
    SchoolInformationDetailView,
    SchoolInformationCreateView,
    SchoolAuthoritySignatureCreateView,
    SchoolInformationUpdateView,
    SchoolInformationDeleteView,
    SetActiveSchoolView,
    SchoolAuthoritySignatureDeleteView,
    SchoolAuthoritySignatureListView,
    SchoolAuthoritySignatureUpdateView,
    SetActiveSignatureView,
    get_terms_by_academic_year,
    manage_scoring_config,
)
from .views.user_management import (
    user_management,
    create_user,
    update_user,
    delete_user,
    resend_credentials,

    reset_password_default,
    bulk_reset_password_default,

    get_user_model,
    configure_service_account,
)
from .views.scores import (
    enter_scores,
    export_scores,
    import_scores,
    export_scores_batch,
    import_scores_batch,
)
from .views.score_sheet import (
    score_sheet_view,
    get_score_sheet_data_ajax,
    export_score_sheet_pdf,
    export_score_sheet_excel,
    print_score_sheet,

    get_form_level_score_sheet_data_ajax,
    export_form_level_score_sheet_pdf,
    print_form_level_score_sheet,
    mock_exam_score_sheet_view,
    get_mock_exam_score_sheet_data_ajax,
    export_mock_exam_score_sheet_pdf,
    export_mock_exam_score_sheet_excel,
    print_mock_exam_score_sheet,
    get_form_level_mock_exam_score_sheet_data_ajax,
    export_form_level_mock_exam_score_sheet_pdf,
    print_form_level_mock_exam_score_sheet,
)
from .views.promotion_sheet import (
    promotion_sheet_view,
    get_promotion_sheet_data_ajax,
    export_promotion_sheet_pdf,
    export_promotion_sheet_excel,
    print_promotion_sheet,

)
from .views.utils import extend_session  # Add this import at the end of the file

# Import score management views
from .views.score_management import (
    ScoreDashboardView,
    ClassScoreListView,
    StudentScoreDetailView,
    SubjectPerformanceView,
    CompareScoreView,
    ProgressTrackingView,
    ExportScorePDFView,
    ExportScoreExcelView,
    ExportScoreCSVView,
)
from .views.debug_views import test_media_serving
from .views.debug_static import debug_static_files
from .views.current_settings import (
    current_settings_dashboard,
    set_current_academic_year,
    set_current_term,
    set_current_settings_both,
    get_terms_for_academic_year,
)


urlpatterns = [
    path("debug/dashboard-urls/", debug_dashboard_urls, name="debug_dashboard_urls"),
    path("debug/student-images/", debug_student_images, name="debug_student_images"),
    path("debug/media-test/", test_media_serving, name="test_media_serving"),
    path("debug/static-info/", debug_static_files, name="debug_static_files"),
    path(
        "api/get_terms_for_academic_year/",
        get_terms_for_academic_year,
        name="get_terms_for_academic_year",
    ),
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(template_name="password_reset.html"),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="password_reset_confirm.html"
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
    path("", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("dashboard/", dashboard, name="dashboard"),
    path("dashboard/admin/", admin_dashboard, name="admin_dashboard"),
    path("dashboard/teacher/", teacher_dashboard, name="teacher_dashboard"),
    path("dashboard/student/", student_dashboard, name="student_dashboard"),
    path("student/profile/", student_profile, name="student_profile"),
    path(
        "student/update-profile/", student_update_profile, name="student_update_profile"
    ),
    path(
        "teacher-dashboard/<int:assignment_id>/",
        teacher_dashboard,
        name="teacher_dashboard_with_assignment",
    ),
    path("enter-scores/", enter_scores, name="enter_scores"),
    path("enhanced-enter-scores/", enhanced_enter_scores, name="enhanced_enter_scores"),
    # Score Sheet Interface URLs
    path("score-sheet/", score_sheet_view, name="score_sheet"),
    path(
        "api/score-sheet-data/",
        get_score_sheet_data_ajax,
        name="get_score_sheet_data_ajax",
    ),

    # Mock Exam Score Sheet URLs
    path("mock-exams/score-sheet/", mock_exam_score_sheet_view, name="mock_exam_score_sheet"),
    path(
        "api/mock-exam-score-sheet-data/",
        get_mock_exam_score_sheet_data_ajax,
        name="get_mock_exam_score_sheet_data_ajax",
    ),
    path(
        "mock-exams/score-sheet/print/",
        print_mock_exam_score_sheet,
        name="print_mock_exam_score_sheet",
    ),
    path(
        "mock-exams/score-sheet/export/pdf/",
        export_mock_exam_score_sheet_pdf,
        name="export_mock_exam_score_sheet_pdf",
    ),
    path(
        "mock-exams/score-sheet/export/excel/",
        export_mock_exam_score_sheet_excel,
        name="export_mock_exam_score_sheet_excel",
    ),
    # Form-level Mock Exam Score Sheet URLs
    path(
        "api/form-level-mock-exam-score-sheet-data/",
        get_form_level_mock_exam_score_sheet_data_ajax,
        name="get_form_level_mock_exam_score_sheet_data_ajax",
    ),
    path(
        "form-level-mock-exam-score-sheet/print/",
        print_form_level_mock_exam_score_sheet,
        name="print_form_level_mock_exam_score_sheet",
    ),
    path(
        "form-level-mock-exam-score-sheet/export/pdf/",
        export_form_level_mock_exam_score_sheet_pdf,
        name="export_form_level_mock_exam_score_sheet_pdf",
    ),

    path(
        "score-sheet/print/",
        print_score_sheet,
        name="print_score_sheet",
    ),
    path(
        "score-sheet/export/pdf/", export_score_sheet_pdf, name="export_score_sheet_pdf"
    ),
    path(
        "score-sheet/export/excel/",
        export_score_sheet_excel,
        name="export_score_sheet_excel",
    ),

    # Form-level Score Sheet URLs
    path(
        "api/form-level-score-sheet-data/",
        get_form_level_score_sheet_data_ajax,
        name="get_form_level_score_sheet_data_ajax",
    ),
    path(
        "form-level-score-sheet/print/",
        print_form_level_score_sheet,
        name="print_form_level_score_sheet",
    ),
    path(
        "form-level-score-sheet/export/pdf/", 
        export_form_level_score_sheet_pdf, 
        name="export_form_level_score_sheet_pdf"
    ),
    # Promotion Sheet Interface URLs
    path("promotion-sheet/", promotion_sheet_view, name="promotion_sheet"),
    path(
        "api/promotion-sheet-data/",
        get_promotion_sheet_data_ajax,
        name="get_promotion_sheet_data_ajax",
    ),
    path(
        "promotion-sheet/print/",
        print_promotion_sheet,
        name="print_promotion_sheet",
    ),
    path(
        "promotion-sheet/export/pdf/", 
        export_promotion_sheet_pdf, 
        name="export_promotion_sheet_pdf"
    ),
    path(
        "promotion-sheet/export/excel/",
        export_promotion_sheet_excel,
        name="export_promotion_sheet_excel",
    ),

    path(
        "api/save-student-scores/",
        save_individual_student_scores,
        name="save_individual_student_scores",
    ),
    path("api/get-grading-info/", get_grading_info, name="get_grading_info"),
    path("export-scores/", export_scores, name="export_scores"),
    path("export-scores-batch/", export_scores_batch, name="export_scores_batch"),
    path("import-scores/", import_scores, name="import_scores"),
    path("import-scores-batch/", import_scores_batch, name="import_scores_batch"),
    path(
        "import-enhanced-scores/", import_enhanced_scores, name="import_enhanced_scores"
    ),
    path(
        "import-enhanced-scores-batch/",
        import_enhanced_scores_batch,
        name="import_enhanced_scores_batch",
    ),
    path(
        "export-enhanced-scores/", export_enhanced_scores, name="export_enhanced_scores"
    ),
    path(
        "export-enhanced-scores-batch/",
        export_enhanced_scores_batch,
        name="export_enhanced_scores_batch",
    ),

    # Mock Exam URLs
    path('mock-exams/entry/', mock_exam_entry_view, name='mock_exam_entry'),
    path('mock-exams/save/', save_mock_exam_scores, name='save_mock_exam_scores'),
    path('mock-exams/dashboard/', mock_exam_dashboard, name='mock_exam_dashboard'),
    # Mock Exam Management URLs
    path('mock-exams/manage/', mock_exam_list, name='mock_exam_list'),
    path('mock-exams/create/', mock_exam_create, name='mock_exam_create'),
    path('mock-exams/<int:pk>/update/', mock_exam_update, name='mock_exam_update'),
    path('mock-exams/<int:pk>/delete/', mock_exam_delete, name='mock_exam_delete'),
    path('mock-exams/<int:pk>/toggle-active/', mock_exam_toggle_active, name='mock_exam_toggle_active'),
    # Mock Exam Export URLs
    path('mock-exams/export/', export_mock_exam_scores, name='export_mock_exam_scores'),
    path('mock-exams/export-batch/', export_mock_exam_scores_batch, name='export_mock_exam_scores_batch'),
    # Mock Exam Import URLs
    path('mock-exams/import/', import_mock_exam_scores, name='import_mock_exam_scores'),
    path('mock-exams/import-batch/', import_mock_exam_scores_batch, name='import_mock_exam_scores_batch'),

    path(
        "api/teacher-assignments/",
        get_teacher_assignments,
        name="teacher_assignments_api",
    ),
    path("teachers/", teacher_list, name="teacher_list"),
    path("teachers/add/", add_teacher, name="add_teacher"),
    path(
        "teachers/bulk-subject-assignment/",
        bulk_subject_assignment,
        name="bulk_subject_assignment",
    ),
    path("teachers/<str:staff_id>/", teacher_detail, name="teacher_detail"),
    path("teachers/<str:staff_id>/edit/", edit_teacher, name="edit_teacher"),
    path("teachers/<str:staff_id>/delete/", delete_teacher, name="delete_teacher"),
    path(
        "teachers/<str:staff_id>/assign-class/",
        assign_class_teacher,
        name="assign_class_teacher",
    ),
    path(
        "teachers/<str:staff_id>/assign-subject/",
        assign_subject,
        name="assign_subject",
    ),
    path(
        "teachers/<str:staff_id>/assign-multiple-subjects/",
        assign_multiple_subjects,
        name="assign_multiple_subjects",
    ),
    path(
        "teachers/remove-subject-assignment/<str:assignment_id>/",
        remove_subject_assignment,
        name="remove_subject_assignment",
    ),
    path(
        "subject-assignments/<str:assignment_id>/remove/",
        remove_subject_assignment,
        name="remove_subject_assignment",
    ),
    path(
        "class-teacher-assignments/<str:class_id>/remove/",
        remove_class_teacher,
        name="remove_class_teacher",
    ),
    # Get subjects for a specific class (API endpoint)
    path(
        "api/class-subjects/",
        get_class_subjects,
        name="get_class_subjects",
    ),
    # Student list with search and filter functionality
    path("student/", student_list, name="student_list"),
    # Student class assignment system (legacy)
    path(
        "student/class-assignment/",
        student_class_assignment,
        name="student_class_assignment",
    ),
    # Modern Student Class Assignment System
    path(
        "student/class-assignment/dashboard/",
        student_class_assignment_dashboard,
        name="student_class_assignment_dashboard",
    ),
    path(
        "student/class-assignment/list/",
        student_class_assignment_list,
        name="student_class_assignment_list",
    ),
    path(
        "student/<int:student_id>/assign-class-new/",
        assign_student_class_new,
        name="assign_student_class_new",
    ),
    path(
        "student/<int:student_id>/unassign-class/",
        unassign_student_class,
        name="unassign_student_class",
    ),
    path(
        "student/class-assignment/bulk-assign/",
        bulk_assign_students,
        name="bulk_assign_students",
    ),
    path(
        "student/class-assignment/bulk-unassign/",
        bulk_unassign_students,
        name="bulk_unassign_students",
    ),
    path(
        "student/<int:student_id>/assignment-history/",
        class_assignment_history,
        name="class_assignment_history",
    ),
    path(
        "class/<int:class_id>/roster/",
        class_roster,
        name="class_roster",
    ),
    # API endpoints for student class assignment
    path(
        "api/students-for-assignment/",
        get_students_for_assignment,
        name="get_students_for_assignment",
    ),
    path(
        "api/class-statistics/",
        get_class_statistics,
        name="get_class_statistics",
    ),

    path(
        "api/class/<int:class_id>/roster-export/",
        get_class_roster_export,
        name="get_class_roster_export",
    ),

    # Modern student enrollment form
    path("student/enroll/", student_enrollment, name="student_enrollment"),
    # Add a new student
    path("student/add/", add_student, name="add_student"),
    # Edit an existing student
    path("student/<int:student_id>/edit/", edit_student, name="edit_student"),
    # Delete a student
    path("student/<int:student_id>/delete/", delete_student, name="delete_student"),
    # Assign or reassign a student to a class
    path(
        "student/<int:student_id>/assign-class/",
        assign_student_class,
        name="assign_student_class",
    ),
    # View student class assignment history
    path(
        "student/<int:student_id>/class-history/",
        student_class_history,
        name="student_class_history",
    ),
    # Bulk student operations
    path("student/bulk-delete/", bulk_delete_students, name="bulk_delete_students"),
    path(
        "student/bulk-operation-progress/",
        bulk_operation_progress,
        name="bulk_operation_progress",
    ),
    path("student/list-ajax/", student_list_ajax, name="student_list_ajax"),
    path("student/view-modal/", get_student_view_modal, name="get_student_view_modal"),
    path("student/edit-modal/", get_student_edit_modal, name="get_student_edit_modal"),
    # Alumni URLs
    path("alumni/", alumni_list, name="alumni_list"),
    path("alumni/<int:student_id>/", alumni_detail, name="alumni_detail"),
    path("alumni/list-ajax/", alumni_list_ajax, name="alumni_list_ajax"),
    # Student Detail URLs
    path("student/<int:student_id>/detail/", student_detail, name="student_detail"),
    path(
        "student/assign-modal/",
        get_student_assign_modal,
        name="get_student_assign_modal",
    ),
    path(
        "student/bulk-import/preview/", bulk_import_preview, name="bulk_import_preview"
    ),
    path(
        "student/bulk-import/import/", bulk_import_students, name="bulk_import_students"
    ),

    path(
        "student/bulk-import/template/", download_student_csv_template, name="download_student_csv_template"
    ),

    # Bulk class assignment operations
    path(
        "student/bulk-assign-class/",
        bulk_assign_students_to_class,
        name="bulk_assign_students_to_class",
    ),
    path(
        "student/bulk-unassign-class/",
        bulk_unassign_students_from_class,
        name="bulk_unassign_students_from_class",
    ),
    path(
        "student/<int:student_id>/assign-class-ajax/",
        assign_student_class_ajax,
        name="assign_student_class_ajax",
    ),
    # Bulk image upload URLs
    path(
        "student/bulk-upload-images/",
        bulk_upload_student_images,
        name="bulk_upload_student_images",
    ),
    path(
        "student/apply-bulk-images/",
        apply_bulk_student_images,
        name="apply_bulk_student_images",
    ),

    # Quick individual student image upload
    path(
        "student/<int:student_id>/quick-upload-image/",
        quick_upload_student_image,
        name="quick_upload_student_image",
    ),
    # Add this new line to redirect from /promotion/ to /promotion_management/
    path("students/promotion/", student_promotion, name="student_promotion"),
    path("teacher/promotion/", teacher_student_promotion, name="teacher_promotion"),
    path("teacher/student/performance/<int:student_id>/", teacher_student_performance_detail, name="teacher_student_performance_detail"),

    path(
        "students/performance/<int:student_id>/",
        student_performance_detail,
        name="student_performance_detail",
    ),
    # Academic Year URLs
    path("academic-years/", academic_year_list, name="academic_year_list"),
    path(
        "academic-years/create/",
        academic_year_create,
        name="academic_year_create",
    ),
    path(
        "academic-years/<int:pk>/",
        academic_year_detail,
        name="academic_year_detail",
    ),
    path(
        "academic-years/<int:pk>/edit/",
        academic_year_edit,
        name="academic_year_edit",
    ),
    path(
        "academic-years/<int:pk>/delete/",
        academic_year_delete,
        name="academic_year_delete",
    ),
    path(
        "academic-years/<int:pk>/set-current/",
        set_current_academic_year,
        name="set_current_academic_year",
    ),
    # Academic Year Template URLs
    path("templates/", template_list, name="template_list"),
    path("templates/create/", template_create, name="template_create"),
    path(
        "templates/create-from-year/",
        template_create_from_academic_year,
        name="template_create_from_academic_year",
    ),
    path("templates/<int:template_id>/", template_detail, name="template_detail"),
    path("templates/<int:template_id>/edit/", template_edit, name="template_edit"),
    path(
        "templates/<int:template_id>/delete/", template_delete, name="template_delete"
    ),
    path("templates/<int:template_id>/apply/", template_apply, name="template_apply"),
    path(
        "templates/<int:template_id>/preview/",
        template_preview,
        name="template_preview",
    ),
    path(
        "templates/<int:template_id>/duplicate/",
        template_duplicate,
        name="template_duplicate",
    ),
    path(
        "templates/<int:template_id>/set-default/",
        template_set_default,
        name="template_set_default",
    ),
    path(
        "templates/<int:template_id>/export/", template_export, name="template_export"
    ),
    # Academic Year Archiving URLs
    path(
        "academic-years/<int:academic_year_id>/archive/",
        archive_academic_year,
        name="archive_academic_year",
    ),
    path(
        "academic-years/<int:academic_year_id>/unarchive/",
        unarchive_academic_year,
        name="unarchive_academic_year",
    ),
    path(
        "academic-years/archived/",
        academic_year_archive_list,
        name="academic_year_archive_list",
    ),
    # Academic Year Diagnostics URLs
    path(
        "academic-years/<int:academic_year_id>/diagnostics/",
        academic_year_diagnostics,
        name="academic_year_diagnostics",
    ),
    path(
        "api/academic-years/<int:academic_year_id>/diagnostics/",
        academic_year_diagnostics_json,
        name="academic_year_diagnostics_json",
    ),
    # Template Debug URLs
    path(
        "debug/template-creation/<int:academic_year_id>/",
        debug_template_creation,
        name="debug_template_creation",
    ),
    # Term URLs
    path("terms/", term_list, name="term_list"),
    path("terms/create/", term_create, name="term_create"),
    path("terms/<int:pk>/edit/", term_edit, name="term_edit"),
    path("terms/<int:pk>/delete/", term_delete, name="term_delete"),
    path("terms/<int:pk>/set-current/", set_current_term, name="set_current_term"),
    # Subject Management
    path("subjects/", subject_list, name="subject_list"),
    path("subjects/create/", subject_create, name="subject_create"),
    path("subjects/<int:pk>/update/", subject_update, name="subject_update"),
    path("subjects/<int:pk>/delete/", subject_delete, name="subject_delete"),
    # Teacher-Subject Assignment Management
    # Class Subject Management
    path("classes/", class_list, name="class_list"),
    path(
        "classes/create/", create_class, name="create_class"
    ),  # This should come before the detail view
    path("classes/<str:class_id>/", class_detail, name="class_detail"),
    path("classes/<str:class_id>/update/", update_class, name="update_class"),
    path("classes/<str:class_id>/delete/", delete_class, name="delete_class"),

    # API endpoint for optimized form data
    path("api/class-form-data/", get_class_form_data, name="get_class_form_data"),
    # API endpoints for bulk operations
    path("api/subjects/", get_subjects, name="get_subjects"),
    path("api/teachers/available/", get_teachers_available, name="get_teachers_available"),
    path("api/bulk-assign-subjects/", bulk_assign_subjects, name="bulk_assign_subjects"),
    path("api/bulk-assign-class-teacher/", bulk_assign_class_teacher, name="bulk_assign_class_teacher"),
    path("api/assign-class-teacher/<str:class_id>/", assign_class_teacher_api, name="assign_class_teacher_api"),
    path("api/test-class-teacher/<str:class_id>/", test_class_teacher_api, name="test_class_teacher_api"),
    path("class-teachers/", class_teacher_list, name="class_teacher_list"),
    path("api/remove-class-teacher/<str:class_id>/", remove_class_teacher_api, name="remove_class_teacher_api"),

    path(
        "classes/<str:class_id>/report/",
        generate_class_report,
        name="generate_class_report",
    ),
    path("class/<str:class_id>/print/", print_class_list, name="print_class_list"),
    path(
        "class/<str:class_id>/student/<int:student_id>/performance/",
        student_term_performance,
        name="student_term_performance",
    ),
    # Class Subject Management
    path(
        "classes/<str:class_id>/assign-subject/",
        assign_class_subject,
        name="assign_class_subject",
    ),
    path(
        "classes/<str:class_id>/bulk-assign-subject/",
        assign_class_subject,  # We'll reuse the same view but modify it to handle bulk assignments
        name="bulk_assign_subject",
    ),
    path(
        "class-subjects/<int:class_subject_id>/update/",
        update_class_subject,
        name="update_class_subject",
    ),
    path(
        "class-subjects/<int:class_subject_id>/delete/",
        delete_class_subject,
        name="delete_class_subject",
    ),
    # School Information URLs
    path(
        "schools/",
        SchoolInformationListView.as_view(),
        name="school_information_list",
    ),
    path(
        "schools/<int:pk>/",
        SchoolInformationDetailView.as_view(),
        name="school_information_detail",
    ),
    path(
        "schools/add/",
        SchoolInformationCreateView.as_view(),
        name="school_information_create",
    ),
    path(
        "schools/<int:pk>/update/",
        SchoolInformationUpdateView.as_view(),
        name="school_information_update",
    ),
    path(
        "schools/<int:pk>/delete/",
        SchoolInformationDeleteView.as_view(),
        name="school_information_delete",
    ),
    path(
        "schools/<int:pk>/set-active/",
        SetActiveSchoolView.as_view(),
        name="set_active_school",
    ),
    # AJAX endpoint for getting terms by academic year
    path(
        "school/get_terms_by_academic_year/<int:academic_year_id>/",
        get_terms_by_academic_year,
        name="get_terms_by_academic_year",
    ),
    # Scoring Configuration URL
    path(
        "school/scoring-config/",
        manage_scoring_config,
        name="manage_scoring_config",
    ),
    # School Authority Signature URLs
    path(
        "schools/<int:school_id>/signatures/",
        SchoolAuthoritySignatureListView.as_view(),
        name="authority_signature_list",
    ),
    path(
        "schools/<int:school_id>/signatures/add/",
        SchoolAuthoritySignatureCreateView.as_view(),
        name="authority_signature_create",
    ),
    path(
        "signatures/<int:pk>/update/",
        SchoolAuthoritySignatureUpdateView.as_view(),
        name="authority_signature_update",
    ),
    path(
        "signatures/<int:pk>/delete/",
        SchoolAuthoritySignatureDeleteView.as_view(),
        name="authority_signature_delete",
    ),
    path(
        "signatures/<int:pk>/set-active/",
        SetActiveSignatureView.as_view(),
        name="set_active_signature",
    ),
    # Class teacher remarks routes
    path("teacher/remarks/", class_teacher_remarks, name="class_teacher_remarks"),
    path(
        "teacher/remarks/save-student/",
        save_student_remarks_ajax,
        name="save_student_remarks_ajax",
    ),
    path(
        "teacher/remarks/save-all/",
        save_all_remarks_ajax,
        name="save_all_remarks_ajax",
    ),

    path(
        "teacher/remarks/export/",
        export_remarks,
        name="export_remarks",
    ),
    path(
        "teacher/remarks/import/",
        import_remarks,
        name="import_remarks",
    ),

    # User Management URLs
    path("users/", user_management, name="user_management"),
    path("users/create/", create_user, name="create_user"),
    path("users/<int:user_id>/update/", update_user, name="update_user"),
    path("users/<int:user_id>/delete/", delete_user, name="delete_user"),
    path(
        "users/<int:user_id>/resend-credentials/",
        resend_credentials,
        name="resend_credentials",
    ),

    path(
        "users/<int:user_id>/reset-password-default/",
        reset_password_default,
        name="reset_password_default",
    ),
    path(
        "users/bulk-reset-password-default/",
        bulk_reset_password_default,
        name="bulk_reset_password_default",
    ),

    # Form URLs
    path("forms/", form_list, name="form_list"),
    path("forms/create/", form_create, name="form_create"),
    path("forms/<int:pk>/update/", form_update, name="form_update"),
    path("forms/<int:pk>/delete/", form_delete, name="form_delete"),
    # Form API URLs for AJAX operations
    path("api/forms/", form_api_list, name="form_api_list"),
    path("api/forms/<int:pk>/", form_api_detail, name="form_api_detail"),
    # Learning Area URLs
    path("learning-areas/", learning_area_list, name="learning_area_list"),
    path(
        "learning-areas/create/",
        learning_area_create,
        name="learning_area_create",
    ),
    path(
        "learning-areas/<int:pk>/update/",
        learning_area_update,
        name="learning_area_update",
    ),
    path(
        "learning-areas/<int:pk>/delete/",
        learning_area_delete,
        name="learning_area_delete",
    ),
    # Learning Area API URLs for AJAX operations
    path("api/learning-areas/", learning_area_api_list, name="learning_area_api_list"),
    path(
        "api/learning-areas/<int:pk>/",
        learning_area_api_detail,
        name="learning_area_api_detail",
    ),
    # Department URLs
    path("departments/", department_list, name="department_list"),
    path("departments/create/", department_create, name="department_create"),
    path(
        "departments/<int:pk>/update/",
        department_update,
        name="department_update",
    ),
    path(
        "departments/<int:pk>/delete/",
        department_delete,
        name="department_delete",
    ),
    # Department API URLs for AJAX operations
    path("api/departments/", department_api_list, name="department_api_list"),
    path(
        "api/departments/<int:pk>/", department_api_detail, name="department_api_detail"
    ),
    # Teacher API for dropdowns
    path("api/teachers/", get_teachers_api, name="get_teachers_api"),
    # Teacher Profile Management
    path("teacher-profile/", teacher_profile, name="teacher_profile"),
    path(
        "teacher-profile/update/",
        teacher_update_profile,
        name="teacher_update_profile",
    ),
    path(
        "teacher-profile/change-password/",
        teacher_change_password,
        name="teacher_change_password",
    ),
    # Grading System URLs
    path("grades/", grading_system_list, name="grading_system_list"),
    path("grades/create/", grading_system_create, name="grading_system_create"),
    path(
        "grades/<int:pk>/update/",
        grading_system_update,
        name="grading_system_update",
    ),
    path(
        "grades/<int:pk>/delete/",
        grading_system_delete,
        name="grading_system_delete",
    ),
    path(
        "grades/initialize/",
        initialize_default_grades,
        name="initialize_default_grades",
    ),
    path(
        "api/get_grade_for_score/",
        get_grade_for_score,
        name="get_grade_for_score",
    ),
    # Performance Requirements URLs
    path(
        "performance-requirements/",
        performance_requirement_list,
        name="performance_requirement_list",
    ),
    path(
        "performance-requirements/create/",
        performance_requirement_create,
        name="performance_requirement_create",
    ),
    path(
        "performance-requirements/<int:pk>/update/",
        performance_requirement_update,
        name="performance_requirement_update",
    ),
    path(
        "performance-requirements/<int:pk>/delete/",
        performance_requirement_delete,
        name="performance_requirement_delete",
    ),
    path(
        "performance-requirements/initialize/",
        initialize_default_performance_requirements,
        name="initialize_default_performance_requirements",
    ),
    # Report Card URLs
    path("report-cards/", report_card_list, name="report_card_list"),
    path(
        "report-cards/bulk-generate/",
        bulk_generate_report_cards,
        name="bulk_generate_report_cards",
    ),
    # Add URL for viewing individual report card details
    path(
        "report-cards/view/<int:report_card_id>/",
        view_report_card_details,
        name="view_report_card_details",
    ),
    # API endpoint for terms in bulk report card generation
    path(
        "school/report-cards/get-terms-for-bulk-generate/<int:academic_year_id>/",
        get_terms_for_bulk_generate,
        name="get_terms_for_bulk_generate",
    ),
    path(
        "report-cards/<int:report_card_id>/approve/",
        approve_report_card,
        name="approve_report_card",
    ),
    path(
        "report-cards/<int:report_card_id>/delete/",
        delete_report_card,
        name="delete_report_card",
    ),
    path(
        "report-cards/<int:student_id>/",
        view_student_report_cards,
        name="view_student_report_cards",
    ),
    path(
        "report-cards/batch-print/",
        batch_print_report_cards,
        name="batch_print_report_cards",
    ),
    path(
        "report-cards/bulk-approve/",
        bulk_approve_report_cards,
        name="bulk_approve_report_cards",
    ),
    path(
        "report-cards/bulk-delete/",
        bulk_delete_report_cards,
        name="bulk_delete_report_cards",
    ),
    path(
        "report-cards/get-classes-by-term/",
        get_classes_by_term,
        name="get_classes_by_term",
    ),

    # Auto Terminal Reports URLs
    path(
        "auto-terminal-reports/",
        auto_terminal_reports_dashboard,
        name="auto_terminal_reports_dashboard",
    ),
    path(
        "auto-terminal-reports/generate/",
        auto_generate_terminal_reports,
        name="auto_generate_terminal_reports",
    ),
    path(
        "auto-terminal-reports/list/",
        auto_terminal_reports_list,
        name="auto_terminal_reports_list",
    ),
    path(
        "auto-terminal-reports/<int:report_card_id>/",
        auto_terminal_report_detail,
        name="auto_terminal_report_detail",
    ),
    path(
        "auto-terminal-reports/bulk-print/",
        auto_bulk_print_terminal_reports,
        name="auto_bulk_print_terminal_reports",
    ),
    path(
        "auto-terminal-reports/analytics/",
        auto_terminal_reports_analytics,
        name="auto_terminal_reports_analytics",
    ),
    path(
        "auto-terminal-reports/export/",
        auto_terminal_reports_export,
        name="auto_terminal_reports_export",
    ),
    path(
        "auto-terminal-reports/api/get-terms/<int:academic_year_id>/",
        get_terms_for_auto_generation,
        name="get_terms_for_auto_generation",
    ),
    path(
        "auto-terminal-reports/api/get-classes/<int:academic_year_id>/",
        get_classes_for_auto_generation,
        name="get_classes_for_auto_generation",
    ),
    path(
        "auto-terminal-reports/<int:report_card_id>/recalculate/",
        recalculate_report_card,
        name="recalculate_report_card",
    ),

    path(
        "users/configure-service-account/",
        configure_service_account,
        name="configure_service_account",
    ),
    # Session management
    path(
        "extend-session/",
        extend_session,
        name="extend_session",
    ),
    # Add the new API endpoint
    path(
        "api/get-academic-year-info/<int:year_id>/",
        get_academic_year_info,
        name="get_academic_year_info",
    ),
    # Add endpoint for filtering terms by academic year
    path(
        "report-cards/get-terms-by-academic-year/",
        views_report_cards.get_terms_by_academic_year,  # Use the fully qualified reference
        name="get_terms_by_academic_year_report_cards",
    ),
    # Add endpoint for auto-generating teacher remarks
    path(
        "report-cards/auto-generate-remarks/",
        auto_generate_remarks,
        name="auto_generate_remarks",
    ),
    # Score Management URLs
    path(
        "score-management/",
        ScoreDashboardView.as_view(),
        name="score_management_dashboard",
    ),
    path(
        "score-management/class-scores/",
        ClassScoreListView.as_view(),
        name="class_score_list",
    ),
    path(
        "score-management/student/<int:student_id>/",
        StudentScoreDetailView.as_view(),
        name="student_score_detail",
    ),
    path(
        "score-management/subject-performance/",
        SubjectPerformanceView.as_view(),
        name="subject_performance",
    ),
    path(
        "score-management/compare-scores/",
        CompareScoreView.as_view(),
        name="compare_scores",
    ),
    path(
        "score-management/progress-tracking/",
        ProgressTrackingView.as_view(),
        name="progress_tracking",
    ),
    # Export URLs
    path(
        "score-management/export/pdf/<int:class_id>/<int:subject_id>/",
        ExportScorePDFView.as_view(),
        name="export_scores_pdf",
    ),
    path(
        "score-management/export/excel/<int:class_id>/<int:subject_id>/",
        ExportScoreExcelView.as_view(),
        name="export_scores_excel",
    ),
    path(
        "score-management/export/csv/<int:class_id>/<int:subject_id>/",
        ExportScoreCSVView.as_view(),
        name="export_scores_csv",
    ),
    # Teacher Monitoring
    path("teacher-monitoring/", teacher_monitoring, name="teacher_monitoring"),
    # Teacher Activity Monitoring URLs
    path(
        "teacher-activity-monitoring/",
        teacher_activity_monitoring,
        name="teacher_activity_monitoring",
    ),
    path(
        "teacher-activity-monitoring/teacher/<int:teacher_id>/",
        teacher_activity_detail,
        name="teacher_activity_detail",
    ),
    path(
        "teacher-activity-monitoring/class/<str:class_id>/",
        class_activity_detail,
        name="class_activity_detail",
    ),
    path(
        "teacher-activity-monitoring/send-reminder/",
        send_activity_reminder,
        name="send_activity_reminder",
    ),
    path(
        "teacher-activity-monitoring/send-reminder/<int:assignment_id>/",
        send_activity_reminder,
        name="send_activity_reminder_with_id",
    ),
    path(
        "teacher-activity-monitoring/reminder-logs/",
        view_reminder_logs,
        name="view_reminder_logs",
    ),
    # API endpoints for AJAX requests
    path("api/academic-years/", get_academic_year_info, name="get_academic_year_info"),
    path("api/terms/", api_get_terms, name="api_get_terms"),
    path("api/subjects/", get_subjects, name="get_subjects"),
    # Current Settings URLs
    path(
        "current-settings/",
        current_settings_dashboard,
        name="current_settings_dashboard",
    ),
    path(
        "api/set-current-academic-year/",
        set_current_academic_year,
        name="set_current_academic_year",
    ),
    path("api/set-current-term/", set_current_term, name="set_current_term"),
    path(
        "api/set-current-settings-both/",
        set_current_settings_both,
        name="set_current_settings_both",
    ),
    path(
        "api/get-terms-for-academic-year/<int:academic_year_id>/",
        get_terms_for_academic_year,
        name="get_terms_for_academic_year",
    ),

    
    # Backup and Restore URLs
    path("backup/", backup_dashboard, name="backup_dashboard"),
    path("backup/create/", create_backup, name="create_backup"),
    path("backup/<int:backup_id>/status/", backup_status, name="backup_status"),
    path("backup/<int:backup_id>/download/", download_backup, name="download_backup"),
    path("backup/<int:backup_id>/delete/", delete_backup, name="delete_backup"),
    
    path("restore/", restore_dashboard, name="restore_dashboard"),
    path("restore/upload/", upload_backup_file, name="upload_backup_file"),
    path("restore/restore/", restore_from_backup, name="restore_from_backup"),
    path("restore/<int:restore_id>/status/", restore_status, name="restore_status"),
    
    path("backup-restore/settings/", backup_restore_settings, name="backup_restore_settings"),
    path("backup-restore/validate/", validate_backup_file, name="validate_backup_file"),
    
    # Backup Settings URLs
    path("backup/settings/", backup_settings, name="backup_settings"),
    path("backup/settings/save/", save_backup_settings, name="save_backup_settings"),
    path("backup/settings/reset/", reset_backup_settings, name="reset_backup_settings"),
    path("backup/cleanup-temp/", cleanup_temp_files, name="cleanup_temp_files"),

]
