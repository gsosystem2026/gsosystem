# GSO (General Services Office) System

Django backend + templates. **Develop with SQLite**, then switch to PostgreSQL (e.g. Supabase) when ready.

## Phase 1.1 – Project setup (done)

- Django project in `core/`
- Apps (all `gso_*`): `gso_accounts`, `gso_requests`, `gso_units`, `gso_inventory`, `gso_reports`, `gso_notifications`
- `requirements.txt`, `.env` for secrets

## Development (SQLite first)

Use **SQLite** by default. No database setup or extra packages needed.

```bash
# Optional: virtual environment
python -m venv .venv
.venv\Scripts\activate   # Windows

# Django only is enough for SQLite
pip install django

# Run
python manage.py migrate
python manage.py runserver
```

- Database file: `db.sqlite3` in the project root.
- Do **not** set `DATABASE_URL` in `.env` during development if you want SQLite.

Admin: http://127.0.0.1:8000/admin/ (`python manage.py createsuperuser`).

## Switching to PostgreSQL (e.g. Supabase)

When you are done developing and want to use PostgreSQL:

1. Copy `.env.example` to `.env`.
2. Set `DATABASE_URL` to your PostgreSQL URI (e.g. Supabase: Project Settings → Database → Connection string URI).
3. Install drivers and run migrations:

   ```bash
   pip install dj-database-url "psycopg[binary]"
   python manage.py migrate
   ```

Django uses the same schema on SQLite and PostgreSQL; no code changes are required. Only configuration changes.

## Optional dependencies

- `python-dotenv` – load `.env` (optional; you can set env vars manually).
- `dj-database-url` + `psycopg[binary]` – required only when using `DATABASE_URL` (PostgreSQL).

Or install everything: `pip install -r requirements.txt`

## Phase 1.2 – Authentication & roles (done)

- **Custom User** (`gso_accounts.User`) with **role**: Requestor, Unit Head, Personnel, GSO Office, Director.
- **Unit** model (`gso_units.Unit`) for linking Unit Head/Personnel to a unit (Phase 1.4 will add the 5 units).
- **Login / logout** at `/accounts/login/` and `/accounts/logout/`.
- **Password reset** (email sent to console in dev): `/accounts/password-reset/`.
- **Role-based redirect after login**: Requestor → requestor dashboard; others → staff dashboard (sidebar).
- **Dashboards**: `/accounts/staff/dashboard/`, `/accounts/requestor/dashboard/`.

**Sample users (for testing):** Run `python manage.py create_sample_users` to create the 5 units and one user per role. All passwords: **sample123**. Usernames: `requestor`, `unithead`, `personnel`, `gsooffice`, `director`. Then open http://127.0.0.1:8000/accounts/login/ and log in with any of them to see the requestor dashboard (requestor) or staff dashboard (others).

**Create users manually:** Admin at http://127.0.0.1:8000/admin/ — create a superuser with `python manage.py createsuperuser`, then edit the user to set **Role** (and **Unit** for Unit Head/Personnel).

**Note:** The custom user model required a fresh database. If you had an existing `db.sqlite3`, it was replaced when applying Phase 1.2 migrations.

## Next: Phase 1.3

Base UI (navbar, sidebar, footer), dashboard placeholders per role.
