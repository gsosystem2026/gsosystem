from django.contrib import admin
from .models import SuccessIndicator, WorkAccomplishmentReport


@admin.register(SuccessIndicator)
class SuccessIndicatorAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'display_order', 'is_active')
    list_editable = ('display_order', 'is_active')
    search_fields = ('code', 'name', 'description')
    ordering = ('display_order', 'code')


@admin.register(WorkAccomplishmentReport)
class WorkAccomplishmentReportAdmin(admin.ModelAdmin):
    list_display = ('request', 'personnel', 'period_start', 'period_end', 'summary', 'created_at')
    list_filter = ('period_end',)
    search_fields = ('summary', 'accomplishments', 'request__title')
    raw_id_fields = ('request', 'personnel', 'created_by')
    filter_horizontal = ('success_indicators',)
    date_hierarchy = 'period_end'
