"""
URL configuration for GSO project.
"""
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import path, include


def root_redirect(request):
    """Redirect / to login or role-based dashboard."""
    if request.user.is_authenticated:
        if getattr(request.user, 'is_requestor', False):
            return redirect('gso_accounts:requestor_dashboard')
        return redirect('gso_accounts:staff_dashboard')
    return redirect('gso_accounts:login')


urlpatterns = [
    path('', root_redirect),
    path('admin/', admin.site.urls),
    path('api/v1/', include('apps.gso_api.urls')),
    path('accounts/', include('apps.gso_accounts.urls')),
    path('accounts/requestor/request/', include('apps.gso_requests.urls')),
]
