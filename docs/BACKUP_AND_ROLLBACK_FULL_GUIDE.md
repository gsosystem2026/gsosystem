# Backup and Rollback Full Guide

This document is a complete explanation of how backup and rollback were implemented for the deployed GSO System. It is written to help the project team fully understand the design, the tools used, the setup process, and how recovery works in real use.

---

## 1) Purpose of this guide

This guide answers the following questions:

- What is our backup and rollback strategy?
- What technologies do we use?
- Why did we choose those technologies?
- How was the setup done?
- How does the automatic backup work every day?
- How does rollback work when we need to return to an older state?
- What are the limitations of the current setup?
- How can this be explained clearly to panelists or non-technical users?

---

## 2) High-level summary

Our deployed system uses:

- **Render** for hosting the Django web application
- **Neon** for the PostgreSQL production database
- **GitHub Actions** for automated daily backup
- **GitHub Artifacts** for storing daily backup files
- **Windows Task Scheduler** for downloading long-term local backup copies
- **PowerShell + batch files** for simplified local setup and guided recovery

In simple terms:

1. Every day, GitHub automatically creates a database backup file.
2. That backup file is stored in GitHub Actions artifacts.
3. A local PC can automatically download and archive those backups.
4. If rollback is needed, a chosen backup file can be restored into a safe Neon branch.
5. The live Render app can then be pointed to that restored branch.

---

## 3) Core concepts

Before going into the setup, it is important to understand three concepts.

### 3.1 Backup

A **backup** is a saved copy of the database at a certain point in time.

In this system, the daily backup is a PostgreSQL dump file:

- `.dump`

This file contains the database structure and data at the time the backup was created.

### 3.2 Rollback

A **rollback** means returning the system to an earlier backup state.

Example:

- If the database becomes corrupted today,
- and yesterday’s backup is still good,
- we can restore yesterday’s backup and make the system use that recovered data.

### 3.3 Recovery target

A **recovery target** is where the restored backup is placed.

In our setup, we usually restore to a **Neon branch**, not directly to production at first.

This gives a safe testing area before changing the live system.

---

## 4) Tech stack used for backup and rollback

### 4.1 Render

Render hosts the Django application.

Why we use it:

- easy deployment
- managed web hosting
- environment variable support
- works well with Django

Role in backup/rollback:

- The app runs on Render.
- When rollback is needed, Render is updated to use a different `DATABASE_URL`.

### 4.2 Neon

Neon hosts the PostgreSQL database.

Why we use it:

- managed PostgreSQL
- easy cloud access
- branch-based workflow
- good fit for testing and rollback

Role in backup/rollback:

- production database lives in Neon
- rollback test branches are created in Neon
- restored backup data is loaded into Neon branches

### 4.3 GitHub Actions

GitHub Actions is used for automation.

Why we use it:

- free enough for student-friendly automation
- already connected to the code repository
- can run scheduled workflows

Role in backup/rollback:

- automatically runs the daily backup workflow
- can also create predeploy snapshot branches

### 4.4 GitHub Artifacts

Artifacts are files attached to a workflow run.

Why we use them:

- easy built-in storage for workflow outputs
- no extra paid cloud object storage required

Role in backup/rollback:

- stores the generated `.dump` backup file
- stores the `.sha256` integrity hash file

### 4.5 Local Windows automation

We also use:

- PowerShell scripts
- `.bat` launchers
- Task Scheduler

Why we use them:

- easy for Windows users
- allows local retention beyond GitHub’s 30-day artifact limit
- makes setup easier for non-technical users

---

## 5) Why this strategy was chosen

We needed a backup and rollback approach that is:

- practical for a student project
- low-cost
- usable without paid enterprise tooling
- easy to demonstrate
- understandable by non-technical personnel

The chosen strategy is a hybrid approach:

### Daily backup

Use GitHub Actions to create automated daily PostgreSQL dump backups.

### Fast rollback safety

Use Neon branches as safe restore targets and pre-deploy rollback points.

### Long retention

Use local archive sync to keep copies longer than GitHub artifact retention.

This gives a good balance of:

- automation
- safety
- affordability
- explainability

---

## 6) Files we created for this system

### GitHub workflow files

- `.github/workflows/nightly-neon-backup.yml`
- `.github/workflows/neon-predeploy-snapshot.yml`

### Project scripts

- `scripts/sync_github_backup_artifact.ps1`
- `scripts/register_github_artifact_sync_task.ps1`

### Portable setup and recovery files

- `scripts/RUN_SETUP.bat`
- `scripts/setup_new_pc_backup.ps1`
- `scripts/sync_github_backup_artifact.ps1`
- `scripts/register_github_artifact_sync_task.ps1`
- `scripts/RUN_ROLLBACK.bat`
- `scripts/guided_rollback_restore.ps1`
- `docs/OTHER_COMPUTER_BACKUP_SETUP.md`

### Documentation

- `docs/OTHER_COMPUTER_BACKUP_SETUP.md`
- `docs/BACKUP_IMPLEMENTATION_WALKTHROUGH.md`
- `docs/BACKUP_AND_ROLLBACK_FULL_GUIDE.md` (this file)

---

## 7) GitHub backup workflow setup

### 7.1 What the nightly workflow does

The nightly workflow:

1. starts on a daily schedule
2. reads the production database URL from GitHub secrets
3. runs `pg_dump`
4. creates a `.dump` backup file
5. creates a `.sha256` hash file
6. uploads both as an artifact

### 7.2 Schedule used

The cron schedule is:

```text
0 18 * * *
```

GitHub uses UTC time.

That means:

- `18:00 UTC`
- which is about `2:00 AM Asia/Manila`

So the backup runs automatically around **2:00 AM Philippine time every day**.

### 7.3 Why the artifact count shows “1”

Each workflow run produces **one artifact bundle**.

So every successful run page shows:

- `Artifacts: 1`

This does not mean there is only one backup total.  
It means that specific run created one backup package.

The list of multiple days is visible in the workflow run history.

---

## 8) GitHub secrets used

The following GitHub Actions secrets were configured:

- `PROD_DATABASE_URL`
- `NEON_API_KEY`
- `NEON_PROJECT_ID`
- `NEON_PARENT_BRANCH_ID`

### What each one does

#### `PROD_DATABASE_URL`

Used by the nightly backup workflow to connect to the production database and create the backup.

#### `NEON_API_KEY`

Used by the snapshot workflow to call the Neon API and create a branch automatically.

#### `NEON_PROJECT_ID`

Identifies which Neon project the workflow should work with.

#### `NEON_PARENT_BRANCH_ID`

Tells Neon which branch should be used as the parent for snapshots.

---

## 9) Why the workflow uses Docker `postgres:17`

During setup, the first backup attempt failed because:

- Neon server version was PostgreSQL 17
- GitHub runner client was using PostgreSQL 16 `pg_dump`

This caused a version mismatch error.

To fix that, the workflow was changed to use:

```text
postgres:17
```

through Docker.

Why this is better:

- exact version match
- no package repository issues
- more reliable in GitHub runners

---

## 10) Where backups are stored

### Cloud location

Backups are first stored as **GitHub Actions artifacts**.

This means:

- they are not stored on Render
- they are not stored in Neon as files
- they are not stored automatically in local PC folders

### Retention

The workflow uses:

- `retention-days: 30`

So the artifacts are kept for about 30 days, then older ones expire automatically.

### Local long-term archive

To extend retention without paid object storage, the latest artifacts can also be downloaded automatically to:

- `%USERPROFILE%\Documents\GSO Backup`

This is handled by the local sync scripts and Task Scheduler.

---

## 11) How local long-term backup archiving works

### Why local archiving was added

GitHub artifact storage is useful, but it is not ideal for long-term historical retention because:

- artifacts expire automatically
- GitHub is not the final archival location

So local auto-download was added.

### Logic used

The local sync script:

1. calls GitHub API
2. finds the latest successful `Nightly Neon Backup` run
3. downloads the latest artifact ZIP
4. extracts it to `Documents\GSO Backup`
5. keeps archive folders for up to the configured retention period

### Local setup behavior

This local auto-download runs via Windows Task Scheduler every day at:

- `3:00 AM`

That is after the GitHub backup is expected to complete.

---

## 12) Why `GITHUB_BACKUP_PAT` is needed

The local sync script needs a GitHub token so it can access Actions artifacts through GitHub API.

This token is stored as a user environment variable:

- `GITHUB_BACKUP_PAT`

Important:

- it is set once per computer
- it does not automatically transfer to another PC
- each PC that wants local archive sync needs its own setup

That is why the other-computer setup kit asks for a token.

---

## 13) Other-computer setup logic

The portable setup and recovery files in `scripts/` plus the guide in `docs/OTHER_COMPUTER_BACKUP_SETUP.md`
were prepared so the backup archive feature can be moved easily to another computer.

### What the setup kit does

When the user runs:

- `RUN_SETUP.bat`

the system:

1. launches PowerShell setup
2. asks for GitHub owner/repo
3. asks for GitHub token
4. saves `GITHUB_BACKUP_PAT`
5. registers the daily archive sync task
6. runs one test sync immediately

### Why this is useful

- non-technical friendly
- avoids manual Task Scheduler configuration
- simplifies migration to another PC

---

## 14) Rollback strategy used

We use two rollback-related approaches:

### 14.1 Fast rollback for deployment safety

This uses a Neon snapshot branch created before deployment.

Purpose:

- recover quickly if a deploy breaks the app

### 14.2 Historical rollback using backup file

This uses a chosen daily `.dump` backup file.

Purpose:

- return to a specific earlier day or backup point

---

## 15) Difference between backup file and Neon branch

This is one of the most important concepts.

### Backup file

The backup file is:

- the **old saved state**
- the data you want to return to

### Neon branch

The Neon branch is:

- the **safe place to restore into**
- the target where you load the old backup

Simple analogy:

- backup file = old photo / checkpoint
- Neon branch = table where you place and inspect that old copy
- Render `DATABASE_URL` switch = telling the app to use that restored copy

---

## 16) Why we restore to a branch first

We do not restore directly to production first because:

- it is risky
- mistakes could overwrite live data
- it is harder to test safely

By restoring to a branch first:

- production remains untouched until verified
- rollback process can be demonstrated safely
- non-technical operators can follow safer steps

---

## 17) How to create a safe Neon restore branch

### Step-by-step

1. Open Neon
2. Open the project
3. Go to **Branches**
4. Click **Create branch**
5. Parent branch:
   - choose `production`
6. Branch name:
   - example: `rollback-test-2026-04-28`
7. Data option:
   - choose **Current data**
8. Click **Create**

After branch creation:

9. Open the new branch
10. Open **Connection details**
11. Turn **Connection pooling OFF**
12. Copy the direct `postgresql://...` URL

This direct branch URL is used for restore and testing.

---

## 18) Why direct URL is important

Neon gives two connection types:

### Pooled URL

- contains `-pooler`
- good for general app connection pooling
- not ideal for rollback restore and migrations in our case

### Direct URL

- does not contain `-pooler`
- better for `pg_restore`
- better for migrations
- avoids schema/search_path problems seen during testing

For rollback and migration testing, we use the **direct URL**.

---

## 19) Guided rollback tool

The rollback tool for non-technical users is:

- `RUN_ROLLBACK.bat`

This launches:

- `guided_rollback_restore.ps1`

### What it asks for

1. backup file path (`.dump` or artifact `.zip`)
2. target `DATABASE_URL`
3. confirmation (`YES`)

### What it does

1. opens the chosen backup
2. extracts `.dump` if a ZIP was provided
3. runs `pg_restore`
4. restores the backup into the selected target database
5. tells the user the next Render step

---

## 20) Schema fix that may be needed after restore

During testing, restore succeeded but Django migrations failed because:

- no schema had been selected to create in

To fix this, the following SQL was used on the restore branch:

```sql
CREATE SCHEMA IF NOT EXISTS public;
GRANT USAGE, CREATE ON SCHEMA public TO neondb_owner;
GRANT USAGE ON SCHEMA public TO public;
ALTER DATABASE neondb SET search_path TO public;
ALTER ROLE neondb_owner SET search_path TO public;
ALTER ROLE neondb_owner IN DATABASE neondb SET search_path TO public;
```

This ensures Django can create or access schema objects correctly.

---

## 21) Example rollback scenario

Example:

- Today is April 28
- Bad data was created today
- We want to go back to April 27 backup

### Process

1. Download the April 27 artifact from GitHub Actions
2. Create Neon branch `rollback-test-2026-04-28`
3. Turn off connection pooling and copy direct URL
4. Run `RUN_ROLLBACK.bat`
5. Provide the April 27 backup and the branch URL
6. Run schema fix SQL if needed
7. Change Render `DATABASE_URL` to that branch URL
8. Redeploy

### Result

- Live app now reflects the April 27 data state
- Changes made after that backup are no longer present

That is how “rollback to yesterday” is performed.

---

## 22) How to use rollback directly on main production

This is possible, but not the recommended first step.

Safe order:

1. create a safety snapshot of production
2. use direct production URL
3. restore backup to production
4. fix schema/search_path if needed
5. redeploy Render

Why this is riskier:

- production is overwritten directly
- less room for testing

That is why branch-first restore is safer.

---

## 23) What we tested successfully

The following were successfully implemented and tested:

### Backup

- GitHub workflow runs manually and on schedule
- backup artifact is created successfully
- artifact can be downloaded
- local archive sync works

### Rollback

- backup artifact `.zip` was restored successfully using the rollback tool
- restore into a Neon branch worked
- direct connection usage improved restore/migration compatibility
- schema/search_path fix was identified and applied

---

## 24) Limitations of the current setup

Although the system is functional, some limitations still exist.

### 24.1 GitHub artifact retention

- default backup artifact retention is about 30 days
- longer history depends on local archive sync

### 24.2 Manual confirmation still needed

Rollback is guided, but not fully automatic.

User still needs to:

- choose the correct backup file
- choose the target database URL
- update Render `DATABASE_URL`

### 24.3 Schema/search_path handling

Some restore cases may require manual SQL fix after `pg_restore`.

### 24.4 Direct vs pooled connection awareness

Operators must understand that rollback and migrations should use the **direct** URL, not pooled URL.

---

## 25) Why this design is still strong for a student system

This approach is strong because it demonstrates:

- automation
- disaster recovery planning
- rollback control
- non-technical operational support
- cross-device setup portability

It is also realistic for a student budget because it avoids needing paid enterprise backup tools.

---

## 26) Suggested explanation to panelists

Short explanation:

> The system uses GitHub Actions to automatically create a PostgreSQL backup every day and store it as an artifact. We also implemented a rollback process that restores a selected backup into a safe Neon branch, then switches the live Render application to that recovered database by updating the `DATABASE_URL`. To extend retention without paid storage, a local scheduled task downloads artifacts to a `Documents\GSO Backup` archive folder. This design provides daily backup, safe rollback testing, and low-cost disaster recovery.

---

## 27) Suggested evidence for defense

Prepare screenshots of:

1. `Nightly Neon Backup` workflow runs
2. `via Schedule` successful run
3. artifact list showing `neon-pg-backup-...`
4. GitHub secrets names
5. Neon rollback branch creation
6. rollback restore success window
7. local `Documents\GSO Backup` folder
8. scheduled task entry on Windows

---

## 28) Final conclusion

The implemented backup and rollback system is a layered recovery design:

- **Daily backup** through GitHub Actions
- **Safe restoration target** through Neon branches
- **Guided recovery** through rollback scripts and batch files
- **Longer retention** through local archive sync

This makes the system recoverable, explainable, and practical for both technical and non-technical operators.
