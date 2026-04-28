# Other Computer Backup Setup Kit

Use the scripts in `scripts/` on a new Windows computer to enable local auto-archive of GitHub backup artifacts.

## Before you run anything (required first)

You need a GitHub Personal Access Token (classic).  
Prepare this first, then run `RUN_SETUP.bat`.

### Which GitHub account should be used?

Use the GitHub account that can access the system repository:
- `gsosystem2026/gsosystem`

Recommended: sign in as `gsosystem2026@gmail.com` before creating the token.
If using another account, that account must be added as collaborator/member with access to the repository and Actions artifacts.

### How to create the token (click-by-click)

1. Sign in to GitHub.
2. Click your profile icon (top-right) -> **Settings**.
3. In left sidebar, open **Developer settings**.
4. Open **Personal access tokens** -> **Tokens (classic)**.
5. Click **Generate new token** -> **Generate new token (classic)**.
6. Fill:
   - **Note**: `gso-backup-artifact-sync`
   - **Expiration**: 90 days (or preferred)
7. Under scopes, check:
   - `repo`
   - `workflow`
8. Click **Generate token** (bottom page).
9. Copy the token now (it is shown only once).

Keep this token private. Do not share it in screenshots or chat.

## Files used

- `scripts\sync_github_backup_artifact.ps1`  
  Downloads the latest successful `Nightly Neon Backup` artifact from GitHub Actions.
- `scripts\register_github_artifact_sync_task.ps1`  
  Registers a daily Task Scheduler job (3:00 AM).
- `scripts\setup_new_pc_backup.ps1`  
  Interactive helper to save GitHub PAT and register the task.
- `scripts\guided_rollback_restore.ps1`  
  Guided restore tool for rollback using a `.dump` or artifact `.zip`.
- `scripts\RUN_ROLLBACK.bat`  
  Double-click launcher for guided rollback restore.
- `scripts\RUN_SETUP.bat`  
  Double-click launcher for new-PC setup.

## What this gives you

- GitHub Actions still creates cloud backup artifacts daily.
- This setup automatically downloads them daily to:
  - `%USERPROFILE%\Documents\GSO Backup`

## One-time setup on new PC

1. Copy the needed project `scripts/` folder or the listed files to the new PC.
2. Easiest for non-technical users: double-click:

- `scripts\RUN_SETUP.bat`

3. Or open PowerShell in the `scripts` folder and run manually:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ".\setup_new_pc_backup.ps1"
```

4. Follow prompts:
   - GitHub owner (default: `gsosystem2026`)
   - GitHub repo (default: `gsosystem`)
   - GitHub PAT token from the steps above (input is hidden)

## Manual test after setup

```powershell
Start-ScheduledTask -TaskName "GSO_Sync_GitHub_Backup_Artifact_Daily_3AM"
```

Then confirm files appear under:
- `C:\Users\<YourUser>\Documents\GSO Backup`

## Token requirements

Create a GitHub Personal Access Token (classic) with:
- `repo`
- `workflow`

## Non-technical rollback (guided)

1. Download backup artifact ZIP from GitHub Actions (or use local archived file).
2. In Neon, create a safe restore branch first:
   - open Neon project
   - go to **Branches**
   - click **Create branch**
   - parent branch = `production`
   - data option = **Current data**
   - branch name example = `rollback-test-2026-04-28`
3. Open the new branch and copy its direct database URL:
   - open **Connection details**
   - turn **Connection pooling OFF**
   - copy the `postgresql://...` URL
4. Double-click `scripts\RUN_ROLLBACK.bat`.
5. Enter:
   - backup file path (`.dump` or `.zip`)
   - target database URL (the direct Neon rollback branch URL)
6. Type `YES` to confirm restore.
7. After success, update Render `DATABASE_URL` to that target URL and redeploy/restart.

### Why create a branch first?

Because the branch is the safe place where the backup will be restored.
This lets you test rollback without immediately overwriting the live production database.

### Requirement for rollback tool

- `pg_restore` must be available on the computer.
- If not on PATH, set User environment variable `PG_BIN_DIR` to PostgreSQL `bin` folder.
