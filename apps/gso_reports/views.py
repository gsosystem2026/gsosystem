"""Phase 6.1: WAR create. Phase 6.3/6.4: Work Reports landing, IPMT and WAR Excel export."""
from datetime import date as _date

from django.contrib import messages
from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F
from django.http import HttpResponse
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.generic import CreateView, FormView, TemplateView, UpdateView

from apps.gso_accounts.views import StaffRequiredMixin
from apps.gso_requests.models import Request, RequestFeedback

from .excel_export import (
    build_ipmt_excel,
    build_war_export_excel,
    build_feedback_export_excel,
    get_war_queryset,
    get_feedback_queryset,
)
from .forms import WARForm, IPMTReportForm, WARExportForm, FeedbackExportForm
from .war_config import get_war_table_config
from .models import WorkAccomplishmentReport


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
        # Unit Head (same unit), assigned Personnel, GSO, Director can add WAR
        if getattr(user, 'is_unit_head', False) and user.unit_id == req.unit_id:
            pass
        elif getattr(user, 'is_personnel', False) and req.assignments.filter(personnel=user).exists():
            pass
        elif getattr(user, 'is_gso_office', False) or getattr(user, 'is_director', False):
            pass
        else:
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
        return context

    def get_success_url(self):
        req = getattr(self, 'request_obj', None) or self.object.request
        messages.success(self.request, 'Work Accomplishment Report updated.')
        return reverse('gso_accounts:staff_request_detail', args=[req.pk])


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
                'unit_bars': unit_bars,
                'unit_distribution': unit_distribution,
                'unit_count': unit_count,
                'top_personnel': top_personnel,
                'active_range': range_key,
                'trend_points': trend_points,
            }
        )
        return context


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
                buf, _ = build_ipmt_excel(personnel, year, month)
                filename = f"IPMT_{personnel.username}_{year}_{month:02d}.xlsx"
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
        context['page_title'] = 'IPMT Report'
        context['page_description'] = 'Select personnel and period (month/year). Download Excel aligned to success indicators.'
        return context


class WARExportView(StaffRequiredMixin, FormView):
    """Phase 6.4: Export WAR to Excel — optional filter by personnel and date range. Uses GET for download."""
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
            if form.is_valid():
                personnel = form.cleaned_data.get('personnel')
                unit = form.cleaned_data.get('unit')
                date_from = form.cleaned_data.get('date_from')
                date_to = form.cleaned_data.get('date_to')
                qs = get_war_queryset(personnel=personnel, unit=unit, date_from=date_from, date_to=date_to)
                buf, name_suffix = build_war_export_excel(qs, title="WAR_Export", unit=unit)
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
        context['page_description'] = 'View and export Work Accomplishment Reports. Filter by unit, personnel, or date range. Table and Excel structure vary by unit.'
        form = context.get('form') or self.get_form()
        unit = None
        if form.is_bound and form.is_valid():
            unit = form.cleaned_data.get('unit')
            qs = get_war_queryset(
                personnel=form.cleaned_data.get('personnel'),
                unit=unit,
                date_from=form.cleaned_data.get('date_from'),
                date_to=form.cleaned_data.get('date_to'),
            )
        else:
            qs = get_war_queryset()
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
