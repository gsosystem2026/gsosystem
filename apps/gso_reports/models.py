"""
Phase 6.1: Work Accomplishment Report (WAR).
Phase 6.2: Success indicators — master data; WAR entries can be tagged with indicators.
"""
from django.conf import settings
from django.db import models
from decimal import Decimal
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)


class SuccessIndicator(models.Model):
    """
    Phase 6.2: Master data for success indicators.
    WAR entries (and later IPMT) can be aligned to these so "what was done" maps to indicators.
    """
    code = models.CharField(max_length=50, unique=True, help_text='Short code, e.g. SI-01')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    target_position = models.CharField(
        max_length=150,
        blank=True,
        default='',
        help_text='Optional position this indicator applies to, e.g. Carpenter. Leave blank for all positions.',
    )
    target_unit = models.ForeignKey(
        'gso_units.Unit',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='success_indicators',
        help_text='Optional GSO service unit this indicator applies to. Leave blank for all units.',
    )
    display_order = models.PositiveSmallIntegerField(default=0, help_text='Order in lists/dropdowns')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'code']
        verbose_name = 'success indicator'
        verbose_name_plural = 'success indicators'

    def __str__(self):
        return f"{self.code}: {self.name}"


class WorkAccomplishmentReport(models.Model):
    """
    WAR: linked to a completed Request and to the Personnel who did the work.
    One request can have multiple WARs (one per assigned personnel).
    """
    request = models.ForeignKey(
        'gso_requests.Request',
        on_delete=models.CASCADE,
        related_name='work_accomplishment_reports',
    )
    personnel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='work_accomplishment_reports',
        limit_choices_to={'role': 'PERSONNEL'},
        help_text='Personnel who did the work (must be assigned to this request).',
    )
    period_start = models.DateField(
        help_text='Start of the work period covered by this report.',
    )
    period_end = models.DateField(
        help_text='End of the work period covered by this report.',
    )
    summary = models.CharField(
        max_length=255,
        blank=True,
        help_text='Short summary or title.',
    )
    accomplishments = models.TextField(
        blank=True,
        help_text='Description of work accomplished.',
    )
    material_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Material cost for this work entry.',
    )
    labor_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Labor cost for this work entry.',
    )
    total_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Auto-computed total cost (material + labor).',
    )
    success_indicators = models.ManyToManyField(
        SuccessIndicator,
        related_name='work_accomplishment_reports',
        blank=True,
        help_text='Success indicators this work aligns to (Phase 6.2).',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='war_created',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-period_end', '-created_at']
        verbose_name = 'work accomplishment report'
        verbose_name_plural = 'work accomplishment reports'
        unique_together = [('request', 'personnel')]

    def __str__(self):
        return f"WAR: {self.request.display_id} — {self.personnel.get_full_name() or self.personnel.username}"

    def save(self, *args, **kwargs):
        material = self.material_cost if self.material_cost is not None else Decimal('0')
        labor = self.labor_cost if self.labor_cost is not None else Decimal('0')
        if self.material_cost is None and self.labor_cost is None:
            self.total_cost = None
        else:
            self.total_cost = material + labor
        super().save(*args, **kwargs)

    @property
    def accomplishments_for_display(self):
        text = self.accomplishments or ""
        if text.startswith("[MIGRATED-LEGACY|"):
            lines = text.splitlines()
            if lines:
                lines = lines[1:]
            while lines and not lines[0].strip():
                lines.pop(0)
            return "\n".join(lines)
        return text


class IPMTDraft(models.Model):
    """Saved editable IPMT draft per personnel and period."""

    personnel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ipmt_drafts',
        limit_choices_to={'role': 'PERSONNEL'},
    )
    year = models.PositiveSmallIntegerField()
    month = models.PositiveSmallIntegerField()
    rows_json = models.JSONField(default=list, blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ipmt_drafts_updated',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        unique_together = [('personnel', 'year', 'month')]
        verbose_name = 'IPMT draft'
        verbose_name_plural = 'IPMT drafts'

    def __str__(self):
        person = self.personnel.get_full_name() or self.personnel.username
        return f"IPMT Draft: {person} ({self.year}-{self.month:02d})"


def ensure_war_for_request(request_obj, created_by=None):
    """
    Ensure that a completed request has one WAR per assigned personnel.
    - Called when a request becomes COMPLETED.
    - Idempotent: safe to call multiple times for the same request.
    - Skips requests with no personnel assignments.
    """
    from apps.gso_requests.models import RequestAssignment, Request  # local import to avoid circulars

    if not isinstance(request_obj, Request):
        return
    # Only act for completed requests
    if request_obj.status != Request.Status.COMPLETED:
        return

    # If no personnel are assigned, skip WAR creation
    assigned_ids = list(
        RequestAssignment.objects.filter(request=request_obj).values_list("personnel_id", flat=True)
    )
    if not assigned_ids:
        return

    existing_personnel_ids = set(
        WorkAccomplishmentReport.objects.filter(request=request_obj).values_list("personnel_id", flat=True)
    )
    to_create_ids = [pid for pid in assigned_ids if pid not in existing_personnel_ids]
    if not to_create_ids:
        return

    # Default period: from request created_at to completed_at (use updated_at as completion timestamp)
    created_date = getattr(request_obj, "created_at", None) or timezone.now()
    completed_date = getattr(request_obj, "updated_at", None) or timezone.now()
    period_start = created_date.date()
    period_end = completed_date.date()

    from apps.gso_accounts.models import User  # local import
    from .ai_service import generate_war_draft, is_ai_configured  # local import

    personnel_qs = User.objects.filter(pk__in=to_create_ids)
    can_generate_ai = is_ai_configured()
    for personnel in personnel_qs:
        summary = "To be filled"
        accomplishments = "To be filled"

        unit_code = (getattr(request_obj.unit, 'code', '') or '').strip().lower() if getattr(request_obj, 'unit_id', None) else ''
        if unit_code == 'motorpool':
            mp = getattr(request_obj, 'motorpool_trip', None)
            purpose = (request_obj.description or '').strip()
            itinerary = (getattr(mp, 'itinerary_of_travel', '') or '').strip()
            first_line = next((ln.strip() for ln in itinerary.splitlines() if ln.strip()), '')

            summary = 'Motorpool trip' if purpose else 'Motorpool transport'

            parts = []
            if purpose:
                parts.append(f"Completed motorpool vehicle transport for: {purpose}.")
            else:
                parts.append("Completed motorpool vehicle transport.")

            # Add one more sentence only when we have factual material.
            fuel_used = getattr(mp, 'fuel_used_liters', None) if mp else None
            other_notes = (getattr(mp, 'other_consumables_notes', '') or '').strip() if mp else ''
            if fuel_used not in (None, ''):
                parts.append(f"Fuel used recorded: {fuel_used} liters.")
            elif other_notes:
                parts.append(f"Consumables noted: {other_notes}.")
            elif first_line:
                parts.append(f"Itinerary (planned lines): {first_line}.")

            accomplishments = ' '.join(parts).strip()
        elif can_generate_ai:
            try:
                ai_draft = generate_war_draft(request_obj=request_obj, personnel=personnel)
                summary = ai_draft.get("summary") or summary
                accomplishments = ai_draft.get("accomplishments") or accomplishments
            except Exception:
                # Fail open: request completion/WAR creation should continue even if AI fails.
                logger.exception(
                    'WAR AI draft generation failed (request_id=%s, personnel_id=%s)',
                    getattr(request_obj, 'id', None),
                    getattr(personnel, 'id', None),
                )
        WorkAccomplishmentReport.objects.create(
            request=request_obj,
            personnel=personnel,
            period_start=period_start,
            period_end=period_end,
            summary=summary,
            accomplishments=accomplishments,
            material_cost=None,
            labor_cost=None,
            total_cost=None,
            created_by=created_by,
        )
