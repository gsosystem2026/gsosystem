# Panel Recommendations — Master Completion Plan

This document is the **ordered roadmap** to finish everything the panel asked for. Use **`PANEL_RECOMMENDATIONS_CHECKLIST.md`** to tick items off as you complete them.

**How to work:** Do phases **in order** where possible. Paper tasks (Phase B) can run **in parallel** with system tasks when they do not block each other.

---

## Guiding rule

**Stabilize core product first** (data safety, clear rules, deploy path), then **documentation and defense materials**, then **nice-to-have integrations** (OAuth, multi-unit, Drive) so you are not blocked on external accounts or big refactors at the end.

---

## Phase 0 — Lock decisions (half day to 1 day)

**Goal:** No rework from “we decided later.”

| Task | Outcome |
|------|---------|
| Post-submission **edit policy** | Written rule: e.g. editable only while `DRAFT` / until director approval / 24h window / never after submit. |
| **Backup storage** | Pick primary: local server folder + optional copy (Drive / second disk). Document who is responsible. |
| **Email channel** | PSU SMTP vs Gmail vs “in-app only for v1” — pick one for production. |
| **Multi-unit requests** | Decide: **in scope for defense** or **Phase 2** (honest scope in paper). |
| **Offline sync** | Treat as **research/limitation** unless you commit to a PWA or separate mobile app with sync (very large scope). |

**Deliverable:** One-page “decisions” note you can paste into your paper’s scope/limitations.

---

## Phase 1 — Prove reliability (system + evidence for panel)

**Goal:** Satisfy Sir Roy on recovery and rollback with **evidence**, not only features.

| Order | Task | Deliverable |
|-------|------|-------------|
| 1.1 | Run **`python manage.py migrate`** on every environment after pulls | No “column does not exist” errors. |
| 1.2 | **Rollback drill:** take backup → change test data → restore → verify | Screenshots + short write-up (append to `BACKUP_AND_ROLLBACK.md` or a `docs/` note). |
| 1.3 | **Power / outage simulation:** kill server or DB mid-submit (safe test user) | Short test matrix: what recovers, what user should retry; document limitations (web apps cannot magically save unsubmitted browser data). |
| 1.4 | **Production backup schedule** (when server exists) | Task Scheduler/cron entry + `GSO_BACKUP_KEEP` value in env. |

**Parallel paper:** One subsection “Disaster recovery and rollback procedure” referencing the drill.

---

## Phase 2 — Core system rules and communications

**Goal:** Clear behavior for requests + real notifications if the panel wants email.

| Order | Task | Deliverable |
|-------|------|-------------|
| 2.1 | Implement **post-submission edit policy** in code + templates | Role-based: who can edit, which statuses, messages when blocked. |
| 2.2 | **SMTP / email** (if chosen in Phase 0) | `.env` on server, send test mail, document in deployment plan. |
| 2.3 | Map **which events** trigger email (subset of in-app notifications) | Avoid spam; document list for paper. |

**Already done (verify in demo only):** inventory arrival tracking, material request notifications, REST API.

---

## Phase 3 — Deployment path with ICT

**Goal:** Ma’am Tine’s “clarify with ICT” becomes a signed-off path.

| Order | Task | Deliverable |
|-------|------|-------------|
| 3.1 | Meeting or email with **ICT**: hosting, domain, HTTPS, firewall, VPN for motorpool if needed | Checklist filled in `PSU_DEPLOYMENT_PLAN.md` (or attach ICT reply). |
| 3.2 | **Staging** URL or internal IP + `DEBUG=False` smoke test | Short go-live checklist executed once. |
| 3.3 | Align **backup job** on the real server (Phase 1.4) | Same as production schedule. |

---

## Phase 4 — Data migration (Excel) and reports polish

**Goal:** Panel Excel + report header items are demonstrable or honestly scoped.

| Order | Task | Deliverable |
|-------|------|-------------|
| 4.1 | Collect **real GSO Excel samples** | Files in a secure folder (not committed if sensitive). |
| 4.2 | **Field mapping table** (Excel column → model field) | Markdown or spreadsheet. |
| 4.3 | One **import command** (or staff-only upload) for **one entity first** (e.g. inventory or users) | Works on copy of DB; error log for bad rows. |
| 4.4 | **Paper:** “Data migration process” section | Cleaning, validation, import steps, rollback if import fails. |
| 4.5 | **Standardized report headers** (PDF/Excel exports you actually generate) | One template reused everywhere. |

---

## Phase 5 — Paper and thesis alignment (parallel from Phase 2 onward)

**Goal:** Sir Roy / Ma’am Kaye / Ma’am Tine documentation requests.

| Order | Task | Deliverable |
|-------|------|-------------|
| 5.1 | **Waterfall** methodology in paper | Chapters aligned (no agile wording left if that was the feedback). |
| 5.2 | **Terminology** pass | One glossary: Job Request, Department vs UoM, roles, units. |
| 5.3 | **NLG** in Definition, RRL, Features, Technical | How NLG will support WAR/IPMT reports (even if AI feature is “next” — scope and ethics). |
| 5.4 | **Definitions of four GSO units** | Short paragraph each in paper + optional in-app help text. |
| 5.5 | **Diagrams** | Remove clutter; split main flowchart into modules (Request, Inventory, Accounts, API, Reports). |
| 5.6 | **Objectives / scope** | Explicit bullet: **RESTful API** implemented. |

---

## Phase 6 — Integrations (only after Phases 0–3 are stable)

**Goal:** High-effort items that are impressive but risky if done too early.

| Order | Task | Notes |
|-------|------|--------|
| 6.1 | **API key generation** (admin UI + revoke) | For integrations; document in API doc. |
| 6.2 | **Google OAuth** | Requires Google Cloud project + ICT policy on external auth. |
| 6.3 | **Multiple units per request** | Model + routing + assignments change; only if Phase 0 says “in scope.” |
| 6.4 | **Attachment / backup “save to Drive”** | Service account or OAuth; security review with ICT. |
| 6.5 | **Offline-to-online sync** | Treat as future work unless you narrow to “draft saved in browser” (limited). |

---

## Phase 7 — Mobile and UX hardening

**Goal:** Responsive layout across main flows.

| Task | Deliverable |
|------|-------------|
| Audit **requestor**, **staff** inventory, **request detail**, **tables** on tablet width | List of breakpoints / fixes. |
| Fix **navigation and tables** (horizontal scroll, stacked actions) | Consistent patterns. |

---

## Phase 8 — Defense package (last week)

| Task | Deliverable |
|------|-------------|
| Demo script (5–10 min) | Request flow + inventory arrival + backup mention + API if asked. |
| **Limitations** slide | Power loss, offline, OAuth not yet, etc., as applicable. |
| Update **`PANEL_RECOMMENDATIONS_CHECKLIST.md`** | All items `[x]` or explicitly “deferred to Phase 2” with panel agreement. |

---

## Suggested “finish order” summary (do this sequence)

1. **Phase 0** — decisions  
2. **Phase 1** — migrate + backup drill + outage notes  
3. **Phase 2** — edit policy + email (if required)  
4. **Phase 3** — ICT + deploy path  
5. **Phase 4** — Excel migration + report headers  
6. **Phase 5** — paper (Waterfall, NLG, units, diagrams, REST in objectives) — **start early**, finish with Phase 8  
7. **Phase 6** — OAuth / API keys / multi-unit / Drive **only if time and decisions allow**  
8. **Phase 7** — responsive pass  
9. **Phase 8** — demo + checklist closure  

---

## What to tell the panel if time runs out

- **Offline sync:** Honest scope — full offline-first is a major product; document as **future enhancement** and show **online-first** + **backup/rollback** instead.  
- **DB triggers for backup:** Prefer **scheduled `gso_backup`**; triggers for backup are unusual in web apps — document **why** you chose scheduled backups + Neon snapshots.  
- **Multi-unit + OAuth:** Either demo-ready or clearly **Phase 2** with dates in the roadmap.

---

*Last aligned with checklist items in `PANEL_RECOMMENDATIONS_CHECKLIST.md`.*
