"""Helpers to create in-app notifications. Phase 4.4: submit, assigned, approved."""
from django.urls import reverse

from .models import Notification


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
    message = f"{request_obj.title} — {request_obj.unit.name}"

    # Notify requestor
    Notification.objects.create(
        user_id=request_obj.requestor_id,
        title=f"Request {request_obj.display_id} submitted",
        message="Your request has been received.",
        link=requestor_link,
    )

    # Notify Unit Head(s) for this unit (use staff detail URL)
    unit_heads = UserModel.objects.filter(role='UNIT_HEAD', unit_id=request_obj.unit_id)
    for u in unit_heads:
        if u.id != request_obj.requestor_id:
            Notification.objects.create(
                user=u,
                title=title,
                message=f"New request for your unit: {request_obj.unit.name}",
                link=staff_link,
            )

    # Notify GSO Office and Director
    staff = UserModel.objects.filter(role__in=('GSO_OFFICE', 'DIRECTOR'))
    for u in staff:
        Notification.objects.create(
            user=u,
            title=title,
            message=message,
            link=staff_link,
        )


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
    message = f"Work can start: {request_obj.title}"

    # Notify requestor: their request has been approved
    Notification.objects.create(
        user_id=request_obj.requestor_id,
        title=f"Request {request_obj.display_id} approved",
        message="Your request has been approved. Work will start soon.",
        link=requestor_link,
    )

    # Notify each assigned personnel
    for a in request_obj.assignments.select_related('personnel').all():
        Notification.objects.create(
            user=a.personnel,
            title=title,
            message=message,
            link=staff_link,
        )

    # Notify Unit Head(s) for this unit
    unit_heads = UserModel.objects.filter(role='UNIT_HEAD', unit_id=request_obj.unit_id)
    for u in unit_heads:
        Notification.objects.create(
            user=u,
            title=title,
            message=f"Request approved; personnel can start work: {request_obj.title}",
            link=staff_link,
        )


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
    message = f"You have been assigned to: {request_obj.title}"

    # Notify each assigned personnel
    for a in request_obj.assignments.select_related('personnel').all():
        Notification.objects.create(
            user=a.personnel,
            title=title,
            message=message,
            link=staff_link,
        )

    # Notify GSO Office and Director (optional per plan)
    staff = UserModel.objects.filter(role__in=('GSO_OFFICE', 'DIRECTOR'))
    for u in staff:
        Notification.objects.create(
            user=u,
            title=title,
            message=f"Personnel assigned to {request_obj.title} — {request_obj.unit.name}",
            link=staff_link,
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
    message = f"Personnel marked work complete for review: {request_obj.title}"
    unit_heads = UserModel.objects.filter(role='UNIT_HEAD', unit_id=request_obj.unit_id)
    for u in unit_heads:
        Notification.objects.create(user=u, title=title, message=message, link=staff_link)
    # Notify requestor: work is done, waiting for unit head to approve completion
    Notification.objects.create(
        user_id=request_obj.requestor_id,
        title=f"Request {request_obj.display_id} — Work done",
        message="Work on your request is complete. It is now awaiting approval from the unit head before it is marked completed.",
        link=requestor_link,
    )


def notify_requestor_work_started(request_obj):
    """Notify requestor when personnel start work (status → IN_PROGRESS from DIRECTOR_APPROVED)."""
    requestor_link = reverse('gso_requests:requestor_request_detail', args=[request_obj.pk])
    Notification.objects.create(
        user_id=request_obj.requestor_id,
        title=f"Request {request_obj.display_id} — Work started",
        message="Work has started on your request.",
        link=requestor_link,
    )


def notify_requestor_work_resumed(request_obj):
    """Notify requestor when personnel resume work (status → IN_PROGRESS from ON_HOLD)."""
    requestor_link = reverse('gso_requests:requestor_request_detail', args=[request_obj.pk])
    Notification.objects.create(
        user_id=request_obj.requestor_id,
        title=f"Request {request_obj.display_id} — Work resumed",
        message="Work on your request has resumed.",
        link=requestor_link,
    )


def notify_requestor_work_on_hold(request_obj):
    """Notify requestor when personnel put work on hold."""
    requestor_link = reverse('gso_requests:requestor_request_detail', args=[request_obj.pk])
    Notification.objects.create(
        user_id=request_obj.requestor_id,
        title=f"Request {request_obj.display_id} — On hold",
        message="Work on your request has been put on hold.",
        link=requestor_link,
    )


def notify_returned_for_rework(request_obj):
    """When Unit Head returns work for rework, notify assigned Personnel."""
    staff_link = reverse('gso_accounts:staff_request_detail', args=[request_obj.pk])
    title = f"Request {request_obj.display_id} returned for rework"
    message = f"Unit Head returned this request for rework. Please review and complete the work again: {request_obj.title}"
    for a in request_obj.assignments.select_related('personnel').all():
        Notification.objects.create(
            user=a.personnel,
            title=title,
            message=message,
            link=staff_link,
        )


def notify_request_completed(request_obj):
    """Phase 5.4: When Unit Head completes request, notify Requestor and optionally GSO/Director."""
    from django.apps import apps
    from django.conf import settings
    app_label, model_name = settings.AUTH_USER_MODEL.rsplit('.', 1)
    UserModel = apps.get_model(app_label, model_name)
    requestor_link = reverse('gso_requests:requestor_request_detail', args=[request_obj.pk])
    staff_link = reverse('gso_accounts:staff_request_detail', args=[request_obj.pk])
    title = f"Request {request_obj.display_id} completed"
    message = f"Your request has been completed: {request_obj.title}. Please submit your feedback (Client Satisfaction form) for this request."
    Notification.objects.create(
        user_id=request_obj.requestor_id,
        title=title,
        message=message,
        link=requestor_link,
    )
    for u in UserModel.objects.filter(role__in=('GSO_OFFICE', 'DIRECTOR')):
        Notification.objects.create(
            user=u,
            title=title,
            message=f"Request completed: {request_obj.title} — {request_obj.unit.name}",
            link=staff_link,
        )


def notify_oic_assigned(oic_user, director):
    """Phase 8.1: When Director assigns OIC, notify the OIC user."""
    link = reverse('gso_accounts:staff_request_management')
    Notification.objects.create(
        user=oic_user,
        title='You are now Officer-in-Charge (OIC)',
        message=f'You can approve requests on behalf of the Director. Go to Request Management to approve assigned requests.',
        link=link,
    )


def notify_oic_revoked(oic_user, director):
    """Phase 8.1: When Director revokes OIC, notify the former OIC user."""
    link = reverse('gso_accounts:staff_dashboard')
    Notification.objects.create(
        user=oic_user,
        title='OIC designation revoked',
        message='You no longer have approval authority. Only the Director can approve requests now.',
        link=link,
    )


def notify_requestor_edited_request(request_obj):
    """When requestor edits their request (after submit), notify Unit Head for this unit, GSO, Director."""
    from django.apps import apps
    from django.conf import settings
    app_label, model_name = settings.AUTH_USER_MODEL.rsplit('.', 1)
    UserModel = apps.get_model(app_label, model_name)
    staff_link = reverse('gso_accounts:staff_request_detail', args=[request_obj.pk])
    title = f"Request {request_obj.display_id} updated by requestor"
    message = f"{request_obj.title} — requestor made changes. Please review if needed."
    for u in UserModel.objects.filter(role='UNIT_HEAD', unit_id=request_obj.unit_id):
        Notification.objects.create(user=u, title=title, message=message, link=staff_link)
    for u in UserModel.objects.filter(role__in=('GSO_OFFICE', 'DIRECTOR')):
        Notification.objects.create(user=u, title=title, message=message, link=staff_link)


def notify_requestor_cancelled_request(request_obj):
    """When requestor cancels their request, notify Unit Head, GSO Office, Director."""
    from django.apps import apps
    from django.conf import settings
    app_label, model_name = settings.AUTH_USER_MODEL.rsplit('.', 1)
    UserModel = apps.get_model(app_label, model_name)
    staff_link = reverse('gso_accounts:staff_request_detail', args=[request_obj.pk])
    title = f"Request {request_obj.display_id} cancelled by requestor"
    message = f"{request_obj.title} — requestor cancelled this request."
    unit_heads = UserModel.objects.filter(role='UNIT_HEAD', unit_id=request_obj.unit_id)
    for u in unit_heads:
        Notification.objects.create(user=u, title=title, message=message, link=staff_link)
    for u in UserModel.objects.filter(role__in=('GSO_OFFICE', 'DIRECTOR')):
        Notification.objects.create(user=u, title=title, message=message, link=staff_link)


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
    message = f"{request_obj.title} — {request_obj.unit.name}"

    if target == 'director':
        # Director and OIC: request pending approval (status ASSIGNED)
        users = UserModel.objects.filter(
            Q(role='DIRECTOR') | Q(oic_for_director__isnull=False)
        ).distinct()
        msg = f"Request {request_obj.display_id} is waiting for your approval. Please review and approve so personnel can start work."
        for u in users:
            Notification.objects.create(user=u, title=title, message=msg, link=staff_link)

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
            Notification.objects.create(user=u, title=title, message=msg, link=staff_link)

    elif target == 'personnel':
        # Assigned personnel
        for a in request_obj.assignments.select_related('personnel').all():
            msg = f"Reminder: Request {request_obj.display_id} is assigned to you and needs your attention. Please start or continue work."
            Notification.objects.create(
                user=a.personnel,
                title=title,
                message=msg,
                link=staff_link,
            )


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
        Notification.objects.create(user=u, title=title, message=message, link=staff_link)


def notify_material_request_approved(material_request):
    """Notify requesting personnel when Unit Head approves a material request."""
    req = material_request.request
    staff_link = reverse('gso_accounts:staff_request_detail', args=[req.pk])
    Notification.objects.create(
        user=material_request.requested_by,
        title=f"Material request approved — {req.display_id}",
        message=f'Your material request for "{material_request.item.name}" was approved.',
        link=staff_link,
    )


def notify_material_request_rejected(material_request):
    """Notify requesting personnel when Unit Head rejects a material request."""
    req = material_request.request
    staff_link = reverse('gso_accounts:staff_request_detail', args=[req.pk])
    Notification.objects.create(
        user=material_request.requested_by,
        title=f"Material request rejected — {req.display_id}",
        message=f'Your material request for "{material_request.item.name}" was rejected.',
        link=staff_link,
    )
