import 'package:flutter/foundation.dart' show defaultTargetPlatform, kIsWeb, TargetPlatform;

class AppConfig {
  /// API base URL.
  /// - Android emulator: 10.0.2.2 (emulator's alias for host localhost)
  /// - Chrome/Web/Windows: 127.0.0.1
  /// - Real device: your machine's LAN IP (e.g. http://192.168.1.x:8000/api/v1/)
  static String get apiBaseUrl {
    if (!kIsWeb && defaultTargetPlatform == TargetPlatform.android) {
      return 'http://10.0.2.2:8000/api/v1/';
    }
    return 'http://127.0.0.1:8000/api/v1/';
  }

  static const String tokenEndpoint = 'auth/token/';
  static const String tokenRefreshEndpoint = 'auth/token/refresh/';

  /// App version for version check. Match pubspec.yaml version.
  static const String appVersion = '1.0.0';
}
