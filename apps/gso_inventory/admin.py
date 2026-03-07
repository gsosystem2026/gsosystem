from django.contrib import admin
from .models import InventoryItem, InventoryTransaction, MaterialRequest


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'unit', 'category', 'quantity', 'unit_of_measure', 'reorder_level', 'is_low_stock', 'updated_at')
    list_filter = ('unit', 'category')
    search_fields = ('name', 'description', 'category', 'serial_or_asset_number')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('created_by', 'updated_by', 'unit')


@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = ('item', 'transaction_type', 'quantity', 'request', 'performed_by', 'created_at')
    list_filter = ('transaction_type',)
    search_fields = ('notes',)
    raw_id_fields = ('item', 'request', 'performed_by')


@admin.register(MaterialRequest)
class MaterialRequestAdmin(admin.ModelAdmin):
    list_display = ('request', 'item', 'quantity', 'requested_by', 'status', 'approved_by', 'approved_at', 'created_at')
    list_filter = ('status',)
    search_fields = ('notes',)
    raw_id_fields = ('request', 'item', 'requested_by', 'approved_by')
