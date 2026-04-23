from django.conf import settings
from django.db import models


def format_quantity_with_uom(quantity, unit_of_measure):
    """
    Return a human-friendly quantity + unit label.
    Examples: 1 pc, 2 pcs, 1 liter, 3 liters.
    """
    uom = (unit_of_measure or '').strip().lower()
    singular_map = {
        'pcs': 'pc',
        'box': 'box',
        'set': 'set',
        'roll': 'roll',
        'liters': 'liter',
        'meters': 'meter',
    }
    plural_map = {
        'pcs': 'pcs',
        'box': 'boxes',
        'set': 'sets',
        'roll': 'rolls',
        'liters': 'liters',
        'meters': 'meters',
    }
    if quantity == 1:
        label = singular_map.get(uom, unit_of_measure or 'unit')
    else:
        label = plural_map.get(uom, unit_of_measure or 'units')
    return f'{quantity} {label}'


class InventoryItem(models.Model):
    """Inventory item tied to a unit (Phase 3.1). Unit Heads manage their unit's items; GSO/Director see all."""

    unit = models.ForeignKey(
        'gso_units.Unit',
        on_delete=models.PROTECT,
        related_name='inventory_items',
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=120, blank=True, help_text='Category or type of item')
    quantity = models.PositiveIntegerField(default=0)
    unit_of_measure = models.CharField(
        max_length=50,
        default='pcs',
        help_text='e.g. pcs, box, set, roll',
    )
    reorder_level = models.PositiveIntegerField(
        default=0,
        blank=True,
        help_text='Reorder when quantity falls at or below this level',
    )
    arrival_date = models.DateField(
        null=True,
        blank=True,
        help_text='Most recent date this item arrived (updated on stock-in).',
    )
    location = models.CharField(max_length=255, blank=True, help_text='Storage location or remarks')
    serial_or_asset_number = models.CharField(max_length=120, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventory_items_created',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventory_items_updated',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['unit', 'name']
        verbose_name = 'inventory item'
        verbose_name_plural = 'inventory items'

    def __str__(self):
        return f"{self.name} ({self.unit.name})"

    @property
    def is_low_stock(self):
        """True if quantity is at or below reorder level."""
        return self.reorder_level > 0 and self.quantity <= self.reorder_level

    @property
    def quantity_display(self):
        """Human-friendly stock text (singular/plural aware)."""
        return format_quantity_with_uom(self.quantity, self.unit_of_measure)


class InventoryTransaction(models.Model):
    """Stock movement log: in/out; optional link to a request when issued for a job (Phase 3.1 optional)."""

    class TransactionType(models.TextChoices):
        IN = 'IN', 'In'
        OUT = 'OUT', 'Out'
        ADJUST = 'ADJUST', 'Adjustment'

    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.CASCADE,
        related_name='transactions',
    )
    transaction_type = models.CharField(max_length=10, choices=TransactionType.choices)
    quantity = models.PositiveIntegerField(help_text='Quantity added (IN) or removed (OUT)')
    request = models.ForeignKey(
        'gso_requests.Request',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventory_issues',
    )
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventory_transactions',
    )
    notes = models.CharField(max_length=500, blank=True)
    arrival_date = models.DateField(
        null=True,
        blank=True,
        help_text='Date this stock batch arrived (for stock-in).',
    )
    supplier_name = models.CharField(max_length=255, blank=True)
    delivery_reference = models.CharField(max_length=120, blank=True, help_text='DR/PO/reference number')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'inventory transaction'
        verbose_name_plural = 'inventory transactions'

    def __str__(self):
        return f"{self.get_transaction_type_display()} {self.quantity} x {self.item.name}"


class MaterialRequest(models.Model):
    """Personnel request for materials on a request; inventory is deducted only when Unit Head approves."""

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    request = models.ForeignKey(
        'gso_requests.Request',
        on_delete=models.CASCADE,
        related_name='material_requests',
    )
    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT,
        related_name='material_requests',
    )
    quantity = models.PositiveIntegerField()
    notes = models.CharField(max_length=500, blank=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='material_requests_made',
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='material_requests_approved',
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'material request'
        verbose_name_plural = 'material requests'

    def __str__(self):
        return f"{self.item.name} x {self.quantity} ({self.get_status_display()})"
