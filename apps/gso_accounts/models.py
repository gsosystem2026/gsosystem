from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    """Custom user with role and optional unit (for Unit Head / Personnel)."""

    AVATAR_CHOICES = (
        ('man1', 'Man 1'),
        ('man2', 'Man 2'),
        ('man3', 'Man 3'),
        ('man4', 'Man 4'),
        ('man5', 'Man 5'),
        ('man6', 'Man 6'),
        ('man7', 'Man 7'),
        ('man8', 'Man 8'),
        ('man9', 'Man 9'),
        ('woman1', 'Woman 1'),
        ('woman2', 'Woman 2'),
        ('woman3', 'Woman 3'),
        ('woman4', 'Woman 4'),
        ('woman5', 'Woman 5'),
        ('woman6', 'Woman 6'),
        ('woman7', 'Woman 7'),
        ('woman8', 'Woman 8'),
    )

    class Role(models.TextChoices):
        REQUESTOR = 'REQUESTOR', 'Requestor'
        UNIT_HEAD = 'UNIT_HEAD', 'Unit Head'
        PERSONNEL = 'PERSONNEL', 'Personnel'
        GSO_OFFICE = 'GSO_OFFICE', 'GSO Office'
        DIRECTOR = 'DIRECTOR', 'Director'

    class AccountStatus(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        SUSPENDED = 'SUSPENDED', 'Suspended'
        DEACTIVATED = 'DEACTIVATED', 'Deactivated'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.REQUESTOR,
    )
    unit = models.ForeignKey(
        'gso_units.Unit',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        help_text='Unit for Unit Head / Personnel.',
    )
    office_department = models.CharField(
        max_length=150,
        blank=True,
        default='',
        help_text='Office/Department for requestor accounts.',
    )
    account_status = models.CharField(
        max_length=16,
        choices=AccountStatus.choices,
        default=AccountStatus.ACTIVE,
        help_text='Lifecycle status for login access control.',
    )
    restriction_reason_category = models.CharField(
        max_length=32,
        blank=True,
        default='',
        help_text='Reason category when account is suspended/deactivated.',
    )
    restriction_reason_details = models.TextField(
        blank=True,
        default='',
        help_text='Detailed reason when account is suspended/deactivated.',
    )
    suspended_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Optional end time for suspension.',
    )
    status_changed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Timestamp when account status last changed.',
    )
    status_changed_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='status_changed_users',
        help_text='Director who changed this account status.',
    )
    avatar_code = models.CharField(
        max_length=20,
        choices=AVATAR_CHOICES,
        blank=True,
        default='man1',
        help_text='Static avatar image key (man1–man9, woman1–woman8).',
    )
    # Phase 4.3: When set, this user (GSO Office) can perform Director approvals as OIC until revoked.
    oic_for_director = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='oic_users',
        help_text='Director who designated this user as Officer-in-Charge (OIC).',
    )

    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    # Convenience booleans for templates (e.g. {% if user.is_director %}) for templates and views
    @property
    def is_requestor(self):
        return self.role == self.Role.REQUESTOR

    @property
    def is_unit_head(self):
        return self.role == self.Role.UNIT_HEAD

    @property
    def is_personnel(self):
        return self.role == self.Role.PERSONNEL

    @property
    def is_gso_office(self):
        return self.role == self.Role.GSO_OFFICE

    @property
    def is_director(self):
        return self.role == self.Role.DIRECTOR

    @property
    def is_staff_role(self):
        """True if user uses staff layout (sidebar): Unit Head, Personnel, GSO Office, Director."""
        return self.role in (
            self.Role.UNIT_HEAD,
            self.Role.PERSONNEL,
            self.Role.GSO_OFFICE,
            self.Role.DIRECTOR,
        )

    @property
    def avatar_static_path(self):
        """Return static path for the selected avatar PNG."""
        code = self.avatar_code or 'man1'
        return f"img/avatars/{code}.png"

    @property
    def can_approve_requests(self):
        """True if user can approve requests (Director or designated OIC). Phase 4.2 / 4.3."""
        return self.is_director or bool(self.oic_for_director_id)

    @property
    def is_suspended_now(self):
        if self.account_status != self.AccountStatus.SUSPENDED:
            return False
        if self.suspended_until and timezone.now() > self.suspended_until:
            return False
        return True


def log_audit(action, user, message, target_model=None, target_id=None):
    """Phase 9.3: Record a sensitive action for audit. Call from views (approve, OIC assign/revoke)."""
    AuditLog.objects.create(
        user=user,
        action=action,
        message=message,
        target_model=target_model or '',
        target_id=target_id,
    )


class AuditLog(models.Model):
    """Phase 9.3: Audit trail for sensitive actions (Director approval, OIC assign/revoke)."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs',
    )
    action = models.CharField(max_length=64, help_text='e.g. director_approve, oic_assign, oic_revoke')
    message = models.TextField(help_text='Human-readable description')
    target_model = models.CharField(max_length=100, blank=True, help_text='Optional: model name')
    target_id = models.CharField(max_length=50, blank=True, null=True, help_text='Optional: object id')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'audit log'
        verbose_name_plural = 'audit logs'

    def __str__(self):
        who = getattr(self.user, 'username', None) or 'Unknown'
        return f"{self.action} by {who} at {self.created_at}"


class PasswordResetOTP(models.Model):
    """One-time password used for email-based password reset."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='password_reset_otps',
    )
    code = models.CharField(max_length=6)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['expires_at']),
        ]

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @property
    def is_used(self):
        return self.used_at is not None

    def __str__(self):
        return f"OTP for {self.user_id} at {self.created_at}"
