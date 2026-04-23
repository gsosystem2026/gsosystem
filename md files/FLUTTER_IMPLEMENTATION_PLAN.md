# GSO (General Services Office) — Flutter Mobile App Implementation Plan

**Goal:** Build a cross-platform mobile app (iOS & Android) that connects to the existing Django backend via REST API, enabling users to manage requests, inventory, and workflows on the go.

**Stack:** Flutter (Dart) + existing Django REST API (`/api/v1/`) + JWT + SQLite (optional local cache)

---

## Current Backend API (Already Available)

| Endpoint | Method | Auth | Purpose |
|---------|--------|------|---------|
| `/api/v1/auth/token/` | POST | No | Username + password → access + refresh tokens |
| `/api/v1/auth/token/refresh/` | POST | Yes | Refresh token → new access token |
| `/api/v1/units/` | GET | No (public) | List units (Repair & Maintenance, Utility, Electrical, Motorpool, Security) |
| `/api/v1/requests/` | GET, POST | JWT | List/create requests (role-filtered) |
| `/api/v1/requests/{id}/` | GET | JWT | Request detail |
| `/api/v1/inventory/` | GET | JWT | List inventory (role-filtered) |

**Note:** API may need extension for full parity (assignments, approvals, chat, WAR, notifications, feedback). Plan phases account for this.

---

## Phase Overview

| Phase | Focus | Outcome | Est. |
|-------|--------|---------|------|
| **1** | Foundation & setup | Flutter project, API client, auth, base UI | 1–2 weeks |
| **2** | Auth & role-based navigation | Login, role detection, dashboard per role | 1 week |
| **3** | Requestor flow | Create request, view my requests, status | 1 week |
| **4** | Staff flow (Unit Head/Personnel) | Request list, assign, approve, work status | 1–2 weeks |
| **5** | Inventory & GSO/Director | Inventory list, filters, unit view | 1 week |
| **6** | Notifications & polish | Push notifications, offline hints, UX polish | 1–2 weeks |

---

## Phase 1: Foundation & Setup

**Goal:** Project skeleton, API client, and base architecture.

### 1.1 Project setup
- Create Flutter project: `flutter create gso_mobile` (or `gso_app`)
- Configure `pubspec.yaml`:
  - `http` or `dio` (HTTP client)
  - `flutter_secure_storage` (secure token storage)
  - `provider` or `riverpod` (state management)
  - `go_router` or `auto_route` (navigation)
- Folder structure:
  ```
  lib/
  ├── main.dart
  ├── app.dart
  ├── core/           # config, constants, theme
  ├── data/            # API client, models, repositories
  ├── domain/          # (optional) business logic
  └── presentation/   # screens, widgets, providers
  ```

### 1.2 API client
- Base URL: configurable (e.g. `https://your-domain.com/api/v1/`)
- Interceptor: attach JWT to `Authorization: Bearer <token>` when present
- Auth interceptor: on 401, try refresh token; if fail → logout
- Error handling: network errors, 4xx/5xx, parse errors

### 1.3 Auth service
- `login(username, password)` → store access + refresh tokens
- `getAccessToken()` → return cached or refresh if expired
- `logout()` → clear tokens
- `isLoggedIn` → check if tokens exist

### 1.4 Base UI
- Theme (colors, typography) aligned with GSO branding
- Splash screen (logo + loading)
- Auth gate: if not logged in → Login screen; else → Home

**Deliverables:** App runs locally, can call API (auth, units), base UI with theme. **Phase 1 complete.**

---

## Phase 2: Auth & Role-Based Navigation

**Goal:** Login flow, role detection, and dashboard per role.

### 2.1 Login screen
- Username + password fields
- Loading state during login
- Error display (invalid credentials, network error)
- Optional: remember me, biometric (future)

### 2.2 User info & role
- After login, store user info (id, username, role, unit_id)
- **Option A:** Backend returns user info in token payload (custom claims)
- **Option B:** Add `/api/v1/users/me/` endpoint to Django → GET current user
- **Option C:** Decode JWT payload (if role is in claims)

### 2.3 Role-based navigation
- Bottom nav or drawer based on role:
  - **Requestor:** My Requests, New Request
  - **Unit Head:** Request Management, Inventory, (optional) Activity Log
  - **Personnel:** Task Management, Task History
  - **GSO Office / Director:** Request Management, Inventory, Work Reports, Reports

### 2.4 Dashboard
- Placeholder per role (or redirect to main screen)
- Optional: quick stats (e.g. pending requests count)

**Deliverables:** Login works, role detected, nav shows correct screens per role. **Phase 2 complete.**

---

## Phase 3: Requestor Flow

**Goal:** Requestors can create and view requests.

### 3.1 Units list
- Fetch `/api/v1/units/` (public)
- Display in picker or list for “New Request”

### 3.2 Create request
- Form: unit (required), title, description, labor, materials, others
- Custom fields: full name, email, contact number (PH format)
- Optional: attachment (file picker → multipart upload; backend must support)
- Submit → POST `/api/v1/requests/` → success/error feedback

### 3.3 My requests list
- GET `/api/v1/requests/` (filtered by requestor)
- Filter: status (All, Submitted, In Progress, Completed, etc.)
- Search: by title or ID
- Pull-to-refresh

### 3.4 Request detail
- GET `/api/v1/requests/{id}/`
- Show: unit, title, description, status, assignments, timestamps
- Attachment preview/download (if available)

**Deliverables:** Requestor can create requests and view their list/detail. **Phase 3 complete.**

---

## Phase 4: Staff Flow (Unit Head, Personnel, GSO, Director)

**Goal:** Staff can manage requests, assign, approve, and update work status.

### 4.1 Request list (staff)
- GET `/api/v1/requests/` (filtered by role)
- Unit Head: unit filter; GSO/Director: all or by unit
- Filter: status, search
- Pull-to-refresh

### 4.2 Request detail (staff) ✓
- Same view as requestor; add staff actions:
  - **Unit Head:** Assign personnel (SUBMITTED/ASSIGNED), Complete / Return for rework (DONE_WORKING)
  - **Director/OIC:** Approve (ASSIGNED → DIRECTOR_APPROVED)
  - **Personnel:** Update work status (In Progress, On Hold, Done working)

### 4.3 API extensions ✓
- **Assign personnel:** `POST /api/v1/requests/{id}/assign/` with `personnel_ids`
- **Approval:** `POST /api/v1/requests/{id}/approve/`
- **Work status:** `PATCH /api/v1/requests/{id}/` or `POST /api/v1/requests/{id}/status/`
- **Personnel list:** `GET /api/v1/users/?role=personnel&unit={id}`

### 4.4 Chat / activity feed (optional)
- If backend has chat: `GET /api/v1/requests/{id}/messages/`, `POST` to add
- Otherwise: defer to Phase 6 or web-only

**Deliverables:** Staff can list, view, assign, approve, and update work status. **Phase 4 complete.**

---

## Phase 5: Inventory & GSO/Director

**Goal:** Unit Heads manage own unit; GSO/Director view all with filter.

### 5.1 Inventory list
- GET `/api/v1/inventory/` (role-filtered)
- Unit Head: only their unit
- GSO/Director: all or filter by unit

### 5.2 Inventory detail
- Show item info: name, quantity, reorder level, location, etc.
- Low stock indicator

### 5.3 Inventory CRUD (optional)
- **API:** Add `POST`, `PUT`, `DELETE` to inventory if backend supports
- **Unit Head:** Add, edit, adjust quantity

### 5.4 Work Reports (Director/GSO)
- **API:** Add `/api/v1/reports/work/` or similar if analytics endpoint exists
- **App:** Display KPIs, charts (or summary cards) in dashboard

**Deliverables:** Inventory list/detail per role; optional CRUD for Unit Head. **Phase 5 complete.**

---

## Phase 6: Notifications & Polish

**Goal:** Push notifications, offline hints, UX polish.

### 6.1 Push notifications
- Firebase Cloud Messaging (FCM) or similar
- Backend: store device tokens; send push on key events (new request, assignment, approval, etc.)
- App: handle foreground/background notifications

### 6.2 In-app notifications
- Optional: `GET /api/v1/notifications/` if backend has
- Badge count on nav icon

### 6.3 Offline & UX
- Offline: show cached data (if using local DB) or “No connection” message
- Loading skeletons
- Error retry
- Empty states

### 6.4 Version check
- Backend: `/accounts/version/` returns app version
- App: show “New version available” banner when outdated

**Deliverables:** Push notifications; polished UX; version check. **Phase 6 complete.**

---

## Suggested Order of Work

1. **Phase 1** — Foundation (project, API client, auth, base UI)
2. **Phase 2** — Auth & role-based navigation
3. **Phase 3** — Requestor flow (create, list, detail)
4. **Phase 4** — Staff flow (assign, approve, work status)
5. **Phase 5** — Inventory (list, detail, optional CRUD)
6. **Phase 6** — Notifications & polish

---

## Backend API Extensions (if needed)

| Feature | Current | Needed |
|---------|---------|--------|
| User/me | — | `GET /api/v1/users/me/` (id, username, role, unit_id) |
| Assign personnel | — | `POST /api/v1/requests/{id}/assign/` |
| Approve | — | `POST /api/v1/requests/{id}/approve/` |
| Work status | — | `PATCH /api/v1/requests/{id}/` or dedicated status endpoint |
| Personnel list | — | `GET /api/v1/users/?role=personnel&unit={id}` |
| Inventory CRUD | Read-only | `POST`, `PUT`, `DELETE` to inventory |
| Notifications | — | `GET /api/v1/notifications/` |
| Attachments | — | Multipart upload for create; download URL for detail |

---

## Tech Stack Summary

| Layer | Choice |
|-------|--------|
| Framework | Flutter |
| State | Provider or Riverpod |
| HTTP | Dio (with interceptors) |
| Auth storage | flutter_secure_storage |
| Routing | go_router |
| Push | Firebase Cloud Messaging |
| Local cache | Optional: sqflite or hive |

---

## Summary Table

| Phase | Focus | Outcome | Status |
|-------|--------|---------|--------|
| 1 | Foundation & setup | Flutter project, API client, auth, base UI | ✅ Done |
| 2 | Auth & role-based nav | Login, role detection, dashboard per role | ✅ Done |
| 3 | Requestor flow | Create request, view my requests, detail | ✅ Done |
| 4 | Staff flow | Request list, assign, approve, work status | ✅ Done |
| 5 | Inventory & GSO/Director | Inventory list, filters, optional CRUD | ✅ Done |
| 6 | Notifications & polish | In-app notifications, badge, mark read | ✅ Done |

---

## Next Step

Phase 6 complete. Added (scaffold for future polish):
- **Version check:** `GET /api/v1/version/` + banner when update required. Set `GSO_APP_MIN_VERSION` in env.
- **Push notifications:** FCM init on login, `POST /api/v1/notifications/register_device/`, `DeviceToken` model. Configure Firebase (google-services.json) to enable.
- **Offline mode:** `connectivity_plus`, offline banner when no connection.
