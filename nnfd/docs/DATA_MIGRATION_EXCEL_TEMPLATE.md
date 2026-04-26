# Data Migration Excel Template

Use one `.xlsx` file with these optional sheets:

- `Units`
- `Users`
- `Requests`

You can import with:

- Dry run (no database changes):  
  `python manage.py gso_import_excel "path/to/file.xlsx" --dry-run`
- Apply changes:  
  `python manage.py gso_import_excel "path/to/file.xlsx"`

If `--dry-run` reports errors, fix the Excel file first.

## Sheet: `Units`

Required columns:

- `code`
- `name`

Optional columns:

- `is_active` (`TRUE/FALSE`, `1/0`, `YES/NO`)

Example row:

- `repair | Repair and Maintenance | TRUE`

## Sheet: `Users`

Required columns:

- `username`
- `email`

Recommended columns:

- `first_name`
- `last_name`
- `role` (`REQUESTOR`, `UNIT_HEAD`, `PERSONNEL`, `GSO_OFFICE`, `DIRECTOR`)
- `unit_code` (required for `UNIT_HEAD`/`PERSONNEL`)
- `office_department` (for requestors)
- `employment_status`
- `position_title`
- `is_active`
- `account_status` (`ACTIVE`, `SUSPENDED`, `DEACTIVATED`)

Notes:

- Existing users are matched by `username` and updated.
- New users are created with unusable password (set password via invite/reset flow).

## Sheet: `Requests`

Required columns:

- `title`
- `requestor_username`
- `unit_code`

Recommended columns:

- `description`
- `location`
- `status` (`DRAFT`, `SUBMITTED`, `ASSIGNED`, `DIRECTOR_APPROVED`, `INSPECTION`, `IN_PROGRESS`, `ON_HOLD`, `DONE_WORKING`, `COMPLETED`, `CANCELLED`)
- `labor`
- `materials`
- `others`
- `is_emergency`
- `request_id` (if present and matches existing request, importer updates that record)
- `created_at` (ISO datetime, optional)
- `updated_at` (ISO datetime, optional)

Notes:

- `requestor_username` must already exist in DB or be included in `Users` sheet in the same file.
- `unit_code` must already exist in DB or be included in `Units` sheet in the same file.

## Recommended migration sequence

1. Prepare Excel file with `Units`, `Users`, then `Requests`.
2. Run dry-run and fix reported errors.
3. Apply import.
4. Run smoke checks:
   - login with migrated users
   - open Request Management
   - open Request History
   - verify sample imported requests by title/status

## Legacy WAR workbook import (monthly WAR files from old format)

For legacy WAR files like `APRIL 2025 / MAY 2025 / JUNE 2025` sheets:

`python manage.py gso_import_legacy_war "path/to/singlewar.xlsx" --unit-code electrical --dry-run`

Then apply:

`python manage.py gso_import_legacy_war "path/to/singlewar.xlsx" --unit-code electrical`

What it does:

- creates placeholder users (`migrated_legacy` personnel, `migrated_requestor` requestor) when missing
- creates completed request stubs per legacy row
- creates WAR entries linked to those requests
- adds clear migrated markers and keeps `Control #` as legacy text
- avoids duplicate imports using per-row migration markers

Optional overrides:

- `--legacy-personnel-username custom_legacy_personnel`
- `--legacy-requestor-username custom_legacy_requestor`
