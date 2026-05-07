"""Phase 6.1: Work Accomplishment Report form."""
from django import forms
from django.db.models import Q
from .models import SuccessIndicator, WorkAccomplishmentReport


class SuccessIndicatorChoiceField(forms.ModelChoiceField):
    """Compact labels for WAR dropdown so native select stays usable."""

    def label_from_instance(self, obj):
        code = (obj.code or '').strip()
        name = (obj.name or '').strip()
        if len(name) > 55:
            name = f"{name[:55].rstrip()}..."
        if code and name:
            return f"{code} - {name}"
        return code or name or str(obj.pk)


class WARForm(forms.ModelForm):
    success_indicators = SuccessIndicatorChoiceField(
        queryset=SuccessIndicator.objects.none(),
        required=False,
        empty_label='-- Select success indicator --',
        widget=forms.Select(
            attrs={
                'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-slate-900 dark:text-slate-100',
            }
        ),
    )
    total_cost_display = forms.DecimalField(
        label='Total Cost',
        required=False,
        decimal_places=2,
        max_digits=12,
        disabled=True,
        widget=forms.NumberInput(attrs={'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-600 px-3 py-2 bg-slate-100 dark:bg-slate-800'}),
    )

    class Meta:
        model = WorkAccomplishmentReport
        fields = ['personnel', 'period_start', 'period_end', 'summary', 'accomplishments', 'success_indicators', 'material_cost', 'labor_cost']
        widgets = {
            'summary': forms.TextInput(attrs={'placeholder': 'Project title', 'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-600 px-3 py-2'}),
            'accomplishments': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Describe the project/work…', 'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-600 px-3 py-2'}),
            'material_cost': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-600 px-3 py-2'}),
            'labor_cost': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-600 px-3 py-2'}),
        }

    def __init__(self, *args, request_obj=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['summary'].label = 'Name of Project'
        self.fields['accomplishments'].label = 'Description'
        self.fields['material_cost'].label = 'Material Cost'
        self.fields['labor_cost'].label = 'Labor Cost'
        self.fields['personnel'].label = 'Assigned Personnel'
        self.fields['period_start'].label = 'Date Started'
        self.fields['period_end'].label = 'Date Completed'
        self.fields['success_indicators'].label = 'Success Indicator'
        self.fields['success_indicators'].required = False
        self.fields['success_indicators'].help_text = 'Select the indicator this work supports. This is used later in IPMT.'
        self.fields['success_indicators'].queryset = SuccessIndicator.objects.filter(is_active=True).order_by('display_order', 'code')
        if getattr(self.instance, 'pk', None) and not self.is_bound:
            self.fields['success_indicators'].initial = self.instance.success_indicators.first()
        self.fields['total_cost_display'].initial = self.instance.total_cost if getattr(self.instance, 'pk', None) else None

        if request_obj is not None:
            from apps.gso_requests.models import RequestAssignment
            assigned_ids = list(request_obj.assignments.values_list('personnel_id', flat=True))
            existing_war_personnel = list(request_obj.work_accomplishment_reports.values_list('personnel_id', flat=True))
            available = [pk for pk in assigned_ids if pk not in existing_war_personnel]
            # Keep currently assigned personnel available when editing an existing WAR.
            if getattr(self.instance, 'pk', None) and self.instance.personnel_id:
                available = sorted(set(available + [self.instance.personnel_id]))
            from apps.gso_accounts.models import User
            self.fields['personnel'].queryset = User.objects.filter(pk__in=available).order_by('first_name', 'last_name', 'username')
            if len(available) == 1 and not getattr(self.instance, 'pk', None):
                self.fields['personnel'].initial = available[0]
            self.fields['success_indicators'].queryset = SuccessIndicator.objects.filter(
                is_active=True,
            ).filter(
                Q(target_unit__isnull=True) | Q(target_unit=request_obj.unit)
            ).order_by('display_order', 'code')
            if getattr(self.instance, 'pk', None) and not self.is_bound:
                self.fields['success_indicators'].initial = self.instance.success_indicators.first()

        if getattr(self.instance, 'pk', None):
            # Edit mode: personnel and period are fixed for this WAR entry.
            self.fields['personnel'].disabled = True
            self.fields['period_start'].disabled = True
            self.fields['period_end'].disabled = True

    def clean(self):
        cleaned = super().clean()
        material = cleaned.get('material_cost')
        labor = cleaned.get('labor_cost')
        if material is not None and material < 0:
            self.add_error('material_cost', 'Material cost cannot be negative.')
        if labor is not None and labor < 0:
            self.add_error('labor_cost', 'Labor cost cannot be negative.')
        if getattr(self.instance, 'pk', None):
            cleaned['personnel'] = self.instance.personnel
            cleaned['period_start'] = self.instance.period_start
            cleaned['period_end'] = self.instance.period_end
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        selected_indicator = self.cleaned_data.get('success_indicators')
        if commit:
            instance.save()
            if selected_indicator:
                instance.success_indicators.set([selected_indicator])
            else:
                instance.success_indicators.clear()
        return instance


MONTH_CHOICES = [(i, f'{i:02d} — {["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][i-1]}') for i in range(1, 13)]


class IPMTReportForm(forms.Form):
    """Phase 6.3: Select personnel and period for IPMT report."""
    unit = forms.ModelChoiceField(
        queryset=None,
        label='Unit (optional)',
        required=False,
        empty_label='All units',
        widget=forms.Select(attrs={'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-slate-900 dark:text-slate-100'}),
    )
    personnel = forms.ModelChoiceField(
        queryset=None,
        label='Personnel',
        required=True,
        empty_label='Select personnel…',
        widget=forms.Select(attrs={'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-slate-900 dark:text-slate-100'}),
    )
    year = forms.IntegerField(
        min_value=2020,
        max_value=2030,
        label='Year',
        widget=forms.NumberInput(attrs={'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2', 'min': 2020, 'max': 2030}),
    )
    month = forms.TypedChoiceField(
        choices=MONTH_CHOICES,
        coerce=int,
        label='Month',
        widget=forms.Select(attrs={'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-slate-900 dark:text-slate-100'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.gso_accounts.models import User
        from apps.gso_units.models import Unit

        personnel_qs = User.objects.filter(
            role=User.Role.PERSONNEL,
            is_active=True,
        )
        self.fields['unit'].queryset = Unit.objects.filter(is_active=True).order_by('name')

        unit_value = None
        if self.data.get('unit'):
            unit_value = self.data.get('unit')
        elif self.initial.get('unit'):
            unit_value = self.initial.get('unit')

        self.fields['personnel'].queryset = personnel_qs.order_by('first_name', 'last_name', 'username')
        from datetime import date
        today = date.today()
        if not self.initial and not self.data:
            self.initial = {'year': today.year, 'month': today.month}

    def clean(self):
        cleaned = super().clean()
        unit = cleaned.get('unit')
        personnel = cleaned.get('personnel')
        if unit and personnel and getattr(personnel, 'unit_id', None) != unit.id:
            self.add_error('personnel', 'Selected personnel is not assigned to the selected unit.')
        return cleaned


class SuccessIndicatorForm(forms.ModelForm):
    """Staff-side form for IPMT success indicator master data."""

    class Meta:
        model = SuccessIndicator
        fields = ['code', 'name', 'description', 'target_unit', 'target_position', 'display_order', 'is_active']
        widgets = {
            'code': forms.TextInput(attrs={'placeholder': 'e.g., SI-01', 'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-slate-900 dark:text-slate-100'}),
            'name': forms.TextInput(attrs={'placeholder': 'Success indicator title', 'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-slate-900 dark:text-slate-100'}),
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Optional details or expected output', 'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-slate-900 dark:text-slate-100'}),
            'target_unit': forms.Select(attrs={'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-slate-900 dark:text-slate-100'}),
            'target_position': forms.TextInput(attrs={'placeholder': 'Optional, e.g., Carpenter', 'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-slate-900 dark:text-slate-100'}),
            'display_order': forms.NumberInput(attrs={'min': 0, 'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-slate-900 dark:text-slate-100'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'rounded border-slate-300 text-primary focus:ring-primary'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.gso_units.models import Unit
        self.fields['target_unit'].queryset = Unit.objects.filter(is_active=True).order_by('name')
        self.fields['target_unit'].required = False
        self.fields['target_unit'].empty_label = 'All units'
        self.fields['target_position'].required = False
        self.fields['description'].required = False
        self.fields['display_order'].initial = self.fields['display_order'].initial or 0


class WARExportForm(forms.Form):
    """Phase 6.4: Filter WAR for export (unit, optional personnel, month/year)."""
    unit = forms.ModelChoiceField(
        queryset=None,
        label='Unit (optional)',
        required=False,
        empty_label='All units',
        widget=forms.Select(attrs={'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-slate-900 dark:text-slate-100'}),
    )
    personnel = forms.ModelChoiceField(
        queryset=None,
        label='Personnel (optional)',
        required=False,
        empty_label='All personnel',
        widget=forms.Select(attrs={'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-slate-900 dark:text-slate-100'}),
    )
    year = forms.IntegerField(
        min_value=2020,
        max_value=2035,
        label='Year',
        widget=forms.NumberInput(attrs={'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2', 'min': 2020, 'max': 2035}),
    )
    month = forms.TypedChoiceField(
        choices=MONTH_CHOICES,
        coerce=int,
        label='Month',
        widget=forms.Select(attrs={'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-slate-900 dark:text-slate-100'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.gso_accounts.models import User
        from apps.gso_units.models import Unit

        # Base querysets
        personnel_qs = User.objects.filter(
            role=User.Role.PERSONNEL,
            is_active=True,
        )

        # If a unit is selected (in GET data or initial), limit personnel to that unit only
        unit_value = None
        if self.data.get('unit'):
            unit_value = self.data.get('unit')
        elif self.initial.get('unit'):
            unit_value = self.initial.get('unit')

        unit_id = None
        if unit_value:
            # unit_value can be a pk string or a Unit instance
            if hasattr(unit_value, 'pk'):
                unit_id = unit_value.pk
            else:
                try:
                    unit_id = int(unit_value)
                except (TypeError, ValueError):
                    unit_id = None

        if unit_id:
            personnel_qs = personnel_qs.filter(unit_id=unit_id)

        self.fields['personnel'].queryset = personnel_qs.order_by('first_name', 'last_name', 'username')
        self.fields['unit'].queryset = Unit.objects.filter(is_active=True).order_by('name')
        from datetime import date
        today = date.today()
        if not self.initial and not self.data:
            self.initial = {'year': today.year, 'month': today.month}


class FeedbackExportForm(forms.Form):
    """Filter feedback for report: date range and optional unit."""
    date_from = forms.DateField(
        label='From date',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-slate-900 dark:text-slate-100'}),
    )
    date_to = forms.DateField(
        label='To date',
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-slate-900 dark:text-slate-100'}),
    )
    unit = forms.ModelChoiceField(
        queryset=None,
        label='Unit (optional)',
        required=False,
        empty_label='All units',
        widget=forms.Select(attrs={'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-slate-900 dark:text-slate-100'}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.gso_units.models import Unit
        self.fields['unit'].queryset = Unit.objects.filter(is_active=True).order_by('name')


def _distinct_requesting_offices():
    from apps.gso_accounts.models import User

    return (
        User.objects.filter(role=User.Role.REQUESTOR)
        .exclude(office_department='')
        .values_list('office_department', flat=True)
        .distinct()
        .order_by('office_department')
    )


class RequestReportForm(forms.Form):
    """Filter completed requests for Request Report (Work Reports submenu)."""

    date_from = forms.DateField(
        label='Completed from',
        required=False,
        widget=forms.DateInput(
            attrs={
                'type': 'date',
                'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-slate-900 dark:text-slate-100',
            }
        ),
    )
    date_to = forms.DateField(
        label='Completed to',
        required=False,
        widget=forms.DateInput(
            attrs={
                'type': 'date',
                'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-slate-900 dark:text-slate-100',
            }
        ),
    )
    unit = forms.ModelChoiceField(
        queryset=None,
        label='Unit (optional)',
        required=False,
        empty_label='All units',
        widget=forms.Select(
            attrs={'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-slate-900 dark:text-slate-100'}
        ),
    )
    requesting_office = forms.ChoiceField(
        label='Requesting office (optional)',
        required=False,
        choices=(('', 'All requesting offices'),),
        widget=forms.Select(
            attrs={'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-slate-900 dark:text-slate-100'}
        ),
    )
    q = forms.CharField(
        label='Search',
        required=False,
        widget=forms.TextInput(
            attrs={
                'placeholder': 'Title, request ID (e.g. GSO-2026-0001), office, contact…',
                'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-slate-900 dark:text-slate-100 min-w-[220px]',
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.gso_units.models import Unit

        self.fields['unit'].queryset = Unit.objects.filter(is_active=True).order_by('name')
        offices = list(_distinct_requesting_offices())
        self.fields['requesting_office'].choices = [('', 'All requesting offices')] + [(o, o) for o in offices]

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get('date_from')
        end = cleaned.get('date_to')
        if start and end and start > end:
            raise forms.ValidationError('Completed-from date cannot be after completed-to date.')
        return cleaned
