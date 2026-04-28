# Legacy WAR and IPMT Migration Guide

This guide explains the **migration feature** used in the GSO System for importing legacy **Work Accomplishment Report (WAR)** and **IPMT** records from Excel files into the current database-driven system.

It is written for both:

- the project team who needs to run or maintain the feature, and
- paper readers or panelists who need a clear explanation of how the migration works and why this approach was used.

---

## 1) Purpose of this guide

This document answers the following questions:

- What does the migration feature do?
- Why was this migration approach chosen?
- What files can be migrated?
- How is the migration performed in the system?
- How does the system validate and process the uploaded Excel data?
- How do users or developers run the migration commands?
- What safety controls are included to protect data integrity?
- What are the limitations of the current migration design?

---

## 2) What the migration feature means in this project

In this project, the term **migration** refers to the **transfer of legacy WAR and IPMT records from old Excel workbooks into the new GSO web system**.

This is different from Django database schema migration. The feature discussed here is a **data migration feature** designed to preserve historical records that were originally stored in spreadsheets.

The system supports two main legacy imports:

1. **WAR migration**
   - Imports old Work Accomplishment Report entries from a legacy workbook.
   - Converts each valid row into records inside the new request and WAR modules.

2. **IPMT migration**
   - Imports legacy IPMT workbook data.
   - Converts the old indicator table into structured `IPMTDraft` records in the new system.

---

## 3) Why this approach was chosen

The project team selected an **Excel import migration approach** instead of manual re-encoding for several practical reasons.

### 3.1 Preserve historical records

The office already had important historical data in spreadsheet form. Requiring users to manually re-enter all old WAR and IPMT records into the new system would be slow, error-prone, and unrealistic.

### 3.2 Reduce implementation risk

The old files were not stored in a live database that could be directly connected to the new system. Because the legacy data already existed as Excel workbooks, the most reliable approach was to build controlled import tools that understand those workbook formats.

### 3.3 Maintain traceability

The migration process stores metadata from the legacy file inside the imported records. This helps the team identify that a record came from a migration and trace it back to the original workbook source if needed.

### 3.4 Support incomplete or inconsistent legacy data

Some old records may contain office names or personnel names that do not exactly match the user accounts already created in the new system. The migration tools were designed to handle this by:

- mapping to existing users when possible,
- creating placeholder migrated users when needed, and
- skipping clearly invalid rows instead of corrupting the database.

### 3.5 Make the process safer before actual saving

The commands support **dry-run mode**, which allows the team to test the migration first and review the results without writing changes to the database.

---

## 4) High-level migration design

The migration feature was implemented as **custom Django management commands**. These commands are run from the terminal and read `.xlsx` files using Python workbook parsing.

At a high level, the process works like this:

1. The user selects a legacy Excel workbook.
2. The command opens the workbook and validates basic requirements.
3. The command reads the rows according to the expected legacy format.
4. The command tries to match unit, requestor, and personnel data to records already in the system.
5. If matching fails, the command uses controlled fallback logic.
6. The command converts legacy rows into new database records.
7. The whole operation runs inside a transaction so the migration stays consistent.
8. If the command is run in `--dry-run`, all detected actions are previewed but rolled back.

---

## 5) Commands used by the system

The project currently uses the following migration commands:

### 5.1 Core workbook migration

This command imports general migration data such as Units, Users, and Requests from an Excel workbook:

```bash
python manage.py gso_import_excel "<path-to-file>.xlsx"
```

Optional preview mode:

```bash
python manage.py gso_import_excel "<path-to-file>.xlsx" --dry-run
```

### 5.2 Legacy WAR migration

This command imports legacy WAR workbook data:

```bash
python manage.py gso_import_legacy_war "<path-to-war-file>.xlsx" --unit-code electrical
```

Optional preview mode:

```bash
python manage.py gso_import_legacy_war "<path-to-war-file>.xlsx" --unit-code electrical --dry-run
```

Optional placeholder account names:

```bash
python manage.py gso_import_legacy_war "<path-to-war-file>.xlsx" --unit-code electrical --legacy-personnel-username migrated_legacy --legacy-requestor-username migrated_requestor
```

### 5.3 Legacy IPMT migration

This command imports legacy IPMT workbook data:

```bash
python manage.py gso_import_legacy_ipmt "<path-to-ipmt-file>.xlsx" --unit-code repair
```

Optional preview mode:

```bash
python manage.py gso_import_legacy_ipmt "<path-to-ipmt-file>.xlsx" --unit-code repair --dry-run
```

Optional updater username:

```bash
python manage.py gso_import_legacy_ipmt "<path-to-ipmt-file>.xlsx" --unit-code repair --updated-by-username migrated_requestor
```

---

## 6) Prerequisites before using the migration feature

Before running the migration, the following conditions should be checked:

### 6.1 The system must already be running

The Django project must be set up properly and connected to the target database.

### 6.2 Units should already exist

The target unit code passed to the command must exist in the database, such as:

- `repair`
- `utility`
- `electrical`
- `motorpool`

If the selected unit does not exist, the migration command will stop with an error.

### 6.3 The file must be an Excel `.xlsx` file

The commands only support `.xlsx` workbooks. If a different file type is used, the command rejects it.

### 6.4 Existing users improve matching quality

If the target requestors or personnel already exist in the system, the migration can map them more accurately. If they do not exist, the system can still continue using controlled fallback accounts.

---

## 7) How to use the migration feature

This section can be used directly in the paper as the operational workflow.

### Step 1: Prepare the legacy workbook

Make sure the source file:

- is in `.xlsx` format,
- follows the expected layout of the old WAR or IPMT workbook,
- contains readable unit, office, personnel, and row data,
- is not currently corrupted or password-protected.

### Step 2: Choose the correct target unit

When running the WAR or IPMT import, the operator must provide the `--unit-code` value.

This is important because the command uses the selected unit to:

- validate whether the workbook appears to belong to the correct unit,
- limit personnel matching to the correct service unit,
- keep imported records organized under the right unit in the new database.

### Step 3: Run in dry-run mode first

The recommended first step is always:

```bash
python manage.py gso_import_legacy_war "<path-to-war-file>.xlsx" --unit-code electrical --dry-run
```

or

```bash
python manage.py gso_import_legacy_ipmt "<path-to-ipmt-file>.xlsx" --unit-code repair --dry-run
```

Dry-run mode lets the team:

- confirm the workbook can be read,
- check if the unit matches,
- review counts of records that would be created or skipped,
- detect errors before saving real data.

### Step 4: Review the summary output

After the dry-run, the command prints a summary showing what happened, such as:

- records created,
- records skipped,
- records updated,
- mapping behavior,
- errors found.

### Step 5: Run the actual migration

If the preview result looks correct, rerun the same command **without** `--dry-run`.

Example:

```bash
python manage.py gso_import_legacy_war "C:\Legacy Files\WAR_April_2025.xlsx" --unit-code electrical
```

### Step 6: Verify imported data in the system

After migration, verify the imported records in the application or admin interface.

For WAR migration, check:

- migrated requests,
- assigned personnel,
- generated WAR records,
- imported dates and cost values.

For IPMT migration, check:

- personnel match,
- period (year and month),
- imported indicator rows,
- saved `IPMTDraft` content.

---

## 8) How WAR migration works internally

WAR migration is more complex because it converts old accomplishment rows into multiple related records in the new system.

### 8.1 Expected source data

The WAR importer expects a workbook that contains rows such as:

- Date Started
- Date Completed
- Name of Activity
- Description
- Requesting Office
- Assigned Personnel
- Status
- Material Cost
- Labor Cost
- Total Cost
- Control Number

The command scans workbook sheets and looks for a recognizable header row before reading the data rows.

### 8.2 Unit detection

Before importing rows, the command scans the workbook for text that matches unit codes or unit names. If the workbook appears to belong to a different unit than the one supplied in `--unit-code`, the import is blocked.

This prevents records from being accidentally assigned to the wrong service unit.

### 8.3 Placeholder account preparation

The command ensures that fallback legacy accounts exist for use when direct mapping is not possible:

- a fallback personnel account, usually `migrated_legacy`
- a fallback requestor account, usually `migrated_requestor`

These accounts are created only when needed and are given unusable passwords so they are not treated like normal user logins.

### 8.4 Requestor matching

For each WAR row, the command reads the **Requesting Office** value and tries to match it to an existing requestor account using office/department text.

The possible outcomes are:

1. **Mapped to an existing requestor**
   - If the office text matches an existing requestor's office department.

2. **Created from office text**
   - If the office is not blank but no matching requestor exists.
   - The command creates a requestor such as `migrated_req_<office-name>`.

3. **Fallback requestor used**
   - If the office is blank.
   - The generic migrated requestor account is used.

### 8.5 Personnel matching

For each WAR row, the command reads the **Assigned Personnel** value and tries to match it to an existing personnel user in the selected unit.

The possible outcomes are:

1. **Mapped to existing personnel**
   - If the assigned name matches an existing personnel full name or username.

2. **Created from personnel name**
   - If the name is present but no user matches it.
   - The command creates a personnel account such as `migrated_per_<name>`.

3. **Fallback personnel used**
   - If the assigned personnel field is blank.
   - The generic migrated personnel account is used.

### 8.6 Row validation

A WAR row is skipped if:

- both activity and description are empty, or
- the date started value is missing or invalid.

This protects the database from meaningless or broken legacy rows.

### 8.7 Duplicate protection

Each imported row is tagged with a unique migration marker that contains:

- workbook filename,
- sheet name,
- row number.

This marker is stored in the request description so the system can detect if the same legacy row was already imported before. If the request already exists, the importer skips creating another duplicate migrated request.

### 8.8 Record creation flow

If the row is valid and not yet imported, the WAR migration command:

1. creates a completed `Request`,
2. creates a `RequestAssignment` that links the selected personnel,
3. sets the request timestamps based on the legacy dates,
4. creates a `WorkAccomplishmentReport` tied to that request and personnel,
5. stores migrated description and cost values.

In short, a single legacy WAR row is transformed into the new relational structure used by the system.

### 8.9 Result of WAR migration

After a successful WAR migration:

- the old row becomes a completed service request in the new system,
- the assigned personnel relationship is preserved,
- the accomplishment entry becomes a WAR record,
- cost and date information are kept when available,
- traceability back to the original row is preserved.

---

## 9) How IPMT migration works internally

IPMT migration is more focused on converting a structured performance worksheet into the system's draft format.

### 9.1 Expected source data

The IPMT importer reads metadata from fixed workbook positions, such as:

- unit text,
- employee name,
- month text.

It then searches for the table area that contains columns like:

- Success Indicators
- Actual Accomplishments
- Remarks or comments

### 9.2 Unit validation

The importer checks whether the workbook's unit text matches the selected `--unit-code`. If the detected unit conflicts with the selected target unit, the command stops.

### 9.3 Personnel validation

The importer tries to match the employee name from the workbook with an **active personnel account** in the selected unit.

Matching is based on:

- full name, or
- username.

If the employee cannot be mapped to a valid personnel user in that unit, the command stops with an error. This stricter behavior is used because IPMT records are directly tied to a specific personnel profile and reporting period.

### 9.4 Month and year parsing

The command extracts the month and year from the workbook text, then converts them into a normalized period such as:

- `2025-04`

### 9.5 Table parsing

After locating the indicator table, the command reads the rows underneath it and groups accomplishments by success indicator.

For each usable row:

- the indicator name is captured,
- the accomplishment text is captured,
- the comment is captured,
- grouped JSON output is prepared for saving.

Rows that do not contain valid accomplishment data are skipped.

### 9.6 Create or update behavior

The importer stores the result in `IPMTDraft`.

The record is identified by:

- personnel,
- year,
- month.

If a matching draft does not exist, the command creates one. If it already exists, the command updates it.

### 9.7 Result of IPMT migration

After a successful IPMT migration:

- the legacy IPMT sheet becomes a structured `IPMTDraft` record,
- indicator rows are preserved in JSON form,
- the draft is linked to the correct personnel and period,
- the record can be reused in the system's current workflow.

---

## 10) Safety and integrity controls

One of the most important design goals of the migration feature is to **avoid damaging the database while importing imperfect legacy data**.

The following controls are built into the commands.

### 10.1 File existence check

The command first checks whether the given file path actually exists.

### 10.2 File type check

Only `.xlsx` files are accepted.

### 10.3 Unit conflict blocking

If the workbook appears to belong to a different unit than the selected one, the import is rejected.

### 10.4 Dry-run mode

Dry-run mode allows the team to test the migration without saving permanent changes.

### 10.5 Database transaction

The import runs inside a database transaction. This means the command treats the migration as one controlled operation, which helps prevent incomplete writes when an error occurs.

### 10.6 Duplicate detection

WAR migration uses a migration marker to detect if the same row was already imported before.

### 10.7 Controlled fallback accounts

Instead of failing every time a legacy name does not match a modern account, the system uses controlled placeholder users when appropriate. This keeps historical data usable while still making the migrated nature of the record visible.

---

## 11) Why WAR and IPMT use different migration strategies

Although both use Excel import, their validation behavior is not exactly the same.

### WAR migration is more tolerant

WAR records may contain inconsistent office names and personnel names from older files. Because of this, the importer allows:

- fallback requestor creation,
- fallback personnel creation,
- generic placeholder accounts for blank values.

This is useful because WAR migration is focused on preserving legacy operational history even when old encoding was inconsistent.

### IPMT migration is stricter

IPMT records are directly tied to a specific personnel record and reporting period. For that reason, the importer requires a valid personnel match and stops when the employee cannot be resolved.

This stricter rule helps preserve the integrity of performance-related records.

---

## 12) Advantages of the current migration design

The current design provides several benefits:

- **Preserves historical data** from old spreadsheets
- **Reduces manual encoding time**
- **Improves consistency** compared with manual copying
- **Keeps traceability** to the source workbook
- **Supports safe previewing** through dry-run mode
- **Handles imperfect real-world data** through fallback logic
- **Fits the Django system architecture** without requiring a separate migration tool

---

## 13) Current limitations

The migration feature is useful, but it also has practical limitations.

### 13.1 Depends on workbook format

If the legacy workbook layout changes too much, the parser may fail or skip data.

### 13.2 Some mappings are best-effort

When office names or personnel names differ too much from current system records, the command may create fallback users instead of finding a perfect match.

### 13.3 Terminal-based operation

The commands are currently run through Django management commands, which means they are intended for developers or technical operators, not normal end users.

### 13.4 Review is still recommended

Even after a successful migration, imported records should still be reviewed, especially for:

- office mapping,
- personnel mapping,
- dates,
- costs,
- duplicate legacy files.

---

## 14) Suggested explanation for the paper

The following wording can be used directly in the paper.

### Formal explanation

The system includes a legacy data migration feature for transferring historical WAR and IPMT records from Excel workbooks into the new database-based platform. Instead of requiring manual re-encoding, the project uses custom Django management commands that parse the old spreadsheets, validate their structure and unit ownership, map legacy offices and personnel to existing system accounts, and convert the source rows into normalized database records. The migration process includes dry-run validation, duplicate protection, fallback account handling, and transactional saving to ensure data integrity while preserving historical records.

### Simpler explanation

The migration feature was built so that old WAR and IPMT Excel files could be moved into the new GSO system without encoding everything again. The system reads the workbook, checks if the file is valid, matches users and units, then converts the old spreadsheet rows into records that fit the new database structure. A preview mode is included so the team can test the migration first before saving any data.

---

## 15) Sample migration workflow for documentation or defense

This sample can be used for a methodology section or oral defense explanation.

1. Prepare the legacy WAR or IPMT Excel workbook.
2. Make sure the correct target unit already exists in the system.
3. Run the migration command in `--dry-run` mode.
4. Review the summary output and resolve any detected errors.
5. Run the same command again without `--dry-run`.
6. Verify the imported records inside the web system or admin panel.
7. Keep the original workbook as the source archive for audit and traceability.

---

## 16) Conclusion

The WAR and IPMT migration feature is an important bridge between the office's old spreadsheet-based workflow and the current web-based GSO System. It was designed to preserve legacy records, reduce re-encoding work, and transform old data into structured records that fit the new database model. By combining workbook parsing, validation, record mapping, fallback handling, duplicate control, and dry-run safety, the migration feature provides a practical and defensible way to move historical office data into the new system.
