"""Phase 6.1: Work Accomplishment Report form."""
from django import forms
from .models import WorkAccomplishmentReport


class WARForm(forms.ModelForm):
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
        fields = ['personnel', 'period_start', 'period_end', 'summary', 'accomplishments', 'material_cost', 'labor_cost']
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


MONTH_CHOICES = [(i, f'{i:02d} — {["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][i-1]}') for i in range(1, 13)]


class IPMTReportForm(forms.Form):
    """Phase 6.3: Select personnel and period for IPMT report."""
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
        self.fields['personnel'].queryset = User.objects.filter(
            role=User.Role.PERSONNEL,
            is_active=True,
        ).order_by('first_name', 'last_name', 'username')
        from datetime import date
        today = date.today()
        if not self.initial and not self.data:
            self.initial = {'year': today.year, 'month': today.month}


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
