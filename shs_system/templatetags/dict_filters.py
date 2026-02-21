from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Template filter to get an item from a dictionary using a key.
    Usage: {{ mydict|get_item:key }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key)


@register.filter
def default_if_none(value, default):
    """
    Template filter that returns default if value is None.
    Usage: {{ value|default_if_none:"default_value" }}
    """
    return default if value is None else value
