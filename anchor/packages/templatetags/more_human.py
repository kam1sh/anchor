import humanize
from django import template

register = template.Library()


@register.filter
def naturalsize(value: int):
    return humanize.naturalsize(value)
