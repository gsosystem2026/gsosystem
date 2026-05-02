# GSO Request Management — REST API

External systems can integrate with the GSO system via the REST API (JSON). Most endpoints require authentication using **JWT (JSON Web Tokens)** or an **integration API key** issued by the Director or GSO Office in Account Management (long-lived, for automated clients). Public endpoints (API root, unit list) stay open as documented below.

## Base URL

- Development: `http://127.0.0.1:8000/api/v1/` (or `http://localhost:8000/api/v1/`)
- Production: `https://your-domain.com/api/v1/`

## Authentication

### 1. Obtain tokens

**POST** `/api/v1/auth/token/`

Request body (JSON):

```json
{
  "username": "your_username",
  "password": "your_password"
}
```

Response:

```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

- **access**: Use in the `Authorization` header for API requests: `Authorization: Bearer <access>`
- **refresh**: Use to get a new access token when it expires (see below).

### 2. Refresh access token

**POST** `/api/v1/auth/token/refresh/`

Request body:

```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

Response:

```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

Use the new `access` token in subsequent requests.

### 3. Integration API key (automated / server-to-server)

Staff can generate a key bound to a specific **user account** (prefer a dedicated integration user with minimal role). The full secret is shown **once** when created.

Send the key on each request using either:

- `Authorization: Api-Key <full_secret>`
- or header `X-Api-Key: <full_secret>`

Access is the same as authenticating as that user with JWT (roles and row-level rules apply). Revoke keys from **Account Management → Integration API keys** for that user if leaked.

---

## Endpoints

### API root (no auth)

**GET** `/api/v1/`

Returns API name, version, and links to all endpoints.

---

### Units (read-only)

**GET** `/api/v1/units/` — List all active units (no auth required).  
**GET** `/api/v1/units/<id>/` — Retrieve one unit.

Use unit IDs when creating requests.

Response fields: `id`, `name`, `code`, `is_active`.

---

### Requests

**GET** `/api/v1/requests/` — List requests (scoped by your role: your requests, your unit, or all).  
**GET** `/api/v1/requests/<id>/` — Retrieve one request.  
**POST** `/api/v1/requests/` — Create a new request (status: Submitted). Auth required.

Query parameters for list:

- `unit` — Filter by unit ID.
- `status` — Filter by status (e.g. `SUBMITTED`, `COMPLETED`).
- `q` — Search in title, description, or request ID (numeric).
- `page` — Page number (pagination, 20 per page).

Request body for **POST** (create):

```json
{
  "unit": 1,
  "title": "Repair door",
  "description": "Room 101, main building",
  "labor": true,
  "materials": false,
  "others": false,
  "custom_full_name": "Optional",
  "custom_email": "optional@example.com",
  "custom_contact_number": "Optional"
}
```

The authenticated user becomes the **requestor**.

---

### Inventory (read-only)

**GET** `/api/v1/inventory/` — List inventory items (scoped by role: your unit or all).  
**GET** `/api/v1/inventory/<id>/` — Retrieve one item.

Query parameters for list:

- `unit` — Filter by unit ID (GSO/Director only; others see only their unit).

Response fields include: `id`, `unit`, `unit_name`, `name`, `quantity`, `unit_of_measure`, `reorder_level`, `is_low_stock`, etc.

---

## Testing the API (how to try it)

### Prerequisites

1. **Run the GSO server** (from project root):
   ```bash
   python manage.py runserver
   ```
2. **Create sample users** (if you haven’t already):
   ```bash
   python manage.py create_sample_users
   ```
   This creates users such as `requestor` / `director` with password `sample123`.

### Option A: Quick script (recommended)

From the project root:

```bash
pip install requests
python docs/test_api.py
```

The script will:

- Call `GET /api/v1/` (API root, no auth)
- Call `GET /api/v1/units/` (list units, no auth)
- Call `POST /api/v1/auth/token/` with `requestor` / `sample123`
- Call `GET /api/v1/requests/` with the JWT

If all steps succeed, the API is ready for other systems to connect.

**Override defaults** (optional):

- `GSO_API_BASE_URL` — e.g. `http://localhost:8000`
- `GSO_API_USER` — e.g. `director`
- `GSO_API_PASSWORD` — e.g. `sample123`

### Option B: Manual steps (browser + cURL)

1. **Check API root** (no auth):
   - Open in browser: [http://127.0.0.1:8000/api/v1/](http://127.0.0.1:8000/api/v1/)
   - You should see JSON with `name`, `version`, and `endpoints`.

2. **Get a JWT token** (replace username/password if needed):
   ```bash
   curl -X POST http://127.0.0.1:8000/api/v1/auth/token/ ^
     -H "Content-Type: application/json" ^
     -d "{\"username\":\"requestor\",\"password\":\"sample123\"}"
   ```
   (On Linux/macOS use `\` for line continuation and single quotes: `-d '{"username":"requestor","password":"sample123"}'`)

3. **Copy the `access` value** from the response, then list requests:
   ```bash
   curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" ^
     http://127.0.0.1:8000/api/v1/requests/
   ```

4. **Create a request** (optional):
   ```bash
   curl -X POST http://127.0.0.1:8000/api/v1/requests/ ^
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN" ^
     -H "Content-Type: application/json" ^
     -d "{\"unit\":1,\"title\":\"API test\",\"description\":\"From external system\",\"labor\":true,\"materials\":false,\"others\":false}"
   ```
   Use a valid `unit` ID from `GET /api/v1/units/`.

### Option C: Postman (or similar)

1. **New request** → GET `http://127.0.0.1:8000/api/v1/` → Send (no auth).
2. **New request** → POST `http://127.0.0.1:8000/api/v1/auth/token/`:
   - Body: raw, JSON: `{"username":"requestor","password":"sample123"}`
   - Send and copy `access` from the response.
3. **New request** → GET `http://127.0.0.1:8000/api/v1/requests/`:
   - Auth: Bearer Token → paste the `access` token → Send.

### Connecting from another system

- **Same machine / server:** Use the base URL (e.g. `http://127.0.0.1:8000` or your server host). No extra setup.
- **Browser from another origin:** If your front end runs on a different port or domain, you may need CORS. Add and configure `django-cors-headers` in the project and allow your front-end origin.
- **Other backend or script:** Send `Authorization: Bearer <access_token>` on every request. Use the refresh token to get a new access token before it expires.

---

## Example: cURL

```bash
# 1. Get token
curl -X POST http://localhost:8000/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"staff1","password":"yourpassword"}'

# 2. List requests (use the "access" value from step 1)
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  http://localhost:8000/api/v1/requests/

# 3. Create a request
curl -X POST http://localhost:8000/api/v1/requests/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"unit":1,"title":"API test","description":"From external system","labor":true,"materials":false,"others":false}'
```

---

## Status codes

- `200` — OK  
- `201` — Created  
- `400` — Bad request (validation error)  
- `401` — Unauthorized (missing or invalid token)  
- `403` — Forbidden (no permission)  
- `404` — Not found  

Errors return JSON, e.g. `{"detail": "..."}` or `{"field_name": ["error message"]}`.

---

## Quick reference for external systems

| Step | What to do |
|------|------------|
| 1 | **Get token:** `POST /api/v1/auth/token/` with `{"username":"...","password":"..."}` |
| 2 | **Use token:** Send header `Authorization: Bearer <access>` on every request (except root and units list) |
| 3 | **Refresh:** When `access` expires, `POST /api/v1/auth/token/refresh/` with `{"refresh":"<refresh>"}` to get a new `access` |

No auth needed: `GET /api/v1/`, `GET /api/v1/units/`.
