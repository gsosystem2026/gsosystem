# Request Flow Finalization (Before Unit-Specific Changes)

**Purpose:** Finalize request workflow and per-unit form/process rules before implementing new logic in code.

This document is the decision source for:
- status transitions per unit
- required approvals per unit
- required fields/forms per unit

---

## 1) Current Baseline Flow (Implemented Today)

The current system uses one shared lifecycle for all units:

`SUBMITTED -> ASSIGNED -> DIRECTOR_APPROVED -> IN_PROGRESS <-> ON_HOLD -> DONE_WORKING -> COMPLETED`

Other exits:
- `CANCELLED` (requestor can cancel only before work starts)
- `DONE_WORKING -> IN_PROGRESS` (return for rework by Unit Head)

Roles in current flow:
- **Requestor:** create/edit/cancel (with current constraints)
- **Unit Head:** assign personnel, mark emergency, complete, return for rework
- **Director/OIC:** approve assigned request
- **Personnel:** update work status and post work messages
- **GSO Office:** oversight/reminders

---

## 2) Finalization Strategy

1. Keep a **base flow** for units that do not need custom behavior.
2. Define **unit-specific overrides** only where needed (start with Motorpool).
3. Finalize required fields/forms per unit before backend refactor.
4. Implement in phases: Motorpool first, then next units.

---

## 3) Unit Workflow Matrix (Decision Table)

Use this table to define the final process per unit.

| Unit | Uses base flow? | Status changes from base | Extra approval needed? | Skip any step? | Notes |
|------|------------------|--------------------------|------------------------|----------------|-------|
| Repair & Maintenance | Yes (default) | Add `INSPECTION` before `IN_PROGRESS` (personnel step) | No | No | Personnel must inspect before starting work |
| Utility | Yes (default) | None | No | No | |
| Electrical | Yes (default) | Add `INSPECTION` before `IN_PROGRESS` (personnel step) | No | No | Personnel must inspect before starting work |
| Motorpool | **TBD (likely custom)** | **TBD** | **TBD** | **TBD** | Driver/off-campus realities may need custom handling |

---

## 4) Unit Form Matrix (Request Submission Requirements)

Define what requestors must submit per unit.

| Field / Requirement | Repair | Utility | Electrical | Motorpool | Notes |
|---------------------|--------|---------|------------|-----------|-------|
| Title | Required | Required | Required | Required | current |
| Description | Required | Required | Required | Required | current |
| Labor checkbox | Optional | Optional | Optional | Optional | current |
| Materials checkbox | Optional | Optional | Optional | Optional | current |
| Others checkbox | Optional | Optional | Optional | Optional | current |
| Contact details | Optional | Optional | Optional | Optional | current |
| Attachment | Optional | Optional | Optional | Optional | current |
| **Date needed** | TBD | TBD | TBD | **TBD** | proposed |
| **Vehicle details** (plate/unit) | N/A | N/A | N/A | **TBD** | Motorpool candidate |
| **Destination / route** | N/A | N/A | N/A | **TBD** | Motorpool candidate |
| **Passenger count** | N/A | N/A | N/A | **TBD** | Motorpool candidate |
| **Trip schedule** (depart/return) | N/A | N/A | N/A | **TBD** | Motorpool candidate |

> Mark each TBD as Required / Optional / Not used.

---

## 5) Motorpool First (Detailed Draft)

This is a starter draft to confirm with stakeholders.

### 5.1 Proposed process options

Pick one:

- **Option A (Conservative):** keep base flow, add Motorpool-specific form fields only.
- **Option B (Moderate):** base flow + one extra pre-approval check before `ASSIGNED` or before `DIRECTOR_APPROVED`.
- **Option C (Custom):** dedicated motorpool statuses (e.g., `SCHEDULED`, `DISPATCHED`, `RETURNED`) in addition to shared statuses.

**Recommended starting point:** **Option A**, then evolve after 2-4 weeks of real usage data.

### 5.2 Proposed Motorpool fields (phase 1)

- destination
- purpose of travel
- date/time needed
- estimated return time
- passenger count
- preferred vehicle type (optional)
- special instructions

---

## 6) Acceptance Criteria for “Flow Finalized”

Flow is considered finalized when:

- [ ] Each unit row in workflow matrix is complete (no TBD).
- [ ] Each unit column in form matrix is complete (no TBD).
- [ ] Motorpool option (A/B/C) is approved.
- [ ] Stakeholders agree on who approves what.
- [ ] Edge cases are decided (cancellation window, rework, emergency path).

---

## 7) Implementation Plan (After Approval)

1. Add config structure for per-unit workflow and form requirements.
2. Implement Motorpool unit-specific rules first.
3. Add tests for transition guards and required fields.
4. Roll out to one unit pilot, collect feedback.
5. Apply same pattern to other units only if needed.

---

## 8) Decision Log

Use this section to record approved decisions.

- Date:
- Participants:
- Decision:
- Effective unit(s):
- Follow-up action:

