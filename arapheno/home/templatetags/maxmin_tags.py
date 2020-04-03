from django import template
from django.utils.safestring import mark_safe
import json

register = template.Library()

# Minimum and maximum of a list of PhenotypeValues
@register.filter
def pv_min(l) :
    return min([p.value for p in l])

@register.filter
def pv_max(l) :
    return max([p.value for p in l])

