"""
REST API views for external system integration.
All endpoints require authentication (JWT or session).
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.core.cache import cache
from django.utils import timezone

from apps.gso_accounts.models import User
from apps.gso_requests.models import Request, RequestAssignment
from apps.gso_inventory.models import InventoryItem
from apps.gso_units.models import Unit
from apps.gso_notifications.models import Notification, DeviceToken

from .serializers import (
    UnitSerializer,
    RequestListSerializer,
    RequestDetailSerializer,
    RequestCreateSerializer,
    InventoryItemSerializer,
    UserMeSerializer,
    NotificationSerializer,
)

INSPECTION_REQUIRED_UNIT_CODES = {'repair', 'electrical'}


def _notification_unread_cache_key(user_id):
    return f"notif_unread_count:{user_id}"


def _invalidate_notification_unread_cache(user_id):
    cache.delete(_notification_unread_cache_key(user_id))


def _requires_inspection(request_obj):
    code = ((request_obj.unit.code if request_obj.unit_id else '') or '').lower()
    return code in INSPECTION_REQUIRED_UNIT_CODES


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
        from apps.gso_notifications.utils import notify_request_submitted
        notify_request_submitted(serializer.instance)

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """Unit Head assigns personnel. POST { personnel_ids: [1, 2, 3] }."""
        req = self.get_object()
        user = request.user
        if not getattr(user, 'is_unit_head', False) or user.unit_id != req.unit_id:
            return Response(
                {'detail': 'Only the Unit Head for this request\'s unit can assign personnel.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if req.status not in (Request.Status.SUBMITTED, Request.Status.ASSIGNED):
            return Response(
                {'detail': 'Personnel can only be assigned when status is Submitted or Assigned.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        personnel_ids = request.data.get('personnel_ids') or []
        if not personnel_ids:
            return Response(
                {'detail': 'Select at least one personnel.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        personnel_qs = User.objects.filter(
            role=User.Role.PERSONNEL,
            unit_id=req.unit_id,
            is_active=True,
            pk__in=personnel_ids,
        )
        for personnel in personnel_qs:
            RequestAssignment.objects.get_or_create(
                request=req,
                personnel=personnel,
                defaults={'assigned_by': user},
            )
        if req.status == Request.Status.SUBMITTED:
            req.status = Request.Status.ASSIGNED
            req.save(update_fields=['status', 'updated_at'])
        from apps.gso_notifications.utils import notify_personnel_assigned
        notify_personnel_assigned(req)
        serializer = RequestDetailSerializer(req, context=self.get_serializer_context())
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Director/OIC approves request (status ASSIGNED → DIRECTOR_APPROVED)."""
        req = self.get_object()
        user = request.user
        if not getattr(user, 'can_approve_requests', False):
            return Response(
                {'detail': 'Only the Director or designated OIC can approve.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if req.status != Request.Status.ASSIGNED:
            return Response(
                {'detail': 'Only Assigned requests can be approved.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        req.status = Request.Status.DIRECTOR_APPROVED
        req.save(update_fields=['status', 'updated_at'])
        from apps.gso_notifications.utils import notify_director_approved
        notify_director_approved(req)
        from apps.gso_accounts.models import log_audit
        log_audit('director_approve', user, f'Approved request {req.display_id}', target_model='gso_requests.Request', target_id=str(req.pk))
        serializer = RequestDetailSerializer(req, context=self.get_serializer_context())
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def status(self, request, pk=None):
        """Personnel update work status. POST { status: INSPECTION | IN_PROGRESS | ON_HOLD | DONE_WORKING }."""
        req = self.get_object()
        user = request.user
        if not getattr(user, 'is_personnel', False):
            return Response({'detail': 'Only assigned personnel can update work status.'}, status=status.HTTP_403_FORBIDDEN)
        if not req.assignments.filter(personnel=user).exists():
            return Response({'detail': 'You are not assigned to this request.'}, status=status.HTTP_403_FORBIDDEN)
        new_status = request.data.get('status') or ''
        allowed = (
            Request.Status.INSPECTION,
            Request.Status.IN_PROGRESS,
            Request.Status.ON_HOLD,
            Request.Status.DONE_WORKING,
        )
        if new_status not in allowed:
            return Response({'detail': f'Invalid status. Use one of: {", ".join(allowed)}'}, status=status.HTTP_400_BAD_REQUEST)
        if req.status == Request.Status.DIRECTOR_APPROVED:
            if _requires_inspection(req):
                allowed_from_approved = (Request.Status.INSPECTION, Request.Status.IN_PROGRESS)
                if new_status not in allowed_from_approved:
                    return Response({'detail': 'From Approved you can only set Inspection or In Progress for this unit.'}, status=status.HTTP_400_BAD_REQUEST)
            elif new_status not in (Request.Status.IN_PROGRESS, Request.Status.ON_HOLD):
                return Response({'detail': 'From Approved you can only set In Progress or On Hold.'}, status=status.HTTP_400_BAD_REQUEST)
        if req.status == Request.Status.INSPECTION and new_status not in (Request.Status.IN_PROGRESS, Request.Status.ON_HOLD):
            return Response({'detail': 'From Inspection you can only set In Progress or On Hold.'}, status=status.HTTP_400_BAD_REQUEST)
        if req.status == Request.Status.IN_PROGRESS and new_status not in (Request.Status.ON_HOLD, Request.Status.DONE_WORKING):
            return Response({'detail': 'From In Progress you can only set On Hold or Done working.'}, status=status.HTTP_400_BAD_REQUEST)
        if req.status == Request.Status.ON_HOLD and new_status not in (Request.Status.IN_PROGRESS, Request.Status.DONE_WORKING):
            return Response({'detail': 'From On Hold you can only set In Progress or Done working.'}, status=status.HTTP_400_BAD_REQUEST)
        old_status = req.status
        req.status = new_status
        update_fields = ['status', 'updated_at']
        if new_status == Request.Status.IN_PROGRESS and not req.work_started_at:
            req.work_started_at = timezone.now()
            update_fields.append('work_started_at')
        req.save(update_fields=update_fields)
        from apps.gso_notifications.utils import notify_after_personnel_work_status_change
        notify_after_personnel_work_status_change(req, old_status, new_status)
        serializer = RequestDetailSerializer(req, context=self.get_serializer_context())
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='my-tasks')
    def my_tasks(self, request):
        """Personnel: assigned requests in active work states (matches web Task Management)."""
        user = request.user
        if not getattr(user, 'is_personnel', False):
            return Response({'detail': 'Only personnel can use this endpoint.'}, status=status.HTTP_403_FORBIDDEN)
        qs = (
            Request.objects.filter(
                assignments__personnel=user,
                status__in=(
                    Request.Status.DIRECTOR_APPROVED,
                    Request.Status.INSPECTION,
                    Request.Status.IN_PROGRESS,
                    Request.Status.ON_HOLD,
                    Request.Status.DONE_WORKING,
                ),
            )
            .select_related('unit', 'requestor')
            .prefetch_related('assignments__personnel')
            .distinct()
            .order_by('-updated_at')
        )
        serializer = RequestListSerializer(qs, many=True, context=self.get_serializer_context())
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='my-task-history')
    def my_task_history(self, request):
        """Personnel: assigned requests completed or cancelled."""
        user = request.user
        if not getattr(user, 'is_personnel', False):
            return Response({'detail': 'Only personnel can use this endpoint.'}, status=status.HTTP_403_FORBIDDEN)
        qs = (
            Request.objects.filter(
                assignments__personnel=user,
                status__in=(Request.Status.COMPLETED, Request.Status.CANCELLED),
            )
            .select_related('unit', 'requestor')
            .prefetch_related('assignments__personnel')
            .distinct()
            .order_by('-updated_at')
        )
        serializer = RequestListSerializer(qs, many=True, context=self.get_serializer_context())
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Unit Head marks request complete (status DONE_WORKING → COMPLETED)."""
        req = self.get_object()
        user = request.user
        if not getattr(user, 'is_unit_head', False) or user.unit_id != req.unit_id:
            return Response({'detail': 'Only the Unit Head for this unit can complete.'}, status=status.HTTP_403_FORBIDDEN)
        if req.status != Request.Status.DONE_WORKING:
            return Response({'detail': 'Only Done working requests can be completed.'}, status=status.HTTP_400_BAD_REQUEST)
        req.status = Request.Status.COMPLETED
        req.save(update_fields=['status', 'updated_at'])
        from apps.gso_reports.models import ensure_war_for_request
        ensure_war_for_request(req)
        from apps.gso_notifications.utils import notify_request_completed
        notify_request_completed(req)
        serializer = RequestDetailSerializer(req, context=self.get_serializer_context())
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def return_rework(self, request, pk=None):
        """Unit Head returns request for rework (status DONE_WORKING → IN_PROGRESS)."""
        req = self.get_object()
        user = request.user
        if not getattr(user, 'is_unit_head', False) or user.unit_id != req.unit_id:
            return Response({'detail': 'Only the Unit Head for this unit can return for rework.'}, status=status.HTTP_403_FORBIDDEN)
        if req.status != Request.Status.DONE_WORKING:
            return Response({'detail': 'Only Done working requests can be returned.'}, status=status.HTTP_400_BAD_REQUEST)
        req.status = Request.Status.IN_PROGRESS
        req.save(update_fields=['status', 'updated_at'])
        from apps.gso_notifications.utils import notify_returned_for_rework
        notify_returned_for_rework(req)
        serializer = RequestDetailSerializer(req, context=self.get_serializer_context())
        return Response(serializer.data)


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


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """List notifications for current user. GET /api/v1/notifications/"""
    serializer_class = NotificationSerializer
    throttle_scope = 'user'

    def get_throttles(self):
        if getattr(self, 'action', '') in ('mark_read', 'mark_all_read', 'register_device'):
            self.throttle_scope = 'notification_write'
        else:
            self.throttle_scope = 'user'
        return super().get_throttles()

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Notification.objects.none()
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """GET /api/v1/notifications/unread_count/ - count of unread notifications."""
        if not request.user.is_authenticated:
            return Response({'count': 0})
        cache_key = _notification_unread_cache_key(request.user.id)
        count = cache.get(cache_key)
        if count is None:
            count = Notification.objects.filter(user=request.user, read=False).count()
            # Keep short TTL; creation/read events also invalidate this cache key.
            cache.set(cache_key, count, 10)
        return Response({'count': count})

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """POST /api/v1/notifications/{id}/mark_read/ - mark one as read."""
        notif = self.get_object()
        if notif.user_id != request.user.id:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        notif.read = True
        notif.save(update_fields=['read'])
        _invalidate_notification_unread_cache(request.user.id)
        return Response(NotificationSerializer(notif).data)

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """POST /api/v1/notifications/mark_all_read/ - mark all as read."""
        Notification.objects.filter(user=request.user, read=False).update(read=True)
        _invalidate_notification_unread_cache(request.user.id)
        return Response({'count': 0})

    @action(detail=False, methods=['post'])
    def register_device(self, request):
        """POST /api/v1/notifications/register_device/ - register FCM token for push. Body: {token, platform?}."""
        if not request.user.is_authenticated:
            return Response({'detail': 'Authentication required.'}, status=status.HTTP_401_UNAUTHORIZED)
        token = (request.data.get('token') or '').strip()
        if not token:
            return Response({'detail': 'Token is required.'}, status=status.HTTP_400_BAD_REQUEST)
        platform = request.data.get('platform') or 'unknown'
        obj, _ = DeviceToken.objects.update_or_create(
            user=request.user,
            token=token,
            defaults={'platform': platform},
        )
        return Response({'id': obj.id})


class UserListView(APIView):
    """GET /api/v1/users/?role=personnel&unit={id} — list personnel for a unit (for assign form)."""
    def get(self, request):
        if not request.user.is_authenticated:
            return Response({'detail': 'Authentication required.'}, status=status.HTTP_401_UNAUTHORIZED)
        role = request.query_params.get('role')
        unit_id = request.query_params.get('unit')
        if role != 'personnel' or not unit_id:
            return Response({'detail': 'Requires role=personnel and unit=id.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            unit_id = int(unit_id)
        except ValueError:
            return Response({'detail': 'Invalid unit id.'}, status=status.HTTP_400_BAD_REQUEST)
        user = request.user
        if getattr(user, 'is_unit_head', False) and user.unit_id != unit_id:
            return Response({'detail': 'You can only list personnel for your own unit.'}, status=status.HTTP_403_FORBIDDEN)
        if getattr(user, 'is_gso_office', False) or getattr(user, 'is_director', False):
            pass
        elif not getattr(user, 'is_unit_head', False):
            return Response({'detail': 'Access denied.'}, status=status.HTTP_403_FORBIDDEN)
        qs = User.objects.filter(
            role=User.Role.PERSONNEL,
            unit_id=unit_id,
            is_active=True,
        ).order_by('first_name', 'last_name', 'username')
        data = [{'id': u.id, 'username': u.username, 'first_name': u.first_name, 'last_name': u.last_name} for u in qs]
        return Response(data)


class UserMeView(APIView):
    """GET /api/v1/users/me/ — current authenticated user (id, username, role, unit_id, unit_name)."""
    def get(self, request):
        if not request.user.is_authenticated:
            return Response({'detail': 'Authentication required.'}, status=status.HTTP_401_UNAUTHORIZED)
        serializer = UserMeSerializer(request.user)
        return Response(serializer.data)


class VersionView(APIView):
    """GET /api/v1/version/ — app version check. Returns min_version, current_version, update_required."""
    permission_classes = []
    authentication_classes = []

    def get(self, request):
        from django.conf import settings
        min_version = getattr(settings, 'GSO_APP_MIN_VERSION', '1.0.0')
        return Response({
            'min_version': min_version,
            'message': 'Update available' if min_version != '1.0.0' else None,
        })


class ThrottledTokenObtainPairView(TokenObtainPairView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth_token'


class ThrottledTokenRefreshView(TokenRefreshView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth_refresh'


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
                'users_me': f'{base}/users/me/',
                'units': f'{base}/units/',
                'requests': f'{base}/requests/',
                'inventory': f'{base}/inventory/',
            },
        })
