# GSO Panel Recommendations Checklist (Updated Status)

**Master order to finish everything:** see **`PANEL_COMPLETION_PLAN.md`** (phased roadmap: what to do first through defense).

Status legend: **DONE** = already implemented, **IN PROGRESS** = partially done / documented but not fully validated, **PENDING** = not yet implemented.

---

## 1) Reliability, Backup, Rollback (Sir Roy)

- [ ] **Power interruption handling tests** — **PENDING**  
  (Need documented outage test cases + execution evidence.)
- [x] **Rollback support exists** — **DONE**  
  (`gso_backup` + restore runbook in `BACKUP_AND_ROLLBACK.md`.)
- [ ] **Rollback drill / simulation evidence** — **IN PROGRESS**  
  (Mechanism exists, but formal recorded drill for panel is still needed.)
- [x] **Automated backup architecture documented** — **DONE**  
  (Process, schedule direction, storage/retention are documented in Part 3 and `BACKUP_AND_ROLLBACK.md`.)
- [ ] **Backup schedule finalized in production machine** — **IN PROGRESS**  
  (Planned; to be activated after deployment.)
- [ ] **Backup storage strategy finalized (local/cloud/drive)** — **IN PROGRESS**  
  (Options mapped; final operational choice pending deployment setup.)
- [ ] **"Save to Drive" behavior fully implemented** — **PENDING**  
  (Currently planned as post-stabilization attachment/backup offload.)

## 2) Request Policy & Workflow

- [ ] **Editable requests after submission policy finalized** — **PENDING**  
  (Need final rule: editable until approval / limited window / locked after submit.)
- [ ] **Policy enforcement in code + UI** — **PENDING**  
  (Implement right after policy decision.)
- [x] **Material arrival tracking in inventory** — **DONE**  
  (Arrival date + supplier/ref tracking implemented in inventory models/forms/views/templates.)
- [x] **Material request lifecycle notifications (personnel <-> unit head)** — **DONE**  
  (Submit/approve/reject notifications implemented.)

## 3) Paper / Documentation Updates

- [ ] **Methodology changed to Waterfall** — **PENDING**
- [ ] **Terminology standardized across paper/system** — **IN PROGRESS**
- [ ] **NLG added in Definition/RRL/Features/Technical Discussion** — **PENDING**
- [ ] **Definitions for 4 GSO units included** — **PENDING**
- [ ] **Only objective-relevant diagrams retained** — **PENDING**
- [ ] **Large flowchart split into module-level flowcharts** — **PENDING**
- [x] **RESTful API is implemented in system** — **DONE**  
  (Still needs explicit mention in Statement of Objectives/scope in paper if not yet added.)

## 4) Integration, Deployment, Platform (Ma'am Tine + Panel)

- [ ] **Review actual GSO Excel formats** — **PENDING**
- [ ] **Document detailed data migration process (mapping/validation/import)** — **PENDING**
- [ ] **API key generation feature for secure auto-connection** — **PENDING**
- [ ] **Deployment process clarified with ICT (hosting/network/security)** — **IN PROGRESS**  
  (Campus-first deployment strategy drafted; ICT coordination step still pending.)
- [ ] **Multiple-unit selection in one request** — **PENDING**
- [ ] **Google OAuth login** — **PENDING**
- [ ] **Mobile responsiveness hardening (all key screens)** — **IN PROGRESS**
- [ ] **Standardized report headers** — **PENDING**

## 5) Notifications Recommendation

- [ ] **PSU email/Gmail notifications enabled end-to-end** — **IN PROGRESS**  
  (SMTP setup was prepared then paused; needs final credentials and production testing.)

---

## Immediate Next Actions (Panel-Readiness)

1. Finalize **post-submission edit policy** and implement it in code/UI.
2. Run and document a **rollback drill** + **power interruption simulation**.
3. Complete **Waterfall + terminology + NLG + unit definitions** in the paper.
4. Coordinate final **ICT deployment checklist** (server/domain/security).
5. Prepare a short **inventory arrival tracking demo script** for panel presentation.
