from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Get an item from a dictionary using its key.
    This is useful when the key needs to be a variable.

    Usage in templates:
    {{ my_dict|get_item:my_key }}
    """
    if dictionary is None:
        return None

    # Try different ways to access the key - sometimes keys are strings, sometimes integers
    if isinstance(key, str) and key.isdigit():
        # If it's a string that looks like a number, try both ways
        return dictionary.get(key) or dictionary.get(int(key)) or None
    else:
        # Otherwise just return the direct lookup or None
        return dictionary.get(key)


@register.filter(name="addclass")
def addclass(field, css_class):
    """Add a CSS class to a form field"""
    return field.as_widget(attrs={"class": css_class})


@register.filter
def avg_score(score_data, subject_name):
    """
    Calculate average score for a specific subject across all students.
    """
    if not score_data:
        return 0

    total_score = 0
    valid_scores = 0

    for student_data in score_data:
        subject_data = student_data.get("subjects", {}).get(subject_name, {})
        score = subject_data.get("score", 0)
        if score > 0:
            total_score += score
            valid_scores += 1

    return total_score / valid_scores if valid_scores > 0 else 0


@register.filter
def avg_total_score(score_data):
    """
    Calculate average total score across all students.
    """
    if not score_data:
        return 0

    total_score = 0
    valid_scores = 0

    for student_data in score_data:
        avg_score = student_data.get("average_score", 0)
        if avg_score > 0:
            total_score += avg_score
            valid_scores += 1

    return total_score / valid_scores if valid_scores > 0 else 0


@register.filter
def get_grade_class(grade):
    """
    Get CSS class for grade styling.
    """
    if not grade or grade == "N/A":
        return "grade-N/A"

    grade_letter = str(grade).upper()
    if grade_letter in ["A", "A+", "A-"]:
        return "grade-A"
    elif grade_letter in ["B", "B+", "B-"]:
        return "grade-B"
    elif grade_letter in ["C", "C+", "C-"]:
        return "grade-C"
    elif grade_letter in ["D", "D+", "D-"]:
        return "grade-D"
    elif grade_letter in ["F"]:
        return "grade-F"
    else:
        return "grade-N/A"
