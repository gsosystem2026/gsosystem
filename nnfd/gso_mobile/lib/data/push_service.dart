// Push notification service. Firebase removed due to Android build (jlink) issue.
// Add firebase_core + firebase_messaging + connectivity_plus when JDK/AGP is fixed.
import 'api_client.dart';
import 'auth_repository.dart';

class PushService {
  final ApiClient _apiClient;
  final AuthRepository _authRepository;

  PushService({
    required ApiClient apiClient,
    required AuthRepository authRepository,
  })  : _apiClient = apiClient,
        _authRepository = authRepository;

  /// Initialize FCM and register token. No-op (Firebase removed for build).
  Future<void> init() async {
    // Firebase/connectivity_plus removed - add back when JDK/AGP is fixed
  }
}
