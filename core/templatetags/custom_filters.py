# your_app/templatetags/custom_filters.py

from django import template

register = template.Library()

@register.filter
def sum_list(value, arg):
    return sum(getattr(item, arg) for item in value)
