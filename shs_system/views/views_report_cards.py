from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, FileResponse, JsonResponse
from django.db.models import Q
from django.template.loader import get_template
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
import csv
import os
from datetime import datetime
from django.urls import reverse
from django.conf import settings
from django.template.loader import render_to_string

# Import models
from shs_system.models import (
    Student,
    Class,
    StudentClass,
    Term,
    ReportCard,
    SchoolInformation,
    Assessment,
    GradingSystem,
    ClassTeacher,
    StudentTermRemarks,
    SchoolAuthoritySignature,
    ClassSubject,
    AcademicYear,
    PerformanceRequirement,
    ScoringConfiguration,
)

# Import utils after models to avoid circular imports
from shs_system.utils.pdf_generator import generate_report_card_pdf
from shs_system.utils import check_promotion_eligibility
from shs_system.views.school_info import set_sweet_alert


# Helper function to get user's school
def get_user_school(user):
    """
    Get the school associated with the current user.
    For superadmins, this will return None (they can access all schools).
    For other users, it will return their associated school.
    """
    if user.is_superadmin:
        return None  # Superadmins can access all schools
    return user.school


def is_admin(user):
    return user.is_authenticated and user.role == "admin"


@login_required
def generate_report_card(request, student_id=None, term_id=None):
    """Generate a report card for a specific student and term"""
    try:
        # Get user's school for multi-tenancy
        user_school = get_user_school(request.user)

        # Get student and term objects with select_related for better performance
        # Apply school filter for multi-tenancy
        if student_id:
            student_query = Student.objects.select_related(
                "form", "learning_area"
            ).filter(pk=student_id)
            if user_school:
                student_query = student_query.filter(school=user_school)
            student = student_query.first()
        else:
            student = None

        if term_id:
            term_query = Term.objects.select_related("academic_year").filter(pk=term_id)
            if user_school:
                term_query = term_query.filter(school=user_school)
            term = term_query.first()
        else:
            term = None

        # If student or term is not provided, return to form
        if not student or not term:
            return redirect("generate_report_card")

        # Get class assignment for the student for the specified term
        # This includes both active and inactive assignments
        # Apply school filter for multi-tenancy
        student_class_query = StudentClass.objects.select_related(
            "assigned_class"
        ).filter(student=student)
        if user_school:
            student_class_query = student_class_query.filter(school=user_school)

        # If we have a specific term, try to find the class assignment for that term
        if term:
            # Get the class assignment that was active during the specified term
            # We'll use the most recent assignment before or during the term
            student_class = (
                student_class_query.filter(
                    date_assigned__lte=(
                        term.end_date if hasattr(term, "end_date") else term.start_date
                    )
                )
                .order_by("-date_assigned")
                .first()
            )
        else:
            # If no specific term, get the current active assignment
            student_class = student_class_query.filter(is_active=True).first()

        if not student_class:
            # Use SweetAlert instead of Django messages
            set_sweet_alert(
                request,
                "Class Assignment Missing",
                "Student was not assigned to any class during the specified period.",
                "error",
            )
            return redirect("generate_report_card")

        current_class = student_class.assigned_class

        # Create or update the report card - add school field to defaults if needed
        report_card_query = ReportCard.objects.filter(
            student=student,
            term=term,
            academic_year=term.academic_year,
            class_assigned=current_class,
        )

        if user_school:
            # If this is a multi-tenant setup and the report card model has a school field
            # (which should be added to the model for complete multi-tenancy)
            if hasattr(ReportCard, "school"):
                report_card_query = report_card_query.filter(school=user_school)

        report_card = report_card_query.first()

        if report_card:
            created = False
        else:
            # Create new report card with school if model supports it
            if hasattr(ReportCard, "school") and user_school:
                report_card = ReportCard.objects.create(
                    student=student,
                    term=term,
                    academic_year=term.academic_year,
                    class_assigned=current_class,
                    generated_by=request.user,
                    school=user_school,
                )
            else:
                report_card = ReportCard.objects.create(
                    student=student,
                    term=term,
                    academic_year=term.academic_year,
                    class_assigned=current_class,
                    generated_by=request.user,
                )
            created = True

        # If newly created or needs update, calculate everything
        if created or request.GET.get("recalculate"):
            report_card.calculate_totals()
            report_card.calculate_attendance()
            report_card.calculate_position()

            # Set promotion status based on term
            if term.term_number == 3:
                # Use the utility function to determine promotion status for Third Term
                eligibility_result = check_promotion_eligibility(
                    student, term.academic_year, [term]  # Consider only this term
                )

                # Update promotion status based on eligibility
                current_form = student.current_form
                if eligibility_result["eligible"]:
                    # If student is in Form 3, they should graduate rather than be promoted
                    if (
                        current_form is not None
                        and hasattr(current_form, "form_number")
                        and current_form.form_number == 3
                    ):
                        report_card.promoted_to = "Graduated"
                    else:
                        # Determine next form
                        next_form = (
                            current_form.form_number + 1
                            if current_form is not None
                            and hasattr(current_form, "form_number")
                            else None
                        )
                        if next_form:
                            report_card.promoted_to = f"Form {next_form}"
                else:
                    # Student is not eligible for promotion
                    form_number = (
                        current_form.form_number
                        if current_form is not None
                        and hasattr(current_form, "form_number")
                        else "Unknown"
                    )
                    report_card.promoted_to = f"Repeat Form {form_number}"

                # Store the reason in principal remarks
                report_card.principal_remarks = eligibility_result["reason"]
            else:
                # For First and Second terms, show "Not Yet"
                report_card.promoted_to = "Not Yet"
                report_card.principal_remarks = (
                    "Promotion decision will be made at the end of the academic year."
                )

            # Set next term date
            report_card.set_next_term_date()
            report_card.save()

        # Force position recalculation if it's not set
        if report_card.position is None or report_card.position <= 1:
            # Get other report cards in same class to see if there should be a different position
            # Apply school filter for multi-tenancy
            other_reports_query = ReportCard.objects.filter(
                class_assigned=current_class,
                term=term,
                academic_year=term.academic_year,
            ).exclude(id=report_card.id)

            if user_school and hasattr(ReportCard, "school"):
                other_reports_query = other_reports_query.filter(school=user_school)

            other_reports = other_reports_query.count()

            if other_reports > 0:
                # Recalculate since there are other students
                report_card.calculate_position()
                report_card.save()

        # Get subjects scores for this student in this term with better performance through select_related
        # Apply school filter for multi-tenancy

        # First, get all class subjects for this class and academic year (only active ones)
        class_subjects = ClassSubject.objects.filter(
            class_name=current_class, academic_year=term.academic_year, is_active=True
        )

        # Then get assessments for these class subjects
        # Exclude mock exam assessments from report card calculations

        subject_scores_query = Assessment.objects.filter(
            student=student,
            class_subject__in=class_subjects,
            term=term,

        ).exclude(assessment_type='mock_exam').select_related("class_subject__subject", "class_subject")


        if user_school:
            subject_scores_query = subject_scores_query.filter(school=user_school)

        subject_scores = subject_scores_query.all()

        # Get class size for student's class (including archived students)
        # Apply school filter for multi-tenancy
        class_size_query = StudentClass.objects.filter(
            assigned_class=current_class,
        )

        if user_school:
            class_size_query = class_size_query.filter(school=user_school)

        class_size = class_size_query.count()

        # Get teacher remarks for this student in this term
        # Apply school filter for multi-tenancy
        teacher_remarks_query = StudentTermRemarks.objects.filter(
            student=student,
            term=term,
            academic_year=term.academic_year,
        )

        if user_school and hasattr(StudentTermRemarks, "school"):
            teacher_remarks_query = teacher_remarks_query.filter(school=user_school)

        teacher_remarks = teacher_remarks_query.first()

        # Get grading system
        # Apply school filter for multi-tenancy
        if user_school:
            grades = GradingSystem.objects.filter(school=user_school).order_by(
                "-min_score"
            )
        else:
            grades = GradingSystem.objects.all().order_by("-min_score")

        # Get school information with prefetch_related for authority signatures
        # For multi-tenancy, get the user's school or active school
        if user_school:
            school_info = user_school
        else:
            school_info = (
                SchoolInformation.objects.filter(is_active=True)
                .prefetch_related("authority_signatures")
                .first()
            )
            if not school_info:
                # Fallback to first school info record if no active one
                school_info = SchoolInformation.objects.prefetch_related(
                    "authority_signatures"
                ).first()

        # Get authority signatures for the appropriate school
        authority_signatures = SchoolAuthoritySignature.objects.filter(
            school=school_info, is_active=True
        )

        # Get active performance requirements for context with school filter
        if user_school:
            performance_requirements = PerformanceRequirement.objects.filter(
                is_active=True, school=user_school
            ).first()
        else:
            performance_requirements = PerformanceRequirement.get_active()

        # Check if format is specified for PDF view/download
        if "format" in request.GET and request.GET.get("format") == "pdf":
            try:
                # Generate PDF
                pdf_file = generate_report_card_pdf(
                    report_card=report_card,
                    subject_scores=subject_scores,
                    teacher_remarks=teacher_remarks,
                    grades=grades,
                    authority_signatures=authority_signatures,
                    school_info=school_info,
                    class_size=class_size,
                )

                # Check if download is requested
                if request.GET.get("download") == "true":
                    response = HttpResponse(pdf_file, content_type="application/pdf")
                    filename = f"report_card_{student.admission_number}_{term.get_term_number_display()}_{term.academic_year}.pdf"
                    response["Content-Disposition"] = (
                        f'attachment; filename="{filename}"'
                    )
                    return response
                else:
                    # Display in browser
                    return HttpResponse(pdf_file, content_type="application/pdf")
            except Exception as e:
                # Use SweetAlert instead of Django messages
                set_sweet_alert(
                    request,
                    "PDF Generation Error",
                    f"Error generating PDF: {str(e)}",
                    "error",
                )

        # Normal HTML response
        context = {
            "report_card": report_card,
            "subject_scores": subject_scores,
            "teacher_remarks": teacher_remarks,
            "grades": grades,
            "authority_signatures": authority_signatures,
            "school_info": school_info,
            "class_size": class_size,
            "performance_requirements": performance_requirements,
            "user_school": user_school,  # Add user's school to context
        }
        return render(request, "reports/report_card.html", context)

    except Exception as e:
        # Use SweetAlert instead of Django messages
        set_sweet_alert(
            request,
            "Error",
            f"Error generating detailed report card: {str(e)}",
            "error",
        )
        return redirect("generate_report_card")


@login_required
@user_passes_test(is_admin)
def bulk_generate_report_cards(request):
    """Generate report cards for all students in a class"""
    # Get user's school for multi-tenancy
    user_school = get_user_school(request.user)

    if request.method == "POST":
        academic_year_id = request.POST.get("academic_year")
        class_id = request.POST.get("class")
        term_id = request.POST.get("term")
    else:
        academic_year_id = request.GET.get("academic_year_id")
        class_id = request.GET.get("class_id")
        term_id = request.GET.get("term_id")

    if not (class_id and term_id):
        # If we don't have class or term, show a form to select them
        # Get all active academic years, terms, and classes with school filter
        academic_years_query = AcademicYear.objects.filter(is_archived=False).order_by(
            "-name"
        )
        if user_school:
            academic_years_query = academic_years_query.filter(school=user_school)
        academic_years = academic_years_query

        # Get selected academic year object, if provided
        selected_academic_year = None
        if academic_year_id:
            try:
                academic_year_query = AcademicYear.objects.filter(id=academic_year_id)
                if user_school:
                    academic_year_query = academic_year_query.filter(school=user_school)
                selected_academic_year = academic_year_query.first()
            except AcademicYear.DoesNotExist:
                pass

        # If academic_year_id is provided, filter terms by that academic year
        if selected_academic_year:
            # Check if the selected academic year is archived
            if selected_academic_year.is_archived:
                terms = Term.objects.none()  # No terms for archived academic years
            else:
                terms_query = Term.objects.filter(
                    academic_year=selected_academic_year
                ).order_by("term_number")
                if user_school:
                    terms_query = terms_query.filter(school=user_school)
                terms = terms_query
        else:
            # Otherwise show terms from all active academic years (filtered by school)
            terms_query = Term.objects.filter(
                academic_year__is_archived=False
            ).order_by("-academic_year__name", "term_number")
            if user_school:
                terms_query = terms_query.filter(school=user_school)
            terms = terms_query

        # Get all classes from active academic years or filter by the selected term if provided
        classes_query = Class.objects.filter(academic_year__is_archived=False).order_by(
            "name"
        )
        if user_school:
            classes_query = classes_query.filter(school=user_school)

        if term_id:
            # Get the term
            try:
                term_query = Term.objects.filter(id=term_id)
                if user_school:
                    term_query = term_query.filter(school=user_school)
                current_term = term_query.first()

                if current_term:

                    # Filter classes by academic year instead of term (only active ones)
                    class_subjects_query = ClassSubject.objects.filter(
                        academic_year=current_term.academic_year, is_active=True

                    )
                    if user_school:
                        class_subjects_query = class_subjects_query.filter(
                            academic_year__school=user_school,
                            class_name__school=user_school,
                        )

                    class_ids = class_subjects_query.values_list(
                        "class_name_id", flat=True
                    ).distinct()
                    classes_query = classes_query.filter(id__in=class_ids)
            except Term.DoesNotExist:
                pass

        classes = classes_query

        context = {
            "academic_years": academic_years,
            "terms": terms,
            "classes": classes,
            "selected_academic_year": selected_academic_year,
            "user_school": user_school,  # Add user's school to context
        }

        return render(request, "reports/bulk_generate_report_cards_form.html", context)

    # Now we have class_id and term_id, so we can generate reports
    try:
        # Get class and term with school filter for multi-tenancy
        class_query = Class.objects.filter(pk=class_id)
        if user_school:
            class_query = class_query.filter(school=user_school)
        class_obj = class_query.first()
        if not class_obj:
            raise Class.DoesNotExist(
                f"Class with ID {class_id} not found or not accessible"
            )

        term_query = Term.objects.filter(pk=term_id)
        if user_school:
            term_query = term_query.filter(school=user_school)
        term = term_query.first()
        if not term:
            raise Term.DoesNotExist(
                f"Term with ID {term_id} not found or not accessible"
            )

        # Get all students who were in the class during the specified term
        # This includes both active students and archived students
        students_query = StudentClass.objects.filter(
            assigned_class=class_obj
        ).select_related("student")

        if user_school:
            students_query = students_query.filter(school=user_school)

        students = students_query

        total_students = students.count()
        report_cards_generated = 0
        error_count = 0
        errors = []  # Store specific error messages

        for student_class in students:
            try:
                # Check if report card exists with school filter
                report_card_query = ReportCard.objects.filter(
                    student=student_class.student,
                    term=term,
                    academic_year=term.academic_year,
                    class_assigned=class_obj,
                )

                if user_school and hasattr(ReportCard, "school"):
                    report_card_query = report_card_query.filter(school=user_school)

                report_card = report_card_query.first()

                if report_card:
                    created = False
                else:
                    # Create new report card with school if model supports it
                    if hasattr(ReportCard, "school") and user_school:
                        report_card = ReportCard.objects.create(
                            student=student_class.student,
                            term=term,
                            academic_year=term.academic_year,
                            class_assigned=class_obj,
                            generated_by=request.user,
                            school=user_school,
                        )
                    else:
                        report_card = ReportCard.objects.create(
                            student=student_class.student,
                            term=term,
                            academic_year=term.academic_year,
                            class_assigned=class_obj,
                            generated_by=request.user,
                        )
                    created = True

                # Check if we should recalculate (new report card, recalculate_all is true, or existing report card has missing data)
                should_recalculate = (
                    created
                    or request.POST.get("recalculate_all") == "true"
                    or (
                        report_card
                        and (
                            report_card.total_score is None
                            or report_card.position is None
                            or report_card.days_present is None
                            or report_card.total_school_days is None
                        )
                    )
                )

                if should_recalculate:
                    try:
                        print(
                            f"Recalculating report card for student {student_class.student.full_name} in term {term.get_term_number_display()}"
                        )
                        report_card.calculate_totals()
                        report_card.calculate_attendance()
                        report_card.calculate_position()
                        print(
                            f"Calculations completed - Total: {report_card.total_score}, Position: {report_card.position}, Attendance: {report_card.days_present}/{report_card.total_school_days}"
                        )
                    except Exception as calc_error:
                        print(
                            f"Error during calculations for {student_class.student.full_name}: {str(calc_error)}"
                        )
                        # Set default values if calculations fail
                        if report_card.total_score is None:
                            report_card.total_score = 0
                        if report_card.average_marks is None:
                            report_card.average_marks = 0
                        if report_card.position is None:
                            report_card.position = 1
                        if report_card.days_present is None:
                            report_card.days_present = 0
                        if report_card.total_school_days is None:
                            report_card.total_school_days = 0

                    # Set promotion status based on term
                    if term.term_number == 3:
                        # Use the utility function to determine promotion status for Third Term
                        eligibility_result = check_promotion_eligibility(
                            student_class.student,
                            term.academic_year,
                            [term],  # Consider only this term
                        )

                        # Update promotion status based on eligibility
                        current_form = student_class.student.current_form
                        if eligibility_result["eligible"]:
                            # If student is in Form 3, they should graduate rather than be promoted
                            if (
                                current_form is not None
                                and hasattr(current_form, "form_number")
                                and current_form.form_number == 3
                            ):
                                report_card.promoted_to = "Graduated"
                            else:
                                # Determine next form
                                next_form = (
                                    current_form.form_number + 1
                                    if current_form is not None
                                    and hasattr(current_form, "form_number")
                                    else None
                                )
                                if next_form:
                                    report_card.promoted_to = f"Form {next_form}"
                        else:
                            # Student is not eligible for promotion
                            form_number = (
                                current_form.form_number
                                if current_form is not None
                                and hasattr(current_form, "form_number")
                                else "Unknown"
                            )
                            report_card.promoted_to = f"Repeat Form {form_number}"

                        # Store the reason in principal remarks
                        report_card.principal_remarks = eligibility_result["reason"]
                    else:
                        # For First and Second terms, show "Not Yet"
                        report_card.promoted_to = "Not Yet"
                        report_card.principal_remarks = "Promotion decision will be made at the end of the academic year."

                # Set next term date
                report_card.set_next_term_date()
                report_card.save()
                report_cards_generated += 1
            except Student.DoesNotExist:
                error_count += 1
                student_name = getattr(student_class, "student", {}).get(
                    "full_name", "Unknown"
                )
                errors.append(f"Student record not found for {student_name}")
            except Term.DoesNotExist:
                error_count += 1
                errors.append(f"Term record not found: {term_id}")
            except Exception as e:
                error_count += 1
                student_name = getattr(student_class.student, "full_name", "Unknown")
                error_msg = (
                    f"Error generating report card for student {student_name}: {str(e)}"
                )
                print(error_msg)
                errors.append(error_msg)

        # If request includes redirect parameter, go to report card list
        if request.GET.get("redirect") == "list":
            # Use SweetAlert instead of Django messages
            set_sweet_alert(
                request,
                "Report Cards Generated",
                f"Successfully generated/updated {report_cards_generated} report cards for {class_obj.name}",
                "success",
            )
            return redirect("report_card_list")

        # Otherwise show detailed results page
        # Get performance requirements with school filter
        if user_school:
            performance_requirements = PerformanceRequirement.objects.filter(
                is_active=True, school=user_school
            ).first()
        else:
            performance_requirements = PerformanceRequirement.get_active()

        context = {
            "generated_count": report_cards_generated,
            "error_count": error_count,
            "errors": errors[:10],  # Show first 10 errors
            "class_name": class_obj.name,
            "term_name": term.get_term_number_display(),
            "academic_year": term.academic_year,
            "total_students": total_students,
            "generation_date": timezone.now().strftime("%d %b, %Y %H:%M"),
            "class_id": class_id,
            "term_id": term_id,
            "performance_requirements": performance_requirements,
            "user_school": user_school,  # Add user's school to context
        }

        return render(request, "reports/bulk_generate_results.html", context)

    except Class.DoesNotExist as e:
        # Use SweetAlert instead of Django messages
        set_sweet_alert(
            request,
            "Class Not Found",
            f"The specified class (ID: {class_id}) does not exist or you don't have access to it.",
            "error",
        )
        return redirect("report_card_list")
    except Term.DoesNotExist as e:
        # Use SweetAlert instead of Django messages
        set_sweet_alert(
            request,
            "Term Not Found",
            f"The specified term (ID: {term_id}) does not exist or you don't have access to it.",
            "error",
        )
        return redirect("report_card_list")
    except Exception as e:
        # Use SweetAlert instead of Django messages
        set_sweet_alert(
            request,
            "Generation Error",
            f"Failed to generate report cards: {str(e)}",
            "error",
        )
        return redirect("report_card_list")


@login_required
@user_passes_test(is_admin)
def approve_report_card(request, report_card_id):
    """Approve a student's report card"""
    report_card = get_object_or_404(ReportCard, pk=report_card_id)

    if request.method == "POST":
        report_card.is_approved = True
        report_card.approved_by = request.user
        report_card.save()

        # Use SweetAlert instead of Django messages
        set_sweet_alert(
            request,
            "Report Card Approved",
            f"Report card for {report_card.student.full_name} has been approved.",
            "success",
        )

        return redirect("report_card_list")

    # If not a POST request, redirect to report card list
    return redirect("report_card_list")


@login_required
def view_student_report_cards(request, student_id):
    """View all report cards for a specific student"""
    try:
        # Get user's school for multi-tenancy
        user_school = get_user_school(request.user)

        # Security check: If user is a student, they can only view their own report cards
        if request.user.role == "student" and hasattr(request.user, "student_profile"):
            # Get the student's own profile
            student = request.user.student_profile

            # Verify the requested student_id matches the logged-in student
            if str(student.id) != str(student_id):
                # Use SweetAlert to notify unauthorized access
                set_sweet_alert(
                    request,
                    "Unauthorized",
                    "You can only view your own report cards.",
                    "error",
                )
                return redirect("student_dashboard")
        else:
            # For admin and teachers, allow viewing any student's report cards with school filter
            student_query = Student.objects.filter(pk=student_id)
            if user_school:
                student_query = student_query.filter(school=user_school)

            student = student_query.first()

            if not student:
                set_sweet_alert(
                    request,
                    "Not Found",
                    "Student not found or you don't have access to this student's records.",
                    "error",
                )
                return redirect("student_list")

        # Filter report cards by student and school
        report_cards_query = ReportCard.objects.filter(student=student).order_by(
            "-academic_year", "-term__term_number"
        )

        # Apply school filter for multi-tenancy
        if user_school and hasattr(ReportCard, "school"):
            report_cards_query = report_cards_query.filter(school=user_school)

        report_cards = report_cards_query

        context = {
            "student": student,
            "report_cards": report_cards,
            "user_school": user_school,  # Add user's school to context
        }

        return render(request, "reports/student_report_cards.html", context)

    except Exception as e:
        # Use SweetAlert instead of Django messages
        set_sweet_alert(
            request, "Error", f"Error viewing student report cards: {str(e)}", "error"
        )
        # Redirect based on user role
        if request.user.role == "student":
            return redirect("student_dashboard")
        else:
            return redirect("student_list")


@login_required
def report_card_list(request):
    """List all report cards with filtering options"""
    # Get user's school for multi-tenancy
    user_school = get_user_school(request.user)

    # Initialize query with school filter for multi-tenancy
    report_cards = ReportCard.objects.all().order_by(
        "-term__academic_year", "-term__term_number"
    )

    # Apply school filter for multi-tenancy
    if user_school and hasattr(ReportCard, "school"):
        report_cards = report_cards.filter(school=user_school)

    # Get filter parameters
    academic_year = request.GET.get("academic_year")
    term_id = request.GET.get("term")
    class_id = request.GET.get("class")
    search = request.GET.get("search")
    approval_status = request.GET.get("approval_status")
    min_score = request.GET.get("min_score")
    max_score = request.GET.get("max_score")

    # Apply filters
    if academic_year:
        report_cards = report_cards.filter(academic_year=academic_year)
    if term_id:
        report_cards = report_cards.filter(term_id=term_id)
    if class_id:
        report_cards = report_cards.filter(class_assigned_id=class_id)
    if search:
        report_cards = report_cards.filter(
            Q(student__full_name__icontains=search)
            | Q(student__admission_number__icontains=search)
        )
    if approval_status:
        if approval_status == "approved":
            report_cards = report_cards.filter(is_approved=True)
        elif approval_status == "pending":
            report_cards = report_cards.filter(is_approved=False)
    if min_score:
        try:
            min_score_float = float(min_score)
            report_cards = report_cards.filter(total_score__gte=min_score_float)
        except ValueError:
            pass
    if max_score:
        try:
            max_score_float = float(max_score)
            report_cards = report_cards.filter(total_score__lte=max_score_float)
        except ValueError:
            pass

    # Prepare filters for pagination
    filter_params = {}
    if academic_year:
        filter_params["academic_year"] = academic_year
    if term_id:
        filter_params["term"] = term_id
    if class_id:
        filter_params["class"] = class_id
    if search:
        filter_params["search"] = search
    if approval_status:
        filter_params["approval_status"] = approval_status
    if min_score:
        filter_params["min_score"] = min_score
    if max_score:
        filter_params["max_score"] = max_score

    # Create filter query string for pagination links
    filter_query = "&".join([f"{key}={value}" for key, value in filter_params.items()])


    # Get all filtered report card IDs before pagination
    all_filtered_ids = list(report_cards.values_list('id', flat=True))


    # Paginate results
    paginator = Paginator(report_cards, 25)  # Show 25 report cards per page
    page = request.GET.get("page")
    try:
        report_cards = paginator.page(page)
    except PageNotAnInteger:
        report_cards = paginator.page(1)
    except EmptyPage:
        report_cards = paginator.page(paginator.num_pages)

    # Get available academic years, terms, and classes with school filter for multi-tenancy
    # Exclude archived academic years and terms from archived academic years
    if user_school:
        academic_years = (
            AcademicYear.objects.filter(school=user_school, is_archived=False)
            .distinct()
            .order_by("-name")
        )
        terms = Term.objects.filter(
            school=user_school, academic_year__is_archived=False
        ).order_by("-academic_year", "-term_number")
        classes = Class.objects.filter(
            school=user_school, academic_year__is_archived=False
        ).order_by("name")
    else:
        academic_years = (
            AcademicYear.objects.filter(is_archived=False).distinct().order_by("-name")
        )
        terms = Term.objects.filter(academic_year__is_archived=False).order_by(
            "-academic_year", "-term_number"
        )
        classes = Class.objects.filter(academic_year__is_archived=False).order_by(
            "name"
        )

    context = {
        "report_cards": report_cards,
        "academic_years": academic_years,
        "terms": terms,
        "classes": classes,
        "filter_query": filter_query,

        "all_filtered_ids": all_filtered_ids,  # Add all filtered IDs for bulk actions

        "user_school": user_school,  # Add user's school to context
    }

    return render(request, "reports/report_card_list.html", context)


@login_required
def view_report_card_details(request, report_card_id):
    """
    View a specific report card detail
    """
    try:
        # Get user's school for multi-tenancy
        user_school = get_user_school(request.user)

        # Get report card with school filter for multi-tenancy
        report_card_query = ReportCard.objects.filter(id=report_card_id)
        if user_school and hasattr(ReportCard, "school"):
            report_card_query = report_card_query.filter(school=user_school)

        report_card = report_card_query.first()

        if not report_card:
            # Use SweetAlert to notify if report card not found or not accessible
            set_sweet_alert(
                request,
                "Not Found",
                "Report card not found or you don't have access to it.",
                "error",
            )
            return redirect("report_card_list")

        # Get all subject scores for this report card with school filter

        # First, get all class subjects for this class and academic year (only active ones)
        class_subjects = ClassSubject.objects.filter(
            class_name=report_card.class_assigned,
            academic_year=report_card.academic_year,
            is_active=True
        )

        # Then get assessments for these class subjects
        # Exclude mock exam assessments from report card calculations

        subject_scores_query = Assessment.objects.filter(
            student=report_card.student,
            class_subject__in=class_subjects,
            term=report_card.term,

        ).exclude(assessment_type='mock_exam').select_related("class_subject__subject")


        if user_school:
            subject_scores_query = subject_scores_query.filter(school=user_school)

        subject_scores = subject_scores_query.all()

        # Count total students in the class for position calculation with school filter
        class_size_query = ReportCard.objects.filter(
            class_assigned=report_card.class_assigned,
            academic_year=report_card.academic_year,
        )

        if user_school and hasattr(ReportCard, "school"):
            class_size_query = class_size_query.filter(school=user_school)

        class_size = class_size_query.count()

        # Get school information - for multi-tenancy, use user's school
        if user_school:
            school_info = user_school
        else:
            school_info = SchoolInformation.objects.first()

        # Get the grading system with school filter
        if user_school:
            grades = GradingSystem.objects.filter(school=user_school).order_by(
                "-min_score"
            )
        else:
            grades = GradingSystem.objects.all().order_by("-min_score")

        # Get teacher remarks with school filter
        teacher_remarks_query = StudentTermRemarks.objects.filter(
            student=report_card.student,
            term=report_card.term,
            academic_year=report_card.academic_year,
        )

        if user_school and hasattr(StudentTermRemarks, "school"):
            teacher_remarks_query = teacher_remarks_query.filter(school=user_school)

        teacher_remarks = teacher_remarks_query.first()

        # Get class teacher if available with school filter
        class_teacher = None
        try:
            class_teacher_query = ClassTeacher.objects.filter(
                class_assigned=report_card.class_assigned,
                academic_year=report_card.academic_year,
            )

            if user_school:
                class_teacher_query = class_teacher_query.filter(school=user_school)

            class_teacher = class_teacher_query.first()

            if not report_card.class_teacher_remarks and class_teacher:
                report_card.class_teacher_remarks = "Keep up the good work."
        except ClassTeacher.DoesNotExist:
            pass

        # Get authority signatures for the appropriate school
        authority_signatures_query = SchoolAuthoritySignature.objects.filter(
            is_active=True
        ).order_by("authority_type")

        if user_school:
            authority_signatures_query = authority_signatures_query.filter(
                school=user_school
            )
        elif school_info:
            authority_signatures_query = authority_signatures_query.filter(
                school=school_info
            )

        authority_signatures = authority_signatures_query

        # Calculate average score from subject scores
        total_points = sum(score.total_score or 0 for score in subject_scores)
        num_subjects = len(subject_scores)
        average = total_points / num_subjects if num_subjects > 0 else 0

        # Add subject_scores to report_card object for the template
        report_card.subject_scores = subject_scores

        # Add class_size to report_card object for the template
        report_card.class_size = class_size

        # Add teacher_remarks to report_card object for the template
        report_card.teacher_remarks = teacher_remarks

        # Add authority_signatures to report_card object for the template
        report_card.authority_signatures = authority_signatures

        # Check if format is specified for PDF view/download
        if "format" in request.GET and request.GET.get("format") == "pdf":
            try:
                # Generate PDF
                pdf_file = generate_report_card_pdf(
                    report_card=report_card,
                    subject_scores=subject_scores,
                    teacher_remarks=teacher_remarks,
                    grades=grades,
                    authority_signatures=authority_signatures,
                    school_info=school_info,
                    class_size=class_size,
                )

                # Check if download is requested
                if request.GET.get("download") == "true":
                    response = HttpResponse(pdf_file, content_type="application/pdf")
                    filename = f"report_card_{report_card.student.admission_number}_{report_card.term.get_term_number_display()}_{report_card.academic_year}.pdf"
                    response["Content-Disposition"] = (
                        f'attachment; filename="{filename}"'
                    )
                    return response
                else:
                    # Display in browser
                    return HttpResponse(pdf_file, content_type="application/pdf")
            except Exception as e:
                # Use SweetAlert instead of Django messages
                set_sweet_alert(
                    request,
                    "PDF Generation Error",
                    f"Error generating PDF: {str(e)}",
                    "error",
                )

        # Get active performance requirements for context with school filter
        if user_school:
            performance_requirements = PerformanceRequirement.objects.filter(
                is_active=True, school=user_school
            ).first()
        else:
            performance_requirements = PerformanceRequirement.get_active()

        # Get scoring configuration for dynamic percentages
        scoring_config = None
        if user_school:
            scoring_config = ScoringConfiguration.get_active_config(user_school)

        context = {
            "report_cards": [
                report_card
            ],  # Put in a list for batch_print_report_cards.html template
            "school_info": school_info,
            "grades": grades,
            "performance_requirements": performance_requirements,
            "is_individual_view": True,  # Flag to identify individual view vs bulk printing
            "user_school": user_school,  # Add user's school to context
            "scoring_config": scoring_config,  # Add scoring configuration for dynamic percentages
        }

        return render(request, "reports/batch_print_report_cards.html", context)
    except ReportCard.DoesNotExist:
        # Use SweetAlert instead of Django messages
        set_sweet_alert(request, "Not Found", "Report card not found", "error")
        return redirect("report_card_list")


@login_required
@user_passes_test(is_admin)
def delete_report_card(request, report_card_id):
    """Delete a student's report card"""
    # Get user's school for multi-tenancy
    user_school = get_user_school(request.user)

    # Debug information
    print(f"DELETE REPORT CARD VIEW - ID: {report_card_id}")
    print(f"Request method: {request.method}")
    print(f"Request POST data: {request.POST}")
    print(f"Request path: {request.path}")
    print(f"User school: {user_school}")

    # Get report card with school filter for multi-tenancy
    report_card_query = ReportCard.objects.filter(pk=report_card_id)
    if user_school and hasattr(ReportCard, "school"):
        report_card_query = report_card_query.filter(school=user_school)

    report_card = report_card_query.first()

    if not report_card:
        # Use SweetAlert to notify if report card not found or not accessible
        set_sweet_alert(
            request,
            "Not Found",
            "Report card not found or you don't have access to it.",
            "error",
        )
        return redirect("report_card_list")

    if request.method == "POST":
        try:
            # Get student and term for the message
            student_name = report_card.student.full_name
            term_name = report_card.term.get_term_number_display()

            print(f"Found report card: Student: {student_name}, Term: {term_name}")

            # Delete the report card
            report_card.delete()
            print(f"Report card deleted successfully")

            # Use SweetAlert instead of Django messages
            set_sweet_alert(
                request,
                "Report Card Deleted",
                f"Report card for {student_name} - {term_name} has been deleted.",
                "success",
            )
            return redirect("report_card_list")
        except Exception as e:
            # Log the error and provide a clear error message
            import logging
            import traceback

            logger = logging.getLogger(__name__)
            logger.error(f"Error deleting report card ID {report_card_id}: {str(e)}")
            print(f"ERROR DELETING REPORT CARD: {str(e)}")
            print(traceback.format_exc())

            # Use SweetAlert to show error
            set_sweet_alert(
                request,
                "Deletion Error",
                f"Failed to delete report card: {str(e)}",
                "error",
            )
            return redirect("report_card_list")

    # If not a POST request, redirect to report card list
    print("Not a POST request, redirecting")
    return redirect("report_card_list")


@login_required
def batch_print_report_cards(request):
    """Display multiple report cards for batch printing"""
    # Get user's school for multi-tenancy
    user_school = get_user_school(request.user)

    # Debug information
    print(f"BATCH PRINT VIEW CALLED")
    print(f"Request method: {request.method}")
    print(f"Request path: {request.path}")
    print(f"User school: {user_school}")

    if request.method != "POST":
        print("Not a POST request, redirecting")
        return redirect("report_card_list")

    report_card_ids = request.POST.getlist("report_card_ids")
    print(f"Report card IDs from POST: {report_card_ids}")

    if not report_card_ids:
        print("No report card IDs in request")
        # Use SweetAlert instead of Django messages with clearer message about batch printing
        set_sweet_alert(
            request,
            "Batch Print - No Selection",
            "No report cards selected for batch printing. Please check at least one checkbox before using the 'Print Selected Report Cards' action.",
            "error",
        )
        return redirect("report_card_list")

    # Get all selected report cards
    report_cards = []

    for report_id in report_card_ids:
        try:
            # Get report card with school filter for multi-tenancy
            report_card_query = ReportCard.objects.filter(id=report_id)
            if user_school and hasattr(ReportCard, "school"):
                report_card_query = report_card_query.filter(school=user_school)

            report_card = report_card_query.first()

            if not report_card:
                # Skip if report card not found or not accessible
                continue

            # If position is not calculated (is 1 or None), recalculate
            if report_card.position is None or report_card.position == 1:
                report_card.calculate_totals()
                report_card.calculate_position()
                report_card.save()

            # Get subject scores for this student in this term with school filter

            # First, get all class subjects for this class and academic year (only active ones)
            class_subjects = ClassSubject.objects.filter(
                class_name=report_card.class_assigned,
                academic_year=report_card.academic_year,
                is_active=True
            )

            # Then get assessments for these class subjects
            # Exclude mock exam assessments from report card calculations

            subject_scores_query = Assessment.objects.filter(
                student=report_card.student,
                class_subject__in=class_subjects,
                term=report_card.term,

            ).exclude(assessment_type='mock_exam').select_related("class_subject__subject")


            if user_school:
                subject_scores_query = subject_scores_query.filter(school=user_school)

            subject_scores = subject_scores_query.all()

            # Get teacher remarks for this student in this term with school filter
            teacher_remarks_query = StudentTermRemarks.objects.filter(
                student=report_card.student,
                term=report_card.term,
                academic_year=report_card.academic_year,
            )

            if user_school and hasattr(StudentTermRemarks, "school"):
                teacher_remarks_query = teacher_remarks_query.filter(school=user_school)

            teacher_remarks = teacher_remarks_query.first()

            # Add subject scores and teacher remarks to report card object
            report_card.subject_scores = subject_scores
            report_card.teacher_remarks = teacher_remarks

            # Calculate and get class size with school filter
            class_size_query = StudentClass.objects.filter(
                assigned_class=report_card.class_assigned,
                is_active=True,
            )

            if user_school:
                class_size_query = class_size_query.filter(school=user_school)

            class_size = class_size_query.count()

            # Store class size directly on report card object for template access
            report_card.class_size = class_size

            # Calculate average score
            total_points = sum(score.total_score or 0 for score in subject_scores)
            num_subjects = len(subject_scores)
            report_card.average = total_points / num_subjects if num_subjects > 0 else 0

            # Add authority signatures with school filter
            authority_signatures_query = SchoolAuthoritySignature.objects.filter(
                is_active=True
            )
            if user_school:
                authority_signatures_query = authority_signatures_query.filter(
                    school=user_school
                )
            else:
                # If no user_school, try to filter by school from active school info
                active_school = SchoolInformation.objects.filter(is_active=True).first()
                if active_school:
                    authority_signatures_query = authority_signatures_query.filter(
                        school=active_school
                    )

            report_card.authority_signatures = authority_signatures_query

            report_cards.append(report_card)

        except ReportCard.DoesNotExist:
            continue
        except Exception as e:
            # Log any other errors during report card processing
            import logging

            logger = logging.getLogger(__name__)
            logger.error(
                f"Error processing report card ID {report_id} for batch print: {str(e)}"
            )
            continue

    # If no report cards could be processed, show an error
    if not report_cards:
        set_sweet_alert(
            request,
            "Batch Print Failed",
            "Could not process any of the selected report cards for printing.",
            "error",
        )
        return redirect("report_card_list")

    # Get school information - for multi-tenancy, use user's school
    if user_school:
        school_info = user_school
    else:
        school_info = SchoolInformation.objects.filter(is_active=True).first()
        if not school_info:
            # Fallback to first school info record if no active one
            school_info = SchoolInformation.objects.first()

    # Get grading system with school filter
    if user_school:
        grades = GradingSystem.objects.filter(school=user_school).order_by("-min_score")
    else:
        grades = GradingSystem.objects.all().order_by("-min_score")

    # Get active performance requirements for context with school filter
    if user_school:
        performance_requirements = PerformanceRequirement.objects.filter(
            is_active=True, school=user_school
        ).first()
    else:
        performance_requirements = PerformanceRequirement.get_active()

    # Get scoring configuration for dynamic percentages
    scoring_config = None
    if user_school:
        scoring_config = ScoringConfiguration.get_active_config(user_school)

    context = {
        "report_cards": report_cards,
        "school_info": school_info,
        "grades": grades,
        "performance_requirements": performance_requirements,
        "is_individual_view": False,  # This is batch printing, not individual view
        "user_school": user_school,  # Add user's school to context
        "scoring_config": scoring_config,  # Add scoring configuration for dynamic percentages
    }

    return render(request, "reports/batch_print_report_cards.html", context)


@login_required
@user_passes_test(is_admin)
def bulk_approve_report_cards(request):
    """Approve multiple report cards at once"""
    # Get user's school for multi-tenancy
    user_school = get_user_school(request.user)

    if request.method != "POST":
        return redirect("report_card_list")

    report_card_ids = request.POST.getlist("report_card_ids")
    filter_query = request.POST.get("filter_query", "")

    if not report_card_ids:
        # Use SweetAlert instead of Django messages
        set_sweet_alert(
            request, "No Selection", "No report cards selected for approval.", "error"
        )
        redirect_url = reverse("report_card_list")
        if filter_query:
            redirect_url = f"{redirect_url}?{filter_query}"
        return redirect(redirect_url)

    # Get all pending report cards from the selection with school filter
    pending_report_cards_query = ReportCard.objects.filter(
        id__in=report_card_ids, is_approved=False
    )

    if user_school and hasattr(ReportCard, "school"):
        pending_report_cards_query = pending_report_cards_query.filter(
            school=user_school
        )

    pending_report_cards = pending_report_cards_query

    approved_count = 0
    for report_card in pending_report_cards:
        report_card.is_approved = True
        report_card.approved_by = request.user
        report_card.save()
        approved_count += 1

    if approved_count > 0:
        # Use SweetAlert instead of Django messages
        set_sweet_alert(
            request,
            "Approval Successful",
            f"Successfully approved {approved_count} report card(s).",
            "success",
        )
    else:
        # Use SweetAlert instead of Django messages
        set_sweet_alert(
            request,
            "No Action Taken",
            "No pending report cards were found in your selection.",
            "info",
        )

    # Use the correct redirect format
    redirect_url = reverse("report_card_list")
    if filter_query:
        redirect_url = f"{redirect_url}?{filter_query}"
    return redirect(redirect_url)


@login_required
@user_passes_test(is_admin)
def bulk_delete_report_cards(request):
    """Delete multiple report cards at once"""
    # Get user's school for multi-tenancy
    user_school = get_user_school(request.user)

    if request.method != "POST":
        return redirect("report_card_list")

    report_card_ids = request.POST.getlist("report_card_ids")
    filter_query = request.POST.get("filter_query", "")

    if not report_card_ids:
        # Use SweetAlert instead of Django messages
        set_sweet_alert(
            request, "No Selection", "No report cards selected for deletion.", "error"
        )
        redirect_url = reverse("report_card_list")
        if filter_query:
            redirect_url = f"{redirect_url}?{filter_query}"
        return redirect(redirect_url)

    # Delete the selected report cards with school filter
    report_cards_to_delete_query = ReportCard.objects.filter(id__in=report_card_ids)
    if user_school and hasattr(ReportCard, "school"):
        report_cards_to_delete_query = report_cards_to_delete_query.filter(
            school=user_school
        )

    deleted_count = report_cards_to_delete_query.delete()[0]

    if deleted_count > 0:
        # Use SweetAlert instead of Django messages
        set_sweet_alert(
            request,
            "Deletion Successful",
            f"Successfully deleted {deleted_count} report card(s).",
            "success",
        )
    else:
        # Use SweetAlert instead of Django messages
        set_sweet_alert(
            request, "Deletion Failed", "No report cards were deleted.", "error"
        )

    # Use the correct redirect format
    redirect_url = reverse("report_card_list")
    if filter_query:
        redirect_url = f"{redirect_url}?{filter_query}"
    return redirect(redirect_url)


@login_required
def get_classes_by_term(request):
    """API endpoint to get classes for a specific term or academic year"""
    term_id = request.GET.get("term_id")
    academic_year = request.GET.get("academic_year")

    # Base query for classes from active academic years only
    classes_query = Class.objects.filter(academic_year__is_archived=False)

    # Filter by term if provided
    if term_id:
        try:
            # Get the term
            term = Term.objects.get(id=term_id)

            # Check if the term's academic year is archived
            if term.academic_year.is_archived:
                classes_query = (
                    Class.objects.none()
                )  # No classes for archived academic years
            else:

                # Find classes that have subjects in this term's academic year (only active ones)
                class_ids = (
                    ClassSubject.objects.filter(academic_year=term.academic_year, is_active=True)

                    .values_list("class_name_id", flat=True)
                    .distinct()
                )

                classes_query = classes_query.filter(id__in=class_ids)
        except Term.DoesNotExist:
            pass

    # Filter by academic year if provided and term is not
    elif academic_year:
        try:
            # Get the academic year object to check if it's archived
            academic_year_obj = AcademicYear.objects.get(id=academic_year)
            if academic_year_obj.is_archived:
                classes_query = (
                    Class.objects.none()
                )  # No classes for archived academic years
            else:

                # Find classes with subjects in this academic year directly (only active ones)
                class_ids = (
                    ClassSubject.objects.filter(academic_year=academic_year, is_active=True)

                    .values_list("class_name_id", flat=True)
                    .distinct()
                )

                classes_query = classes_query.filter(id__in=class_ids)
        except (AcademicYear.DoesNotExist, Exception) as e:
            print(f"Error filtering classes by academic year: {str(e)}")

    # Get the final list of classes
    classes = classes_query.order_by("name")

    # Prepare the response data
    response_data = {
        "classes": [{"id": str(cls.id), "name": cls.name} for cls in classes]
    }

    return JsonResponse(response_data)


@login_required
def get_terms_for_bulk_generate(request, academic_year_id):
    """
    API endpoint specifically for the bulk report card generation form.
    Returns terms filtered by academic year.
    """
    # Debug information - log URL path and request info
    print("=" * 50)
    print(f"DEBUG - get_terms_for_bulk_generate called")
    print(f"Request path: {request.path}")
    print(f"Academic year ID: {academic_year_id}")
    print(f"Request method: {request.method}")
    print(f"Content type: {request.content_type}")
    print("=" * 50)

    try:
        # Log the incoming request for debugging
        print(
            f"get_terms_for_bulk_generate called with academic_year_id: {academic_year_id}"
        )

        # Get the academic year - handle both numeric and string IDs
        try:
            academic_year_id = int(academic_year_id)
            academic_year = get_object_or_404(AcademicYear, pk=academic_year_id)
        except ValueError:
            # If academic_year_id is not an integer, try to get by name
            academic_year = get_object_or_404(AcademicYear, name=academic_year_id)

        print(f"Found academic year: {academic_year.name} (ID: {academic_year.id})")

        # Check if academic year is archived
        if academic_year.is_archived:
            print(
                f"Academic year {academic_year.name} is archived, returning empty terms"
            )
            return JsonResponse(
                {
                    "error": "Cannot access terms for archived academic year.",
                    "terms": [],
                },
                status=400,
            )

        # Get terms for this academic year
        terms = Term.objects.filter(academic_year=academic_year).order_by("term_number")
        print(f"Found {terms.count()} terms for academic year {academic_year.name}")

        # Format the terms as JSON
        terms_data = []
        for term in terms:
            # Get term name in the format "Academic Year - Term Name"
            term_name = f"{term.get_term_number_display()} - {term.academic_year}"
            terms_data.append({"id": term.id, "name": term_name})
            print(f"Added term: {term_name} (ID: {term.id})")

        # Return as JSON response
        return JsonResponse({"terms": terms_data})
    except Exception as e:
        print(f"Error in get_terms_for_bulk_generate: {str(e)}")
        # Return a more detailed error response for debugging
        error_msg = f"Failed to retrieve terms: {str(e)}"
        print(error_msg)
        return JsonResponse({"error": error_msg, "terms": []}, status=400)


@login_required
def get_terms_by_academic_year(request):
    """
    API endpoint specifically for the report card list.
    Returns terms filtered by academic year.
    """
    # Enhanced debugging
    print("=" * 80)
    print(f"DEBUG - get_terms_by_academic_year called")
    print(f"Full request path: {request.path}")
    print(f"Full GET parameters: {request.GET}")
    print(f"All GET parameters: {dict(request.GET)}")
    print(f"academic_year_id parameter: {request.GET.get('academic_year_id')}")
    print(f"Parameter type: {type(request.GET.get('academic_year_id'))}")

    # Backup check for alternative parameter names
    alt_param = None
    if "academic_year" in request.GET:
        alt_param = request.GET.get("academic_year")
        print(f"Found alternative parameter 'academic_year': {alt_param}")

    # Get the academic_year_id parameter
    academic_year_id = request.GET.get("academic_year_id")
    if not academic_year_id and alt_param:
        academic_year_id = alt_param
        print(f"Using alternative parameter value: {academic_year_id}")

    # Log all headers for debugging
    print("Request Headers:")
    for header, value in request.headers.items():
        print(f"  {header}: {value}")
    print("=" * 80)

    try:
        # If academic_year_id is None, empty string, or whitespace - return all terms
        if not academic_year_id or (
            isinstance(academic_year_id, str) and academic_year_id.strip() == ""
        ):
            print("No meaningful academic_year_id provided, returning all terms")
            try:
                terms = Term.objects.filter(academic_year__is_archived=False).order_by(
                    "-academic_year__name", "term_number"
                )
                terms_data = []
                for term in terms:
                    try:
                        term_name = (
                            f"{term.get_term_number_display()} - {term.academic_year}"
                        )
                        terms_data.append({"id": term.id, "name": term_name})
                    except Exception as term_err:
                        print(f"Error formatting term {term.id}: {str(term_err)}")
                        # Skip this term and continue
                        continue

                print(f"Returning {len(terms_data)} terms (all years)")
                return JsonResponse({"terms": terms_data})
            except Exception as all_terms_err:
                print(f"Error getting all terms: {str(all_terms_err)}")
                import traceback

                traceback.print_exc()
                return JsonResponse(
                    {
                        "error": f"Error getting all terms: {str(all_terms_err)}",
                        "terms": [],
                    },
                    status=500,
                )

        # Get the academic year - try to convert to int first
        try:
            if (
                academic_year_id and academic_year_id.strip() != ""
            ):  # Avoid conversion on empty strings
                academic_year_id_int = int(academic_year_id)
                print(f"Converted academic_year_id to integer: {academic_year_id_int}")
                academic_year_id = academic_year_id_int
        except (ValueError, TypeError, AttributeError) as e:
            print(f"Could not convert academic_year_id to integer: {str(e)}")
            # Continue with the original value

        # Get the academic year object
        academic_year = None
        try:
            academic_year = AcademicYear.objects.get(pk=academic_year_id)
            print(
                f"Found academic year by ID: {academic_year.name} (ID: {academic_year.id})"
            )
        except (AcademicYear.DoesNotExist, ValueError, TypeError) as lookup_error:
            print(f"Academic year lookup error: {str(lookup_error)}")
            # Try to get by name if ID lookup fails
            try:
                academic_year = AcademicYear.objects.get(name=academic_year_id)
                print(
                    f"Found academic year by name: {academic_year.name} (ID: {academic_year.id})"
                )
            except AcademicYear.DoesNotExist:
                print(f"Academic year not found by name: {academic_year_id}")

                # Try one more attempt with a more flexible query
                try:
                    matching_years = list(
                        AcademicYear.objects.filter(
                            name__icontains=str(academic_year_id)
                        )
                    )
                    if matching_years:
                        academic_year = matching_years[0]
                        print(
                            f"Found academic year by partial match: {academic_year.name} (ID: {academic_year.id})"
                        )
                    else:
                        print(f"No academic years match pattern: {academic_year_id}")
                except Exception as flexible_err:
                    print(
                        f"Error in flexible academic year search: {str(flexible_err)}"
                    )

                if not academic_year:
                    error_msg = (
                        f"Academic year not found with ID or name: {academic_year_id}"
                    )
                    print(error_msg)
                    # Return all terms as a fallback when academic year not found
                    try:
                        all_terms = Term.objects.filter(
                            academic_year__is_archived=False
                        ).order_by("-academic_year__name", "term_number")
                        all_terms_data = []
                        for term in all_terms:
                            try:
                                term_name = f"{term.get_term_number_display()} - {term.academic_year}"
                                all_terms_data.append(
                                    {"id": term.id, "name": term_name}
                                )
                            except Exception as term_err:
                                print(
                                    f"Error formatting term {term.id}: {str(term_err)}"
                                )
                                continue
                        print(
                            f"Academic year not found. Returning {len(all_terms_data)} terms (all years) as fallback"
                        )
                        return JsonResponse(
                            {
                                "note": "Academic year not found, showing all terms",
                                "terms": all_terms_data,
                            }
                        )
                    except Exception as fallback_err:
                        print(f"Error in fallback: {str(fallback_err)}")
                        return JsonResponse({"error": error_msg, "terms": []})
        except Exception as year_err:
            print(f"Unexpected error looking up academic year: {str(year_err)}")
            error_msg = f"Error finding academic year: {str(year_err)}"

            # Return all terms as a fallback
            try:
                all_terms = Term.objects.filter(
                    academic_year__is_archived=False
                ).order_by("-academic_year__name", "term_number")
                all_terms_data = []
                for term in all_terms:
                    try:
                        term_name = (
                            f"{term.get_term_number_display()} - {term.academic_year}"
                        )
                        all_terms_data.append({"id": term.id, "name": term_name})
                    except Exception as term_err:
                        print(f"Error formatting term {term.id}: {str(term_err)}")
                        continue
                print(
                    f"Error finding academic year. Returning {len(all_terms_data)} terms (all years) as fallback"
                )
                return JsonResponse(
                    {
                        "note": "Academic year lookup error, showing all terms",
                        "terms": all_terms_data,
                    }
                )
            except Exception as fallback_err:
                print(f"Error in fallback: {str(fallback_err)}")
                return JsonResponse({"error": error_msg, "terms": []}, status=500)

        if not academic_year:
            print("Academic year is still None after all lookup attempts")
            # Return all terms as a fallback
            try:
                all_terms = Term.objects.filter(
                    academic_year__is_archived=False
                ).order_by("-academic_year__name", "term_number")
                all_terms_data = []
                for term in all_terms:
                    try:
                        term_name = (
                            f"{term.get_term_number_display()} - {term.academic_year}"
                        )
                        all_terms_data.append({"id": term.id, "name": term_name})
                    except Exception as term_err:
                        print(f"Error formatting term {term.id}: {str(term_err)}")
                        continue
                print(
                    f"Academic year not found. Returning {len(all_terms_data)} terms (all years) as fallback"
                )
                return JsonResponse(
                    {
                        "note": "Academic year not found, showing all terms",
                        "terms": all_terms_data,
                    }
                )
            except Exception as fallback_err:
                print(f"Error in fallback: {str(fallback_err)}")
                return JsonResponse(
                    {"error": "Could not find academic year", "terms": []}
                )

        # Check if academic year is archived
        if academic_year.is_archived:
            print(
                f"Academic year {academic_year.name} is archived, returning empty terms"
            )
            return JsonResponse(
                {
                    "error": "Cannot access terms for archived academic year.",
                    "terms": [],
                },
                status=400,
            )

        # Get terms for this academic year only
        try:
            terms = Term.objects.filter(academic_year=academic_year).order_by(
                "term_number"
            )
            print(f"Found {terms.count()} terms for academic year {academic_year.name}")
        except Exception as terms_err:
            print(f"Error querying terms: {str(terms_err)}")
            # Fallback to all terms on error
            try:
                all_terms = Term.objects.filter(
                    academic_year__is_archived=False
                ).order_by("-academic_year__name", "term_number")
                all_terms_data = []
                for term in all_terms:
                    term_name = (
                        f"{term.get_term_number_display()} - {term.academic_year}"
                    )
                    all_terms_data.append({"id": term.id, "name": term_name})
                print(
                    f"Error querying terms for academic year. Returning all {len(all_terms_data)} terms as fallback"
                )
                return JsonResponse(
                    {
                        "note": "Error filtering by academic year, showing all terms",
                        "terms": all_terms_data,
                    }
                )
            except Exception as fallback_err:
                print(f"Error in fallback: {str(fallback_err)}")
                return JsonResponse(
                    {"error": f"Error querying terms: {str(terms_err)}", "terms": []},
                    status=500,
                )

        # Format the terms as JSON
        terms_data = []
        for term in terms:
            try:
                term_name = f"{term.get_term_number_display()} - {term.academic_year}"
                terms_data.append({"id": term.id, "name": term_name})
                print(f"Added term: {term_name} (ID: {term.id})")
            except Exception as format_err:
                print(f"Error formatting term {term.id}: {str(format_err)}")
                # Skip this term if there's an error

        # Return as JSON response
        print(
            f"Successfully returning {len(terms_data)} terms for year {academic_year.name}"
        )
        return JsonResponse({"terms": terms_data})
    except Exception as e:
        print(f"ERROR in get_terms_by_academic_year: {str(e)}")
        import traceback

        print("Traceback:")
        traceback.print_exc()

        # Fallback to returning all terms on any error
        try:
            all_terms = Term.objects.all().order_by(
                "-academic_year__name", "term_number"
            )
            all_terms_data = []
            for term in all_terms:
                try:
                    term_name = (
                        f"{term.get_term_number_display()} - {term.academic_year}"
                    )
                    all_terms_data.append({"id": term.id, "name": term_name})
                except:
                    # Skip terms with errors
                    continue
            print(
                f"Error in main function. Returning all {len(all_terms_data)} terms as final fallback"
            )
            return JsonResponse(
                {"note": "Error occurred, showing all terms", "terms": all_terms_data}
            )
        except:
            error_msg = f"Failed to retrieve terms: {str(e)}"
            return JsonResponse({"error": error_msg, "terms": []}, status=500)
