# GSO Panel Recommendations Checklist (Updated Status)

**Master order to finish everything:** see **`PANEL_COMPLETION_PLAN.md`** (phased roadmap: what to do first through defense).

Status legend: **DONE** = completed.

---

## 1) Reliability, Backup, Rollback (Sir Roy)

- [x] **Power interruption handling tests** — **DONE**  
  (Completed and documented.)
- [x] **Rollback support exists** — **DONE**  
  (`gso_backup` + restore runbook in `BACKUP_AND_ROLLBACK.md`.)
- [x] **Rollback drill / simulation evidence** — **DONE**  
  (Verified on laptop evidence run: backup created, restore executed successfully, and rollback flow confirmed.)
- [x] **Automated backup architecture documented** — **DONE**  
  (Process, schedule direction, storage/retention are documented in Part 3 and `BACKUP_AND_ROLLBACK.md`.)
- [x] **Backup schedule finalized in production machine** — **DONE**  
  (Completed and validated.)
- [x] **Backup storage strategy finalized (local/cloud/drive)** — **DONE**  
  (Completed and validated.)
- [x] **"Save to Drive" behavior fully implemented** — **DONE**  
  (Completed and validated.)

## 2) Request Policy & Workflow

- [x] **Editable requests after submission policy finalized** — **DONE**  
  (Locked in Phase 0: editable only until `DIRECTOR_APPROVED`.)
- [x] **Policy enforcement in code + UI** — **DONE**  
  (Implemented: requestor can edit while `DRAFT`, `SUBMITTED`, or `ASSIGNED`; editing is blocked from `DIRECTOR_APPROVED` onward.)
- [x] **Material arrival tracking in inventory** — **DONE**  
  (Arrival date + supplier/ref tracking implemented in inventory models/forms/views/templates.)
- [x] **Material request lifecycle notifications (personnel <-> unit head)** — **DONE**  
  (Submit/approve/reject notifications implemented.)

## 3) Paper / Documentation Updates

- [x] **Methodology changed to Waterfall** — **DONE**  
  (Completed.)
- [x] **Terminology standardized across paper/system** — **DONE**  
  (Completed.)
- [x] **NLG added in Definition/RRL/Features/Technical Discussion** — **DONE**  
  (Completed.)
- [x] **Definitions for 4 GSO units included** — **DONE**  
  (Completed.)
- [x] **Only objective-relevant diagrams retained** — **DONE**  
  (Completed.)
- [x] **Large flowchart split into module-level flowcharts** — **DONE**  
  (Completed.)
- [x] **RESTful API is implemented in system** — **DONE**  
  (Still needs explicit mention in Statement of Objectives/scope in paper if not yet added.)

## 4) Integration, Deployment, Platform (Ma'am Tine + Panel)

- [x] **Review actual GSO Excel formats** — **DONE**
- [x] **Document detailed data migration process (mapping/validation/import)** — **DONE**
- [x] **API key generation feature for secure auto-connection** — **DONE**
- [x] **Deployment process clarified with ICT (hosting/network/security)** — **DONE**  
  (Completed and aligned.)
- [x] **Multiple-unit selection in one request** — **DONE**  
  (Completed.)
- [x] **Google OAuth login** — **DONE**  
  (Implemented and tested.)
- [x] **Mobile responsiveness hardening (all key screens)** — **DONE**
- [x] **Standardized report headers** — **DONE**

## 5) Notifications Recommendation

- [x] **PSU email/Gmail notifications enabled end-to-end** — **DONE**  
  (SMTP + formatted email notifications validated end-to-end.)

## 6) Scope/Deferral Decisions (Phase 0 Locked)

- [x] **Offline-to-online sync scope decision finalized** — **DONE**  
  (Full offline sync marked as future enhancement for post-defense scope.)

---

## Immediate Next Actions (Panel-Readiness)

All panel recommendation items are marked **DONE**.

## Notes

- Checklist updated to reflect completion across all panel recommendation items.
