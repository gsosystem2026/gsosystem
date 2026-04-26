# Power Interruption Test Matrix (Phase 1 Reliability Evidence)

Use this document as proof for panel review that the system was tested for interruption scenarios and recovery behavior.

---

## Test metadata

- Test date:
- Testers:
- Environment:
  - OS:
  - Python version:
  - Database: Neon PostgreSQL
  - App URL:
- Build/version:

---

## Pass criteria

1. No permanent data corruption after interruption.
2. System can reconnect and continue normal operations.
3. If interruption happens mid-action, user receives failure/retry behavior (not silent success with bad data).
4. If needed, restore from backup completes successfully.

---

## Pre-test checklist

- [ ] `python manage.py gso_db_check` shows PostgreSQL and `Connection OK`.
- [ ] Fresh backup created (`scripts\run_gso_backup.bat`).
- [ ] Backup files confirmed in `backups/`:
  - [ ] `pg_YYYYMMDD_HHMMSS.dump`
  - [ ] `data_YYYYMMDD_HHMMSS.json`
- [ ] Test accounts prepared (requestor + staff/unit head).
- [ ] One test inventory item identified for verification.

---

## Test cases

### TC-PI-01: Interruption during read-only operation

- **Scenario:** User is browsing dashboard/request list when interruption occurs.
- **Steps:**
  1. Open staff dashboard and request list.
  2. Simulate interruption (network off / app stop / machine sleep).
  3. Restore connection and reopen page.
- **Expected result:**
  - Page loads after reconnect.
  - No data changes/loss because operation is read-only.
- **Actual result:**
- **Status (PASS/FAIL):**
- **Evidence (screenshot/log):**
- **Notes:**

---

### TC-PI-02: Interruption during request submission

- **Scenario:** Requestor submits a request while interruption happens near submit.
- **Steps:**
  1. Prepare request form with test data.
  2. Click submit.
  3. Immediately simulate interruption.
  4. Reconnect and check request list.
- **Expected result:**
  - Request is either fully saved once or not saved at all.
  - No duplicate/corrupted partial record.
  - User can retry safely if needed.
- **Actual result:**
- **Status (PASS/FAIL):**
- **Evidence (screenshot/log):**
- **Notes:**

---

### TC-PI-03: Interruption during inventory update

- **Scenario:** Staff updates inventory quantity while interruption occurs.
- **Steps:**
  1. Note baseline quantity of test item.
  2. Perform quantity adjustment.
  3. Simulate interruption near action.
  4. Reconnect and verify final quantity.
- **Expected result:**
  - Quantity is consistent (either previous or fully updated value).
  - No broken state.
- **Actual result:**
- **Status (PASS/FAIL):**
- **Evidence (screenshot/log):**
- **Notes:**

---

### TC-PI-04: Recovery via restore after interruption test

- **Scenario:** Validate disaster recovery path after test modifications.
- **Steps:**
  1. Run rollback:
     ```powershell
     powershell -ExecutionPolicy Bypass -File scripts\rollback_latest_backup.ps1
     ```
  2. Verify critical records (users, requests, inventory sample).
- **Expected result:**
  - Restore completes successfully.
  - Selected records match backup state.
- **Actual result:**
- **Status (PASS/FAIL):**
- **Evidence (screenshot/log):**
- **Notes:**

---

## Summary

- Total cases:
- Passed:
- Failed:
- Overall result: **PASS / FAIL**

### Observed risks

- 

### Mitigations / next actions

- 

---

## Panel-ready conclusion (template)

> Interruption scenarios were tested across read, submit, and inventory update flows. The system recovered correctly after reconnection, preserved data integrity, and rollback from backup was successfully executed. This validates the project’s recovery strategy for power/network interruption events within current scope.
