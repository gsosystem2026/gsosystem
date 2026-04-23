from django.conf import settings
from django.db import models


class Request(models.Model):
    """GSO request: one per submission, tied to a single unit (Phase 2.1)."""

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        SUBMITTED = 'SUBMITTED', 'Submitted'
        ASSIGNED = 'ASSIGNED', 'Assigned'
        DIRECTOR_APPROVED = 'DIRECTOR_APPROVED', 'Approved'
        INSPECTION = 'INSPECTION', 'Inspection'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        ON_HOLD = 'ON_HOLD', 'On Hold'
        DONE_WORKING = 'DONE_WORKING', 'Done working'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    requestor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='gso_requests',
    )
    unit = models.ForeignKey(
        'gso_units.Unit',
        on_delete=models.PROTECT,
        related_name='requests',
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=255, blank=True)
    # Request type checkboxes (labor / materials / others)
    labor = models.BooleanField(default=False)
    materials = models.BooleanField(default=False)
    others = models.BooleanField(default=False)
    # Optional requestor info at submission (e.g. contact for this request)
    custom_full_name = models.CharField(max_length=255, blank=True)
    custom_email = models.EmailField(blank=True)
    custom_contact_number = models.CharField(max_length=32, blank=True)
    attachment = models.FileField(
        upload_to='gso_requests/%Y/%m/',
        blank=True,
        null=True,
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    is_emergency = models.BooleanField(
        default=False,
        help_text='Unit Head marks as emergency (e.g. school president request). Shown at top for Director/GSO.',
    )
    requestor_cancel_reason = models.TextField(
        blank=True,
        help_text='Reason given by requestor when they cancelled (before work started).',
    )
    requestor_cancelled_at = models.DateTimeField(null=True, blank=True)
    # First moment work actually started; used for ON_HOLD button label logic.
    work_started_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'request'
        verbose_name_plural = 'requests'

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    @property
    def display_id(self):
        """Human-readable ID for lists/detail (e.g. GSO-2025-0001)."""
        if self.pk:
            return f"GSO-{self.created_at.year}-{self.pk:04d}"
        return "—"

    @property
    def unit_name(self):
        return self.unit.name if self.unit_id else "—"

    @property
    def status_display(self):
        return self.get_status_display()

    @property
    def show_urgent_indicator(self):
        """True if request should show red/emergency styling. Only Unit Head can mark as emergency."""
        return self.is_emergency

    @property
    def unit_icon(self):
        """Material symbol name per unit code for dashboard/listing."""
        if not self.unit_id:
            return "build"
        icons = {
            'repair': 'build',
            'utility': 'cleaning_services',
            'electrical': 'bolt',
            'motorpool': 'directions_car',
        }
        return icons.get(self.unit.code, 'build')

    @property
    def unit_icon_class(self):
        """Tailwind text color class per unit for dashboard."""
        if not self.unit_id:
            return 'text-slate-500'
        classes = {
            'repair': 'text-blue-500',
            'utility': 'text-green-500',
            'electrical': 'text-amber-500',
            'motorpool': 'text-indigo-500',
        }
        return classes.get(self.unit.code, 'text-slate-500')

    @property
    def status_badge_class(self):
        """Tailwind classes for status badge."""
        map_ = {
            self.Status.DRAFT: 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300',
            self.Status.SUBMITTED: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
            self.Status.ASSIGNED: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
            self.Status.DIRECTOR_APPROVED: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400',
            self.Status.INSPECTION: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-300',
            self.Status.IN_PROGRESS: 'bg-primary/10 text-primary',
            self.Status.ON_HOLD: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
            self.Status.DONE_WORKING: 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300',
            self.Status.COMPLETED: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
            self.Status.CANCELLED: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
        }
        return map_.get(self.status, 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300')


class RequestAssignment(models.Model):
    """Phase 4.1: Unit Head assigns one or more Personnel to a request (waiting Director approval)."""
    request = models.ForeignKey(
        Request,
        on_delete=models.CASCADE,
        related_name='assignments',
    )
    personnel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='request_assignments',
        limit_choices_to={'role': 'PERSONNEL'},
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assignments_made',
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['assigned_at']
        unique_together = [('request', 'personnel')]
        verbose_name = 'request assignment'
        verbose_name_plural = 'request assignments'

    def __str__(self):
        return f"{self.request.display_id} → {self.personnel.get_full_name() or self.personnel.username}"


class RequestMessage(models.Model):
    """Phase 5.2: Per-request chat/activity — Personnel, Unit Head, GSO, Director can post."""
    request = models.ForeignKey(
        Request,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='request_messages',
    )
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'request message'
        verbose_name_plural = 'request messages'

    def __str__(self):
        return f"{self.request.display_id} — {self.user} at {self.created_at}"


class RequestFeedback(models.Model):
    """Phase 7.1: CSM-style feedback per request. Requestor only, for completed requests."""
    request = models.ForeignKey(
        Request,
        on_delete=models.CASCADE,
        related_name='feedback',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='request_feedback',
    )
    # Legacy (optional) for backward compatibility
    rating = models.PositiveSmallIntegerField(
        choices=[(i, str(i)) for i in range(1, 6)],
        blank=True,
        null=True,
    )
    comment = models.TextField(blank=True)
    # Part I: Citizen's Charter Awareness (CC1–CC3)
    CC1_CHOICES = [
        ('', ''),
        ('know_saw', 'I know what a CC is and I saw this office\'s CC'),
        ('know_no_saw', 'I know what a CC is but I did not see this office\'s CC'),
        ('learned_here', 'I learned of the CC only when I saw this office\'s CC'),
        ('no_know', 'I do not know what a CC is and I did not see one in this office'),
    ]
    CC2_CHOICES = [
        ('', ''),
        ('easy', 'Easy to see'),
        ('somewhat', 'Somewhat easy to see'),
        ('difficult', 'Difficult to see'),
        ('not_visible', 'Not visible at all'),
    ]
    CC3_CHOICES = [
        ('', ''),
        ('very_much', 'Helped very much'),
        ('somewhat', 'Somewhat helped'),
        ('no_help', 'Did not help'),
    ]
    cc1 = models.CharField(max_length=32, choices=CC1_CHOICES, blank=True)
    cc2 = models.CharField(max_length=32, choices=CC2_CHOICES, blank=True)
    cc3 = models.CharField(max_length=32, choices=CC3_CHOICES, blank=True)
    # Part II: Service Quality Dimensions SQD1–SQD9 (1=Strongly Disagree to 5=Strongly Agree)
    SQD_SCALE = [(i, str(i)) for i in range(1, 6)]
    sqd1 = models.PositiveSmallIntegerField(choices=SQD_SCALE, null=True, blank=True)
    sqd2 = models.PositiveSmallIntegerField(choices=SQD_SCALE, null=True, blank=True)
    sqd3 = models.PositiveSmallIntegerField(choices=SQD_SCALE, null=True, blank=True)
    sqd4 = models.PositiveSmallIntegerField(choices=SQD_SCALE, null=True, blank=True)
    sqd5 = models.PositiveSmallIntegerField(choices=SQD_SCALE, null=True, blank=True)
    sqd6 = models.PositiveSmallIntegerField(choices=SQD_SCALE, null=True, blank=True)
    sqd7 = models.PositiveSmallIntegerField(choices=SQD_SCALE, null=True, blank=True)
    sqd8 = models.PositiveSmallIntegerField(choices=SQD_SCALE, null=True, blank=True)
    sqd9 = models.PositiveSmallIntegerField(choices=SQD_SCALE, null=True, blank=True)
    suggestions = models.TextField(blank=True)
    email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = [('request', 'user')]
        verbose_name = 'request feedback'
        verbose_name_plural = 'request feedback'

    # SQD question labels for forms/reports (1–9)
    SQD_LABELS = [
        'The office was easy to find/locate.',
        'The office had adequate signage.',
        'I was attended to promptly.',
        'The staff were courteous and professional.',
        'The service met my expectations.',
        'The transaction was completed within the promised time.',
        'I was satisfied with the overall service.',
        'The facilities were clean and adequate.',
        'I would recommend this office to others.',
    ]

    def __str__(self):
        if self.cc1 or self.sqd1:
            return f"{self.request.display_id} — {self.user} (CSM)"
        return f"{self.request.display_id} — {self.user} ({self.rating or '—'}/5)"
