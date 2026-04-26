# System Improvement Audit

This document is now a working action tracker. Update each item's status as work progresses.

## Status legend

- `TODO`: not started
- `IN PROGRESS`: currently being worked on
- `BLOCKED`: cannot proceed due to dependency/decision
- `DONE`: completed and verified

## Action tracker

### 1) Secrets management and rotation

- **Priority:** P0
- **Owner:** DevOps + Project Lead
- **Status:** IN PROGRESS
- **Files/systems:** `.env`, hosting secret manager, email/OAuth/API provider dashboards
- **Why:** Sensitive credentials are stored in local env and may be exposed if leaked or committed.
- **Implementation steps:**
  1. Create new credentials for database, email, OAuth, and API providers.
  2. Revoke/rotate old credentials immediately after cutover.
  3. Move production secrets to platform-managed secret storage.
  4. Keep `.env` for local development only and verify it is git-ignored.
  5. Add secret scanning in CI/pre-commit.
- **Done criteria:**
  - All production credentials rotated and old keys revoked.
  - No active sensitive values in tracked files.
  - Deploy pipeline reads secrets from secure secret store.
- **Risk if skipped:** High chance of account or data compromise.

### 2) Production security defaults hardening

- **Priority:** P0
- **Owner:** Backend
- **Status:** DONE
- **Files/systems:** `core/settings.py`
- **Why:** Safety posture depends on environment hygiene and can fail open.
- **Implementation steps:**
  1. Default `DEBUG` to `False`.
  2. Set strict `ALLOWED_HOSTS` from env.
  3. Ensure production-only security flags are enabled (`SECURE_SSL_REDIRECT`, HSTS, secure cookies).
  4. Lock down CORS to explicit trusted origins.
  5. Validate settings in staging before production release.
- **Done criteria:**
  - Production runs with `DEBUG=False`.
  - CORS and hosts are explicit allowlists.
  - HTTPS-related security flags active in production.
- **Risk if skipped:** Increased attack surface and accidental insecure deployment.

### 3) Safe redirect handling

- **Priority:** P1
- **Owner:** Backend
- **Status:** DONE
- **Files/systems:** `apps/gso_accounts/views.py`
- **Why:** Redirect targets from user-controlled or dynamic sources may enable phishing/open redirect abuse.
- **Implementation steps:**
  1. Identify all redirect targets derived from links, query params, and referer.
  2. Validate with Django safe URL checks (`url_has_allowed_host_and_scheme`).
  3. Use internal fallback routes when target is unsafe.
  4. Add tests for safe/unsafe redirect cases.
- **Done criteria:**
  - Unsafe external redirect inputs are rejected.
  - All tested redirect endpoints have safe fallback behavior.
- **Risk if skipped:** Open redirect abuse, phishing and trust issues.

### 4) Enforce proper HTTP semantics for state changes

- **Priority:** P1
- **Owner:** Backend
- **Status:** DONE
- **Files/systems:** `apps/gso_accounts/views.py`, related templates/forms
- **Why:** GET-triggered state changes break web safety assumptions and can bypass expected protections.
- **Implementation steps:**
  1. Locate mutation actions callable through GET.
  2. Convert to POST-only handlers.
  3. Update templates/UI actions to submit CSRF-protected forms.
  4. Add tests confirming GET does not mutate state.
- **Done criteria:**
  - Mutating endpoints reject GET.
  - UI still functions using POST actions.
- **Risk if skipped:** Unintended state changes, CSRF/caching-related issues.

### 5) Exception handling and observability cleanup

- **Priority:** P1
- **Owner:** Backend
- **Status:** DONE
- **Files/systems:** `apps/gso_reports/models.py`, `apps/gso_reports/excel_export.py`, `apps/gso_accounts/context_processors.py`, related views
- **Why:** Broad catches and silent failure paths hide defects and complicate debugging.
- **Implementation steps:**
  1. Replace broad `except Exception` where possible with specific exceptions.
  2. Remove silent `pass` in critical code paths.
  3. Add structured logs (operation, request/user context, error type).
  4. Keep user-facing responses friendly while preserving internal diagnostics.
- **Done criteria:**
  - Critical paths log meaningful errors.
  - Fewer/no silent exception blocks in high-risk modules.
- **Risk if skipped:** Hidden failures, slower incident response.

### 6) Server-side upload validation

- **Priority:** P1
- **Owner:** Backend
- **Status:** DONE
- **Files/systems:** `apps/gso_requests/forms.py`, `apps/gso_requests/models.py`, upload endpoints
- **Why:** Client-side `accept` attributes are not security controls.
- **Implementation steps:**
  1. Add server validators for extension/MIME and file size.
  2. Define clear allowed file list and max file size policy.
  3. Ensure storage and serving rules prevent dangerous execution.
  4. Add tests for rejected invalid uploads.
- **Done criteria:**
  - Unsupported/oversized files are rejected server-side.
  - Allowed files upload and render correctly.
- **Risk if skipped:** Malicious upload and resource exhaustion risk.

### 7) API error response sanitization

- **Priority:** P2
- **Owner:** Backend
- **Status:** DONE
- **Files/systems:** `apps/gso_reports/views.py`, other API views
- **Why:** Returning raw exception strings leaks internals.
- **Implementation steps:**
  1. Replace raw exception text in API responses with generic messages.
  2. Log technical details server-side with trace/context.
  3. Standardize API error shape for consistency.
- **Done criteria:**
  - API responses do not reveal stack/internal service details.
  - Logs still contain actionable diagnostics.
- **Risk if skipped:** Information disclosure and inconsistent client experience.

### 8) Query optimization for dashboard/report pages

- **Priority:** P2
- **Owner:** Backend
- **Status:** DONE
- **Files/systems:** `apps/gso_accounts/views.py`, dashboard-related query code
- **Why:** Repeated per-loop count queries will degrade with data growth.
- **Implementation steps:**
  1. Profile key dashboard requests (query count + latency).
  2. Replace repeated `.count()` patterns with grouped aggregate queries.
  3. Use `select_related`/`prefetch_related` where needed.
  4. Re-measure and compare performance.
- **Done criteria:**
  - Lower query count on target pages.
  - Improved response time under realistic data volume.
- **Risk if skipped:** Slow dashboards and poor user experience at scale.

### 9) DRF throttling and abuse protection

- **Priority:** P2
- **Owner:** Backend
- **Status:** DONE
- **Files/systems:** `core/settings.py`, DRF views/viewsets
- **Why:** Missing throttles increase risk of brute-force and abusive request bursts.
- **Implementation steps:**
  1. Enable baseline `AnonRateThrottle` and `UserRateThrottle`.
  2. Add scoped throttles for sensitive endpoints (auth, OTP, notifications).
  3. Tune rates with staging load tests.
  4. Document expected behavior for clients.
- **Done criteria:**
  - Throttles active and tested on sensitive endpoints.
  - Clear error responses for throttle limits.
- **Risk if skipped:** Higher abuse/DoS risk and unstable API behavior.

### 10) Automated test coverage for critical flows

- **Priority:** P1
- **Owner:** QA + Backend
- **Status:** DONE
- **Files/systems:** app test modules (`apps/*/tests/`)
- **Why:** Core workflows are at risk of regressions without automated safety checks.
- **Implementation steps:**
  1. Add baseline test structure per app if missing.
  2. Prioritize tests for role permissions, request lifecycle, OTP/reset, exports, and notifications.
  3. Add API contract tests for key endpoints.
  4. Enforce tests in CI before merge.
- **Done criteria:**
  - High-risk flows covered by repeatable automated tests.
  - CI blocks merges when critical tests fail.
- **Risk if skipped:** Frequent regressions and manual QA bottlenecks.

## Dry-run high-severity consistency fixes (follow-up)

- **Status:** DONE
- **Decision date:** April 2026
- **Scope:** Consistency and completion-readiness items from the no-change dry-run review.

1) **WAR permission mismatch**
- **Chosen option:** Option 1 (strict role control)
- **Implemented result:** Only `GSO Office` and `Director` can create/edit WAR.
- **Files:** `apps/gso_reports/views.py`
- **Verification:** Access/permission regression tests added and passing.

2) **Work Reports KPI placeholders**
- **Chosen option:** Option B (real computed deltas)
- **Implemented result:** KPI trend badges now use actual period-over-period delta values instead of static placeholders.
- **Files:** `apps/gso_reports/views.py`, `templates/staff/work_reports.html`
- **Verification:** View renders with dynamic up/down/flat indicators and values.

3) **Request History logic (Personnel)**
- **Chosen option:** Personnel sees requests they handled.
- **Implemented result:** Personnel history now shows only completed/cancelled requests assigned to the logged-in personnel.
- **Files:** `apps/gso_accounts/views.py`
- **Verification:** Dedicated test confirms assigned-only visibility.

4) **Dead-end footer links (`#`)**
- **Chosen option:** Option B (real pages aligned to current UI)
- **Implemented result:** Added public Privacy, Terms, and Support pages; wired all footer links across requestor/staff/auth pages.
- **Files:** `apps/gso_accounts/views.py`, `apps/gso_accounts/urls.py`, `templates/public/info_page.html`, `templates/layouts/base_requestor.html`, `templates/includes/footer_staff.html`, `templates/registration/login.html`, `templates/registration/password_reset_form.html`
- **Verification:** Public info page route tests added and passing.

## Data migration readiness (WAR + IPMT)

- **Status:** DONE
- **Decision date:** April 2026
- **Scope:** Deploy-ready migration workflow for legacy WAR and IPMT records, including UI workflow and validation safeguards.

1) **WAR migration command + UI flow**
- **Implemented result:** Added robust legacy WAR import (`gso_import_legacy_war`) with Dry-run/Apply, integrated into Work Reports migration modal.
- **Behavior highlights:** Requesting Office + Assigned Personnel mapping, fallback rules, and migration badges in UI.
- **Safety:** Workbook unit auto-detection and mismatch blocking against selected target unit.

2) **IPMT migration command + UI flow**
- **Implemented result:** Added legacy IPMT import (`gso_import_legacy_ipmt`) for finalized template format (unit/employee/month + indicator rows), integrated into the same migration modal.
- **Behavior highlights:** Creates/updates `IPMTDraft`, supports continuation accomplishment rows and Dry-run/Apply.
- **Safety:** Workbook unit auto-detection and mismatch blocking against selected target unit.

3) **Operator UX hardening**
- **Implemented result:** In-modal processing/result popup for migration actions (Dry-run + Apply), with clear completion state and auto-close behavior.
- **Implemented result:** Account Management hides technical migration users (`migrated_req_*`, `migrated_per_*`, placeholders) to avoid operational clutter.

4) **Verification evidence**
- **Automated tests:** WAR import suite + IPMT import suite passing.
- **System check:** `python manage.py check` passing.
- **Manual verification:** Migration UI flow validated with sample files and cleanup/retry cycles.

## Recommended delivery sequence

- **Week 1 (P0):** Actions 1-2
- **Week 2 (P1):** Actions 3-4
- **Week 3 (P1):** Actions 5-6
- **Week 4 (P2):** Actions 7-9
- **Weeks 5-6 (P1):** Action 10 + regression test expansion

## Pre-deploy gate (must pass before release)

- `BLOCKER`: Do not deploy to production until **Action 1 (Secrets management and rotation)** is completed.
- Before final deployment:
  - Rotate all exposed credentials.
  - Update deployment secret store with new values.
  - Revoke old credentials after validation.
  - Complete `docs/SECRETS_ROTATION_RUNBOOK.md` sign-off.

## Quick architecture map

- `core`: project settings and routing
- `apps/gso_accounts`: auth, roles, profile, dashboards, notifications
- `apps/gso_requests`: request lifecycle, attachments, status transitions
- `apps/gso_inventory`: inventory items, transactions, material requests
- `apps/gso_reports`: WAR/IPMT generation and exports, AI-assisted drafting
- `apps/gso_notifications`: in-app and email notification dispatch
- `apps/gso_api`: JWT and REST API endpoints/serializers
