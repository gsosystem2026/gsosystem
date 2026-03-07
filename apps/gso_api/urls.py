from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import APIRootView, UnitViewSet, RequestViewSet, InventoryItemViewSet

router = DefaultRouter()
router.register(r'units', UnitViewSet, basename='api-units')
router.register(r'requests', RequestViewSet, basename='api-requests')
router.register(r'inventory', InventoryItemViewSet, basename='api-inventory')

urlpatterns = [
    path('', APIRootView.as_view(), name='api-root'),
    path('auth/token/', TokenObtainPairView.as_view(), name='api-token-obtain'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='api-token-refresh'),
    path('', include(router.urls)),
]
