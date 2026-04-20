from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import APIRootView, VersionView, UnitViewSet, RequestViewSet, InventoryItemViewSet, UserMeView, UserListView, NotificationViewSet

router = DefaultRouter()
router.register(r'units', UnitViewSet, basename='api-units')
router.register(r'requests', RequestViewSet, basename='api-requests')
router.register(r'inventory', InventoryItemViewSet, basename='api-inventory')
router.register(r'notifications', NotificationViewSet, basename='api-notifications')

urlpatterns = [
    path('', APIRootView.as_view(), name='api-root'),
    path('version/', VersionView.as_view(), name='api-version'),
    path('auth/token/', TokenObtainPairView.as_view(), name='api-token-obtain'),
    path('users/me/', UserMeView.as_view(), name='api-users-me'),
    path('users/', UserListView.as_view(), name='api-users-list'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='api-token-refresh'),
    path('', include(router.urls)),
]
