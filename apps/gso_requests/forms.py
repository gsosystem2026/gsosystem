"""
Phase 2.2: Request form — fields only (layout/design in templates).
Phase 4.1: Assign personnel form for Unit Head.
"""
from django import forms
from .models import Request, RequestAssignment, RequestMessage, RequestFeedback


class RequestorCancelForm(forms.Form):
    """Requestor must provide a reason when cancelling their request."""
    reason = forms.CharField(
        required=True,
        max_length=1000,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Please state why you are cancelling this request…',
            'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-sm text-slate-900 dark:text-slate-100',
        }),
        label='Reason for cancellation',
    )


class RequestForm(forms.ModelForm):
    """Form to create a request. Unit is set from selection; requestor set in view."""

    class Meta:
        model = Request
        fields = [
            'unit',
            'description',
            'location',
            'labor',
            'materials',
            'others',
            'custom_full_name',
            'custom_email',
            'custom_contact_number',
            'attachment',
        ]
        widgets = {
            'unit': forms.HiddenInput(),
            'description': forms.Textarea(attrs={'placeholder': 'Purpose/s (Preferably in English)', 'rows': 4}),
            'location': forms.TextInput(attrs={'placeholder': 'IT Building - IT101'}),
            'labor': forms.CheckboxInput(),
            'materials': forms.CheckboxInput(),
            'others': forms.CheckboxInput(),
            'custom_full_name': forms.TextInput(attrs={'placeholder': 'John Doe'}),
            'custom_email': forms.EmailInput(attrs={'placeholder': 'name@psu.palawan.edu.ph'}),
            'custom_contact_number': forms.TextInput(attrs={'placeholder': '09XX XXX XXXX', 'type': 'tel'}),
            'attachment': forms.FileInput(attrs={'accept': 'image/*'}),
        }
        labels = {
            'labor': 'Labor',
            'materials': 'Materials',
            'others': 'Others',
            'custom_full_name': 'Full Name',
            'custom_email': 'Email',
            'custom_contact_number': 'Contact Number',
            'attachment': 'Attachments',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['description'].required = True
        self.fields['location'].required = True
        self.fields['labor'].required = False
        self.fields['materials'].required = False
        self.fields['others'].required = False

    def clean(self):
        cleaned = super().clean()
        purpose = (cleaned.get('description') or '').strip()
        location = (cleaned.get('location') or '').strip()
        # Keep internal title auto-generated while hiding it from requestor UI.
        cleaned['title'] = f"{purpose[:140]} @ {location}"[:255]
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.title = self.cleaned_data.get('title', instance.title)
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class AssignPersonnelForm(forms.Form):
    """Unit Head assigns one or more Personnel to a request (Phase 4.1). Emergency is set via the Emergency flag section."""
    personnel = forms.ModelMultipleChoiceField(
        queryset=None,  # set in view: Personnel in same unit as request
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label='Personnel',
    )

    def __init__(self, *args, unit_id=None, request_obj=None, **kwargs):
        super().__init__(*args, **kwargs)
        if unit_id is not None:
            from apps.gso_accounts.models import User
            self.fields['personnel'].queryset = User.objects.filter(
                role=User.Role.PERSONNEL,
                unit_id=unit_id,
                is_active=True,
            ).order_by('first_name', 'last_name', 'username')
        if request_obj is not None:
            # Exclude already assigned
            existing = request_obj.assignments.values_list('personnel_id', flat=True)
            if existing:
                self.fields['personnel'].queryset = self.fields['personnel'].queryset.exclude(pk__in=existing)


class RequestMessageForm(forms.ModelForm):
    """Phase 5.2: Post a message on a request (staff: Personnel, Unit Head, GSO, Director)."""
    class Meta:
        model = RequestMessage
        fields = ['message']
        widgets = {
            'message': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Add a message…', 'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-sm'}),
        }


def _input_class():
    return 'rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-slate-900 dark:text-slate-100 w-full'


class RequestFeedbackForm(forms.ModelForm):
    """Phase 7.1: CSM-style feedback — requestor only, for completed requests. Part I (CC1–CC3), Part II (SQD1–SQD9), suggestions, email."""
    class Meta:
        model = RequestFeedback
        fields = [
            'cc1', 'cc2', 'cc3',
            'sqd1', 'sqd2', 'sqd3', 'sqd4', 'sqd5', 'sqd6', 'sqd7', 'sqd8', 'sqd9',
            'suggestions', 'email',
        ]
        widgets = {
            'cc1': forms.Select(attrs={'class': _input_class(), 'required': True}),
            'cc2': forms.Select(attrs={'class': _input_class()}),
            'cc3': forms.Select(attrs={'class': _input_class()}),
            'sqd1': forms.Select(attrs={'class': _input_class()}),
            'sqd2': forms.Select(attrs={'class': _input_class()}),
            'sqd3': forms.Select(attrs={'class': _input_class()}),
            'sqd4': forms.Select(attrs={'class': _input_class()}),
            'sqd5': forms.Select(attrs={'class': _input_class()}),
            'sqd6': forms.Select(attrs={'class': _input_class()}),
            'sqd7': forms.Select(attrs={'class': _input_class()}),
            'sqd8': forms.Select(attrs={'class': _input_class()}),
            'sqd9': forms.Select(attrs={'class': _input_class()}),
            'suggestions': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Optional', 'class': _input_class()}),
            'email': forms.EmailInput(attrs={'placeholder': 'Optional', 'class': _input_class()}),
        }
        labels = {
            'cc1': 'CC1. Which best describes your awareness of a Citizen\'s Charter (CC)?',
            'cc2': 'CC2. If aware of CC, how would you describe the CC of this office?',
            'cc3': 'CC3. How much did the CC help you in your transaction?',
            'sqd1': 'SQD1',
            'sqd2': 'SQD2',
            'sqd3': 'SQD3',
            'sqd4': 'SQD4',
            'sqd5': 'SQD5',
            'sqd6': 'SQD6',
            'sqd7': 'SQD7',
            'sqd8': 'SQD8',
            'sqd9': 'SQD9',
            'suggestions': 'Suggestions for improvement (optional)',
            'email': 'Email (optional)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cc1'].required = True
        for i in range(1, 10):
            self.fields[f'sqd{i}'].required = True
