# Backup and rollback — GSO system

This project uses the management command **`gso_backup`** and optional platform-level backups (Supabase, Neon, etc.).

**Phased approach:** While you are **pre-production** (Neon only, not deployed), rely on **Neon’s backups** and optional **manual** `gso_backup`. After **deploy**, add **scheduled** `gso_backup` on the host and optional **off-site** sync (Google Drive, etc.). See **`MAIN_SYSTEM_AND_DEPLOYMENT_PLAN.md`** — Part 3 §3.3.

---

## What gets backed up

| Engine | Command behavior | Output files |
|--------|------------------|--------------|
| **SQLite** | Copies the DB file | `backups/db_YYYYMMDD_HHMMSS.sqlite3` |
| **PostgreSQL** | Runs **`pg_dump -Fc`** (custom format) | `backups/pg_YYYYMMDD_HHMMSS.dump` |
| **Any** | JSON export of key tables (no passwords) | `backups/data_YYYYMMDD_HHMMSS.json` |

Set **`GSO_BACKUP_DIR`** in `.env` to use a different folder (e.g. `/var/backups/gso` on Linux).

---

## Requirements

### PostgreSQL (`pg_dump`)

- Install **PostgreSQL client tools** on the machine that runs the backup (same server as the app, or a jump host with network access to the DB).
- On Windows: install from [PostgreSQL.org](https://www.postgresql.org/download/windows/) and ensure `pg_dump.exe` is on **PATH**, or use **WSL** with `postgresql-client`.
- **`DATABASE_URL`** (or Django `DATABASES`) must be correct so `pg_dump` can connect.

If `pg_dump` is missing, the command still runs **JSON export** and prints an error for the DB dump step. Use your host’s automated backups (Supabase/Neon dashboards) as a fallback.

---

## Run a backup manually

From the project root (with virtualenv activated):

```bash
python manage.py gso_backup
```

Options:

- `python manage.py gso_backup --db-only` — only SQLite copy or `pg_dump`, no JSON.
- `python manage.py gso_backup --json-only` — only JSON (works even without `pg_dump`).
- `python manage.py gso_backup --keep 10` — keep the **10** newest files **per type** (overrides env for this run).

### Automatic rotation (built in)

Each run creates **new timestamped files** (`db_*`, `pg_*`, `data_*`). After that, the command **deletes older files** so you only keep the newest **N** of each family:

| Pattern | Meaning |
|---------|---------|
| `db_*.sqlite3` | SQLite copies — up to **N** kept |
| `pg_*.dump` | Postgres dumps — up to **N** kept |
| `data_*.json` | JSON exports — up to **N** kept |

**Default N = 7.** Set **`GSO_BACKUP_KEEP=10`** in `.env` (or `5`–`10` as you prefer). Use **`--keep`** for a one-off override.

This is **better than a single “replace” file**: you keep several points in time (e.g. last week of daily runs) for rollback. For long-term archive, still copy `backups/` to another disk or cloud periodically.

---

## Schedule backups

### Monday–Friday at 5:00 PM (working days)

**Yes, this is possible.** Cron and Task Scheduler use the **computer’s local time** unless you configure otherwise — set the server (or your PC) to **Asia/Manila** if you want “5 PM Philippines time.”

**Linux/macOS — cron** (5 PM Mon–Fri):

```cron
0 17 * * 1-5 cd /path/to/GSO && /path/to/venv/bin/python manage.py gso_backup >> /var/log/gso_backup.log 2>&1
```

- `0 17` = minute **0**, hour **17** (5:00 PM).
- `1-5` = Monday through Friday (`0`/`7` = Sunday).

Add the line with `crontab -e` on the user that should run the job.

**Windows — Task Scheduler**

1. **Task Scheduler** → **Create Task…** (not Basic Task, so you can set env vars).
2. **General:** name e.g. `GSO backup Mon–Fri 5PM`; choose “Run whether user is logged on or not” if the server runs headless.
3. **Triggers** → **New…** → **Weekly** → **Recur every:** `1` **weeks** → check **Monday, Tuesday, Wednesday, Thursday, Friday** → **Start:** today’s date, time **5:00:00 PM**.
4. **Actions** → **New…** → **Start a program**  
   - Program: full path to `python.exe` (e.g. `C:\Python313\python.exe` or your venv `Scripts\python.exe`).  
   - Arguments: `manage.py gso_backup`  
   - **Start in:** your project folder (e.g. `C:\...\GSO Final System 2026`).
5. Optional: set user or system env vars **`GSO_BACKUP_KEEP`**, **`DATABASE_URL`**, etc., or rely on a **`.env`** file in the project folder (`python-dotenv` loads it when **Start in** is the project root).

That gives **one backup per working day** after hours (5 runs/week). With **`GSO_BACKUP_KEEP=10`**, you keep more than a week of files per backup type.

### Other examples

- **Linux/macOS — every day at 2:00 AM:**

  `0 2 * * * cd /path/to/GSO && /path/to/venv/bin/python manage.py gso_backup >> /var/log/gso_backup.log 2>&1`

- **Managed Postgres** — enable automatic backups in Supabase/Neon/Railway; keep **`gso_backup`** JSON + `pg_dump` files as a second layer you control.

**Retention:** Env **`GSO_BACKUP_KEEP`** (default **7**); typical range **5–10** for on-disk rotation. Archive older copies off-server (S3, NAS) if you need months of history.

---

## Rollback (restore database)

Rollback means **restore the database** to a point in time. **Test on a copy first** when possible.

### SQLite

1. Stop the Django app (or avoid writes during restore).
2. Replace `db.sqlite3` (or your configured path) with the chosen `db_*.sqlite3` backup file.
3. If the schema changed since the backup, run `python manage.py migrate` after consulting Django docs (often you restore first, then migrate forward cautiously).
4. Start the app and verify.

### PostgreSQL (custom-format dump from `gso_backup`)

1. Stop the Django app or put the site in maintenance mode.
2. **Option A — restore into the same database (destructive):**

   ```bash
   pg_restore --clean --if-exists --no-owner -d "postgresql://USER:PASS@HOST:PORT/DBNAME" backups/pg_YYYYMMDD_HHMMSS.dump
   ```

   Use the same connection string as production. `--clean` drops objects before recreating; this **wipes current data** in that database.

3. **Option B — safer:** create a **new** empty database, `pg_restore` into it, point **`DATABASE_URL`** at the new DB, test, then switch traffic.

4. Run `python manage.py migrate` if needed (usually after restore of an older dump).
5. Restart the app.

**Passwords with special characters:** put the URI in quotes or use a `.pgpass` file; see PostgreSQL documentation.

### JSON export

The JSON files are **not** a full DB restore; they are for audit, migration scripts, or partial recovery. Do not rely on JSON alone for disaster recovery if you need exact DB fidelity (constraints, auth tables, etc.).

---

## Rollback application code

If a bad deploy caused issues:

1. Redeploy the previous Git tag/commit.
2. Run `python manage.py migrate` — only applies if migrations changed between versions.
3. Restart workers/processes.

Database restore and code rollback are independent; do both only when both changed.

---

## Checklist before production

- [ ] `DATABASE_URL` set; migrations applied.
- [ ] `gso_backup` runs successfully on the server (`pg_dump` found for Postgres).
- [ ] Backups scheduled daily; `GSO_BACKUP_DIR` on disk with enough space.
- [ ] Off-site or cloud copy of `backups/` periodically.
- [ ] One person knows how to run **`pg_restore`** / SQLite file swap under stress.

---

## See also

- `MAIN_SYSTEM_AND_DEPLOYMENT_PLAN.md` — Part 3 overview.
- `python manage.py gso_backup --help`
