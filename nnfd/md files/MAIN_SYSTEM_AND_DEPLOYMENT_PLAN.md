# GSO Main System — Finish, Deploy & Scale Plan

**Purpose:** Finish the main (Django/web) system so it is ready for real use at your school, then plan deployment, AI features, data migration, database, and backup/rollback. Flutter is deferred until the main system is complete.

---

## How I Understand Your Goals

1. **Main system first** — All workflows, notifications, and reports must work and feel “done” on the web before focusing on the mobile app.
2. **Auto-updating** — When something happens (e.g. new request from mobile or another user), the web UI (notifications, dashboard, request list) should update without manual refresh. **Web main system: done** (see Part 1.1).
3. **Notifications** — Reliable and polished (who gets notified, when, and that they see it on the web).
4. **Deployment** — A clear, realistic way to deploy so the school can use it (and you can add AI later).
5. **AI** — You want AI for **WAR and IPMT only** (not for request descriptions):
   - **WAR description generation** — Generate or improve the text for Work Accomplishment Reports (summary, accomplishments).
   - **Summarization** — Summarize long text in WAR or IPMT context (e.g. WAR accomplishments, long narrative into a short summary).
   - **IPMT** — (a) Generate or improve the **description/sentence** for each success indicator (what the person did for that indicator); (b) possibly **map** which success indicators fit a person’s work; (c) possibly **suggest or build** an IPMT for a person based on their work that month (so the system “studies” what they did and proposes the right indicators + descriptions).
6. **Data migration** — Bring existing data into the system:
   - **Excel** — Import from Excel files (users, units, requests, inventory, success indicators, etc.) into the right tables.
   - **Paper** — Ideally: **scan a paper form** and have the system (e.g. OCR + parsing) put the data into the right place in the DB (semi-automated data entry).
7. **Database** — Choose a database that is **free** (or very low cost) and **suitable for production** and future AI.
8. **Backup & rollback** — Backups that work for your chosen database, plus a clear **rollback** process if something goes wrong.

---

## Part 1 — Main System: What’s Left to “Finish”

### 1.1 Auto-updating — **complete (web main system)**

| Area | Status | Notes |
|------|--------|--------|
| Staff request list (Request Management page) | Done | Polling every 15s; `credentials: 'same-origin'`; **“Last updated” + spinner** on refresh/filter. |
| Dashboard “Pending Requests Overview” | Done | Polling every 15s; partial endpoint `/accounts/staff/dashboard/pending-requests/`; **“Last updated” + spinner**. |
| Notifications (bell + dropdown, staff & requestor) | Done | Polling every 15s from `/api/v1/notifications/` and `/api/v1/notifications/unread_count/`. |
| Flutter notifications | Deferred | Flutter app; align after main system is stable. |

**Polish (done):** Request Management and Unit Head dashboard show **“Auto-refreshes every 15s. Last updated: …”** with a short spinner while a refresh is in flight, so users see that the list is live.

### 1.2 Notifications polish — **complete (audited + API parity fix)**

**Accuracy audit (web + API where applicable):**

| Action | Notification helper(s) | Who is notified |
|--------|------------------------|-----------------|
| Request submitted (web/API) | `notify_request_submitted` | Requestor, unit head(s), GSO, director |
| Request edited by requestor | `notify_requestor_edited_request` | Unit head(s), GSO, director |
| Request cancelled by requestor | `notify_requestor_cancelled_request` | Unit head(s), GSO, director |
| Personnel assigned | `notify_personnel_assigned` | Assigned personnel, GSO, director |
| Director/OIC approves | `notify_director_approved` | Requestor, assigned personnel, unit head(s) |
| Personnel work status change | `notify_after_personnel_work_status_change` | See below (unified web + API) |
| → Done working | `notify_done_working` | Unit head(s), requestor |
| → In progress (from Approved) | `notify_requestor_work_started` | Requestor |
| → In progress (from On hold) | `notify_requestor_work_resumed` | Requestor |
| → On hold | `notify_requestor_work_on_hold` | Requestor |
| Unit head completes request | `notify_request_completed` | Requestor, GSO, director |
| Return for rework | `notify_returned_for_rework` | Assigned personnel |
| GSO reminder | `notify_gso_reminder` | Director/OIC, unit head, or personnel (by target) |
| OIC assigned / revoked | `notify_oic_assigned`, `notify_oic_revoked` | OIC user |

**Fix applied:** Personnel status updates from the **REST API** (`POST /api/v1/requests/{id}/status/`) previously only fired `notify_done_working` for “Done working.” They now use the same helper as the web form: `notify_after_personnel_work_status_change` in `apps/gso_notifications/utils.py`, so requestors also get **work started / resumed / on hold** notifications when personnel use the mobile app.

**Delivery** — In-app notifications use polling on the web (§1.1). Optional email digest remains a future enhancement.

**Mark as read** — Web and API (`mark_read`, `mark_all_read`) are implemented.

**Duplicates** — Notifications are created once per action; avoid double-submit in the UI. Full idempotency (dedupe by event key) is optional for later.

### 1.3 Production readiness — **implemented in code**

| Item | What we did |
|------|-------------|
| **DEBUG** | Env `DEBUG` (default `True` for local). Production: set `DEBUG=False`. |
| **SECRET_KEY** | Env `DJANGO_SECRET_KEY`. If `DEBUG=False`, Django **refuses to start** unless `DJANGO_SECRET_KEY` is set and not the default `django-insecure-*` prefix. |
| **ALLOWED_HOSTS** | Env `ALLOWED_HOSTS` (comma-separated; entries trimmed). Default includes `localhost`, `127.0.0.1`, `10.0.2.2`. |
| **CSRF_TRUSTED_ORIGINS** | Env `CSRF_TRUSTED_ORIGINS` (comma-separated HTTPS origins), e.g. `https://gso.school.edu`. |
| **CORS** | Extra origins via `CORS_ALLOWED_ORIGINS` env (comma-separated). `CORS_ALLOW_ALL_ORIGINS` only when `DEBUG=True`. |
| **HTTPS / cookies** | When `DEBUG=False`: `SECURE_BROWSER_XSS_FILTER`, `SECURE_CONTENT_TYPE_NOSNIFF`, `X_FRAME_OPTIONS=DENY`. If `USE_TLS_BEHIND_PROXY=True`: `SECURE_PROXY_SSL_HEADER`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`. |
| **Logging** | `LOGGING` in `core/settings.py`: console + rotating file `logs/gso.log` (5 MB × 5). `logs/` gitignored. |
| **Reference** | **`.env.example`** lists variables for local vs production. |

**You still do on the server:** HTTPS termination (Nginx/Caddy/platform), `python manage.py collectstatic`, serve `staticfiles/` and `media/`, optional HSTS at the proxy.

**Part 1 (main system finish) is complete.** **Part 2** (PostgreSQL via `DATABASE_URL`) is **wired in** (`core/settings.py`, `dj-database-url`, `psycopg` in `requirements.txt`; see **`.env.example`**). **Part 3** (backup/rollback) is implemented (`gso_backup` + `BACKUP_AND_ROLLBACK.md`).

**Neon (this project):** With **`DATABASE_URL`** set to your Neon URI, **`python manage.py gso_db_check`** should show **Engine: PostgreSQL** and **Connection OK**; **`python manage.py migrate --check`** should report no pending migrations. Seed **units** for the requestor dashboard (`python manage.py create_sample_users` and/or **Admin → Units**). **Next:** deploy the **web app** to a host (Part 4) with the same env vars + HTTPS; keep Neon as the DB or use a separate Neon branch for staging.

### 1.4 Account Management — **implemented / polished**

Director-side Account Management is now modal-based and role-aware:

| Area | Status | Notes |
|------|--------|-------|
| Add user | Done | Opens as popup; role is selected first; fields adapt by role. |
| Edit user | Done | Opens as popup; no page navigation from Account Management. |
| Requestor Office/Department | Done | Requestor accounts require `Office/Department`; one requestor account per office/department. This is separate from the four GSO service units. |
| Password setup | Done | Director-created users do **not** receive a default password. They receive an email invitation to set their own password. |
| OIC assignment | Done | Set OIC uses select popup + final confirmation + success feedback. |
| Account lifecycle | Done | Users can be Active, Suspended, or Deactivated. Suspended/deactivated users are blocked at login. |
| Audit trail | Done | User creation/edit/status changes and OIC actions are logged in Activity Log. |

**Important production dependency:** account invitation emails require working SMTP settings and a correct `GSO_SITE_URL`; otherwise account creation may succeed but the user may not receive the set-password invitation.

---

## Part 2 — Database (PostgreSQL for production) — **configured**

| Option | Cost | Best for | Notes |
|--------|------|----------|--------|
| **PostgreSQL (Supabase free tier)** | Free (with limits) | Production, multi-user, AI later | Paste URI into `DATABASE_URL`; often includes `?sslmode=require`. |
| **PostgreSQL ([Neon](https://neon.tech) free tier)** | Free (limits; no card on free signup) | **DB-only** — our default recommendation | Serverless Postgres; copy **Connection string** → `DATABASE_URL`. See **§2.1 Neon** below. |
| **PostgreSQL (Railway / Render free tier)** | Free or low | Small school usage | Often paired with app hosting on same platform. |
| **SQLite** | Free | Local development | Default when `DATABASE_URL` is unset (`db.sqlite3`). Not ideal for high concurrency production. |

**Already in the codebase:** `DATABASE_URL` → `dj_database_url.parse(...)` with `conn_max_age` and health checks; SQLite fallback for dev.

**You do when going live:**

1. Create a database (Neon — recommended if you only need Postgres — or Supabase, or Postgres bundled with your host).
2. Set **`DATABASE_URL`** on the server to the provider’s **postgresql://** URI (keep `sslmode=require` if the dashboard gives it).
3. Deploy application code, then run **`python manage.py migrate`** (and `collectstatic`, superuser, etc.).
4. **Optional — copy existing dev data:** e.g. `dumpdata` from SQLite → `loaddata` on Postgres for selected apps, or re-enter critical records; test on a staging DB first.

### 2.1 Neon (database only) — **supported; no extra code**

Neon is **PostgreSQL in the cloud**. This project does not need Neon's SDK — only a normal Postgres URL.

**Free tier:** Neon offers a **free** plan with limits (storage, compute hours; see [Neon pricing / free tier](https://neon.tech/docs/introduction/free-tier) for current numbers). Fine for school-scale traffic to start.

**Steps:**

1. Sign up at [https://neon.tech](https://neon.tech) and create a **project** (pick a region close to your app server).
2. In the Neon **Dashboard** → your project → **Connection details**, copy the **connection string** (URI). It usually looks like `postgresql://user:pass@ep-xxxxx.region.aws.neon.tech/neondb?sslmode=require`.
3. Put that value in **`DATABASE_URL`** in your **local** `.env` temporarily to confirm it works, then in **production** env (never commit secrets to Git).
4. **Verify connection:**  
   `python manage.py gso_db_check`  
   You should see `Engine: PostgreSQL`, your Neon host/name, and `Connection OK`. If it fails, fix the URI, network, or Neon project status before migrating.
5. Apply schema:  
   `python manage.py migrate`  
   Optionally: `python manage.py createsuperuser`
6. For **`gso_backup`** / `pg_dump` against Neon, use the same URI (or Neon’s docs for “direct” vs “pooled” host if you split them); install PostgreSQL client tools on the machine running backups.

### 2.2 SQLite now, Neon when deployed (recommended flow)

| Phase | `DATABASE_URL` | Database |
|--------|----------------|----------|
| Daily development | **Unset** | SQLite (`db.sqlite3`) |
| Optional: test Neon from your PC | **Set** to Neon URI | PostgreSQL (Neon) |
| Production server | **Set** to same Neon URI | PostgreSQL (Neon) |

- **Start on SQLite** — no account required; `gso_db_check` still works and shows SQLite.
- **Before or after deploy**, point **`DATABASE_URL`** at Neon, run **`gso_db_check`**, then **`migrate`**. That creates tables on Neon; the app code is identical.
- **Moving existing SQLite data to Neon** (optional): after `migrate` on Neon, use `dumpdata` / `loaddata` for the apps you care about, or re-create users in admin. Test on a throwaway Neon branch/project first if you use Neon branching.

**Local dev:** Keep **`DATABASE_URL` unset** so Django uses SQLite. Remove or comment out `DATABASE_URL` in `.env` when switching back to SQLite-only dev.

### 2.3 Neon — **connection checklist (any machine)**

| Step | Command / action |
|------|------------------|
| URI in env | `DATABASE_URL=postgresql://…` in `.env` (local) or host env (production). Never commit secrets. |
| Test | `python manage.py gso_db_check` → **Connection OK**, host like `*.neon.tech`. |
| Schema | `python manage.py migrate` (and `migrate --check` should exit 0 when up to date). |
| Units for requestors | At least one **`gso_units.Unit`** with **`is_active=True`** or the requestor “Service Selection” grid is empty (`create_sample_users` creates five units, or add via Admin). |
| Users | Create requestors/staff in Account Management. Requestor accounts require **Office/Department**; staff Unit Head/Personnel require a GSO service unit. Neon starts empty after migrate. |

### 2.4 After Neon works locally — **what to do next**

1. **Deploy the Django app** (Part 4): e.g. Railway, Render, Fly, VPS, or school server. Set **`DATABASE_URL`** (same Neon project or a dedicated staging DB), **`DEBUG=False`**, strong **`DJANGO_SECRET_KEY`**, **`ALLOWED_HOSTS`**, **`CSRF_TRUSTED_ORIGINS`**, **`USE_TLS_BEHIND_PROXY`** if behind HTTPS. Run **`migrate`**, **`collectstatic`**, use a production WSGI server (not `runserver`).
2. **HTTPS** at the proxy or platform; point the school domain when ready.
3. **Secrets:** Rotate Neon DB password if it was ever shared; keep `.env` out of Git.
4. **Backups:** Schedule **`gso_backup`** on the server (Part 3); Neon also has provider snapshots.
5. **Product backlog:** Excel import (Part 6), AI for WAR/IPMT (Part 5), Flutter hardening (Part 7–8) — prioritize with the school.

---

## Part 3 — Backup and Rollback — **implemented**

### 3.1 What you have

- **`gso_backup`** (`python manage.py gso_backup`):
  - **SQLite:** copies `db.sqlite3` → `backups/db_YYYYMMDD_HHMMSS.sqlite3`
  - **PostgreSQL:** runs **`pg_dump -Fc`** → `backups/pg_YYYYMMDD_HHMMSS.dump` (needs `pg_dump` on PATH)
  - **Any engine:** JSON export → `backups/data_YYYYMMDD_HHMMSS.json`
  - **Rotation:** After each run, old files are pruned per type — keep the newest **`GSO_BACKUP_KEEP`** files (default **7**, range **5–10** typical); override with **`--keep N`** or env.
- **`BACKUP_AND_ROLLBACK.md`** — Restore steps, scheduling, rotation, off-server archive.

### 3.2 What you do on the server

1. **Schedule** daily: `python manage.py gso_backup` (cron / Task Scheduler). Set **`GSO_BACKUP_KEEP`** (e.g. `10`) in the task environment if you want more rollback points.
2. **Postgres:** Install client tools so `pg_dump` works; or rely on Supabase/Neon automated backups and keep JSON exports from this command as a second layer.
3. **Long-term archive:** Copy `backups/` off-server periodically (rotation only keeps recent **N** files on disk).

### 3.3 Backup roadmap — **now (pre-deploy) vs after go-live**

You can treat this as a **checklist to finish later** when the app is deployed and stable.

| Phase | Situation | What to rely on | What to add when ready |
|--------|-----------|-----------------|-------------------------|
| **A — Now (development)** | Neon is the DB; app not deployed yet. | **Neon** project backups/snapshots (dashboard) + optional manual `python manage.py gso_backup` on your PC. | Nothing mandatory; focus on finishing features. |
| **B — After deploy** | Django runs on a server (or school PC that is always on). | Same Neon DB + **`gso_backup`** on a **scheduled** job (Mon–Fri 5 PM or daily) on that machine, with **`DATABASE_URL`** and **`pg_dump`** on PATH. | Set **`GSO_BACKUP_DIR`**, **`GSO_BACKUP_KEEP`**; see **`BACKUP_AND_ROLLBACK.md`**. |
| **C — Off-site copy (optional)** | You want copies off the server. | — | Sync **`backups/`** to **Google Drive** (Drive app folder + `GSO_BACKUP_DIR` inside it), **OneDrive**, or **`rclone`** to a bucket; do **not** rely on a single laptop that may be off. |

**Summary:** Right now **Neon + your code** are enough for development. **Automated `gso_backup` + schedule + optional cloud folder** are the **post-deploy** steps — mapped here so you can implement them when the system is live and you know which machine runs the job.

---

## Part 4 — Deployment Method (With AI in Mind)

You want to add AI later (WAR/IPMT description generation, summarization). That implies:

- An **AI provider** (e.g. OpenAI API, or free/local model).
- Possibly **background tasks** (e.g. Celery) for long-running or async AI calls so the web request doesn’t time out.
- **Secrets** (API keys) stored in environment, not in code.

Deployment options that work with Django + optional AI:

| Method | Pros | Cons | AI-friendly? |
|--------|------|------|----------------|
| **VPS (e.g. DigitalOcean, Linode)** | Full control, can run Celery, Redis, any DB | You manage OS, Nginx, SSL, backups | Yes |
| **PaaS (Railway, Render, Fly.io)** | Easy deploy from Git; add-ons for DB/Redis | Less control; may need paid tier for workers | Yes (background workers available) |
| **School server (on-prem)** | Free, data stays on-site | You maintain server and updates | Yes if you can run Python + optional Redis/Celery |

**Suggested path for “free or cheap” and AI later:**

1. **Short term:** Deploy Django on **Railway** or **Render** (free tier) with **Supabase** or **Neon** PostgreSQL. Use environment variables for `SECRET_KEY`, `DATABASE_URL`, and later `OPENAI_API_KEY` (or similar). No AI yet — just get the main system live.
2. **When adding AI:** Use the same host; add a **background task queue** (e.g. Celery + Redis, or Django-Q, or a single “AI worker” process) so AI calls don’t block the web request. Keep API keys in env.

**Minimal deploy steps (generic):**

- Push code to Git (e.g. GitHub).
- Connect repo to Railway/Render; set env vars (`DEBUG=False`, `SECRET_KEY`, `DATABASE_URL`, `ALLOWED_HOSTS`).
- Use PostgreSQL from Supabase/Neon; run migrations in deploy command or via CLI.
- Run `collectstatic`; serve static files.
- Configure custom domain and HTTPS (platform usually provides this).

---

## Part 5 — AI Features (Clarified)

AI in this system is for **WAR and IPMT only**. Request description generation is out of scope.

### 5.1 WAR description generation and summarization

- **Where:** WAR create/edit (summary, accomplishments fields).
- **What:** (1) Generate or improve the **accomplishments** or **summary** text from a short input or from context (e.g. request title + assignee). (2) **Summarize** long narrative into a concise summary or accomplishment sentence.
- **How:** Call an AI API (e.g. OpenAI) with a prompt; e.g. “Improve this accomplishment text” or “Summarize this for the WAR” in the WAR form.

### 5.2 IPMT and success indicators

Your intent as I understand it:

- **IPMT** = list of success indicators for a person (and often a period). Each indicator has a “description” or “sentence” saying what that person did for that indicator.
- **AI use cases:**
  1. **Per-indicator description:** When a personnel’s work (e.g. WAR entries, completed requests) is linked to a success indicator, AI **generates the sentence/description** that says “this person did X for indicator Y” (so the IPMT export or form is filled with proper text).
  2. **Mapping:** AI suggests **which success indicators** fit a person’s work in a given month (based on their WARs, requests, etc.).
  3. **Build IPMT from work:** AI “studies” what the person did that month and proposes (or fills) the list of indicators + descriptions for the IPMT report.

**Implementation outline:**

- Add an **AI service** layer (e.g. `apps.gso_ai` or use existing pattern): one module that calls the external AI API with prompts.
- **Prompts:**  
  - “Given this success indicator and this list of work accomplishments (WARs), write one sentence describing what this person did for this indicator.”  
  - “Given this person’s WARs for this month, suggest which success indicators apply and a short description for each.”
- **Where it plugs in:** IPMT report page (staff): “Generate descriptions” button per row or “Fill from WARs” that runs AI and pre-fills descriptions. Optionally: background job that pre-generates and stores text.
- **Data foundation:** Personnel records now carry `position_title` and `employment_status` for IPMT header/profile data. `SuccessIndicator` can also be targeted by GSO unit and/or position, and WAR entries can be tagged to success indicators so IPMT can later be generated from real work data.
- **Data:** Use existing `SuccessIndicator`, `WorkAccomplishmentReport`, and IPMT export (personnel + month). No need to change the IPMT Excel structure initially; AI can fill the “accomplishments” or a new “indicator description” field used in the export.

**Order:** Implement WAR description/summarization first (simpler); then IPMT per-indicator description generation; then mapping/suggestion if needed.

---

## Part 6 — Data Migration

### 6.1 Excel import

- **Goal:** Take Excel files (from school) and import into the right Django models (Users, Units, Requests, Inventory, Success Indicators, maybe WARs).
- **Approach:**
  1. **Define templates** — One (or more) Excel template(s) per entity (e.g. “users.xlsx”, “requests.xlsx”, “inventory.xlsx”, “success_indicators.xlsx”) with clear column names matching your models.
  2. **Management commands or admin actions** — e.g. `python manage.py import_users users.xlsx`, `import_requests requests.xlsx`, etc., using `openpyxl` or `pandas` to read and create/update records. Handle duplicates (e.g. by ID or code) and validation (skip invalid rows, log errors).
  3. **Optional UI** — Staff-only page “Import data” with file upload that runs the same import logic and shows a summary (created/updated/failed).

**Phasing:** Start with one entity (e.g. Users or Success Indicators); then Requests, Inventory, etc., depending on what the school actually has in Excel.

### 6.2 Paper / scan → database

- **Goal:** Scan a paper form and have the system put the data into the right table (e.g. request form, feedback form, personnel form).
- **Challenges:** OCR quality, layout variability, need to map “where on the form” to “which field in the DB”.
- **Approach:**
  1. **OCR** — Use an OCR API or library (e.g. Tesseract, or cloud: Google Vision, Azure Form Recognizer) to get text (and optionally structure) from the scanned image/PDF.
  2. **Structured extraction** — Either fixed layout (e.g. “row 3 = request title”) or a small ML/rule layer that maps detected fields to your model fields. For school use, starting with **fixed templates** (one type of form per document type) is most realistic.
  3. **Review before save** — Don’t auto-insert blindly. Provide a **review screen**: show extracted data in a form, let staff correct it, then “Save” to create/update the record. This avoids bad data from OCR errors.
  4. **Storage** — Store the scanned file in `Media` and optionally link it to the created record (e.g. “Request GSO-2026-0042 – attachment: scan.pdf”).

**Phasing:** Pick one form (e.g. “Request form” or “Feedback form”); define the layout; implement OCR + extraction + review UI for that form. Then replicate for other forms if needed.

---

## Part 7 — Rollout Order (Suggested)

So that the main system is “finished,” deployable, and then extended with AI and migration:

| Order | Focus | Outcome |
|-------|--------|--------|
| **1** | Deploy web app + production env | Neon DB ready (`DATABASE_URL`); deploy Django with `DEBUG=False`, HTTPS, `collectstatic`, domain; not `runserver`. |
| **2** | Backup & rollback | Done: `gso_backup` (SQLite copy + `pg_dump -Fc` + JSON); `BACKUP_AND_ROLLBACK.md`; schedule on server. |
| **3** | Notifications polish | Verify all notification triggers and recipients; optional email. |
| **4** | Account Management smoke test | Verify add/edit users, invite email, requestor office/department, OIC, suspend/deactivate/reactivate, and login blocking. |
| **5** | Data migration – Excel | At least one import path (e.g. users or success indicators) via command or UI. |
| **6** | Data migration – scan/OCR | One form type: upload scan → OCR → review screen → save to DB. |
| **7** | AI – WAR & IPMT description & summarization | AI service + “Generate/improve description” and “Summarize” in WAR form; then IPMT descriptions. |
| **8** | AI – IPMT mapping/suggestions | Optional: suggest indicators or “fill IPMT from work” for a person/month. |
| **9** | Attachment offload (Google Drive) | Pending finalization phase: move request attachments to Drive via service account; keep only file ID/link in DB; keep local media fallback until verified. |
| **10** | Flutter | After main system is stable and deployed; connect to same API. |

---

## Part 8 — Summary Checklist

- **Main system “done” (Part 1):** §1.1 auto-update, §1.2 notifications, §1.3 production settings — **all complete** in code + docs.
- **Account Management:** Modal add/edit users; requestor Office/Department; invite-based password setup; OIC double-confirm; Active/Suspended/Deactivated lifecycle; Activity Log entries.
- **Database:** Neon — use **`DATABASE_URL`**; verify with **`gso_db_check`**; seed **units** so requestors see “Service Selection” (Part 2 §2.3). For SQLite-only local dev, leave `DATABASE_URL` unset.
- **Backup:** Pre-deploy: Neon dashboard + optional manual `gso_backup`. After deploy: schedule + `pg_dump` + optional Drive/sync (Part 3 §3.3, `BACKUP_AND_ROLLBACK.md`).
- **Deploy:** **Next major step** — host Django (Railway/Render/VPS/etc.), same **`DATABASE_URL`** to Neon, production env vars, HTTPS, static files; then schedule backups on the server.
- **Attachments (pending finalization):** Keep current local upload during stabilization. Plan Google Drive offload after edge-case/UAT finalization, with role-based access check and migration of existing files.
- **AI:** WAR & IPMT description generation and summarization only (no request description); then IPMT mapping/suggestions if needed.
- **Data migration:** Excel import (templates + commands/UI); scan/OCR with review UI for at least one form.
- **Order:** Deploy app + HTTPS + backup on server → notifications + Account Management smoke-test → Excel import → scan → AI (WAR → IPMT) → Flutter last.

**Current focus:** Neon is configured; **deploy the web application** (Part 4) so users reach the system on a real URL. After that: **Excel import** (Part 6), **AI** (Part 5), **Flutter** polish — as the school prioritizes.

