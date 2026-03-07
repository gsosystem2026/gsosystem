from django.contrib import admin
from .models import Request, RequestFeedback


@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    list_display = ('display_id', 'title', 'unit', 'requestor', 'status', 'is_emergency', 'created_at')
    list_filter = ('status', 'unit', 'is_emergency')
    search_fields = ('title', 'description')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('requestor',)


@admin.register(RequestFeedback)
class RequestFeedbackAdmin(admin.ModelAdmin):
    list_display = ('request', 'user', 'rating', 'created_at')
    list_filter = ('rating',)
    search_fields = ('request__display_id', 'user__username')
    readonly_fields = ('created_at',)
    raw_id_fields = ('request', 'user')
