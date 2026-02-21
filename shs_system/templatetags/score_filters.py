from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Gets an item from a dictionary using the key.
    Usage: {{ my_dict|get_item:key_var }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key)


@register.filter
def divide(value, arg):
    """
    Divides the value by the argument.
    Usage: {{ value|divide:arg }}
    """
    try:
        value = float(value)
        arg = float(arg)
        if arg == 0:
            return 0
        return value / arg
    except (ValueError, TypeError, ZeroDivisionError):
        return 0


@register.filter
def divided_by(value, arg):
    """
    Divides the value by the argument.
    Usage: {{ value|divided_by:arg }}
    """
    try:
        value = float(value)
        arg = float(arg)
        if arg == 0:
            return 0
        return value / arg
    except (ValueError, TypeError, ZeroDivisionError):
        return 0


@register.filter
def multiply(value, arg):
    """
    Multiplies the value by the argument.
    Usage: {{ value|multiply:arg }}
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0
