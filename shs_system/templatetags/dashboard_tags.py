from django import template
from django.db.models import Avg, Count, Q, F
from shs_system.models import (
    Assessment,
    SchoolInformation,
    Term,
    Subject,
    Class,
    Student,
    StudentClass,
    ClassSubject,
)
import json



register = template.Library()



@register.simple_tag
def get_score_statistics(school=None):
    """
    Get overall score statistics for current academic year
    """
    if school:
        school_info = school
    else:
        school_info = SchoolInformation.get_active()
    
    if not school_info:
        return {
            "avg_score": 0,
            "passing_percentage": 0,
            "excellent_percentage": 0,
            "below_average_percentage": 0,
        }
    
    current_academic_year = school_info.current_academic_year
    current_term = school_info.current_term

    # Base queryset - assessments for current academic year, filtered by school
    # Exclude mock exam assessments from dashboard statistics
    assessments = Assessment.objects.filter(
        class_subject__academic_year=current_academic_year, 
        total_score__isnull=False,
        school=school_info
    ).exclude(assessment_type='mock_exam')


    # Get overall statistics
    stats = {
        "avg_score": 0,
        "passing_count": 0,
        "failing_count": 0,
        "total_count": 0,
        "excellent_count": 0,
        "very_good_count": 0,
        "good_count": 0,
        "average_count": 0,
        "below_average_count": 0,
    }

    # Calculate overall statistics
    agg_data = assessments.aggregate(
        avg_score=Avg("total_score"),
        total_count=Count("id"),
        passing_count=Count("id", filter=Q(total_score__gte=40)),
        excellent_count=Count("id", filter=Q(total_score__gte=80)),
        very_good_count=Count("id", filter=Q(total_score__gte=70, total_score__lt=80)),
        good_count=Count("id", filter=Q(total_score__gte=60, total_score__lt=70)),
        average_count=Count("id", filter=Q(total_score__gte=40, total_score__lt=60)),
        below_average_count=Count("id", filter=Q(total_score__lt=40)),
    )

    stats.update(agg_data)
    stats["failing_count"] = stats["total_count"] - stats["passing_count"]

    # Calculate percentages
    if stats["total_count"] > 0:
        stats["passing_percentage"] = round(
            (stats["passing_count"] / stats["total_count"]) * 100, 2
        )
        stats["failing_percentage"] = round(
            (stats["failing_count"] / stats["total_count"]) * 100, 2
        )
        stats["excellent_percentage"] = round(
            (stats["excellent_count"] / stats["total_count"]) * 100, 2
        )
        stats["very_good_percentage"] = round(
            (stats["very_good_count"] / stats["total_count"]) * 100, 2
        )
        stats["good_percentage"] = round(
            (stats["good_count"] / stats["total_count"]) * 100, 2
        )
        stats["average_percentage"] = round(
            (stats["average_count"] / stats["total_count"]) * 100, 2
        )
        stats["below_average_percentage"] = round(
            (stats["below_average_count"] / stats["total_count"]) * 100, 2
        )
    else:
        stats.update(
            {
                "passing_percentage": 0,
                "failing_percentage": 0,
                "excellent_percentage": 0,
                "very_good_percentage": 0,
                "good_percentage": 0,
                "average_percentage": 0,
                "below_average_percentage": 0,
            }
        )

    return stats


@register.simple_tag

def get_subject_performance_data(school=None):
    """
    Get subject performance data for chart visualization
    """
    if school:
        school_info = school
    else:
        school_info = SchoolInformation.get_active()
    
    if not school_info:
        return {"labels": json.dumps([]), "data": json.dumps([])}
    
    current_academic_year = school_info.current_academic_year

    # Get top subjects by performance, filtered by school

    subject_performance = (
        Assessment.objects.filter(
            class_subject__academic_year=current_academic_year,
            total_score__isnull=False,

            school=school_info,

        )
        .values("class_subject__subject__subject_name")
        .annotate(average_score=Avg("total_score"))
        .order_by("-average_score")[:10]  # Top 10 subjects
    )

    # Format for charts
    labels = [
        item["class_subject__subject__subject_name"] for item in subject_performance
    ]

    data = [round(float(item["average_score"]), 2) for item in subject_performance]


    return {"labels": json.dumps(labels), "data": json.dumps(data)}


@register.simple_tag

def get_class_performance_data(school=None):
    """
    Get class performance data for chart visualization
    """
    if school:
        school_info = school
    else:
        school_info = SchoolInformation.get_active()
    
    if not school_info:
        return {"labels": json.dumps([]), "data": json.dumps([])}
    
    current_academic_year = school_info.current_academic_year

    # Get class performance, filtered by school

    class_performance = (
        Assessment.objects.filter(
            class_subject__academic_year=current_academic_year,
            total_score__isnull=False,

            school=school_info,

        )
        .values("class_subject__class_name__name")
        .annotate(average_score=Avg("total_score"))
        .order_by("class_subject__class_name__name")
    )

    # Format for charts
    labels = [item["class_subject__class_name__name"] for item in class_performance]

    data = [round(float(item["average_score"]), 2) for item in class_performance]


    return {"labels": json.dumps(labels), "data": json.dumps(data)}


@register.simple_tag

def get_score_distribution_data(school=None):
    """
    Get score distribution data for chart visualization
    """
    if school:
        school_info = school
    else:
        school_info = SchoolInformation.get_active()
    
    if not school_info:
        return {"labels": json.dumps([]), "data": json.dumps([])}
    

    current_academic_year = school_info.current_academic_year

    # Define score ranges
    score_ranges = [
        {"min": 0, "max": 40, "label": "0-40"},
        {"min": 40, "max": 55, "label": "40-55"},
        {"min": 55, "max": 70, "label": "55-70"},
        {"min": 70, "max": 85, "label": "70-85"},
        {"min": 85, "max": 101, "label": "85-100"},
    ]


    # Calculate counts for each range, filtered by school

    distribution_data = []
    for range_info in score_ranges:
        count = Assessment.objects.filter(
            class_subject__academic_year=current_academic_year,
            total_score__isnull=False,
            total_score__gte=range_info["min"],
            total_score__lt=range_info["max"],

            school=school_info,

        ).count()
        distribution_data.append({"label": range_info["label"], "count": count})

    # Format for charts
    labels = [item["label"] for item in distribution_data]
    data = [item["count"] for item in distribution_data]

    return {"labels": json.dumps(labels), "data": json.dumps(data)}


@register.simple_tag

def get_term_performance_trend(school=None):
    """
    Get term performance trend data for the current academic year
    """
    if school:
        school_info = school
    else:
        school_info = SchoolInformation.get_active()
    
    if not school_info:
        return {"labels": json.dumps([]), "data": json.dumps([])}
    
    current_academic_year = school_info.current_academic_year

    # Get terms in current academic year, filtered by school
    terms = Term.objects.filter(academic_year=current_academic_year, school=school_info).order_by(

        "term_number"
    )

    term_data = []
    for term in terms:

        # Find assessments for this term's academic year, filtered by school
        avg_score = (
            Assessment.objects.filter(
                class_subject__academic_year=term.academic_year,
                school=school_info,

            ).aggregate(avg=Avg("total_score"))["avg"]
            or 0
        )

        term_data.append(
            {
                "term_name": f"Term {term.term_number}",
                "avg_score": round(float(avg_score), 2),
            }
        )

    # Format for charts
    labels = [item["term_name"] for item in term_data]
    data = [item["avg_score"] for item in term_data]

    return {"labels": json.dumps(labels), "data": json.dumps(data)}


@register.simple_tag

def get_top_students(school=None):
    """
    Get top performing students in the current academic year
    """
    if school:
        school_info = school
    else:
        school_info = SchoolInformation.get_active()
    
    if not school_info:
        return []
    
    current_academic_year = school_info.current_academic_year

    # Get student IDs and their average scores, filtered by school

    top_students_data = (
        Assessment.objects.filter(
            class_subject__academic_year=current_academic_year,
            total_score__isnull=False,

            school=school_info,

        )
        .values("student")
        .annotate(avg_score=Avg("total_score"), assessment_count=Count("id"))
        .filter(
            assessment_count__gte=3
        )  # Only include students with at least 3 assessments
        .order_by("-avg_score")[:5]  # Top 5 students
    )

    # Get full student objects
    top_students = []
    for data in top_students_data:
        student = Student.objects.get(id=data["student"])
        current_class = student.get_current_class()

        top_students.append(
            {
                "student": student,
                "full_name": student.full_name,
                "avg_score": round(data["avg_score"], 2),
                "current_class": current_class.name if current_class else "N/A",
                "assessment_count": data["assessment_count"],
            }
        )

    return top_students


@register.simple_tag
def get_teacher_subject_performance(teacher, academic_year=None):
    """
    Get subject performance data for a specific teacher
    """
    if not academic_year:
        school_info = SchoolInformation.get_active()
        academic_year = school_info.current_academic_year

    # Get this teacher's subject assignments
    teacher_assignments = teacher.teachersubjectassignment_set.filter(
        academic_year=academic_year, is_active=True
    ).select_related("class_assigned", "subject")

    # Find class subjects matching those assignments
    subject_performance = []

    for assignment in teacher_assignments:
        # Find class subject
        class_subject = ClassSubject.objects.filter(
            class_name=assignment.class_assigned,
            subject=assignment.subject,
            academic_year=academic_year,

            is_active=True

        ).first()

        if class_subject:
            # Get assessment data for this class subject
            avg_score = (
                Assessment.objects.filter(
                    class_subject=class_subject, total_score__isnull=False
                ).aggregate(avg=Avg("total_score"))["avg"]
                or 0
            )

            # Calculate passing rate
            assessments = Assessment.objects.filter(class_subject=class_subject)
            total_count = assessments.count()
            passing_count = assessments.filter(total_score__gte=40).count()
            passing_rate = (passing_count / total_count * 100) if total_count > 0 else 0

            subject_performance.append(
                {
                    "subject_name": assignment.subject.subject_name,
                    "class_name": assignment.class_assigned.name,
                    "avg_score": round(float(avg_score), 2),
                    "passing_rate": round(passing_rate, 2),
                    "total_students": total_count,
                }
            )

    # Sort by average score descending
    subject_performance = sorted(
        subject_performance, key=lambda x: x["avg_score"], reverse=True
    )

    # Format for charts
    chart_data = {
        "labels": json.dumps(
            [
                item["subject_name"] + " (" + item["class_name"] + ")"
                for item in subject_performance
            ]
        ),

        "avg_scores": json.dumps([item["avg_score"] for item in subject_performance]),
        "passing_rates": json.dumps(
            [item["passing_rate"] for item in subject_performance]

        ),
    }

    return {"performance_data": subject_performance, "chart_data": chart_data}


@register.simple_tag
def get_teacher_assessment_trends(teacher, academic_year=None):
    """
    Get assessment trends over time for a specific teacher
    """
    if not academic_year:
        school_info = SchoolInformation.get_active()
        academic_year = school_info.current_academic_year

    # Get last 6 months of data
    from datetime import timedelta, datetime

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=180)  # Approximately 6 months

    # Get this teacher's subject assignments
    teacher_assignments = teacher.teachersubjectassignment_set.filter(
        academic_year=academic_year, is_active=True
    )

    # Get all class subjects for this teacher
    class_subjects = []
    for assignment in teacher_assignments:
        class_subject = ClassSubject.objects.filter(
            class_name=assignment.class_assigned,
            subject=assignment.subject,
            academic_year=academic_year,

            is_active=True

        ).first()

        if class_subject:
            class_subjects.append(class_subject.id)

    # Get assessments by month
    from django.db.models.functions import TruncMonth

    monthly_data = (
        Assessment.objects.filter(
            class_subject_id__in=class_subjects,
            date_recorded__gte=start_date,
            date_recorded__lte=end_date,
        )
        .annotate(month=TruncMonth("date_recorded"))
        .values("month")
        .annotate(avg_score=Avg("total_score"), count=Count("id"))
        .order_by("month")
    )

    # Format for charts
    months = []
    avg_scores = []
    assessment_counts = []

    for month_data in monthly_data:
        months.append(month_data["month"].strftime("%b %Y"))
        avg_scores.append(round(float(month_data["avg_score"] or 0), 2))
        assessment_counts.append(month_data["count"])

    return {
        "labels": json.dumps(months),
        "avg_scores": json.dumps(avg_scores),
        "assessment_counts": json.dumps(assessment_counts),
    }


@register.simple_tag
def get_teacher_grade_distribution(teacher, academic_year=None):
    """
    Get grade distribution for a specific teacher
    """
    if not academic_year:
        school_info = SchoolInformation.get_active()
        academic_year = school_info.current_academic_year

    # Get this teacher's subject assignments
    teacher_assignments = teacher.teachersubjectassignment_set.filter(
        academic_year=academic_year, is_active=True
    )

    # Get all class subjects for this teacher
    class_subjects = []
    for assignment in teacher_assignments:
        class_subject = ClassSubject.objects.filter(
            class_name=assignment.class_assigned,
            subject=assignment.subject,
            academic_year=academic_year,

            is_active=True

        ).first()

        if class_subject:
            class_subjects.append(class_subject.id)

    # Grade distribution
    grade_distribution = {
        "excellent": Assessment.objects.filter(
            class_subject_id__in=class_subjects, total_score__gte=80
        ).count(),
        "very_good": Assessment.objects.filter(
            class_subject_id__in=class_subjects, total_score__gte=70, total_score__lt=80
        ).count(),
        "good": Assessment.objects.filter(
            class_subject_id__in=class_subjects, total_score__gte=60, total_score__lt=70
        ).count(),
        "average": Assessment.objects.filter(
            class_subject_id__in=class_subjects, total_score__gte=40, total_score__lt=60
        ).count(),
        "below_average": Assessment.objects.filter(
            class_subject_id__in=class_subjects, total_score__lt=40
        ).count(),
    }

    # Calculate total
    total = sum(grade_distribution.values())

    # Calculate percentages
    percentages = {}
    for grade, count in grade_distribution.items():
        percentages[grade] = round((count / total * 100), 2) if total > 0 else 0

    # Format for charts
    labels = [
        "Excellent (80-100)",
        "Very Good (70-79)",
        "Good (60-69)",
        "Average (40-59)",
        "Below Average (0-39)",
    ]
    counts = [
        grade_distribution["excellent"],
        grade_distribution["very_good"],
        grade_distribution["good"],
        grade_distribution["average"],
        grade_distribution["below_average"],
    ]

    return {
        "distribution": grade_distribution,
        "percentages": percentages,
        "labels": json.dumps(labels),
        "counts": json.dumps(counts),
        "total": total,
    }


@register.filter
def get_teacher_monitoring_status(completion_rate):
    """
    Determine the status of teacher monitoring based on completion rate.
    Returns: 'complete', 'in-progress', or 'not-started'

    Args:
        completion_rate: The percentage of completion (0-100)
    """
    try:
        # Convert to float in case it's a string or None
        rate = float(completion_rate) if completion_rate is not None else 0

        if rate >= 90:
            return "complete"
        elif rate > 0:
            return "in-progress"
        else:
            return "not-started"
    except (ValueError, TypeError):
        # Handle cases where completion_rate is not a valid number
        return "not-started"


@register.filter
def get_status_badge_class(status):
    """
    Return the appropriate Bootstrap badge class based on status.

    Args:
        status: One of 'complete', 'in-progress', or 'not-started'
    """
    status_classes = {
        "complete": "badge bg-success",
        "in-progress": "badge bg-warning text-dark",
        "not-started": "badge bg-danger",
        # Default case
        None: "badge bg-secondary",
    }

    return status_classes.get(status, "badge bg-secondary")


@register.filter
def percentage_display(value, default=0):
    """
    Format a percentage value with proper handling of None values.

    Args:
        value: The percentage value to format
        default: Default value to use if value is None
    """
    try:
        if value is None:
            return f"{default}%"
        return f"{float(value):.1f}%"
    except (ValueError, TypeError):
        return f"{default}%"


@register.filter
def safe_division(numerator, denominator):
    """
    Safely divide two numbers, returning 0 if denominator is 0.

    Args:
        numerator: The top number in division
        denominator: The bottom number in division
    """
    try:
        if denominator == 0:
            return 0
        return (numerator / denominator) * 100
    except (ValueError, TypeError, ZeroDivisionError):
        return 0
