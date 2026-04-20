# GSO Mobile

Flutter mobile app for the GSO (General Services Office) system. Connects to the Django backend via REST API.

## Prerequisites

- [Flutter SDK](https://docs.flutter.dev/get-started/install) installed and in PATH
- Django backend running (e.g. `http://127.0.0.1:8000`)

## Setup

1. **Ensure Flutter is installed** and in your PATH: `flutter doctor`

2. **Add/update platform support** (generates gradle wrapper, launcher icons, etc.):

   ```bash
   cd gso_mobile
   flutter create . --project-name gso_mobile
   ```

3. **Install dependencies**:

   ```bash
   flutter pub get
   ```

4. **Run the app**:

   ```bash
   flutter run
   ```

   Use an Android emulator or connected device. Ensure the Django backend is running.

## API URL

Edit `lib/core/config.dart` to set your backend URL:

- **Android emulator:** `http://10.0.2.2:8000/api/v1/` (10.0.2.2 = host localhost)
- **iOS simulator:** `http://127.0.0.1:8000/api/v1/`
- **Real device:** Use your machine's LAN IP, e.g. `http://192.168.1.x:8000/api/v1/`

## Phase 1 Complete

- Project structure
- API client with JWT auth + refresh
- Auth repository (login, logout, token storage)
- Splash → Login → Home flow
- Theme and routing (go_router)
