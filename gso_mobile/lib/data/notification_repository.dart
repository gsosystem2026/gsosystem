import 'api_client.dart';
import 'models/notification.dart';

class NotificationRepository {
  final ApiClient _apiClient;

  NotificationRepository({required ApiClient apiClient}) : _apiClient = apiClient;

  /// List notifications for current user.
  Future<List<GsoNotification>> getNotifications() async {
    final response = await _apiClient.dio.get('notifications/');
    final data = response.data;
    final list = data is Map && data.containsKey('results')
        ? data['results']
        : (data is List ? data : <dynamic>[]);
    final items = list is List ? list : <dynamic>[];
    return items
        .map((e) => GsoNotification.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// Unread count for badge.
  Future<int> getUnreadCount() async {
    final response = await _apiClient.dio.get('notifications/unread_count/');
    return (response.data as Map<String, dynamic>)['count'] as int? ?? 0;
  }

  /// Mark one notification as read.
  Future<void> markRead(int id) async {
    await _apiClient.dio.post('notifications/$id/mark_read/');
  }

  /// Mark all as read.
  Future<void> markAllRead() async {
    await _apiClient.dio.post('notifications/mark_all_read/');
  }
}
