from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.db.models import Q, F, Case, When, IntegerField, Avg
from django.template.loader import render_to_string
from django.conf import settings
import json
import logging
from decimal import Decimal

from ..models import (
    Class,
    Subject,
    Assessment,
    Student,
    StudentClass,
    ClassSubject,
    Term,
    AcademicYear,
    SchoolInformation,
    GradingSystem,
    Form,
    PerformanceRequirement,
)
from ..utils.pdf_generator import generate_pdf_from_html
from ..utils.excel_generator import generate_excel_from_data
from ..utils import check_promotion_eligibility, calculate_student_average

logger = logging.getLogger(__name__)


@login_required
def promotion_sheet_view(request):
    """
    Main promotion sheet interface with dynamic filtering by class and form.
    Provides a single interface for viewing promotion status with professional formatting.
    """
    try:
        # Get current school context
        school = getattr(request.user, "school", None)
        if not school:
            # Try to get from session or use first available school
            school = SchoolInformation.objects.first()

        # Get current academic year and term
        current_academic_year = AcademicYear.objects.filter(
            school=school, is_current=True
        ).first()

        current_term = Term.objects.filter(school=school, is_current=True).first()

        # Get all classes for the current academic year
        classes = (
            Class.objects.filter(
                school=school, academic_year=current_academic_year
            ).order_by("name")
            if current_academic_year
            else Class.objects.none()
        )

        # Get all forms for the school
        forms = Form.objects.filter(school=school).order_by("form_number")

        # Get all terms for the current academic year
        terms = (
            Term.objects.filter(
                school=school, academic_year=current_academic_year
            ).order_by("term_number")
            if current_academic_year
            else Term.objects.none()
        )

        # Default selections
        selected_class = classes.first() if classes.exists() else None
        selected_form = None  # Will be set to "All Forms" by default

        # Get promotion data based on selections
        promotion_data = get_promotion_sheet_data(
            school, selected_class, selected_form, current_academic_year
        )

        context = {
            "classes": classes,
            "forms": forms,
            "terms": terms,
            "selected_class": selected_class,
            "selected_form": selected_form,
            "current_academic_year": current_academic_year,
            "promotion_data": promotion_data,
            "current_term": current_term,
            "school": school,
        }

        return render(request, "promotion/promotion_sheet.html", context)

    except Exception as e:
        logger.error(f"Error in promotion_sheet_view: {str(e)}")
        return render(
            request,
            "promotion/promotion_sheet.html",
            {
                "error": "An error occurred while loading the promotion sheet.",
                "classes": [],
                "forms": [],
                "promotion_data": [],
            },
        )


@login_required
@require_http_methods(["GET"])
def get_promotion_sheet_data_ajax(request):
    """
    AJAX endpoint to get promotion sheet data based on selected class, form, and term.
    """
    try:
        class_id = request.GET.get("class_id")
        form_id = request.GET.get("form_id")
        term_id = request.GET.get("term_id")

        if not class_id and not form_id:
            return JsonResponse({"error": "Class ID or Form ID is required"}, status=400)

        # Get current school context
        school = getattr(request.user, "school", None)
        if not school:
            school = SchoolInformation.objects.first()

        # Get current academic year and its terms
        current_academic_year = None
        if term_id:
            selected_term = get_object_or_404(Term, pk=term_id)
            current_academic_year = selected_term.academic_year
        else:
            # Get current academic year
            current_academic_year = AcademicYear.objects.filter(is_current=True).first()
            if not current_academic_year:
                current_academic_year = AcademicYear.objects.first()
            # Get any term from current academic year for context
            selected_term = Term.objects.filter(academic_year=current_academic_year).first()

        # Get selected class or form
        selected_class = None
        selected_form = None
        
        if class_id:
            # Don't filter by school to avoid school mismatch issues (same as score sheet)
            selected_class = get_object_or_404(Class, class_id=class_id)
        elif form_id:
            selected_form = get_object_or_404(Form, pk=form_id, school=school)

        # Get promotion data
        promotion_data = get_promotion_sheet_data(
            school, selected_class, selected_form, current_academic_year
        )

        # Render the promotion sheet content
        html_content = render_to_string(
            "promotion/partials/promotion_sheet_content.html",
            {
                "promotion_data": promotion_data["students"] if isinstance(promotion_data, dict) else promotion_data,
                "promotion_stats": promotion_data if isinstance(promotion_data, dict) else None,
                "selected_class": selected_class,
                "selected_form": selected_form,
                "current_academic_year": current_academic_year,
                "school": school,
            },
        )

        return JsonResponse(
            {
                "success": True,
                "html_content": html_content,
                "class_name": selected_class.name if selected_class else None,
                "form_name": selected_form.name if selected_form else None,
            }
        )

    except Exception as e:
        logger.error(f"Error in get_promotion_sheet_data_ajax: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


def get_promotion_sheet_data(school, selected_class, selected_form, academic_year):
    """
    Helper function to retrieve and format promotion sheet data.
    """
    if not academic_year:
        return []

    try:
        # Get all students based on selection
        if selected_class:
            # Class-level view
            student_classes = StudentClass.objects.filter(
                assigned_class=selected_class, is_active=True
            ).select_related("student")
            students = [sc.student for sc in student_classes]
        elif selected_form:
            # Form-level view - get all classes in the form
            classes_in_form = Class.objects.filter(
                form=selected_form, 
                academic_year=academic_year
            )
            student_classes = StudentClass.objects.filter(
                assigned_class__in=classes_in_form, 
                is_active=True
            ).select_related("student", "assigned_class")
            
            # Create a mapping of student to their current class
            student_class_mapping = {}
            for sc in student_classes:
                if sc.student not in student_class_mapping:
                    student_class_mapping[sc.student] = sc.assigned_class
            
            students = list(student_class_mapping.keys())
        else:
            return []

        if not students:
            return []

        # Get all terms for the current academic year
        academic_terms = Term.objects.filter(
            academic_year=academic_year
        ).order_by("term_number")

        # Get latest 3 terms (or all available if fewer)
        term_ids = list(academic_terms.values_list("id", flat=True))
        terms_to_use = term_ids[-min(3, len(term_ids)):]
        terms_to_use_objects = Term.objects.filter(id__in=terms_to_use)

        promotion_data = []

        for student in students:
            # Get student's current class
            current_class = None
            if selected_class:
                current_class = selected_class
            elif selected_form and student in student_class_mapping:
                current_class = student_class_mapping[student]

            if not current_class:
                continue

            # Get student's performance data
            performance = calculate_student_average(
                student, academic_year, terms_to_use_objects, school=school
            )


            # Calculate term averages and check completion
            term_averages = {}
            terms_completed = 0
            total_terms = len(terms_to_use_objects)
            
            for term in terms_to_use_objects:
                # Get all assessments for this student in this term across all subjects
                # Exclude mock exam assessments from promotion calculations
                term_assessments = Assessment.objects.filter(
                    student=student,
                    class_subject__academic_year=academic_year,
                    term=term,
                ).exclude(assessment_type='mock_exam')
                
                if term_assessments.exists():
                    # Calculate average of all subjects for this term
                    total_score = sum(assessment.total_score for assessment in term_assessments if assessment.total_score)
                    count = len([a for a in term_assessments if a.total_score])
                    avg_score = total_score / count if count > 0 else 0
                    term_averages[f"term_{term.term_number}"] = round(float(avg_score), 2)
                    terms_completed += 1
                else:
                    term_averages[f"term_{term.term_number}"] = 0.0

            # Check if student has completed all terms before checking promotion eligibility
            if terms_completed < total_terms:
                status = "RETAINED"
                status_reason = f"INCOMPLETE TERMS - Only completed {terms_completed} out of {total_terms} terms"
                eligible = False
            else:
                # Check promotion eligibility only if all terms are completed
                eligibility_result = check_promotion_eligibility(
                    student, academic_year, terms_to_use_objects, school=school
                )
                eligible = eligibility_result["eligible"]

            # Determine promotion status
            current_form_obj = current_class.form
            current_form_number = current_form_obj.form_number if hasattr(current_form_obj, "form_number") else None
            current_form_name = current_form_obj.name if hasattr(current_form_obj, "name") else f"Form {current_form_number}"

            if eligible:
                if current_form_number == 3:  # Final form students graduate
                    status = "PROMOTED"
                    status_reason = "GRADUATED"
                else:
                    status = "PROMOTED"
                    status_reason = "READY FOR PROMOTION"
            else:
                if status != "RETAINED":  # Don't override incomplete terms status
                    status = "RETAINED"
                    status_reason = eligibility_result.get("reason", "FAILED REQUIREMENTS")

            # Calculate overall average and position
            overall_average = performance["average_score"]
            
            # Get position (we'll calculate this after collecting all data)
            student_data = {
                "student": student,
                "current_class": current_class,
                "current_form_number": current_form_number,
                "current_form_name": current_form_name,
                "term_averages": term_averages,
                "overall_average": overall_average,
                "position": 0,  # Will be calculated later
                "status": status,
                "status_reason": status_reason,
                "performance": performance,
                "eligible": eligible,
            }
            
            promotion_data.append(student_data)

        # Sort by overall average (descending) and assign positions
        promotion_data.sort(key=lambda x: x["overall_average"], reverse=True)
        
        for i, student_data in enumerate(promotion_data):
            student_data["position"] = i + 1

        # Calculate class/form average
        if promotion_data:
            total_average = sum(student["overall_average"] for student in promotion_data)
            class_average = total_average / len(promotion_data)
        else:
            class_average = 0.0

        # Add class average to the data
        promotion_data_with_stats = {
            "students": promotion_data,
            "class_average": round(class_average, 2),
            "total_students": len(promotion_data),
            "promoted_count": len([s for s in promotion_data if s["status"] == "PROMOTED"]),
            "retained_count": len([s for s in promotion_data if s["status"] == "RETAINED"]),
        }

        return promotion_data_with_stats

    except Exception as e:
        logger.error(f"Error in get_promotion_sheet_data: {str(e)}")
        return []


@login_required
@require_http_methods(["GET"])
def export_promotion_sheet_pdf(request):
    """
    Export promotion sheet as PDF.
    """
    try:
        class_id = request.GET.get("class_id")
        form_id = request.GET.get("form_id")
        term_id = request.GET.get("term_id")

        if not class_id and not form_id:
            return JsonResponse({"error": "Class ID or Form ID is required"}, status=400)

        # Get current school context
        school = getattr(request.user, "school", None)
        if not school:
            school = SchoolInformation.objects.first()

        # Get current academic year and its terms
        current_academic_year = None
        if term_id:
            selected_term = get_object_or_404(Term, pk=term_id)
            current_academic_year = selected_term.academic_year
        else:
            # Get current academic year
            current_academic_year = AcademicYear.objects.filter(is_current=True).first()
            if not current_academic_year:
                current_academic_year = AcademicYear.objects.first()
            # Get any term from current academic year for context
            selected_term = Term.objects.filter(academic_year=current_academic_year).first()

        # Get selected class or form
        selected_class = None
        selected_form = None
        
        if class_id:
            # Don't filter by school to avoid school mismatch issues (same as score sheet)
            selected_class = get_object_or_404(Class, class_id=class_id)
        elif form_id:
            selected_form = get_object_or_404(Form, pk=form_id, school=school)

        # Get promotion data
        promotion_data = get_promotion_sheet_data(
            school, selected_class, selected_form, current_academic_year
        )

        # Generate PDF
        html_content = render_to_string(
            "promotion/print/promotion_sheet_pdf.html",
            {
                "promotion_data": promotion_data["students"] if isinstance(promotion_data, dict) else promotion_data,
                "promotion_stats": promotion_data if isinstance(promotion_data, dict) else None,
                "selected_class": selected_class,
                "selected_form": selected_form,
                "current_academic_year": current_academic_year,
                "school": school,
                "request": request,
            },
        )

        pdf_content = generate_pdf_from_html(html_content)

        # Prepare response
        filename = f"promotion_sheet"
        if selected_class:
            filename += f"_{selected_class.name}"
        elif selected_form:
            filename += f"_{selected_form.name}"
        filename += f"_{current_academic_year.name.replace('/', '_')}.pdf"

        # Check if this is a print request (from print button)
        is_print_request = request.GET.get("print", "false").lower() == "true"

        response = HttpResponse(pdf_content, content_type="application/pdf")

        if is_print_request:
            # For print preview, use inline disposition
            response["Content-Disposition"] = f'inline; filename="{filename}"'
        else:
            # For download, use attachment disposition
            response["Content-Disposition"] = f'attachment; filename="{filename}"'

        return response

    except Exception as e:
        logger.error(f"Error in export_promotion_sheet_pdf: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def print_promotion_sheet(request):
    """
    Print promotion sheet as HTML (for print preview).
    """
    try:
        class_id = request.GET.get("class_id")
        form_id = request.GET.get("form_id")
        term_id = request.GET.get("term_id")

        if not class_id and not form_id:
            return JsonResponse({"error": "Class ID or Form ID is required"}, status=400)

        # Get current school context
        school = getattr(request.user, "school", None)
        if not school:
            school = SchoolInformation.objects.first()

        # Get current academic year and its terms
        current_academic_year = None
        if term_id:
            selected_term = get_object_or_404(Term, pk=term_id)
            current_academic_year = selected_term.academic_year
        else:
            # Get current academic year
            current_academic_year = AcademicYear.objects.filter(is_current=True).first()
            if not current_academic_year:
                current_academic_year = AcademicYear.objects.first()
            # Get any term from current academic year for context
            selected_term = Term.objects.filter(academic_year=current_academic_year).first()

        # Get selected class or form
        selected_class = None
        selected_form = None
        
        if class_id:
            # Don't filter by school to avoid school mismatch issues (same as score sheet)
            selected_class = get_object_or_404(Class, class_id=class_id)
        elif form_id:
            selected_form = get_object_or_404(Form, pk=form_id, school=school)

        # Get promotion data
        promotion_data = get_promotion_sheet_data(
            school, selected_class, selected_form, current_academic_year
        )

        # Render HTML template for printing
        return render(
            request,
            "promotion/print/promotion_sheet_print.html",
            {
                "promotion_data": promotion_data["students"] if isinstance(promotion_data, dict) else promotion_data,
                "promotion_stats": promotion_data if isinstance(promotion_data, dict) else None,
                "selected_class": selected_class,
                "selected_form": selected_form,
                "current_academic_year": current_academic_year,
                "school": school,
                "request": request,
            },
        )

    except Exception as e:
        logger.error(f"Error in print_promotion_sheet: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def export_promotion_sheet_excel(request):
    """
    Export promotion sheet as Excel.
    """
    try:
        class_id = request.GET.get("class_id")
        form_id = request.GET.get("form_id")
        term_id = request.GET.get("term_id")

        if not class_id and not form_id:
            return JsonResponse({"error": "Class ID or Form ID is required"}, status=400)

        # Get current school context
        school = getattr(request.user, "school", None)
        if not school:
            school = SchoolInformation.objects.first()

        # Get current academic year and its terms
        current_academic_year = None
        if term_id:
            selected_term = get_object_or_404(Term, pk=term_id)
            current_academic_year = selected_term.academic_year
        else:
            # Get current academic year
            current_academic_year = AcademicYear.objects.filter(is_current=True).first()
            if not current_academic_year:
                current_academic_year = AcademicYear.objects.first()
            # Get any term from current academic year for context
            selected_term = Term.objects.filter(academic_year=current_academic_year).first()

        # Get selected class or form
        selected_class = None
        selected_form = None
        
        if class_id:
            # Don't filter by school to avoid school mismatch issues (same as score sheet)
            selected_class = get_object_or_404(Class, class_id=class_id)
        elif form_id:
            selected_form = get_object_or_404(Form, pk=form_id, school=school)

        # Get promotion data
        promotion_data = get_promotion_sheet_data(
            school, selected_class, selected_form, current_academic_year
        )

        # Prepare Excel data
        excel_data = prepare_promotion_excel_data(
            promotion_data["students"] if isinstance(promotion_data, dict) else promotion_data, 
            selected_class, selected_form, current_academic_year
        )

        # Generate Excel
        excel_content = generate_excel_from_data(excel_data)

        # Prepare response
        filename = f"promotion_sheet"
        if selected_class:
            filename += f"_{selected_class.name}"
        elif selected_form:
            filename += f"_{selected_form.name}"
        filename += f"_{current_academic_year.name.replace('/', '_')}.xlsx"

        response = HttpResponse(
            excel_content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        return response

    except Exception as e:
        logger.error(f"Error in export_promotion_sheet_excel: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


def prepare_promotion_excel_data(promotion_data, selected_class, selected_form, academic_year):
    """
    Prepare data for Excel export.
    """
    excel_data = {
        "title": f"Promotion Sheet",
        "subtitle": f'{selected_class.name if selected_class else selected_form.name} - {academic_year.name}',
        "headers": ["Student ID", "Student Name", "1st Term", "2nd Term", "3rd Term", "Overall Average", "Position", "Status"],
        "data": [],
    }

    # Add data rows
    for student_data in promotion_data:
        row = [
            student_data["student"].admission_number,
            student_data["student"].full_name,
            student_data["term_averages"].get("term_1", 0),
            student_data["term_averages"].get("term_2", 0),
            student_data["term_averages"].get("term_3", 0),
            student_data["overall_average"],
            student_data["position"],
            student_data["status"],
        ]
        excel_data["data"].append(row)

    return excel_data
