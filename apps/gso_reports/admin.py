from django.contrib import admin
from .models import SuccessIndicator, WorkAccomplishmentReport, IPMTDraft


@admin.register(SuccessIndicator)
class SuccessIndicatorAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'target_position', 'target_unit', 'display_order', 'is_active')
    list_editable = ('display_order', 'is_active')
    list_filter = ('target_unit', 'target_position', 'is_active')
    search_fields = ('code', 'name', 'description', 'target_position')
    ordering = ('display_order', 'code')


@admin.register(WorkAccomplishmentReport)
class WorkAccomplishmentReportAdmin(admin.ModelAdmin):
    list_display = ('request', 'personnel', 'period_start', 'period_end', 'summary', 'created_at')
    list_filter = ('period_end',)
    search_fields = ('summary', 'accomplishments', 'request__title')
    raw_id_fields = ('request', 'personnel', 'created_by')
    filter_horizontal = ('success_indicators',)
    date_hierarchy = 'period_end'


@admin.register(IPMTDraft)
class IPMTDraftAdmin(admin.ModelAdmin):
    list_display = ('personnel', 'year', 'month', 'updated_by', 'updated_at')
    list_filter = ('year', 'month')
    search_fields = ('personnel__username', 'personnel__first_name', 'personnel__last_name')
    raw_id_fields = ('personnel', 'updated_by')
