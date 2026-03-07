# Phase 5 completion checklist

All Phase 5 items from the plan are implemented.

## 5.1 Work status and "Done working"
- **Personnel** can set work status: **In Progress**, **On Hold**, **Done working** (from Director Approved or from On Hold).
- **Done working** sets request status to `DONE_WORKING` so the Unit Head sees it for review.
- **ON_HOLD** status added to `Request.Status`.
- **UpdateWorkStatusView** enforces valid transitions and notifies Unit Head when status is Done working.
- Request detail shows **Work status** section with the correct buttons when the user is assigned personnel.

## 5.2 Chat / activity feed
- **RequestMessage** model: `request`, `user`, `message`, `created_at`.
- **Personnel, Unit Head, GSO Office, Director** can post messages on a request (staff only; Unit Head/Personnel restricted to same unit).
- **AddRequestMessageView** and **RequestMessageForm**.
- Request detail shows **Activity / Chat**: list of messages and a form to post. Shown to all staff who can access the request.

## 5.3 Unit Head completion
- Unit Head sees requests in **Request Management** where status is **Done working** (same unit).
- **Complete request** button in request detail when `can_complete` (Unit Head, same unit, status Done working) → sets status **Completed**.
- **Return for rework** button: Unit Head can send work back to personnel (status → In Progress); assigned personnel are notified.

## 5.4 Notifications
- **notify_done_working(request_obj)**: notifies Unit Head(s) of the request’s unit when personnel mark Done working.
- **notify_request_completed(request_obj)**: notifies Requestor; notifies GSO Office and Director.
- **notify_returned_for_rework(request_obj)**: notifies assigned personnel when Unit Head returns for rework.

## Additional (Personnel task lists)
- **PersonnelTaskListView** (Task Management): requests assigned to the current user with status Director Approved, In Progress, On Hold, or Done working.
- **PersonnelTaskHistoryView** (Task History): completed requests (assigned to the current user, status Completed).
- Request detail **Back** link: Personnel → Task Management; others → Request Management.

## Deliverables (plan)
- Personnel can work, update status, and chat.  
- Unit Head can complete requests (and return for rework).  
- Clear status flow: Director Approved → In Progress / On Hold → Done working → Completed (or back to In Progress if returned).

**Phase 5 is complete.**
