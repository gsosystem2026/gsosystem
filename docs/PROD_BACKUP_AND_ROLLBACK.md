# Production Backup and Rollback (Render + Neon)

This runbook applies the backup/rollback strategy to the deployed system.

## 1) What is automated

- Nightly logical backup (`pg_dump`) via GitHub Actions workflow:
  - `.github/workflows/nightly-neon-backup.yml`
- On-demand predeploy Neon snapshot branch via workflow:
  - `.github/workflows/neon-predeploy-snapshot.yml`

## 2) Required GitHub repository secrets

Set these in `GitHub -> Settings -> Secrets and variables -> Actions`:

- `PROD_DATABASE_URL`
  - Render production database URL (Neon connection string used by app).
- `NEON_API_KEY`
  - Neon API key with permission to create branches.
- `NEON_PROJECT_ID`
  - Neon project ID.
- `NEON_PARENT_BRANCH_ID`
  - Parent branch ID for snapshots (usually production branch, e.g. main).

## 3) Daily automated backup

Workflow: `Nightly Neon Backup`

- Runs every day at 02:00 AM Asia/Manila (18:00 UTC).
- Creates:
  - `pg_<timestamp>.dump`
  - `pg_<timestamp>.sha256`
- Uploads both as GitHub workflow artifacts (30-day retention).

## 4) Predeploy snapshot process

Before each production deploy:

1. Run workflow `Neon Predeploy Snapshot` manually.
2. Keep the returned branch details in deploy notes.
3. Deploy app to Render.
4. Run smoke test (login, create request, IPMT/WAR quick checks).

## 5) Rollback process (database)

Fast rollback (recommended):

1. In Neon, identify the latest healthy snapshot branch.
2. In Render service environment, set `DATABASE_URL` to that snapshot branch URL.
3. Redeploy/restart the Render service.
4. Verify app health.

If needed, restore from dump:

1. Download backup artifact (`.dump`) from workflow run.
2. Restore into a new Neon branch/database using `pg_restore`.
3. Point Render `DATABASE_URL` to restored target.
4. Redeploy/restart and verify.

## 6) Suggested operational targets for paper

- RPO (data loss tolerance): up to 24 hours (nightly dumps), lower when predeploy snapshot is used.
- RTO (service recovery): typically minutes for branch-switch rollback.

## 7) Notes

- Do not store backups only on web service filesystem.
- Keep secret rotation policy for database credentials and API keys.
- Periodically run restore drills and document elapsed recovery time.
