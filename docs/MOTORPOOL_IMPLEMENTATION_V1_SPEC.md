# Motorpool Implementation Spec (v1)

## Status
Proposed spec for implementation planning (no code yet).

## Goal
Implement a **Motorpool** workflow that matches the provided paper forms:
1. **Request for Use of University Vehicle** (Motorpool Request)
2. **Driver’s Trip Ticket** (Trip Ticket)

Motorpool requests must keep the existing **Director/OIC approval gate**.

## Locked workflow decisions (from discussion)
1. **Director/OIC approval is required** (do not bypass Director/OIC approval).
2. Motorpool request submission is still `gso_requests.Request`, but Motorpool has a **different UI/process** than other units.
3. **Driver/Personnel** (assigned user) sets the `Done working` status.
4. **Unit Head** clicks `Complete request` to mark `COMPLETED`.
5. Actual trip-ticket fields are **hybrid digital + manual**:
   - If fields are entered digitally, they appear on generated printable tickets.
   - If fields are not entered, the printable ticket contains **blank spaces** so officials can **handwrite** values.
6. Actuals can be entered by **both**:
   - driver/personnel
   - unit head
7. **WAR entries should still be created** on `COMPLETED`, but the system must be adjusted so WAR content is **trip-relevant** (not irrelevant to motorpool).
8. **GSO Office generation/printing is removed** for Motorpool. (They can still view.)
9. Motorpool must include **fuel + other consumables** tracking on the trip ticket.  
   - Fuel/supplies are treated as **ticket consumption**, not inventory deduction, per the process option chosen in the discussion.
10. Keep the existing attachment mechanism unless the Motorpool forms require additional upload(s) (TBD).

## Role-based actions (v1)
### Requestor
- Submits a Motorpool request with **planned trip data**.
- Provides request context: purpose, places/itinerary, passengers/contact info, etc. (see “Required Fields”).
- May upload supporting attachments if the UI supports it (optional; the core flow does not depend on it).

### Unit Head (Motorpool)
- Assigns **personnel/driver** using the existing assignment mechanism (`RequestAssignment`).
- Enters/maintains **vehicle** details needed for the request/ticket.
- Generates/prints:
  - Motorpool Request (page A)
  - Driver’s Trip Ticket (page B)
- Can enter **actuals** on the trip ticket (fuel/consumables and any per-leg actuals) as needed.

### Driver/Personnel (assigned)
- Updates work lifecycle:
  - sets `IN_PROGRESS` → after trip start, then sets `DONE_WORKING` when trip/actuals are ready.
- Enters **actuals** on the trip ticket (hybrid digital + manual):
  - per-leg actual times/places (if digitized)
  - distance totals (if digitized)
  - fuel and other consumables usage (if digitized)
- Can leave fields blank to be handwritten on printed ticket.

### Director/OIC
- Approves the request at the existing Director gate (`DIRECTOR_APPROVED` status).
- No special motorpool bypass in v1.

## Data model & UI requirements (high level)
### Key principle
Motorpool trip data is **structured** enough to:
- render a printable ticket
- support hybrid blanks when values are missing
- keep WAR “reasonably relevant” (trip-related summary/accomplishments)

### Planned vs Actual
Motorpool ticket generation should support:
- **Planned fields** (entered by requestor)
- **Actual fields** (optional; entered by driver and/or unit head after the trip)

### Fuel & other consumables
- Fuel (gasoline) and other consumables must be captured on the **Trip Ticket** section.
- Since the process selected treats these as ticket consumption (not inventory deduction), the v1 implementation must **not** imply inventory stock deduction for motorpool consumables.

## Required motorpool fields (map from paper forms)
> Note: this list is derived from the screenshots. Some labels may differ slightly in the final implementation. The key is the same underlying meaning.

### A) Motorpool Request (Request for Use of University Vehicle) – required sections
1. Filing/Date info:
   - Date of filing (default to creation timestamp; may be editable)
2. Driver & vehicle identifiers:
   - Driver name
   - Vehicle plate/stamp/contract identifiers (as applicable)
   - (Optional) “Trans.” field if your paper uses it as a required identifier
3. Request context:
   - Requesting office / requesting unit text
   - Purpose/s
   - Place(s) to be visited
4. Trip schedule:
   - Date and time of trip
   - Number of days
   - Itinerary of travel (multi-leg lines)
5. Personnel / passengers / contact:
   - Number of passengers
   - Contact number
   - Contact person
6. Administrative sign-off lines:
   - Noted by (immediate supervisor)
   - Recommending approval (unit head / approver lines)
   - Approved (Director/OIC or President/OIC as per paper)

### B) Driver’s Trip Ticket – required sections
1. Trip metadata:
   - Travel date
   - Driver name
   - Vehicle contract/stamp number
   - Authorized requester/passenger info
   - Purpose
2. Per-leg trip table (multi-row):
   - Sequence/leg identifier
   - Departure datetime + departure place
   - Arrival datetime + arrival place
   - Requisitioning office / destination (as shown by paper)
   - Distance per leg
3. Totals:
   - Total number of hours
   - Total number of trips (if applicable)
   - Total distance of travel
4. Fuel & consumables (hybrid):
   - Beginning fuel in tank (liters)
   - Added/issued/purchased during trip (liters)
   - Total fuel available/used (as per paper’s calculation)
   - Fuel used (liters)
   - Ending balance in tank (liters)
   - Other consumables (wheel/gas can usage, oil, etc. as applicable to your paper—store as quantities/text)
5. Driver and certifications/signatures:
   - Signature/certification lines at bottom (walking signatures).

## Printing outputs (v1)
### What to generate
1. Motorpool Request (page A template)
2. Driver’s Trip Ticket (page B template)

### When printing is allowed
- Unit Head can print once the motorpool request is approved enough for the trip to proceed.
- (Exact status gating is TBD but should align with existing Director approval gate semantics.)

### Print method
- Generate **print-friendly HTML** pages (browser print) or any existing templating approach used by the app.
- Include signature lines on the page so officials can sign physically after printing.

## Existing app lifecycle mapping (important)
- `SUBMITTED` / `ASSIGNED` / `DIRECTOR_APPROVED` should remain meaningful.
- Motorpool “actuals entry” should be allowed after `DIRECTOR_APPROVED` (TBD), but must support blanks.
- `DONE_WORKING` is driver/personnel-controlled.
- `COMPLETED` is unit head-controlled and triggers:
  - WAR creation (keep)
  - any finalization logic for trip ticket completeness (TBD).

## WAR “relevance fix” requirement
On `COMPLETED`, the system currently auto-creates WARs for assigned personnel.
For motorpool, WAR should be based on the trip ticket content (planned and/or actual where available):
- Summary should reflect trip purpose/route.
- Accomplishments should reflect executed trip and consumables usage in a concise trip narrative.
If actuals are blank, WAR can reference planned fields (and note “actuals pending / to be handwritten” if needed).

## Dependencies / integration points in repo (for implementers)
Relevant areas (from existing code):
- `apps/gso_requests`:
  - request lifecycle statuses
  - assignment model (`RequestAssignment`)
  - Director approval gate
  - WAR creation trigger on `COMPLETED`
- `apps/gso_reports`:
  - WAR generation (`ensure_war_for_request`)
  - WAR editor and export exist already; motorpool content needs to be trip relevant.

## Non-goals in v1 (explicit)
- No full PDF generation library integration in v1 unless already present.
- No digitized signatures (walking signatures only).
- No inventory stock deduction for motorpool consumables (since process is ticket-only consumption).

## Open questions (must confirm before coding)
1. **Status gating for printing**: exactly which request status allows unit head to print the request and trip ticket?
2. **Do we store uploaded attachments for motorpool** (paper copies/photos) in addition to digitized fields? If yes, still only one attachment or do we need two?
3. **Exact fields to treat as “other consumables”** beyond fuel (e.g., oil, lubrication, wheel, gas can). Confirm the list from your paper/training.
4. **Itinerary table columns**: confirm the exact set/order used for legs so the generated HTML matches your form.

