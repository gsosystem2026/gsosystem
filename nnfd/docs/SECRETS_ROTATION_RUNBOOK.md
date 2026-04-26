# Secrets Rotation Runbook

Use this runbook to rotate sensitive credentials safely with minimal downtime.

## Scope (rotate now)

- `DATABASE_URL` (database user/password or connection secret)
- `EMAIL_HOST_PASSWORD` (Gmail app password or SMTP secret)
- `GOOGLE_OAUTH_CLIENT_SECRET`
- `OPENROUTER_API_KEY`

## Pre-rotation safety checks

- [ ] Confirm current system is healthy (login, dashboard, key APIs).
- [ ] Confirm `.env` is not tracked in git.
- [ ] Confirm you have admin access to all provider dashboards.
- [ ] Prepare a maintenance window or low-traffic period.
- [ ] Keep old secrets active until post-rotation validation passes.

## Rotation plan (ordered)

### 1) Database secret

- [ ] Create new DB credential/secret in provider.
- [ ] Update `DATABASE_URL` in deployment secret manager.
- [ ] Update local `.env` `DATABASE_URL` if needed.
- [ ] Restart app/service using new value.
- [ ] Validate:
  - [ ] App starts without DB errors.
  - [ ] Login works.
  - [ ] Create/update request works.
- [ ] Revoke old DB credential only after successful validation.

### 2) Email secret

- [ ] Create new SMTP/Gmail app password.
- [ ] Update `EMAIL_HOST_PASSWORD` in deployment secrets and local `.env`.
- [ ] Restart app/service.
- [ ] Validate:
  - [ ] Password reset email is sent.
  - [ ] Notification email (if enabled) is sent.
- [ ] Revoke old SMTP secret.

### 3) Google OAuth secret

- [ ] Generate/rotate OAuth client secret in Google Cloud console.
- [ ] Update `GOOGLE_OAUTH_CLIENT_SECRET` in deployment secrets and local `.env`.
- [ ] Restart app/service.
- [ ] Validate:
  - [ ] Google sign-in flow completes.
  - [ ] Existing non-OAuth login still works.
- [ ] Revoke old Google OAuth secret.

### 4) OpenRouter API key

- [ ] Generate new OpenRouter key.
- [ ] Update `OPENROUTER_API_KEY` in deployment secrets and local `.env`.
- [ ] Restart app/service.
- [ ] Validate:
  - [ ] IPMT AI generation endpoint responds successfully.
  - [ ] AI error handling remains safe (no raw internals leaked).
- [ ] Revoke old OpenRouter key.

## Post-rotation validation checklist

- [ ] User login works for requestor and staff.
- [ ] Request creation/edit/notification flow works.
- [ ] Password reset OTP email works.
- [ ] Google OAuth works.
- [ ] IPMT AI generation works.
- [ ] No new errors in app logs.

## Rollback plan (if any step fails)

- [ ] Revert only the failing secret to previous value.
- [ ] Restart affected service.
- [ ] Re-test impacted flow.
- [ ] Investigate and fix provider config before retrying rotation.

## Completion record

- Rotation date:
- Rotated by:
- Environment(s):
- Old secrets revoked by:
- Final verification completed by:

