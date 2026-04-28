from __future__ import annotations

import io
import json
import os
from typing import Optional

from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import File
from django.core.files.storage import FileSystemStorage, Storage
from django.utils.deconstruct import deconstructible
from django.utils.text import get_valid_filename


def _split_stored_name(name: str) -> tuple[str, str]:
    """
    Stored format: "<file_id>::<original_filename>".
    Fallback for legacy values that only contain the file id.
    """
    if "::" in name:
        file_id, original_name = name.split("::", 1)
        return file_id.strip(), original_name.strip() or file_id.strip()
    return name.strip(), name.strip()


@deconstructible
class GoogleDriveStorage(Storage):
    """
    Minimal Django storage backend for Google Drive.

    Files are uploaded to a configured Drive folder and the DB stores:
    "<file_id>::<original_filename>".

    Supported auth modes:
    - service_account (default)
    - oauth_user (recommended for personal Google Drive)
    """

    def __init__(
        self,
        folder_id: Optional[str] = None,
        credentials_file: Optional[str] = None,
        credentials_json: Optional[str] = None,
    ):
        self.folder_id = folder_id or os.environ.get("GSO_GDRIVE_FOLDER_ID", "").strip()
        self.auth_mode = (os.environ.get("GSO_GDRIVE_AUTH_MODE") or "service_account").strip().lower()
        self.credentials_file = credentials_file or os.environ.get("GSO_GDRIVE_SERVICE_ACCOUNT_FILE", "").strip()
        self.credentials_json = credentials_json or os.environ.get("GSO_GDRIVE_SERVICE_ACCOUNT_JSON", "").strip()
        self._service = None

    def _get_service(self):
        if self._service is not None:
            return self._service

        if not self.folder_id:
            raise ImproperlyConfigured("GSO_GDRIVE_FOLDER_ID is required for Google Drive attachment storage.")

        try:
            from googleapiclient.discovery import build
        except ImportError as exc:
            raise ImproperlyConfigured("Missing dependency: google-api-python-client") from exc

        scopes = ["https://www.googleapis.com/auth/drive.file"]
        if self.auth_mode == "oauth_user":
            try:
                from google.oauth2.credentials import Credentials
            except ImportError as exc:
                raise ImproperlyConfigured("Missing dependency: google-auth") from exc

            client_id = os.environ.get("GSO_GDRIVE_OAUTH_CLIENT_ID", "").strip()
            client_secret = os.environ.get("GSO_GDRIVE_OAUTH_CLIENT_SECRET", "").strip()
            refresh_token = os.environ.get("GSO_GDRIVE_OAUTH_REFRESH_TOKEN", "").strip()
            token_uri = os.environ.get("GSO_GDRIVE_OAUTH_TOKEN_URI", "https://oauth2.googleapis.com/token").strip()
            if not client_id or not client_secret or not refresh_token:
                raise ImproperlyConfigured(
                    "OAuth user credentials are required for GSO_GDRIVE_AUTH_MODE=oauth_user. "
                    "Set GSO_GDRIVE_OAUTH_CLIENT_ID, GSO_GDRIVE_OAUTH_CLIENT_SECRET, "
                    "and GSO_GDRIVE_OAUTH_REFRESH_TOKEN."
                )
            creds = Credentials(
                token=None,
                refresh_token=refresh_token,
                token_uri=token_uri,
                client_id=client_id,
                client_secret=client_secret,
                scopes=scopes,
            )
        else:
            try:
                from google.oauth2 import service_account
            except ImportError as exc:
                raise ImproperlyConfigured("Missing dependency: google-auth") from exc

            if self.credentials_json:
                info = json.loads(self.credentials_json)
                creds = service_account.Credentials.from_service_account_info(info, scopes=scopes)
            elif self.credentials_file:
                creds = service_account.Credentials.from_service_account_file(self.credentials_file, scopes=scopes)
            else:
                raise ImproperlyConfigured(
                    "Service-account credentials are required for GSO_GDRIVE_AUTH_MODE=service_account. "
                    "Set GSO_GDRIVE_SERVICE_ACCOUNT_FILE or GSO_GDRIVE_SERVICE_ACCOUNT_JSON."
                )

        self._service = build("drive", "v3", credentials=creds, cache_discovery=False)
        return self._service

    def _save(self, name, content):
        service = self._get_service()
        file_name = get_valid_filename(os.path.basename(name) or "upload.bin")
        file_metadata = {"name": file_name, "parents": [self.folder_id]}

        content.seek(0)
        raw = content.read()
        body = io.BytesIO(raw)

        from googleapiclient.http import MediaIoBaseUpload

        media = MediaIoBaseUpload(
            body,
            mimetype=getattr(content, "content_type", None) or "application/octet-stream",
            resumable=False,
        )
        created = (
            service.files()
            .create(body=file_metadata, media_body=media, fields="id,name")
            .execute()
        )
        file_id = created["id"]
        return f"{file_id}::{file_name}"

    def _open(self, name, mode="rb"):
        service = self._get_service()
        file_id, file_name = _split_stored_name(name)

        from googleapiclient.http import MediaIoBaseDownload

        request = service.files().get_media(fileId=file_id)
        out = io.BytesIO()
        downloader = MediaIoBaseDownload(out, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        out.seek(0)
        return File(out, name=file_name)

    def delete(self, name):
        service = self._get_service()
        file_id, _ = _split_stored_name(name)
        try:
            service.files().delete(fileId=file_id).execute()
        except Exception:
            # Delete should be best-effort to match Django storage behavior.
            return

    def exists(self, name):
        service = self._get_service()
        file_id, _ = _split_stored_name(name)
        try:
            service.files().get(fileId=file_id, fields="id").execute()
            return True
        except Exception:
            return False

    def size(self, name):
        service = self._get_service()
        file_id, _ = _split_stored_name(name)
        try:
            data = service.files().get(fileId=file_id, fields="size").execute()
            return int(data.get("size") or 0)
        except Exception:
            return 0

    def url(self, name):
        # Access is controlled through app permissions using RequestAttachmentView.
        return ""


def get_request_attachment_storage():
    backend = (os.environ.get("GSO_REQUEST_ATTACHMENT_STORAGE") or "local").strip().lower()
    if backend == "gdrive":
        return GoogleDriveStorage()
    return FileSystemStorage()
