"""
Utility functions for mock exam performance analysis.
Contains helper functions for trend calculation, predictions, and recommendations.
"""

from decimal import Decimal
from typing import List, Dict, Optional, Tuple
from django.db.models import Avg, Count, Q
from django.utils import timezone
from datetime import date, timedelta

from ..models import (
    Assessment,
    MockExamPerformance,
    Student,
    ClassSubject,
    Term,
    AcademicYear,
    SchoolInformation,
)


def calculate_score_trend(student: Student, class_subject: ClassSubject, academic_year: AcademicYear) -> Dict:
    """
    Calculate comprehensive score trend for a student in a specific subject.
    
    Args:
        student: Student instance
        class_subject: ClassSubject instance
        academic_year: AcademicYear instance
    
    Returns:
        Dict containing trend analysis
    """
    # Get all mock exams for this student/subject/year
    mock_performances = MockExamPerformance.objects.filter(
        student=student,
        class_subject=class_subject,
        academic_year=academic_year
    ).order_by('mock_exam_date')
    
    if not mock_performances.exists():
        return {
            'trend': 'no_data',
            'trend_description': 'No mock exams taken yet',
            'total_mocks': 0,
            'average_score': 0,
            'score_progression': [],
            'improvement_rate': 0,
            'consistency': 'unknown'
        }
    
    # Convert to floats to avoid Decimal arithmetic issues in statistical ops
    scores = [float(mp.scaled_score) for mp in mock_performances]
    dates = [mp.mock_exam_date for mp in mock_performances]
    
    # Calculate basic statistics
    total_mocks = len(scores)
    average_score = sum(scores) / total_mocks
    
    # Calculate trend
    if total_mocks == 1:
        trend = 'baseline'
        trend_description = 'First mock exam - baseline established'
        improvement_rate = 0
    elif total_mocks >= 2:
        # Calculate improvement rate (slope)
        x_values = list(range(total_mocks))
        y_values = scores
        
        # Simple linear regression
        n = total_mocks
        x_mean = sum(x_values) / n
        y_mean = sum(y_values) / n
        
        numerator = sum((x_values[i] - x_mean) * (y_values[i] - y_mean) for i in range(n))
        denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))
        
        if denominator != 0:
            slope = numerator / denominator
            improvement_rate = slope
        else:
            improvement_rate = 0
        
        # Determine trend category
        if improvement_rate > 2:
            trend = 'strongly_improving'
            trend_description = f'Strong upward trend (+{improvement_rate:.1f} points per mock)'
        elif improvement_rate > 0.5:
            trend = 'improving'
            trend_description = f'Improving trend (+{improvement_rate:.1f} points per mock)'
        elif improvement_rate < -2:
            trend = 'strongly_declining'
            trend_description = f'Strong downward trend ({improvement_rate:.1f} points per mock)'
        elif improvement_rate < -0.5:
            trend = 'declining'
            trend_description = f'Declining trend ({improvement_rate:.1f} points per mock)'
        else:
            trend = 'stable'
            trend_description = f'Stable performance (±{abs(improvement_rate):.1f} points per mock)'
    else:
        trend = 'insufficient_data'
        trend_description = 'Insufficient data for trend analysis'
        improvement_rate = 0
    
    # Calculate consistency (standard deviation)
    if total_mocks >= 2:
        variance = sum((score - average_score) ** 2 for score in scores) / total_mocks
        std_dev = variance ** 0.5
        
        if std_dev <= 5:
            consistency = 'very_consistent'
        elif std_dev <= 10:
            consistency = 'consistent'
        elif std_dev <= 15:
            consistency = 'moderately_consistent'
        else:
            consistency = 'inconsistent'
    else:
        consistency = 'unknown'
    
    # Create score progression data
    score_progression = [
        {
            'mock_number': i + 1,
            'date': dates[i].strftime('%Y-%m-%d'),
            'score': float(scores[i]),
            'position': mp.position_in_class if hasattr(mp, 'position_in_class') else None
        }
        for i, mp in enumerate(mock_performances)
    ]
    
    return {
        'trend': trend,
        'trend_description': trend_description,
        'total_mocks': total_mocks,
        'average_score': float(average_score),
        'score_progression': score_progression,
        'improvement_rate': float(improvement_rate),
        'consistency': consistency,
        'standard_deviation': float(std_dev) if total_mocks >= 2 else 0,
        'latest_score': float(scores[-1]) if scores else 0,
        'best_score': float(max(scores)) if scores else 0,
        'worst_score': float(min(scores)) if scores else 0,
    }


def get_previous_mock_scores(student: Student, class_subject: ClassSubject, limit: int = 5) -> List[Dict]:
    """
    Get previous mock exam scores for trend analysis.
    
    Args:
        student: Student instance
        class_subject: ClassSubject instance
        limit: Maximum number of previous scores to return
    
    Returns:
        List of dictionaries containing mock exam data
    """
    mock_performances = MockExamPerformance.objects.filter(
        student=student,
        class_subject=class_subject
    ).order_by('-mock_exam_date')[:limit]
    
    return [
        {
            'mock_number': mp.mock_exam_number,
            'date': mp.mock_exam_date,
            'raw_score': float(mp.raw_score),
            'scaled_score': float(mp.scaled_score),
            'position': mp.position_in_class,
            'class_average': float(mp.class_average),
            'percentile': float(mp.percentile_rank),
            'trend': mp.score_trend,
            'percentage_change': float(mp.percentage_change) if mp.percentage_change else None,
        }
        for mp in mock_performances
    ]


def predict_final_exam_score(mock_scores: List[float], confidence_threshold: float = 0.7) -> Dict:
    """
    Predict final exam score using linear regression on mock exam scores.
    
    Args:
        mock_scores: List of mock exam scores
        confidence_threshold: Minimum confidence level for prediction
    
    Returns:
        Dict containing prediction and confidence metrics
    """
    if len(mock_scores) < 2:
        return {
            'predicted_score': None,
            'confidence': 'insufficient_data',
            'confidence_level': 0,
            'prediction_method': 'insufficient_data',
            'error_margin': None,
            'recommendation': 'Take more mock exams for accurate prediction'
        }
    
    n = len(mock_scores)
    x_values = list(range(n))
    y_values = mock_scores
    
    # Calculate linear regression
    x_mean = sum(x_values) / n
    y_mean = sum(y_values) / n
    
    numerator = sum((x_values[i] - x_mean) * (y_values[i] - y_mean) for i in range(n))
    denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))
    
    if denominator == 0:
        slope = 0
    else:
        slope = numerator / denominator
    
    intercept = y_mean - slope * x_mean
    
    # Predict final exam score (next data point)
    predicted_score = intercept + slope * n
    
    # Calculate confidence based on R-squared and number of data points
    if n >= 2:
        # Calculate R-squared
        y_pred = [intercept + slope * x for x in x_values]
        ss_res = sum((y_values[i] - y_pred[i]) ** 2 for i in range(n))
        ss_tot = sum((y_values[i] - y_mean) ** 2 for i in range(n))
        
        if ss_tot != 0:
            r_squared = 1 - (ss_res / ss_tot)
        else:
            r_squared = 0
        
        # Calculate confidence level
        confidence_level = min(r_squared, 1.0)
        
        # Adjust confidence based on number of data points
        if n >= 5:
            confidence_level *= 1.0
        elif n >= 3:
            confidence_level *= 0.8
        else:
            confidence_level *= 0.6
        
        # Determine confidence category
        if confidence_level >= 0.8:
            confidence = 'high'
        elif confidence_level >= 0.6:
            confidence = 'medium'
        else:
            confidence = 'low'
        
        # Calculate error margin (standard error)
        if n > 2:
            mse = ss_res / (n - 2)
            error_margin = (mse ** 0.5) * 1.96  # 95% confidence interval
        else:
            error_margin = None
        
        prediction_method = f'Linear regression (R²={r_squared:.3f})'
        
    else:
        confidence_level = 0
        confidence = 'insufficient_data'
        error_margin = None
        prediction_method = 'insufficient_data'
    
    # Clamp predicted score between 0 and 100
    predicted_score = max(0, min(100, predicted_score))
    
    # Generate recommendation
    if confidence_level >= confidence_threshold:
        if predicted_score >= 80:
            recommendation = 'Excellent predicted performance - maintain current approach'
        elif predicted_score >= 70:
            recommendation = 'Good predicted performance - continue current study methods'
        elif predicted_score >= 60:
            recommendation = 'Average predicted performance - focus on weak areas'
        else:
            recommendation = 'Below average predicted performance - intensive study needed'
    else:
        recommendation = 'Take more mock exams for reliable prediction'
    
    return {
        'predicted_score': float(predicted_score),
        'confidence': confidence,
        'confidence_level': float(confidence_level),
        'prediction_method': prediction_method,
        'error_margin': float(error_margin) if error_margin else None,
        'recommendation': recommendation,
        'slope': float(slope),
        'intercept': float(intercept),
        'r_squared': float(r_squared) if n >= 2 else 0,
    }


def generate_study_recommendations(performance_data: Dict) -> Dict:
    """
    Generate personalized study recommendations based on performance data.
    
    Args:
        performance_data: Dictionary containing performance metrics
    
    Returns:
        Dict containing recommendations and improvement areas
    """
    recommendations = []
    improvement_areas = []
    priority_actions = []
    
    trend = performance_data.get('trend', 'unknown')
    consistency = performance_data.get('consistency', 'unknown')
    average_score = performance_data.get('average_score', 0)
    total_mocks = performance_data.get('total_mocks', 0)
    
    # Trend-based recommendations
    if trend == 'strongly_improving':
        recommendations.append("Excellent progress! Maintain your current study approach")
        recommendations.append("Consider taking on more challenging practice questions")
        improvement_areas.append("Advanced problem-solving")
        
    elif trend == 'improving':
        recommendations.append("Good improvement trend - keep up the consistent effort")
        recommendations.append("Focus on maintaining momentum with regular practice")
        improvement_areas.append("Consistency maintenance")
        
    elif trend == 'declining':
        recommendations.append("Performance is declining - review study methods")
        recommendations.append("Identify specific topics causing difficulty")
        recommendations.append("Consider seeking additional help from teacher")
        improvement_areas.append("Study method review")
        improvement_areas.append("Weak topic identification")
        priority_actions.append("Schedule teacher consultation")
        
    elif trend == 'strongly_declining':
        recommendations.append("Significant performance decline - immediate action needed")
        recommendations.append("Review fundamental concepts")
        recommendations.append("Consider intensive tutoring")
        improvement_areas.append("Fundamental concept review")
        improvement_areas.append("Intensive remediation")
        priority_actions.append("Urgent teacher meeting")
        priority_actions.append("Consider additional tutoring")
        
    elif trend == 'stable':
        recommendations.append("Performance is stable - identify areas for breakthrough")
        recommendations.append("Increase practice intensity")
        recommendations.append("Focus on weak areas")
        improvement_areas.append("Targeted improvement")
        improvement_areas.append("Practice intensity")
    
    # Consistency-based recommendations
    if consistency == 'inconsistent':
        recommendations.append("Performance is inconsistent - establish regular study routine")
        recommendations.append("Focus on consistent preparation rather than cramming")
        improvement_areas.append("Study routine establishment")
        priority_actions.append("Create study schedule")
    
    elif consistency == 'very_consistent':
        recommendations.append("Excellent consistency - consider pushing boundaries")
        recommendations.append("Try more challenging problems")
        improvement_areas.append("Advanced challenges")
    
    # Score-based recommendations
    if average_score >= 85:
        recommendations.append("Outstanding performance - maintain excellence")
        recommendations.append("Consider helping classmates or advanced topics")
        improvement_areas.append("Peer tutoring")
        improvement_areas.append("Advanced topics")
        
    elif average_score >= 75:
        recommendations.append("Good performance - focus on reaching excellence")
        recommendations.append("Identify remaining weak areas")
        improvement_areas.append("Excellence pursuit")
        
    elif average_score >= 65:
        recommendations.append("Average performance - significant improvement possible")
        recommendations.append("Focus on fundamental understanding")
        improvement_areas.append("Fundamental understanding")
        improvement_areas.append("Practice intensity")
        
    else:
        recommendations.append("Below average performance - intensive improvement needed")
        recommendations.append("Focus on basic concepts and regular practice")
        recommendations.append("Consider additional support")
        improvement_areas.append("Basic concept mastery")
        improvement_areas.append("Regular practice")
        priority_actions.append("Seek additional help")
    
    # Mock exam frequency recommendations
    if total_mocks < 3:
        recommendations.append("Take more mock exams for better trend analysis")
        priority_actions.append("Schedule more mock exams")
    
    return {
        'recommendations': recommendations,
        'improvement_areas': improvement_areas,
        'priority_actions': priority_actions,
        'study_focus': improvement_areas[:3],  # Top 3 areas
        'next_steps': priority_actions[:2],   # Top 2 actions
    }


def calculate_class_statistics(class_subject: ClassSubject, mock_date: Optional[date] = None) -> Dict:
    """
    Calculate comprehensive class statistics for mock exams.
    
    Args:
        class_subject: ClassSubject instance
        mock_date: Optional specific date for mock exam
    
    Returns:
        Dict containing class statistics
    """
    # Build query
    query = MockExamPerformance.objects.filter(class_subject=class_subject)
    
    if mock_date:
        query = query.filter(mock_exam_date=mock_date)
    
    mock_performances = query.select_related('student')
    
    if not mock_performances.exists():
        return {
            'total_students': 0,
            'average_score': 0,
            'highest_score': 0,
            'lowest_score': 0,
            'median_score': 0,
            'standard_deviation': 0,
            'pass_rate': 0,
            'grade_distribution': {},
            'performance_levels': {},
        }
    
    scores = [float(mp.scaled_score) for mp in mock_performances]
    total_students = len(scores)
    
    # Basic statistics
    average_score = sum(scores) / total_students
    highest_score = max(scores)
    lowest_score = min(scores)
    
    # Median calculation
    sorted_scores = sorted(scores)
    if total_students % 2 == 0:
        median_score = (sorted_scores[total_students // 2 - 1] + sorted_scores[total_students // 2]) / 2
    else:
        median_score = sorted_scores[total_students // 2]
    
    # Standard deviation
    variance = sum((score - average_score) ** 2 for score in scores) / total_students
    standard_deviation = variance ** 0.5
    
    # Pass rate (assuming 50% is passing)
    pass_rate = (sum(1 for score in scores if score >= 50) / total_students) * 100
    
    # Grade distribution
    grade_distribution = {
        'A': sum(1 for score in scores if score >= 80),
        'B': sum(1 for score in scores if 70 <= score < 80),
        'C': sum(1 for score in scores if 60 <= score < 70),
        'D': sum(1 for score in scores if 50 <= score < 60),
        'F': sum(1 for score in scores if score < 50),
    }
    
    # Performance levels
    performance_levels = {
        'excellent': sum(1 for score in scores if score >= 85),
        'good': sum(1 for score in scores if 70 <= score < 85),
        'average': sum(1 for score in scores if 60 <= score < 70),
        'below_average': sum(1 for score in scores if score < 60),
    }
    
    return {
        'total_students': total_students,
        'average_score': float(average_score),
        'highest_score': float(highest_score),
        'lowest_score': float(lowest_score),
        'median_score': float(median_score),
        'standard_deviation': float(standard_deviation),
        'pass_rate': float(pass_rate),
        'grade_distribution': grade_distribution,
        'performance_levels': performance_levels,
    }


def get_percentile_rank(score: float, all_scores: List[float]) -> float:
    """
    Calculate percentile rank for a given score.
    
    Args:
        score: Score to calculate percentile for
        all_scores: List of all scores in the distribution
    
    Returns:
        Percentile rank (0-100)
    """
    if not all_scores:
        return 0
    
    scores_below = sum(1 for s in all_scores if s < score)
    total_scores = len(all_scores)
    
    percentile = (scores_below / total_scores) * 100
    return float(percentile)


def get_mock_exam_summary(student: Student, academic_year: AcademicYear) -> Dict:
    """
    Get comprehensive mock exam summary for a student across all subjects.
    
    Args:
        student: Student instance
        academic_year: AcademicYear instance
    
    Returns:
        Dict containing comprehensive summary
    """
    mock_performances = MockExamPerformance.objects.filter(
        student=student,
        academic_year=academic_year
    ).select_related('class_subject', 'class_subject__subject')
    
    if not mock_performances.exists():
        return {
            'total_mock_exams': 0,
            'subjects_taken': [],
            'overall_average': 0,
            'best_subject': None,
            'weakest_subject': None,
            'improvement_trend': 'no_data',
            'recommendations': ['Take mock exams to track progress'],
        }
    
    # Group by subject
    subject_data = {}
    for mp in mock_performances:
        subject_name = mp.class_subject.subject.subject_name
        if subject_name not in subject_data:
            subject_data[subject_name] = {
                'scores': [],
                'dates': [],
                'trends': [],
                'class_subject': mp.class_subject,
            }
        
        subject_data[subject_name]['scores'].append(mp.scaled_score)
        subject_data[subject_name]['dates'].append(mp.mock_exam_date)
        subject_data[subject_name]['trends'].append(mp.score_trend)
    
    # Calculate subject averages and trends
    subject_summaries = []
    all_scores = []
    
    for subject_name, data in subject_data.items():
        avg_score = sum(data['scores']) / len(data['scores'])
        latest_trend = data['trends'][-1] if data['trends'] else 'unknown'
        
        subject_summaries.append({
            'subject': subject_name,
            'average_score': float(avg_score),
            'mock_count': len(data['scores']),
            'latest_trend': latest_trend,
            'class_subject': data['class_subject'],
        })
        
        all_scores.extend(data['scores'])
    
    # Sort by average score
    subject_summaries.sort(key=lambda x: x['average_score'], reverse=True)
    
    # Calculate overall statistics
    overall_average = sum(all_scores) / len(all_scores) if all_scores else 0
    
    # Determine best and weakest subjects
    best_subject = subject_summaries[0] if subject_summaries else None
    weakest_subject = subject_summaries[-1] if subject_summaries else None
    
    # Overall improvement trend
    improving_subjects = sum(1 for s in subject_summaries if s['latest_trend'] == 'improving')
    declining_subjects = sum(1 for s in subject_summaries if s['latest_trend'] == 'declining')
    
    if improving_subjects > declining_subjects:
        improvement_trend = 'improving'
    elif declining_subjects > improving_subjects:
        improvement_trend = 'declining'
    else:
        improvement_trend = 'stable'
    
    # Generate recommendations
    recommendations = []
    if overall_average >= 80:
        recommendations.append("Excellent overall performance - maintain excellence")
    elif overall_average >= 70:
        recommendations.append("Good performance - focus on reaching excellence")
    elif overall_average >= 60:
        recommendations.append("Average performance - significant improvement possible")
    else:
        recommendations.append("Below average performance - intensive improvement needed")
    
    if weakest_subject:
        recommendations.append(f"Focus on improving {weakest_subject['subject']}")
    
    return {
        'total_mock_exams': len(all_scores),
        'subjects_taken': [s['subject'] for s in subject_summaries],
        'subject_summaries': subject_summaries,
        'overall_average': float(overall_average),
        'best_subject': best_subject,
        'weakest_subject': weakest_subject,
        'improvement_trend': improvement_trend,
        'recommendations': recommendations,
        'total_subjects': len(subject_summaries),
    }

