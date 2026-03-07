from django.conf import settings
from django.db import models


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
