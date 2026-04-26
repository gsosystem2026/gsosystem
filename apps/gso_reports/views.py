"""Phase 6.1: WAR create. Phase 6.3/6.4: Work Reports landing, IPMT and WAR Excel export."""
import io
import json
import logging
import os
import tempfile
from datetime import date as _date, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, get_object_or_404, render
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone
from django.views.generic import CreateView, FormView, TemplateView, UpdateView
from django.views.decorators.http import require_POST

from apps.gso_accounts.views import StaffRequiredMixin
from apps.gso_requests.models import Request, RequestFeedback
from apps.gso_units.models import Unit

from .excel_export import (
    build_ipmt_excel,
    build_war_export_excel,
    build_feedback_export_excel,
    get_war_queryset,
    get_feedback_queryset,
)
from .forms import WARForm, IPMTReportForm, WARExportForm, FeedbackExportForm, SuccessIndicatorForm
from .war_config import get_war_table_config
from .models import SuccessIndicator, WorkAccomplishmentReport, IPMTDraft
from .ai_service import generate_ipmt_accomplishment, is_ai_configured

logger = logging.getLogger(__name__)


def _safe_json_server_error(message='Something went wrong. Please try again later.'):
    return JsonResponse({'ok': False, 'error': message}, status=502)


def _delta_display(current, previous, *, suffix=''):
    """
    Return display metadata for KPI trend badge.
    """
    if current is None or previous is None:
        return {'value': '—', 'direction': 'flat', 'is_positive': True}
    delta = round(current - previous, 1)
    if delta > 0:
        value = f"+{delta:g}{suffix}"
        direction = 'up'
    elif delta < 0:
        value = f"{delta:g}{suffix}"
        direction = 'down'
    else:
        value = f"0{suffix}"
        direction = 'flat'
    return {
        'value': value,
        'direction': direction,
        'is_positive': delta >= 0,
    }


class WARCreateView(StaffRequiredMixin, CreateView):
    """Create a WAR for a completed request (one per assigned personnel). Phase 6.1."""
    model = WorkAccomplishmentReport
    form_class = WARForm
    template_name = 'staff/war_form.html'

    def dispatch(self, request, *args, **kwargs):
        req = get_object_or_404(Request.objects.select_related('unit'), pk=kwargs['request_pk'])
        if req.status != Request.Status.COMPLETED:
            messages.warning(request, 'WAR can only be added for completed requests.')
            return redirect('gso_accounts:staff_request_detail', pk=req.pk)
        user = request.user
        if getattr(user, 'is_requestor', False):
            return redirect('gso_accounts:staff_dashboard')
        # Only GSO Office and Director can add WAR.
        if not (getattr(user, 'is_gso_office', False) or getattr(user, 'is_director', False)):
            messages.error(request, 'You cannot add a WAR for this request.')
            return redirect('gso_accounts:staff_request_detail', pk=req.pk)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request_obj'] = get_object_or_404(Request, pk=self.kwargs['request_pk'])
        return kwargs

    def form_valid(self, form):
        req = get_object_or_404(Request, pk=self.kwargs['request_pk'])
        form.instance.request = req
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Work Accomplishment Report added.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('gso_accounts:staff_request_detail', args=[self.kwargs['request_pk']])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['req'] = get_object_or_404(Request.objects.select_related('unit'), pk=self.kwargs['request_pk'])
        context['page_title'] = 'Add Work Accomplishment Report'
        context['page_description'] = f'Report for request {context["req"].display_id}. One WAR per personnel.'
        return context


class WARUpdateView(StaffRequiredMixin, UpdateView):
    """Edit an existing WAR. Only GSO Office and Director can edit."""
    model = WorkAccomplishmentReport
    form_class = WARForm
    template_name = 'staff/war_form.html'
    context_object_name = 'war'

    def _wants_partial(self):
        return bool(
            self.request.GET.get('partial')
            or self.request.POST.get('partial')
            or self.request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        )

    def _requested_source(self):
        return (self.request.GET.get('source') or self.request.POST.get('source') or '').strip().lower()

    def _next_url(self):
        raw_next = (self.request.GET.get('next') or self.request.POST.get('next') or '').strip()
        if raw_next and url_has_allowed_host_and_scheme(
            raw_next,
            allowed_hosts={self.request.get_host()},
            require_https=self.request.is_secure(),
        ):
            return raw_next
        req = getattr(self, 'request_obj', None) or getattr(self.object, 'request', None)
        if self._requested_source() == 'war':
            return reverse('gso_accounts:staff_work_reports_war_export')
        if req:
            return reverse('gso_accounts:staff_request_detail', args=[req.pk])
        return reverse('gso_accounts:staff_work_reports_war_export')

    def get_template_names(self):
        if self._wants_partial():
            return ['staff/war_edit_partial.html']
        return [self.template_name]

    def dispatch(self, request, *args, **kwargs):
        war = get_object_or_404(WorkAccomplishmentReport.objects.select_related('request'), pk=kwargs['pk'])
        user = request.user
        # Only GSO Office and Director can edit WARs
        if getattr(user, 'is_requestor', False) or getattr(user, 'is_unit_head', False) or getattr(user, 'is_personnel', False):
            messages.error(request, 'Only GSO Office and Director can edit Work Accomplishment Reports.')
            return redirect('gso_accounts:staff_request_detail', pk=war.request_id)
        self.request_obj = war.request
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        req = getattr(self, 'request_obj', None) or self.object.request
        context['req'] = req
        context['page_title'] = 'Edit Work Accomplishment Report'
        context['page_description'] = f'Update report for request {req.display_id}.'
        context['is_edit'] = True
        context['war_edit_source'] = self._requested_source() or 'request'
        context['war_edit_next_url'] = self._next_url()
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        req = getattr(self, 'request_obj', None)
        if req is not None:
            kwargs['request_obj'] = req
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Work Accomplishment Report updated.')
        if self._wants_partial():
            return redirect(self._next_url())
        return response

    def form_invalid(self, form):
        if self._wants_partial():
            return TemplateResponse(
                self.request,
                self.get_template_names(),
                self.get_context_data(form=form),
                status=400,
            )
        return super().form_invalid(form)

    def get_success_url(self):
        return self._next_url()


def _can_access_work_reports(user):
    """True if user is GSO Office or Director (Work Reports nav)."""
    return getattr(user, 'is_gso_office', False) or getattr(user, 'is_director', False)


class WorkReportsLandingView(StaffRequiredMixin, TemplateView):
    """Work Reports landing: analytics overview for Director/GSO."""
    template_name = 'staff/work_reports.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('gso_accounts:login')
        if getattr(request.user, 'is_requestor', False):
            return redirect('gso_accounts:requestor_dashboard')
        if not _can_access_work_reports(request.user):
            messages.info(request, 'Work Reports is for GSO Office and Director only.')
            return redirect('gso_accounts:staff_dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        # Range selector: weekly (last 7 days) or monthly (last 30 days) unless custom start/end provided
        range_key = self.request.GET.get('range', 'monthly').lower()
        if range_key not in ('weekly', 'monthly'):
            range_key = 'monthly'
        start_param = self.request.GET.get('start') or ''
        end_param = self.request.GET.get('end') or ''
        date_from = None
        date_to = None
        # Custom date range from inputs if both provided and valid
        try:
            if start_param and end_param:
                date_from = _date.fromisoformat(start_param)
                date_to = _date.fromisoformat(end_param)
        except ValueError:
            date_from = None
            date_to = None
        if date_from is None or date_to is None:
            if range_key == 'weekly':
                days_back = 6
            else:
                days_back = 29
            date_to = today
            date_from = today - timezone.timedelta(days=days_back)

        # Completed requests in window (fallback to all-time if none)
        completed_qs = Request.objects.filter(
            status=Request.Status.COMPLETED,
            updated_at__date__gte=date_from,
            updated_at__date__lte=date_to,
        )
        total_completed = completed_qs.count()
        if total_completed == 0:
            # Fallback: use all completed requests so charts are never empty
            completed_qs = Request.objects.filter(status=Request.Status.COMPLETED)
            total_completed = completed_qs.count()
            if total_completed:
                first_completed = completed_qs.order_by('updated_at').first().updated_at.date()
                last_completed = completed_qs.order_by('-updated_at').first().updated_at.date()
                date_from, date_to = first_completed, last_completed

        # Average completion time (created_at -> updated_at) in days
        duration_expr = ExpressionWrapper(
            F('updated_at') - F('created_at'),
            output_field=DurationField(),
        )
        avg_duration = (
            completed_qs.annotate(duration=duration_expr)
            .aggregate(avg_duration=Avg('duration'))
            .get('avg_duration')
        )
        avg_days = round(avg_duration.total_seconds() / 86400, 1) if avg_duration else None

        # Success rate: completed vs completed+cancelled
        finished_qs = Request.objects.filter(
            status__in=(Request.Status.COMPLETED, Request.Status.CANCELLED),
            updated_at__date__gte=date_from,
            updated_at__date__lte=date_to,
        )
        finished_total = finished_qs.count()
        success_rate = round((total_completed / finished_total) * 100, 1) if finished_total else None

        # Average rating from feedback (1–5)
        feedback_qs = RequestFeedback.objects.filter(
            request__status=Request.Status.COMPLETED,
            created_at__date__gte=date_from,
            created_at__date__lte=date_to,
            rating__isnull=False,
        )
        avg_rating = feedback_qs.aggregate(avg_rating=Avg('rating')).get('avg_rating')
        avg_rating_rounded = round(avg_rating, 1) if avg_rating else None

        # Tasks by unit (completed requests)
        unit_counts = list(
            completed_qs.values('unit__name')
            .annotate(total=Count('id'))
            .order_by('-total')[:6]
        )
        max_total = max((u['total'] for u in unit_counts), default=0)
        unit_bars = []
        for idx, row in enumerate(unit_counts):
            label = row['unit__name'] or '—'
            if max_total:
                height_pct = int(30 + 70 * (row['total'] / max_total))
            else:
                height_pct = 0
            unit_bars.append(
                {
                    'label': label,
                    'height_pct': f"{height_pct}%",
                    'is_top': idx == 0,
                }
            )

        # Unit distribution percentages (same data as bars)
        total_for_dist = sum((u['total'] for u in unit_counts), 0)
        unit_distribution = []
        for row in unit_counts:
            label = row['unit__name'] or '—'
            percent = round((row['total'] / total_for_dist) * 100) if total_for_dist else 0
            unit_distribution.append({'label': label, 'percent': percent})
        unit_count = len(unit_distribution)

        # Top personnel based on WAR count in window
        war_qs = WorkAccomplishmentReport.objects.filter(
            period_end__gte=date_from,
            period_end__lte=date_to,
        ).exclude(
            personnel__username__iexact=getattr(
                settings,
                'GSO_LEGACY_MIGRATION_PERSONNEL_USERNAME',
                'migrated_legacy',
            )
        ).select_related('personnel', 'personnel__unit')
        personnel_rows = (
            war_qs.values(
                'personnel_id',
                'personnel__first_name',
                'personnel__last_name',
                'personnel__username',
                'personnel__unit__name',
            )
            .annotate(total=Count('id'))
            .order_by('-total')[:5]
        )
        top_personnel = []
        for row in personnel_rows:
            first = (row.get('personnel__first_name') or '').strip()
            last = (row.get('personnel__last_name') or '').strip()
            full_name = (first + ' ' + last).strip() or row.get('personnel__username') or '—'
            top_personnel.append(
                {
                    'name': full_name,
                    'unit_name': row.get('personnel__unit__name') or '—',
                    'accomplishments': row['total'],
                }
            )

        # Trend over time: completed requests per day in range
        trend_points = []
        days_count = (date_to - date_from).days + 1
        for offset in range(days_count):
            day = date_from + timezone.timedelta(days=offset)
            count = completed_qs.filter(updated_at__date=day).count()
            # Windows strftime does not support %-d; use %d and strip leading zero
            label = day.strftime('%b %d')
            trend_points.append({'label': label.lstrip('0'), 'count': count})
        max_trend = max((p['count'] for p in trend_points), default=0)
        for p in trend_points:
            if max_trend:
                height = int(20 + 80 * (p['count'] / max_trend))
            else:
                height = 0
            p['height_pct'] = f"{height}%"

        period_days = (date_to - date_from).days + 1
        prev_to = date_from - timedelta(days=1)
        prev_from = prev_to - timedelta(days=period_days - 1)

        prev_completed_qs = Request.objects.filter(
            status=Request.Status.COMPLETED,
            updated_at__date__gte=prev_from,
            updated_at__date__lte=prev_to,
        )
        prev_total_completed = prev_completed_qs.count()
        prev_duration = (
            prev_completed_qs.annotate(duration=duration_expr)
            .aggregate(avg_duration=Avg('duration'))
            .get('avg_duration')
        )
        prev_avg_days = round(prev_duration.total_seconds() / 86400, 1) if prev_duration else None
        prev_finished_qs = Request.objects.filter(
            status__in=(Request.Status.COMPLETED, Request.Status.CANCELLED),
            updated_at__date__gte=prev_from,
            updated_at__date__lte=prev_to,
        )
        prev_finished_total = prev_finished_qs.count()
        prev_success_rate = round((prev_total_completed / prev_finished_total) * 100, 1) if prev_finished_total else None
        prev_feedback_qs = RequestFeedback.objects.filter(
            request__status=Request.Status.COMPLETED,
            created_at__date__gte=prev_from,
            created_at__date__lte=prev_to,
            rating__isnull=False,
        )
        prev_avg_rating = prev_feedback_qs.aggregate(avg_rating=Avg('rating')).get('avg_rating')
        prev_avg_rating_rounded = round(prev_avg_rating, 1) if prev_avg_rating else None

        context.update(
            {
                'page_title': 'Work Reports',
                'page_description': 'Analytics based on completed requests, WARs, and feedback.',
                'date_range_label': f"{date_from.strftime('%b %d, %Y')} - {date_to.strftime('%b %d, %Y')}",
                'date_from_input': date_from.isoformat(),
                'date_to_input': date_to.isoformat(),
                'kpi_total_completed': total_completed,
                'kpi_avg_completion_days': avg_days,
                'kpi_success_rate': success_rate,
                'kpi_avg_rating': avg_rating_rounded,
                'kpi_total_completed_delta': _delta_display(total_completed, prev_total_completed),
                # Lower completion days is better.
                'kpi_avg_completion_days_delta': _delta_display(
                    avg_days,
                    prev_avg_days,
                    suffix='d',
                ),
                'kpi_success_rate_delta': _delta_display(success_rate, prev_success_rate, suffix='%'),
                'kpi_avg_rating_delta': _delta_display(avg_rating_rounded, prev_avg_rating_rounded),
                'unit_bars': unit_bars,
                'unit_distribution': unit_distribution,
                'unit_count': unit_count,
                'top_personnel': top_personnel,
                'active_range': range_key,
                'trend_points': trend_points,
                'migration_units': Unit.objects.filter(is_active=True).order_by('name'),
            }
        )
        return context


class WorkReportsMigrationView(StaffRequiredMixin, TemplateView):
    """Upload and import legacy WAR workbook from Work Reports page."""
    template_name = 'staff/work_reports.html'

    def _is_ajax(self, request):
        return request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    def _respond(self, request, *, ok, message, redirect_name='gso_accounts:staff_work_reports', level='info', status=200):
        if self._is_ajax(request):
            return JsonResponse({'ok': ok, 'message': message, 'level': level}, status=status)
        if level == 'success':
            messages.success(request, message)
        elif level == 'error':
            messages.error(request, message)
        elif level == 'warning':
            messages.warning(request, message)
        else:
            messages.info(request, message)
        return redirect(redirect_name)

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('gso_accounts:login')
        if getattr(request.user, 'is_requestor', False) or not _can_access_work_reports(request.user):
            return self._respond(
                request,
                ok=False,
                message='Only GSO Office and Director can run migration.',
                redirect_name='gso_accounts:staff_dashboard',
                level='error',
                status=403,
            )

        upload = request.FILES.get('excel_file')
        unit_id = (request.POST.get('unit_id') or '').strip()
        report_type = (request.POST.get('report_type') or 'war').strip().lower()
        mode = (request.POST.get('mode') or 'dry_run').strip().lower()
        if not upload:
            return self._respond(request, ok=False, message='Please upload an Excel file first.', level='error', status=400)
        if not unit_id:
            return self._respond(request, ok=False, message='Please select a target unit.', level='error', status=400)
        if report_type not in {'war', 'ipmt'}:
            return self._respond(request, ok=False, message='Invalid report type selected.', level='error', status=400)
        unit = Unit.objects.filter(pk=unit_id, is_active=True).first()
        if not unit:
            return self._respond(request, ok=False, message='Selected unit is invalid or inactive.', level='error', status=400)

        is_dry_run = mode != 'apply'
        temp_path = None
        out = io.StringIO()
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
                for chunk in upload.chunks():
                    tmp.write(chunk)
                temp_path = tmp.name

            command_name = 'gso_import_legacy_war' if report_type == 'war' else 'gso_import_legacy_ipmt'
            cmd_args = [command_name, temp_path, '--unit-code', unit.code]
            if is_dry_run:
                cmd_args.append('--dry-run')
            call_command(*cmd_args, stdout=out)
            summary = self._extract_summary(out.getvalue())
            mode_label = 'Dry-run' if is_dry_run else 'Apply'
            report_label = 'WAR' if report_type == 'war' else 'IPMT'
            return self._respond(
                request,
                ok=True,
                message=f"{mode_label} {report_label} migration finished. {summary}",
                level='success',
                status=200,
            )
        except CommandError as exc:
            logger.warning('Legacy migration command failed: %s', exc)
            return self._respond(
                request,
                ok=False,
                message=f"Migration failed: {exc}",
                level='error',
                status=400,
            )
        except Exception:
            logger.exception('Unexpected migration upload failure')
            return self._respond(
                request,
                ok=False,
                message='Migration failed due to an unexpected error.',
                level='error',
                status=500,
            )
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except OSError:
                    logger.warning('Unable to remove temporary migration file: %s', temp_path)
        return self._respond(request, ok=False, message='Migration did not complete.', level='error', status=500)

    def _extract_summary(self, output_text):
        wanted = (
            'Requests created',
            'Requests skipped',
            'WAR created',
            'WAR skipped',
            'Drafts created',
            'Drafts updated',
            'Rows parsed',
            'Rows skipped',
            'Errors',
        )
        parts = []
        for raw_line in output_text.splitlines():
            line = raw_line.strip()
            for key in wanted:
                if line.startswith(key + ':'):
                    parts.append(line)
                    break
        return ' | '.join(parts) if parts else 'See command summary in logs.'


class IPMTReportView(StaffRequiredMixin, FormView):
    """Phase 6.3: Generate IPMT Excel — select personnel and month/year. Uses GET for download."""
    form_class = IPMTReportForm
    template_name = 'staff/ipmt_report.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('gso_accounts:login')
        if getattr(request.user, 'is_requestor', False):
            return redirect('gso_accounts:requestor_dashboard')
        if not _can_access_work_reports(request.user):
            messages.info(request, 'Work Reports is for GSO Office and Director only.')
            return redirect('gso_accounts:staff_dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        from datetime import date
        today = date.today()
        return {'year': today.year, 'month': today.month}

    def get(self, request, *args, **kwargs):
        if request.GET:
            form = self.get_form()
            if form.is_valid():
                personnel = form.cleaned_data['personnel']
                year = form.cleaned_data['year']
                month = form.cleaned_data['month']
                action = (request.GET.get('action') or 'preview').strip().lower()
                preview_rows = self._build_preview_rows(personnel, year, month)
                self.preview_rows = preview_rows
                self.preview_personnel = personnel
                self.preview_year = year
                self.preview_month = month
                draft = IPMTDraft.objects.filter(
                    personnel=personnel,
                    year=year,
                    month=month,
                ).first()
                if action == 'download':
                    edited_rows = self._parse_preview_edits(request.GET.get('preview_edits', ''))
                    rows_for_export = edited_rows or preview_rows
                    IPMTDraft.objects.update_or_create(
                        personnel=personnel,
                        year=year,
                        month=month,
                        defaults={
                            'rows_json': rows_for_export,
                            'updated_by': request.user,
                        }
                    )
                    buf, _ = build_ipmt_excel(personnel, year, month, preview_rows=rows_for_export)
                    filename = f"IPMT_{personnel.username}_{year}_{month:02d}.xlsx"
                    response = HttpResponse(
                        buf.getvalue(),
                        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    )
                    response['Content-Disposition'] = f'attachment; filename="{filename}"'
                    return response
                if action == 'preview':
                    # Draft-first behavior with incremental merge:
                    # keep existing edited draft rows, append only new WAR-derived items.
                    if draft and isinstance(draft.rows_json, list) and draft.rows_json:
                        self.preview_rows = self._merge_draft_with_preview(
                            draft_rows=draft.rows_json,
                            preview_rows=preview_rows,
                        )
                    IPMTDraft.objects.update_or_create(
                        personnel=personnel,
                        year=year,
                        month=month,
                        defaults={
                            'rows_json': self.preview_rows,
                            'updated_by': request.user,
                        }
                    )
                if action == 'save_draft':
                    edited_rows = self._parse_preview_edits(request.GET.get('preview_edits', ''))
                    rows_for_draft = edited_rows or preview_rows
                    IPMTDraft.objects.update_or_create(
                        personnel=personnel,
                        year=year,
                        month=month,
                        defaults={
                            'rows_json': rows_for_draft,
                            'updated_by': request.user,
                        }
                    )
                    self.preview_rows = rows_for_draft
                    messages.success(request, 'IPMT draft saved.')
                if action == 'load_draft':
                    if draft and isinstance(draft.rows_json, list) and draft.rows_json:
                        self.preview_rows = draft.rows_json
                        messages.success(request, 'Latest IPMT draft loaded.')
                    else:
                        messages.info(request, 'No saved draft found for this personnel and month.')
                if action == 'refresh':
                    self.preview_rows = preview_rows
                    messages.success(request, 'Preview refreshed from WAR source data.')
        return super().get(request, *args, **kwargs)

    def _merge_draft_with_preview(self, draft_rows, preview_rows):
        """
        Preserve draft edits and append only new WAR-derived content.
        - Existing draft indicators remain in place.
        - New preview indicators are appended.
        - New accomplishments under existing indicators are appended if not present.
        """
        if not isinstance(draft_rows, list):
            draft_rows = []
        if not isinstance(preview_rows, list):
            preview_rows = []

        def _norm_text(value):
            return (str(value or '').strip()).lower()

        merged = []
        indicator_index = {}

        for row in draft_rows:
            if not isinstance(row, dict):
                continue
            indicator = (row.get('indicator') or '').strip()
            if not indicator:
                continue
            accomplishments = row.get('accomplishments') or []
            if not isinstance(accomplishments, list):
                accomplishments = [str(accomplishments)]
            clean_acc = [str(a).strip() for a in accomplishments if str(a).strip()]
            payload = {
                'indicator': indicator,
                'accomplishments': clean_acc or [''],
                'comment': (row.get('comment') or '').strip(),
            }
            merged.append(payload)
            indicator_index[_norm_text(indicator)] = payload

        for row in preview_rows:
            if not isinstance(row, dict):
                continue
            indicator = (row.get('indicator') or '').strip()
            if not indicator:
                continue
            accomplishments = row.get('accomplishments') or []
            if not isinstance(accomplishments, list):
                accomplishments = [str(accomplishments)]
            clean_acc = [str(a).strip() for a in accomplishments if str(a).strip()]
            comment = (row.get('comment') or '').strip()
            key = _norm_text(indicator)
            existing = indicator_index.get(key)
            if not existing:
                payload = {
                    'indicator': indicator,
                    'accomplishments': clean_acc or [''],
                    'comment': comment,
                }
                merged.append(payload)
                indicator_index[key] = payload
                continue

            existing_set = {_norm_text(item) for item in existing.get('accomplishments') or []}
            for item in clean_acc:
                n_item = _norm_text(item)
                if n_item and n_item not in existing_set:
                    existing['accomplishments'].append(item)
                    existing_set.add(n_item)
            if not existing.get('comment') and comment:
                existing['comment'] = comment

        return merged

    def _build_preview_rows(self, personnel, year, month):
        start = _date(year, month, 1)
        if month == 12:
            end = _date(year, 12, 31)
        else:
            end = _date(year, month + 1, 1) - timedelta(days=1)
        qs = WorkAccomplishmentReport.objects.filter(
            personnel=personnel,
            period_start__lte=end,
            period_end__gte=start,
        ).select_related('request').prefetch_related('success_indicators').order_by('period_start')

        grouped = {}
        for war in qs:
            accomplishment = (war.accomplishments or war.summary or '').strip()
            if not accomplishment:
                accomplishment = f"{war.period_start:%b %d} - {war.period_end:%b %d, %Y}: Completed work activity"
            indicators = list(war.success_indicators.all())
            if not indicators:
                continue
            for indicator in indicators:
                bucket = grouped.setdefault(
                    indicator.pk,
                    {
                        "order": indicator.display_order or 0,
                        "indicator": f"{indicator.code}. {indicator.name}" if indicator.code else indicator.name,
                        "accomplishments": [],
                        "comment": "Complied",
                    },
                )
                bucket["accomplishments"].append(accomplishment)

        rows = []
        for payload in sorted(grouped.values(), key=lambda p: (p["order"], p["indicator"].lower())):
            seen = set()
            normalized = []
            for item in payload["accomplishments"]:
                key = item.lower()
                if key in seen:
                    continue
                seen.add(key)
                normalized.append(item)
            rows.append(
                {
                    "indicator": payload["indicator"],
                    "accomplishments": normalized or [""],
                    "comment": payload["comment"],
                }
            )
        if not rows:
            rows = [
                {
                    "indicator": "No success indicators tagged yet.",
                    "accomplishments": ["Tag indicators in WAR first, then regenerate IPMT."],
                    "comment": "",
                }
            ]
        return rows

    def _parse_preview_edits(self, raw_payload):
        if not raw_payload:
            return []
        try:
            payload = json.loads(raw_payload)
        except (TypeError, ValueError, json.JSONDecodeError):
            return []
        if not isinstance(payload, list):
            return []
        parsed = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            indicator = (item.get('indicator') or '').strip()
            if not indicator:
                continue
            accomplishments = item.get('accomplishments') or []
            if not isinstance(accomplishments, list):
                accomplishments = [str(accomplishments)]
            clean_acc = [str(acc).strip() for acc in accomplishments if str(acc).strip()]
            parsed.append(
                {
                    "indicator": indicator,
                    "accomplishments": clean_acc or [""],
                    "comment": (item.get('comment') or '').strip(),
                }
            )
        return parsed

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if self.request.GET:
            kwargs['data'] = self.request.GET
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'IPMT Report'
        context['page_description'] = 'Filter first, preview/edit IPMT rows, then download Excel.'
        context['preview_rows'] = getattr(self, 'preview_rows', [])
        context['preview_indicator_options'] = self._get_indicator_options(getattr(self, 'preview_personnel', None))
        context['preview_personnel'] = getattr(self, 'preview_personnel', None)
        context['preview_year'] = getattr(self, 'preview_year', None)
        context['preview_month'] = getattr(self, 'preview_month', None)
        draft = None
        if context['preview_personnel'] and context['preview_year'] and context['preview_month']:
            draft = IPMTDraft.objects.filter(
                personnel=context['preview_personnel'],
                year=context['preview_year'],
                month=context['preview_month'],
            ).first()
        context['ipmt_draft'] = draft
        return context

    def _get_indicator_options(self, personnel):
        qs = self._get_allowed_indicators_queryset(personnel)
        options = []
        for indicator in qs.order_by('display_order', 'code'):
            label = f"{indicator.code}. {indicator.name}" if indicator.code else indicator.name
            options.append(label)
        return options

    def _get_allowed_indicators_queryset(self, personnel):
        if not personnel:
            return SuccessIndicator.objects.none()
        qs = SuccessIndicator.objects.filter(is_active=True)
        qs = qs.filter(Q(target_unit__isnull=True) | Q(target_unit=personnel.unit))
        position_title = (getattr(personnel, 'position_title', '') or '').strip()
        if position_title:
            qs = qs.filter(Q(target_position='') | Q(target_position__iexact=position_title))
        else:
            qs = qs.filter(Q(target_position=''))
        return qs


@require_POST
def ipmt_generate_accomplishment_view(request):
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({'ok': False, 'error': 'Authentication required.'}, status=401)
    if getattr(user, 'is_requestor', False) or not _can_access_work_reports(user):
        return JsonResponse({'ok': False, 'error': 'You are not allowed to generate IPMT text.'}, status=403)
    if not is_ai_configured():
        return JsonResponse({'ok': False, 'error': 'AI is not configured. Set OPENROUTER_API_KEY first.'}, status=400)

    try:
        personnel_id = int((request.POST.get('personnel_id') or '').strip())
        year = int((request.POST.get('year') or '').strip())
        month = int((request.POST.get('month') or '').strip())
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'Invalid personnel or period values.'}, status=400)

    indicator_label = (request.POST.get('indicator') or '').strip()
    if not indicator_label:
        return JsonResponse({'ok': False, 'error': 'Select a success indicator first.'}, status=400)

    User = get_user_model()
    personnel = get_object_or_404(User, pk=personnel_id, role=User.Role.PERSONNEL)
    helper = IPMTReportView()
    allowed_indicators = helper._get_allowed_indicators_queryset(personnel).order_by('display_order', 'code')

    indicator_obj = None
    for indicator in allowed_indicators:
        label = f"{indicator.code}. {indicator.name}" if indicator.code else indicator.name
        if label == indicator_label:
            indicator_obj = indicator
            break
    if indicator_obj is None:
        return JsonResponse({'ok': False, 'error': 'Selected indicator is not valid for this personnel.'}, status=400)

    start = _date(year, month, 1)
    if month == 12:
        end = _date(year, 12, 31)
    else:
        end = _date(year, month + 1, 1) - timedelta(days=1)

    wars_qs = WorkAccomplishmentReport.objects.filter(
        personnel=personnel,
        period_start__lte=end,
        period_end__gte=start,
    ).select_related('request').prefetch_related('success_indicators')

    wars_for_indicator = wars_qs.filter(success_indicators=indicator_obj)
    source_qs = wars_for_indicator if wars_for_indicator.exists() else wars_qs
    war_accomplishments = []
    for war in source_qs:
        text = (war.accomplishments or war.summary or '').strip()
        if text:
            war_accomplishments.append(text)

    try:
        generated = generate_ipmt_accomplishment(
            indicator_label=indicator_label,
            indicator_description=indicator_obj.description or '',
            personnel_name=personnel.get_full_name() or personnel.username,
            unit_name=personnel.unit.name if personnel.unit_id else 'N/A',
            year=year,
            month=month,
            war_accomplishments=war_accomplishments,
        )
    except Exception:
        logger.exception(
            'IPMT accomplishment generation failed (personnel_id=%s, year=%s, month=%s, indicator=%s)',
            personnel_id,
            year,
            month,
            indicator_label,
        )
        return _safe_json_server_error(
            'Unable to generate accomplishment at the moment. Please try again later.'
        )

    return JsonResponse({'ok': True, 'accomplishment': generated.strip()})


@require_POST
def ipmt_autosave_draft_view(request):
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({'ok': False, 'error': 'Authentication required.'}, status=401)
    if getattr(user, 'is_requestor', False) or not _can_access_work_reports(user):
        return JsonResponse({'ok': False, 'error': 'You are not allowed to save IPMT drafts.'}, status=403)

    try:
        personnel_id = int((request.POST.get('personnel_id') or '').strip())
        year = int((request.POST.get('year') or '').strip())
        month = int((request.POST.get('month') or '').strip())
    except (TypeError, ValueError):
        return JsonResponse({'ok': False, 'error': 'Invalid personnel or period values.'}, status=400)

    raw_rows = request.POST.get('preview_edits', '')
    try:
        payload = json.loads(raw_rows) if raw_rows else []
    except (TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({'ok': False, 'error': 'Invalid preview payload.'}, status=400)
    if not isinstance(payload, list):
        return JsonResponse({'ok': False, 'error': 'Invalid preview rows format.'}, status=400)

    User = get_user_model()
    personnel = get_object_or_404(User, pk=personnel_id, role=User.Role.PERSONNEL)

    clean_rows = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        indicator = (item.get('indicator') or '').strip()
        if not indicator:
            continue
        accomplishments = item.get('accomplishments') or []
        if not isinstance(accomplishments, list):
            accomplishments = [str(accomplishments)]
        clean_accomplishments = [str(v).strip() for v in accomplishments if str(v).strip()]
        clean_rows.append(
            {
                'indicator': indicator,
                'accomplishments': clean_accomplishments or [''],
                'comment': (item.get('comment') or '').strip(),
            }
        )

    try:
        IPMTDraft.objects.update_or_create(
            personnel=personnel,
            year=year,
            month=month,
            defaults={
                'rows_json': clean_rows,
                'updated_by': user,
            }
        )
    except Exception:
        logger.exception(
            'IPMT autosave failed (personnel_id=%s, year=%s, month=%s, user_id=%s)',
            personnel_id,
            year,
            month,
            getattr(user, 'id', None),
        )
        return _safe_json_server_error(
            'Unable to save draft at the moment. Please try again later.'
        )
    return JsonResponse({'ok': True})


class SuccessIndicatorManageView(StaffRequiredMixin, FormView):
    """Manage IPMT success indicators from the staff Work Reports area."""
    template_name = 'staff/success_indicator_manage.html'
    form_class = SuccessIndicatorForm

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('gso_accounts:login')
        if getattr(request.user, 'is_requestor', False):
            return redirect('gso_accounts:requestor_dashboard')
        if not _can_access_work_reports(request.user):
            messages.info(request, 'Success Indicators are for GSO Office and Director only.')
            return redirect('gso_accounts:staff_dashboard')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.save()
        messages.success(self.request, 'Success indicator added.')
        return redirect('gso_accounts:staff_work_reports_success_indicators')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Success Indicators'
        context['page_description'] = 'Manage the IPMT success indicator list used when tagging WAR entries.'
        context['indicators'] = SuccessIndicator.objects.select_related('target_unit').order_by('display_order', 'code')
        return context


class SuccessIndicatorUpdateView(StaffRequiredMixin, UpdateView):
    """Edit one IPMT success indicator."""
    model = SuccessIndicator
    form_class = SuccessIndicatorForm
    template_name = 'staff/success_indicator_form.html'
    context_object_name = 'indicator'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('gso_accounts:login')
        if getattr(request.user, 'is_requestor', False):
            return redirect('gso_accounts:requestor_dashboard')
        if not _can_access_work_reports(request.user):
            messages.info(request, 'Success Indicators are for GSO Office and Director only.')
            return redirect('gso_accounts:staff_dashboard')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save()
        if self._wants_json():
            return JsonResponse({'ok': True, 'message': 'Success indicator updated.'})
        messages.success(self.request, 'Success indicator updated.')
        return super().form_valid(form)

    def form_invalid(self, form):
        if self._wants_json():
            return JsonResponse({'ok': False, 'errors': form.errors, 'non_field_errors': form.non_field_errors()}, status=400)
        return super().form_invalid(form)

    def _wants_partial(self):
        return bool(
            self.request.GET.get('partial')
            or self.request.POST.get('partial')
            or self.request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        )

    def _wants_json(self):
        accepts = (self.request.headers.get('Accept') or '').lower()
        return bool(
            self.request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            or self.request.POST.get('ajax')
            or 'application/json' in accepts
        )

    def get_template_names(self):
        if self._wants_partial():
            return ['staff/_success_indicator_edit_form.html']
        return [self.template_name]

    def get_success_url(self):
        return reverse('gso_accounts:staff_work_reports_success_indicators')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Edit Success Indicator'
        context['page_description'] = 'Update the indicator details used by WAR and IPMT.'
        return context


class WARExportView(StaffRequiredMixin, FormView):
    """Phase 6.4: Export WAR to Excel — optional filter by personnel, with month/year period."""
    form_class = WARExportForm
    template_name = 'staff/war_export.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('gso_accounts:login')
        if getattr(request.user, 'is_requestor', False):
            return redirect('gso_accounts:requestor_dashboard')
        if not _can_access_work_reports(request.user):
            messages.info(request, 'Work Reports is for GSO Office and Director only.')
            return redirect('gso_accounts:staff_dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if request.GET and request.GET.get('download') == 'excel':
            form = self.get_form()
            if not form.is_valid():
                # Common case: selected personnel is no longer valid after changing unit.
                # Fallback by dropping personnel filter so export still works.
                fallback_data = request.GET.copy()
                if 'personnel' in fallback_data:
                    fallback_data['personnel'] = ''
                fallback_form = self.form_class(data=fallback_data)
                if fallback_form.is_valid():
                    form = fallback_form
                    messages.warning(
                        request,
                        'Selected personnel filter was not valid for the chosen unit, so WAR export used broader filters.',
                    )
                else:
                    messages.error(
                        request,
                        'WAR export could not proceed because filter values are invalid. Please review filters and try again.',
                    )
                    return super().get(request, *args, **kwargs)

            personnel = form.cleaned_data.get('personnel')
            unit = form.cleaned_data.get('unit')
            year = form.cleaned_data.get('year')
            month = form.cleaned_data.get('month')
            date_from = _date(year, month, 1)
            if month == 12:
                date_to = _date(year + 1, 1, 1) - timedelta(days=1)
            else:
                date_to = _date(year, month + 1, 1) - timedelta(days=1)
            qs = get_war_queryset(personnel=personnel, unit=unit, date_from=date_from, date_to=date_to)
            buf, name_suffix = build_war_export_excel(qs, title=f"WAR_{year}_{month:02d}", unit=unit, split_by_unit_when_all=True)
            filename = f"WAR_export_{name_suffix}.xlsx"
            response = HttpResponse(
                buf.getvalue(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        return super().get(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if self.request.GET:
            kwargs['data'] = self.request.GET
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'WAR (Work Accomplishment Report)'
        context['page_description'] = 'View and export Work Accomplishment Reports. Filter by unit and month/year; personnel is optional. Table and Excel structure vary by unit.'
        today = timezone.localdate()
        context['default_filter_year'] = today.year
        context['default_filter_month'] = today.month
        form = context.get('form') or self.get_form()
        unit = None
        if form.is_bound and form.is_valid():
            unit = form.cleaned_data.get('unit')
            year = form.cleaned_data.get('year')
            month = form.cleaned_data.get('month')
            date_from = _date(year, month, 1)
            if month == 12:
                date_to = _date(year + 1, 1, 1) - timedelta(days=1)
            else:
                date_to = _date(year, month + 1, 1) - timedelta(days=1)
            qs = get_war_queryset(
                personnel=form.cleaned_data.get('personnel'),
                unit=unit,
                date_from=date_from,
                date_to=date_to,
            )
        else:
            year = today.year
            month = today.month
            date_from = _date(year, month, 1)
            if month == 12:
                date_to = _date(year + 1, 1, 1) - timedelta(days=1)
            else:
                date_to = _date(year, month + 1, 1) - timedelta(days=1)
            qs = get_war_queryset(date_from=date_from, date_to=date_to)
        context['war_list'] = list(qs[:500])  # cap for page load; export has no cap
        config_key, config = get_war_table_config(unit)
        context['war_table_config_key'] = config_key
        context['war_headers'] = config['web_headers']
        context['selected_unit'] = unit
        return context


class FeedbackReportsView(StaffRequiredMixin, FormView):
    """Phase 7.1: Director/GSO — view and export Client Satisfaction (feedback) reports. No staff submission."""
    form_class = FeedbackExportForm
    template_name = 'staff/feedback_reports.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('gso_accounts:login')
        if getattr(request.user, 'is_requestor', False):
            return redirect('gso_accounts:requestor_dashboard')
        if not _can_access_work_reports(request.user):
            messages.info(request, 'Feedback Reports is for GSO Office and Director only.')
            return redirect('gso_accounts:staff_dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if request.GET:
            form = self.get_form()
            if form.is_valid():
                date_from = form.cleaned_data.get('date_from')
                date_to = form.cleaned_data.get('date_to')
                unit = form.cleaned_data.get('unit')
                qs = get_feedback_queryset(date_from=date_from, date_to=date_to, unit=unit)
                if request.GET.get('download') == 'excel':
                    buf, _ = build_feedback_export_excel(qs)
                    from django.utils import timezone
                    suffix = timezone.now().strftime('%Y%m%d_%H%M')
                    filename = f"Feedback_export_{suffix}.xlsx"
                    response = HttpResponse(
                        buf.getvalue(),
                        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    )
                    response['Content-Disposition'] = f'attachment; filename="{filename}"'
                    return response
        return super().get(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if self.request.GET:
            kwargs['data'] = self.request.GET
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Feedback Reports'
        context['page_description'] = 'View and download Client Satisfaction Measurement (CSM) feedback submitted by requestors. Filter by date range or unit.'
        form = context.get('form')
        if form and form.is_valid():
            context['feedback_list'] = get_feedback_queryset(
                date_from=form.cleaned_data.get('date_from'),
                date_to=form.cleaned_data.get('date_to'),
                unit=form.cleaned_data.get('unit'),
            )[:100]
        else:
            context['feedback_list'] = get_feedback_queryset()[:100]
        return context
