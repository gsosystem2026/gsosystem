# Staff sidebar and access by role

All four staff roles use the **same base template with sidebar**, but **each role sees a different sidebar**. Requestor uses a different layout (separate design).

---

## Unit Head – sidebar

| Item | Purpose |
|------|--------|
| **Dashboard** | Overview / home |
| **Request Management** | Requests for their unit; assign personnel, approve/complete work |
| **Request History** | Past requests (list/filter by status, date, etc.) |
| **Personnel Management** | Manage personnel in their unit (view, assign to requests) |
| **Inventory** | Manage their **unit’s** inventory (CRUD, adjust stock) |
| **Reports** | Reports if needed for the unit (e.g. unit-level summaries) |

**Request History:** Included so Unit Head can review past requests; can be a separate page or a tab/filter under Request Management when we build it.

---

## Personnel – sidebar

| Item | Purpose |
|------|--------|
| **Dashboard** | Overview / home |
| **Task Management** | My assigned tasks; update status, chat, mark “Done working” |
| **Task History** | Past tasks (completed, etc.) – optional but useful for “what I did” |
| **Inventory** | **View only** – see **stocks** for **their unit only**; filter/search (no add/edit/delete) |

**Inventory for Personnel:** Read-only. Personnel can see current stock levels and search/filter within their unit so they know what’s available when doing work. No create/edit/delete.

---

## GSO Office & Director – sidebar

| Item | GSO Office | Director | Purpose |
|------|------------|----------|--------|
| **Dashboard** | ✓ | ✓ | Overview / home |
| **Request Management** | ✓ | ✓ | View all requests; GSO notifies, Director (or OIC) approves |
| **Inventory** | ✓ | ✓ | All units, with filter by unit (manage/edit) |
| **Work Reports** | ✓ | ✓ | All reports (see below) |
| **Account Management** | No | ✓ | Add users, assign roles, **Assign OIC** |

**Work Reports** is the right term for the section that contains:

- **Work Accomplishment Report (WAR)**
- **IPMT Report**
- **Feedback** (and feedback summaries)
- Any other reports (e.g. export, analytics)

So one menu item **“Work Reports”** with sub-pages or sections for WAR, IPMT, Feedback, etc.

**Account Management (Director only):**

- **Add new users** and set their **role** (Requestor, Unit Head, Personnel, GSO Office, Director).
- **Assign OIC** (Officer-in-Charge): choose a GSO Office user to act as Director when the Director is away (that user can then approve requests).
- Optionally: edit/disable users, reset passwords, etc.

So **Assign OIC** lives **inside** Account Management (or a dedicated “Assign OIC” sub-page), not as a separate top-level sidebar item. Same place where the Director manages who can do what.

---

## Summary table

| Sidebar item | Unit Head | Personnel | GSO Office | Director |
|--------------|-----------|-----------|------------|----------|
| Dashboard | ✓ | ✓ | ✓ | ✓ |
| Request Management | ✓ | — | ✓ | ✓ |
| Request History | ✓ | — | — | — |
| Personnel Management | ✓ | — | — | — |
| Task Management | — | ✓ | — | — |
| Task History | — | ✓ | — | — |
| Inventory | ✓ (own unit, manage) | ✓ (own unit, **view only**) | ✓ (all, filter) | ✓ (all, filter) |
| Reports | ✓ | — | — | — |
| Work Reports | — | — | ✓ | ✓ |
| Account Management | — | — | — | ✓ |

---

## Requestor

Requestor uses a **different layout** (no staff sidebar). You’ll send the design later; we’ll keep Dashboard, My Requests, New Request, etc. in that layout.
