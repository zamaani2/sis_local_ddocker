# Class view
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.template.loader import render_to_string

from django.db.models import Count, Q, F
from django.conf import settings
from django.db import transaction
import logging

from shs_system.models import (
    Class,
    Teacher,
    AcademicYear,
    Student,
    SchoolInformation,
    LearningArea,
    Form,
    StudentClass,
    ClassSubject,
    Subject,
    Term,
    Assessment,
    TeacherSubjectAssignment,
    ClassTeacher,
)
from shs_system.forms import ClassForm, StudentClassAssignmentForm, StudentForm
import csv
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from io import StringIO
import datetime


def get_user_school(user):
    """
    Get the school associated with the current user.
    For superadmins, this will return None (they can access all schools).
    For other users, it will return their associated school.
    """
    if user.is_superadmin:
        return None  # Superadmins can access all schools
    return user.school


@login_required
def class_list(request):
    # Get the user's school
    school = get_user_school(request.user)

    # Get current academic year or use the one from the filter
    current_academic_year = SchoolInformation.get_current_academic_year(school=school)

    # Get the academic year ID from request parameters or use current academic year
    academic_year_id = request.GET.get("academic_year")

    
    # Always default to current academic year if no specific year is requested
    if not academic_year_id:
        if current_academic_year:
            academic_year_id = str(current_academic_year.id)
        else:
            # Fallback: get the most recent academic year for this school
            if school:
                latest_academic_year = (
                    AcademicYear.objects.filter(school=school, is_archived=False)
                    .order_by("-start_date")
                    .first()
                )
                if latest_academic_year:
                    academic_year_id = str(latest_academic_year.id)


    # Apply filters if they exist
    form_filter = request.GET.get("form", None)
    learning_area_filter = request.GET.get("learning_area", None)
    search = request.GET.get("search", "")

    # Start with all classes, filtered by school if needed
    classes = Class.objects.all()
    if school:
        classes = classes.filter(school=school)


    # Apply academic year filter - now we always have an academic_year_id

    if academic_year_id:
        try:
            academic_year = AcademicYear.objects.get(pk=academic_year_id)
            classes = classes.filter(academic_year=academic_year)
        except AcademicYear.DoesNotExist:

            # If the academic year doesn't exist, fall back to current academic year
            if current_academic_year:
                academic_year = current_academic_year
                classes = classes.filter(academic_year=academic_year)
                academic_year_id = str(current_academic_year.id)
            else:
                academic_year = None
    else:
        academic_year = None


    # Apply form filter if it exists
    if form_filter:
        try:
            form_filter = int(form_filter)
            classes = classes.filter(form=form_filter)
        except (ValueError, TypeError):
            pass

    # Apply learning area filter if it exists
    if learning_area_filter:
        classes = classes.filter(learning_area=learning_area_filter)

    # Apply search if it exists
    if search:
        # Use a subquery to find classes where the teacher name matches the search term
        teacher_classes_query = ClassTeacher.objects.filter(
            teacher__full_name__icontains=search, is_active=True
        )

        # Filter teacher classes by school if user is not a superadmin
        if school:
            teacher_classes_query = teacher_classes_query.filter(school=school)

        teacher_classes = teacher_classes_query.values_list(
            "class_assigned_id", flat=True
        )

        classes = classes.filter(Q(name__icontains=search) | Q(id__in=teacher_classes))


    # Annotate with student count only first
    classes = classes.annotate(
        student_count=Count("studentclass", filter=Q(studentclass__is_active=True))
    ).select_related("academic_year", "form", "learning_area")
    
    # Add subject count manually to avoid annotation issues
    for class_obj in classes:
        # Count subjects for this specific class and academic year (only active ones)
        subject_count = ClassSubject.objects.filter(
            class_name=class_obj,
            academic_year=class_obj.academic_year,
            is_active=True
        ).count()
        class_obj.subject_count = subject_count


    # Get class teacher information from ClassTeacher model
    class_teachers_query = ClassTeacher.objects.filter(
        class_assigned__in=classes, is_active=True
    )

    # Add academic year filter if available
    if academic_year:
        class_teachers_query = class_teachers_query.filter(academic_year=academic_year)

    # Filter class teachers by school if user is not a superadmin
    if school:
        class_teachers_query = class_teachers_query.filter(school=school)

    class_teachers = {
        ct.class_assigned_id: ct.teacher.full_name
        for ct in class_teachers_query.select_related("teacher")
    }

    # Add class teacher names to each class
    for class_obj in classes:
        class_obj.class_teacher_name = class_teachers.get(class_obj.id)

    # Forms for filtering - filter by school if user is not a superadmin
    forms_query = Form.objects.all()
    if school:
        forms_query = forms_query.filter(school=school)
    forms = [

        (form.id, form.name) for form in forms_query.order_by("form_number")

    ]

    # Learning areas - filter by school if user is not a superadmin
    learning_areas_query = LearningArea.objects.all()
    if school:
        learning_areas_query = learning_areas_query.filter(school=school)
    learning_areas = [
        (area.id, area.name) for area in learning_areas_query.order_by("name")
    ]

    # Get all academic years for the dropdown - filter by school if user is not a superadmin
    academic_years_query = AcademicYear.objects.all()
    if school:
        academic_years_query = academic_years_query.filter(school=school)
    academic_years = academic_years_query.order_by("-is_current", "-start_date")

    context = {
        "title": "Class List",
        "classes": classes,
        "forms": forms,
        "learning_areas": learning_areas,
        "form_filter": form_filter,
        "learning_area_filter": learning_area_filter,
        "academic_years": academic_years,
        "current_year_id": int(academic_year_id) if academic_year_id else None,

        "current_academic_year": current_academic_year,
        "academic_year": academic_year,

        "search": search,
    }

    # Return JSON response for AJAX requests
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse(
            {
                "success": True,
                "redirect_url": f"{reverse('class_list')}?{request.GET.urlencode()}",
            }
        )

    return render(request, "class/class_list.html", context)


@login_required
def class_detail(request, class_id):
    """View to display detailed information about a specific class"""
    # Get the user's school
    school = get_user_school(request.user)

    # Get the class object, filtering by school if user is not a superadmin
    class_query = Class.objects.select_related("academic_year")
    if school:
        class_query = class_query.filter(school=school)
    class_obj = get_object_or_404(class_query, class_id=class_id)

    # Get class teacher information from ClassTeacher model
    class_teacher_query = ClassTeacher.objects.filter(
        class_assigned=class_obj,
        academic_year=class_obj.academic_year,
        is_active=True,
    )

    # Filter by school if user is not a superadmin
    if school:
        class_teacher_query = class_teacher_query.filter(school=school)

    class_teacher = class_teacher_query.select_related("teacher").first()

    if class_teacher:
        class_obj.class_teacher = class_teacher.teacher
        class_obj.class_teacher_name = class_teacher.teacher.full_name
    else:
        class_obj.class_teacher = None
        class_obj.class_teacher_name = None

    # Get all students in this class
    students_query = class_obj.studentclass_set.filter(is_active=True)

    # Filter by school if user is not a superadmin
    if school:
        students_query = students_query.filter(school=school)

    students = students_query.select_related("student")

    # Get available classes for both assignment forms
    current_academic_year = SchoolInformation.get_current_academic_year(school=school)
    available_classes = []

    if current_academic_year:
        available_classes_query = Class.objects.filter(
            academic_year=current_academic_year
        )
        if school:
            available_classes_query = available_classes_query.filter(school=school)
        available_classes = available_classes_query

    # Create assignment forms for each student
    assignment_forms = {}
    for student_class in students:
        student = student_class.student
        # Create the form with initial values and available classes
        form = StudentClassAssignmentForm(initial={"assigned_class": class_obj.id})
        # If your form takes a queryset for available classes:
        # form.fields['assigned_class'].queryset = available_classes
        assignment_forms[student.id] = form

    # Add new student form for the add student modal
    new_student_form = StudentForm()


    # Get class subjects for the current academic year (only active ones)
    class_subjects_query = ClassSubject.objects.filter(
        class_name=class_obj, academic_year=class_obj.academic_year, is_active=True

    )
    class_subjects = class_subjects_query.select_related("subject")

    # Get the teacher assignments for these class subjects
    class_subject_ids = [cs.id for cs in class_subjects]
    teacher_assignments = {}

    # Get active teacher subject assignments for these subjects
    subject_teachers_query = TeacherSubjectAssignment.objects.filter(
        class_assigned=class_obj, academic_year=class_obj.academic_year, is_active=True
    )

    # Filter by school if user is not a superadmin
    if school:
        subject_teachers_query = subject_teachers_query.filter(school=school)


    # Filter out assignments where ClassSubject is not active
    # Get active class-subject combinations
    active_class_subjects = ClassSubject.objects.filter(
        academic_year=class_obj.academic_year, is_active=True
    ).values_list('class_name_id', 'subject_id')
    
    # Filter assignments to only include those with active ClassSubject
    filtered_assignments = []
    for assignment in subject_teachers_query.select_related("teacher", "subject"):
        if (assignment.class_assigned.id, assignment.subject.id) in active_class_subjects:
            filtered_assignments.append(assignment)
    
    subject_teachers = filtered_assignments


    # Create a mapping of subject_id to teacher
    for assignment in subject_teachers:
        teacher_assignments[assignment.subject.id] = assignment.teacher

    # Get available subjects and teachers for assignment
    available_subjects_query = Subject.objects.all()
    available_teachers_query = Teacher.objects.all()

    # Filter by school if user is not a superadmin
    if school:
        available_subjects_query = available_subjects_query.filter(school=school)
        available_teachers_query = available_teachers_query.filter(school=school)

    available_subjects = available_subjects_query.order_by("subject_name")
    available_teachers = available_teachers_query.order_by("full_name")

    # Get forms and learning areas for the user's school
    forms_query = Form.objects.all()
    learning_areas_query = LearningArea.objects.all()

    if school:
        forms_query = forms_query.filter(school=school)
        learning_areas_query = learning_areas_query.filter(school=school)

    context = {
        "class": class_obj,
        "class_teacher": class_teacher.teacher if class_teacher else None,
        "students": students,
        "student_count": students.count(),
        "title": f"Class: {class_obj.name}",
        "assignment_forms": assignment_forms,
        "forms": [

            (form.id, form.name)

            for form in forms_query.order_by("form_number")
        ],
        "learning_areas": [
            (area.id, area.name) for area in learning_areas_query.order_by("name")
        ],
        "new_student_form": new_student_form,
        "available_classes": available_classes,
        "class_subjects": class_subjects,
        "teacher_assignments": teacher_assignments,
        "available_subjects": available_subjects,
        "available_teachers": available_teachers,
    }
    return render(request, "class/class_detail.html", context)


@login_required
def create_class(request):
    """View to create a new class, can be called via AJAX for modal"""
    # Get the user's school
    school = get_user_school(request.user)

    if request.method == "POST":
        form = ClassForm(request.POST)
        if form.is_valid():
            new_class = form.save(commit=False)

            # Set the school for the new class
            if school:
                new_class.school = school

            new_class.save()

            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {
                        "success": True,
                        "message": f"Class {new_class.name} has been created successfully.",
                        "redirect_url": reverse(
                            "class_detail", kwargs={"class_id": new_class.class_id}
                        ),
                    }
                )

            messages.success(
                request, f"Class {new_class.name} has been created successfully."
            )
            return redirect("class_detail", class_id=new_class.class_id)
        else:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {
                        "success": False,
                        "html": render_to_string(
                            "class/includes/class_form.html",
                            {"form": form},
                            request=request,
                        ),
                    }
                )
    else:
        form = ClassForm()


        # Simplified database queries for better performance
        if school and hasattr(form, "fields"):
            try:
                if "form" in form.fields:
                    form.fields["form"].queryset = Form.objects.filter(school=school).only('id', 'name')
                if "learning_area" in form.fields:
                    form.fields["learning_area"].queryset = LearningArea.objects.filter(
                        school=school
                    ).only('id', 'name')
                if "academic_year" in form.fields:
                    form.fields["academic_year"].queryset = AcademicYear.objects.filter(
                        school=school
                    ).only('id', 'name')
            except Exception as e:
                print(f"Error filtering form fields: {e}")
                # If there's an error, use empty querysets
                if "form" in form.fields:
                    form.fields["form"].queryset = Form.objects.none()
                if "learning_area" in form.fields:
                    form.fields["learning_area"].queryset = LearningArea.objects.none()
                if "academic_year" in form.fields:
                    form.fields["academic_year"].queryset = AcademicYear.objects.none()


    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        try:
            html = render_to_string(
                "class/includes/class_form.html", {"form": form}, request=request
            )
            return JsonResponse({"html": html})
        except Exception as e:
            import traceback

            error_details = traceback.format_exc()
            print(f"Error rendering class form: {error_details}")
            return JsonResponse(
                {
                    "success": False,
                    "error": f"Error loading form: {str(e)}",
                    "details": error_details if settings.DEBUG else None,
                },
                status=500,
            )

    context = {"form": form, "title": "Create New Class"}
    return render(request, "class/class_form.html", context)


@login_required

def get_class_form_data(request):
    """API endpoint to get form data for class creation/editing - optimized for performance"""
    from django.core.cache import cache
    from django.http import JsonResponse
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        school = get_user_school(request.user)
        cache_key = f"class_form_data_{school.id if school else 'no_school'}"
        
        # Try to get cached data first
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"Returning cached form data for school {school.id if school else 'no_school'}")
            return JsonResponse(cached_data)
        
        # If not cached, build the data
        form_data = {
            'forms': [],
            'learning_areas': [],
            'academic_years': []
        }
        
        if school:
            logger.info(f"Building form data for school {school.id}")
            # Optimize queries with only() to fetch only needed fields
            forms = Form.objects.filter(school=school).only('id', 'name').order_by('name')
            learning_areas = LearningArea.objects.filter(school=school).only('id', 'name').order_by('name')
            academic_years = AcademicYear.objects.filter(school=school).only('id', 'name').order_by('-name')
            
            form_data['forms'] = [{'id': f.id, 'name': f.name} for f in forms]
            form_data['learning_areas'] = [{'id': la.id, 'name': la.name} for la in learning_areas]
            form_data['academic_years'] = [{'id': ay.id, 'name': ay.name} for ay in academic_years]
            
            logger.info(f"Form data built: {len(form_data['forms'])} forms, {len(form_data['learning_areas'])} learning areas, {len(form_data['academic_years'])} academic years")
        else:
            logger.warning("No school found for user, returning empty form data")
        
        # Cache for 5 minutes
        cache.set(cache_key, form_data, 300)
        
        return JsonResponse(form_data)
        
    except Exception as e:
        logger.error(f"Error in get_class_form_data: {str(e)}")
        return JsonResponse({
            'error': 'Failed to load form data',
            'forms': [],
            'learning_areas': [],
            'academic_years': []
        }, status=500)


@login_required

def update_class(request, class_id):
    """View to update an existing class, can be called via AJAX for modal"""
    # Get the user's school
    school = get_user_school(request.user)

    # Get the class object, filtering by school if user is not a superadmin
    class_query = Class.objects
    if school:
        class_query = class_query.filter(school=school)
    class_obj = get_object_or_404(class_query, class_id=class_id)

    if request.method == "POST":
        form = ClassForm(request.POST, instance=class_obj)
        if form.is_valid():
            updated_class = form.save(commit=False)

            # Ensure school doesn't change if user has a school
            if school:
                updated_class.school = school

            updated_class.save()

            message = f"Class '{class_obj.name}' was successfully updated."

            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {
                        "success": True,
                        "message": message,
                        "redirect_url": reverse(
                            "class_detail", kwargs={"class_id": class_id}
                        ),
                    }
                )

            messages.success(request, message)
            return redirect("class_detail", class_id=class_id)
        else:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {
                        "success": False,
                        "html": render_to_string(
                            "class/includes/class_form.html",
                            {"form": form, "class": class_obj},
                            request=request,
                        ),
                    }
                )
    else:
        form = ClassForm(instance=class_obj)

        # Filter form fields based on user's school
        if school and hasattr(form, "fields"):
            if "form" in form.fields:
                form.fields["form"].queryset = Form.objects.filter(school=school)
            if "learning_area" in form.fields:
                form.fields["learning_area"].queryset = LearningArea.objects.filter(
                    school=school
                )
            if "academic_year" in form.fields:
                form.fields["academic_year"].queryset = AcademicYear.objects.filter(
                    school=school
                )

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        try:
            html = render_to_string(
                "class/includes/class_form.html",
                {"form": form, "class": class_obj},
                request=request,
            )
            return JsonResponse({"html": html})
        except Exception as e:
            import traceback

            error_details = traceback.format_exc()
            print(f"Error rendering class form: {error_details}")
            return JsonResponse(
                {
                    "success": False,
                    "error": f"Error loading form: {str(e)}",
                    "details": error_details if settings.DEBUG else None,
                },
                status=500,
            )

    return render(
        request,
        "class/class_form.html",
        {"form": form, "class": class_obj, "title": f"Update {class_obj.name}"},
    )


@login_required
def delete_class(request, class_id):
    """View to delete a class, can be called via AJAX"""
    # Get the user's school
    school = get_user_school(request.user)

    # Get the class object, filtering by school if user is not a superadmin
    class_query = Class.objects
    if school:
        class_query = class_query.filter(school=school)
    class_obj = get_object_or_404(class_query, class_id=class_id)

    class_name = class_obj.name

    if request.method == "POST":
        # Check for students in this class
        student_class_query = StudentClass.objects.filter(
            assigned_class=class_obj, is_active=True
        )

        # Filter by school if user is not a superadmin
        if school:
            student_class_query = student_class_query.filter(school=school)

        student_count = student_class_query.count()

        # If there are students, don't delete
        if student_count > 0:
            message = f"Cannot delete class '{class_name}' because it has {student_count} students assigned to it."
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"success": False, "message": message}, status=400)

            messages.error(request, message)
            return redirect("class_list")

        # Delete the class
        try:
            class_obj.delete()
            message = f"Class '{class_name}' was successfully deleted."

            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"success": True, "message": message})

            messages.success(request, message)
            return redirect("class_list")

        except Exception as e:
            message = f"Error deleting class: {str(e)}"
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"success": False, "message": message}, status=500)

            messages.error(request, message)
            return redirect("class_list")

    # GET request - show confirmation page
    return render(
        request,
        "class/class_confirm_delete.html",
        {"class": class_obj, "title": f"Delete {class_name}"},
    )


@login_required
def generate_class_report(request, class_id):
    # Get the user's school
    school = get_user_school(request.user)

    # Get the class object, filtering by school if user is not a superadmin
    class_query = Class.objects
    if school:
        class_query = class_query.filter(school=school)
    class_obj = get_object_or_404(class_query, class_id=class_id)

    # Get current academic year and term (or use the ones associated with the class)
    academic_year = class_obj.academic_year

    # Get current term, filtering by school if user is not a superadmin
    term_query = Term.objects.filter(academic_year=academic_year, is_current=True)
    if school:
        term_query = term_query.filter(school=school)
    current_term = term_query.first()

    # Get all students in this class
    student_classes_query = StudentClass.objects.filter(
        assigned_class=class_obj, is_active=True
    )

    # Filter by school if user is not a superadmin
    if school:
        student_classes_query = student_classes_query.filter(school=school)

    student_classes = student_classes_query.select_related("student")


    # Get all subjects for this class (only active ones)
    class_subjects_query = ClassSubject.objects.filter(
        class_name=class_obj,
        academic_year=academic_year,
        is_active=True

    )
    class_subjects = class_subjects_query.select_related("subject")

    # Get teacher assignments for these subjects
    teacher_assignments = {}
    subject_teachers_query = TeacherSubjectAssignment.objects.filter(
        class_assigned=class_obj, academic_year=academic_year, is_active=True
    )

    # Filter by school if user is not a superadmin
    if school:
        subject_teachers_query = subject_teachers_query.filter(school=school)

    subject_teachers = subject_teachers_query.select_related("teacher", "subject")

    # Create a mapping of subject_id to teacher
    for assignment in subject_teachers:
        teacher_assignments[assignment.subject.id] = assignment.teacher

    # Prepare report data
    report_data = []

    for student_class in student_classes:
        student = student_class.student
        student_data = {
            "student": student,
            "admission_number": student.admission_number,
            "full_name": student.full_name,
            "gender": student.get_gender_display(),
            "subjects": [],
        }

        total_score = 0
        subjects_count = 0

        for cs in class_subjects:
            # Get assessment for this student in this subject

            # Exclude mock exam assessments from class report calculations
            assessment_query = Assessment.objects.filter(
                class_subject=cs, student=student
            ).exclude(assessment_type='mock_exam')

            assessment = assessment_query.first()

            # Get teacher for this subject
            teacher = teacher_assignments.get(cs.subject.id)
            teacher_name = teacher.full_name if teacher else "Not Assigned"

            subject_data = {
                "subject_name": cs.subject.subject_name,
                "teacher": teacher_name,
                "class_score": (
                    assessment.class_score
                    if assessment and assessment.class_score
                    else 0
                ),
                "exam_score": (
                    assessment.exam_score if assessment and assessment.exam_score else 0
                ),
                "total_score": (
                    assessment.total_score
                    if assessment and assessment.total_score
                    else 0
                ),
                "grade": assessment.grade if assessment and assessment.grade else "N/A",
                "position": (
                    assessment.position if assessment and assessment.position else "N/A"
                ),
                "remarks": (
                    assessment.remarks if assessment and assessment.remarks else "N/A"
                ),
            }

            student_data["subjects"].append(subject_data)

            if assessment and assessment.total_score:
                total_score += assessment.total_score
                subjects_count += 1

        # Calculate average score
        student_data["average_score"] = (
            round(total_score / subjects_count, 2) if subjects_count > 0 else 0
        )

        report_data.append(student_data)

    # Sort by average score (descending) to determine class positions
    report_data.sort(key=lambda x: x["average_score"], reverse=True)

    # Add position to each student
    for position, student_data in enumerate(report_data, 1):
        student_data["position"] = position

    # Calculate class statistics
    class_statistics = {
        "total_students": len(report_data),
        "average_score": (
            round(sum(s["average_score"] for s in report_data) / len(report_data), 2)
            if report_data
            else 0
        ),
        "highest_average": max((s["average_score"] for s in report_data), default=0),
        "lowest_average": min((s["average_score"] for s in report_data), default=0),
    }

    # Determine format (HTML or CSV)
    export_format = request.GET.get("format", "html")

    if export_format == "csv":
        # Generate CSV
        csv_buffer = StringIO()
        csv_writer = csv.writer(csv_buffer)

        # Write header
        header = ["Position", "Admission Number", "Student Name", "Gender"]
        for cs in class_subjects:
            header.append(f"{cs.subject.subject_name} (Total)")
        header.append("Average Score")

        csv_writer.writerow(header)

        # Write data
        for student_data in report_data:
            row = [
                student_data["position"],
                student_data["admission_number"],
                student_data["full_name"],
                student_data["gender"],
            ]

            for subject in student_data["subjects"]:
                row.append(subject["total_score"])

            row.append(student_data["average_score"])
            csv_writer.writerow(row)

        # Return CSV response
        response = HttpResponse(csv_buffer.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="{class_obj.name}_Report_{datetime.datetime.now().strftime("%Y%m%d")}.csv"'
        )
        return response

    elif export_format == "pdf":
        # For PDF, we'll render to a template first
        context = {
            "class": class_obj,
            "academic_year": academic_year,
            "term": current_term,
            "report_data": report_data,
            "class_subjects": class_subjects,
            "class_statistics": class_statistics,
            "generation_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "school": school,  # Include the school in the context
        }

        # Render the HTML template for PDF conversion
        html_string = render_to_string("class/class_report_pdf.html", context)

        # For now, we'll just return the HTML as a response
        # In a real implementation, you'd use a library like WeasyPrint or xhtml2pdf
        # to convert this HTML to PDF
        return HttpResponse(html_string)

    else:  # HTML format
        context = {
            "class": class_obj,
            "academic_year": academic_year,
            "term": current_term,
            "report_data": report_data,
            "class_subjects": class_subjects,
            "class_statistics": class_statistics,
            "generation_date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "school": school,  # Include the school in the context
        }

        return render(request, "class/class_report.html", context)


@login_required
def get_terms_for_academic_year(request):
    """
    AJAX view to get terms for a specific academic year
    """
    academic_year_id = request.GET.get("academic_year_id")

    # Get the user's school
    school = get_user_school(request.user)

    if not academic_year_id:
        return JsonResponse({"terms": []})

    try:
        # Get all terms for the specified academic year
        terms_query = Term.objects.filter(academic_year_id=academic_year_id)

        # Filter by school if user is not a superadmin
        if school:
            terms_query = terms_query.filter(school=school)

        terms = terms_query.values("id", "term_number")

        # Format the terms for display
        formatted_terms = []
        for term in terms:
            # Get the display name for the term number using the choices dictionary
            term_choices = dict(Term.TERMS)
            term_name = term_choices.get(
                term["term_number"], f"Term {term['term_number']}"
            )

            formatted_terms.append({"id": term["id"], "name": term_name})

        return JsonResponse({"terms": formatted_terms})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@user_passes_test(lambda u: u.role == "admin")
def assign_class_subject(request, class_id):
    """Assign a subject or multiple subjects to a specific class for the entire academic year"""
    # Get the user's school
    school = get_user_school(request.user)

    # Get the class object, filtering by school if user is not a superadmin
    class_query = Class.objects
    if school:
        class_query = class_query.filter(school=school)
    class_obj = get_object_or_404(class_query, class_id=class_id)

    if request.method == "POST":
        # Check if this is a bulk assignment request
        is_bulk = "subject_ids" in request.POST

        if is_bulk:
            # Handle bulk assignment
            subject_ids_str = request.POST.get("subject_ids", "")
            if not subject_ids_str:
                return JsonResponse(
                    {
                        "success": False,
                        "message": "No subjects selected for assignment.",
                    }
                )

            # Split the comma-separated subject IDs
            subject_ids = [
                id.strip() for id in subject_ids_str.split(",") if id.strip()
            ]

            success_count = 0
            already_assigned = 0
            failed = 0

            for subject_id in subject_ids:
                try:
                    # Get subject, filtering by school if user is not a superadmin
                    subject_query = Subject.objects
                    if school:
                        subject_query = subject_query.filter(school=school)
                    subject = subject_query.get(id=subject_id)


                    # Check if assignment already exists (including inactive ones)

                    existing_assignment_query = ClassSubject.objects.filter(
                        class_name=class_obj,
                        subject=subject,
                        academic_year=class_obj.academic_year,
                    )

                    existing_assignment = existing_assignment_query.first()

                    if existing_assignment:

                        if existing_assignment.is_active:
                            # Already active - skip
                            already_assigned += 1
                            continue
                        else:
                            # Reactivate the existing assignment
                            existing_assignment.is_active = True
                            existing_assignment.assigned_by = request.user
                            existing_assignment.save()
                            success_count += 1
                            continue

                    # Create new class subject assignment

                    class_subject = ClassSubject.objects.create(
                        subject=subject,
                        class_name=class_obj,
                        academic_year=class_obj.academic_year,
                        school=school if school else None,

                        assigned_by=request.user,

                    )
                    success_count += 1

                except Subject.DoesNotExist:
                    failed += 1
                except Exception:
                    failed += 1

            # Prepare response message
            message_parts = []
            if success_count > 0:
                message_parts.append(
                    f"{success_count} subject(s) assigned successfully"
                )
            if already_assigned > 0:
                message_parts.append(
                    f"{already_assigned} subject(s) were already assigned"
                )
            if failed > 0:
                message_parts.append(f"{failed} subject(s) failed to assign")

            return JsonResponse(
                {
                    "success": success_count > 0,
                    "message": ". ".join(message_parts) + ".",
                    "assigned_count": success_count,
                    "already_assigned_count": already_assigned,
                    "failed_count": failed,
                }
            )
        else:
            # Handle single subject assignment (original functionality)
            subject_id = request.POST.get("subject_id")

            try:
                # Get subject, filtering by school if user is not a superadmin
                subject_query = Subject.objects
                if school:
                    subject_query = subject_query.filter(school=school)
                subject = subject_query.get(id=subject_id)

                # Check if assignment already exists for this subject in this academic year
                existing_assignment_query = ClassSubject.objects.filter(
                    class_name=class_obj,
                    subject=subject,
                    academic_year=class_obj.academic_year,
                )

                existing_assignment = existing_assignment_query.first()

                if existing_assignment:
                    return JsonResponse(
                        {
                            "success": False,
                            "message": f"This subject is already assigned to this class for the academic year {class_obj.academic_year.name}.",
                        }
                    )

                # Create the class subject assignment
                class_subject = ClassSubject.objects.create(
                    subject=subject,
                    class_name=class_obj,
                    academic_year=class_obj.academic_year,
                    school=school if school else None,
                )

                return JsonResponse(
                    {
                        "success": True,
                        "message": f"{subject.subject_name} has been assigned to {class_obj.name} successfully.",
                    }
                )

            except Subject.DoesNotExist:
                return JsonResponse({"success": False, "message": "Subject not found."})
            except Exception as e:
                return JsonResponse({"success": False, "message": str(e)})

    # GET requests are not handled - form is in the template
    return redirect("class_detail", class_id=class_id)


@login_required
@user_passes_test(lambda u: u.role == "admin")
def update_class_subject(request, class_subject_id):
    """Update an existing class subject assignment"""
    # Get the user's school
    school = get_user_school(request.user)

    # Get the class subject, filtering by school if needed
    class_subject_query = ClassSubject.objects
    if school:
        class_subject_query = class_subject_query.filter(class_name__school=school)
    class_subject = get_object_or_404(class_subject_query, id=class_subject_id)

    class_id = class_subject.class_name.class_id

    if request.method == "POST":
        teacher_id = request.POST.get("teacher_id")

        try:
            # Get teacher, filtering by school if needed
            teacher_query = Teacher.objects
            if school:
                teacher_query = teacher_query.filter(school=school)
            teacher = teacher_query.get(id=teacher_id)

            # Update the assignment (only the teacher can change)
            class_subject.teacher = teacher
            class_subject.save()

            return JsonResponse(
                {
                    "success": True,
                    "message": f"Subject teacher has been updated successfully.",
                }
            )

        except Teacher.DoesNotExist:
            return JsonResponse({"success": False, "message": "Teacher not found"})
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)})

    # GET requests are not handled - form is in the template
    return redirect("class_detail", class_id=class_id)


@login_required
@user_passes_test(lambda u: u.role == "admin")
def delete_class_subject(request, class_subject_id):

    """Deactivate a class subject assignment (soft delete)"""

    # Get the user's school
    school = get_user_school(request.user)

    # Get the class subject, filtering by school if needed

    class_subject_query = ClassSubject.objects.filter(is_active=True)

    if school:
        class_subject_query = class_subject_query.filter(class_name__school=school)
    class_subject = get_object_or_404(class_subject_query, id=class_subject_id)

    class_id = class_subject.class_name.class_id
    subject_name = class_subject.subject.subject_name

    if request.method == "POST":
        try:

            # Deactivate the assignment instead of deleting it
            class_subject.is_active = False
            class_subject.save()
            

            return JsonResponse(
                {
                    "success": True,
                    "message": f"{subject_name} has been removed from the class successfully.",
                }
            )
        except Exception as e:
            return JsonResponse(
                {"success": False, "message": f"Error removing subject: {str(e)}"}
            )

    # GET requests should be handled by a confirmation template
    return redirect("class_detail", class_id=class_id)


@login_required
def get_subjects(request):
    """Get all subjects for the bulk assign modal"""
    # Get the user's school
    school = get_user_school(request.user)

    try:

        # Get current academic year
        current_academic_year = AcademicYear.objects.filter(
            is_current=True, school=school
        ).first()
        if not current_academic_year:
            current_academic_year = AcademicYear.objects.filter(is_current=True).first()

        if not current_academic_year:
            return JsonResponse({"error": "No active academic year found"}, status=400)

        # Get subjects that have active ClassSubject assignments
        active_subject_ids = ClassSubject.objects.filter(
            academic_year=current_academic_year, is_active=True
        ).values_list('subject_id', flat=True).distinct()

        # Get subjects, filtering by school and active assignments
        subjects_query = Subject.objects.filter(id__in=active_subject_ids)

        if school:
            subjects_query = subjects_query.filter(school=school)

        subjects = subjects_query.values("id", "subject_name")

        # Convert to the format expected by frontend
        subjects_list = []
        for subject in subjects:
            subjects_list.append({
                "id": subject["id"],
                "name": subject["subject_name"]  # Map subject_name to name
            })
        return JsonResponse({"subjects": subjects_list})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
def get_teachers_available(request):
    """Get all available teachers for the bulk assign modal"""
    # Get the user's school
    school = get_user_school(request.user)

    try:
        # Get teachers, filtering by school if needed
        teachers_query = Teacher.objects.all()
        if school:
            teachers_query = teachers_query.filter(school=school)

        teachers = teachers_query.values("id", "full_name")
        # Convert to the format expected by frontend
        teachers_list = []
        for teacher in teachers:
            teachers_list.append({
                "id": teacher["id"],
                "name": teacher["full_name"]  # Map full_name to name
            })
        return JsonResponse({"teachers": teachers_list})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required

@user_passes_test(lambda u: u.role == "admin")
def bulk_assign_subjects(request):
    """API endpoint for bulk assigning subjects to multiple classes"""
    if request.method != "POST":
        return JsonResponse({"error": "Only POST method allowed"}, status=405)
    
    # Get the user's school
    school = get_user_school(request.user)
    
    try:
        # Get data from request
        class_ids = request.POST.getlist('class_ids[]') or request.POST.getlist('class_ids')
        subject_ids = request.POST.getlist('subject_ids[]') or request.POST.getlist('subject_ids')
        
        # Handle JSON data if sent
        if request.content_type == 'application/json':
            import json
            data = json.loads(request.body)
            class_ids = data.get('class_ids', [])
            subject_ids = data.get('subject_ids', [])
        
        if not class_ids or not subject_ids:
            return JsonResponse({
                "success": False,
                "message": "Class IDs and Subject IDs are required"
            }, status=400)
        
        # Get classes, filtering by school if needed
        classes_query = Class.objects.all()
        if school:
            classes_query = classes_query.filter(school=school)
        
        classes = classes_query.filter(class_id__in=class_ids)
        
        if len(classes) != len(class_ids):
            return JsonResponse({
                "success": False,
                "message": "Some classes not found or don't belong to your school"
            }, status=400)
        
        # Get subjects, filtering by school if needed
        subjects_query = Subject.objects.all()
        if school:
            subjects_query = subjects_query.filter(school=school)
        
        subjects = subjects_query.filter(id__in=subject_ids)
        
        if len(subjects) != len(subject_ids):
            return JsonResponse({
                "success": False,
                "message": "Some subjects not found or don't belong to your school"
            }, status=400)
        
        # Perform bulk assignment
        success_count = 0
        already_assigned = 0
        failed_count = 0
        errors = []
        
        for class_obj in classes:
            for subject in subjects:
                try:
                    # Check if assignment already exists (including inactive ones)
                    existing_assignment = ClassSubject.objects.filter(
                        class_name=class_obj,
                        subject=subject,
                        academic_year=class_obj.academic_year,
                    ).first()
                    
                    if existing_assignment:
                        if existing_assignment.is_active:
                            # Already active - skip
                            already_assigned += 1
                            continue
                        else:
                            # Reactivate the existing assignment
                            existing_assignment.is_active = True
                            existing_assignment.assigned_by = request.user
                            existing_assignment.save()
                            success_count += 1
                            continue
                    
                    # Create new assignment
                    ClassSubject.objects.create(
                        subject=subject,
                        class_name=class_obj,
                        academic_year=class_obj.academic_year,
                        school=school if school else None,
                        assigned_by=request.user,
                    )
                    success_count += 1
                    
                except Exception as e:
                    failed_count += 1
                    errors.append(f"Failed to assign {subject.subject_name} to {class_obj.name}: {str(e)}")
        
        # Prepare response message
        message_parts = []
        if success_count > 0:
            message_parts.append(f"Successfully assigned {success_count} subject(s)")
        if already_assigned > 0:
            message_parts.append(f"{already_assigned} assignment(s) already existed")
        if failed_count > 0:
            message_parts.append(f"{failed_count} assignment(s) failed")
        
        return JsonResponse({
            "success": success_count > 0,
            "message": ". ".join(message_parts) + ".",
            "assigned_count": success_count,
            "already_assigned_count": already_assigned,
            "failed_count": failed_count,
            "errors": errors[:5]  # Limit errors to first 5
        })
        
    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": f"Error processing bulk assignment: {str(e)}"
        }, status=500)


# Set up logger
logger = logging.getLogger(__name__)

@login_required
@user_passes_test(lambda u: u.role == "admin")
def test_class_teacher_api(request, class_id):
    """
    Simple test endpoint to verify the API is working
    """
    return JsonResponse({
        "success": True,
        "message": f"Test endpoint working for class_id: {class_id}",
        "class_id": class_id,
        "user": str(request.user),
        "method": request.method
    })


@login_required
@user_passes_test(lambda u: u.role == "admin")
def assign_class_teacher_api(request, class_id):
    """
    API endpoint for assigning a teacher as class teacher to a specific class.
    Uses the same transaction safety and smart assignment logic as the teacher management view.
    """
    logger.info(f"assign_class_teacher_api called with class_id: {class_id}")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request POST data: {request.POST}")
    logger.info(f"User: {request.user}")
    
    if request.method != "POST":
        return JsonResponse({"error": "Only POST method allowed"}, status=405)
    
    # Get the user's school
    school = get_user_school(request.user)
    logger.info(f"User school: {school}")
    
    try:
        # Get the class object, filtering by school if user is not a superadmin
        logger.info(f"Looking for class with class_id: {class_id}")
        class_query = Class.objects
        if school:
            class_query = class_query.filter(school=school)
        
        try:
            class_obj = class_query.get(class_id=class_id)
            logger.info(f"Found class: {class_obj.name}")
        except Class.DoesNotExist:
            logger.error(f"Class with class_id {class_id} not found")
            return JsonResponse({
                "success": False,
                "message": f"Class with ID {class_id} not found."
            }, status=404)
        
        teacher_id = request.POST.get("teacher_id")
        logger.info(f"Teacher ID from request: {teacher_id}")
        
        if not teacher_id:
            logger.error("No teacher_id provided in request")
            return JsonResponse({
                "success": False,
                "message": "Teacher ID is required."
            }, status=400)
        
        # Ensure teacher belongs to user's school
        logger.info(f"Looking for teacher with id: {teacher_id}")
        teacher_query = Teacher.objects
        if school:
            teacher_query = teacher_query.filter(school=school)
        
        try:
            teacher = teacher_query.get(id=teacher_id)
            logger.info(f"Found teacher: {teacher.full_name}")
        except Teacher.DoesNotExist:
            logger.error(f"Teacher with id {teacher_id} not found")
            return JsonResponse({
                "success": False,
                "message": f"Teacher with ID {teacher_id} not found."
            }, status=404)
        
        # Get current academic year for the school
        logger.info(f"Looking for current academic year for school: {school}")
        current_academic_year = AcademicYear.objects.filter(
            school=school, is_current=True
        ).first()
        if not current_academic_year:
            logger.info("No current academic year found for school, looking globally")
            current_academic_year = AcademicYear.objects.filter(
                is_current=True
            ).first()
        
        if not current_academic_year:
            logger.error("No active academic year found")
            return JsonResponse({
                "success": False,
                "message": "No active academic year found."
            }, status=400)
        
        logger.info(f"Using academic year: {current_academic_year.name}")
        
        # Use transaction for data consistency
        logger.info("Starting transaction for class teacher assignment")
        with transaction.atomic():
            # Check for existing active class teacher, filtered by school
            logger.info("Checking for existing active class teacher assignment")
            existing_class_teacher = ClassTeacher.objects.filter(
                class_assigned=class_obj,
                academic_year=current_academic_year,
                is_active=True,
                school=school,
            ).first()
            
            # Check for deactivated class teacher assignment, filtered by school
            logger.info("Checking for deactivated class teacher assignment")
            deactivated_assignment = ClassTeacher.objects.filter(
                class_assigned=class_obj,
                academic_year=current_academic_year,
                is_active=False,
                school=school,
            ).first()
            
            if existing_class_teacher:
                logger.info(f"Found existing active assignment: {existing_class_teacher.teacher.full_name}")
                # If the class already has this teacher, do nothing
                if existing_class_teacher.teacher == teacher:
                    logger.info("Same teacher already assigned, returning success")
                    return JsonResponse({
                        "success": True,
                        "message": f"{teacher.full_name} is already the class teacher for {class_obj.name}.",
                    })
                
                # Update the class teacher assignment
                logger.info("Updating existing class teacher assignment")
                previous_teacher = existing_class_teacher.teacher.full_name
                existing_class_teacher.teacher = teacher
                existing_class_teacher.assigned_by = request.user
                existing_class_teacher.save()
                
                logger.info(f"Successfully updated class teacher from {previous_teacher} to {teacher.full_name}")
                return JsonResponse({
                    "success": True,
                    "message": f"Successfully changed class teacher for {class_obj.name} from {previous_teacher} to {teacher.full_name}.",
                })
            elif deactivated_assignment:
                logger.info(f"Found deactivated assignment: {deactivated_assignment.teacher.full_name}")
                # Reactivate the deactivated assignment and update teacher
                previous_teacher = (
                    deactivated_assignment.teacher.full_name
                    if deactivated_assignment.teacher != teacher
                    else None
                )
                deactivated_assignment.teacher = teacher
                deactivated_assignment.is_active = True
                deactivated_assignment.assigned_by = request.user
                deactivated_assignment.save()
                
                logger.info(f"Successfully reactivated assignment for {teacher.full_name}")
                if previous_teacher:
                    message = f"Successfully reassigned class teacher for {class_obj.name} from {previous_teacher} to {teacher.full_name}."
                else:
                    message = f"Successfully reactivated class teacher assignment for {class_obj.name} to {teacher.full_name}."
                
                return JsonResponse({"success": True, "message": message})
            else:
                logger.info("No existing assignment found, creating new one")
                # Create new class teacher assignment with school
                class_teacher = ClassTeacher.objects.create(
                    teacher=teacher,
                    class_assigned=class_obj,
                    academic_year=current_academic_year,
                    assigned_by=request.user,
                    school=school,  # Set the school for multi-tenancy
                )
                
                logger.info(f"Successfully created new assignment for {teacher.full_name}")
                return JsonResponse({
                    "success": True,
                    "message": f"Successfully assigned {teacher.full_name} as class teacher for {class_obj.name}.",
                })
                
    except Exception as e:
        logger.error(f"Error assigning class teacher: {str(e)}", exc_info=True)
        return JsonResponse({
            "success": False,
            "message": str(e)
        }, status=500)


@login_required
@user_passes_test(lambda u: u.role == "admin")
def bulk_assign_class_teacher(request):
    """API endpoint for bulk assigning a teacher to multiple classes using transaction safety"""
    if request.method != "POST":
        return JsonResponse({"error": "Only POST method allowed"}, status=405)
    
    # Get the user's school
    school = get_user_school(request.user)
    
    try:
        # Get data from request
        class_ids = request.POST.getlist('class_ids[]') or request.POST.getlist('class_ids')
        teacher_id = request.POST.get('teacher_id')
        
        # Handle JSON data if sent
        if request.content_type == 'application/json':
            import json
            data = json.loads(request.body)
            class_ids = data.get('class_ids', [])
            teacher_id = data.get('teacher_id')
        
        if not class_ids or not teacher_id:
            return JsonResponse({
                "success": False,
                "message": "Class IDs and Teacher ID are required"
            }, status=400)
        
        # Get classes, filtering by school if needed
        classes_query = Class.objects.all()
        if school:
            classes_query = classes_query.filter(school=school)
        
        classes = classes_query.filter(class_id__in=class_ids)
        
        if len(classes) != len(class_ids):
            return JsonResponse({
                "success": False,
                "message": "Some classes not found or don't belong to your school"
            }, status=400)
        
        # Get teacher, filtering by school if needed
        teacher_query = Teacher.objects.all()
        if school:
            teacher_query = teacher_query.filter(school=school)
        
        try:
            teacher = teacher_query.get(id=teacher_id)
        except Teacher.DoesNotExist:
            return JsonResponse({
                "success": False,
                "message": "Teacher not found or doesn't belong to your school"
            }, status=400)
        
        # Get current academic year for the school
        current_academic_year = AcademicYear.objects.filter(
            school=school, is_current=True
        ).first()
        if not current_academic_year:
            current_academic_year = AcademicYear.objects.filter(
                is_current=True
            ).first()
        
        if not current_academic_year:
            return JsonResponse({
                "success": False,
                "message": "No active academic year found."
            }, status=400)
        
        # Perform bulk assignment with transaction safety
        success_count = 0
        failed_count = 0
        already_assigned_count = 0
        errors = []
        
        with transaction.atomic():
            for class_obj in classes:
                try:
                    # Check for existing active class teacher
                    existing_class_teacher = ClassTeacher.objects.filter(
                        class_assigned=class_obj,
                        academic_year=current_academic_year,
                        is_active=True,
                        school=school,
                    ).first()
                    
                    # Check for deactivated class teacher assignment
                    deactivated_assignment = ClassTeacher.objects.filter(
                        class_assigned=class_obj,
                        academic_year=current_academic_year,
                        is_active=False,
                        school=school,
                    ).first()
                    
                    if existing_class_teacher:
                        # If the class already has this teacher, skip
                        if existing_class_teacher.teacher == teacher:
                            already_assigned_count += 1
                            continue
                        
                        # Update the class teacher assignment
                        existing_class_teacher.teacher = teacher
                        existing_class_teacher.assigned_by = request.user
                        existing_class_teacher.save()
                        success_count += 1
                        
                    elif deactivated_assignment:
                        # Reactivate the deactivated assignment and update teacher
                        deactivated_assignment.teacher = teacher
                        deactivated_assignment.is_active = True
                        deactivated_assignment.assigned_by = request.user
                        deactivated_assignment.save()
                        success_count += 1
                        
                    else:
                        # Create new class teacher assignment
                        ClassTeacher.objects.create(
                            teacher=teacher,
                            class_assigned=class_obj,
                            academic_year=current_academic_year,
                            assigned_by=request.user,
                            school=school,
                        )
                        success_count += 1
                        
                except Exception as e:
                    failed_count += 1
                    errors.append(f"Failed to assign teacher to {class_obj.name}: {str(e)}")
        
        # Prepare response message
        message_parts = []
        if success_count > 0:
            message_parts.append(f"Successfully assigned {teacher.full_name} to {success_count} class(es)")
        if already_assigned_count > 0:
            message_parts.append(f"{already_assigned_count} class(es) already had this teacher assigned")
        if failed_count > 0:
            message_parts.append(f"{failed_count} assignment(s) failed")
        
        return JsonResponse({
            "success": success_count > 0,
            "message": ". ".join(message_parts) + ".",
            "assigned_count": success_count,
            "already_assigned_count": already_assigned_count,
            "failed_count": failed_count,
            "errors": errors[:5]  # Limit errors to first 5
        })
        
    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": f"Error processing bulk teacher assignment: {str(e)}"
        }, status=500)


@login_required

def print_class_list(request, class_id):
    """Generate a printable list of students in a class"""
    # Get the user's school
    school = get_user_school(request.user)

    # Get the class object, filtering by school if needed
    class_query = Class.objects
    if school:
        class_query = class_query.filter(school=school)
    class_obj = get_object_or_404(class_query, class_id=class_id)

    # Get all students in this class
    students_query = class_obj.studentclass_set.filter(is_active=True)

    # Filter by school if needed
    if school:
        students_query = students_query.filter(school=school)

    students = students_query.select_related("student").order_by("student__full_name")

    context = {
        "class": class_obj,
        "students": students,
        "student_count": students.count(),
        "title": f"Class List: {class_obj.name}",
        "academic_year": class_obj.academic_year,
        "print_date": datetime.datetime.now(),
        "school": school,  # Include school in context
    }

    return render(request, "class/class_print_list.html", context)



@login_required
@user_passes_test(lambda u: u.role == "admin")
def class_teacher_list(request):
    """
    View to display all class teacher assignments with management capabilities.
    Shows statistics, filters, and allows bulk operations.
    """
    # Get the user's school
    school = get_user_school(request.user)
    
    # Get current academic year
    current_academic_year = SchoolInformation.get_current_academic_year(school=school)
    current_term = SchoolInformation.get_current_term(school=school)
    
    if not current_academic_year:
        messages.warning(request, "No active academic year found. Please set up an academic year first.")
        return redirect("academic_year_list")
    
    # Get all classes for the current academic year
    classes_query = Class.objects.filter(academic_year=current_academic_year).select_related(
        'form', 'learning_area', 'academic_year'
    )
    
    # Filter by school if needed
    if school:
        classes_query = classes_query.filter(school=school)
    
    classes = classes_query.order_by('form__form_number', 'name')
    
    # Get class teacher assignments
    class_teacher_assignments = ClassTeacher.objects.filter(
        class_assigned__in=classes,
        academic_year=current_academic_year,
        is_active=True
    ).select_related('teacher', 'class_assigned')
    
    # Filter by school if needed
    if school:
        class_teacher_assignments = class_teacher_assignments.filter(school=school)
    
    # Create a mapping of class to teacher
    class_teacher_map = {}
    for assignment in class_teacher_assignments:
        class_teacher_map[assignment.class_assigned.id] = {
            'teacher': assignment.teacher,
            'assignment_date': assignment.date_assigned
        }
    
    # Enhance classes with teacher information
    for class_obj in classes:
        if class_obj.id in class_teacher_map:
            assignment_info = class_teacher_map[class_obj.id]
            class_obj.class_teacher = assignment_info['teacher']
            class_obj.class_teacher_name = assignment_info['teacher'].full_name
            class_obj.class_teacher_assignment_date = assignment_info['assignment_date']
        else:
            class_obj.class_teacher = None
            class_obj.class_teacher_name = None
            class_obj.class_teacher_assignment_date = None
        
        # Get student count
        student_count_query = class_obj.studentclass_set.filter(is_active=True)
        if school:
            student_count_query = student_count_query.filter(school=school)
        class_obj.student_count = student_count_query.count()
        
        # Get subject count
        subject_count_query = class_obj.classsubject_set.filter(academic_year=current_academic_year)
        if school:
            subject_count_query = subject_count_query.filter(school=school)
        class_obj.subject_count = subject_count_query.count()
    
    # Get statistics
    total_classes = classes.count()
    assigned_classes = len([c for c in classes if c.class_teacher])
    unassigned_classes = total_classes - assigned_classes
    
    # Get available teachers
    teachers_query = Teacher.objects.all()
    if school:
        teachers_query = teachers_query.filter(school=school)
    
    teachers = teachers_query.select_related('department').order_by('full_name')
    
    # Add current class count for each teacher
    for teacher in teachers:
        teacher_class_count_query = ClassTeacher.objects.filter(
            teacher=teacher,
            academic_year=current_academic_year,
            is_active=True
        )
        if school:
            teacher_class_count_query = teacher_class_count_query.filter(school=school)
        teacher.current_class_count = teacher_class_count_query.count()
    
    # Get forms and learning areas for filters
    forms_query = Form.objects.all()
    learning_areas_query = LearningArea.objects.all()
    
    if school:
        forms_query = forms_query.filter(school=school)
        learning_areas_query = learning_areas_query.filter(school=school)
    
    forms = forms_query.order_by('form_number')
    learning_areas = learning_areas_query.order_by('name')
    
    context = {
        'title': 'Class Teachers',
        'classes': classes,
        'teachers': teachers,
        'forms': forms,
        'learning_areas': learning_areas,
        'current_academic_year': current_academic_year,
        'current_term': current_term,
        'total_classes': total_classes,
        'assigned_classes': assigned_classes,
        'unassigned_classes': unassigned_classes,
        'total_teachers': teachers.count(),
        'school': school,
    }
    
    return render(request, 'class/class_teacher_list.html', context)


@login_required
@user_passes_test(lambda u: u.role == "admin")
def remove_class_teacher_api(request, class_id):
    """
    API endpoint for removing a class teacher assignment.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Only POST method allowed"}, status=405)
    
    # Get the user's school
    school = get_user_school(request.user)
    
    try:
        # Get the class object
        class_query = Class.objects
        if school:
            class_query = class_query.filter(school=school)
        
        class_obj = class_query.get(class_id=class_id)
        
        # Get current academic year
        current_academic_year = SchoolInformation.get_current_academic_year(school=school)
        if not current_academic_year:
            return JsonResponse({
                "success": False,
                "message": "No active academic year found."
            }, status=400)
        
        # Find active class teacher assignment
        class_teacher_query = ClassTeacher.objects.filter(
            class_assigned=class_obj,
            academic_year=current_academic_year,
            is_active=True
        )
        
        if school:
            class_teacher_query = class_teacher_query.filter(school=school)
        
        class_teacher = class_teacher_query.first()
        
        if not class_teacher:
            return JsonResponse({
                "success": False,
                "message": f"No active class teacher found for {class_obj.name}."
            }, status=404)
        
        # Deactivate the assignment
        with transaction.atomic():
            class_teacher.is_active = False
            class_teacher.save()
            
            logger.info(f"Admin {request.user.username} removed {class_teacher.teacher.full_name} as class teacher for {class_obj.name}")
        
        return JsonResponse({
            "success": True,
            "message": f"Successfully removed {class_teacher.teacher.full_name} as class teacher for {class_obj.name}."
        })
        
    except Class.DoesNotExist:
        return JsonResponse({
            "success": False,
            "message": f"Class with ID {class_id} not found."
        }, status=404)
    except Exception as e:
        logger.error(f"Error removing class teacher: {str(e)}", exc_info=True)
        return JsonResponse({
            "success": False,
            "message": f"Error removing class teacher: {str(e)}"
        }, status=500)

