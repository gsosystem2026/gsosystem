# GSO template structure

## Layouts

- **`base.html`** – Root base (minimal). Used by login and as parent for both layouts.
- **`layouts/base_staff.html`** – **Staff UI with sidebar.** Used by **Unit Head, Personnel, GSO Office, Director** (same base; role-based menu later).
- **`layouts/base_requestor.html`** – **Requestor UI** (Tailwind CDN, Public Sans, Material Symbols; header with search/notifications, no sidebar). Standalone HTML (does not extend `base.html`).

## Folders

| Folder       | Purpose |
|-------------|---------|
| `layouts/`  | Base templates: `base_staff.html`, `base_requestor.html`. |
| `includes/` | Reusable fragments: `sidebar_staff.html`, `header_staff.html`, `footer_staff.html`. |
| `staff/`    | Pages that extend `layouts/base_staff.html` (dashboard, requests, inventory, reports, etc.). |
| `requestor/`| Pages that extend `layouts/base_requestor.html` (dashboard, my requests, new request). |

## Usage

- **Staff (Unit Head, Personnel, GSO Office, Director):**  
  `{% extends "layouts/base_staff.html" %}` and fill `{% block staff_content %}`.
- **Requestor:**  
  `{% extends "layouts/base_requestor.html" %}` and fill `{% block requestor_content %}`.

## Block names

- **base.html:** `title`, `body_class`, `content`, `extra_css`, `extra_js`
- **base_staff.html:** `staff_content`, `header_title`
- **base_requestor.html:** `title`, `requestor_content`, `extra_css`, `extra_js`
