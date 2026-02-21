from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.db.models import Q, F, Case, When, IntegerField
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
    MockExam,

)
from ..utils.pdf_generator import generate_pdf_from_html
from ..utils.excel_generator import generate_excel_from_data

logger = logging.getLogger(__name__)


@login_required
def score_sheet_view(request):
    """
    Main score sheet interface with dynamic filtering by class and subject.
    Provides a single interface for viewing detailed score sheets with professional formatting.
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

        # Get all subjects for the school
        subjects = Subject.objects.filter(school=school).order_by("subject_name")


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
        selected_subject = None  # Will be set to "All Subjects" by default
        selected_term = current_term  # Default to current term

        # Get score data based on selections
        score_data = get_score_sheet_data(
            school, selected_class, selected_subject, selected_term
        )

        context = {
            "classes": classes,

            "forms": forms,

            "subjects": subjects,
            "terms": terms,
            "selected_class": selected_class,
            "selected_subject": selected_subject,
            "selected_term": selected_term,
            "score_data": score_data,
            "current_academic_year": current_academic_year,
            "current_term": current_term,
            "school": school,
        }

        return render(request, "scores/score_sheet.html", context)

    except Exception as e:
        logger.error(f"Error in score_sheet_view: {str(e)}")
        return render(
            request,
            "scores/score_sheet.html",
            {
                "error": "An error occurred while loading the score sheet.",
                "classes": [],
                "subjects": [],
                "score_data": [],
            },
        )


@login_required
@require_http_methods(["GET"])
def get_score_sheet_data_ajax(request):
    """
    AJAX endpoint to get score sheet data based on selected class, subject, and term.
    """
    try:
        class_id = request.GET.get("class_id")
        subject_id = request.GET.get("subject_id")
        term_id = request.GET.get("term_id")

        if not class_id:
            return JsonResponse({"error": "Class ID is required"}, status=400)

        # Get current school context
        school = getattr(request.user, "school", None)
        if not school:
            school = SchoolInformation.objects.first()

        # Get selected term or default to current term
        selected_term = None
        if term_id:
            selected_term = get_object_or_404(Term, pk=term_id, school=school)
        else:
            selected_term = Term.objects.filter(school=school, is_current=True).first()


        # Get selected class (don't filter by school to avoid school mismatch issues)
        selected_class = get_object_or_404(Class, class_id=class_id)


        # Get selected subject (None means "All Subjects")
        selected_subject = None
        if subject_id and subject_id != "all":

            selected_subject = get_object_or_404(Subject, pk=subject_id)


        # Get score data
        score_data = get_score_sheet_data(
            school, selected_class, selected_subject, selected_term
        )

        # Render the score sheet content
        html_content = render_to_string(
            "scores/partials/score_sheet_content.html",
            {
                "score_data": score_data,
                "selected_class": selected_class,
                "selected_subject": selected_subject,
                "current_term": selected_term,
                "school": school,
            },
        )

        return JsonResponse(
            {
                "success": True,
                "html_content": html_content,
                "class_name": selected_class.name,
                "subject_name": (
                    selected_subject.subject_name
                    if selected_subject
                    else "All Subjects"
                ),
            }
        )

    except Exception as e:
        logger.error(f"Error in get_score_sheet_data_ajax: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


def get_score_sheet_data(school, selected_class, selected_subject, selected_term):
    """
    Helper function to retrieve and format score sheet data.
    """
    if not selected_class or not selected_term:
        return []

    try:
        # Get all students in the selected class
        student_classes = StudentClass.objects.filter(
            assigned_class=selected_class, is_active=True
        ).select_related("student")

        students = [sc.student for sc in student_classes]

        if not students:
            return []

        # Determine which subjects to include
        if selected_subject:
            # Single subject view
            subjects_to_include = [selected_subject]
        else:

            # All subjects view - get all subjects for this class (only active ones)
            class_subjects = ClassSubject.objects.filter(
                class_name=selected_class, is_active=True

            ).select_related("subject")
            subjects_to_include = [cs.subject for cs in class_subjects]

        score_data = []

        for student in students:
            student_data = {
                "student": student,
                "subjects": {},
                "total_score": 0,
                "average_score": 0,
                "position": 0,
                "grade": "N/A",
                "remarks": "Not Graded",
            }

            total_subject_scores = 0
            valid_subjects = 0

            for subject in subjects_to_include:
                # Get assessment for this student, subject, and term

                # Exclude mock exam assessments from regular score sheet

                assessment = Assessment.objects.filter(
                    student=student,
                    class_subject__subject=subject,
                    class_subject__class_name=selected_class,

                    class_subject__is_active=True,
                    term=selected_term,
                ).exclude(assessment_type='mock_exam').first()


                if assessment and assessment.total_score is not None:
                    student_data["subjects"][subject.subject_name] = {
                        "score": float(assessment.total_score),
                        "grade": assessment.grade or "N/A",
                        "position": assessment.position or 0,
                        "class_score": (
                            float(assessment.class_score)
                            if assessment.class_score
                            else 0
                        ),
                        "exam_score": (
                            float(assessment.exam_score) if assessment.exam_score else 0
                        ),
                    }
                    total_subject_scores += float(assessment.total_score)
                    valid_subjects += 1
                else:
                    student_data["subjects"][subject.subject_name] = {
                        "score": 0,
                        "grade": "N/A",
                        "position": 0,
                        "class_score": 0,
                        "exam_score": 0,
                    }

            # Calculate average score
            if valid_subjects > 0:
                student_data["average_score"] = round(
                    total_subject_scores / valid_subjects, 2
                )
                student_data["total_score"] = total_subject_scores

                # Get grade and remarks for average score
                grade_info = GradingSystem.get_grade_for_score(
                    Decimal(str(student_data["average_score"])), school
                )
                if grade_info:
                    student_data["grade"] = grade_info.grade_letter
                    student_data["remarks"] = grade_info.remarks

            score_data.append(student_data)

        # Sort by average score (descending) and assign positions
        score_data.sort(key=lambda x: x["average_score"], reverse=True)

        for i, student_data in enumerate(score_data):
            student_data["position"] = i + 1

        return score_data

    except Exception as e:
        logger.error(f"Error in get_score_sheet_data: {str(e)}")
        return []



def get_form_level_score_sheet_data(school, selected_form, selected_subject, selected_term):
    """
    Helper function to retrieve and format score sheet data for an entire form/level.
    Combines all classes within the form (e.g., JHS 1A, JHS 1B, etc.)
    """
    if not selected_form or not selected_term:
        return []

    try:
        # Get all classes in the selected form
        # Note: We don't filter by school here since the form might be associated with a different school
        classes_in_form = Class.objects.filter(
            form=selected_form, 
            academic_year=selected_term.academic_year
        )
        
        if not classes_in_form.exists():
            return []

        # Get all students across all classes in this form
        student_classes = StudentClass.objects.filter(
            assigned_class__in=classes_in_form, 
            is_active=True
        ).select_related("student", "assigned_class")

        # Create a mapping of student to their CURRENT class for display purposes
        # This ensures each student appears only once with their current class
        student_class_mapping = {}
        for sc in student_classes:
            if sc.student not in student_class_mapping:
                student_class_mapping[sc.student] = sc.assigned_class
        
        students = list(student_class_mapping.keys())

        if not students:
            return []

        # Determine which subjects to include
        if selected_subject:
            # Single subject view
            subjects_to_include = [selected_subject]
        else:
            # All subjects view - get all subjects taught across all classes in this form (only active ones)
            class_subjects = ClassSubject.objects.filter(
                class_name__in=classes_in_form, is_active=True
            ).select_related("subject")
            subjects_to_include = list(set([cs.subject for cs in class_subjects]))

        score_data = []

        for student in students:
            student_data = {
                "student": student,
                "student_class": student_class_mapping[student],  # Add class info for display
                "subjects": {},
                "total_score": 0,
                "average_score": 0,
                "position": 0,
                "grade": "N/A",
                "remarks": "Not Graded",
            }

            total_subject_scores = 0
            valid_subjects = 0

            for subject in subjects_to_include:
                # Get assessment for this student, subject, and term
                # ONLY from student's current class - NO historical fallback
                current_class = student_class_mapping[student]
                
                # Get assessment ONLY from student's current class
                # Exclude mock exam assessments from regular score sheet
                assessment = Assessment.objects.filter(
                    student=student,
                    class_subject__subject=subject,
                    class_subject__class_name=current_class,
                    class_subject__is_active=True,
                    term=selected_term,
                ).exclude(assessment_type='mock_exam').first()

                if assessment and assessment.total_score is not None:
                    student_data["subjects"][subject.subject_name] = {
                        "score": float(assessment.total_score),
                        "grade": assessment.grade or "N/A",
                        "position": assessment.position or 0,
                        "class_score": (
                            float(assessment.class_score)
                            if assessment.class_score
                            else 0
                        ),
                        "exam_score": (
                            float(assessment.exam_score) if assessment.exam_score else 0
                        ),
                    }
                    total_subject_scores += float(assessment.total_score)
                    valid_subjects += 1
                else:
                    student_data["subjects"][subject.subject_name] = {
                        "score": 0,
                        "grade": "N/A",
                        "position": 0,
                        "class_score": 0,
                        "exam_score": 0,
                    }

            # Calculate average score
            if valid_subjects > 0:
                student_data["average_score"] = round(
                    total_subject_scores / valid_subjects, 2
                )
                student_data["total_score"] = total_subject_scores

                # Get grade and remarks for average score
                grade_info = GradingSystem.get_grade_for_score(
                    Decimal(str(student_data["average_score"])), school
                )
                if grade_info:
                    student_data["grade"] = grade_info.grade_letter
                    student_data["remarks"] = grade_info.remarks

            score_data.append(student_data)

        # Sort by average score (descending) and assign positions
        score_data.sort(key=lambda x: x["average_score"], reverse=True)

        for i, student_data in enumerate(score_data):
            student_data["position"] = i + 1

        return score_data

    except Exception as e:
        logger.error(f"Error in get_form_level_score_sheet_data: {str(e)}")
        return []



@login_required
@require_http_methods(["GET"])
def export_score_sheet_pdf(request):
    """
    Export score sheet as PDF.
    """
    try:
        class_id = request.GET.get("class_id")
        subject_id = request.GET.get("subject_id")
        term_id = request.GET.get("term_id")

        if not class_id:
            return JsonResponse({"error": "Class ID is required"}, status=400)

        # Get current school context
        school = getattr(request.user, "school", None)
        if not school:
            school = SchoolInformation.objects.first()

        # Get selected term or default to current term
        selected_term = None
        if term_id:
            selected_term = get_object_or_404(Term, pk=term_id, school=school)
        else:
            selected_term = Term.objects.filter(school=school, is_current=True).first()

        # Get selected class and subject
        selected_class = get_object_or_404(Class, class_id=class_id, school=school)
        selected_subject = None
        if subject_id and subject_id != "all":
            selected_subject = get_object_or_404(Subject, pk=subject_id, school=school)

        # Get score data
        score_data = get_score_sheet_data(
            school, selected_class, selected_subject, selected_term
        )

        # Generate PDF
        html_content = render_to_string(
            "scores/print/score_sheet_pdf.html",
            {
                "score_data": score_data,
                "selected_class": selected_class,
                "selected_subject": selected_subject,
                "current_term": selected_term,
                "school": school,
                "request": request,
            },
        )

        pdf_content = generate_pdf_from_html(html_content)

        # Prepare response
        filename = f"score_sheet_{selected_class.name}"
        if selected_subject:
            filename += f"_{selected_subject.subject_name}"
        filename += f"_{selected_term.get_term_number_display()}.pdf"

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
        logger.error(f"Error in export_score_sheet_pdf: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def print_score_sheet(request):
    """
    Print score sheet as HTML (for print preview).
    """
    try:
        class_id = request.GET.get("class_id")
        subject_id = request.GET.get("subject_id")
        term_id = request.GET.get("term_id")

        if not class_id:
            return JsonResponse({"error": "Class ID is required"}, status=400)

        # Get current school context
        school = getattr(request.user, "school", None)
        if not school:
            school = SchoolInformation.objects.first()

        # Get selected term or default to current term
        selected_term = None
        if term_id:
            selected_term = get_object_or_404(Term, pk=term_id, school=school)
        else:
            selected_term = Term.objects.filter(school=school, is_current=True).first()

        # Get selected class and subject
        selected_class = get_object_or_404(Class, class_id=class_id, school=school)
        selected_subject = None
        if subject_id and subject_id != "all":
            selected_subject = get_object_or_404(Subject, pk=subject_id, school=school)

        # Get score data
        score_data = get_score_sheet_data(
            school, selected_class, selected_subject, selected_term
        )

        # Render HTML template for printing
        return render(
            request,
            "scores/print/score_sheet_print.html",
            {
                "score_data": score_data,
                "selected_class": selected_class,
                "selected_subject": selected_subject,
                "current_term": selected_term,
                "school": school,
                "request": request,
            },
        )

    except Exception as e:
        logger.error(f"Error in print_score_sheet: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def export_score_sheet_excel(request):
    """
    Export score sheet as Excel.
    """
    try:
        class_id = request.GET.get("class_id")
        subject_id = request.GET.get("subject_id")
        term_id = request.GET.get("term_id")

        if not class_id:
            return JsonResponse({"error": "Class ID is required"}, status=400)

        # Get current school context
        school = getattr(request.user, "school", None)
        if not school:
            school = SchoolInformation.objects.first()

        # Get selected term or default to current term
        selected_term = None
        if term_id:
            selected_term = get_object_or_404(Term, pk=term_id, school=school)
        else:
            selected_term = Term.objects.filter(school=school, is_current=True).first()

        # Get selected class and subject
        selected_class = get_object_or_404(Class, class_id=class_id, school=school)
        selected_subject = None
        if subject_id and subject_id != "all":
            selected_subject = get_object_or_404(Subject, pk=subject_id, school=school)

        # Get score data
        score_data = get_score_sheet_data(
            school, selected_class, selected_subject, selected_term
        )

        # Prepare Excel data
        excel_data = prepare_excel_data(
            score_data, selected_class, selected_subject, selected_term
        )

        # Generate Excel
        excel_content = generate_excel_from_data(excel_data)

        # Prepare response
        filename = f"score_sheet_{selected_class.name}"
        if selected_subject:
            filename += f"_{selected_subject.subject_name}"
        filename += f"_{selected_term.get_term_number_display()}.xlsx"

        response = HttpResponse(
            excel_content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        return response

    except Exception as e:
        logger.error(f"Error in export_score_sheet_excel: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


def prepare_excel_data(score_data, selected_class, selected_subject, selected_term):
    """
    Prepare data for Excel export.
    """
    excel_data = {
        "title": f"Score Sheet - {selected_class.name}",
        "subtitle": f'{selected_subject.subject_name if selected_subject else "All Subjects"} - {selected_term.get_term_number_display()}',
        "headers": ["Student Name", "Student ID"],
        "data": [],
    }

    # Add subject columns if showing all subjects
    if not selected_subject:
        subjects = list(score_data[0]["subjects"].keys()) if score_data else []
        excel_data["headers"].extend(subjects)
        excel_data["headers"].extend(["Average Score", "Position"])
    else:
        excel_data["headers"].extend(
            ["Position", "Class Score", "Exam Score", "Total Score", "Grade", "Remarks"]
        )

    # Add data rows
    for student_data in score_data:
        row = [
            student_data["student"].full_name,
            student_data["student"].admission_number,
        ]

        if not selected_subject:
            # All subjects view
            for subject_name in excel_data["headers"][
                2:-2
            ]:  # Skip student name, id, avg, position
                subject_data = student_data["subjects"].get(subject_name, {})
                row.append(subject_data.get("score", 0))

            row.extend(
                [
                    student_data["average_score"],
                    student_data["position"],
                ]
            )
        else:
            # Single subject view
            row.append(student_data["position"])
            subject_data = student_data["subjects"].get(
                selected_subject.subject_name, {}
            )
            row.extend(
                [
                    subject_data.get("class_score", 0),
                    subject_data.get("exam_score", 0),
                    subject_data.get("score", 0),
                    subject_data.get("grade", "N/A"),
                    student_data["remarks"],
                ]
            )

        excel_data["data"].append(row)

    return excel_data



@login_required
@require_http_methods(["GET"])
def get_form_level_score_sheet_data_ajax(request):
    """
    AJAX endpoint to get form-level score sheet data.
    """
    try:
        form_id = request.GET.get("form_id")
        subject_id = request.GET.get("subject_id")
        term_id = request.GET.get("term_id")

        if not form_id:
            return JsonResponse({"error": "Form ID is required"}, status=400)

        # Get current school context
        school = getattr(request.user, "school", None)
        if not school:
            school = SchoolInformation.objects.first()

        # Get selected term or default to current term
        selected_term = None
        if term_id:
            selected_term = get_object_or_404(Term, pk=term_id, school=school)
        else:
            selected_term = Term.objects.filter(school=school, is_current=True).first()

        # Get selected form and subject
        selected_form = get_object_or_404(Form, pk=form_id, school=school)
        selected_subject = None
        if subject_id and subject_id != "all":
            selected_subject = get_object_or_404(Subject, pk=subject_id, school=school)

        # Get score data
        score_data = get_form_level_score_sheet_data(
            school, selected_form, selected_subject, selected_term
        )

        # Serialize score data for JSON response
        serialized_score_data = []
        for student_data in score_data:
            serialized_student = {
                "student": {
                    "id": student_data["student"].id,
                    "full_name": student_data["student"].full_name,
                    "admission_number": student_data["student"].admission_number,
                },
                "student_class": {
                    "id": student_data["student_class"].id,
                    "name": student_data["student_class"].name,
                },
                "subjects": student_data["subjects"],
                "total_score": student_data["total_score"],
                "average_score": student_data["average_score"],
                "position": student_data["position"],
                "grade": student_data["grade"],
                "remarks": student_data["remarks"],
            }
            serialized_score_data.append(serialized_student)

        return JsonResponse({
            "score_data": serialized_score_data,
            "selected_form": {
                "id": selected_form.id,
                "name": selected_form.name,
            },
            "selected_subject": {
                "id": selected_subject.id,
                "subject_name": selected_subject.subject_name,
            } if selected_subject else None,
            "current_term": {
                "id": selected_term.id,
                "name": selected_term.get_term_number_display(),
            },
        })

    except Exception as e:
        logger.error(f"Error in get_form_level_score_sheet_data_ajax: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def export_form_level_score_sheet_pdf(request):
    """
    Export form-level score sheet as PDF.
    """
    try:
        form_id = request.GET.get("form_id")
        subject_id = request.GET.get("subject_id")
        term_id = request.GET.get("term_id")

        if not form_id:
            return JsonResponse({"error": "Form ID is required"}, status=400)

        # Get current school context
        school = getattr(request.user, "school", None)
        if not school:
            school = SchoolInformation.objects.first()

        # Get selected term or default to current term
        selected_term = None
        if term_id:
            selected_term = get_object_or_404(Term, pk=term_id, school=school)
        else:
            selected_term = Term.objects.filter(school=school, is_current=True).first()

        # Get selected form and subject
        selected_form = get_object_or_404(Form, pk=form_id, school=school)
        selected_subject = None
        if subject_id and subject_id != "all":
            selected_subject = get_object_or_404(Subject, pk=subject_id, school=school)

        # Get score data
        score_data = get_form_level_score_sheet_data(
            school, selected_form, selected_subject, selected_term
        )

        # Generate PDF
        html_content = render_to_string(
            "scores/print/score_sheet_pdf.html",
            {
                "score_data": score_data,
                "selected_form": selected_form,
                "selected_subject": selected_subject,
                "current_term": selected_term,
                "school": school,
                "request": request,
                "is_form_level": True,  # Flag to indicate this is form-level
            },
        )

        pdf_content = generate_pdf_from_html(html_content)

        # Prepare response
        filename = f"form_level_score_sheet_{selected_form.name}"
        if selected_subject:
            filename += f"_{selected_subject.subject_name}"
        filename += f"_{selected_term.get_term_number_display()}.pdf"

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
        logger.error(f"Error in export_form_level_score_sheet_pdf: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def print_form_level_score_sheet(request):
    """
    Print form-level score sheet as HTML (for print preview).
    """
    try:
        form_id = request.GET.get("form_id")
        subject_id = request.GET.get("subject_id")
        term_id = request.GET.get("term_id")

        if not form_id:
            return JsonResponse({"error": "Form ID is required"}, status=400)

        # Get current school context
        school = getattr(request.user, "school", None)
        if not school:
            school = SchoolInformation.objects.first()

        # Get selected term or default to current term
        selected_term = None
        if term_id:
            selected_term = get_object_or_404(Term, pk=term_id, school=school)
        else:
            selected_term = Term.objects.filter(school=school, is_current=True).first()

        # Get selected form and subject
        selected_form = get_object_or_404(Form, pk=form_id, school=school)
        selected_subject = None
        if subject_id and subject_id != "all":
            selected_subject = get_object_or_404(Subject, pk=subject_id, school=school)

        # Get score data
        score_data = get_form_level_score_sheet_data(
            school, selected_form, selected_subject, selected_term
        )

        # Render HTML template for printing
        return render(
            request,
            "scores/print/score_sheet_print.html",
            {
                "score_data": score_data,
                "selected_form": selected_form,
                "selected_subject": selected_subject,
                "current_term": selected_term,
                "school": school,
                "request": request,
                "is_form_level": True,  # Flag to indicate this is form-level
            },
        )

    except Exception as e:
        logger.error(f"Error in print_form_level_score_sheet: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


# ==================== MOCK EXAM SCORE SHEET VIEWS ====================

def get_form_level_mock_exam_score_sheet_data(school, selected_form, selected_subject, selected_mock_exam):
    """
    Helper function to retrieve and format mock exam score sheet data for an entire form/level.
    Combines all classes within the form (e.g., JHS 1A, JHS 1B, etc.)
    """
    if not selected_form or not selected_mock_exam:
        return []

    try:
        # Get current academic year
        current_academic_year = AcademicYear.objects.filter(
            school=school, is_current=True
        ).first()

        if not current_academic_year:
            return []

        # Get all classes in the selected form
        classes_in_form = Class.objects.filter(
            form=selected_form, 
            academic_year=current_academic_year
        )
        
        if not classes_in_form.exists():
            return []

        # Get all students across all classes in this form
        student_classes = StudentClass.objects.filter(
            assigned_class__in=classes_in_form, 
            is_active=True
        ).select_related("student", "assigned_class")

        # Create a mapping of student to their CURRENT class for display purposes
        # This ensures each student appears only once with their current class
        student_class_mapping = {}
        for sc in student_classes:
            if sc.student not in student_class_mapping:
                student_class_mapping[sc.student] = sc.assigned_class
        
        students = list(student_class_mapping.keys())

        if not students:
            return []

        # Determine which subjects to include
        if selected_subject:
            # Single subject view
            subjects_to_include = [selected_subject]
        else:
            # All subjects view - get all subjects taught across all classes in this form (only active ones)
            class_subjects = ClassSubject.objects.filter(
                class_name__in=classes_in_form, is_active=True
            ).select_related("subject")
            subjects_to_include = list(set([cs.subject for cs in class_subjects]))

        score_data = []

        for student in students:
            student_data = {
                "student": student,
                "student_class": student_class_mapping[student],  # Add class info for display
                "subjects": {},
                "total_score": 0,
                "average_score": 0,
                "position": 0,
                "grade": "N/A",
                "remarks": "Not Graded",
            }

            total_subject_scores = 0
            valid_subjects = 0

            for subject in subjects_to_include:
                # Get ClassSubject for this class and subject
                current_class = student_class_mapping[student]
                class_subject = ClassSubject.objects.filter(
                    class_name=current_class,
                    subject=subject,
                    is_active=True,
                ).first()

                if not class_subject:
                    student_data["subjects"][subject.subject_name] = {
                        "score": 0,
                        "grade": "N/A",
                        "position": 0,
                        "raw_score": 0,
                    }
                    continue

                # Get mock exam assessment for this student, class_subject, and mock_exam
                assessment = Assessment.objects.filter(
                    student=student,
                    class_subject=class_subject,
                    assessment_type="mock_exam",
                    mock_exam=selected_mock_exam,
                ).first()

                if assessment and assessment.total_score is not None:
                    student_data["subjects"][subject.subject_name] = {
                        "score": float(assessment.total_score),
                        "grade": assessment.grade or "N/A",
                        "position": assessment.position or 0,
                        "raw_score": (
                            float(assessment.raw_exam_score)
                            if assessment.raw_exam_score
                            else 0
                        ),
                    }
                    total_subject_scores += float(assessment.total_score)
                    valid_subjects += 1
                else:
                    student_data["subjects"][subject.subject_name] = {
                        "score": 0,
                        "grade": "N/A",
                        "position": 0,
                        "raw_score": 0,
                    }

            # Calculate average score
            if valid_subjects > 0:
                student_data["average_score"] = round(
                    total_subject_scores / valid_subjects, 2
                )
                student_data["total_score"] = total_subject_scores

                # Get grade and remarks for average score
                grade_info = GradingSystem.get_grade_for_score(
                    Decimal(str(student_data["average_score"])), school
                )
                if grade_info:
                    student_data["grade"] = grade_info.grade_letter
                    student_data["remarks"] = grade_info.remarks

            score_data.append(student_data)

        # Sort by average score (descending) and assign positions
        score_data.sort(key=lambda x: x["average_score"], reverse=True)

        for i, student_data in enumerate(score_data):
            student_data["position"] = i + 1

        return score_data

    except Exception as e:
        logger.error(f"Error in get_form_level_mock_exam_score_sheet_data: {str(e)}")
        return []

@login_required
def mock_exam_score_sheet_view(request):
    """
    Main mock exam score sheet interface with dynamic filtering by class/form, subject, and mock exam.
    """
    try:
        # Get current school context
        school = getattr(request.user, "school", None)
        if not school:
            school = SchoolInformation.objects.first()

        # Get current academic year
        current_academic_year = AcademicYear.objects.filter(
            school=school, is_current=True
        ).first()

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

        # Get all subjects for the school
        subjects = Subject.objects.filter(school=school).order_by("subject_name")

        # Get all active mock exams
        mock_exams = MockExam.objects.filter(
            school=school, is_active=True
        ).order_by("-exam_date")

        # Default selections
        selected_class = classes.first() if classes.exists() else None
        selected_form = None
        selected_subject = None  # Will be set to "All Subjects" by default
        selected_mock_exam = mock_exams.first() if mock_exams.exists() else None

        # Get score data based on selections (default to class level)
        score_data = []
        if selected_class and selected_mock_exam:
            score_data = get_mock_exam_score_sheet_data(
                school, selected_class, selected_subject, selected_mock_exam
            )

        context = {
            "classes": classes,
            "forms": forms,
            "subjects": subjects,
            "mock_exams": mock_exams,
            "selected_class": selected_class,
            "selected_form": selected_form,
            "selected_subject": selected_subject,
            "selected_mock_exam": selected_mock_exam,
            "score_data": score_data,
            "current_academic_year": current_academic_year,
            "school": school,
        }

        return render(request, "mock_exams/score_sheet.html", context)

    except Exception as e:
        logger.error(f"Error in mock_exam_score_sheet_view: {str(e)}")
        return render(
            request,
            "mock_exams/score_sheet.html",
            {
                "classes": [],
                "forms": [],
                "subjects": [],
                "mock_exams": [],
                "error": str(e),
                "score_data": [],
            },
        )


def get_mock_exam_score_sheet_data(school, selected_class, selected_subject, selected_mock_exam):
    """
    Helper function to retrieve and format mock exam score sheet data.
    """
    if not selected_class or not selected_mock_exam:
        return []

    try:
        # Get all students in the selected class
        student_classes = StudentClass.objects.filter(
            assigned_class=selected_class, is_active=True
        ).select_related("student")

        students = [sc.student for sc in student_classes]

        if not students:
            return []

        # Determine which subjects to include
        if selected_subject:
            # Single subject view
            subjects_to_include = [selected_subject]
        else:
            # All subjects view - get all subjects for this class (only active ones)
            class_subjects = ClassSubject.objects.filter(
                class_name=selected_class, is_active=True
            ).select_related("subject")
            subjects_to_include = [cs.subject for cs in class_subjects]

        score_data = []

        for student in students:
            student_data = {
                "student": student,
                "subjects": {},
                "total_score": 0,
                "average_score": 0,
                "position": 0,
                "grade": "N/A",
                "remarks": "Not Graded",
            }

            total_subject_scores = 0
            valid_subjects = 0

            for subject in subjects_to_include:
                # Get ClassSubject for this class and subject
                class_subject = ClassSubject.objects.filter(
                    class_name=selected_class,
                    subject=subject,
                    is_active=True,
                ).first()

                if not class_subject:
                    student_data["subjects"][subject.subject_name] = {
                        "score": 0,
                        "grade": "N/A",
                        "position": 0,
                        "raw_score": 0,
                    }
                    continue

                # Get mock exam assessment for this student, class_subject, and mock_exam
                assessment = Assessment.objects.filter(
                    student=student,
                    class_subject=class_subject,
                    assessment_type="mock_exam",
                    mock_exam=selected_mock_exam,
                ).first()

                if assessment and assessment.total_score is not None:
                    student_data["subjects"][subject.subject_name] = {
                        "score": float(assessment.total_score),
                        "grade": assessment.grade or "N/A",
                        "position": assessment.position or 0,
                        "raw_score": (
                            float(assessment.raw_exam_score)
                            if assessment.raw_exam_score
                            else 0
                        ),
                    }
                    total_subject_scores += float(assessment.total_score)
                    valid_subjects += 1
                else:
                    student_data["subjects"][subject.subject_name] = {
                        "score": 0,
                        "grade": "N/A",
                        "position": 0,
                        "raw_score": 0,
                    }

            # Calculate average score
            if valid_subjects > 0:
                student_data["average_score"] = round(
                    total_subject_scores / valid_subjects, 2
                )
                student_data["total_score"] = total_subject_scores

                # Get grade and remarks for average score
                grade_info = GradingSystem.get_grade_for_score(
                    Decimal(str(student_data["average_score"])), school
                )
                if grade_info:
                    student_data["grade"] = grade_info.grade_letter
                    student_data["remarks"] = grade_info.remarks

            score_data.append(student_data)

        # Sort by average score (descending) and assign positions
        score_data.sort(key=lambda x: x["average_score"], reverse=True)

        for i, student_data in enumerate(score_data):
            student_data["position"] = i + 1

        return score_data

    except Exception as e:
        logger.error(f"Error in get_mock_exam_score_sheet_data: {str(e)}")
        return []


@login_required
@require_http_methods(["GET"])
def get_mock_exam_score_sheet_data_ajax(request):
    """
    AJAX endpoint to get mock exam score sheet data based on selected class, subject, and mock exam.
    """
    try:
        class_id = request.GET.get("class_id")
        subject_id = request.GET.get("subject_id")
        mock_exam_id = request.GET.get("mock_exam_id")

        if not class_id:
            return JsonResponse({"error": "Class ID is required"}, status=400)

        if not mock_exam_id:
            return JsonResponse({"error": "Mock Exam ID is required"}, status=400)

        # Get current school context
        school = getattr(request.user, "school", None)
        if not school:
            school = SchoolInformation.objects.first()

        # Get selected class
        selected_class = get_object_or_404(Class, class_id=class_id)

        # Get selected subject (None means "All Subjects")
        selected_subject = None
        if subject_id and subject_id != "all":
            selected_subject = get_object_or_404(Subject, pk=subject_id)

        # Get selected mock exam
        selected_mock_exam = get_object_or_404(
            MockExam, pk=mock_exam_id, school=school, is_active=True
        )

        # Get score data
        score_data = get_mock_exam_score_sheet_data(
            school, selected_class, selected_subject, selected_mock_exam
        )

        # Render the score sheet content
        html_content = render_to_string(
            "mock_exams/partials/score_sheet_content.html",
            {
                "score_data": score_data,
                "selected_class": selected_class,
                "selected_subject": selected_subject,
                "selected_mock_exam": selected_mock_exam,
                "school": school,
            },
        )

        return JsonResponse(
            {
                "success": True,
                "html_content": html_content,
                "selected_subject": {
                    "id": selected_subject.id if selected_subject else None,
                    "subject_name": selected_subject.subject_name
                    if selected_subject
                    else None,
                },
            }
        )

    except Exception as e:
        logger.error(f"Error in get_mock_exam_score_sheet_data_ajax: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def get_form_level_mock_exam_score_sheet_data_ajax(request):
    """
    AJAX endpoint to get form-level mock exam score sheet data.
    """
    try:
        form_id = request.GET.get("form_id")
        subject_id = request.GET.get("subject_id")
        mock_exam_id = request.GET.get("mock_exam_id")

        if not form_id:
            return JsonResponse({"error": "Form ID is required"}, status=400)

        if not mock_exam_id:
            return JsonResponse({"error": "Mock Exam ID is required"}, status=400)

        # Get current school context
        school = getattr(request.user, "school", None)
        if not school:
            school = SchoolInformation.objects.first()

        # Get selected form and subject
        selected_form = get_object_or_404(Form, pk=form_id, school=school)
        selected_subject = None
        if subject_id and subject_id != "all":
            selected_subject = get_object_or_404(Subject, pk=subject_id, school=school)

        # Get selected mock exam
        selected_mock_exam = get_object_or_404(
            MockExam, pk=mock_exam_id, school=school, is_active=True
        )

        # Get score data
        score_data = get_form_level_mock_exam_score_sheet_data(
            school, selected_form, selected_subject, selected_mock_exam
        )

        # Serialize score data for JSON response
        serialized_score_data = []
        for student_data in score_data:
            serialized_student = {
                "student": {
                    "full_name": student_data["student"].full_name,
                    "admission_number": student_data["student"].admission_number,
                },
                "student_class": {
                    "name": student_data["student_class"].name,
                },
                "subjects": student_data["subjects"],
                "average_score": student_data["average_score"],
                "position": student_data["position"],
                "grade": student_data["grade"],
                "remarks": student_data["remarks"],
            }
            serialized_score_data.append(serialized_student)

        return JsonResponse(
            {
                "success": True,
                "score_data": serialized_score_data,
                "selected_subject": {
                    "id": selected_subject.id if selected_subject else None,
                    "subject_name": selected_subject.subject_name
                    if selected_subject
                    else None,
                },
            }
        )

    except Exception as e:
        logger.error(f"Error in get_form_level_mock_exam_score_sheet_data_ajax: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def print_mock_exam_score_sheet(request):
    """
    Print mock exam score sheet as HTML (for print preview).
    """
    try:
        class_id = request.GET.get("class_id")
        subject_id = request.GET.get("subject_id")
        mock_exam_id = request.GET.get("mock_exam_id")

        if not class_id:
            return JsonResponse({"error": "Class ID is required"}, status=400)

        if not mock_exam_id:
            return JsonResponse({"error": "Mock Exam ID is required"}, status=400)

        # Get current school context
        school = getattr(request.user, "school", None)
        if not school:
            school = SchoolInformation.objects.first()

        # Get selected class and subject
        selected_class = get_object_or_404(Class, class_id=class_id, school=school)
        selected_subject = None
        if subject_id and subject_id != "all":
            selected_subject = get_object_or_404(Subject, pk=subject_id, school=school)

        # Get selected mock exam
        selected_mock_exam = get_object_or_404(
            MockExam, pk=mock_exam_id, school=school, is_active=True
        )

        # Get score data
        score_data = get_mock_exam_score_sheet_data(
            school, selected_class, selected_subject, selected_mock_exam
        )

        # Render HTML template for printing
        return render(
            request,
            "mock_exams/print/score_sheet_print.html",
            {
                "score_data": score_data,
                "selected_class": selected_class,
                "selected_subject": selected_subject,
                "selected_mock_exam": selected_mock_exam,
                "school": school,
                "request": request,
            },
        )

    except Exception as e:
        logger.error(f"Error in print_mock_exam_score_sheet: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def export_mock_exam_score_sheet_pdf(request):
    """
    Export mock exam score sheet as PDF.
    """
    try:
        class_id = request.GET.get("class_id")
        subject_id = request.GET.get("subject_id")
        mock_exam_id = request.GET.get("mock_exam_id")

        if not class_id:
            return JsonResponse({"error": "Class ID is required"}, status=400)

        if not mock_exam_id:
            return JsonResponse({"error": "Mock Exam ID is required"}, status=400)

        # Get current school context
        school = getattr(request.user, "school", None)
        if not school:
            school = SchoolInformation.objects.first()

        # Get selected class and subject
        selected_class = get_object_or_404(Class, class_id=class_id, school=school)
        selected_subject = None
        if subject_id and subject_id != "all":
            selected_subject = get_object_or_404(Subject, pk=subject_id, school=school)

        # Get selected mock exam
        selected_mock_exam = get_object_or_404(
            MockExam, pk=mock_exam_id, school=school, is_active=True
        )

        # Get score data
        score_data = get_mock_exam_score_sheet_data(
            school, selected_class, selected_subject, selected_mock_exam
        )

        # Generate PDF
        html_content = render_to_string(
            "mock_exams/print/score_sheet_print.html",
            {
                "score_data": score_data,
                "selected_class": selected_class,
                "selected_subject": selected_subject,
                "selected_mock_exam": selected_mock_exam,
                "school": school,
                "request": request,
            },
        )

        pdf_content = generate_pdf_from_html(html_content)

        # Prepare response
        filename = f"mock_exam_score_sheet_{selected_class.name}"
        if selected_subject:
            filename += f"_{selected_subject.subject_name}"
        filename += f"_{selected_mock_exam.name.replace(' ', '_')}.pdf"

        response = HttpResponse(pdf_content, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        return response

    except Exception as e:
        logger.error(f"Error in export_mock_exam_score_sheet_pdf: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def export_mock_exam_score_sheet_excel(request):
    """
    Export mock exam score sheet as Excel.
    """
    try:
        class_id = request.GET.get("class_id")
        subject_id = request.GET.get("subject_id")
        mock_exam_id = request.GET.get("mock_exam_id")

        if not class_id:
            return JsonResponse({"error": "Class ID is required"}, status=400)

        if not mock_exam_id:
            return JsonResponse({"error": "Mock Exam ID is required"}, status=400)

        # Get current school context
        school = getattr(request.user, "school", None)
        if not school:
            school = SchoolInformation.objects.first()

        # Get selected class and subject
        selected_class = get_object_or_404(Class, class_id=class_id, school=school)
        selected_subject = None
        if subject_id and subject_id != "all":
            selected_subject = get_object_or_404(Subject, pk=subject_id, school=school)

        # Get selected mock exam
        selected_mock_exam = get_object_or_404(
            MockExam, pk=mock_exam_id, school=school, is_active=True
        )

        # Get score data
        score_data = get_mock_exam_score_sheet_data(
            school, selected_class, selected_subject, selected_mock_exam
        )

        # Prepare Excel data (similar to termly score sheet)
        excel_data = []
        excel_data.append(["Student ID", "Student Name"])

        if selected_subject:
            # Single subject view
            excel_data[0].extend(["Raw Score", "Total Score", "Grade", "Remarks", "Position"])
        else:
            # All subjects view
            if score_data and score_data[0].get("subjects"):
                for subject_name in score_data[0]["subjects"].keys():
                    excel_data[0].append(subject_name)
            excel_data[0].extend(["Average Score", "Position"])

        for student_data in score_data:
            row = [
                student_data["student"].admission_number,
                student_data["student"].full_name,
            ]

            if selected_subject:
                # Single subject view
                subject_data = student_data["subjects"].get(selected_subject.subject_name, {})
                row.extend([
                    subject_data.get("raw_score", 0),
                    subject_data.get("score", 0),
                    subject_data.get("grade", "N/A"),
                    student_data.get("remarks", "Not Graded"),
                    student_data.get("position", 0),
                ])
            else:
                # All subjects view
                if student_data.get("subjects"):
                    for subject_name in score_data[0]["subjects"].keys():
                        subject_data = student_data["subjects"].get(subject_name, {})
                        row.append(subject_data.get("score", 0))
                row.extend([
                    student_data.get("average_score", 0),
                    student_data.get("position", 0),
                ])

            excel_data.append(row)

        # Generate Excel file
        excel_file = generate_excel_from_data(excel_data)

        # Prepare response
        filename = f"mock_exam_score_sheet_{selected_class.name}"
        if selected_subject:
            filename += f"_{selected_subject.subject_name}"
        filename += f"_{selected_mock_exam.name.replace(' ', '_')}.xlsx"

        response = HttpResponse(
            excel_file.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        return response

    except Exception as e:
        logger.error(f"Error in export_mock_exam_score_sheet_excel: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def print_form_level_mock_exam_score_sheet(request):
    """
    Print form-level mock exam score sheet as HTML (for print preview).
    """
    try:
        form_id = request.GET.get("form_id")
        subject_id = request.GET.get("subject_id")
        mock_exam_id = request.GET.get("mock_exam_id")

        if not form_id:
            return JsonResponse({"error": "Form ID is required"}, status=400)

        if not mock_exam_id:
            return JsonResponse({"error": "Mock Exam ID is required"}, status=400)

        # Get current school context
        school = getattr(request.user, "school", None)
        if not school:
            school = SchoolInformation.objects.first()

        # Get selected form and subject
        selected_form = get_object_or_404(Form, pk=form_id, school=school)
        selected_subject = None
        if subject_id and subject_id != "all":
            selected_subject = get_object_or_404(Subject, pk=subject_id, school=school)

        # Get selected mock exam
        selected_mock_exam = get_object_or_404(
            MockExam, pk=mock_exam_id, school=school, is_active=True
        )

        # Get score data
        score_data = get_form_level_mock_exam_score_sheet_data(
            school, selected_form, selected_subject, selected_mock_exam
        )

        # Render HTML template for printing
        return render(
            request,
            "mock_exams/print/score_sheet_print.html",
            {
                "score_data": score_data,
                "selected_form": selected_form,
                "selected_subject": selected_subject,
                "selected_mock_exam": selected_mock_exam,
                "school": school,
                "request": request,
                "is_form_level": True,  # Flag to indicate this is form-level
            },
        )

    except Exception as e:
        logger.error(f"Error in print_form_level_mock_exam_score_sheet: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def export_form_level_mock_exam_score_sheet_pdf(request):
    """
    Export form-level mock exam score sheet as PDF.
    """
    try:
        form_id = request.GET.get("form_id")
        subject_id = request.GET.get("subject_id")
        mock_exam_id = request.GET.get("mock_exam_id")

        if not form_id:
            return JsonResponse({"error": "Form ID is required"}, status=400)

        if not mock_exam_id:
            return JsonResponse({"error": "Mock Exam ID is required"}, status=400)

        # Get current school context
        school = getattr(request.user, "school", None)
        if not school:
            school = SchoolInformation.objects.first()

        # Get selected form and subject
        selected_form = get_object_or_404(Form, pk=form_id, school=school)
        selected_subject = None
        if subject_id and subject_id != "all":
            selected_subject = get_object_or_404(Subject, pk=subject_id, school=school)

        # Get selected mock exam
        selected_mock_exam = get_object_or_404(
            MockExam, pk=mock_exam_id, school=school, is_active=True
        )

        # Get score data
        score_data = get_form_level_mock_exam_score_sheet_data(
            school, selected_form, selected_subject, selected_mock_exam
        )

        # Generate PDF
        html_content = render_to_string(
            "mock_exams/print/score_sheet_print.html",
            {
                "score_data": score_data,
                "selected_form": selected_form,
                "selected_subject": selected_subject,
                "selected_mock_exam": selected_mock_exam,
                "school": school,
                "request": request,
                "is_form_level": True,
            },
        )

        pdf_content = generate_pdf_from_html(html_content)

        # Prepare response
        filename = f"form_level_mock_exam_score_sheet_{selected_form.name}"
        if selected_subject:
            filename += f"_{selected_subject.subject_name}"
        filename += f"_{selected_mock_exam.name.replace(' ', '_')}.pdf"

        response = HttpResponse(pdf_content, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        return response

    except Exception as e:
        logger.error(f"Error in export_form_level_mock_exam_score_sheet_pdf: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)

