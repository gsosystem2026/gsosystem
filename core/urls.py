"""
URL configuration for GSO project.
"""
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import path, include
from core import views as core_views


def root_redirect(request):
    """Redirect / to login or role-based dashboard."""
    if request.user.is_authenticated:
        if getattr(request.user, 'is_requestor', False):
            return redirect('gso_accounts:requestor_dashboard')
        return redirect('gso_accounts:staff_dashboard')
    return redirect('gso_accounts:login')


urlpatterns = [
    path('', root_redirect),
    path('service-worker.js', core_views.service_worker_view, name='service_worker'),
    path('manifest.webmanifest', core_views.manifest_view, name='web_manifest'),
    path('offline/', core_views.OfflineFallbackView.as_view(), name='offline_fallback'),
    path('admin/', admin.site.urls),
    path('api/v1/', include('apps.gso_api.urls')),
    path('accounts/social/', include('allauth.urls')),
    path('accounts/', include('apps.gso_accounts.urls')),
    path('accounts/requestor/request/', include('apps.gso_requests.urls')),
]
