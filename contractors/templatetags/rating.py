from django import template

register = template.Library()


@register.filter
def stars(value):
    """Turn a number such as 4.3 into ★★★★☆."""
    try:
        count = int(round(float(value)))
    except (TypeError, ValueError):
        return ""
    count = max(0, min(5, count))
    return "★" * count + "☆" * (5 - count)