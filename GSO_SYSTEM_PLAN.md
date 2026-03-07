# GSO (General Services Office) System — Implementation Plan

**Stack:** Django (backend + built-in templates), **SQLite** (default; optional Supabase/PostgreSQL via `DATABASE_URL`)  
**Purpose:** Request workflow, approvals, personnel assignment, **unit-based inventory**, Work Accomplishment Reports (WAR), IPMT reports, feedback, and system safety (backup, rollback, notifications).

---

## Progress & Status

**All phases complete.** The system is ready for final testing and deployment.

| Phase | Status   | Notes |
|-------|----------|--------|
| **1** | ✅ Done  | Project setup, auth & roles, base UI (requestor + staff), **5 units in DB** (Repair & Maintenance, Utility, Electrical, Motorpool, Security). |
| **2** | ✅ Done  | Request model (2.1), shared form for all units (2.2), submission flow + notifications on submit (2.3), **list/detail by role** (2.4): Requestor = my requests; Unit Head/Personnel = their unit; GSO/Director = all + unit filter; detail view shows status and request data. |
| **3** | ✅ Done  | Inventory (3.1–3.4): Unit Head own unit (CRUD/adjust); GSO/Director all + unit filter; Personnel view-only for their unit. |
| **4** | ✅ Done  | Assignment & approval (Unit Head assigns, Director/OIC approves); OIC assign/revoke; in-app notifications on submit, assign, approve. |
| **5** | ✅ Done  | Personnel work status (In Progress, On Hold, Done working), chat/messages, Unit Head complete & return-for-rework; notifications. |
| **6** | ✅ Done  | WAR model + create-from-request, success indicators (M2M), IPMT report (Excel), WAR export (Excel); Work Reports landing. |
| **7** | ✅ Done  | Requestor-only CSM feedback (popup) for completed requests; Director/GSO Feedback Reports (view + Excel); Director/GSO same UI; Approve only for Director/OIC. |
| **8** | ✅ Done  | In-app notifications on all key events (including OIC assign/revoke); notification center (list, mark read, link); version endpoint + “New version available” prompt. |
| **9** | ✅ Done  | Backup: `gso_backup` command (SQLite copy + JSON export); rollback & security doc; audit log (Director approve, OIC assign/revoke). |

---

## Roles Summary

| Role | Main actions |
|------|----------------|
| **Requestor** | Create requests (by unit), fill unit-specific forms |
| **Unit Head** | Receive requests, assign Personnel, approve/complete work after Personnel marks done; **manage own unit's inventory** |
| **Personnel** | Receive assigned work after Director approval, update status, chat, mark “Done working” |
| **GSO Office** | Notify parties, same UI as Director, generate reports; cannot approve; **manage/view all inventory (filter by unit)** |
| **Director** | Approve requests (start work), assign OIC from GSO Office when away, generate reports; **manage/view all inventory (filter by unit)** |

---

## Phase 1: Foundation & Setup

**Goal:** Project skeleton, database, auth, and base UI.

1. **1.1 Project setup**
   - Django project and apps structure (e.g. `core`, `apps.gso_accounts`, `apps.gso_requests`, `apps.gso_units`, `apps.gso_inventory`, `apps.gso_reports`, `apps.gso_notifications`). Develop with SQLite; ready to switch to PostgreSQL via `DATABASE_URL`.
   - Python env, `requirements.txt`, `.env` for secrets.
   - Connect Django to **Supabase** (use Supabase’s PostgreSQL connection string; Django uses it as the default DB).

2. **1.2 Authentication & roles**
   - Custom user model (or extend AbstractUser) with role: Requestor, Unit Head, Personnel, GSO Office, Director.
   - Optional: link users to **Unit** (for Unit Heads/Personnel: Repair & Maintenance, Utility, Electrical, Motorpool, Security).
   - Login/logout, password reset (email if you have SMTP).
   - Role-based redirect after login (dashboard per role).

3. **1.3 Base UI (Django templates)**
   - Base template (navbar, sidebar, footer), CSS/JS assets.
   - Dashboard placeholders per role.
   - “Same UI for GSO Office and Director” with permission checks hiding/blocking “Approve” for GSO Office.

4. **1.4 Units and request types**
   - Master data: **5 units in DB** — Repair & Maintenance, Utility, Electrical, Motorpool, Security (`Unit` model, seeded).
   - Define “request type” or “form type” per unit (metadata only in this phase; forms in Phase 2).

**Deliverables:** App runs locally, login by role, Supabase (or SQLite) connected, base templates and dashboards. **Phase 1 complete.**

---

## Phase 2: Request Creation & Unit-Specific Forms

**Goal:** Requestors can submit requests per unit with the correct form.

1. **2.1 Request model**
   - Core fields: requestor, unit, title/description, status (e.g. Draft, Submitted, Assigned, Director Approved, In Progress, Done, Unit Head Completed, etc.), timestamps, optional priority.

2. **2.2 Unit-specific form definitions**
   - Per unit, define which fields the request form has (e.g. JSON schema or Django model with optional fields; or separate “detail” models per unit).
   - Forms: Repair & Maintenance, Utility, Electrical, Motorpool, Security — each with its own template and form class.

3. **2.3 Request submission flow**
   - Requestor selects unit → form loads → submit.
   - Status: e.g. “Submitted”; notify Unit Head, GSO Office, Director (Phase 4 can add real notifications).

4. **2.4 Request list and detail views**
   - List views filtered by role (Requestor: my requests; Unit Head: for my unit; GSO/Director: all or by unit).
   - Detail view shows unit-specific data and current status.

**Deliverables:** Requestor can create requests per unit with correct forms; others can see requests in lists/detail. **Phase 2.4 complete.**

---

## Phase 3: Inventory (Unit-Based)

**Goal:** Unit Heads manage their unit’s inventory; GSO Office and Director manage/view all inventory with optional unit filter.

1. **3.1 Inventory model**
   - Items tied to a **Unit** (Repair & Maintenance, Utility, Electrical, Motorpool, Security).
   - Fields: unit (FK), name/description, category or type, quantity, unit of measure (e.g. pcs, box), reorder level, location/remarks, optional serial/asset number; created/updated by and timestamps.
   - Optional: `InventoryTransaction` or stock movement log (in/out, request link if issued for a job).

2. **3.2 Unit Head — own unit only**
   - Unit Head sees only inventory for **their** unit (filter by `user.unit` or equivalent).
   - CRUD on items in their unit: add, edit, delete, adjust quantity (in/out).
   - List and detail views; simple search/filter by name or category within the unit.

3. **3.3 GSO Office & Director — all inventory, filter by unit**
   - Same inventory list/detail UI as Unit Head but **no unit restriction**: show all units’ inventory.
   - **Filter by unit** (dropdown or tabs): All, Repair & Maintenance, Utility, Electrical, Motorpool, Security.
   - Both can create/edit/delete items for any unit and adjust quantities (full management).
   - Optional: GSO Office “view only” and Director “manage” if you need that split later; for now both can manage all.

4. **3.4 Permissions and UX**
   - Unit Head: `queryset.filter(unit=request.user.unit)` (or equivalent) on all inventory views.
   - GSO Office / Director: no unit filter on queryset; unit filter is a user-selected filter for display only.
   - Shared templates where possible; branch only on “can see all units” vs “see only my unit”.

**Deliverables:** Unit Head manages own unit inventory; GSO Office and Director manage all inventory with unit filter; consistent list/detail and CRUD.

---

## Phase 4: Assignment & Approval Workflow

**Goal:** Unit Head assigns personnel; Director approves; Personnel can start only after approval.

1. **4.1 Personnel assignment**
   - Unit Head can assign one (or more) Personnel to a request.
   - Store assignment (e.g. `RequestAssignment`: request, personnel, assigned_by, assigned_at).
   - Status progression: e.g. “Assigned” (waiting Director approval).

2. **4.2 Director approval**
   - Director (or OIC when set) is the only one who can “Approve” the request for work to start.
   - Status: e.g. “Director Approved” or “Ready for work”.
   - GSO Office sees same screen but “Approve” button hidden or disabled.

3. **4.3 OIC (Officer-in-Charge)**
   - Director can assign a GSO Office user as OIC (e.g. `User.oic_for_director` or a small OIC table with date range).
   - When OIC is set, that user can perform Director approvals until OIC is revoked.

4. **4.4 Notifications (basic)**
   - When request is submitted: notify Unit Head, GSO Office, Director.
   - When assigned: notify Personnel (and optionally Director/GSO).
   - When Director approves: notify assigned Personnel and Unit Head.
   - Use Django messages or a simple in-app notification model (mark as read later).

**Deliverables:** Full path: Submit → Assign (Unit Head) → Approve (Director/OIC) → visible to Personnel as “ready to start”.

---

## Phase 5: Personnel Work Execution & Completion

**Goal:** Personnel do the work, update status, chat; Unit Head marks request complete.

1. **5.1 Work status and “Done working”**
   - Personnel can set work status (e.g. In Progress, On Hold, Done working).
   - “Done working” changes request status so Unit Head sees it for review.

2. **5.2 Chat / activity feed**
   - Per-request thread: Personnel, Unit Head, GSO, Director can post messages (simple model: request, user, message, created_at).
   - Show in request detail; optional real-time later (e.g. polling or WebSocket).

3. **5.3 Unit Head completion**
   - Unit Head sees requests where Personnel marked “Done working”.
   - Unit Head can “Approve/Complete” after checking → request status “Completed”.

4. **5.4 Notifications**
   - Notify when Personnel mark “Done working” (to Unit Head); when Unit Head completes (to Requestor, optional GSO/Director).

**Deliverables:** Personnel can work, update status, chat; Unit Head can complete requests; clear status flow.

---

## Phase 6: Work Accomplishment Report (WAR) & IPMT

**Goal:** Every completed request has a WAR; personnel WARs feed IPMT report.

1. **6.1 Work Accomplishment Report (WAR)**
   - WAR model: linked to Request and to Personnel (who did the work), plus date range, summary, accomplishments text, etc.
   - One request → one WAR (or one per personnel if multiple assigned); tie clearly to “who did it”.

2. **6.2 Success indicators**
   - Master data: Success indicators + descriptions (e.g. model or table).
   - Link or tag WAR entries (or request types) to success indicators so “what was done” can align with indicators.

3. **6.3 IPMT report generation**
   - Per personnel, per period (e.g. month): list WARs / work done; match to success indicators.
   - “Generate IPMT” view: select personnel (or current user), period; build dataset aligned to success indicators.
   - Export to Excel (openpyxl or xlsxwriter).

4. **6.4 WAR export**
   - Export WAR (per request or per personnel/period) to Excel for reporting.

**Deliverables:** WAR per completed request/personnel; IPMT and WAR Excel exports; success-indicator alignment.

---

## Phase 7: Feedback, Reports UI & Director/GSO Parity

**Goal:** Feedback on requests; Director and GSO Office share UI; only Director (or OIC) approves.

1. **7.1 Feedback**
   - **Implemented:** Requestor-only CSM (Client Satisfaction Measurement) feedback for completed requests: Part I (CC1–CC3), Part II (SQD1–SQD9), suggestions, email. Popup form; one submission per request. Director/GSO view and download feedback via Work Reports → Feedback Reports.

2. **7.2 Director / GSO Office UI**
   - Same templates and views for both; use permission checks:
     - “Approve” button only for Director (or OIC).
   - Both can generate WAR and IPMT reports (filters by unit, personnel, date).

3. **7.3 Report generation and Excel**
   - Central place (e.g. “Reports” menu) to generate:
     - WAR Excel (by request, personnel, or date range).
     - IPMT Excel (by personnel and month, with success indicators).
   - Auto-notification (Phase 8) can optionally “notify when report is generated” or scheduled.

**Deliverables:** Feedback on requests; single UI for Director/GSO with correct permissions; report generation and Excel downloads.

---

## Phase 8: Auto-Notification & Auto-Update

**Goal:** Proactive notifications and optional auto-update mechanism.

1. **8.1 Auto-notification**
   - **Implemented:** In-app notifications on: new request, assignment, Director approval, “Done working”, Unit Head completion, OIC assigned/revoked. Celery deferred until after system finalization (optional later).

2. **8.2 In-app notification center**
   - List of notifications per user, mark as read, link to relevant request/report.

3. **8.3 Auto-update (application)**
   - **Implemented:** Option A — `/accounts/version/` returns app version; staff and requestor layouts check periodically and show “A new version is available. Please refresh.” banner when version changes. Set `GSO_APP_VERSION` (env) on deploy.

**Deliverables:** Notifications on key events; notification center; simple “new version available” prompt if desired.

---

## Phase 9: Backup, Rollback & Security

**Goal:** Data safety and ability to roll back.

**Current setup: SQLite** (`db.sqlite3`). If you switch to Supabase/PostgreSQL later, use the provider’s backup/restore; see `docs/PHASE9_BACKUP_ROLLBACK_SECURITY.md`.

1. **9.1 Backup**
   - **Implemented:** Management command `python manage.py gso_backup` — copies SQLite file to `backups/db_YYYYMMDD_HHMMSS.sqlite3` and exports critical data (users, requests, feedback, WAR, inventory) to `backups/data_YYYYMMDD_HHMMSS.json`. Options: `--db-only`, `--json-only`. Set `GSO_BACKUP_DIR` (env) for custom backup folder. Schedule via cron or Task Scheduler.

2. **9.2 Rollback**
   - **Documented:** In `docs/PHASE9_BACKUP_ROLLBACK_SECURITY.md` — SQLite restore (stop app, replace `db.sqlite3` with backup file, start app); application rollback via Git + migration rollback steps.

3. **9.3 Security**
   - **Implemented:** Audit log (AuditLog model) for Director approve, OIC assign, OIC revoke; viewable in Django Admin. Security checklist in doc: HTTPS, `SECRET_KEY`/`DEBUG`/`ALLOWED_HOSTS` from env, `pip audit`/`safety check`.

**Deliverables:** Backup command and doc; rollback procedure; audit log and security checklist.

---

## Suggested Order of Work (Approach)

1. **Phase 1** ✅ — Foundation (auth, DB, base UI, 5 units in DB). **Done.**
2. **Phase 2** ✅ — Request creation, unit-specific forms, list/detail by role. **Done.**
3. **Phase 3** ✅ — Inventory (unit-based): Unit Head own unit; GSO/Director all + filter. **Done.**
4. **Phase 4** ✅ — Assignment and Director approval (Unit Head assigns, Director/OIC approves). **Done.**
5. **Phase 5** ✅ — Personnel execution and Unit Head completion; core workflow done. **Done.**
6. **Phase 6** ✅ — WAR and IPMT (reports depend on completed requests). **Done.**
7. **Phase 7** ✅ — Feedback and report UI polish; Director/GSO same UI. **Done.**
8. **Phase 8** ✅ — Auto-notifications and optional auto-update. **Done.**
9. **Phase 9** ✅ — Backup, rollback, and security hardening. **Done.**

**All phases complete.** Proceed with final testing, then deployment. Optional later: Celery for async notifications; Supabase/PostgreSQL when scaling.

---

## Database: SQLite (current) & optional Supabase/PostgreSQL

- **Current:** The system runs on **SQLite** (`db.sqlite3`) by default. Backup, rollback, and Phase 9 docs are written for SQLite.
- **Optional — Supabase/PostgreSQL:** Set `DATABASE_URL` in `.env` to a PostgreSQL connection string (e.g. Supabase “Connection string” from Settings → Database). Install `dj-database-url` and `psycopg[binary]`; run `python manage.py migrate`. Use the provider’s backup/restore for the database; `gso_backup --json-only` still works for data export.
- Migrations: run `python manage.py migrate` as usual; switching DB is config-only.

---

## Summary Table

| Phase | Focus | Outcome | Status |
|-------|--------|--------|--------|
| 1 | Foundation & setup | Django + SQLite (or PostgreSQL via DATABASE_URL), auth, roles, base UI, **5 units in DB** | ✅ Done |
| 2 | Requests & forms | Unit-specific forms, request CRUD, list/detail by role | ✅ Done |
| 3 | Inventory (unit-based) | Unit Head: own unit only; GSO Office/Director: all inventory, filter by unit; Personnel view-only | ✅ Done |
| 4 | Assignment & approval | Unit Head assigns, Director/OIC approves, notifications | ✅ Done |
| 5 | Work execution | Personnel status, chat, Unit Head complete & return-for-rework, notifications | ✅ Done |
| 6 | WAR & IPMT | WAR model, success indicators, IPMT & WAR Excel, Work Reports landing | ✅ Done |
| 7 | Feedback & reports UI | Requestor CSM feedback (popup), Feedback Reports for Director/GSO, same UI, report generation | ✅ Done |
| 8 | Notifications & update | In-app notifications (all events + OIC), notification center, version endpoint + refresh prompt | ✅ Done |
| 9 | Backup & rollback | `gso_backup` command (SQLite + JSON), rollback doc, audit log, security checklist | ✅ Done |

**All phases complete.** The GSO system is ready for final testing and deployment. See `docs/PHASE9_BACKUP_ROLLBACK_SECURITY.md` for backup, rollback, and security; use `python manage.py gso_backup` for backups when using SQLite.
