# Backup and Rollback Implementation Walkthrough

This document explains how backup and rollback were implemented in the deployed system, from initial setup to daily operations.

---

## 1) Objective

The deployment uses Render (app hosting) and Neon (PostgreSQL).  
We implemented a practical backup + rollback process with these goals:

- create automatic daily backups,
- keep a fast rollback point before each deployment,
- maintain local long-retention copies without paid object storage.

---

## 2) Architecture Used

### Cloud side

- **GitHub Actions**: runs scheduled backup jobs.
- **Neon database**: source of production data.
- **GitHub Artifacts**: stores backup dump files (30-day retention).

### Local side

- **Windows Task Scheduler**: daily task to download latest artifact.
- **Local archive folder**: `%USERPROFILE%\Documents\GSO Backup` (long retention).

---

## 3) What We Implemented in GitHub

Two workflows were created in `.github/workflows/`:

1. `nightly-neon-backup.yml`
   - Runs daily on schedule (`cron: 0 18 * * *`, which is ~2:00 AM Asia/Manila).
   - Uses `pg_dump` via `postgres:17` Docker image.
   - Produces:
     - `pg_<timestamp>.dump`
     - `pg_<timestamp>.sha256`
   - Uploads both as GitHub Actions artifact (`retention-days: 30`).

2. `neon-predeploy-snapshot.yml`
   - Manual workflow (`workflow_dispatch`).
   - Calls Neon API to create a pre-deploy branch snapshot.
   - Snapshot is used as fast rollback point if deployment fails.

---

## 4) GitHub Secrets We Added

In **GitHub repo -> Settings -> Secrets and variables -> Actions**:

- `PROD_DATABASE_URL`  
  Production Neon connection string used for `pg_dump`.
- `NEON_API_KEY`  
  API key allowed to create Neon branches.
- `NEON_PROJECT_ID`  
  Neon project identifier.
- `NEON_PARENT_BRANCH_ID`  
  Parent branch for snapshot creation (usually production/main branch ID).

These are one-time setup values, updated only when credentials rotate.

---

## 5) Why We Changed `pg_dump` Method

Initial run failed due to version mismatch:
- server: PostgreSQL 17
- runner client: `pg_dump` 16

Fix applied:
- Instead of apt-installing client, workflow uses:
  - `docker run postgres:17 pg_dump ...`

This guarantees compatibility with Neon PG17.

---

## 6) End-to-End Backup Logic

At scheduled time:

1. GitHub Action starts runner.
2. Workflow loads `PROD_DATABASE_URL` from secrets.
3. `pg_dump -Fc` creates compressed logical backup.
4. `sha256sum` file is generated for integrity check.
5. Files are uploaded as artifact.
6. Artifact is retained for 30 days.

Result: rolling daily backup history in GitHub Actions artifacts.

---

## 7) Rollback Logic

### A) Fast rollback (recommended for bad deploy)

1. Before deployment, run `Neon Predeploy Snapshot`.
2. If issue occurs, get snapshot branch DB URL.
3. Update Render `DATABASE_URL` to snapshot branch URL.
4. Redeploy/restart service.

This provides fast restore of the last known-good database state.

### B) Restore from daily dump

If older recovery is needed:

1. Download artifact `.dump` from GitHub Actions.
2. Restore using `pg_restore` into a target database/branch.
3. Point Render `DATABASE_URL` to restored target.

---

## 7.1) Why create a Neon branch before restoring?

For non-technical explanation:

- The backup file (`.dump`) is the **old copy of the data** you want to return to.
- The Neon branch is the **safe place where you pour that old copy back in**.

Why we do this:

- It avoids overwriting production immediately.
- It lets us test first before changing the live app.
- If something is wrong, production is still untouched.

Simple analogy:

- Backup file = saved checkpoint
- Neon branch = practice area / recovery area
- Render `DATABASE_URL` switch = telling the live app to use that recovered database

---

## 7.2) How to create a safe Neon restore branch

Use this every time you want to test a rollback safely.

### Steps in Neon

1. Open the Neon project.
2. Go to **Branches**.
3. Click **Create branch**.
4. Parent branch:
   - choose `production` (or your current main/live branch)
5. Branch name:
   - example: `rollback-test-2026-04-28`
6. Data option:
   - choose **Current data**
7. Click **Create**

After branch creation:

8. Open the new branch.
9. Open **Connection details** / **Connect**.
10. Turn **Connection pooling OFF**.
11. Copy the full `postgresql://...` connection string.

Important:

- Use the **direct** connection string for rollback and migrations.
- Do **not** use the URL with `-pooler` for restore testing.

---

## 7.3) Non-technical rollback tutorial

This section is written as if guiding a non-IT personnel.

### Goal

Return the system data to an earlier backup date safely.

### What you need before starting

1. A backup file from the date you want:
   - either downloaded from GitHub Actions artifact, or
   - from local archive in `Documents\GSO Backup`
2. A new Neon restore branch (safe recovery place)
3. The rollback kit file:
   - `RUN_ROLLBACK.bat`

### Step-by-step

#### Step 1: Choose the backup date

Decide which backup you want to return to.

Example:
- If today is April 28 and you want yesterday’s data, choose the April 27 backup artifact.

#### Step 2: Create safe restore branch in Neon

Create a new branch first using the instructions in **7.2** above.

This gives you a safe place to restore the backup without damaging the live production database.

#### Step 3: Run the rollback launcher

1. Double-click:
   - `RUN_ROLLBACK.bat`
2. Enter the full path to the backup file:
   - `.dump` or downloaded `.zip`
3. Paste the direct branch `DATABASE_URL`
4. Type:
   - `YES`

The tool will:
- open the backup,
- restore it using `pg_restore`,
- prepare the selected Neon branch as the recovered database.

#### Step 4: Fix schema/search path if needed

In Neon SQL Editor for that rollback branch, run:

```sql
CREATE SCHEMA IF NOT EXISTS public;
GRANT USAGE, CREATE ON SCHEMA public TO neondb_owner;
GRANT USAGE ON SCHEMA public TO public;
ALTER DATABASE neondb SET search_path TO public;
ALTER ROLE neondb_owner SET search_path TO public;
ALTER ROLE neondb_owner IN DATABASE neondb SET search_path TO public;
```

#### Step 5: Point the live app to the restored branch

1. Open Render
2. Open the web service
3. Go to **Environment**
4. Change `DATABASE_URL` to the direct URL of the restored Neon rollback branch
5. Save changes
6. Redeploy/restart service

#### Step 6: Verify

Open the live app and check:

- login works
- dashboard opens
- requests list reflects the selected old backup state
- reports still load

If everything looks correct, rollback is successful.

---

## 7.4) Example scenario for panel explanation

Example:

- April 28: system has new incorrect data
- We want to return to April 27 nightly backup

Process:

1. Download April 27 backup artifact
2. Create Neon branch `rollback-test-2026-04-28`
3. Run `RUN_ROLLBACK.bat`
4. Restore April 27 backup into that branch
5. Change Render `DATABASE_URL` to the restored branch
6. Redeploy

Result:

- The live system now reflects April 27 backup state
- Changes made after that backup are no longer present

This is how point-in-time rollback is achieved in the implemented setup.

---

## 8) What We Run Operationally

### Before each production deploy

1. Run `Neon Predeploy Snapshot` workflow manually.
2. Deploy app to Render.
3. Run smoke tests (login, key flows).

### Daily (automatic)

- `Nightly Neon Backup` runs automatically.

### Periodic verification

- Manually check recent backup artifacts exist and are downloadable.

---

## 9) No-Cost Long Retention (Local Archive)

Because paid object storage was not enabled, we added local archive sync.

Implemented scripts:

- `scripts/sync_github_backup_artifact.ps1`
- `scripts/register_github_artifact_sync_task.ps1`

and transfer kit:

- `scripts/` launchers and helpers
- `docs/OTHER_COMPUTER_BACKUP_SETUP.md`

How it works:

1. Script calls GitHub API for latest successful backup artifact.
2. Downloads ZIP artifact.
3. Extracts to `%USERPROFILE%\Documents\GSO Backup`.
4. Prunes old local folders using retention days (default 365).

This extends retention beyond GitHub’s 30-day artifact window.

---

## 10) New Computer Setup Process

To replicate behavior on another PC:

1. Copy the needed files from `scripts/`.
2. Read `docs/OTHER_COMPUTER_BACKUP_SETUP.md`.
3. Run `scripts/RUN_SETUP.bat`.
4. Provide GitHub token (`repo` + `workflow` scopes).
5. Script saves token as user env var (`GITHUB_BACKUP_PAT`), registers scheduled task, and performs test sync.

Important:
- Use `gsosystem2026` account (or a collaborator account with access to `gsosystem2026/gsosystem`).

---

## 11) Evidence to Show Panelists

For demonstration/defense, prepare screenshots of:

1. GitHub workflow files (`nightly-neon-backup.yml`, `neon-predeploy-snapshot.yml`)
2. GitHub secrets list (names only, no values)
3. Successful snapshot run
4. Successful nightly backup run
5. Artifacts page showing `neon-pg-backup-...`
6. Local archive folder `%USERPROFILE%\Documents\GSO Backup`
7. Scheduled task entry `GSO_Sync_GitHub_Backup_Artifact_Daily_3AM`

---

## 12) Summary for Presentation

The implemented strategy combines:

- automated daily logical backups (GitHub Actions),
- pre-deploy point-in-time rollback readiness (Neon snapshot branch),
- local long-term archive sync (Task Scheduler + GitHub API),

giving practical disaster recovery coverage within a no-cost student setup.
