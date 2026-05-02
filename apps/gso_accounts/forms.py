from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm, SetPasswordForm
from django.core.exceptions import ValidationError
from django.utils import timezone

User = get_user_model()


class GsoAuthenticationForm(AuthenticationForm):
    """Login form; optionally add Bootstrap/extra classes in template."""
    username = forms.CharField(
        widget=forms.TextInput(attrs={'autofocus': True, 'placeholder': 'Username'})
    )
    password = forms.CharField(
        strip=False,
        widget=forms.PasswordInput(attrs={'placeholder': 'Password'})
    )

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        status = getattr(user, 'account_status', getattr(User.AccountStatus, 'ACTIVE', 'ACTIVE'))
        if status == User.AccountStatus.DEACTIVATED:
            raise ValidationError('Your account is deactivated. Please contact the administrator.', code='inactive')
        if status == User.AccountStatus.SUSPENDED:
            suspended_until = getattr(user, 'suspended_until', None)
            if suspended_until and suspended_until <= timezone.now():
                # Suspension expired; auto-restore active status.
                user.account_status = User.AccountStatus.ACTIVE
                user.restriction_reason_category = ''
                user.restriction_reason_details = ''
                user.suspended_until = None
                user.save(update_fields=['account_status', 'restriction_reason_category', 'restriction_reason_details', 'suspended_until'])
                return
            if suspended_until:
                until_str = timezone.localtime(suspended_until).strftime('%b %d, %Y %I:%M %p')
                raise ValidationError(f'Your account is suspended until {until_str}. Please contact the administrator.', code='inactive')
            raise ValidationError('Your account is suspended. Please contact the administrator.', code='inactive')


class GsoPasswordResetForm(PasswordResetForm):
    """Password reset request; email field."""
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': 'Email address', 'autocomplete': 'email'})
    )


class GsoPasswordResetOTPForm(forms.Form):
    """Enter 6-digit OTP sent by email."""
    otp = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter 6-digit OTP',
            'autocomplete': 'one-time-code',
            'inputmode': 'numeric',
            'pattern': '[0-9]*',
            'class': 'w-full px-3 py-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-sm focus:ring-2 focus:ring-primary focus:border-transparent transition-all outline-none text-center tracking-[0.3em] font-semibold',
        }),
    )

    def clean_otp(self):
        otp = (self.cleaned_data.get('otp') or '').strip()
        if not otp.isdigit():
            raise ValidationError('OTP must be numeric.')
        return otp


class GsoSetPasswordForm(SetPasswordForm):
    """Set new password (from reset link)."""
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'New password',
            'autocomplete': 'new-password',
            'class': 'w-full px-3 py-2.5 pr-12 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-sm focus:ring-2 focus:ring-primary focus:border-transparent transition-all outline-none'
        })
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Confirm new password',
            'autocomplete': 'new-password',
            'class': 'w-full px-3 py-2.5 pr-12 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-sm focus:ring-2 focus:ring-primary focus:border-transparent transition-all outline-none'
        })
    )


class RequestorProfileForm(forms.ModelForm):
    """Edit profile: first name, last name, email, avatar (requestor)."""
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'avatar_code')
        widgets = {
            'avatar_code': forms.Select(
                attrs={
                    'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-3 py-2 text-sm focus:ring-2 focus:ring-primary/30 focus:border-primary'
                }
            )
        }


class DirectorUserCreateForm(forms.ModelForm):
    """Director adds a new user; user sets password via invitation email."""

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'role', 'unit', 'office_department', 'employment_status', 'position_title')
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': 'Username', 'autocomplete': 'username', 'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-3 py-2 text-sm focus:ring-2 focus:ring-primary/30 focus:border-primary'}),
            'first_name': forms.TextInput(attrs={'placeholder': 'First name', 'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-3 py-2 text-sm focus:ring-2 focus:ring-primary/30 focus:border-primary'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Last name', 'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-3 py-2 text-sm focus:ring-2 focus:ring-primary/30 focus:border-primary'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Email', 'autocomplete': 'email', 'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-3 py-2 text-sm focus:ring-2 focus:ring-primary/30 focus:border-primary'}),
            'role': forms.Select(attrs={'class': 'rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-3 py-2 text-sm focus:ring-2 focus:ring-primary/30 focus:border-primary min-w-[200px]'}),
            'unit': forms.Select(attrs={'class': 'rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-3 py-2 text-sm focus:ring-2 focus:ring-primary/30 focus:border-primary min-w-[200px]'}),
            'office_department': forms.TextInput(attrs={'placeholder': 'Office/Department (e.g., Registrar, HR, Accounting)', 'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-3 py-2 text-sm focus:ring-2 focus:ring-primary/30 focus:border-primary'}),
            'employment_status': forms.TextInput(attrs={'placeholder': 'Employment status (e.g., Permanent, Job Order)', 'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-3 py-2 text-sm focus:ring-2 focus:ring-primary/30 focus:border-primary'}),
            'position_title': forms.TextInput(attrs={'placeholder': 'Position title (e.g., Carpenter, Admin Aide-III)', 'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-3 py-2 text-sm focus:ring-2 focus:ring-primary/30 focus:border-primary'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['unit'].required = False
        from apps.gso_units.models import Unit
        self.fields['unit'].queryset = Unit.objects.filter(is_active=True).order_by('name')
        self.fields['email'].required = True
        # Director role is system-level; do not allow creating directors from this form.
        if 'role' in self.fields:
            self.fields['role'].choices = [
                (v, l) for (v, l) in self.fields['role'].choices
                if v != User.Role.DIRECTOR
            ]

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if username and User.objects.filter(username__iexact=username).exists():
            raise ValidationError('A user with this username already exists.')
        return username

    def clean(self):
        data = super().clean()
        role = data.get('role')
        unit = data.get('unit')
        employment_status = (data.get('employment_status') or '').strip()
        position_title = (data.get('position_title') or '').strip()
        if role == User.Role.DIRECTOR:
            self.add_error('role', 'Director accounts cannot be created from Account Management.')
        if role in (User.Role.UNIT_HEAD, User.Role.PERSONNEL) and not unit:
            self.add_error('unit', 'Unit is required for Unit Head and Personnel.')
        if role == User.Role.PERSONNEL:
            if not employment_status:
                self.add_error('employment_status', 'Employment status is required for Personnel.')
            if not position_title:
                self.add_error('position_title', 'Position title is required for Personnel.')
        elif role == User.Role.REQUESTOR:
            data['employment_status'] = ''
            data['position_title'] = ''
        office = (data.get('office_department') or '').strip()
        if role == User.Role.REQUESTOR:
            if not office:
                self.add_error('office_department', 'Office/Department is required for Requestor.')
            elif User.objects.filter(role=User.Role.REQUESTOR, office_department__iexact=office).exists():
                self.add_error('office_department', 'A requestor account for this office/department already exists.')
        else:
            data['office_department'] = ''
        return data

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip()
        if not email:
            raise ValidationError('Email is required.')
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError('A user with this email already exists.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        # Security: no default password. User sets password via invite link.
        user.set_unusable_password()
        if commit:
            user.save()
        return user


class DirectorUserEditForm(forms.ModelForm):
    """Director edits user: profile and role. Optional password change."""
    password1 = forms.CharField(
        label='New password (leave blank to keep current)',
        required=False,
        widget=forms.PasswordInput(attrs={'placeholder': 'New password', 'autocomplete': 'new-password', 'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-3 py-2 pr-12 text-sm focus:ring-2 focus:ring-primary/30 focus:border-primary'}),
        strip=False,
    )
    password2 = forms.CharField(
        label='Confirm new password',
        required=False,
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm', 'autocomplete': 'new-password', 'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-3 py-2 pr-12 text-sm focus:ring-2 focus:ring-primary/30 focus:border-primary'}),
        strip=False,
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'role', 'unit', 'office_department', 'employment_status', 'position_title', 'is_active')
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': 'Username', 'autocomplete': 'username', 'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 px-3 py-2 text-sm'}),
            'first_name': forms.TextInput(attrs={'placeholder': 'First name', 'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-3 py-2 text-sm focus:ring-2 focus:ring-primary/30 focus:border-primary'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Last name', 'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-3 py-2 text-sm focus:ring-2 focus:ring-primary/30 focus:border-primary'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Email', 'autocomplete': 'email', 'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-3 py-2 text-sm focus:ring-2 focus:ring-primary/30 focus:border-primary'}),
            'role': forms.Select(attrs={'class': 'rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-3 py-2 text-sm focus:ring-2 focus:ring-primary/30 focus:border-primary min-w-[200px]'}),
            'unit': forms.Select(attrs={'class': 'rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-3 py-2 text-sm focus:ring-2 focus:ring-primary/30 focus:border-primary min-w-[200px]'}),
            'office_department': forms.TextInput(attrs={'placeholder': 'Office/Department (e.g., Registrar, HR, Accounting)', 'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-3 py-2 text-sm focus:ring-2 focus:ring-primary/30 focus:border-primary'}),
            'employment_status': forms.TextInput(attrs={'placeholder': 'Employment status (e.g., Permanent, Job Order)', 'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-3 py-2 text-sm focus:ring-2 focus:ring-primary/30 focus:border-primary'}),
            'position_title': forms.TextInput(attrs={'placeholder': 'Position title (e.g., Carpenter, Admin Aide-III)', 'class': 'w-full rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-3 py-2 text-sm focus:ring-2 focus:ring-primary/30 focus:border-primary'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['unit'].required = False
        from apps.gso_units.models import Unit
        self.fields['unit'].queryset = Unit.objects.filter(is_active=True).order_by('name')
        self.fields['email'].required = False
        self.fields['username'].disabled = True
        # Director role is system-level; do not allow assigning directors from this form.
        if 'role' in self.fields:
            self.fields['role'].choices = [
                (v, l) for (v, l) in self.fields['role'].choices
                if v != User.Role.DIRECTOR
            ]

    def clean(self):
        data = super().clean()
        p1 = data.get('password1')
        p2 = data.get('password2')
        if p1 or p2:
            if p1 != p2:
                self.add_error('password2', 'Passwords do not match.')
        role = data.get('role')
        unit = data.get('unit')
        employment_status = (data.get('employment_status') or '').strip()
        position_title = (data.get('position_title') or '').strip()
        if role == User.Role.DIRECTOR:
            self.add_error('role', 'Director role cannot be assigned from Account Management.')
        if role in (User.Role.UNIT_HEAD, User.Role.PERSONNEL) and not unit:
            self.add_error('unit', 'Unit is required for Unit Head and Personnel.')
        if role == User.Role.PERSONNEL:
            if not employment_status:
                self.add_error('employment_status', 'Employment status is required for Personnel.')
            if not position_title:
                self.add_error('position_title', 'Position title is required for Personnel.')
        elif role == User.Role.REQUESTOR:
            data['employment_status'] = ''
            data['position_title'] = ''
        office = (data.get('office_department') or '').strip()
        if role == User.Role.REQUESTOR:
            if not office:
                self.add_error('office_department', 'Office/Department is required for Requestor.')
            else:
                existing = User.objects.filter(
                    role=User.Role.REQUESTOR,
                    office_department__iexact=office,
                ).exclude(pk=self.instance.pk)
                if existing.exists():
                    self.add_error('office_department', 'A requestor account for this office/department already exists.')
        else:
            data['office_department'] = ''
        return data

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data.get('password1'):
            user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user
