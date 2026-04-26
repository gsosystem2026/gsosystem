# Phase 9: Backup, Rollback & Security (SQLite)

This document covers backup and rollback when using **SQLite** (`db.sqlite3`). If you switch to PostgreSQL (e.g. Supabase) later, use the provider’s backup/restore and update this doc.

---

## 9.1 Backup

### What is backed up

- **SQLite file copy:** `db.sqlite3` is copied to the backup folder with a timestamp (e.g. `db_20260222_143000.sqlite3`).
- **JSON export:** Critical data (users, requests, request feedback, WAR, inventory) is exported to `data_YYYYMMDD_HHMMSS.json` for extra safety and portability. No passwords are included.

### Running backups

```bash
# Full backup (DB copy + JSON export)
python manage.py gso_backup

# SQLite file copy only
python manage.py gso_backup --db-only

# JSON export only (works with any database)
python manage.py gso_backup --json-only
```

### Backup location

- **Default:** `project_root/backups/` (created automatically).
- **Custom:** Set `GSO_BACKUP_DIR` in `.env` to an absolute path (e.g. a different drive or network folder).

### Scheduling (recommended)

- **Windows (Task Scheduler):** Create a daily task that runs `python manage.py gso_backup` (use full path to `python` and project).
- **Linux/macOS (cron):** Add a line like:
  ```cron
  0 2 * * * cd /path/to/project && python manage.py gso_backup
  ```
- Run at a time when usage is low (e.g. 2 AM).

---

## 9.2 Rollback

### Database (SQLite) restore

1. **Stop the application** (stop the Django server / gunicorn / any process using the DB).
2. **Replace the database file:**
   - Rename or move the current `db.sqlite3` (e.g. `db.sqlite3.broken`).
   - Copy the desired backup file from `backups/` (e.g. `backups/db_20260222_143000.sqlite3`) to the project root and rename it to `db.sqlite3`.
3. **Start the application again.**

Example (Windows PowerShell, from project root):

```powershell
# Stop app first, then:
Move-Item db.sqlite3 db.sqlite3.bak
Copy-Item backups\db_20260222_143000.sqlite3 db.sqlite3
# Start app
```

### Application (code) rollback

1. **Revert code** with Git:
   ```bash
   git log --oneline   # find the commit to restore
   git checkout <commit-hash>
   ```
2. **Migrations:** If you moved to an older commit that has fewer migrations, run migrations **backward** for the affected app(s):
   ```bash
   python manage.py migrate gso_requests 0004_phase5_status_and_messages
   ```
   Use the migration name that matches the commit you rolled back to. Then restart the app.

### After rollback

- Test login and key flows (request, approval, reports).
- If you only restored the DB and kept new code, ensure the schema matches (migrations are applied). If you restored old code, the DB schema should match that code.

---

## 9.3 Security checklist

### Before production

| Item | Action |
|------|--------|
| **HTTPS** | Serve the site over HTTPS (reverse proxy or load balancer). |
| **SECRET_KEY** | Set `DJANGO_SECRET_KEY` in the environment; do not use the default. |
| **DEBUG** | Set `DEBUG=False` in production (or `DEBUG=0` / `DEBUG=false` in env). |
| **ALLOWED_HOSTS** | Set `ALLOWED_HOSTS` to your domain(s), e.g. `ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com`. |
| **Database** | For SQLite: keep `db.sqlite3` out of public web root and restrict file permissions. For PostgreSQL: use a strong password and `DATABASE_URL` in env. |
| **Sensitive views** | All sensitive actions (approve, OIC assign/revoke, etc.) are protected by login and role checks. |

### Audit log

Sensitive actions are recorded in the **Audit log** (Admin → Audit logs):

- Director (or OIC) approves a request  
- Director assigns OIC  
- Director revokes OIC  

Use it to see who did what and when.

### Dependencies

- Run periodically:
  ```bash
  pip audit
  ```
  If available:
  ```bash
  pip install safety && safety check
  ```
- Update packages when security issues are reported.

---

## Switching to PostgreSQL later

When you move to Supabase (or another PostgreSQL host):

1. Set `DATABASE_URL` in `.env` to the PostgreSQL connection string.
2. Install: `pip install dj-database-url "psycopg[binary]"`.
3. Run `python manage.py migrate` on the new database (you can load data from the JSON backup or migrate from SQLite with a one-time script).
4. Use the provider’s backup/restore for the database; keep using `python manage.py gso_backup --json-only` for data export if you want.
