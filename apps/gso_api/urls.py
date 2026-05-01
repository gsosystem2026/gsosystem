from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    APIRootView,
    VersionView,
    UnitViewSet,
    RequestViewSet,
    InventoryItemViewSet,
    UserMeView,
    UserPasswordChangeView,
    UserListView,
    NotificationViewSet,
    ThrottledTokenObtainPairView,
    ThrottledTokenRefreshView,
)

router = DefaultRouter()
router.register(r'units', UnitViewSet, basename='api-units')
router.register(r'requests', RequestViewSet, basename='api-requests')
router.register(r'inventory', InventoryItemViewSet, basename='api-inventory')
router.register(r'notifications', NotificationViewSet, basename='api-notifications')

urlpatterns = [
    path('', APIRootView.as_view(), name='api-root'),
    path('version/', VersionView.as_view(), name='api-version'),
    path('auth/token/', ThrottledTokenObtainPairView.as_view(), name='api-token-obtain'),
    path('users/me/', UserMeView.as_view(), name='api-users-me'),
    path('users/change-password/', UserPasswordChangeView.as_view(), name='api-users-change-password'),
    path('users/', UserListView.as_view(), name='api-users-list'),
    path('auth/token/refresh/', ThrottledTokenRefreshView.as_view(), name='api-token-refresh'),
    path('', include(router.urls)),
]
