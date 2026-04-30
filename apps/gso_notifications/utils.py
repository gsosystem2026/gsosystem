"""Helpers to create in-app notifications. Phase 4.4: submit, assigned, approved."""
import logging

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.template.loader import render_to_string
from django.urls import reverse

from core.emailing import send_gso_email
from .models import Notification

logger = logging.getLogger(__name__)


def _notification_unread_cache_key(user_id):
    return f"notif_unread_count:{user_id}"


def _email_notifications_enabled():
    return bool(getattr(settings, 'GSO_EMAIL_NOTIFICATIONS_ENABLED', True))


def _pick_notification_email(user, to_email=''):
    """
    Prefer explicit email override when valid; otherwise fall back to user.email.
    """
    candidates = [to_email, getattr(user, 'email', '')]
    for candidate in candidates:
        email = (candidate or '').strip()
        if not email:
            continue
        try:
            validate_email(email)
            return email
        except ValidationError:
            continue
    return ''


def _safe_send_email(user, title, message, link='', to_email=''):
    if not _email_notifications_enabled():
        logger.info('Notification email disabled by GSO_EMAIL_NOTIFICATIONS_ENABLED.')
        return
    email = _pick_notification_email(user, to_email=to_email)
    if not email:
        logger.warning(
            'Skipping notification email: no valid recipient for user_id=%s override=%s',
            getattr(user, 'id', None),
            (to_email or '').strip(),
        )
        return
    app_url = (getattr(settings, 'GSO_SITE_URL', '') or '').rstrip('/')
    resolved_link = link or ''
    if resolved_link and resolved_link.startswith('/') and app_url:
        resolved_link = f'{app_url}{resolved_link}'
    text_body = render_to_string(
        'emails/notification.txt',
        {
            'title': title,
            'message': message,
            'link': resolved_link,
            'user': user,
        },
    )
    html_body = render_to_string(
        'emails/notification.html',
        {
            'title': title,
            'message': message,
            'link': resolved_link,
            'user': user,
        },
    )
    try:
        send_gso_email(
            subject=f'GSO Notification: {title}',
            message=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_body,
            fail_silently=False,
        )
        logger.info(
            'Notification email sent to user_id=%s recipient=%s',
            getattr(user, 'id', None),
            email,
        )
    except Exception:
        logger.exception(
            'Failed sending notification email to user_id=%s recipient=%s',
            getattr(user, 'id', None),
            email,
        )


def _notify(user, title, message, link=''):
    notif = Notification.objects.create(user=user, title=title, message=message, link=link)
    cache.delete(_notification_unread_cache_key(user.id))
    _safe_send_email(user, title, message, link)
    return notif


def _notify_user_id(user_id, title, message, link='', email_override=''):
    notif = Notification.objects.create(user_id=user_id, title=title, message=message, link=link)
    cache.delete(_notification_unread_cache_key(user_id))
    if _email_notifications_enabled():
        from django.apps import apps
        app_label, model_name = settings.AUTH_USER_MODEL.rsplit('.', 1)
        UserModel = apps.get_model(app_label, model_name)
        user = UserModel.objects.filter(pk=user_id).first()
        if user:
            _safe_send_email(user, title, message, link, to_email=email_override)
    return notif


def _requestor_email_for_request(request_obj):
    """Requestor email routing: form-entered email first, then account email."""
    return (getattr(request_obj, 'custom_email', '') or '').strip()


def _request_context_line(request_obj):
    """Short request reference for notifications."""
    display_id = (getattr(request_obj, 'display_id', '') or '').strip()
    if display_id:
        return f"Request {display_id}"
    return 'Service request'


def notify_request_submitted(request_obj):
    """
    Create notifications when a request is submitted.
    - Requestor: "Your request was submitted."
    - Unit Head (of request unit): "New request for your unit."
    - GSO Office & Director: "New request submitted."
    """
    from django.apps import apps
    from django.conf import settings
    app_label, model_name = settings.AUTH_USER_MODEL.rsplit('.', 1)
    UserModel = apps.get_model(app_label, model_name)

    requestor_link = reverse('gso_requests:requestor_request_detail', args=[request_obj.pk])
    staff_link = reverse('gso_accounts:staff_request_detail', args=[request_obj.pk])
    title = f"Request {request_obj.display_id} submitted"
    context_line = _request_context_line(request_obj)

    # Notify requestor
    _notify_user_id(
        request_obj.requestor_id,
        f"Request {request_obj.display_id} submitted",
        "Your request has been received.",
        requestor_link,
        email_override=_requestor_email_for_request(request_obj),
    )

    # Notify Unit Head(s) for this unit (use staff detail URL)
    unit_heads = UserModel.objects.filter(role='UNIT_HEAD', unit_id=request_obj.unit_id)
    for u in unit_heads:
        if u.id != request_obj.requestor_id:
            _notify(u, title, f"New request for your unit: {context_line}", staff_link)

    # Notify GSO Office and Director
    staff = UserModel.objects.filter(role__in=('GSO_OFFICE', 'DIRECTOR'))
    for u in staff:
        _notify(u, title, context_line, staff_link)


def notify_director_approved(request_obj):
    """
    Phase 4.4: When Director approves, notify assigned Personnel, Unit Head(s), and the Requestor.
    """
    from django.apps import apps
    from django.conf import settings
    app_label, model_name = settings.AUTH_USER_MODEL.rsplit('.', 1)
    UserModel = apps.get_model(app_label, model_name)

    staff_link = reverse('gso_accounts:staff_request_detail', args=[request_obj.pk])
    requestor_link = reverse('gso_requests:requestor_request_detail', args=[request_obj.pk])
    title = f"Request {request_obj.display_id} approved"
    context_line = _request_context_line(request_obj)
    message = f"Approved. Work can start: {context_line}"

    # Notify requestor: their request has been approved
    _notify_user_id(
        request_obj.requestor_id,
        f"Request {request_obj.display_id} approved",
        "Your request has been approved. Work will start soon.",
        requestor_link,
        email_override=_requestor_email_for_request(request_obj),
    )

    # Notify each assigned personnel
    for a in request_obj.assignments.select_related('personnel').all():
        _notify(a.personnel, title, message, staff_link)

    # Notify Unit Head(s) for this unit
    unit_heads = UserModel.objects.filter(role='UNIT_HEAD', unit_id=request_obj.unit_id)
    for u in unit_heads:
        _notify(u, title, f"Request approved; personnel can start work: {context_line}", staff_link)


def notify_personnel_assigned(request_obj):
    """
    Phase 4.4: When Unit Head assigns personnel, notify each assigned Personnel and (optionally) Director/GSO.
    """
    from django.apps import apps
    from django.conf import settings
    app_label, model_name = settings.AUTH_USER_MODEL.rsplit('.', 1)
    UserModel = apps.get_model(app_label, model_name)

    staff_link = reverse('gso_accounts:staff_request_detail', args=[request_obj.pk])
    title = f"Request {request_obj.display_id} assigned"
    context_line = _request_context_line(request_obj)
    message = (
        f"You were assigned to: {context_line}. "
        "This request is waiting for Director approval before you can start work."
    )

    # Notify each assigned personnel
    for a in request_obj.assignments.select_related('personnel').all():
        _notify(a.personnel, title, message, staff_link)

    # Notify GSO Office and Director (optional per plan)
    staff = UserModel.objects.filter(role__in=('GSO_OFFICE', 'DIRECTOR'))
    for u in staff:
        _notify(u, title, f"Personnel assigned: {context_line}", staff_link)

    # Notify requestor: personnel has been assigned
    requestor_link = reverse('gso_requests:requestor_request_detail', args=[request_obj.pk])
    _notify_user_id(
        request_obj.requestor_id,
        f"Request {request_obj.display_id} assigned",
        "Personnel has been assigned to your request. It is now waiting for approval/work start.",
        requestor_link,
        email_override=_requestor_email_for_request(request_obj),
    )


def notify_after_personnel_work_status_change(request_obj, old_status, new_status):
    """
    After personnel saves a work status change (web or API). Same rules as UpdateWorkStatusView.
    - DONE_WORKING → notify_done_working (unit heads + requestor).
    - IN_PROGRESS from DIRECTOR_APPROVED/INSPECTION → requestor "work started".
    - IN_PROGRESS from ON_HOLD → requestor "work resumed".
    - ON_HOLD → requestor "on hold".
    """
    from apps.gso_requests.models import Request

    if new_status == Request.Status.DONE_WORKING:
        notify_done_working(request_obj)
        return
    if new_status == Request.Status.IN_PROGRESS:
        if old_status in (Request.Status.DIRECTOR_APPROVED, Request.Status.INSPECTION):
            notify_requestor_work_started(request_obj)
        elif old_status == Request.Status.ON_HOLD:
            notify_requestor_work_resumed(request_obj)
    elif new_status == Request.Status.ON_HOLD:
        notify_requestor_work_on_hold(request_obj)


def notify_done_working(request_obj):
    """Phase 5.4: When Personnel mark Done working, notify Unit Head(s) and the Requestor."""
    from django.apps import apps
    from django.conf import settings
    app_label, model_name = settings.AUTH_USER_MODEL.rsplit('.', 1)
    UserModel = apps.get_model(app_label, model_name)
    staff_link = reverse('gso_accounts:staff_request_detail', args=[request_obj.pk])
    requestor_link = reverse('gso_requests:requestor_request_detail', args=[request_obj.pk])
    title = f"Request {request_obj.display_id} — Done working"
    context_line = _request_context_line(request_obj)
    message = f"Personnel marked work complete for review: {context_line}"
    unit_heads = UserModel.objects.filter(role='UNIT_HEAD', unit_id=request_obj.unit_id)
    for u in unit_heads:
        _notify(u, title, message, staff_link)
    # Notify requestor: work is done, waiting for unit head to approve completion
    _notify_user_id(
        request_obj.requestor_id,
        f"Request {request_obj.display_id} — Work done",
        "Work on your request is complete. It is now awaiting approval from the unit head before it is marked completed.",
        requestor_link,
        email_override=_requestor_email_for_request(request_obj),
    )


def notify_requestor_work_started(request_obj):
    """Notify requestor when personnel start work (status → IN_PROGRESS from DIRECTOR_APPROVED)."""
    requestor_link = reverse('gso_requests:requestor_request_detail', args=[request_obj.pk])
    _notify_user_id(
        request_obj.requestor_id,
        f"Request {request_obj.display_id} — Work started",
        "Work has started on your request.",
        requestor_link,
        email_override=_requestor_email_for_request(request_obj),
    )


def notify_requestor_work_resumed(request_obj):
    """Notify requestor when personnel resume work (status → IN_PROGRESS from ON_HOLD)."""
    requestor_link = reverse('gso_requests:requestor_request_detail', args=[request_obj.pk])
    _notify_user_id(
        request_obj.requestor_id,
        f"Request {request_obj.display_id} — Work resumed",
        "Work on your request has resumed.",
        requestor_link,
        email_override=_requestor_email_for_request(request_obj),
    )


def notify_requestor_work_on_hold(request_obj):
    """Notify requestor when personnel put work on hold."""
    requestor_link = reverse('gso_requests:requestor_request_detail', args=[request_obj.pk])
    _notify_user_id(
        request_obj.requestor_id,
        f"Request {request_obj.display_id} — On hold",
        "Work on your request has been put on hold.",
        requestor_link,
        email_override=_requestor_email_for_request(request_obj),
    )


def notify_returned_for_rework(request_obj):
    """When Unit Head returns work for rework, notify assigned Personnel."""
    staff_link = reverse('gso_accounts:staff_request_detail', args=[request_obj.pk])
    title = f"Request {request_obj.display_id} returned for rework"
    message = (
        f"Unit Head returned this request for rework. "
        f"Please review and complete the work again: {_request_context_line(request_obj)}"
    )
    for a in request_obj.assignments.select_related('personnel').all():
        _notify(a.personnel, title, message, staff_link)


def notify_request_completed(request_obj):
    """Phase 5.4: When Unit Head completes request, notify Requestor and optionally GSO/Director."""
    from django.apps import apps
    from django.conf import settings
    app_label, model_name = settings.AUTH_USER_MODEL.rsplit('.', 1)
    UserModel = apps.get_model(app_label, model_name)
    requestor_link = reverse('gso_requests:requestor_request_detail', args=[request_obj.pk])
    staff_link = reverse('gso_accounts:staff_request_detail', args=[request_obj.pk])
    title = f"Request {request_obj.display_id} completed"
    message = (
        f"Your request has been completed: {_request_context_line(request_obj)}. "
        "Please submit your feedback (Client Satisfaction form) for this request."
    )
    _notify_user_id(
        request_obj.requestor_id,
        title,
        message,
        requestor_link,
        email_override=_requestor_email_for_request(request_obj),
    )
    for u in UserModel.objects.filter(role__in=('GSO_OFFICE', 'DIRECTOR')):
        _notify(u, title, f"Request completed: {_request_context_line(request_obj)}", staff_link)


def notify_oic_assigned(oic_user, director):
    """Phase 8.1: When Director assigns OIC, notify the OIC user."""
    link = reverse('gso_accounts:staff_request_management')
    _notify(
        oic_user,
        'You are now Officer-in-Charge (OIC)',
        'You can approve requests on behalf of the Director. Go to Request Management to approve assigned requests.',
        link,
    )


def notify_oic_revoked(oic_user, director):
    """Phase 8.1: When Director revokes OIC, notify the former OIC user."""
    link = reverse('gso_accounts:staff_dashboard')
    _notify(
        oic_user,
        'OIC designation revoked',
        'You no longer have approval authority. Only the Director can approve requests now.',
        link,
    )


def notify_requestor_edited_request(request_obj):
    """When requestor edits their request (after submit), notify Unit Head for this unit, GSO, Director."""
    from django.apps import apps
    from django.conf import settings
    app_label, model_name = settings.AUTH_USER_MODEL.rsplit('.', 1)
    UserModel = apps.get_model(app_label, model_name)
    staff_link = reverse('gso_accounts:staff_request_detail', args=[request_obj.pk])
    title = f"Request {request_obj.display_id} updated by requestor"
    message = f"{_request_context_line(request_obj)} — requestor made changes. Please review if needed."
    for u in UserModel.objects.filter(role='UNIT_HEAD', unit_id=request_obj.unit_id):
        _notify(u, title, message, staff_link)
    for u in UserModel.objects.filter(role__in=('GSO_OFFICE', 'DIRECTOR')):
        _notify(u, title, message, staff_link)


def notify_requestor_cancelled_request(request_obj):
    """When requestor cancels their request, notify Unit Head, GSO Office, Director."""
    from django.apps import apps
    from django.conf import settings
    app_label, model_name = settings.AUTH_USER_MODEL.rsplit('.', 1)
    UserModel = apps.get_model(app_label, model_name)
    staff_link = reverse('gso_accounts:staff_request_detail', args=[request_obj.pk])
    title = f"Request {request_obj.display_id} cancelled by requestor"
    message = f"{_request_context_line(request_obj)} — requestor cancelled this request."
    unit_heads = UserModel.objects.filter(role='UNIT_HEAD', unit_id=request_obj.unit_id)
    for u in unit_heads:
        _notify(u, title, message, staff_link)
    for u in UserModel.objects.filter(role__in=('GSO_OFFICE', 'DIRECTOR')):
        _notify(u, title, message, staff_link)


def notify_gso_reminder(request_obj, target):
    """
    GSO Office sends a reminder notification to Director, Unit Head, or Personnel
    about a pending request that needs their attention.
    target: 'director' | 'unit_head' | 'personnel'
    """
    from django.apps import apps
    from django.conf import settings
    from django.db.models import Q
    app_label, model_name = settings.AUTH_USER_MODEL.rsplit('.', 1)
    UserModel = apps.get_model(app_label, model_name)

    staff_link = reverse('gso_accounts:staff_request_detail', args=[request_obj.pk])
    title = f"Reminder: {request_obj.display_id} needs your attention"
    message = _request_context_line(request_obj)

    if target == 'director':
        # Director and OIC: request pending approval (status ASSIGNED)
        users = UserModel.objects.filter(
            Q(role='DIRECTOR') | Q(oic_for_director__isnull=False)
        ).distinct()
        msg = f"Request {request_obj.display_id} is waiting for your approval. Please review and approve so personnel can start work."
        for u in users:
            _notify(u, title, msg, staff_link)

    elif target == 'unit_head':
        # Unit Head(s) for this unit
        unit_heads = UserModel.objects.filter(role='UNIT_HEAD', unit_id=request_obj.unit_id)
        if request_obj.status == request_obj.Status.SUBMITTED:
            msg = f"Request {request_obj.display_id} needs personnel assignment. Please assign personnel to this request."
        elif request_obj.status == request_obj.Status.DONE_WORKING:
            msg = f"Request {request_obj.display_id} — work is done. Please review and mark as completed."
        else:
            msg = f"Request {request_obj.display_id} needs your attention: {message}"
        for u in unit_heads:
            _notify(u, title, msg, staff_link)

    elif target == 'personnel':
        # Assigned personnel
        for a in request_obj.assignments.select_related('personnel').all():
            msg = f"Reminder: Request {request_obj.display_id} is assigned to you and needs your attention. Please start or continue work."
            _notify(a.personnel, title, msg, staff_link)


def notify_material_request_submitted(material_request):
    """Notify Unit Head(s) when personnel submit a material request."""
    from django.apps import apps
    from django.conf import settings
    app_label, model_name = settings.AUTH_USER_MODEL.rsplit('.', 1)
    UserModel = apps.get_model(app_label, model_name)

    req = material_request.request
    staff_link = reverse('gso_accounts:staff_request_detail', args=[req.pk])
    requester_name = material_request.requested_by.get_full_name() or material_request.requested_by.username
    title = f"Material request submitted — {req.display_id}"
    message = (
        f'{requester_name} requested '
        f'{material_request.quantity} x {material_request.item.name}.'
    )
    for u in UserModel.objects.filter(role='UNIT_HEAD', unit_id=req.unit_id):
        _notify(u, title, message, staff_link)


def notify_material_request_approved(material_request):
    """Notify requesting personnel when Unit Head approves a material request."""
    req = material_request.request
    staff_link = reverse('gso_accounts:staff_request_detail', args=[req.pk])
    _notify(
        material_request.requested_by,
        f"Material request approved — {req.display_id}",
        f'Your material request for "{material_request.item.name}" was approved.',
        staff_link,
    )


def notify_material_request_rejected(material_request):
    """Notify requesting personnel when Unit Head rejects a material request."""
    req = material_request.request
    staff_link = reverse('gso_accounts:staff_request_detail', args=[req.pk])
    _notify(
        material_request.requested_by,
        f"Material request rejected — {req.display_id}",
        f'Your material request for "{material_request.item.name}" was rejected.',
        staff_link,
    )
