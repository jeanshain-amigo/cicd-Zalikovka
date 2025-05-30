from django import template

register = template.Library()

@register.filter
def lookup(sequence, index):
    """
    Returns the item at the specified index in a sequence.
    """
    try:
        return sequence[int(index)]
    except (IndexError, TypeError, ValueError):
        return None

@register.filter
def attr(obj, attr_name):
    """
    Returns the value of the specified attribute of an object.
    """
    try:
        return getattr(obj, attr_name)
    except AttributeError:
        return None