# Render / Railway Deployment Setup (Including Google OAuth)

This guide lists all changes/config needed when moving the current system from local to Render or Railway.

---

## 1) Required Environment Variables (Set in Platform Dashboard)

Set these in Render/Railway service variables:

- `DEBUG=False`
- `DJANGO_SECRET_KEY=<strong-random-secret>`
- `DATABASE_URL=<platform/neon postgres url>`
- `ALLOWED_HOSTS=<your-app-domain>`
- `CSRF_TRUSTED_ORIGINS=https://<your-app-domain>`
- `GSO_SITE_URL=https://<your-app-domain>`
- `USE_TLS_BEHIND_PROXY=True`

Email / notifications:

- `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`
- `EMAIL_HOST=smtp.gmail.com`
- `EMAIL_PORT=587`
- `EMAIL_HOST_USER=<gmail>`
- `EMAIL_HOST_PASSWORD=<gmail-app-password>`
- `EMAIL_USE_TLS=True`
- `EMAIL_USE_SSL=False`
- `DEFAULT_FROM_EMAIL=GSO System <<gmail>>`
- `GSO_EMAIL_NOTIFICATIONS_ENABLED=True`
- `GSO_INVITE_LINK_TIMEOUT_SECONDS=86400` (optional; default 24h)

Important for new account creation:

- Director-created users now receive an email invitation to set their password.
- This requires working SMTP settings in production (`EMAIL_*` + `DEFAULT_FROM_EMAIL` + valid `GSO_SITE_URL`).
- If email is misconfigured, user account may be created but invite delivery will fail.
- Account Management uses lifecycle statuses (`Active`, `Suspended`, `Deactivated`). Suspended/deactivated users are blocked at login.
- Requestor accounts require an **Office/Department**. This is separate from GSO service units (Repair, Electrical, Utility, Motorpool).

Google OAuth:

- `GOOGLE_OAUTH_CLIENT_ID=<google-client-id>`
- `GOOGLE_OAUTH_CLIENT_SECRET=<google-client-secret>`

Backup options (if enabled in cloud host):

- `GSO_BACKUP_DIR=<writable-path>`
- `GSO_BACKUP_KEEP=10`

---

## 2) Domain-Specific Values (Render vs Railway)

Use your actual deployed URL:

- Render example: `https://your-service.onrender.com`
- Railway example: `https://your-app.up.railway.app`

Apply that same domain to:

1. `ALLOWED_HOSTS`
2. `CSRF_TRUSTED_ORIGINS`
3. `GSO_SITE_URL`

---

## 3) Google OAuth: What Must Be Changed for Deployment

In Google Cloud Console -> OAuth Client -> Authorized redirect URIs, add:

- `https://<your-app-domain>/accounts/social/google/login/callback/`

Keep local URIs too if you still test locally:

- `http://127.0.0.1:8000/accounts/social/google/login/callback/`
- `http://localhost:8000/accounts/social/google/login/callback/`

### Important system behavior already enforced

- Google login is allowed only when Gmail matches an existing active account in your system.
- If no matching account exists, login is blocked.

---

## 4) Django Site Domain (allauth / sites framework)

After first deploy, set `django_site` domain to deployed domain (important for auth links).

Run once:

```bash
python manage.py shell -c "from django.contrib.sites.models import Site; s=Site.objects.get(pk=1); s.domain='<your-app-domain>'; s.name='GSO'; s.save(); print(s.domain)"
```

Use domain only (no `https://`) in `Site.domain`.

Example:

- `your-service.onrender.com`
- `your-app.up.railway.app`

---

## 5) Build / Start Commands

Minimum production-safe approach:

- Build command:
  - `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`
- Start command:
  - `gunicorn core.wsgi:application --bind 0.0.0.0:$PORT`

If `gunicorn` is not yet in `requirements.txt`, add it before go-live.

---

## 6) Post-Deploy Smoke Test (Must Pass)

1. Open login page over deployed URL.
2. Username/password login works.
3. Continue with Google works for pre-created email.
4. Google login blocks non-existing email (expected).
5. Forgot password OTP email sends.
6. Request lifecycle sends in-app + email notifications.
7. Static files load correctly (styles/icons/logo).
8. Add User sends invitation email and invited user can open link and set password.
9. Account Management: edit user modal works; requestor Office/Department saves; OIC assign/revoke works.
10. Account lifecycle: suspend/deactivate blocks login; reinstate/reactivate restores login.

---

## 7) Quick Rollback Safety

Before major deploy updates:

1. Run backup (`gso_backup`) and verify output.
2. Keep latest DB dump.
3. Only then apply migrations.

---

## 8) Common Deployment Mistakes

- `GSO_SITE_URL` still set to localhost.
- Missing production callback URI in Google console.
- `CSRF_TRUSTED_ORIGINS` missing `https://` prefix.
- `django_site` still set to `example.com`.
- Wrong Gmail app password or blocked SMTP.
- `GSO_SITE_URL` not set to the live HTTPS domain (invite links become wrong).
- Forgetting to run migrations after deploy (`office_department` and account lifecycle fields must exist).

---

## 9) Final Checklist Before Announcing Live

- [ ] All required env vars set in platform.
- [ ] Google callback URI added for deployed domain.
- [ ] `django_site` domain updated.
- [ ] Migrations + collectstatic completed.
- [ ] Auth flows validated (password + Google).
- [ ] Notification emails validated.
- [ ] Add User invitation email validated.
- [ ] Account lifecycle validated (suspend/deactivate/reactivate + login block).
- [ ] Backup policy enabled.

