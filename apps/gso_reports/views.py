"""Phase 6.1: WAR create. Phase 6.3/6.4: Work Reports landing, IPMT and WAR Excel export."""
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse
from django.views.generic import CreateView, FormView, TemplateView, UpdateView

from apps.gso_accounts.views import StaffRequiredMixin
from apps.gso_requests.models import Request

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
    """Work Reports landing: IPMT report and WAR export. Phase 6.3/6.4."""
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
        context['page_title'] = 'Work Reports'
        context['page_description'] = 'Generate IPMT reports and export Work Accomplishment Reports (WAR) to Excel.'
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
