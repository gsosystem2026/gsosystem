# GSO Personnel (Flutter)

Offline-capable personnel task client for the GSO Django system. This repo folder is the **Flutter app**; Django stays the source of truth on the server.

## Why Flutter here

- Reliable **SQLite** on device for queued actions (status updates, messages).
- **Connectivity** APIs without fragile browser service workers.
- One codebase for **Android** (primary) and optional **iOS**.

## What is implemented now

- Project scaffold (`gso_personnel`) with analyzer-clean code.
- **Login UI** (`lib/screens/login_screen.dart`) aligned with web `templates/registration/login.html`: gradient background, header with GSO logo, login card (username/password, visibility toggle, remember me, Sign In), Google button (opens system browser), departmental units strip, footer links. Typography via **Google Fonts — Public Sans** (same family as the web app).
- **Auth** (`lib/services/auth_repository.dart`): **JWT** `POST /api/v1/auth/token/`; tokens stored in `flutter_secure_storage`. After sign-in, **Task list** opens (`lib/screens/task_list_screen.dart`).
- **Tasks** (`lib/services/api_client.dart`): `GET /api/v1/requests/my-tasks/` and `GET /api/v1/requests/my-task-history/` (personnel-only; same filters as web Task Management). Detail: `GET /api/v1/requests/{id}/`. Work status: `POST /api/v1/requests/{id}/status/` with body `{"status": "<code>"}` (`postWorkStatus`).
- **Screens**: task list (pull-to-refresh, history nav), task detail (status actions), task history.
- **Dependencies**: `dio`, `flutter_secure_storage`, `sqflite`, `path`, `connectivity_plus`, `uuid`, `url_launcher`, `google_fonts`.
- **`lib/config/env.dart`**: API base URL via `--dart-define=GSO_API_BASE=...` (default matches production host).
- **`lib/data/outbox_database.dart`**: SQLite table `pending_ops` for mutations to sync later.

## Prerequisites

1. [Flutter SDK](https://docs.flutter.dev/get-started/install) (stable channel).
2. Android: Android Studio / SDK, USB debugging or emulator.
3. (Optional iOS): Xcode on macOS only.

Verify:

```bash
flutter doctor
```

## Run the app

```bash
cd mobile/gso_personnel
flutter pub get
flutter run --dart-define=GSO_API_BASE=https://palsugso.site
```

## Production Android build checklist

1. Install JDK 17 and set `JAVA_HOME`.
2. Generate an upload keystore (one-time):

```bash
keytool -genkey -v -keystore android/keystore/upload-keystore.jks -keyalg RSA -keysize 2048 -validity 10000 -alias upload
```

3. Create `android/key.properties` from `android/key.properties.example` and fill real values.
4. Build release APK or App Bundle:

```bash
flutter build apk --release --dart-define=GSO_API_BASE=https://palsugso.site
flutter build appbundle --release --dart-define=GSO_API_BASE=https://palsugso.site
```

Notes:
- `android/key.properties` and `*.jks` are ignored by git.
- If `key.properties` is missing, Gradle falls back to debug signing (local testing only).

## Tests

```bash
cd mobile/gso_personnel
flutter test
```

## Perfect-plan roadmap (tie to Django)

### Phase 1 — API contract (backend)

**Done for list/history/detail/status:** personnel JWT can call `RequestViewSet` actions `my-tasks`, `my-task-history`, plus standard retrieve and work-status update (aligned with web).

**Optional next:** dedicated message/chat endpoint mirroring `AddRequestMessageView`; refresh token flow on 401.

### Phase 2 — Flutter app logic

1. **Auth**: store refresh/access tokens in `flutter_secure_storage`; refresh on 401.
2. **Screens**: Login → Task list → Task detail → status chips + message field.
3. **Outbox**: on submit, if offline → `OutboxDatabase.enqueue(...)`; if online → Dio POST.
4. **Sync**: on `Connectivity` back to online + periodic timer → drain `pending_ops` FIFO with backoff.

### Phase 3 — Release

1. Bump `version` in `pubspec.yaml` per release.
2. Android: signing config in `android/app/build.gradle`; build `flutter build appbundle`.
3. Google Play Internal testing track first.

## Repo layout reminder

```
GSO Final System 2026/
  mobile/gso_personnel/     ← Flutter app (this folder)
  apps/                     ← Django apps
```

## Security

- Prefer **minimal** payloads in SQLite (ids, status enums, short message).
- Clear tokens + optional wipe `pending_ops` on logout.

For questions specific to Django API shaping, coordinate with whoever owns `apps/gso_api/`.
