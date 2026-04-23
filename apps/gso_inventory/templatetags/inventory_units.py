from django import template

from apps.gso_inventory.models import format_quantity_with_uom

register = template.Library()


@register.filter(name='qty_uom')
def qty_uom(quantity, unit_of_measure):
    """Template filter: {{ qty|qty_uom:item.unit_of_measure }}."""
    try:
        qty = int(quantity)
    except (TypeError, ValueError):
        qty = quantity
    return format_quantity_with_uom(qty, unit_of_measure)

