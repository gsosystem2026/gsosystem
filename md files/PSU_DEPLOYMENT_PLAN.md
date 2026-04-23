# PSU Deployment Plan (Campus-First + VPN for Motorpool)

**Purpose:** Final deployment playbook for your university use case:
- Most users are inside PSU (Wi-Fi/LAN).
- One key outside user group exists (motorpool driver/personnel).
- System stays private; remote access is controlled.

This document is intended for the **last phase** after feature completion and UAT.

---

## 1) Recommended Architecture

### Primary model (recommended)
- Host Django app on a **PSU on-prem server**.
- Keep DB on **Neon PostgreSQL** (already configured), or migrate DB on-prem later if policy requires.
- Make app reachable to:
  - PSU LAN/Wi-Fi users directly.
  - Off-campus motorpool personnel via **VPN** only.

### Why this model
- Keeps access mostly internal.
- Avoids exposing full app to public internet.
- Supports outside driver updates securely.
- Aligns with your current setup and team capacity.

---

## 2) Access Policy

### Campus users
- Access app via PSU network address (internal DNS or LAN IP).
- No public internet exposure required.

### Motorpool remote users
- Must connect through PSU-approved VPN (WireGuard/OpenVPN/IPSec).
- Use role-based accounts with least privilege (personnel scope only).

### Security baseline
- Enforce strong passwords and role-based permissions.
- Use HTTPS where possible (internal CA or reverse proxy cert).
- Restrict server firewall to PSU subnets + VPN subnet.

---

## 3) Connectivity Behavior (for the driver)

### Phase 1 (simple, recommended now)
- App works only when connected to PSU network or VPN.
- If driver is offline, they submit updates when connection returns.

### Phase 2 (optional future)
- Add offline queue/sync in Flutter:
  - Store pending actions locally.
  - Auto-sync when online.
  - Handle conflict resolution and sync status UI.

Do not block deployment on Phase 2.

---

## 4) Deployment Components

### App host (on-campus)
- OS: Ubuntu Server or Windows Server (stable, always-on machine).
- Runtime: Python + virtualenv.
- Web stack:
  - Preferred: Nginx + Gunicorn (Linux), or equivalent reverse proxy setup.
  - Avoid Django `runserver` in production.

### Database
- Neon PostgreSQL via `DATABASE_URL`.
- Keep connection private in env variables.
- Continue using `python manage.py gso_db_check` for validation.

### Static/media
- Run `collectstatic` on deployment.
- Serve `staticfiles/` through proxy.
- Keep `media/` with backup policy.

---

## 5) Required Environment Variables (Production)

- `DEBUG=False`
- `DJANGO_SECRET_KEY=<strong-random-secret>`
- `DATABASE_URL=<neon-postgresql-uri>`
- `ALLOWED_HOSTS=<internal-domain-or-ip>`
- `CSRF_TRUSTED_ORIGINS=https://<internal-domain>`
- `USE_TLS_BEHIND_PROXY=True` (if TLS terminated at proxy)
- Optional backup:
  - `GSO_BACKUP_DIR=<path>`
  - `GSO_BACKUP_KEEP=10`

---

## 6) Backup and Rollback in Production

- Schedule `python manage.py gso_backup` on server (e.g., Mon-Fri 5 PM).
- Keep rotation (`GSO_BACKUP_KEEP=5` to `10` typical).
- Ensure `pg_dump` exists on server PATH for PostgreSQL dumps.
- Keep an additional off-server copy (NAS/cloud) when feasible.

Reference: `BACKUP_AND_ROLLBACK.md`

---

## 7) Network and Security Checklist

- [ ] Server has static internal IP or internal DNS name.
- [ ] Firewall allows PSU subnets and VPN subnet only.
- [ ] VPN configured and tested for motorpool account.
- [ ] HTTPS configured (internal cert or trusted cert).
- [ ] Admin route access restricted (network + role).
- [ ] Logs enabled and retained (`logs/gso.log`).

---

## 8) Go-Live Runbook (Last Step)

1. Freeze code for release candidate.
2. Run final migration check and smoke tests.
3. Apply production env vars on server.
4. Run:
   - `python manage.py migrate`
   - `python manage.py collectstatic --noinput`
5. Start production service (Gunicorn + proxy).
6. Validate role flows:
   - Requestor submit/edit/cancel
   - Unit head assign/complete
   - Personnel status update
   - Notifications polling
7. Validate motorpool remote access via VPN.
8. Enable scheduled backups.
9. Document support contacts and rollback trigger policy.

---

## 9) Decision Summary (for PSU)

- **Deployment style:** Campus-first private deployment.
- **Remote access:** VPN for motorpool driver/personnel.
- **Database:** Neon PostgreSQL (current), with option to revisit later.
- **Backup:** Automated scheduled backups + rotation, then off-site copy.
- **Offline mode:** Future enhancement, not a blocker for initial launch.

