from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from django.core.mail import send_mail
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import TemplateView, UpdateView, View, ListView, CreateView, FormView
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.utils import timezone
from django.template.loader import render_to_string
from datetime import timedelta
import secrets
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

from .forms import GsoAuthenticationForm, GsoPasswordResetForm, GsoPasswordResetOTPForm, GsoSetPasswordForm, RequestorProfileForm, DirectorUserCreateForm, DirectorUserEditForm
from .models import User, PasswordResetOTP
from apps.gso_requests.models import Request

# Lazy import to avoid circular import
def _requestor_request_list(user):
    from apps.gso_requests.models import Request
    return Request.objects.filter(requestor=user).order_by('-created_at')[:100]


def app_version_view(request):
    """Phase 8.3: Return current app version (JSON) for 'new version available' check. No auth required."""
    return JsonResponse({'version': getattr(settings, 'GSO_APP_VERSION', '1.0')})


class GsoLoginView(LoginView):
    """Login with role-based redirect: Requestor -> requestor dashboard, others -> staff dashboard."""
    form_class = GsoAuthenticationForm
    template_name = 'registration/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        user = self.request.user
        if isinstance(user, User) and user.is_requestor:
            return reverse_lazy('gso_accounts:requestor_dashboard')
        return reverse_lazy('gso_accounts:staff_dashboard')


class GsoLogoutView(LogoutView):
    """Logout; redirect to login page. Must use POST (form with csrf_token in template)."""
    next_page = reverse_lazy('gso_accounts:login')


class StaffRequiredMixin:
    """Redirect to login or requestor dashboard if user is not staff. Use as first base for staff views."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('gso_accounts:login')
        if hasattr(request.user, 'is_requestor') and request.user.is_requestor:
            return redirect('gso_accounts:requestor_dashboard')
        return super().dispatch(request, *args, **kwargs)


class StaffDashboardView(StaffRequiredMixin, TemplateView):
    """Dashboard for Unit Head, Personnel, GSO Office, Director (staff layout with sidebar)."""
    template_name = 'staff/dashboard.html'

    def get_context_data(self, **kwargs):
        from django.db.models import F, Case, When, IntegerField
        from apps.gso_requests.models import Request, RequestAssignment
        from apps.gso_units.models import Unit
        from apps.gso_accounts.models import AuditLog

        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['show_director_dashboard'] = getattr(user, 'is_director', False) or getattr(user, 'is_gso_office', False)
        context['show_unit_head_dashboard'] = getattr(user, 'is_unit_head', False) and bool(getattr(user, 'unit_id', None))
        context['show_personnel_dashboard'] = getattr(user, 'is_personnel', False)

        # Pending approvals (ASSIGNED) for users who can approve
        if getattr(user, 'can_approve_requests', False):
            pending_qs = Request.objects.filter(
                status=Request.Status.ASSIGNED
            ).select_related('unit').prefetch_related('assignments__personnel').order_by('-is_emergency', '-created_at')[:10]
            context['pending_approvals'] = list(pending_qs)
            context['pending_approvals_count'] = Request.objects.filter(status=Request.Status.ASSIGNED).count()
        else:
            context['pending_approvals'] = []
            context['pending_approvals_count'] = 0

        # Total requests (all) and total active (exclude completed/cancelled)
        request_qs = Request.objects.all()
        if getattr(user, 'is_unit_head', False) and user.unit_id:
            request_qs = request_qs.filter(unit_id=user.unit_id)
        elif getattr(user, 'is_personnel', False):
            request_qs = request_qs.filter(assignments__personnel=user).distinct()
        context['total_requests'] = request_qs.count()
        context['total_active_requests'] = request_qs.exclude(
            status__in=(Request.Status.COMPLETED, Request.Status.CANCELLED)
        ).count()
        # New requests in the last 7 days (for dashboard trend badge)
        try:
            recent_start = timezone.now() - timedelta(days=7)
            context['new_requests_last_7_days'] = request_qs.filter(created_at__gte=recent_start).count()
        except Exception:
            context['new_requests_last_7_days'] = 0

        # Inventory alerts (low stock) — Director/GSO see all; Unit Head their unit
        try:
            from apps.gso_inventory.models import InventoryItem
            inv_qs = InventoryItem.objects.all()
            if getattr(user, 'is_unit_head', False) and user.unit_id:
                inv_qs = inv_qs.filter(unit_id=user.unit_id)
            context['inventory_alerts_count'] = inv_qs.filter(reorder_level__gt=0).filter(
                quantity__lte=F('reorder_level')
            ).count()
        except Exception:
            context['inventory_alerts_count'] = 0

        # Unit performance (completion rate per unit) and active unit count — for Director/GSO only
        if context['show_director_dashboard']:
            units = Unit.objects.filter(is_active=True).order_by('name')
            per_unit = []
            total_pct = 0
            for u in units:
                total = Request.objects.filter(unit=u).exclude(status=Request.Status.CANCELLED).count()
                completed = Request.objects.filter(unit=u, status=Request.Status.COMPLETED).count()
                pct = round(100 * completed / total) if total else 0
                per_unit.append({'unit': u, 'percent': pct})
                total_pct += pct
            context['unit_performance'] = per_unit
            context['unit_performance_avg'] = round(total_pct / len(per_unit)) if per_unit else 0
            context['active_units_count'] = units.count()
        else:
            context['unit_performance'] = []
            context['unit_performance_avg'] = 0
            context['active_units_count'] = 0

        # Unit Head dashboard: request management overview, unit overview, inventory overview
        if context.get('show_unit_head_dashboard') and user.unit_id:
            unit_reqs = Request.objects.filter(unit_id=user.unit_id)
            context['unit_head_unit'] = getattr(user, 'unit', None)
            pending_submitted = unit_reqs.filter(status=Request.Status.SUBMITTED)
            context['unit_head_pending_assign_count'] = pending_submitted.count()
            context['unit_head_pending_assign'] = list(
                pending_submitted.select_related('unit').prefetch_related('assignments__personnel').order_by('-is_emergency', '-created_at')[:10]
            )
            total_unit = unit_reqs.exclude(status=Request.Status.CANCELLED).count()
            completed_unit = unit_reqs.filter(status=Request.Status.COMPLETED).count()
            context['unit_head_performance_percent'] = round(100 * completed_unit / total_unit) if total_unit else 0
            try:
                from apps.gso_inventory.models import InventoryItem
                context['unit_head_inventory_total'] = InventoryItem.objects.filter(unit_id=user.unit_id).count()
            except Exception:
                context['unit_head_inventory_total'] = 0
        else:
            context['unit_head_unit'] = None
            context['unit_head_pending_assign'] = []
            context['unit_head_pending_assign_count'] = 0
            context['unit_head_performance_percent'] = 0
            context['unit_head_inventory_total'] = 0

        # Personnel dashboard: requests assigned to this user (show those first)
        if context.get('show_personnel_dashboard'):
            personnel_reqs = Request.objects.filter(assignments__personnel=user).distinct()
            # Order: Work to be done first (Assigned, Director Approved, In Progress), then Done working, COMPLETED last
            status_order = Case(
                When(status=Request.Status.ASSIGNED, then=1),
                When(status=Request.Status.DIRECTOR_APPROVED, then=2),
                When(status=Request.Status.INSPECTION, then=3),
                When(status=Request.Status.IN_PROGRESS, then=4),
                When(status=Request.Status.DONE_WORKING, then=5),
                When(status=Request.Status.COMPLETED, then=999),
                When(status=Request.Status.CANCELLED, then=999),
                default=6,
                output_field=IntegerField(),
            )
            context['personnel_assigned_requests'] = list(
                personnel_reqs.select_related('unit')
                .prefetch_related('assignments__personnel')
                .order_by(status_order, '-created_at')[:5]
            )
            context['personnel_assigned_total'] = personnel_reqs.count()
            context['personnel_in_progress_count'] = personnel_reqs.filter(status=Request.Status.IN_PROGRESS).count()
            context['personnel_completed_count'] = personnel_reqs.filter(status=Request.Status.COMPLETED).count()
            context['personnel_active_count'] = personnel_reqs.exclude(
                status__in=(Request.Status.COMPLETED, Request.Status.CANCELLED)
            ).count()
        else:
            context['personnel_assigned_requests'] = []
            context['personnel_assigned_total'] = 0
            context['personnel_in_progress_count'] = 0
            context['personnel_completed_count'] = 0
            context['personnel_active_count'] = 0

        # Recent activity: Director sees all logs (to know who did what); GSO Office sees only their own
        try:
            if getattr(user, 'is_director', False):
                context['recent_activity'] = list(
                    AuditLog.objects.all().select_related('user').order_by('-created_at')[:5]
                )
                context['recent_activity_show_all'] = True  # show "by [user]" and link to full Activity Log page
            else:
                context['recent_activity'] = list(
                    AuditLog.objects.filter(user=user).select_related('user').order_by('-created_at')[:5]
                )
                context['recent_activity_show_all'] = False
        except Exception:
            context['recent_activity'] = []
            context['recent_activity_show_all'] = False

        # For the briefing card: Director/OIC see "Director's Briefing" with pending approvals; GSO Office sees "Quick Actions"
        context['user_can_approve'] = getattr(user, 'can_approve_requests', False)

        return context


class StaffDashboardPendingRequestsView(StaffRequiredMixin, TemplateView):
    """Returns only the Pending Requests Overview table fragment for dashboard AJAX polling."""
    template_name = 'staff/dashboard_pending_requests_partial.html'

    def get_context_data(self, **kwargs):
        from apps.gso_requests.models import Request
        context = super().get_context_data(**kwargs)
        user = self.request.user
        if getattr(user, 'is_unit_head', False) and user.unit_id:
            pending_submitted = Request.objects.filter(
                unit_id=user.unit_id,
                status=Request.Status.SUBMITTED,
            )
            context['unit_head_pending_assign'] = list(
                pending_submitted.select_related('unit')
                .prefetch_related('assignments__personnel')
                .order_by('-is_emergency', '-created_at')[:10]
            )
        else:
            context['unit_head_pending_assign'] = []
        return context


class StaffActivityLogView(StaffRequiredMixin, ListView):
    """Director only: activity log (system audit) and inventory logs in one place. Filter by log type to switch table."""
    template_name = 'staff/activity_log.html'
    context_object_name = 'activity_list'
    paginate_by = 25

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('gso_accounts:login')
        if hasattr(request.user, 'is_requestor') and request.user.is_requestor:
            return redirect('gso_accounts:requestor_dashboard')
        if not getattr(request.user, 'is_director', False):
            messages.info(request, 'Activity Log is available to the Director only.')
            return redirect('gso_accounts:staff_dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        log_type = self.request.GET.get('log_type', '').strip()
        if log_type == 'inventory':
            from apps.gso_inventory.models import InventoryTransaction
            qs = (
                InventoryTransaction.objects
                .select_related('item', 'item__unit', 'performed_by', 'request')
                .order_by('-created_at')
            )
            unit_id = self.request.GET.get('unit', '').strip()
            if unit_id and unit_id.isdigit():
                qs = qs.filter(item__unit_id=int(unit_id))
            trans_type = self.request.GET.get('type', '').strip()
            if trans_type and trans_type in ('IN', 'OUT', 'ADJUST'):
                qs = qs.filter(transaction_type=trans_type)
            date_from = self.request.GET.get('date_from', '').strip()
            if date_from:
                qs = qs.filter(created_at__date__gte=date_from)
            date_to = self.request.GET.get('date_to', '').strip()
            if date_to:
                qs = qs.filter(created_at__date__lte=date_to)
            return qs
        from .models import AuditLog
        qs = AuditLog.objects.all().select_related('user').order_by('-created_at')
        user_id = self.request.GET.get('user')
        if user_id:
            qs = qs.filter(user_id=user_id)
        action = self.request.GET.get('action', '').strip()
        if action:
            qs = qs.filter(action=action)
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(Q(message__icontains=q) | Q(action__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        from apps.gso_units.models import Unit
        context = super().get_context_data(**kwargs)
        context['log_type'] = self.request.GET.get('log_type', '').strip()
        context['page_title'] = 'Activity Log'
        context['page_description'] = 'View system activity (approvals, users) or inventory movements (stock in/out). Use "Log type" to switch.'
        context['filter_user'] = self.request.GET.get('user', '')
        context['filter_action'] = self.request.GET.get('action', '')
        context['filter_q'] = self.request.GET.get('q', '')
        context['action_choices'] = [
            ('', 'All actions'),
            ('director_approve', 'Request Approved'),
            ('oic_assign', 'OIC Assigned'),
            ('oic_revoke', 'OIC Revoked'),
            ('user_create', 'User Created'),
            ('user_edit', 'User Edited'),
            ('requestor_edit_request', 'Requestor Edited Request'),
            ('requestor_cancel_request', 'Requestor Cancelled Request'),
        ]
        context['users_with_logs'] = User.objects.filter(
            audit_logs__isnull=False
        ).distinct().order_by('first_name', 'last_name', 'username')
        # Inventory log filters (when log_type=inventory)
        context['units'] = Unit.objects.filter(is_active=True).order_by('name')
        context['filter_unit'] = self.request.GET.get('unit', '')
        context['filter_type'] = self.request.GET.get('type', '')
        context['filter_date_from'] = self.request.GET.get('date_from', '')
        context['filter_date_to'] = self.request.GET.get('date_to', '')
        context['inventory_type_choices'] = [
            ('', 'All types'),
            ('IN', 'In'),
            ('OUT', 'Out'),
            ('ADJUST', 'Adjustment'),
        ]
        return context


class UnitHeadInventoryActivityLogView(StaffRequiredMixin, ListView):
    """Unit Head only: inventory activity log for their own unit (stock in/out/adjust)."""
    template_name = 'staff/inventory_activity_log.html'
    context_object_name = 'activity_list'
    paginate_by = 25

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('gso_accounts:login')
        if getattr(request.user, 'is_requestor', False):
            return redirect('gso_accounts:requestor_dashboard')
        if not getattr(request.user, 'is_unit_head', False) or not request.user.unit_id:
            messages.info(request, 'Inventory Activity Log is available to Unit Heads for their unit only.')
            return redirect('gso_accounts:staff_dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        from apps.gso_inventory.models import InventoryTransaction
        unit_id = self.request.user.unit_id
        # Only transactions on this unit's items AND performed by someone in this unit (or no performer)
        qs = (
            InventoryTransaction.objects
            .filter(item__unit_id=unit_id)
            .filter(Q(performed_by__unit_id=unit_id) | Q(performed_by__isnull=True))
            .select_related('item', 'item__unit', 'performed_by', 'request')
            .order_by('-created_at')
        )
        trans_type = self.request.GET.get('type', '').strip()
        if trans_type and trans_type in ('IN', 'OUT', 'ADJUST'):
            qs = qs.filter(transaction_type=trans_type)
        date_from = self.request.GET.get('date_from', '').strip()
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        date_to = self.request.GET.get('date_to', '').strip()
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Inventory Activity Log'
        context['page_description'] = 'Stock movements (in, out, adjustments) for your unit\'s inventory.'
        context['filter_type'] = self.request.GET.get('type', '')
        context['filter_date_from'] = self.request.GET.get('date_from', '')
        context['filter_date_to'] = self.request.GET.get('date_to', '')
        context['inventory_type_choices'] = [
            ('', 'All types'),
            ('IN', 'In'),
            ('OUT', 'Out'),
            ('ADJUST', 'Adjustment'),
        ]
        context['unit_name'] = getattr(self.request.user.unit, 'name', 'Your unit') if self.request.user.unit_id else 'Your unit'
        return context


class StaffPlaceholderView(StaffRequiredMixin, TemplateView):
    """Placeholder page for staff sidebar links. Subclass and set page_title (and optional page_description)."""
    template_name = 'staff/placeholder.html'
    page_title = 'Page'
    page_description = 'This page is a placeholder. Content will be added here.'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = self.page_title
        context['page_description'] = self.page_description
        return context


class StaffRequestManagementView(StaffPlaceholderView):
    page_title = 'Request Management'
    page_description = 'Assign and manage incoming service requests.'


class StaffRequestHistoryView(StaffRequiredMixin, ListView):
    """Unit Head: their unit's history. Director/GSO: all units with optional unit filter."""
    model = Request
    template_name = 'staff/request_history.html'
    context_object_name = 'request_list'
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            return redirect('gso_accounts:login')
        if getattr(user, 'is_unit_head', False) and user.unit_id:
            return super().dispatch(request, *args, **kwargs)
        if getattr(user, 'is_gso_office', False) or getattr(user, 'is_director', False):
            return super().dispatch(request, *args, **kwargs)
        messages.info(request, 'Request History is for Unit Heads, GSO Office, and Director.')
        return redirect('gso_accounts:staff_dashboard')

    def get_queryset(self):
        user = self.request.user
        qs = Request.objects.none()
        if getattr(user, 'is_unit_head', False) and user.unit_id:
            qs = Request.objects.filter(
                unit_id=user.unit_id,
                status__in=(Request.Status.COMPLETED, Request.Status.CANCELLED),
            )
        elif getattr(user, 'is_personnel', False) and user.unit_id:
            qs = Request.objects.filter(
                unit_id=user.unit_id,
                status__in=(Request.Status.COMPLETED, Request.Status.CANCELLED),
            )
        elif getattr(user, 'is_gso_office', False) or getattr(user, 'is_director', False):
            qs = Request.objects.filter(
                status__in=(Request.Status.COMPLETED, Request.Status.CANCELLED),
            )
            unit_id = self.request.GET.get('unit', '').strip()
            if unit_id and unit_id.isdigit():
                qs = qs.filter(unit_id=int(unit_id))
        # Optional filter by status (Completed / Cancelled)
        status = self.request.GET.get('status', '').strip()
        if status:
            qs = qs.filter(status=status)
        # Search by ID, purpose, location, requestor, unit
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(title__icontains=q)
                | Q(description__icontains=q)
                | Q(location__icontains=q)
                | Q(unit__name__icontains=q)
                | Q(requestor__first_name__icontains=q)
                | Q(requestor__last_name__icontains=q)
                | Q(requestor__username__icontains=q)
                | Q(pk__icontains=q)
            )
        return qs.select_related('unit', 'requestor').prefetch_related('work_accomplishment_reports').order_by('-created_at')

    def get_context_data(self, **kwargs):
        from apps.gso_units.models import Unit
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['page_title'] = 'Request History'
        context['show_unit_filter'] = getattr(user, 'is_gso_office', False) or getattr(user, 'is_director', False)
        if context['show_unit_filter']:
            context['page_description'] = 'Completed and cancelled requests across all units. Filter by unit below.'
            context['units'] = Unit.objects.filter(is_active=True).order_by('name')
            context['unit_filter'] = self.request.GET.get('unit', '')
        else:
            context['page_description'] = 'Completed and cancelled requests for your unit.'
            context['units'] = []
            context['unit_filter'] = ''
        context['status_filter'] = self.request.GET.get('status', '')
        context['search_q'] = self.request.GET.get('q', '')
        context['status_choices'] = [
            (Request.Status.COMPLETED, 'Completed'),
            (Request.Status.CANCELLED, 'Cancelled'),
        ]
        return context


class StaffPersonnelManagementView(StaffRequiredMixin, TemplateView):
    """Unit Head: view personnel in own unit and their active workload."""
    template_name = 'staff/personnel_management.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('gso_accounts:login')
        if not getattr(request.user, 'is_unit_head', False) or not request.user.unit_id:
            messages.info(request, 'Personnel Management is available to Unit Heads only.')
            return redirect('gso_accounts:staff_dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['page_title'] = 'Personnel Management'
        context['page_description'] = 'View personnel in your unit and their current workload.'
        personnel_qs = User.objects.filter(
            role=User.Role.PERSONNEL,
            unit_id=user.unit_id,
            is_active=True,
        ).order_by('first_name', 'last_name', 'username')
        personnel = list(personnel_qs)
        context['personnel_list'] = personnel
        # Active workload counts per personnel (requests not completed/cancelled)
        if personnel:
            active_statuses = (
                Request.Status.SUBMITTED,
                Request.Status.ASSIGNED,
                Request.Status.DIRECTOR_APPROVED,
                Request.Status.INSPECTION,
                Request.Status.IN_PROGRESS,
                Request.Status.ON_HOLD,
                Request.Status.DONE_WORKING,
            )
            from apps.gso_requests.models import RequestAssignment
            counts = (
                RequestAssignment.objects.filter(
                    personnel__in=personnel,
                    request__status__in=active_statuses,
                )
                .values('personnel_id')
                .annotate(total=Count('request_id', distinct=True))
            )
            workload_map = {row['personnel_id']: row['total'] for row in counts}
            assignments = (
                RequestAssignment.objects.filter(personnel__in=personnel)
                .select_related('request')
                .order_by('-request__created_at')
            )
            assigned_map = {}
            for assignment in assignments:
                req = assignment.request
                assigned_map.setdefault(assignment.personnel_id, []).append({
                    'id': req.id,
                    'display_id': req.display_id,
                    'purpose': req.description or '—',
                    'location': req.location or '—',
                    'status_display': req.status_display,
                    'status_badge_class': req.status_badge_class,
                    'created_at': req.created_at,
                })
        else:
            workload_map = {}
            assigned_map = {}
        # Build rows with precomputed counts for easier template usage
        context['personnel_rows'] = [
            {
                'personnel': p,
                'active_count': workload_map.get(p.id, 0),
                'assigned_requests': assigned_map.get(p.id, []),
            }
            for p in personnel
        ]
        return context


class StaffInventoryView(StaffPlaceholderView):
    page_title = 'Inventory'
    page_description = 'View and manage unit inventory and supplies.'


class StaffReportsView(StaffPlaceholderView):
    page_title = 'Reports'
    page_description = 'Generate and view reports.'


class StaffTaskManagementView(StaffPlaceholderView):
    page_title = 'Task Management'
    page_description = 'View and manage your assigned tasks.'


class StaffTaskHistoryView(StaffPlaceholderView):
    page_title = 'Task History'
    page_description = 'View history of your completed tasks.'


class StaffWorkReportsView(StaffPlaceholderView):
    page_title = 'Work Reports'
    page_description = 'View and submit work reports.'


class StaffAccountManagementView(StaffRequiredMixin, ListView):
    """Director only: List all users with filter/search, OIC section, and add/edit user."""
    template_name = 'staff/account_management.html'
    model = User
    context_object_name = 'user_list'
    paginate_by = 25

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('gso_accounts:login')
        if hasattr(request.user, 'is_requestor') and request.user.is_requestor:
            return redirect('gso_accounts:requestor_dashboard')
        if not getattr(request.user, 'is_director', False):
            messages.info(request, 'Account Management is for the Director only.')
            return redirect('gso_accounts:staff_dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        # Director accounts are considered system-level and are not managed here.
        qs = User.objects.exclude(role=User.Role.DIRECTOR).select_related('unit').order_by('first_name', 'last_name', 'username')
        role = self.request.GET.get('role', '').strip()
        if role:
            qs = qs.filter(role=role)
        unit_id = self.request.GET.get('unit', '').strip()
        if unit_id:
            qs = qs.filter(unit_id=unit_id)
        active = self.request.GET.get('active', '')
        if active == '1':
            qs = qs.filter(is_active=True)
        elif active == '0':
            qs = qs.filter(is_active=False)
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(username__icontains=q)
                | Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
                | Q(email__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        from apps.gso_units.models import Unit
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Account Management'
        context['page_description'] = 'View and manage all users. Assign OIC (Officer-in-Charge) or add and edit accounts.'
        director = self.request.user
        context['current_oic'] = User.objects.filter(oic_for_director=director).select_related('oic_for_director').first()
        context['gso_users'] = User.objects.filter(role=User.Role.GSO_OFFICE, is_active=True).order_by('first_name', 'last_name', 'username')
        context['filter_role'] = self.request.GET.get('role', '')
        context['filter_unit'] = self.request.GET.get('unit', '')
        context['filter_active'] = self.request.GET.get('active', '')
        context['filter_q'] = self.request.GET.get('q', '')
        context['units'] = Unit.objects.filter(is_active=True).order_by('name')
        context['role_choices'] = [
            ('', 'All roles'),
            (User.Role.REQUESTOR, 'Requestor'),
            (User.Role.UNIT_HEAD, 'Unit Head'),
            (User.Role.PERSONNEL, 'Personnel'),
            (User.Role.GSO_OFFICE, 'GSO Office'),
        ]
        return context


class AssignOICView(LoginRequiredMixin, View):
    """Director assigns a GSO Office user as OIC (POST only). Phase 4.3."""
    http_method_names = ['post']

    def post(self, request):
        if not getattr(request.user, 'is_director', False):
            messages.error(request, 'Only the Director can assign OIC.')
            return redirect('gso_accounts:staff_dashboard')
        user_id = request.POST.get('user_id', '').strip()
        if not user_id:
            messages.error(request, 'Please select a user.')
            return redirect('gso_accounts:staff_account_management')
        oic_user = get_object_or_404(User, pk=user_id, role=User.Role.GSO_OFFICE, is_active=True)
        director = request.user
        # Revoke any current OIC for this director
        User.objects.filter(oic_for_director=director).update(oic_for_director=None)
        oic_user.oic_for_director = director
        oic_user.save(update_fields=['oic_for_director'])
        from apps.gso_notifications.utils import notify_oic_assigned
        notify_oic_assigned(oic_user, director)
        from apps.gso_accounts.models import log_audit
        log_audit('oic_assign', request.user, f'Assigned OIC: {oic_user.get_full_name() or oic_user.username} (id={oic_user.pk})', target_model='gso_accounts.User', target_id=str(oic_user.pk))
        messages.success(request, f'{oic_user.get_full_name() or oic_user.username} is now Officer-in-Charge and can approve requests.')
        return redirect('gso_accounts:staff_account_management')


class RevokeOICView(LoginRequiredMixin, View):
    """Director revokes OIC (POST only). Phase 4.3."""
    http_method_names = ['post']

    def post(self, request):
        if not getattr(request.user, 'is_director', False):
            messages.error(request, 'Only the Director can revoke OIC.')
            return redirect('gso_accounts:staff_dashboard')
        director = request.user
        previous_oic = User.objects.filter(oic_for_director=director).first()
        User.objects.filter(oic_for_director=director).update(oic_for_director=None)
        if previous_oic:
            from apps.gso_notifications.utils import notify_oic_revoked
            notify_oic_revoked(previous_oic, director)
            from apps.gso_accounts.models import log_audit
            log_audit('oic_revoke', request.user, f'Revoked OIC: {previous_oic.get_full_name() or previous_oic.username} (id={previous_oic.pk})', target_model='gso_accounts.User', target_id=str(previous_oic.pk))
        messages.success(request, 'OIC revoked. Only the Director can approve requests now.')
        return redirect('gso_accounts:staff_account_management')


class DirectorUserCreateView(StaffRequiredMixin, CreateView):
    """Director only: Add a new user."""
    model = User
    form_class = DirectorUserCreateForm
    template_name = 'staff/director_user_form.html'
    success_url = reverse_lazy('gso_accounts:staff_account_management')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('gso_accounts:login')
        if hasattr(request.user, 'is_requestor') and request.user.is_requestor:
            return redirect('gso_accounts:requestor_dashboard')
        if not getattr(request.user, 'is_director', False):
            messages.error(request, 'Only the Director can add users.')
            return redirect('gso_accounts:staff_dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Add user'
        context['page_description'] = 'Create a new user account. Set role and unit (for Unit Head/Personnel).'
        return context

    def form_valid(self, form):
        from .models import log_audit
        response = super().form_valid(form)
        log_audit(
            'user_create',
            self.request.user,
            f'Created user account for {self.object.get_full_name() or self.object.username}',
            target_model='gso_accounts.User',
            target_id=str(self.object.pk),
        )
        messages.success(self.request, f'User "{self.object.username}" has been created.')
        return response


class DirectorUserEditView(StaffRequiredMixin, UpdateView):
    """Director only: Edit a user (profile, role, unit, active; optional password change)."""
    model = User
    form_class = DirectorUserEditForm
    template_name = 'staff/director_user_form.html'
    context_object_name = 'user_obj'
    success_url = reverse_lazy('gso_accounts:staff_account_management')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('gso_accounts:login')
        if hasattr(request.user, 'is_requestor') and request.user.is_requestor:
            return redirect('gso_accounts:requestor_dashboard')
        if not getattr(request.user, 'is_director', False):
            messages.error(request, 'Only the Director can edit users.')
            return redirect('gso_accounts:staff_dashboard')
        # Do not allow editing Director accounts from this UI.
        try:
            obj = self.get_object()
            if obj and obj.role == User.Role.DIRECTOR:
                messages.error(request, 'Director accounts cannot be edited from Account Management.')
                return redirect('gso_accounts:staff_account_management')
        except Exception:
            pass
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Edit user'
        context['page_description'] = f'Update account for {self.object.username}.'
        context['is_edit'] = True
        return context

    def form_valid(self, form):
        from .models import log_audit
        response = super().form_valid(form)
        log_audit(
            'user_edit',
            self.request.user,
            f'Updated user account for {self.object.get_full_name() or self.object.username}',
            target_model='gso_accounts.User',
            target_id=str(self.object.pk),
        )
        messages.success(self.request, f'User "{self.object.username}" has been updated.')
        return response


# Unit display for requestor dashboard (icon + description by unit code)
UNIT_DISPLAY = {
    'repair': {'icon': 'build', 'bg': 'bg-blue-50 dark:bg-blue-900/20', 'text': 'text-blue-600', 'description': 'Fix office furniture, plumbing, or masonry work.'},
    'utility': {'icon': 'cleaning_services', 'bg': 'bg-green-50 dark:bg-green-900/20', 'text': 'text-green-600', 'description': 'Request cleaning services or venue setup.'},
    'electrical': {'icon': 'bolt', 'bg': 'bg-amber-50 dark:bg-amber-900/20', 'text': 'text-amber-600', 'description': 'Report lighting issues or power requirements.'},
    'motorpool': {'icon': 'directions_car', 'bg': 'bg-indigo-50 dark:bg-indigo-900/20', 'text': 'text-indigo-600', 'description': 'Book vehicle services and transport.'},
}


class RequestorDashboardView(TemplateView):
    """Dashboard for Requestor (different layout – service selection + my requests)."""
    template_name = 'requestor/dashboard.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('gso_accounts:login')
        if hasattr(request.user, 'is_staff_role') and request.user.is_staff_role:
            return redirect('gso_accounts:staff_dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        context = self.get_context_data()
        # AJAX partial for My Requests (filters/pagination without full page reload)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.GET.get('partial') == 'my_requests':
            from django.template.loader import render_to_string
            html = render_to_string('requestor/_my_requests_content.html', context, request=request)
            return HttpResponse(html)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        from apps.gso_units.models import Unit
        from apps.gso_requests.forms import RequestForm
        from apps.gso_requests.models import Request
        context = super().get_context_data(**kwargs)
        user = self.request.user
        # Base queryset: this requestor's requests
        qs = Request.objects.filter(requestor=user).select_related('unit').order_by('-created_at')
        # Filters: status and search
        status = self.request.GET.get('status', '').strip()
        q = self.request.GET.get('q', '').strip()
        if status:
            qs = qs.filter(status=status)
        if q:
            qs = qs.filter(
                Q(title__icontains=q)
                | Q(description__icontains=q)
                | Q(location__icontains=q)
                | Q(unit__name__icontains=q)
            )
        # Paginate: 5 requests per page so requestor can easily browse history
        paginator = Paginator(qs, 5)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        context['request_list'] = page_obj.object_list
        context['page_obj'] = page_obj
        context['submitted'] = self.request.GET.get('submitted') == '1'
        # Filter metadata for UI
        context['filter_status'] = status
        context['filter_q'] = q
        context['status_choices'] = Request.Status.choices
        units = list(Unit.objects.filter(is_active=True).order_by('name'))
        # Fixed requestor card order:
        # Repair & Maintenance, Electrical, Utility, Motorpool.
        unit_order = {
            'repair': 0,
            'electrical': 1,
            'utility': 2,
            'motorpool': 3,
        }
        units.sort(key=lambda u: (unit_order.get((u.code or '').lower(), 99), u.name.lower()))
        context['units'] = [
            {'unit': u, 'display': UNIT_DISPLAY.get(u.code, {'icon': 'build', 'bg': 'bg-slate-50 dark:bg-slate-800', 'text': 'text-slate-600', 'description': u.name})}
            for u in units
        ]
        # Form for the request popup modal (unit comes from hidden "units" input set by JS)
        request_form = RequestForm()
        request_form.fields.pop('unit', None)
        context['request_form'] = request_form
        return context


class NotificationGoView(LoginRequiredMixin, View):
    """Mark one notification as read and redirect to its link (so the red badge updates when user clicks)."""

    def get(self, request, pk):
        from apps.gso_notifications.models import Notification
        n = get_object_or_404(Notification, pk=pk, user=request.user)
        n.read = True
        n.save(update_fields=['read'])
        return redirect(n.link or reverse('gso_accounts:requestor_dashboard'))


class MarkAllNotificationsReadView(LoginRequiredMixin, View):
    """Mark all notifications for current user as read, then redirect back or to notifications page."""

    def post(self, request):
        from apps.gso_notifications.models import Notification
        Notification.objects.filter(user=request.user).update(read=True)
        return redirect(request.META.get('HTTP_REFERER') or self._notifications_url(request))

    def get(self, request):
        return self.post(request)

    def _notifications_url(self, request):
        if getattr(request.user, 'is_requestor', False):
            return reverse('gso_accounts:requestor_notifications')
        return reverse('gso_accounts:staff_notifications')


class StaffNotificationsView(StaffRequiredMixin, TemplateView):
    """Staff notifications page — list from Notification model."""
    template_name = 'staff/notifications.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.gso_notifications.models import Notification
        context['notifications'] = Notification.objects.filter(user=self.request.user).order_by('-created_at')[:100]
        return context


class RequestorNotificationsView(TemplateView):
    """Requestor notifications page — real list from Notification model."""
    template_name = 'requestor/notifications.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('gso_accounts:login')
        if hasattr(request.user, 'is_staff_role') and request.user.is_staff_role:
            return redirect('gso_accounts:staff_dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from apps.gso_notifications.models import Notification
        context['notifications'] = Notification.objects.filter(user=self.request.user).order_by('-created_at')[:100]
        return context


class RequestorProfileView(TemplateView):
    """Requestor profile/settings page (view only; edit via RequestorProfileEditView)."""
    template_name = 'requestor/profile.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('gso_accounts:login')
        if hasattr(request.user, 'is_staff_role') and request.user.is_staff_role:
            return redirect('gso_accounts:staff_dashboard')
        return super().dispatch(request, *args, **kwargs)


class RequestorProfileEditView(UpdateView):
    """Edit requestor profile: first name, last name, email."""
    model = User
    form_class = RequestorProfileForm
    template_name = 'requestor/profile_edit.html'
    success_url = reverse_lazy('gso_accounts:requestor_dashboard')

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER') or reverse('gso_accounts:requestor_dashboard')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('gso_accounts:login')
        if hasattr(request.user, 'is_staff_role') and request.user.is_staff_role:
            return redirect('gso_accounts:staff_dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return self.request.user


class StaffProfileEditView(UpdateView):
    """Edit profile for staff users: first name, last name, email, avatar."""
    model = User
    form_class = RequestorProfileForm
    template_name = 'staff/profile_edit.html'

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER') or reverse('gso_accounts:staff_dashboard')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('gso_accounts:login')
        if getattr(request.user, 'is_requestor', False):
            return redirect('gso_accounts:requestor_dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return self.request.user


def _redirect_with_query(url, params):
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    for key, value in params.items():
        if value is None:
            query.pop(key, None)
        else:
            query[key] = str(value)
    return urlunparse(parsed._replace(query=urlencode(query)))


class GsoPasswordChangeView(LoginRequiredMixin, View):
    """Logged-in change password flow for profile modal."""
    http_method_names = ['post']

    def post(self, request):
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        fallback = reverse('gso_accounts:requestor_dashboard') if getattr(request.user, 'is_requestor', False) else reverse('gso_accounts:staff_dashboard')
        referer = request.META.get('HTTP_REFERER') or fallback
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            if is_ajax:
                return JsonResponse({'ok': True})
            url = _redirect_with_query(
                referer,
                {
                    'profile_pane': 'view',
                    'pw_success': '1',
                    'pw_error': None,
                },
            )
            return redirect(url)
        error_text = '; '.join([e for errors in form.errors.values() for e in errors]) or 'Unable to change password.'
        if is_ajax:
            return JsonResponse({'ok': False, 'error': error_text}, status=400)
        url = _redirect_with_query(
            referer,
            {
                'profile_pane': 'password',
                'pw_success': None,
                'pw_error': error_text,
            },
        )
        return redirect(url)


# Password reset via OTP email (Forgot Password flow)
class GsoPasswordResetView(FormView):
    form_class = GsoPasswordResetForm
    template_name = 'registration/password_reset_form.html'
    success_url = reverse_lazy('gso_accounts:password_reset_done')

    def form_valid(self, form):
        email = (form.cleaned_data.get('email') or '').strip()
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        # Always clear stale session state first.
        for key in (
            'password_reset_pending_user_id',
            'password_reset_pending_otp_id',
            'password_reset_verified',
        ):
            self.request.session.pop(key, None)

        # Keep response generic to avoid exposing whether account exists.
        if user:
            _issue_password_reset_otp(self.request, user, force=True)

        return super().form_valid(form)


class GsoPasswordResetDoneView(TemplateView):
    template_name = 'registration/password_reset_done.html'


def _otp_resend_cooldown_seconds():
    return max(10, int(getattr(settings, 'GSO_PASSWORD_RESET_OTP_RESEND_COOLDOWN_SECONDS', 60)))


def _issue_password_reset_otp(request, user, *, force=False):
    """Issue and email OTP; optionally enforce resend cooldown."""
    cooldown_seconds = _otp_resend_cooldown_seconds()
    latest_active = (
        PasswordResetOTP.objects
        .filter(user=user, used_at__isnull=True, expires_at__gt=timezone.now())
        .order_by('-created_at')
        .first()
    )
    if latest_active and not force:
        elapsed = (timezone.now() - latest_active.created_at).total_seconds()
        if elapsed < cooldown_seconds:
            return None, int(cooldown_seconds - elapsed)

    code = f"{secrets.randbelow(1000000):06d}"
    otp_minutes = max(3, int(getattr(settings, 'GSO_PASSWORD_RESET_OTP_EXP_MINUTES', 10)))
    expires_at = timezone.now() + timedelta(minutes=otp_minutes)

    PasswordResetOTP.objects.filter(
        user=user,
        used_at__isnull=True,
        expires_at__gt=timezone.now(),
    ).update(expires_at=timezone.now())

    otp = PasswordResetOTP.objects.create(
        user=user,
        code=code,
        expires_at=expires_at,
    )
    body = render_to_string(
        'registration/password_reset_otp_email.txt',
        {
            'code': code,
            'user': user,
            'minutes': otp_minutes,
        },
    )
    send_mail(
        subject='GSO System - Your password reset OTP',
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )
    request.session['password_reset_pending_user_id'] = user.pk
    request.session['password_reset_pending_otp_id'] = otp.pk
    request.session['password_reset_verified'] = False
    return otp, 0


class GsoPasswordResetOTPVerifyView(FormView):
    form_class = GsoPasswordResetOTPForm
    template_name = 'registration/password_reset_otp_verify.html'
    success_url = reverse_lazy('gso_accounts:password_reset_confirm')

    def dispatch(self, request, *args, **kwargs):
        if not request.session.get('password_reset_pending_user_id'):
            messages.info(request, 'Please request a password reset OTP first.')
            return redirect('gso_accounts:password_reset')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_id = self.request.session.get('password_reset_pending_user_id')
        otp_id = self.request.session.get('password_reset_pending_otp_id')
        otp = PasswordResetOTP.objects.filter(pk=otp_id, user_id=user_id).first()
        seconds_left = 0
        if otp and not otp.is_used and not otp.is_expired:
            elapsed = (timezone.now() - otp.created_at).total_seconds()
            seconds_left = max(0, int(_otp_resend_cooldown_seconds() - elapsed))
        context['otp_resend_seconds_left'] = seconds_left
        return context

    def form_valid(self, form):
        otp_id = self.request.session.get('password_reset_pending_otp_id')
        user_id = self.request.session.get('password_reset_pending_user_id')
        otp = PasswordResetOTP.objects.filter(pk=otp_id, user_id=user_id).first()
        max_attempts = max(1, int(getattr(settings, 'GSO_PASSWORD_RESET_OTP_MAX_ATTEMPTS', 5)))

        if not otp or otp.is_used or otp.is_expired:
            form.add_error('otp', 'OTP is invalid or expired. Please request a new one.')
            return self.form_invalid(form)
        if otp.attempts >= max_attempts:
            form.add_error('otp', 'Too many attempts. Please request a new OTP.')
            return self.form_invalid(form)
        if form.cleaned_data['otp'] != otp.code:
            otp.attempts += 1
            otp.save(update_fields=['attempts'])
            form.add_error('otp', 'Incorrect OTP. Please try again.')
            return self.form_invalid(form)

        self.request.session['password_reset_verified'] = True
        return super().form_valid(form)


class GsoPasswordResetOTPResendView(View):
    """Resend OTP with cooldown protection."""
    http_method_names = ['post']

    def post(self, request):
        user_id = request.session.get('password_reset_pending_user_id')
        if not user_id:
            messages.info(request, 'Please request a password reset OTP first.')
            return redirect('gso_accounts:password_reset')
        user = User.objects.filter(pk=user_id, is_active=True).first()
        if not user or not user.email:
            messages.error(request, 'Unable to resend OTP. Please request reset again.')
            return redirect('gso_accounts:password_reset')
        otp, seconds_left = _issue_password_reset_otp(request, user, force=False)
        if otp is None:
            messages.info(request, f'Please wait {seconds_left} seconds before resending OTP.')
        else:
            messages.success(request, 'A new OTP has been sent to your email.')
        return redirect('gso_accounts:password_reset_verify')


class GsoPasswordResetConfirmView(FormView):
    form_class = GsoSetPasswordForm
    template_name = 'registration/password_reset_confirm.html'
    success_url = reverse_lazy('gso_accounts:password_reset_complete')

    def dispatch(self, request, *args, **kwargs):
        if not request.session.get('password_reset_pending_user_id'):
            messages.info(request, 'Please request a password reset OTP first.')
            return redirect('gso_accounts:password_reset')
        if not request.session.get('password_reset_verified'):
            messages.info(request, 'Please verify your OTP before setting a new password.')
            return redirect('gso_accounts:password_reset_verify')
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        user_id = self.request.session.get('password_reset_pending_user_id')
        kwargs['user'] = get_object_or_404(User, pk=user_id, is_active=True)
        return kwargs

    def form_valid(self, form):
        user = form.user
        user.set_password(form.cleaned_data['new_password1'])
        user.save(update_fields=['password'])
        otp_id = self.request.session.get('password_reset_pending_otp_id')
        PasswordResetOTP.objects.filter(pk=otp_id, user=user).update(used_at=timezone.now())
        for key in (
            'password_reset_pending_user_id',
            'password_reset_pending_otp_id',
            'password_reset_verified',
        ):
            self.request.session.pop(key, None)
        return super().form_valid(form)


class GsoPasswordResetCompleteView(TemplateView):
    template_name = 'registration/password_reset_complete.html'
