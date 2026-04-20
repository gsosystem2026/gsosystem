import 'api_client.dart';
import '../core/config.dart';

class VersionRepository {
  final ApiClient _apiClient;

  VersionRepository({required ApiClient apiClient}) : _apiClient = apiClient;

  /// Check if app needs update. Returns true if update required.
  Future<bool> isUpdateRequired() async {
    try {
      final response = await _apiClient.dio.get('version/');
      final minVersion = response.data['min_version'] as String? ?? '1.0.0';
      return _compareVersions(AppConfig.appVersion, minVersion) < 0;
    } catch (_) {
      return false; // On error, don't block user
    }
  }

  int _compareVersions(String a, String b) {
    final aParts = a.split('.').map((e) => int.tryParse(e) ?? 0).toList();
    final bParts = b.split('.').map((e) => int.tryParse(e) ?? 0).toList();
    for (var i = 0; i < aParts.length || i < bParts.length; i++) {
      final av = i < aParts.length ? aParts[i] : 0;
      final bv = i < bParts.length ? bParts[i] : 0;
      if (av != bv) return av.compareTo(bv);
    }
    return 0;
  }
}
