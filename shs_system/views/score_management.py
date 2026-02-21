from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView, DetailView
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.urls import reverse, reverse_lazy
from django.db.models import (
    Q,
    Avg,
    Max,
    Min,
    Count,
    F,
    Sum,
    Case,
    When,
    Value,
    IntegerField,
    FloatField,
)
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string

import json
import csv
import pandas as pd
import numpy as np
import io
import base64
from datetime import datetime
from collections import defaultdict


# For PDF exports - use safe utility function

from django.template.loader import get_template
from django.conf import settings

# Excel exports
import xlsxwriter

from shs_system.models import (
    User,
    Student,
    Teacher,
    Class,
    Subject,
    ClassSubject,
    Assessment,
    Term,
    AcademicYear,
    SchoolInformation,
    StudentClass,
    ClassTeacher,
    TeacherSubjectAssignment,
    GradingSystem,
    Form,
    ScoringConfiguration,
)
from shs_system.utils import filter_by_school

from shs_system.utils.pdf_generator import generate_pdf_from_html



class ScoreManagementAccessMixin(UserPassesTestMixin):
    """Mixin to handle access control for score management views."""

    def test_func(self):
        # Admin users have access to their school's data
        if self.request.user.role == "admin" and self.request.user.school:
            return True

        # Super admins have access to all schools' data
        if self.request.user.is_superadmin:
            return True

        # For teachers, we need to check their specific permissions
        if self.request.user.role == "teacher":
            teacher = self.request.user.teacher_profile
            # Teachers can only view scores for classes and subjects they teach in their school
            if teacher and teacher.school == self.request.user.school:
                # The specific class and subject check will be done in the view
                return True

        # Default deny
        return False

    def handle_no_permission(self):
        messages.error(self.request, "You don't have permission to access this page.")
        return redirect("dashboard")

    def get_school_filter(self):
        """Get the appropriate school filter based on user role."""
        user = self.request.user

        # Super admins can see all schools' data but can filter by a specific school if needed
        if user.is_superadmin:
            # If a school_id is in the request parameters, filter by that school
            school_id = self.request.GET.get("school_id")
            if school_id:
                return Q(school_id=school_id)
            # Otherwise, no filter (see all schools)
            return Q()

        # Regular admins and teachers can only see their school's data
        return Q(school=user.school)


class ScoreDashboardView(LoginRequiredMixin, ScoreManagementAccessMixin, View):
    """Main dashboard for score management system."""

    def get(self, request):
        # Get the user's school or the selected school for superadmins
        school_filter = self.get_school_filter()

        # For superadmins, get all schools for the school selector dropdown
        all_schools = None
        if request.user.is_superadmin:
            all_schools = SchoolInformation.objects.filter(is_active=True)

        # Get the current school context
        school_id = request.GET.get("school_id")
        if request.user.is_superadmin and school_id:
            school_info = SchoolInformation.objects.get(id=school_id)
        else:
            school_info = request.user.school or SchoolInformation.get_active()

        current_academic_year = school_info.current_academic_year
        current_term = school_info.current_term

        # Get classes based on user role with school filtering
        if request.user.role == "admin" or request.user.is_superadmin:
            classes = Class.objects.filter(
                school_filter, academic_year=current_academic_year
            )
        elif request.user.role == "teacher" and request.user.teacher_profile:
            # Get classes this teacher teaches in their school

            teacher_assignments_query = TeacherSubjectAssignment.objects.filter(

                school_filter,
                teacher=request.user.teacher_profile,
                academic_year=current_academic_year,
                is_active=True,
            )

            
            # Filter out assignments where ClassSubject is not active
            # Get active class-subject combinations
            active_class_subjects = ClassSubject.objects.filter(
                academic_year=current_academic_year, is_active=True
            ).values_list('class_name_id', 'subject_id')
            
            # Filter assignments to only include those with active ClassSubject
            filtered_assignments = []
            for assignment in teacher_assignments_query:
                if (assignment.class_assigned.id, assignment.subject.id) in active_class_subjects:
                    filtered_assignments.append(assignment)
            
            teacher_assignments = filtered_assignments
            class_ids = [assignment.class_assigned.id for assignment in teacher_assignments]

            classes = Class.objects.filter(id__in=class_ids)
        else:
            classes = Class.objects.none()

        # Get subjects for the current school
        subjects = Subject.objects.filter(school_filter)

        # Get academic years and terms for the current school
        academic_years = AcademicYear.objects.filter(school_filter).order_by(
            "-start_date"
        )
        terms = Term.objects.filter(
            school_filter, academic_year=current_academic_year
        ).order_by("term_number")

        # Get basic statistics with school filtering
        total_students = StudentClass.objects.filter(
            school_filter,
            is_active=True,
            assigned_class__academic_year=current_academic_year,
        ).count()


        # Exclude mock exam assessments from total count
        total_assessments = Assessment.objects.filter(
            school_filter,
            class_subject__academic_year=current_academic_year,
            class_subject__is_active=True,
            term=current_term,
        ).exclude(assessment_type='mock_exam').count()

        # Performance overview (average scores by subject) with school filtering
        # Exclude mock exam assessments from subject averages

        subject_averages = (
            Assessment.objects.filter(
                school_filter,
                class_subject__academic_year=current_academic_year,

                class_subject__is_active=True,
                term=current_term,
                total_score__isnull=False,
            ).exclude(assessment_type='mock_exam')

            .values("class_subject__subject__subject_name")
            .annotate(average_score=Avg("total_score"))
            .order_by("-average_score")[:5]
        )  # Top 5 subjects

        # Generate performance graph data with school filtering
        graph_data = self._generate_performance_graph_data(
            current_academic_year, current_term, school_filter
        )

        context = {
            "classes": classes,
            "subjects": subjects,
            "academic_years": academic_years,
            "terms": terms,
            "current_academic_year": current_academic_year,
            "current_term": current_term,
            "total_students": total_students,
            "total_assessments": total_assessments,
            "subject_averages": subject_averages,
            "performance_graph": graph_data,
            "school_info": school_info,
            "all_schools": all_schools,
            "selected_school_id": school_id if request.user.is_superadmin else None,
        }

        return render(request, "scores/dashboard.html", context)

    def _generate_performance_graph_data(self, academic_year, term, school_filter):
        """Generate data for performance graphs with school filtering"""

        # Average scores by class with school filtering

        # Exclude mock exam assessments from class averages
        class_averages = Assessment.objects.filter(
            school_filter,
            class_subject__academic_year=academic_year,
            class_subject__is_active=True,
            term=term,
            total_score__isnull=False,
        ).exclude(assessment_type='mock_exam')


        if term:
            # If we have term data, filter by the term's academic year
            class_averages = class_averages.filter(
                class_subject__academic_year=term.academic_year
            )

        class_averages = (
            class_averages.values("class_subject__class_name__name")
            .annotate(average_score=Avg("total_score"))
            .order_by("class_subject__class_name__name")
        )

        # Convert to format suitable for Chart.js
        labels = [item["class_subject__class_name__name"] for item in class_averages]
        data = [round(float(item["average_score"]), 2) for item in class_averages]

        # Generate performance distribution (score ranges) with school filtering
        score_ranges = [
            {"min": 0, "max": 40, "label": "0-40"},
            {"min": 40, "max": 55, "label": "40-55"},
            {"min": 55, "max": 70, "label": "55-70"},
            {"min": 70, "max": 85, "label": "70-85"},
            {"min": 85, "max": 101, "label": "85-100"},
        ]

        distribution_data = []
        distribution_labels = []

        for score_range in score_ranges:

            # Exclude mock exam assessments from score distribution
            query = Assessment.objects.filter(
                school_filter,
                class_subject__academic_year=academic_year,
                class_subject__is_active=True,
                term=term,
                total_score__gte=score_range["min"],
                total_score__lt=score_range["max"],
            ).exclude(assessment_type='mock_exam')


            if term:
                # Apply the same term filtering here
                query = query.filter(class_subject__academic_year=term.academic_year)

            count = query.count()

            distribution_data.append(count)
            distribution_labels.append(score_range["label"])

        return {
            "class_performance": {
                "labels": labels,
                "data": data,
            },
            "score_distribution": {
                "labels": distribution_labels,
                "data": distribution_data,
            },
        }


class ClassScoreListView(LoginRequiredMixin, ScoreManagementAccessMixin, View):
    """View for listing scores for a specific class."""

    def get(self, request):
        # Get filter parameters
        class_id = request.GET.get("class_id")
        subject_id = request.GET.get("subject_id")
        term_id = request.GET.get("term_id")
        academic_year_id = request.GET.get("academic_year_id")
        search_query = request.GET.get("search", "")
        sort_by = request.GET.get("sort_by", "name")  # Default sort by name

        # Get school filter
        school_filter = self.get_school_filter()

        # Get current school context
        school_id = request.GET.get("school_id")
        if request.user.is_superadmin and school_id:
            school_info = SchoolInformation.objects.get(id=school_id)
        else:
            school_info = request.user.school or SchoolInformation.get_active()

        current_academic_year = school_info.current_academic_year
        current_term = school_info.current_term

        # For superadmins, get all schools for the school selector dropdown
        all_schools = None
        if request.user.is_superadmin:
            all_schools = SchoolInformation.objects.filter(is_active=True)

        # Use provided filters or defaults
        selected_academic_year = (
            AcademicYear.objects.filter(school_filter, id=academic_year_id).first()
            or current_academic_year
        )

        # Handle empty term_id properly
        if term_id and term_id.strip():  # Only filter if term_id is not empty
            selected_term = (
                Term.objects.filter(school_filter, id=term_id).first() or current_term
            )
        else:
            selected_term = current_term

        # Get classes and subjects for filter dropdowns with school filtering
        if request.user.role == "admin" or request.user.is_superadmin:
            available_classes = Class.objects.filter(
                school_filter, academic_year=selected_academic_year
            )
        elif request.user.role == "teacher" and request.user.teacher_profile:
            # Get classes this teacher teaches in their school
            teacher_assignments = TeacherSubjectAssignment.objects.filter(
                school_filter,
                teacher=request.user.teacher_profile,
                academic_year=selected_academic_year,
                is_active=True,
            )
            class_ids = teacher_assignments.values_list(
                "class_assigned_id", flat=True
            ).distinct()
            available_classes = Class.objects.filter(school_filter, id__in=class_ids)
        else:
            available_classes = Class.objects.none()

        # Selected class
        selected_class = None
        if class_id:
            selected_class = get_object_or_404(Class, school_filter, id=class_id)

            # Check if teacher has access to this class
            if request.user.role == "teacher":
                teacher = request.user.teacher_profile
                if not TeacherSubjectAssignment.objects.filter(
                    school_filter,
                    teacher=teacher,
                    class_assigned=selected_class,
                    is_active=True,
                ).exists():
                    messages.error(
                        request,
                        "You don't have permission to view scores for this class.",
                    )
                    return redirect("score_management_dashboard")
        elif available_classes.exists():
            selected_class = available_classes.first()

        # Available subjects for the selected class with school filtering
        available_subjects = []
        if selected_class:
            if request.user.role == "admin" or request.user.is_superadmin:
                # Use filter_by_school helper for ClassSubject filtering
                school = (
                    school_info
                    if not request.user.is_superadmin
                    else (
                        SchoolInformation.objects.get(id=school_id)
                        if school_id
                        else None
                    )
                )

                class_subjects_query = ClassSubject.objects.filter(
                    class_name=selected_class,
                    academic_year=selected_academic_year,

                    is_active=True

                )
                class_subjects = filter_by_school(
                    class_subjects_query, "ClassSubject", school
                )

                subject_ids = class_subjects.values_list(
                    "subject", flat=True
                ).distinct()
                available_subjects = Subject.objects.filter(
                    school_filter, id__in=subject_ids
                )
            elif request.user.role == "teacher":
                teacher = request.user.teacher_profile
                teacher_subjects = TeacherSubjectAssignment.objects.filter(
                    school_filter,
                    teacher=teacher,
                    class_assigned=selected_class,
                    academic_year=selected_academic_year,
                    is_active=True,
                ).values_list("subject", flat=True)
                available_subjects = Subject.objects.filter(
                    school_filter, id__in=teacher_subjects
                )

        # Selected subject
        selected_subject = None
        if subject_id and available_subjects:
            selected_subject = get_object_or_404(Subject, school_filter, id=subject_id)

            # For teachers, verify they teach this subject
            if request.user.role == "teacher":
                teacher = request.user.teacher_profile
                if not TeacherSubjectAssignment.objects.filter(
                    school_filter,
                    teacher=teacher,
                    class_assigned=selected_class,
                    subject=selected_subject,
                    is_active=True,
                ).exists():
                    messages.error(
                        request,
                        "You don't have permission to view scores for this subject.",
                    )
                    return redirect("class_score_list")
        elif available_subjects.exists():
            selected_subject = available_subjects.first()

        # Get students and their scores with school filtering
        students = []
        if selected_class and selected_subject:
            # Get class subject using the helper function
            school = (
                school_info
                if not request.user.is_superadmin
                else (
                    SchoolInformation.objects.get(id=school_id) if school_id else None
                )
            )

            try:
                # Use direct school field if available
                class_subject_query = ClassSubject.objects.filter(
                    class_name=selected_class,
                    subject=selected_subject,
                    academic_year=selected_academic_year,

                    is_active=True

                )
                class_subject = filter_by_school(
                    class_subject_query, "ClassSubject", school
                ).first()

                if not class_subject:
                    raise ClassSubject.DoesNotExist

                # Get students in this class with school filtering
                student_classes = StudentClass.objects.filter(
                    school_filter, assigned_class=selected_class, is_active=True
                )

                # Apply search filter if provided
                if search_query:
                    student_classes = student_classes.filter(
                        Q(student__full_name__icontains=search_query)
                        | Q(student__admission_number__icontains=search_query)
                    )

                # Get assessment data for these students with school filtering
                for student_class in student_classes:
                    student = student_class.student

                    # Get assessment for this student, subject, and term

                    # Exclude mock exam assessments

                    assessment = Assessment.objects.filter(
                        school_filter,
                        class_subject=class_subject,
                        student=student,
                        term=selected_term,

                    ).exclude(assessment_type='mock_exam').first()


                    students.append(
                        {
                            "student": student,
                            "assessment": assessment,
                        }
                    )

                # Apply sorting
                if sort_by == "score_asc":
                    students.sort(
                        key=lambda x: (
                            x["assessment"].total_score
                            if x["assessment"] and x["assessment"].total_score
                            else 0
                        )
                    )
                elif sort_by == "score_desc":
                    students.sort(
                        key=lambda x: (
                            x["assessment"].total_score
                            if x["assessment"] and x["assessment"].total_score
                            else 0
                        ),
                        reverse=True,
                    )
                elif sort_by == "name":
                    students.sort(key=lambda x: x["student"].full_name)
                elif sort_by == "id":
                    students.sort(key=lambda x: x["student"].admission_number)

            except ClassSubject.DoesNotExist:
                messages.warning(
                    request,
                    f"No subject assignment found for {selected_subject} in {selected_class}.",
                )

        # Paginate students
        paginator = Paginator(students, 20)  # Show 20 students per page
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        # Academic years and terms for filter dropdowns with school filtering
        academic_years = AcademicYear.objects.filter(school_filter).order_by(
            "-start_date"
        )
        terms = Term.objects.filter(
            school_filter, academic_year=selected_academic_year
        ).order_by("term_number")

        # Get scoring configuration
        scoring_config = None
        if school_info:
            scoring_config = ScoringConfiguration.get_active_config(school_info)

        context = {
            "page_obj": page_obj,
            "available_classes": available_classes,
            "available_subjects": available_subjects,
            "selected_class": selected_class,
            "selected_subject": selected_subject,
            "selected_term": selected_term,
            "selected_academic_year": selected_academic_year,
            "academic_years": academic_years,
            "terms": terms,
            "search_query": search_query,
            "sort_by": sort_by,
            "school_info": school_info,
            "all_schools": all_schools,
            "selected_school_id": school_id if request.user.is_superadmin else None,
            "scoring_config": scoring_config,
        }

        return render(request, "scores/class_score_list.html", context)


class StudentScoreDetailView(LoginRequiredMixin, ScoreManagementAccessMixin, View):
    """View for detailed scores of a specific student."""

    def get(self, request, student_id):
        # Get school filter
        school_filter = self.get_school_filter()

        # Get current school context
        school_id = request.GET.get("school_id")
        if request.user.is_superadmin and school_id:
            school_info = SchoolInformation.objects.get(id=school_id)
        else:
            school_info = request.user.school or SchoolInformation.get_active()

        # For superadmins, get all schools for the school selector dropdown
        all_schools = None
        if request.user.is_superadmin:
            all_schools = SchoolInformation.objects.filter(is_active=True)

        student = get_object_or_404(Student, school_filter, id=student_id)
        academic_year_id = request.GET.get("academic_year_id")

        # Get current settings if not specified
        selected_academic_year = (
            AcademicYear.objects.filter(school_filter, id=academic_year_id).first()
            or school_info.current_academic_year
        )

        # Check permissions for teachers
        if request.user.role == "teacher":
            teacher = request.user.teacher_profile

            # Get the student's current class
            student_class = StudentClass.objects.filter(
                school_filter, student=student, is_active=True
            ).first()

            if student_class:
                # Check if teacher teaches this student
                if not TeacherSubjectAssignment.objects.filter(
                    school_filter,
                    teacher=teacher,
                    class_assigned=student_class.assigned_class,
                    is_active=True,
                ).exists():
                    messages.error(
                        request,
                        "You don't have permission to view this student's scores.",
                    )
                    return redirect("score_management_dashboard")

        # Get all terms in the academic year with school filtering
        terms = Term.objects.filter(
            school_filter, academic_year=selected_academic_year
        ).order_by("term_number")

        # Get the student's current class
        current_class = student.get_current_class()

        # Get all subjects and assessments for this student in the selected academic year
        subject_data = []

        # Get the school for filtering
        school = (
            school_info
            if not request.user.is_superadmin
            else (SchoolInformation.objects.get(id=school_id) if school_id else None)
        )

        for term in terms:
            # Find class assignments for this academic year/term with school filtering
            student_classes = StudentClass.objects.filter(
                school_filter,
                student=student,
                assigned_class__academic_year=selected_academic_year,
                date_assigned__lte=term.end_date,  # Class assignment before term end
            ).order_by("-date_assigned")

            student_class = student_classes.first()

            if student_class:

                # Get class subjects for this class - using the helper function (only active ones)
                class_subjects_query = ClassSubject.objects.filter(
                    class_name=student_class.assigned_class,
                    academic_year=selected_academic_year,
                    is_active=True

                )
                class_subjects = filter_by_school(
                    class_subjects_query, "ClassSubject", school
                )

                # Get assessments for each subject with school filtering
                for class_subject in class_subjects:
                    subject = class_subject.subject

                    # Check if we already have this subject in our data
                    subject_entry = next(
                        (
                            item
                            for item in subject_data
                            if item["subject"].id == subject.id
                        ),
                        None,
                    )

                    if not subject_entry:
                        subject_entry = {
                            "subject": subject,
                            "terms": {
                                t.id: {"term": t, "assessment": None} for t in terms
                            },
                        }
                        subject_data.append(subject_entry)

                    # Get assessment for this subject and term with school filtering

                    # Exclude mock exam assessments

                    assessment = Assessment.objects.filter(
                        school_filter,
                        class_subject=class_subject,
                        student=student,
                        term=term,

                    ).exclude(assessment_type='mock_exam').first()


                    # Add to subject data
                    subject_entry["terms"][term.id]["assessment"] = assessment

        # Calculate term averages
        term_averages = {}
        for term in terms:
            assessments = []
            for subject in subject_data:
                assessment = subject["terms"][term.id]["assessment"]
                if assessment and assessment.total_score is not None:
                    assessments.append(assessment.total_score)

            if assessments:
                term_averages[term.id] = sum(assessments) / len(assessments)
            else:
                term_averages[term.id] = None

        # Calculate subject averages across terms
        for subject in subject_data:
            assessments = []
            for term_id, term_data in subject["terms"].items():
                assessment = term_data["assessment"]
                if assessment and assessment.total_score is not None:
                    assessments.append(assessment.total_score)

            if assessments:
                subject["average"] = sum(assessments) / len(assessments)
            else:
                subject["average"] = None

        # Sort subjects by average scores (highest first)
        subject_data.sort(
            key=lambda x: x["average"] if x["average"] is not None else 0, reverse=True
        )

        # Generate performance graph data
        graph_data = self._generate_student_performance_graph(
            student, subject_data, terms
        )

        # Get all academic years for the filter dropdown with school filtering
        academic_years = AcademicYear.objects.filter(school_filter).order_by(
            "-start_date"
        )

        # Get scoring configuration
        scoring_config = None
        if school_info:
            scoring_config = ScoringConfiguration.get_active_config(school_info)

        context = {
            "student": student,
            "current_class": current_class,
            "subject_data": subject_data,
            "terms": terms,
            "term_averages": term_averages,
            "selected_academic_year": selected_academic_year,
            "academic_years": academic_years,
            "school_info": school_info,
            "performance_graph": graph_data,
            "all_schools": all_schools,
            "selected_school_id": school_id if request.user.is_superadmin else None,
            "scoring_config": scoring_config,
        }

        return render(request, "scores/student_score_detail.html", context)

    def _generate_student_performance_graph(self, student, subject_data, terms):
        """Generate performance graph data for a specific student"""

        # Term labels
        term_labels = [f"Term {term.term_number}" for term in terms]

        # Dataset for overall term averages
        overall_data = []
        for term in terms:
            term_scores = []
            for subject in subject_data:
                assessment = subject["terms"][term.id]["assessment"]
                if assessment and assessment.total_score is not None:
                    term_scores.append(assessment.total_score)

            if term_scores:
                overall_data.append(round(sum(term_scores) / len(term_scores), 2))
            else:
                overall_data.append(0)

        # Datasets for top 5 subjects
        subject_datasets = []
        for subject in subject_data[:5]:  # Top 5 subjects
            subject_scores = []
            for term in terms:
                assessment = subject["terms"][term.id]["assessment"]
                if assessment and assessment.total_score is not None:
                    subject_scores.append(float(assessment.total_score))
                else:
                    subject_scores.append(0)

            subject_datasets.append(
                {"label": subject["subject"].subject_name, "data": subject_scores}
            )

        return {
            "labels": term_labels,
            "overall_data": overall_data,
            "subject_datasets": subject_datasets,
        }


class SubjectPerformanceView(LoginRequiredMixin, ScoreManagementAccessMixin, View):
    """View for analyzing performance in a specific subject across multiple classes."""

    def get(self, request):
        subject_id = request.GET.get("subject_id")
        academic_year_id = request.GET.get("academic_year_id")
        term_id = request.GET.get("term_id")

        # Get school filter
        school_filter = self.get_school_filter()

        # Get current school context
        school_id = request.GET.get("school_id")
        if request.user.is_superadmin and school_id:
            school_info = SchoolInformation.objects.get(id=school_id)
        else:
            school_info = request.user.school or SchoolInformation.get_active()

        # For superadmins, get all schools for the school selector dropdown
        all_schools = None
        if request.user.is_superadmin:
            all_schools = SchoolInformation.objects.filter(is_active=True)

        # Use provided filters or defaults
        selected_academic_year = (
            AcademicYear.objects.filter(school_filter, id=academic_year_id).first()
            or school_info.current_academic_year
        )

        # Handle empty term_id properly
        selected_term = None
        if term_id and term_id.strip():  # Only filter if term_id is not empty
            selected_term = Term.objects.filter(
                school_filter, id=term_id, academic_year=selected_academic_year
            ).first()
        else:
            # Use current term or just set to None
            selected_term = school_info.current_term

        # Get all subjects with school filtering
        if request.user.role == "admin" or request.user.is_superadmin:
            available_subjects = Subject.objects.filter(school_filter).order_by(
                "subject_name"
            )
        elif request.user.role == "teacher":
            # Get subjects this teacher teaches within their school
            teacher = request.user.teacher_profile
            subject_ids = (
                TeacherSubjectAssignment.objects.filter(
                    school_filter,
                    teacher=teacher,
                    academic_year=selected_academic_year,
                    is_active=True,
                )
                .values_list("subject_id", flat=True)
                .distinct()
            )

            
            # Also filter by active ClassSubject assignments
            active_class_subject_subject_ids = ClassSubject.objects.filter(
                academic_year=selected_academic_year, is_active=True
            ).values_list('subject_id', flat=True).distinct()
            
            # Intersect the two sets of subject IDs
            final_subject_ids = set(subject_ids) & set(active_class_subject_subject_ids)
            
            available_subjects = Subject.objects.filter(
                school_filter, id__in=final_subject_ids

            ).order_by("subject_name")
        else:
            available_subjects = Subject.objects.none()

        # Selected subject
        selected_subject = None
        if subject_id:
            selected_subject = get_object_or_404(Subject, school_filter, id=subject_id)

            # Check if teacher teaches this subject
            if request.user.role == "teacher":
                teacher = request.user.teacher_profile
                if not TeacherSubjectAssignment.objects.filter(
                    school_filter,
                    teacher=teacher,
                    subject=selected_subject,
                    academic_year=selected_academic_year,
                    is_active=True,
                ).exists():
                    messages.error(
                        request,
                        "You don't have permission to view performance for this subject.",
                    )
                    return redirect("score_management_dashboard")
        elif available_subjects.exists():
            selected_subject = available_subjects.first()

        # Get class performance data for the selected subject with school filtering
        class_performance = []
        if selected_subject:
            # Get the school for filtering
            school = (
                school_info
                if not request.user.is_superadmin
                else (
                    SchoolInformation.objects.get(id=school_id) if school_id else None
                )
            )

            # Get all classes with this subject
            if request.user.role == "admin" or request.user.is_superadmin:
                # Use direct school field for ClassSubject
                class_subjects_query = ClassSubject.objects.filter(
                    subject=selected_subject,
                    academic_year=selected_academic_year,

                    is_active=True

                )
                class_subjects = filter_by_school(
                    class_subjects_query, "ClassSubject", school
                )
            else:
                # For teachers, only show classes they teach
                teacher = request.user.teacher_profile
                teacher_classes = TeacherSubjectAssignment.objects.filter(
                    school_filter,
                    teacher=teacher,
                    subject=selected_subject,
                    academic_year=selected_academic_year,
                    is_active=True,
                ).values_list("class_assigned_id", flat=True)

                # Get class subjects filtered by school and teacher assignments
                class_subjects_query = ClassSubject.objects.filter(
                    subject=selected_subject,
                    academic_year=selected_academic_year,
                    class_name__id__in=teacher_classes,

                    is_active=True

                )
                class_subjects = filter_by_school(
                    class_subjects_query, "ClassSubject", school
                )

            for class_subject in class_subjects:
                # Get all assessments for this class and subject with school filtering

                # Exclude mock exam assessments from subject performance statistics

                assessment_query = Assessment.objects.filter(
                    school_filter,
                    class_subject=class_subject,
                    term=selected_term,
                    total_score__isnull=False,

                ).exclude(assessment_type='mock_exam')


                # Apply term filter if specified
                if selected_term:
                    assessment_query = assessment_query.filter(
                        class_subject__academic_year=selected_term.academic_year
                    )

                # Calculate statistics
                if assessment_query.exists():
                    stats = assessment_query.aggregate(
                        average=Avg("total_score"),
                        maximum=Max("total_score"),
                        minimum=Min("total_score"),
                        count=Count("id"),
                    )

                    # Calculate grade distribution with school filtering
                    grade_distribution = {}
                    for grade in GradingSystem.get_all_active_grades(
                        school=school_info
                    ):
                        grade_count = assessment_query.filter(
                            total_score__gte=grade.min_score,
                            total_score__lte=grade.max_score,
                        ).count()
                        grade_distribution[grade.grade_letter] = grade_count

                    class_performance.append(
                        {
                            "class": class_subject.class_name,
                            "stats": stats,
                            "grade_distribution": grade_distribution,
                        }
                    )

        # Sort classes by average score (highest first)
        class_performance.sort(key=lambda x: x["stats"]["average"] or 0, reverse=True)

        # Generate performance graph data
        graph_data = self._generate_subject_performance_graph(
            selected_subject, class_performance
        )

        # Academic years and terms for filter dropdowns with school filtering
        academic_years = AcademicYear.objects.filter(school_filter).order_by(
            "-start_date"
        )
        terms = Term.objects.filter(
            school_filter, academic_year=selected_academic_year
        ).order_by("term_number")

        context = {
            "available_subjects": available_subjects,
            "selected_subject": selected_subject,
            "selected_academic_year": selected_academic_year,
            "selected_term": selected_term,
            "academic_years": academic_years,
            "terms": terms,
            "class_performance": class_performance,
            "school_info": school_info,
            "performance_graph": graph_data,
            "all_schools": all_schools,
            "selected_school_id": school_id if request.user.is_superadmin else None,
        }

        return render(request, "scores/subject_performance.html", context)

    def _generate_subject_performance_graph(self, subject, class_performance):
        """Generate performance graph data for a specific subject across classes"""

        if not subject or not class_performance:
            return None

        # Class labels
        class_labels = [item["class"].name for item in class_performance]

        # Average scores
        average_scores = [
            round(float(item["stats"]["average"]), 2) if item["stats"]["average"] else 0
            for item in class_performance
        ]

        # Min and max scores
        min_scores = [
            round(float(item["stats"]["minimum"]), 2) if item["stats"]["minimum"] else 0
            for item in class_performance
        ]
        max_scores = [
            round(float(item["stats"]["maximum"]), 2) if item["stats"]["maximum"] else 0
            for item in class_performance
        ]

        # Grade distribution data (collect all unique grades first)
        all_grades = set()
        for item in class_performance:
            all_grades.update(item["grade_distribution"].keys())

        grade_datasets = []
        for grade in sorted(all_grades):
            grade_data = []
            for item in class_performance:
                grade_data.append(item["grade_distribution"].get(grade, 0))

            grade_datasets.append({"label": grade, "data": grade_data})

        return {
            "labels": class_labels,
            "averages": average_scores,
            "min_scores": min_scores,
            "max_scores": max_scores,
            "grade_datasets": grade_datasets,
        }


class CompareScoreView(LoginRequiredMixin, ScoreManagementAccessMixin, View):
    """View for comparing scores across terms or subjects."""

    def get(self, request):
        comparison_type = request.GET.get("comparison_type", "terms")
        academic_year_id = request.GET.get("academic_year_id")
        class_id = request.GET.get("class_id")

        # Get school filter
        school_filter = self.get_school_filter()

        # Get current school context
        school_id = request.GET.get("school_id")
        if request.user.is_superadmin and school_id:
            school_info = SchoolInformation.objects.get(id=school_id)
        else:
            school_info = request.user.school or SchoolInformation.get_active()

        # For superadmins, get all schools for the school selector dropdown
        all_schools = None
        if request.user.is_superadmin:
            all_schools = SchoolInformation.objects.filter(is_active=True)

        # Get current settings if not specified
        selected_academic_year = (
            AcademicYear.objects.filter(school_filter, id=academic_year_id).first()
            or school_info.current_academic_year
        )

        # Get current term for assessment filtering
        selected_term = school_info.current_term

        # Get available classes based on user role with school filtering
        if request.user.role == "admin" or request.user.is_superadmin:
            available_classes = Class.objects.filter(
                school_filter, academic_year=selected_academic_year
            )
        elif request.user.role == "teacher":
            # Get classes this teacher teaches
            teacher = request.user.teacher_profile
            class_ids = (
                TeacherSubjectAssignment.objects.filter(
                    school_filter,
                    teacher=teacher,
                    academic_year=selected_academic_year,
                    is_active=True,
                )
                .values_list("class_assigned_id", flat=True)
                .distinct()
            )
            available_classes = Class.objects.filter(school_filter, id__in=class_ids)
        else:
            available_classes = Class.objects.none()

        # Selected class
        selected_class = None
        if class_id:
            selected_class = get_object_or_404(Class, school_filter, id=class_id)

            # Check if teacher has access to this class
            if request.user.role == "teacher":
                teacher = request.user.teacher_profile
                if not TeacherSubjectAssignment.objects.filter(
                    school_filter,
                    teacher=teacher,
                    class_assigned=selected_class,
                    is_active=True,
                ).exists():
                    messages.error(
                        request,
                        "You don't have permission to view scores for this class.",
                    )
                    return redirect("score_management_dashboard")
        elif available_classes.exists():
            selected_class = available_classes.first()

        # Prepare data based on comparison type
        comparison_data = None
        if selected_class:
            if comparison_type == "terms":
                comparison_data = self._compare_terms(
                    selected_class, selected_academic_year, school_filter
                )
            else:  # comparison_type == 'subjects'
                comparison_data = self._compare_subjects(
                    selected_class, selected_academic_year, school_filter, selected_term
                )

        # Academic years for filter dropdown with school filtering
        academic_years = AcademicYear.objects.filter(school_filter).order_by(
            "-start_date"
        )

        context = {
            "comparison_type": comparison_type,
            "available_classes": available_classes,
            "selected_class": selected_class,
            "selected_academic_year": selected_academic_year,
            "academic_years": academic_years,
            "comparison_data": comparison_data,
            "school_info": school_info,
            "all_schools": all_schools,
            "selected_school_id": school_id if request.user.is_superadmin else None,
        }

        return render(request, "scores/compare_scores.html", context)

    def _compare_terms(self, selected_class, academic_year, school_filter):
        """Generate data for term comparison with school filtering"""
        terms = Term.objects.filter(
            school_filter, academic_year=academic_year
        ).order_by("term_number")

        if not terms.exists():
            return None

        # Get students in this class with school filtering
        student_classes = StudentClass.objects.filter(
            school_filter, assigned_class=selected_class, is_active=True
        )

        students = [sc.student for sc in student_classes]

        # Initialize comparison data
        comparison_data = {
            "type": "terms",
            "terms": terms,
            "students": [],
            "averages": {},  # Term averages for the whole class
        }

        # For each student, collect performance across terms
        for student in students:
            student_terms = {}

            for term in terms:
                # Get all class subjects for this class in this academic year
                # ClassSubject doesn't have a school field, so we use the selected_class
                # which has already been filtered by school
                class_subjects = ClassSubject.objects.filter(

                    class_name=selected_class, academic_year=academic_year, is_active=True

                )

                # Get assessments for this student in this term with school filtering
                term_assessments = []
                for class_subject in class_subjects:

                    # Exclude mock exam assessments from term comparison

                    assessment = Assessment.objects.filter(
                        school_filter,
                        class_subject=class_subject,
                        student=student,
                        term=term,

                    ).exclude(assessment_type='mock_exam').first()


                    if assessment and assessment.total_score is not None:
                        term_assessments.append(assessment)

                # Calculate average for this term
                if term_assessments:
                    term_avg = sum(a.total_score for a in term_assessments) / len(
                        term_assessments
                    )
                    student_terms[term.id] = {
                        "term": term,
                        "average": round(term_avg, 2),
                        "assessments": term_assessments,
                    }
                else:
                    student_terms[term.id] = {
                        "term": term,
                        "average": None,
                        "assessments": [],
                    }

            # Add student data to comparison
            comparison_data["students"].append(
                {"student": student, "terms": student_terms}
            )

        # Calculate class averages per term
        for term in terms:
            term_scores = [
                s["terms"][term.id]["average"]
                for s in comparison_data["students"]
                if s["terms"][term.id]["average"] is not None
            ]

            if term_scores:
                comparison_data["averages"][term.id] = round(
                    sum(term_scores) / len(term_scores), 2
                )
            else:
                comparison_data["averages"][term.id] = None

        return comparison_data

    def _compare_subjects(self, selected_class, academic_year, school_filter, term):
        """Generate data for subject comparison with school filtering"""
        # Get all subjects for this class
        # ClassSubject doesn't have a school field, so we use the selected_class
        # which has already been filtered by school
        class_subjects = ClassSubject.objects.filter(

            class_name=selected_class, academic_year=academic_year, is_active=True

        )

        subjects = [cs.subject for cs in class_subjects]

        if not subjects:
            return None

        # Get students in this class with school filtering
        student_classes = StudentClass.objects.filter(
            school_filter, assigned_class=selected_class, is_active=True
        )

        students = [sc.student for sc in student_classes]

        # Initialize comparison data
        comparison_data = {
            "type": "subjects",
            "subjects": subjects,
            "students": [],
            "averages": {},  # Subject averages for the whole class
        }

        # For each student, collect performance across subjects
        for student in students:
            student_subjects = {}

            for subject in subjects:
                # Find the class subject
                try:
                    class_subject = ClassSubject.objects.get(
                        class_name=selected_class,
                        subject=subject,
                        academic_year=academic_year,

                        is_active=True
                    )

                    # Get assessment for this subject with school filtering
                    # Exclude mock exam assessments

                    assessment = Assessment.objects.filter(
                        school_filter,
                        class_subject=class_subject,
                        student=student,
                        term=term,

                    ).exclude(assessment_type='mock_exam').first()


                    if assessment:
                        student_subjects[subject.id] = {
                            "subject": subject,
                            "assessment": assessment,
                        }
                    else:
                        student_subjects[subject.id] = {
                            "subject": subject,
                            "assessment": None,
                        }

                except ClassSubject.DoesNotExist:
                    student_subjects[subject.id] = {
                        "subject": subject,
                        "assessment": None,
                    }

            # Add student data to comparison
            comparison_data["students"].append(
                {"student": student, "subjects": student_subjects}
            )

        # Calculate class averages per subject
        for subject in subjects:
            subject_scores = [
                s["subjects"][subject.id]["assessment"].total_score
                for s in comparison_data["students"]
                if s["subjects"][subject.id]["assessment"]
                and s["subjects"][subject.id]["assessment"].total_score is not None
            ]

            if subject_scores:
                comparison_data["averages"][subject.id] = round(
                    sum(subject_scores) / len(subject_scores), 2
                )
            else:
                comparison_data["averages"][subject.id] = None

        return comparison_data


class ProgressTrackingView(LoginRequiredMixin, ScoreManagementAccessMixin, View):
    """View for tracking student progress over time."""

    def get(self, request):
        student_id = request.GET.get("student_id")
        form_id = request.GET.get("form_id")

        # Get school filter
        school_filter = self.get_school_filter()

        # Get current school context
        school_id = request.GET.get("school_id")
        if request.user.is_superadmin and school_id:
            school_info = SchoolInformation.objects.get(id=school_id)
        else:
            school_info = request.user.school or SchoolInformation.get_active()

        # For superadmins, get all schools for the school selector dropdown
        all_schools = None
        if request.user.is_superadmin:
            all_schools = SchoolInformation.objects.filter(is_active=True)

        # Get available forms with school filtering
        forms = Form.objects.filter(school_filter).order_by("form_number")

        # Selected form
        selected_form = None
        if form_id:
            selected_form = get_object_or_404(Form, school_filter, id=form_id)
        elif forms.exists():
            selected_form = forms.first()

        # Get students in the selected form with school filtering
        available_students = []
        if selected_form:
            # Get current academic year
            current_academic_year = school_info.current_academic_year

            # Get classes for this form with school filtering
            form_classes = Class.objects.filter(
                school_filter, form=selected_form, academic_year=current_academic_year
            )

            # Get students in these classes with school filtering
            student_classes = StudentClass.objects.filter(
                school_filter, assigned_class__in=form_classes, is_active=True
            )

            # For teachers, filter to only their students
            if request.user.role == "teacher":
                teacher = request.user.teacher_profile
                teacher_classes = TeacherSubjectAssignment.objects.filter(
                    school_filter,
                    teacher=teacher,
                    academic_year=current_academic_year,
                    is_active=True,
                ).values_list("class_assigned_id", flat=True)

                student_classes = student_classes.filter(
                    assigned_class_id__in=teacher_classes
                )

            # Get unique students
            available_students = Student.objects.filter(
                school_filter,
                id__in=student_classes.values_list("student_id", flat=True),
            ).order_by("full_name")

        # Selected student
        selected_student = None
        if student_id:
            selected_student = get_object_or_404(Student, school_filter, id=student_id)

            # Check if teacher has access to this student
            if request.user.role == "teacher":
                teacher = request.user.teacher_profile
                student_class = StudentClass.objects.filter(
                    school_filter, student=selected_student, is_active=True
                ).first()

                if (
                    student_class
                    and not TeacherSubjectAssignment.objects.filter(
                        school_filter,
                        teacher=teacher,
                        class_assigned=student_class.assigned_class,
                        is_active=True,
                    ).exists()
                ):
                    messages.error(
                        request,
                        "You don't have permission to track this student's progress.",
                    )
                    return redirect("score_management_dashboard")
        elif available_students.exists():
            selected_student = available_students.first()

        # Get progress data for the selected student
        progress_data = None
        if selected_student:
            progress_data = self._get_student_progress(selected_student, school_filter)

        context = {
            "forms": forms,
            "selected_form": selected_form,
            "available_students": available_students,
            "selected_student": selected_student,
            "progress_data": progress_data,
            "school_info": school_info,
            "all_schools": all_schools,
            "selected_school_id": school_id if request.user.is_superadmin else None,
        }

        return render(request, "scores/progress_tracking.html", context)

    def _get_student_progress(self, student, school_filter):
        """Get comprehensive progress data for a student with school filtering"""
        # Get all academic years with school filtering
        academic_years = AcademicYear.objects.filter(school_filter).order_by(
            "start_date"
        )

        # Initialize progress data
        progress_data = {
            "academic_years": [],
            "overall_trend": [],
            "subject_trends": defaultdict(list),
        }

        # For each academic year, collect term data
        for academic_year in academic_years:
            year_data = {
                "academic_year": academic_year,
                "terms": [],
                "overall_average": None,
                "subjects": defaultdict(list),
            }

            # Get terms for this academic year with school filtering
            terms = Term.objects.filter(
                school_filter, academic_year=academic_year
            ).order_by("term_number")

            term_averages = []
            for term in terms:
                # Find student class for this term with school filtering
                student_class = (
                    StudentClass.objects.filter(
                        school_filter,
                        student=student,
                        assigned_class__academic_year=academic_year,
                        date_assigned__lte=term.end_date,
                    )
                    .order_by("-date_assigned")
                    .first()
                )

                if student_class:
                    # Get class subjects for this class
                    # ClassSubject doesn't have school field, so we use the student_class.assigned_class
                    # which has already been filtered by school
                    class_subjects = ClassSubject.objects.filter(
                        class_name=student_class.assigned_class,
                        academic_year=academic_year,

                        is_active=True

                    )

                    # Get assessments for this term with school filtering
                    term_assessments = []
                    for class_subject in class_subjects:

                        # Exclude mock exam assessments

                        assessment = Assessment.objects.filter(
                            school_filter,
                            class_subject=class_subject,
                            student=student,
                            term=term,

                        ).exclude(assessment_type='mock_exam').first()


                        if assessment and assessment.total_score is not None:
                            term_assessments.append(assessment)

                            # Add to subject trend
                            subject_name = class_subject.subject.subject_name
                            year_data["subjects"][subject_name].append(
                                {"term": term, "score": assessment.total_score}
                            )

                    # Calculate average for this term
                    if term_assessments:
                        term_avg = sum(a.total_score for a in term_assessments) / len(
                            term_assessments
                        )
                        term_averages.append(term_avg)

                        year_data["terms"].append(
                            {
                                "term": term,
                                "average": round(term_avg, 2),
                                "assessments": term_assessments,
                            }
                        )
                    else:
                        year_data["terms"].append(
                            {"term": term, "average": None, "assessments": []}
                        )
                else:
                    year_data["terms"].append(
                        {"term": term, "average": None, "assessments": []}
                    )

            # Calculate overall average for this academic year
            if term_averages:
                year_data["overall_average"] = round(
                    sum(term_averages) / len(term_averages), 2
                )

                # Add to overall trend
                progress_data["overall_trend"].append(
                    {
                        "academic_year": academic_year,
                        "average": year_data["overall_average"],
                    }
                )

            # Add year data to progress
            progress_data["academic_years"].append(year_data)

        # Process subject trends across academic years
        all_subjects = set()
        for year_data in progress_data["academic_years"]:
            all_subjects.update(year_data["subjects"].keys())

        for subject in all_subjects:
            subject_scores = []

            for year_data in progress_data["academic_years"]:
                for term_data in year_data["subjects"].get(subject, []):
                    subject_scores.append(
                        {
                            "academic_year": year_data["academic_year"],
                            "term": term_data["term"],
                            "score": term_data["score"],
                        }
                    )

            progress_data["subject_trends"][subject] = sorted(
                subject_scores,
                key=lambda x: (x["academic_year"].start_date, x["term"].term_number),
            )

        return progress_data


# Export views
class ExportScoreView(LoginRequiredMixin, ScoreManagementAccessMixin, View):
    """Base class for exporting scores in various formats."""

    def get_class_scores(self, class_id, subject_id, term_id, academic_year_id):
        """Get scores for a specific class, subject, term, and academic year."""
        # Get school filter
        school_filter = self.get_school_filter()

        # Get filter parameters or defaults
        if self.request.user.is_superadmin and self.request.GET.get("school_id"):
            school_info = SchoolInformation.objects.get(
                id=self.request.GET.get("school_id")
            )
        else:
            school_info = self.request.user.school or SchoolInformation.get_active()

        academic_year = (
            AcademicYear.objects.filter(school_filter, id=academic_year_id).first()
            or school_info.current_academic_year
        )

        # Handle empty term_id properly
        if term_id and term_id.strip():  # Only filter if term_id is not empty
            term = (
                Term.objects.filter(school_filter, id=term_id).first()
                or school_info.current_term
            )
        else:
            term = school_info.current_term

        class_obj = get_object_or_404(Class, school_filter, id=class_id)
        subject = get_object_or_404(Subject, school_filter, id=subject_id)

        # Check if teacher has access to this class and subject
        if self.request.user.role == "teacher":
            teacher = self.request.user.teacher_profile
            if not TeacherSubjectAssignment.objects.filter(
                school_filter,
                teacher=teacher,
                class_assigned=class_obj,
                subject=subject,
                is_active=True,
            ).exists():
                return None, None, None, None

        # Get class subject using helper function for school filtering
        school = (
            school_info
            if not self.request.user.is_superadmin
            else (
                SchoolInformation.objects.get(id=self.request.GET.get("school_id"))
                if self.request.GET.get("school_id")
                else None
            )
        )

        try:
            class_subject_query = ClassSubject.objects.filter(

                class_name=class_obj, subject=subject, academic_year=academic_year, is_active=True

            )
            class_subject = filter_by_school(
                class_subject_query, "ClassSubject", school
            ).first()

            if not class_subject:
                return None, None, None, None

        except ClassSubject.DoesNotExist:
            return None, None, None, None

        # Get students in this class with school filtering
        student_classes = StudentClass.objects.filter(
            school_filter, assigned_class=class_obj, is_active=True
        )

        # Get assessment data for these students with school filtering
        students_with_scores = []
        for student_class in student_classes:
            student = student_class.student

            # Get assessment for this student and subject with school filtering

            # Exclude mock exam assessments
            assessment = Assessment.objects.filter(
                school_filter, class_subject=class_subject, student=student, term=term
            ).exclude(assessment_type='mock_exam').first()


            students_with_scores.append(
                {
                    "student": student,
                    "assessment": assessment,
                }
            )

        # Sort by name
        students_with_scores.sort(key=lambda x: x["student"].full_name)

        return students_with_scores, class_obj, subject, academic_year


class ExportScorePDFView(ExportScoreView):
    """View for exporting scores as PDF."""

    def get(self, request, class_id, subject_id, term_id=None, academic_year_id=None):
        students_with_scores, class_obj, subject, academic_year = self.get_class_scores(
            class_id, subject_id, term_id, academic_year_id
        )

        if not students_with_scores:
            messages.error(request, "No data available to export.")
            return redirect("class_score_list")

        # Get school context
        if request.user.is_superadmin and request.GET.get("school_id"):
            school_info = SchoolInformation.objects.get(id=request.GET.get("school_id"))
        else:
            school_info = request.user.school or SchoolInformation.get_active()

        # Get scoring configuration
        scoring_config = None
        if school_info:
            scoring_config = ScoringConfiguration.get_active_config(school_info)

        # Get teacher information for this subject and class
        teacher_name = "Not Assigned"
        try:
            # Get the school for filtering
            school = (
                school_info
                if not request.user.is_superadmin
                else (
                    SchoolInformation.objects.get(id=request.GET.get("school_id"))
                    if request.GET.get("school_id")
                    else None
                )
            )

            # Find the teacher assigned to this class and subject
            class_subject_query = ClassSubject.objects.filter(

                class_name=class_obj, subject=subject, academic_year=academic_year, is_active=True

            )
            class_subject = filter_by_school(
                class_subject_query, "ClassSubject", school
            ).first()

            if class_subject:
                # Get teacher assignment for this class and subject
                teacher_assignment = TeacherSubjectAssignment.objects.filter(
                    class_assigned=class_obj,
                    subject=subject,
                    academic_year=academic_year,
                    is_active=True,
                ).first()

                if teacher_assignment and teacher_assignment.teacher:
                    teacher_name = teacher_assignment.teacher.full_name
        except Exception:
            # If there's any error getting teacher info, use default
            pass

        # Prepare context for PDF template with school info
        context = {
            "students": students_with_scores,
            "class": class_obj,
            "subject": subject,
            "academic_year": academic_year,
            "school_info": school_info,
            "teacher_name": teacher_name,
            "date_generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "generated_by": request.user.full_name,
            "scoring_config": scoring_config,
        }

        # Render HTML template
        html_string = render_to_string("scores/exports/score_sheet_pdf.html", context)


        # Generate PDF using safe utility function (handles WeasyPrint unavailability)
        pdf_file = generate_pdf_from_html(html_string)


        # Create HTTP response with PDF
        response = HttpResponse(pdf_file, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="{school_info.short_name}_score_sheet_{class_obj.name}_{subject.subject_name}.pdf"'
        )

        return response


class ExportScoreExcelView(ExportScoreView):
    """View for exporting scores as Excel."""

    def get(self, request, class_id, subject_id, term_id=None, academic_year_id=None):
        students_with_scores, class_obj, subject, academic_year = self.get_class_scores(
            class_id, subject_id, term_id, academic_year_id
        )

        if not students_with_scores:
            messages.error(request, "No data available to export.")
            return redirect("class_score_list")

        # Get school context
        if request.user.is_superadmin and request.GET.get("school_id"):
            school_info = SchoolInformation.objects.get(id=request.GET.get("school_id"))
        else:
            school_info = request.user.school or SchoolInformation.get_active()

        # Create a BytesIO object for the Excel file
        output = io.BytesIO()

        # Create Excel workbook and worksheet
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet("Score Sheet")

        # Add header row
        bold_format = workbook.add_format(
            {"bold": True, "align": "center", "border": 1}
        )
        date_format = workbook.add_format({"num_format": "yyyy-mm-dd", "border": 1})
        score_format = workbook.add_format(
            {"num_format": "0.00", "align": "center", "border": 1}
        )
        text_format = workbook.add_format({"align": "left", "border": 1})

        # Add school information in the header
        worksheet.merge_range(
            "A1:H1",
            f"{school_info.name} - Score Sheet",
            bold_format,
        )

        # Add title and metadata
        worksheet.merge_range(
            "A2:H2",
            f"Class: {class_obj.name} - Subject: {subject.subject_name}",
            bold_format,
        )
        worksheet.merge_range(
            "A3:H3", f"Academic Year: {academic_year.name}", text_format
        )
        worksheet.merge_range(
            "A4:H4",
            f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} by {request.user.full_name}",
            text_format,
        )

        # Header row
        headers = [
            "#",
            "Student ID",
            "Student Name",
            "Class Score",
            "Exam Score",
            "Total Score",
            "Grade",
            "Remarks",
        ]
        for col, header in enumerate(headers):
            worksheet.write(5, col, header, bold_format)

        # Data rows
        for row, data in enumerate(students_with_scores, start=6):
            student = data["student"]
            assessment = data["assessment"]

            worksheet.write(row, 0, row - 5, text_format)  # Row number
            worksheet.write(row, 1, student.admission_number, text_format)
            worksheet.write(row, 2, student.full_name, text_format)

            if assessment:
                worksheet.write(row, 3, assessment.class_score or 0, score_format)
                worksheet.write(row, 4, assessment.exam_score or 0, score_format)
                worksheet.write(row, 5, assessment.total_score or 0, score_format)
                worksheet.write(row, 6, assessment.grade or "N/A", text_format)
                worksheet.write(row, 7, assessment.remarks or "N/A", text_format)
            else:
                worksheet.write(row, 3, 0, score_format)
                worksheet.write(row, 4, 0, score_format)
                worksheet.write(row, 5, 0, score_format)
                worksheet.write(row, 6, "N/A", text_format)
                worksheet.write(row, 7, "N/A", text_format)

        # Adjust column widths
        worksheet.set_column("A:A", 5)
        worksheet.set_column("B:B", 15)
        worksheet.set_column("C:C", 30)
        worksheet.set_column("D:G", 12)
        worksheet.set_column("H:H", 20)

        # Close workbook
        workbook.close()

        # Create response with Excel file
        output.seek(0)
        response = HttpResponse(
            output.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = (
            f'attachment; filename="{school_info.short_name}_score_sheet_{class_obj.name}_{subject.subject_name}.xlsx"'
        )

        return response


class ExportScoreCSVView(ExportScoreView):
    """View for exporting scores as CSV."""

    def get(self, request, class_id, subject_id, term_id=None, academic_year_id=None):
        students_with_scores, class_obj, subject, academic_year = self.get_class_scores(
            class_id, subject_id, term_id, academic_year_id
        )

        if not students_with_scores:
            messages.error(request, "No data available to export.")
            return redirect("class_score_list")

        # Get school context
        if request.user.is_superadmin and request.GET.get("school_id"):
            school_info = SchoolInformation.objects.get(id=request.GET.get("school_id"))
        else:
            school_info = request.user.school or SchoolInformation.get_active()

        # Create response with CSV content type
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="{school_info.short_name}_score_sheet_{class_obj.name}_{subject.subject_name}.csv"'
        )

        # Create CSV writer
        writer = csv.writer(response)

        # Write header row with school information
        writer.writerow([f"{school_info.name} - Score Sheet"])
        writer.writerow([f"Class: {class_obj.name} - Subject: {subject.subject_name}"])
        writer.writerow([f"Academic Year: {academic_year.name}"])
        writer.writerow(
            [f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"]
        )
        writer.writerow([])  # Empty row for spacing

        # Write column headers
        writer.writerow(
            [
                "Student ID",
                "Student Name",
                "Class Score",
                "Exam Score",
                "Total Score",
                "Grade",
                "Remarks",
            ]
        )

        # Write data rows
        for data in students_with_scores:
            student = data["student"]
            assessment = data["assessment"]

            if assessment:
                writer.writerow(
                    [
                        student.admission_number,
                        student.full_name,
                        assessment.class_score or 0,
                        assessment.exam_score or 0,
                        assessment.total_score or 0,
                        assessment.grade or "N/A",
                        assessment.remarks or "N/A",
                    ]
                )
            else:
                writer.writerow(
                    [student.admission_number, student.full_name, 0, 0, 0, "N/A", "N/A"]
                )

        return response
