# Request Attachment Google Drive Setup

This guide configures requestor-side request attachments to upload to Google Drive instead of local `media/` storage.

---

## 1) What this changes

When enabled, uploaded request attachments (`Request.attachment`) are:

- validated by the existing form rules (size/type/image checks),
- uploaded to a Google Drive folder via Google API,
- stored in the DB as a Drive reference plus original filename,
- still accessed through the same protected endpoint:
  - `/requests/<id>/attachment/`

Access control remains unchanged (requestor owner, same unit staff, GSO, director).

---

## 2) Prerequisites

1. A Google Cloud project
2. Google Drive API enabled
3. Google OAuth client credentials (for OAuth user mode), or service account JSON (alternative)
4. A Google Drive folder for attachments
5. If using service account mode, the Drive folder is shared with service account email (Editor)

---

## 3) Install dependencies

```bash
pip install -r requirements.txt
```

Added packages:

- `google-api-python-client`
- `google-auth`

---

## 4) Environment variables

Set these in `.env` (or deployment environment):

```env
GSO_REQUEST_ATTACHMENT_STORAGE=gdrive
GSO_GDRIVE_AUTH_MODE=oauth_user
GSO_GDRIVE_FOLDER_ID=<your_drive_folder_id>
GSO_GDRIVE_OAUTH_CLIENT_ID=<google_oauth_client_id>
GSO_GDRIVE_OAUTH_CLIENT_SECRET=<google_oauth_client_secret>
GSO_GDRIVE_OAUTH_REFRESH_TOKEN=<google_oauth_refresh_token>
```

Optional token endpoint (defaults correctly if omitted):

```env
GSO_GDRIVE_OAUTH_TOKEN_URI=https://oauth2.googleapis.com/token
```

Service-account mode (alternative):

```env
GSO_GDRIVE_AUTH_MODE=service_account
GSO_GDRIVE_SERVICE_ACCOUNT_FILE=<absolute_path_to_service_account.json>
```

Notes:

- For personal Google Drive, prefer `oauth_user`.
- Use service-account mode only with Shared Drive / Workspace-compatible setup.
- Keep credentials secret and never commit them to Git.
- If `GSO_REQUEST_ATTACHMENT_STORAGE` is unset or `local`, the app continues using local storage.

---

## 5) How to get Drive folder ID

Open the folder in Google Drive. The URL looks like:

`https://drive.google.com/drive/folders/<FOLDER_ID>`

Copy the `<FOLDER_ID>` part into `GSO_GDRIVE_FOLDER_ID`.

---

## 6) Verification checklist

1. Restart Django after changing env vars.
2. Submit a new request with an image attachment from requestor UI.
3. Confirm file appears in target Google Drive folder.
4. Open request detail and click preview/download.
5. Confirm permissions still work (unauthorized users cannot access).

---

## 7) Behavior and compatibility notes

- Existing local attachments remain readable if still present in local storage.
- New uploads go to Google Drive only when `GSO_REQUEST_ATTACHMENT_STORAGE=gdrive`.
- Attachment URLs in templates do not change because files are served through the app endpoint.

---

## 8) Troubleshooting

### `ImproperlyConfigured: GSO_GDRIVE_FOLDER_ID is required`

Set `GSO_GDRIVE_FOLDER_ID` in env.

### `ImproperlyConfigured: credentials are required`

Set credentials based on auth mode:

- `oauth_user`: set `GSO_GDRIVE_OAUTH_CLIENT_ID`, `GSO_GDRIVE_OAUTH_CLIENT_SECRET`, `GSO_GDRIVE_OAUTH_REFRESH_TOKEN`
- `service_account`: set `GSO_GDRIVE_SERVICE_ACCOUNT_FILE` or `GSO_GDRIVE_SERVICE_ACCOUNT_JSON`

### 403/404 from Google API

- Ensure Drive API is enabled in the GCP project.
- Ensure the Drive folder is shared with the service account email.
- Ensure the service account key belongs to the same project/API.

### 403 with `storageQuotaExceeded` for service account

This is expected on personal Google Drive because service accounts do not have personal storage quota.  
Use `GSO_GDRIVE_AUTH_MODE=oauth_user` or move to Shared Drive + Workspace setup.
