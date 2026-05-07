"""Phase 3.2 Unit Head — own unit only; Phase 3.3 GSO Office & Director — all inventory with unit filter."""
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
    FormView,
    View,
)

from apps.gso_accounts.views import StaffRequiredMixin

from django.utils import timezone

from .forms import InventoryItemForm, InventoryItemFormAllUnits, InventoryAdjustForm, IssueMaterialForm, RequestMaterialForm
from .models import InventoryItem, InventoryTransaction, MaterialRequest, format_quantity_with_uom
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string


def user_can_manage_all_units(user):
    """True if user can see and manage inventory for all units (GSO Office, Director)."""
    return getattr(user, 'is_gso_office', False) or getattr(user, 'is_director', False)


def user_sees_own_unit_only(user):
    """True if user sees only their unit's inventory (Unit Head or Personnel with unit)."""
    return (
        (getattr(user, 'is_unit_head', False) or getattr(user, 'is_personnel', False))
        and getattr(user, 'unit_id', None)
    )


class InventoryAccessMixin:
    """Allow Unit Head, Personnel (with unit), GSO Office, and Director. Use with StaffRequiredMixin first."""

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if getattr(user, 'is_unit_head', False) or getattr(user, 'is_personnel', False):
            if not getattr(user, 'unit_id', None):
                messages.warning(request, 'No unit assigned. Contact admin to access inventory.')
                return redirect('gso_accounts:staff_dashboard')
            return super().dispatch(request, *args, **kwargs)
        if user_can_manage_all_units(user):
            return super().dispatch(request, *args, **kwargs)
        messages.info(request, 'Inventory is for Unit Heads, Personnel, GSO Office, and Director only.')
        return redirect('gso_accounts:staff_dashboard')

    def get_queryset(self):
        if user_can_manage_all_units(self.request.user):
            return InventoryItem.objects.all().select_related('unit')
        return InventoryItem.objects.filter(unit_id=self.request.user.unit_id).select_related('unit')


class InventoryListView(StaffRequiredMixin, InventoryAccessMixin, ListView):
    model = InventoryItem
    template_name = 'staff/inventory_list.html'
    context_object_name = 'items'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().order_by('unit__name', 'name')
        if user_can_manage_all_units(self.request.user):
            unit_id = self.request.GET.get('unit', '').strip()
            if unit_id and unit_id.isdigit():
                qs = qs.filter(unit_id=int(unit_id))
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(name__icontains=q) | Q(category__icontains=q) | Q(description__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        from apps.gso_units.models import Unit
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Inventory'
        can_all = user_can_manage_all_units(self.request.user)
        context['show_unit_filter'] = can_all
        if can_all:
            context['units'] = Unit.objects.filter(is_active=True).order_by('name')
            raw = self.request.GET.get('unit', '').strip()
            context['filter_unit_id'] = int(raw) if raw.isdigit() else None
            context['page_description'] = 'View and manage inventory across all units. Filter by unit below.'
        else:
            context['units'] = []
            context['filter_unit_id'] = None
            context['page_description'] = f'Manage inventory for {self.request.user.unit.name}.'
        context['search_q'] = self.request.GET.get('q', '')
        return context


class InventoryDetailView(StaffRequiredMixin, InventoryAccessMixin, DetailView):
    model = InventoryItem
    template_name = 'staff/inventory_detail.html'
    context_object_name = 'item'

    def get(self, request, *args, **kwargs):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.GET.get('partial') == '1':
            self.object = self.get_object()
            context = self.get_context_data(object=self.object)
            html = render_to_string('staff/_inventory_detail_modal.html', context, request=request)
            return HttpResponse(html)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['transactions'] = self.object.transactions.select_related('performed_by')[:20]
        return context


class InventoryCreateView(StaffRequiredMixin, InventoryAccessMixin, CreateView):
    model = InventoryItem
    template_name = 'staff/inventory_form.html'
    context_object_name = 'item'

    def dispatch(self, request, *args, **kwargs):
        if getattr(request.user, 'is_personnel', False):
            messages.info(request, 'Personnel can only view inventory. Only Unit Heads, GSO Office, and Director can add items.')
            return redirect('gso_accounts:staff_inventory')
        return super().dispatch(request, *args, **kwargs)

    def get_form_class(self):
        return InventoryItemFormAllUnits if user_can_manage_all_units(self.request.user) else InventoryItemForm

    def get(self, request, *args, **kwargs):
        # AJAX partial for modal
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.GET.get('partial') == '1':
            self.object = None
            form = self.get_form(self.get_form_class())
            context = self.get_context_data(form=form)
            html = render_to_string('staff/_inventory_form_modal.html', context, request=request)
            return HttpResponse(html)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        # AJAX submit from modal
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.GET.get('partial') == '1':
            self.object = None
            form = self.get_form(self.get_form_class())
            if form.is_valid():
                if not user_can_manage_all_units(self.request.user):
                    form.instance.unit_id = self.request.user.unit_id
                form.instance.created_by = self.request.user
                form.instance.updated_by = self.request.user
                self.object = form.save()
                if self.object.quantity > 0:
                    initial_arrival_date = self.object.arrival_date or timezone.localdate()
                    InventoryTransaction.objects.create(
                        item=self.object,
                        transaction_type=InventoryTransaction.TransactionType.IN,
                        quantity=self.object.quantity,
                        performed_by=self.request.user,
                        notes='Initial stock',
                        arrival_date=initial_arrival_date,
                    )
                messages.success(self.request, f'Item "{self.object.name}" added.')
                return JsonResponse({'success': True})
            context = self.get_context_data(form=form)
            html = render_to_string('staff/_inventory_form_modal.html', context, request=request)
            return JsonResponse({'success': False, 'html': html}, status=400)
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        if not user_can_manage_all_units(self.request.user):
            form.instance.unit_id = self.request.user.unit_id
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        response = super().form_valid(form)
        if self.object.quantity > 0:
            initial_arrival_date = self.object.arrival_date or timezone.localdate()
            InventoryTransaction.objects.create(
                item=self.object,
                transaction_type=InventoryTransaction.TransactionType.IN,
                quantity=self.object.quantity,
                performed_by=self.request.user,
                notes='Initial stock',
                arrival_date=initial_arrival_date,
            )
        return response

    def get_success_url(self):
        return reverse_lazy('gso_accounts:staff_inventory_detail', args=[self.object.pk])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Add inventory item'
        return context


class InventoryUpdateView(StaffRequiredMixin, InventoryAccessMixin, UpdateView):
    model = InventoryItem
    template_name = 'staff/inventory_form.html'
    context_object_name = 'item'

    def dispatch(self, request, *args, **kwargs):
        if getattr(request.user, 'is_personnel', False):
            messages.info(request, 'Personnel can only view inventory. Only Unit Heads, GSO Office, and Director can edit items.')
            return redirect('gso_accounts:staff_inventory_detail', pk=kwargs.get('pk'))
        return super().dispatch(request, *args, **kwargs)

    def get_form_class(self):
        return InventoryItemFormAllUnits if user_can_manage_all_units(self.request.user) else InventoryItemForm

    def get(self, request, *args, **kwargs):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.GET.get('partial') == '1':
            self.object = self.get_object()
            form = self.get_form(self.get_form_class())
            context = self.get_context_data(form=form)
            html = render_to_string('staff/_inventory_form_modal.html', context, request=request)
            return HttpResponse(html)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.GET.get('partial') == '1':
            self.object = self.get_object()
            form = self.get_form(self.get_form_class())
            if form.is_valid():
                form.instance.updated_by = self.request.user
                self.object = form.save()
                messages.success(self.request, f'Item "{self.object.name}" updated.')
                return JsonResponse({'success': True})
            context = self.get_context_data(form=form)
            html = render_to_string('staff/_inventory_form_modal.html', context, request=request)
            return JsonResponse({'success': False, 'html': html}, status=400)
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, f'Item "{form.instance.name}" updated.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('gso_accounts:staff_inventory_detail', args=[self.object.pk])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Edit inventory item'
        return context


class InventoryDeleteView(StaffRequiredMixin, InventoryAccessMixin, DeleteView):
    model = InventoryItem
    template_name = 'staff/inventory_confirm_delete.html'
    context_object_name = 'item'

    def dispatch(self, request, *args, **kwargs):
        if getattr(request.user, 'is_personnel', False):
            messages.info(request, 'Personnel can only view inventory. Only Unit Heads, GSO Office, and Director can delete items.')
            return redirect('gso_accounts:staff_inventory_detail', pk=kwargs.get('pk'))
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.GET.get('partial') == '1':
            self.object = self.get_object()
            context = self.get_context_data(object=self.object)
            html = render_to_string('staff/_inventory_delete_modal.html', context, request=request)
            return HttpResponse(html)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.GET.get('partial') == '1':
            self.object = self.get_object()
            self.object.delete()
            messages.success(self.request, 'Item deleted.')
            return JsonResponse({'success': True})
        return super().post(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy('gso_accounts:staff_inventory')

    def form_valid(self, form):
        messages.success(self.request, f'Item "{self.object.name}" deleted.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Delete inventory item'
        return context


class InventoryAdjustView(StaffRequiredMixin, InventoryAccessMixin, FormView):
    form_class = InventoryAdjustForm
    template_name = 'staff/inventory_adjust.html'

    def dispatch(self, request, *args, **kwargs):
        if getattr(request.user, 'is_personnel', False):
            messages.info(request, 'Personnel can only view inventory. Only Unit Heads, GSO Office, and Director can adjust quantities.')
            return redirect('gso_accounts:staff_inventory_detail', pk=kwargs.get('pk'))
        if user_can_manage_all_units(request.user):
            self.item = get_object_or_404(InventoryItem.objects.select_related('unit'), pk=kwargs['pk'])
        else:
            self.item = get_object_or_404(
                InventoryItem,
                pk=kwargs['pk'],
                unit_id=request.user.unit_id,
            )
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['item'] = self.item
        context['page_title'] = 'Adjust quantity'
        return context

    def get(self, request, *args, **kwargs):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.GET.get('partial') == '1':
            form = self.get_form()
            context = self.get_context_data(form=form)
            html = render_to_string('staff/_inventory_adjust_modal.html', context, request=request)
            return HttpResponse(html)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.GET.get('partial') == '1':
            form = self.get_form()
            if form.is_valid():
                trans_type = form.cleaned_data['transaction_type']
                quantity = form.cleaned_data['quantity']
                notes = form.cleaned_data.get('notes', '')
                arrival_date = form.cleaned_data.get('arrival_date')
                if trans_type == 'OUT' and quantity > self.item.quantity:
                    form.add_error(
                        'quantity',
                        f'Not enough stock. Current: {format_quantity_with_uom(self.item.quantity, self.item.unit_of_measure)}',
                    )
                else:
                    if trans_type == 'IN':
                        self.item.quantity += quantity
                        self.item.arrival_date = arrival_date or timezone.localdate()
                    else:
                        self.item.quantity -= quantity
                    self.item.updated_by = self.request.user
                    update_fields = ['quantity', 'updated_by', 'updated_at']
                    if trans_type == 'IN':
                        update_fields.append('arrival_date')
                    self.item.save(update_fields=update_fields)
                    InventoryTransaction.objects.create(
                        item=self.item,
                        transaction_type=trans_type,
                        quantity=quantity,
                        performed_by=self.request.user,
                        notes=notes,
                        arrival_date=arrival_date if trans_type == 'IN' else None,
                    )
                    messages.success(self.request, f'Quantity updated. New stock: {format_quantity_with_uom(self.item.quantity, self.item.unit_of_measure)}.')
                    return JsonResponse({'success': True})
            context = self.get_context_data(form=form)
            html = render_to_string('staff/_inventory_adjust_modal.html', context, request=request)
            return JsonResponse({'success': False, 'html': html}, status=400)
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        trans_type = form.cleaned_data['transaction_type']
        quantity = form.cleaned_data['quantity']
        notes = form.cleaned_data.get('notes', '')
        arrival_date = form.cleaned_data.get('arrival_date')
        if trans_type == 'OUT' and quantity > self.item.quantity:
            form.add_error(
                'quantity',
                f'Not enough stock. Current: {format_quantity_with_uom(self.item.quantity, self.item.unit_of_measure)}',
            )
            return self.form_invalid(form)
        if trans_type == 'IN':
            self.item.quantity += quantity
            self.item.arrival_date = arrival_date or timezone.localdate()
        else:
            self.item.quantity -= quantity
        self.item.updated_by = self.request.user
        update_fields = ['quantity', 'updated_by', 'updated_at']
        if trans_type == 'IN':
            update_fields.append('arrival_date')
        self.item.save(update_fields=update_fields)
        InventoryTransaction.objects.create(
            item=self.item,
            transaction_type=trans_type,
            quantity=quantity,
            performed_by=self.request.user,
            notes=notes,
            arrival_date=arrival_date if trans_type == 'IN' else None,
        )
        messages.success(self.request, f'Quantity updated. New stock: {format_quantity_with_uom(self.item.quantity, self.item.unit_of_measure)}.')
        return redirect('gso_accounts:staff_inventory_detail', pk=self.item.pk)


class IssueMaterialToRequestView(StaffRequiredMixin, View):
    """Unit Head: issue material from unit inventory to a request (deducts stock, links transaction to request)."""
    http_method_names = ['post']

    def post(self, request, pk):
        from apps.gso_requests.models import Request
        req = get_object_or_404(Request.objects.select_related('unit'), pk=pk)
        user = request.user
        if not getattr(user, 'is_unit_head', False) or user.unit_id != req.unit_id:
            messages.error(request, 'Only the Unit Head for this request\'s unit can issue materials.')
            return redirect('gso_accounts:staff_request_detail', pk=pk)
        if req.status in (Request.Status.COMPLETED, Request.Status.CANCELLED, Request.Status.NOT_APPLICABLE):
            messages.warning(request, 'Cannot issue materials for a completed, cancelled, or not applicable request.')
            return redirect('gso_accounts:staff_request_detail', pk=pk)
        form = IssueMaterialForm(request.POST, unit_id=req.unit_id, prefix='issue')
        if not form.is_valid():
            for _field, errors in form.errors.items():
                for err in errors:
                    messages.error(request, err)
            return redirect('gso_accounts:staff_request_detail', pk=pk)
        item = form.cleaned_data['item']
        quantity = form.cleaned_data['quantity']
        notes = (form.cleaned_data.get('notes') or '').strip()
        item.quantity -= quantity
        item.updated_by = user
        item.save(update_fields=['quantity', 'updated_by', 'updated_at'])
        InventoryTransaction.objects.create(
            item=item,
            transaction_type=InventoryTransaction.TransactionType.OUT,
            quantity=quantity,
            request=req,
            performed_by=user,
            notes=notes or f'Issued for request {req.display_id}',
        )
        messages.success(
            request,
            f'Issued {format_quantity_with_uom(quantity, item.unit_of_measure)} of "{item.name}" to this request. Stock updated.',
        )
        return redirect('gso_accounts:staff_request_detail', pk=pk)


class SubmitMaterialRequestView(StaffRequiredMixin, View):
    """Personnel (assigned to the request): request material; no deduction until Unit Head approves."""
    http_method_names = ['post']

    def post(self, request, pk):
        from apps.gso_requests.models import Request
        req = get_object_or_404(Request.objects.select_related('unit'), pk=pk)
        user = request.user
        if not getattr(user, 'is_personnel', False):
            messages.error(request, 'Only assigned personnel can request materials.')
            return redirect('gso_accounts:staff_request_detail', pk=pk)
        if not req.assignments.filter(personnel=user).exists():
            messages.error(request, 'You are not assigned to this request.')
            return redirect('gso_accounts:staff_request_detail', pk=pk)
        if req.status in (Request.Status.COMPLETED, Request.Status.CANCELLED, Request.Status.NOT_APPLICABLE):
            messages.warning(request, 'Cannot request materials for a completed, cancelled, or not applicable request.')
            return redirect('gso_accounts:staff_request_detail', pk=pk)
        form = RequestMaterialForm(request.POST, unit_id=req.unit_id, prefix='request')
        if not form.is_valid():
            for _field, errors in form.errors.items():
                for err in errors:
                    messages.error(request, err)
            return redirect('gso_accounts:staff_request_detail', pk=pk)
        mr = MaterialRequest.objects.create(
            request=req,
            item=form.cleaned_data['item'],
            quantity=form.cleaned_data['quantity'],
            notes=(form.cleaned_data.get('notes') or '').strip(),
            requested_by=user,
            status=MaterialRequest.Status.PENDING,
        )
        from apps.gso_notifications.utils import notify_material_request_submitted
        notify_material_request_submitted(mr)
        messages.success(request, 'Material request submitted. Unit Head will approve before stock is deducted.')
        return redirect('gso_accounts:staff_request_detail', pk=pk)


class ApproveMaterialRequestView(StaffRequiredMixin, View):
    """Unit Head: approve a personnel material request; deducts from inventory and creates OUT transaction."""
    http_method_names = ['post']

    def post(self, request, mr_pk):
        mr = get_object_or_404(
            MaterialRequest.objects.select_related('request', 'item', 'request__unit'),
            pk=mr_pk,
            status=MaterialRequest.Status.PENDING,
        )
        req = mr.request
        user = request.user
        if not getattr(user, 'is_unit_head', False) or user.unit_id != req.unit_id:
            messages.error(request, 'Only the Unit Head for this request\'s unit can approve material requests.')
            return redirect('gso_accounts:staff_request_detail', pk=req.pk)
        item = mr.item
        if mr.quantity > item.quantity:
            messages.error(
                request,
                f'Not enough stock. Available: {format_quantity_with_uom(item.quantity, item.unit_of_measure)}. Request was not approved.',
            )
            return redirect('gso_accounts:staff_request_detail', pk=req.pk)
        item.quantity -= mr.quantity
        item.updated_by = user
        item.save(update_fields=['quantity', 'updated_by', 'updated_at'])
        InventoryTransaction.objects.create(
            item=item,
            transaction_type=InventoryTransaction.TransactionType.OUT,
            quantity=mr.quantity,
            request=req,
            performed_by=user,
            notes=mr.notes or f'Approved material request by {mr.requested_by.get_full_name() or mr.requested_by.username}',
        )
        mr.status = MaterialRequest.Status.APPROVED
        mr.approved_by = user
        mr.approved_at = timezone.now()
        mr.save(update_fields=['status', 'approved_by', 'approved_at'])
        from apps.gso_notifications.utils import notify_material_request_approved
        notify_material_request_approved(mr)
        messages.success(request, f'Approved: {format_quantity_with_uom(mr.quantity, item.unit_of_measure)} of "{item.name}" deducted from inventory.')
        return redirect('gso_accounts:staff_request_detail', pk=req.pk)


class RejectMaterialRequestView(StaffRequiredMixin, View):
    """Unit Head: reject a personnel material request; no deduction."""
    http_method_names = ['post']

    def post(self, request, mr_pk):
        mr = get_object_or_404(
            MaterialRequest.objects.select_related('request'),
            pk=mr_pk,
            status=MaterialRequest.Status.PENDING,
        )
        req = mr.request
        user = request.user
        if not getattr(user, 'is_unit_head', False) or user.unit_id != req.unit_id:
            messages.error(request, 'Only the Unit Head for this request\'s unit can reject material requests.')
            return redirect('gso_accounts:staff_request_detail', pk=req.pk)
        mr.status = MaterialRequest.Status.REJECTED
        mr.approved_by = user
        mr.approved_at = timezone.now()
        mr.save(update_fields=['status', 'approved_by', 'approved_at'])
        from apps.gso_notifications.utils import notify_material_request_rejected
        notify_material_request_rejected(mr)
        messages.success(request, 'Material request rejected.')
        return redirect('gso_accounts:staff_request_detail', pk=req.pk)
