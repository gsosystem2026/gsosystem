"""
REST API views for external system integration.
All endpoints require authentication (JWT or session).
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.gso_requests.models import Request
from apps.gso_inventory.models import InventoryItem
from apps.gso_units.models import Unit

from .serializers import (
    UnitSerializer,
    RequestListSerializer,
    RequestDetailSerializer,
    RequestCreateSerializer,
    InventoryItemSerializer,
)


def _filter_requests_queryset(queryset, request):
    """Apply query params: unit, status, search."""
    unit_id = request.query_params.get('unit')
    if unit_id:
        queryset = queryset.filter(unit_id=unit_id)
    status_filter = request.query_params.get('status')
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    q = request.query_params.get('q', '').strip()
    if q:
        from django.db.models import Q
        q_filter = Q(title__icontains=q) | Q(description__icontains=q)
        if q.isdigit():
            q_filter |= Q(pk=int(q))
        queryset = queryset.filter(q_filter)
    return queryset


class UnitViewSet(viewsets.ReadOnlyModelViewSet):
    """List and retrieve service units (read-only). Public (no auth) so integrators can get unit IDs."""
    queryset = Unit.objects.filter(is_active=True).order_by('name')
    serializer_class = UnitSerializer
    permission_classes = [AllowAny]
    authentication_classes = []  # no auth required for list or retrieve


class RequestViewSet(viewsets.ModelViewSet):
    """List, retrieve, and create requests. Filter by unit, status, search."""
    queryset = Request.objects.select_related('unit', 'requestor').prefetch_related('assignments__personnel').order_by('-created_at')

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user.is_authenticated:
            return qs.none()
        if getattr(user, 'is_unit_head', False) and user.unit_id:
            qs = qs.filter(unit_id=user.unit_id)
        elif getattr(user, 'is_personnel', False):
            qs = qs.filter(assignments__personnel=user).distinct()
        elif not (getattr(user, 'is_gso_office', False) or getattr(user, 'is_director', False)):
            qs = qs.filter(requestor=user)
        return _filter_requests_queryset(qs, self.request)

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return RequestDetailSerializer
        if self.action == 'create':
            return RequestCreateSerializer
        return RequestListSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def create(self, request, *args, **kwargs):
        """Create a new request (submitted on behalf of authenticated user)."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        obj = serializer.instance
        return Response(
            RequestDetailSerializer(obj, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

    def perform_create(self, serializer):
        serializer.save()


class InventoryItemViewSet(viewsets.ReadOnlyModelViewSet):
    """List and retrieve inventory items. Scoped by role (unit or all)."""
    serializer_class = InventoryItemSerializer

    def get_queryset(self):
        from apps.gso_inventory.views import user_can_manage_all_units
        user = self.request.user
        qs = InventoryItem.objects.select_related('unit').order_by('unit__name', 'name')
        if user_can_manage_all_units(user):
            unit_id = self.request.query_params.get('unit')
            if unit_id:
                qs = qs.filter(unit_id=unit_id)
        else:
            if getattr(user, 'unit_id', None):
                qs = qs.filter(unit_id=user.unit_id)
            else:
                qs = qs.none()
        return qs


class APIRootView(APIView):
    """API info and links to main resources."""
    permission_classes = []
    authentication_classes = []

    def get(self, request):
        base = request.build_absolute_uri('/api/v1/').rstrip('/')
        return Response({
            'name': 'GSO Request Management API',
            'version': '1.0',
            'auth': 'Use POST /api/v1/auth/token/ with username and password to get access and refresh tokens.',
            'endpoints': {
                'auth_token': f'{base}/auth/token/',
                'auth_refresh': f'{base}/auth/token/refresh/',
                'units': f'{base}/units/',
                'requests': f'{base}/requests/',
                'inventory': f'{base}/inventory/',
            },
        })
