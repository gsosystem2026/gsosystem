# Laptop Backup Test Guide (Windows)

This guide sets up and verifies automatic local backup on your laptop, including full PostgreSQL dump support for Neon.

## Quick start (finalized flow)

Run these in order from project root:

```powershell
python manage.py gso_db_check
scripts\run_gso_backup.bat
powershell -ExecutionPolicy Bypass -File scripts\rollback_latest_backup.ps1
```

Expected result:
- `gso_db_check` shows PostgreSQL + `Connection OK`
- backup creates `pg_*.dump` and `data_*.json`
- rollback prints `Restore completed successfully.`

## 1) Prerequisites (install first)

1. **Python** is installed and works:
   ```powershell
   python --version
   ```
2. **Project dependencies** are installed:
   ```powershell
   pip install -r requirements.txt
   ```
3. **PostgreSQL client tools** are installed (required for `pg_dump`):
   - Install from PostgreSQL official installer (Windows).
   - During install, include **Command Line Tools**.
4. Add PostgreSQL `bin` folder to PATH (example):
   - `C:\Program Files\PostgreSQL\17\bin`
5. Restart terminal and verify:
   ```powershell
   pg_dump --version
   ```

If `pg_dump` is missing, JSON backup still works, but full Neon `.dump` file will not be created.

## 2) Neon connection setup

1. Open `.env` in project root and ensure `DATABASE_URL` is your Neon URI.
2. Ensure these are set:
   - `GSO_BACKUP_DIR=C:\Users\CLIENT\Desktop\GSO Final System 2026\backups`
   - `GSO_BACKUP_KEEP=10`
   - `PG_BIN_DIR=C:\Program Files\PostgreSQL\17\bin`
3. Verify Django can connect to Neon:
   ```powershell
   python manage.py gso_db_check
   ```
   Expected: engine is PostgreSQL and connection is OK.

## 3) What is already configured in this project

- Backup runner script:
  - `scripts/run_gso_backup.bat`
- Task registration script:
  - `scripts/register_gso_backup_task.ps1`
- Rollback script:
  - `scripts/rollback_latest_backup.ps1`
- Backup command used by script:
  - `python manage.py gso_backup --keep 10`

## 4) First manual backup test (required)

From project root:

```powershell
scripts\run_gso_backup.bat
```

Then check:

- `backups/` has `data_YYYYMMDD_HHMMSS.json`
- `logs/` has `backup_run_YYYYMMDD_HHMMSS.log`
- If `pg_dump` is configured, `backups/` also has `pg_YYYYMMDD_HHMMSS.dump`

## 5) Rollback test (clean setup, no manual URI copy)

The rollback script reads `.env` automatically and restores the latest `pg_*.dump`.

```powershell
powershell -ExecutionPolicy Bypass -File scripts\rollback_latest_backup.ps1
```

Optional: restore a specific file:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\rollback_latest_backup.ps1 -DumpPath "C:\Users\CLIENT\Desktop\GSO Final System 2026\backups\pg_YYYYMMDD_HHMMSS.dump"
```

## 6) Enable automatic schedule (Mon-Fri, 5:00 PM)

Run PowerShell **as Administrator** in project root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\register_gso_backup_task.ps1
```

This creates/updates the task:

- `GSO_AutoBackup_Weekdays_5PM`

## 7) Test scheduled task immediately

```powershell
Start-ScheduledTask -TaskName "GSO_AutoBackup_Weekdays_5PM"
```

Wait 5-10 seconds, then verify new files in `backups/` and `logs/`.

## 8) Troubleshooting

- **Error: `pg_dump not found`**
  - Install PostgreSQL client tools.
  - Set `PG_BIN_DIR` in `.env` (recommended).
  - Or add PostgreSQL `bin` to global PATH and restart terminal.
- **Error: `%DATABASE_URL%` not set in CMD**
  - Use the rollback script instead of direct `pg_restore` command.
  - Script reads `DATABASE_URL` from `.env`.
- **Error connecting to Neon**
  - Check `DATABASE_URL` in `.env`.
  - Run `python manage.py gso_db_check`.
  - Verify internet and Neon project status.
- **Task does not run**
  - Open Task Scheduler and check task history.
  - Ensure task user has access to project folder.
  - Run task manually once from Task Scheduler to validate.
- **No new backup files**
  - Check latest file in `logs/backup_run_*.log` for exact error.

## 9) Panel-ready statement

You can state:

- Backups are automated every weekday at 5 PM.
- Backups are stored in local drive folder.
- Retention keeps last 10 backups per type.
- JSON backup always runs.
- Full PostgreSQL dump backup runs when `pg_dump` is installed and Neon connection is valid.

## 10) Evidence checklist (for panel)

- Screenshot of `python manage.py gso_db_check` with Neon host and `Connection OK`
- Screenshot/log of `scripts\run_gso_backup.bat` success
- File proof in `backups/`:
  - `pg_YYYYMMDD_HHMMSS.dump`
  - `data_YYYYMMDD_HHMMSS.json`
- Screenshot/log of rollback script success:
  - `Restore completed successfully.`
- Optional: one data point before and after rollback (e.g., inventory quantity restored)
