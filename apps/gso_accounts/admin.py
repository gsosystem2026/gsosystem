from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User, AuditLog


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'get_full_name', 'role', 'unit', 'is_staff', 'is_active')
    list_filter = ('role', 'unit', 'is_staff', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('username',)
    filter_horizontal = ('groups', 'user_permissions')

    fieldsets = BaseUserAdmin.fieldsets + (
        ('GSO', {'fields': ('role', 'unit')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('GSO', {'fields': ('role', 'unit')}),
    )


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'user', 'message', 'target_model', 'target_id', 'created_at')
    list_filter = ('action',)
    search_fields = ('message', 'action')
    readonly_fields = ('user', 'action', 'message', 'target_model', 'target_id', 'created_at')
    date_hierarchy = 'created_at'
