from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
import mimetypes
from django.db import transaction

from django.http import Http404, HttpResponse, FileResponse, JsonResponse
from django.shortcuts import redirect, get_object_or_404
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import FormView, ListView, DetailView, UpdateView
import csv

from apps.gso_accounts.views import StaffRequiredMixin
from apps.gso_units.models import Unit

from .forms import RequestForm, RequestorCancelForm, AssignPersonnelForm, RequestMessageForm, RequestFeedbackForm
from .models import Request, RequestAssignment, RequestMessage, RequestFeedback
from apps.gso_reports.models import ensure_war_for_request

INSPECTION_REQUIRED_UNIT_CODES = {'repair', 'electrical'}
SINGLE_SUBMISSION_UNIT_CODES = {'motorpool'}


def _requires_inspection(request_obj):
    code = ((request_obj.unit.code if request_obj.unit_id else '') or '').lower()
    return code in INSPECTION_REQUIRED_UNIT_CODES


class RequestCreateView(LoginRequiredMixin, FormView):
    """Requestor: one shared form for all units; creates one request per selected unit."""
    form_class = RequestForm
    template_name = 'requestor/request_new.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('gso_accounts:login')
        if getattr(request.user, 'is_staff_role', False):
            return redirect('gso_accounts:staff_dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        units_param = self.request.GET.get('units', '')
        codes = [c.strip() for c in units_param.split(',') if c.strip()]
        units = list(Unit.objects.filter(code__in=codes, is_active=True).order_by('name'))
        if len(units) == 1:
            initial['unit'] = units[0].pk
        return initial

    def get(self, request, *args, **kwargs):
        units_param = request.GET.get('units', '')
        codes = [c.strip() for c in units_param.split(',') if c.strip()]
        if not codes or not Unit.objects.filter(code__in=codes, is_active=True).exists():
            return redirect('gso_accounts:requestor_dashboard')
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        units_param = self.request.GET.get('units', '')
        codes = [c.strip() for c in units_param.split(',') if c.strip()]
        context['selected_units'] = list(Unit.objects.filter(code__in=codes, is_active=True).order_by('name'))
        context['units_param'] = units_param
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        units_param = self.request.GET.get('units') or self.request.POST.get('units', '')
        codes = [c.strip() for c in units_param.split(',') if c.strip()]
        selected = list(Unit.objects.filter(code__in=codes, is_active=True))
        # When units come from param (single or multiple), don't use form's unit field
        if selected:
            form.fields.pop('unit', None)
        return form

    def form_valid(self, form):
        units_param = self.request.POST.get('units') or self.request.GET.get('units', '')
        codes = [c.strip() for c in units_param.split(',') if c.strip()]
        selected_codes = {c.lower() for c in codes}
        if any(code in selected_codes for code in SINGLE_SUBMISSION_UNIT_CODES) and len(selected_codes) > 1:
            form.add_error(
                None,
                'Motorpool requests must be submitted separately because they use a different request form.'
            )
            return self.form_invalid(form)
        units = list(Unit.objects.filter(code__in=codes, is_active=True))
        if not units:
            form.add_error(None, 'No valid unit selected. Please go back and select at least one unit.')
            return self.form_invalid(form)

        data = {k: v for k, v in form.cleaned_data.items() if k != 'unit'}
        attachment = data.pop('attachment', None)
        data['requestor'] = self.request.user
        data['status'] = Request.Status.SUBMITTED

        from apps.gso_notifications.utils import notify_request_submitted

        with transaction.atomic():
            for i, unit in enumerate(units):
                data['unit'] = unit
                data['attachment'] = attachment if i == 0 else None
                req = Request.objects.create(**data)
                notify_request_submitted(req)

        return redirect(reverse('gso_accounts:requestor_dashboard') + '?submitted=1')

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form))


class RequestEditView(LoginRequiredMixin, UpdateView):
    """Requestor: edit their request. Only when status is Draft or Submitted (no personnel assigned, not yet approved)."""
    model = Request
    form_class = RequestForm
    template_name = 'requestor/request_edit.html'
    context_object_name = 'req'

    def _wants_partial(self):
        return bool(
            self.request.GET.get('partial')
            or self.request.POST.get('partial')
            or self.request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        )

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('gso_accounts:login')
        if getattr(request.user, 'is_staff_role', False):
            return redirect('gso_accounts:staff_dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Request.objects.filter(requestor=self.request.user).select_related('unit')

    def get_template_names(self):
        if self._wants_partial():
            return ['requestor/request_edit_partial.html']
        return [self.template_name]

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.status not in (Request.Status.DRAFT, Request.Status.SUBMITTED):
            messages.warning(request, 'You can only edit a request before personnel are assigned or the request is approved.')
            return redirect('gso_requests:requestor_request_detail', pk=self.object.pk)
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        # Keep unit unchanged on edit
        form.instance.unit_id = self.object.unit_id
        response = super().form_valid(form)
        from apps.gso_accounts.models import log_audit
        log_audit(
            'requestor_edit_request',
            self.request.user,
            f'Request {self.object.display_id} edited by {self.request.user.get_full_name() or self.request.user.username}',
            target_model='gso_requests.Request',
            target_id=str(self.object.pk),
        )
        from apps.gso_notifications.utils import notify_requestor_edited_request
        notify_requestor_edited_request(self.object)
        messages.success(self.request, 'Your request has been updated.')
        if self._wants_partial():
            detail_url = reverse('gso_requests:requestor_request_detail', args=[self.object.pk])
            return redirect(f'{detail_url}?partial=1&modal=1&updated=1')
        return response

    def get_success_url(self):
        return reverse('gso_requests:requestor_request_detail', args=[self.object.pk])

    def form_invalid(self, form):
        if self._wants_partial():
            return TemplateResponse(
                self.request,
                self.get_template_names(),
                self.get_context_data(form=form),
                status=400,
            )
        return super().form_invalid(form)


class RequestCancelView(LoginRequiredMixin, View):
    """Requestor: cancel their request with a reason. Only before work has started (Draft, Submitted, Assigned)."""
    http_method_names = ['post']

    def post(self, request, pk):
        req = get_object_or_404(Request.objects.select_related('unit'), pk=pk)
        user = request.user
        if not getattr(user, 'is_requestor', False) or req.requestor_id != user.id:
            messages.error(request, 'Only the requestor can cancel this request.')
            return redirect('gso_requests:requestor_request_detail', pk=pk)
        if req.status not in (Request.Status.DRAFT, Request.Status.SUBMITTED, Request.Status.ASSIGNED):
            messages.warning(request, 'You can only cancel a request before work has started.')
            return redirect('gso_requests:requestor_request_detail', pk=pk)
        form = RequestorCancelForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Please provide a reason for cancellation.')
            return redirect('gso_requests:requestor_request_detail', pk=pk)
        reason = form.cleaned_data['reason'].strip()
        req.status = Request.Status.CANCELLED
        req.requestor_cancel_reason = reason
        req.requestor_cancelled_at = timezone.now()
        req.save(update_fields=['status', 'requestor_cancel_reason', 'requestor_cancelled_at', 'updated_at'])
        from apps.gso_accounts.models import log_audit
        log_audit(
            'requestor_cancel_request',
            user,
            f'Request {req.display_id} cancelled by requestor. Reason: {reason[:200]}{"…" if len(reason) > 200 else ""}',
            target_model='gso_requests.Request',
            target_id=str(req.pk),
        )
        from apps.gso_notifications.utils import notify_requestor_cancelled_request
        notify_requestor_cancelled_request(req)
        messages.success(request, 'Your request has been cancelled.')
        return redirect('gso_requests:requestor_request_detail', pk=pk)


def _staff_request_queryset(request):
    """Requests visible to current user by role: Unit Head = their unit; GSO/Director = all (optional unit filter)."""
    from apps.gso_accounts.models import User
    user = request.user
    if not isinstance(user, User):
        return Request.objects.none()
    if user.is_unit_head and user.unit_id:
        qs = Request.objects.filter(unit_id=user.unit_id)
    elif user.is_gso_office or user.is_director:
        qs = Request.objects.all()
        unit_filter = request.GET.get('unit')
        if unit_filter:
            qs = qs.filter(unit_id=unit_filter)
    else:
        # Personnel: later Phase 4 can filter by assigned; for now same as unit head if has unit
        qs = Request.objects.filter(unit_id=user.unit_id) if user.unit_id else Request.objects.none()
    return qs.order_by('-created_at')


class StaffRequestListView(StaffRequiredMixin, ListView):
    """Staff: Request Management — list requests (Unit Head: own unit; GSO/Director: all, optional unit filter)."""
    model = Request
    template_name = 'staff/request_list.html'
    context_object_name = 'request_list'
    paginate_by = 10

    def get_queryset(self):
        qs = _staff_request_queryset(self.request)
        # Request Management: show only active lifecycle (exclude Completed / Cancelled)
        qs = qs.exclude(status__in=(Request.Status.COMPLETED, Request.Status.CANCELLED))
        # Optional filter by status within active set
        status = self.request.GET.get('status', '').strip()
        if status:
            qs = qs.filter(status=status)
        # Optional filter by personnel (assigned to)
        personnel_id = self.request.GET.get('personnel', '').strip()
        if personnel_id:
            qs = qs.filter(assignments__personnel_id=personnel_id)
        # Search by request ID, purpose, location, requestor name, or unit
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
        return qs.select_related('requestor', 'unit').order_by('-is_emergency', '-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Request Management'
        context['page_description'] = 'View and manage active service requests.'
        context['units'] = Unit.objects.filter(is_active=True).order_by('name')
        context['unit_filter'] = self.request.GET.get('unit', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['search_q'] = self.request.GET.get('q', '')
        # Active statuses only for status filter
        context['status_choices'] = [
            (Request.Status.SUBMITTED, 'Submitted'),
            (Request.Status.ASSIGNED, 'Assigned'),
            (Request.Status.DIRECTOR_APPROVED, 'Approved'),
            (Request.Status.INSPECTION, 'Inspection'),
            (Request.Status.IN_PROGRESS, 'In Progress'),
            (Request.Status.ON_HOLD, 'On Hold'),
            (Request.Status.DONE_WORKING, 'Done working'),
        ]
        return context


class RequestDetailView(LoginRequiredMixin, DetailView):
    """Request detail — requestor (own), Unit Head (their unit), GSO/Director (all)."""
    model = Request
    context_object_name = 'req'

    def get_template_names(self):
        if getattr(self.request.user, 'is_requestor', False):
            if self.request.GET.get('partial') or self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return ['requestor/request_detail_partial.html']
            return ['requestor/request_detail.html']
        if self.request.GET.get('partial') or self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return ['staff/request_detail_partial.html']
        return ['staff/request_detail.html']

    def get_queryset(self):
        return Request.objects.select_related('unit', 'requestor')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('gso_accounts:login')
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        obj = super().get_object(queryset=queryset)
        user = self.request.user
        if getattr(user, 'is_requestor', False):
            if obj.requestor_id != user.id:
                raise Http404()
        elif getattr(user, 'is_unit_head', False) or getattr(user, 'is_personnel', False):
            if user.unit_id != obj.unit_id:
                raise Http404()
        elif not (getattr(user, 'is_gso_office', False) or getattr(user, 'is_director', False)):
            raise Http404()
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['is_requestor_layout'] = getattr(user, 'is_requestor', False)
        context['in_modal'] = self.request.GET.get('modal') == '1'
        req = self.object
        # Phase 4.1: assignments and assign form for Unit Head
        context['assignments'] = []
        context['can_assign'] = False
        context['assign_form'] = None
        if not context['is_requestor_layout'] and req:
            context['assignments'] = req.assignments.select_related('personnel', 'assigned_by').order_by('assigned_at')
            if getattr(user, 'is_unit_head', False) and user.unit_id == req.unit_id and req.status in (Request.Status.SUBMITTED, Request.Status.ASSIGNED):
                context['can_assign'] = True
                assign_form = AssignPersonnelForm(unit_id=req.unit_id, request_obj=req)
                # For each available personnel, attach a list of their other active requests
                # so the Unit Head can see current workload when assigning.
                from .models import RequestAssignment
                candidates = list(assign_form.fields['personnel'].queryset or [])
                if candidates:
                    personnel_map = {p.pk: p for p in candidates}
                    for p in candidates:
                        p.active_requests_for_assignment = []
                    active_statuses = (
                        Request.Status.SUBMITTED,
                        Request.Status.ASSIGNED,
                        Request.Status.DIRECTOR_APPROVED,
                        Request.Status.IN_PROGRESS,
                        Request.Status.ON_HOLD,
                        Request.Status.DONE_WORKING,
                    )
                    active_assignments = RequestAssignment.objects.filter(
                        personnel_id__in=personnel_map.keys(),
                        request__status__in=active_statuses,
                    ).exclude(request=req).select_related('request').order_by('-request__updated_at')
                    for a in active_assignments:
                        p = personnel_map.get(a.personnel_id)
                        if p is not None:
                            p.active_requests_for_assignment.append(a.request)
                context['assign_form'] = assign_form
            # Phase 4.2/4.3: Director or designated OIC can approve — GSO Office (non-OIC) sees no button
            context['can_approve'] = (
                getattr(user, 'can_approve_requests', False)
                and req.status == Request.Status.ASSIGNED
            )
            # Phase 5.1: Personnel (assigned) can update work status
            is_assigned = req.assignments.filter(personnel=user).exists()
            context['can_update_work_status'] = (
                getattr(user, 'is_personnel', False) and is_assigned
                and req.status in (
                    Request.Status.DIRECTOR_APPROVED,
                    Request.Status.INSPECTION,
                    Request.Status.IN_PROGRESS,
                    Request.Status.ON_HOLD,
                )
            )
            context['is_personnel_waiting_approval'] = (
                getattr(user, 'is_personnel', False)
                and is_assigned
                and req.status == Request.Status.ASSIGNED
            )
            # Phase 5.3: Unit Head can complete when Done working
            context['can_complete'] = (
                getattr(user, 'is_unit_head', False) and user.unit_id == req.unit_id
                and req.status == Request.Status.DONE_WORKING
            )
            # Phase 5.2: Chat messages and form (staff only) — only after Director/OIC approval and until completed
            chat_allowed_statuses = (
                Request.Status.DIRECTOR_APPROVED,
                Request.Status.INSPECTION,
                Request.Status.IN_PROGRESS,
                Request.Status.ON_HOLD,
                Request.Status.DONE_WORKING,
            )
            if req.status in chat_allowed_statuses:
                context['request_messages'] = req.messages.select_related('user').order_by('created_at')
                context['message_form'] = RequestMessageForm()
            else:
                context['request_messages'] = []
                context['message_form'] = None
            if self.request.GET.get('from') == 'history':
                context['staff_back_url'] = reverse('gso_accounts:staff_request_history')
            elif self.request.GET.get('from') == 'task_history':
                context['staff_back_url'] = reverse('gso_accounts:staff_task_history')
            else:
                context['staff_back_url'] = reverse('gso_accounts:staff_task_management') if getattr(user, 'is_personnel', False) else reverse('gso_accounts:staff_request_management')
            # GSO Office: Send reminder to Director, Unit Head, or Personnel
            context['can_send_reminder'] = getattr(user, 'is_gso_office', False)
            context['remind_targets'] = []
            if context['can_send_reminder'] and req.status not in (Request.Status.COMPLETED, Request.Status.CANCELLED):
                if req.status == Request.Status.ASSIGNED:
                    context['remind_targets'].append(('director', 'Director', 'Request waiting for your approval'))
                if req.status == Request.Status.SUBMITTED:
                    context['remind_targets'].append(('unit_head', 'Unit Head', 'Request needs personnel assignment'))
                if req.status == Request.Status.DONE_WORKING:
                    context['remind_targets'].append(('unit_head', 'Unit Head', 'Work done — needs to be marked completed'))
                if req.status in (
                    Request.Status.DIRECTOR_APPROVED,
                    Request.Status.INSPECTION,
                    Request.Status.IN_PROGRESS,
                    Request.Status.ON_HOLD,
                ) and req.assignments.exists():
                    context['remind_targets'].append(('personnel', 'Assigned personnel', 'Request needs your attention'))
            # Materials issued to this request (Unit Head can add; deducts from inventory)
            context['materials_issued'] = req.inventory_issues.select_related('item', 'performed_by').order_by('-created_at')
            context['can_add_materials'] = (
                getattr(user, 'is_unit_head', False)
                and user.unit_id == req.unit_id
                and req.status not in (Request.Status.COMPLETED, Request.Status.CANCELLED)
            )
            if context['can_add_materials']:
                from apps.gso_inventory.forms import IssueMaterialForm
                context['issue_material_form'] = IssueMaterialForm(unit_id=req.unit_id, prefix='issue')
            else:
                context['issue_material_form'] = None
            # Personnel material requests (deduct only after Unit Head approves)
            context['material_requests'] = req.material_requests.select_related(
                'item', 'requested_by', 'approved_by'
            ).order_by('-created_at')
            context['can_request_materials'] = (
                getattr(user, 'is_personnel', False)
                and req.assignments.filter(personnel=user).exists()
                and req.status in (
                    Request.Status.DIRECTOR_APPROVED,
                    Request.Status.INSPECTION,
                    Request.Status.IN_PROGRESS,
                    Request.Status.ON_HOLD,
                )
            )
            if context['can_request_materials']:
                from apps.gso_inventory.forms import RequestMaterialForm
                context['request_material_form'] = RequestMaterialForm(unit_id=req.unit_id, prefix='request')
            else:
                context['request_material_form'] = None
            context['can_approve_reject_materials'] = (
                getattr(user, 'is_unit_head', False)
                and user.unit_id == req.unit_id
                and req.status not in (Request.Status.COMPLETED, Request.Status.CANCELLED)
            )
            # Phase 6.1: Work Accomplishment Reports (completed requests only)
            # Only GSO Office and Director can view/edit WARs; Unit Head/Personnel do not see WAR section.
            is_war_allowed_role = getattr(user, 'is_gso_office', False) or getattr(user, 'is_director', False)
            context['show_war_section'] = is_war_allowed_role and (req.status == Request.Status.COMPLETED)
            context['war_list'] = []
            context['can_add_war'] = False
            context['can_edit_war'] = False
            if context['show_war_section']:
                context['war_list'] = req.work_accomplishment_reports.select_related('personnel', 'created_by').prefetch_related('success_indicators').order_by('-created_at')
                context['can_edit_war'] = bool(context['war_list'])
        # Requestor: can edit (only Draft/Submitted) or cancel (only before work started: Draft, Submitted, Assigned)
        if req and getattr(user, 'is_requestor', False) and req.requestor_id == user.id:
            context['can_requestor_edit'] = req.status in (Request.Status.DRAFT, Request.Status.SUBMITTED)
            context['can_requestor_cancel'] = req.status in (Request.Status.DRAFT, Request.Status.SUBMITTED, Request.Status.ASSIGNED)
            context['requestor_cancel_form'] = RequestorCancelForm() if context['can_requestor_cancel'] else None
        else:
            context['can_requestor_edit'] = False
            context['can_requestor_cancel'] = False
            context['requestor_cancel_form'] = None
        # Phase 7.1: Feedback — requestor only, for completed requests; one submission per request
        if req:
            context['feedback_list'] = req.feedback.select_related('user').order_by('-created_at')
            context['user_has_feedback'] = req.feedback.filter(user=user).exists()
            context['show_feedback_form'] = (
                getattr(user, 'is_requestor', False)
                and req.requestor_id == user.id
                and req.status == Request.Status.COMPLETED
                and not context['user_has_feedback']
            )
            context['feedback_form'] = RequestFeedbackForm() if context['show_feedback_form'] else None
            context['sqd_labels'] = RequestFeedback.SQD_LABELS if context.get('show_feedback_form') else []
        return context


class RequestAttachmentView(LoginRequiredMixin, View):
    """Serve request attachment with same permission as request detail (requestor / unit head / personnel / GSO / director)."""

    def get(self, request, pk):
        req = get_object_or_404(Request.objects.select_related('unit'), pk=pk)
        user = request.user
        # Same rules as RequestDetailView.get_object()
        if getattr(user, 'is_requestor', False):
            if req.requestor_id != user.id:
                raise Http404()
        elif getattr(user, 'is_unit_head', False) or getattr(user, 'is_personnel', False):
            if user.unit_id != req.unit_id:
                raise Http404()
        elif not (getattr(user, 'is_gso_office', False) or getattr(user, 'is_director', False)):
            raise Http404()
        if not req.attachment:
            raise Http404()

        try:
            req.attachment.open('rb')
        except Exception as exc:
            raise Http404() from exc

        disposition = 'attachment' if request.GET.get('download') else 'inline'
        filename = req.attachment.name.rsplit('::', 1)[-1].rsplit('/', 1)[-1]
        content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        response = FileResponse(
            req.attachment.file,
            content_type=content_type,
            as_attachment=(disposition == 'attachment'),
        )
        response['Content-Disposition'] = f'{disposition}; filename="{filename}"'
        return response


class AssignPersonnelView(LoginRequiredMixin, View):
    """Phase 4.1: Unit Head assigns personnel to a request (POST only). Sets status to ASSIGNED."""
    http_method_names = ['post']

    def post(self, request, pk):
        from apps.gso_accounts.models import User
        req = get_object_or_404(Request.objects.select_related('unit'), pk=pk)
        user = request.user
        if not getattr(user, 'is_unit_head', False) or user.unit_id != req.unit_id:
            messages.error(request, 'Only the Unit Head for this request\'s unit can assign personnel.')
            return redirect('gso_accounts:staff_request_detail', pk=pk)
        if req.status not in (Request.Status.SUBMITTED, Request.Status.ASSIGNED):
            messages.warning(request, 'Personnel can only be assigned when the request is Submitted or Assigned.')
            return redirect('gso_accounts:staff_request_detail', pk=pk)
        form = AssignPersonnelForm(request.POST, unit_id=req.unit_id, request_obj=req)
        if not form.is_valid():
            messages.error(request, 'Please select at least one personnel to assign.')
            return redirect('gso_accounts:staff_request_detail', pk=pk)
        for personnel in form.cleaned_data['personnel']:
            RequestAssignment.objects.get_or_create(
                request=req,
                personnel=personnel,
                defaults={'assigned_by': user},
            )
        if req.status == Request.Status.SUBMITTED:
            req.status = Request.Status.ASSIGNED
            req.save(update_fields=['status', 'updated_at'])
        # is_emergency is managed via the Emergency flag section (ToggleEmergencyView)
        from apps.gso_notifications.utils import notify_personnel_assigned
        notify_personnel_assigned(req)
        names = ', '.join((p.get_full_name() or p.username for p in form.cleaned_data['personnel']))
        messages.success(request, f'Assigned {names}. Status set to Assigned (waiting Director approval).')
        return redirect('gso_accounts:staff_request_detail', pk=pk)


class ToggleEmergencyView(LoginRequiredMixin, View):
    """Unit Head toggles is_emergency on a request."""
    http_method_names = ['post']

    def post(self, request, pk):
        req = get_object_or_404(Request, pk=pk)
        user = request.user
        if not getattr(user, 'is_unit_head', False) or user.unit_id != req.unit_id:
            messages.error(request, 'Only the Unit Head for this request\'s unit can mark as emergency.')
            return redirect('gso_accounts:staff_request_detail', pk=pk)
        req.is_emergency = not req.is_emergency
        req.save(update_fields=['is_emergency', 'updated_at'])
        label = 'Emergency' if req.is_emergency else 'Normal'
        messages.success(request, f'Request marked as {label}.')
        return redirect('gso_accounts:staff_request_detail', pk=pk)


class StaffRequestRemindView(LoginRequiredMixin, View):
    """GSO Office sends a reminder notification to Director, Unit Head, or Personnel about a pending request."""
    http_method_names = ['post']

    def post(self, request, pk):
        req = get_object_or_404(Request.objects.select_related('unit'), pk=pk)
        user = request.user
        if not getattr(user, 'is_gso_office', False):
            messages.error(request, 'Only GSO Office can send reminder notifications.')
            return redirect('gso_accounts:staff_request_detail', pk=pk)
        target = (request.POST.get('target') or '').strip()
        if target not in ('director', 'unit_head', 'personnel'):
            messages.error(request, 'Invalid reminder target.')
            return redirect('gso_accounts:staff_request_detail', pk=pk)
        # Validate target makes sense for current status
        if target == 'director' and req.status != Request.Status.ASSIGNED:
            messages.warning(request, 'Director reminder is only for requests waiting approval (Assigned).')
            return redirect('gso_accounts:staff_request_detail', pk=pk)
        if target == 'unit_head' and req.status not in (Request.Status.SUBMITTED, Request.Status.DONE_WORKING):
            messages.warning(request, 'Unit Head reminder is for requests needing assignment or completion.')
            return redirect('gso_accounts:staff_request_detail', pk=pk)
        if target == 'personnel' and req.status not in (
            Request.Status.DIRECTOR_APPROVED,
            Request.Status.INSPECTION,
            Request.Status.IN_PROGRESS,
            Request.Status.ON_HOLD,
        ):
            messages.warning(request, 'Personnel reminder is for requests with assigned work in progress.')
            return redirect('gso_accounts:staff_request_detail', pk=pk)
        if target == 'personnel' and not req.assignments.exists():
            messages.warning(request, 'No personnel assigned to this request.')
            return redirect('gso_accounts:staff_request_detail', pk=pk)
        from apps.gso_notifications.utils import notify_gso_reminder
        notify_gso_reminder(req, target)
        labels = {'director': 'Director', 'unit_head': 'Unit Head', 'personnel': 'Assigned personnel'}
        messages.success(request, f'Reminder sent to {labels[target]}.')
        return redirect('gso_accounts:staff_request_detail', pk=pk)


class ApproveRequestView(LoginRequiredMixin, View):
    """Phase 4.2: Director approves request so work can start. GSO Office cannot approve."""
    http_method_names = ['post']

    def post(self, request, pk):
        req = get_object_or_404(Request.objects.select_related('unit'), pk=pk)
        user = request.user
        if not getattr(user, 'can_approve_requests', False):
            messages.error(request, 'Only the Director or designated OIC can approve requests for work to start.')
            return redirect('gso_accounts:staff_request_detail', pk=pk)
        if req.status != Request.Status.ASSIGNED:
            messages.warning(request, 'Only Assigned requests can be approved.')
            return redirect('gso_accounts:staff_request_detail', pk=pk)
        req.status = Request.Status.DIRECTOR_APPROVED
        req.save(update_fields=['status', 'updated_at'])
        from apps.gso_notifications.utils import notify_director_approved
        notify_director_approved(req)
        from apps.gso_accounts.models import log_audit
        log_audit('director_approve', user, f'Approved request {req.display_id}: {req.title}', target_model='gso_requests.Request', target_id=str(req.pk))
        messages.success(request, f'Request {req.display_id} approved. Personnel can start work.')
        return redirect('gso_accounts:staff_request_detail', pk=pk)


# --- Phase 5: Work execution & completion ---

WORK_STATUS_ALLOWED = (
    Request.Status.INSPECTION,
    Request.Status.IN_PROGRESS,
    Request.Status.ON_HOLD,
    Request.Status.DONE_WORKING,
)


class UpdateWorkStatusView(LoginRequiredMixin, View):
    """Phase 5.1: Personnel set work status (In Progress, On Hold, Done working)."""
    http_method_names = ['post']

    def post(self, request, pk):
        req = get_object_or_404(Request.objects.select_related('unit'), pk=pk)
        user = request.user
        if not getattr(user, 'is_personnel', False):
            messages.error(request, 'Only assigned personnel can update work status.')
            return redirect('gso_accounts:staff_request_detail', pk=pk)
        if not req.assignments.filter(personnel=user).exists():
            messages.error(request, 'You are not assigned to this request.')
            return redirect('gso_accounts:staff_request_detail', pk=pk)
        new_status = request.POST.get('status', '').strip()
        if new_status not in (s for s, _ in Request.Status.choices if s in WORK_STATUS_ALLOWED):
            messages.error(request, 'Invalid status.')
            return redirect('gso_accounts:staff_request_detail', pk=pk)
        if req.status == Request.Status.DIRECTOR_APPROVED:
            if _requires_inspection(req):
                allowed_from_approved = (Request.Status.INSPECTION, Request.Status.IN_PROGRESS)
                if new_status not in allowed_from_approved:
                    messages.error(request, 'From Approved you can only set Inspection or In Progress for this unit.')
                    return redirect('gso_accounts:staff_request_detail', pk=pk)
            elif new_status not in (Request.Status.IN_PROGRESS, Request.Status.ON_HOLD):
                messages.error(request, 'From Approved you can only set In Progress or On Hold.')
                return redirect('gso_accounts:staff_request_detail', pk=pk)
        if req.status == Request.Status.INSPECTION and new_status not in (Request.Status.IN_PROGRESS, Request.Status.ON_HOLD):
            messages.error(request, 'From Inspection you can only set In Progress or On Hold.')
            return redirect('gso_accounts:staff_request_detail', pk=pk)
        if req.status == Request.Status.IN_PROGRESS and new_status not in (Request.Status.ON_HOLD, Request.Status.DONE_WORKING):
            messages.error(request, 'From In Progress you can only set On Hold or Done working.')
            return redirect('gso_accounts:staff_request_detail', pk=pk)
        if req.status == Request.Status.ON_HOLD and new_status not in (Request.Status.IN_PROGRESS, Request.Status.DONE_WORKING):
            messages.error(request, 'From On Hold you can only set In Progress or Done working.')
            return redirect('gso_accounts:staff_request_detail', pk=pk)
        old_status = req.status
        req.status = new_status
        update_fields = ['status', 'updated_at']
        if new_status == Request.Status.IN_PROGRESS and not req.work_started_at:
            req.work_started_at = timezone.now()
            update_fields.append('work_started_at')
        req.save(update_fields=update_fields)
        from apps.gso_notifications.utils import notify_after_personnel_work_status_change
        notify_after_personnel_work_status_change(req, old_status, new_status)
        messages.success(request, f'Status set to {req.get_status_display()}.')
        return redirect('gso_accounts:staff_request_detail', pk=pk)


class CompleteRequestView(LoginRequiredMixin, View):
    """Phase 5.3: Unit Head marks request Completed after personnel Done working."""
    http_method_names = ['post']

    def post(self, request, pk):
        req = get_object_or_404(Request.objects.select_related('unit'), pk=pk)
        user = request.user
        if not getattr(user, 'is_unit_head', False) or user.unit_id != req.unit_id:
            messages.error(request, 'Only the Unit Head for this request\'s unit can complete it.')
            return redirect('gso_accounts:staff_request_detail', pk=pk)
        if req.status != Request.Status.DONE_WORKING:
            messages.warning(request, 'Only requests with status Done working can be completed.')
            return redirect('gso_accounts:staff_request_detail', pk=pk)
        req.status = Request.Status.COMPLETED
        req.save(update_fields=['status', 'updated_at'])
        # Auto-create WAR entries (one per assigned personnel) for completed requests
        ensure_war_for_request(req, created_by=user)
        from apps.gso_notifications.utils import notify_request_completed
        notify_request_completed(req)
        messages.success(request, f'Request {req.display_id} marked completed.')
        return redirect('gso_accounts:staff_request_detail', pk=pk)


class ReturnForReworkView(LoginRequiredMixin, View):
    """Unit Head returns request to personnel when work is not satisfactory (Done working → In Progress)."""
    http_method_names = ['post']

    def post(self, request, pk):
        req = get_object_or_404(Request.objects.select_related('unit'), pk=pk)
        user = request.user
        if not getattr(user, 'is_unit_head', False) or user.unit_id != req.unit_id:
            messages.error(request, 'Only the Unit Head for this request\'s unit can return it for rework.')
            return redirect('gso_accounts:staff_request_detail', pk=pk)
        if req.status != Request.Status.DONE_WORKING:
            messages.warning(request, 'Only requests with status Done working can be returned for rework.')
            return redirect('gso_accounts:staff_request_detail', pk=pk)
        req.status = Request.Status.IN_PROGRESS
        req.save(update_fields=['status', 'updated_at'])
        from apps.gso_notifications.utils import notify_returned_for_rework
        notify_returned_for_rework(req)
        messages.success(request, f'Request {req.display_id} returned for rework. Personnel have been notified.')
        return redirect('gso_accounts:staff_request_detail', pk=pk)


class AddRequestMessageView(LoginRequiredMixin, View):
    """Phase 5.2: Staff post messages on a request only after Director/OIC approval and until completed."""
    http_method_names = ['post']

    def post(self, request, pk):
        req = get_object_or_404(Request.objects.select_related('unit'), pk=pk)
        user = request.user
        if getattr(user, 'is_requestor', False):
            messages.error(request, 'Only staff can post messages here.')
            return redirect('gso_accounts:staff_request_detail', pk=pk)
        if getattr(user, 'is_unit_head', False) or getattr(user, 'is_personnel', False):
            if user.unit_id != req.unit_id:
                raise Http404()
        chat_allowed = req.status in (
            Request.Status.DIRECTOR_APPROVED,
            Request.Status.INSPECTION,
            Request.Status.IN_PROGRESS,
            Request.Status.ON_HOLD,
            Request.Status.DONE_WORKING,
        )
        if not chat_allowed:
            messages.error(request, 'Chat is only available after the request is approved and until it is completed.')
            return redirect('gso_accounts:staff_request_detail', pk=pk)
        form = RequestMessageForm(request.POST)
        if form.is_valid():
            RequestMessage.objects.create(request=req, user=user, message=form.cleaned_data['message'])
            messages.success(request, 'Message added.')
        return redirect('gso_accounts:staff_request_detail', pk=pk)


class SubmitFeedbackView(LoginRequiredMixin, View):
    """Phase 7.1: Submit CSM feedback. Requestor only, for completed requests; one per request."""
    http_method_names = ['post']

    def _is_ajax(self, request):
        return request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    def post(self, request, pk):
        req = get_object_or_404(Request.objects.select_related('unit'), pk=pk)
        user = request.user
        if not getattr(user, 'is_requestor', False) or req.requestor_id != user.id:
            msg = 'Only the requestor can submit feedback for this request.'
            if self._is_ajax(request):
                return JsonResponse({'ok': False, 'error': msg}, status=403)
            messages.error(request, msg)
            return redirect('gso_requests:requestor_request_detail', pk=pk)
        if req.status != Request.Status.COMPLETED:
            msg = 'Feedback can only be submitted for completed requests.'
            if self._is_ajax(request):
                return JsonResponse({'ok': False, 'error': msg}, status=400)
            messages.warning(request, msg)
            return redirect('gso_requests:requestor_request_detail', pk=pk)
        if req.feedback.filter(user=user).exists():
            msg = 'You have already submitted feedback for this request.'
            if self._is_ajax(request):
                return JsonResponse({'ok': False, 'error': msg}, status=400)
            messages.warning(request, msg)
            return redirect('gso_requests:requestor_request_detail', pk=pk)
        form = RequestFeedbackForm(request.POST)
        if form.is_valid():
            RequestFeedback.objects.create(
                request=req,
                user=user,
                cc1=form.cleaned_data.get('cc1', ''),
                cc2=form.cleaned_data.get('cc2', ''),
                cc3=form.cleaned_data.get('cc3', ''),
                sqd1=form.cleaned_data.get('sqd1'),
                sqd2=form.cleaned_data.get('sqd2'),
                sqd3=form.cleaned_data.get('sqd3'),
                sqd4=form.cleaned_data.get('sqd4'),
                sqd5=form.cleaned_data.get('sqd5'),
                sqd6=form.cleaned_data.get('sqd6'),
                sqd7=form.cleaned_data.get('sqd7'),
                sqd8=form.cleaned_data.get('sqd8'),
                sqd9=form.cleaned_data.get('sqd9'),
                suggestions=form.cleaned_data.get('suggestions', ''),
                email=form.cleaned_data.get('email', ''),
            )
            success_msg = 'Thank you. Your feedback has been submitted.'
            if self._is_ajax(request):
                return JsonResponse({'ok': True, 'message': success_msg})
            messages.success(request, success_msg)
        else:
            err_msg = 'Please complete the required fields (CC1 and SQD1–SQD9).'
            if self._is_ajax(request):
                return JsonResponse({'ok': False, 'error': err_msg}, status=400)
            messages.error(request, err_msg)
        return redirect('gso_requests:requestor_request_detail', pk=pk)


class PersonnelTaskListView(StaffRequiredMixin, ListView):
    """Phase 5: Personnel — list of requests assigned to me (active: Director Approved → Done working)."""
    model = Request
    template_name = 'staff/task_list.html'
    context_object_name = 'task_list'
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        if not getattr(request.user, 'is_personnel', False):
            messages.info(request, 'Task Management is for Personnel only.')
            return redirect('gso_accounts:staff_dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return (
            Request.objects.filter(
                assignments__personnel=self.request.user,
                status__in=(
                    Request.Status.DIRECTOR_APPROVED,
                    Request.Status.INSPECTION,
                    Request.Status.IN_PROGRESS,
                    Request.Status.ON_HOLD,
                    Request.Status.DONE_WORKING,
                ),
            )
            .select_related('unit', 'requestor')
            .distinct()
            .order_by('-updated_at')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Task Management'
        context['page_description'] = 'Your assigned requests. Update status and add messages.'
        return context


class PersonnelTaskHistoryView(StaffRequiredMixin, ListView):
    """Phase 5: Personnel — completed and cancelled requests (assigned to me)."""
    model = Request
    template_name = 'staff/task_history.html'
    context_object_name = 'task_list'
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        if not getattr(request.user, 'is_personnel', False):
            messages.info(request, 'Task History is for Personnel only.')
            return redirect('gso_accounts:staff_dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return (
            Request.objects.filter(
                assignments__personnel=self.request.user,
                status__in=(Request.Status.COMPLETED, Request.Status.CANCELLED),
            )
            .select_related('unit', 'requestor')
            .distinct()
            .order_by('-updated_at')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Task History'
        context['page_description'] = 'Your completed and cancelled requests.'
        return context


class RequestorRequestExportCsvView(LoginRequiredMixin, View):
    """Requestor: export my requests (with current filters) to CSV."""

    def get(self, request):
        # Only requestors (non-staff) can export their own requests
        if getattr(request.user, 'is_staff_role', False):
            return redirect('gso_accounts:staff_dashboard')
        user = request.user
        qs = (
            Request.objects.filter(requestor=user)
            .select_related('unit')
            .order_by('-created_at')
        )
        status = request.GET.get('status', '').strip()
        q = request.GET.get('q', '').strip()
        if status:
            qs = qs.filter(status=status)
        if q:
            qs = qs.filter(
                Q(title__icontains=q)
                | Q(description__icontains=q)
                | Q(location__icontains=q)
                | Q(unit__name__icontains=q)
            )
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="my_requests.csv"'
        writer = csv.writer(response)
        writer.writerow(['Request ID', 'Purpose/s', 'Location', 'Unit', 'Status', 'Date submitted'])
        for req in qs:
            writer.writerow([
                getattr(req, 'display_id', '') or req.pk,
                req.description,
                req.location,
                getattr(req, 'unit_name', '') or (req.unit.name if req.unit_id else ''),
                req.get_status_display(),
                req.created_at.strftime('%Y-%m-%d %H:%M'),
            ])
        return response
