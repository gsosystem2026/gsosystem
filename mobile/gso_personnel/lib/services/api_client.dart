import 'package:dio/dio.dart';

import '../config/env.dart';
import '../models/app_notification.dart';
import '../models/material_request_item.dart';
import '../models/request_message.dart';
import '../models/request_task.dart';

typedef AccessTokenProvider = Future<String?> Function();
typedef RefreshAccessToken = Future<String?> Function();

class ApiClient {
  ApiClient({
    required AccessTokenProvider accessToken,
    RefreshAccessToken? refreshAccessToken,
  })  : _accessToken = accessToken,
        _refreshAccessToken = refreshAccessToken {
    _dio = Dio(
      BaseOptions(
        baseUrl: '$kGsoApiBase/api/v1',
        connectTimeout: const Duration(seconds: 25),
        receiveTimeout: const Duration(seconds: 25),
        sendTimeout: const Duration(seconds: 25),
        headers: {'Content-Type': 'application/json'},
      ),
    );
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          final t = await _accessToken();
          if (t != null && t.isNotEmpty) {
            options.headers['Authorization'] = 'Bearer $t';
          }
          return handler.next(options);
        },
        onError: (err, handler) async {
          final refresh = _refreshAccessToken;
          final status = err.response?.statusCode;
          final retried = err.requestOptions.extra['jwt_refreshed'] == true;
          if (refresh == null || status != 401 || retried) {
            return handler.next(err);
          }

          final freshAccess = await refresh();
          if (freshAccess == null || freshAccess.isEmpty) {
            return handler.next(err);
          }

          final req = err.requestOptions;
          req.extra['jwt_refreshed'] = true;
          req.headers['Authorization'] = 'Bearer $freshAccess';
          try {
            final response = await _dio.fetch(req);
            return handler.resolve(response);
          } on DioException catch (e) {
            return handler.next(e);
          }
        },
      ),
    );
  }

  final AccessTokenProvider _accessToken;
  final RefreshAccessToken? _refreshAccessToken;
  late final Dio _dio;

  Future<List<RequestTask>> fetchMyTasks() async {
    final list = await _getRequestTaskListWithFallback(
      primaryPath: '/requests/my-tasks/',
      fallbackPath: '/requests/my_tasks/',
      listFallbackFilter: (req) => _activeTaskStatuses.contains(req.status),
    );
    return list;
  }

  Future<List<RequestTask>> fetchMyTaskHistory() async {
    final list = await _getRequestTaskListWithFallback(
      primaryPath: '/requests/my-task-history/',
      fallbackPath: '/requests/my_task_history/',
      listFallbackFilter: (req) => _historyTaskStatuses.contains(req.status),
    );
    return list;
  }

  static const Set<String> _activeTaskStatuses = {
    'DIRECTOR_APPROVED',
    'INSPECTION',
    'IN_PROGRESS',
    'ON_HOLD',
    'DONE_WORKING',
  };

  static const Set<String> _historyTaskStatuses = {
    'COMPLETED',
    'CANCELLED',
  };

  Future<List<RequestTask>> _getRequestTaskListWithFallback({
    required String primaryPath,
    required String fallbackPath,
    required bool Function(RequestTask req) listFallbackFilter,
  }) async {
    Response<List<dynamic>> response;
    try {
      response = await _dio.get<List<dynamic>>(primaryPath);
    } on DioException catch (e) {
      if (!_isNotFound(e)) rethrow;
      try {
        response = await _dio.get<List<dynamic>>(fallbackPath);
      } on DioException catch (e2) {
        if (!_isNotFound(e2)) rethrow;
        final fallbackList = await _fetchRequestsListFallback();
        return fallbackList.where(listFallbackFilter).toList();
      }
    }
    final list = response.data ?? [];
    return list
        .map((e) => RequestTask.fromJson(Map<String, dynamic>.from(e as Map)))
        .toList();
  }

  Future<List<RequestTask>> _fetchRequestsListFallback() async {
    final response = await _dio.get<dynamic>('/requests/');
    final data = response.data;
    if (data is List) {
      return data
          .map((e) => RequestTask.fromJson(Map<String, dynamic>.from(e as Map)))
          .toList();
    }
    if (data is Map && data['results'] is List) {
      final results = data['results'] as List<dynamic>;
      return results
          .map((e) => RequestTask.fromJson(Map<String, dynamic>.from(e as Map)))
          .toList();
    }
    return const [];
  }

  bool _isNotFound(DioException e) {
    final status = e.response?.statusCode;
    final data = e.response?.data;
    return status == 404 &&
        data is Map &&
        (data['detail']?.toString().toLowerCase() == 'not found.');
  }

  Future<RequestTask> fetchRequestDetail(int id) async {
    final response = await _dio.get<Map<String, dynamic>>('/requests/$id/');
    return RequestTask.fromJson(Map<String, dynamic>.from(response.data!));
  }

  /// Returns updated request JSON (detail shape).
  Future<Map<String, dynamic>> postWorkStatus(
    int id,
    String status, {
    String? idempotencyKey,
  }) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/requests/$id/status/',
      data: {'status': status},
      options: Options(
        headers: idempotencyKey == null ? null : {'X-Idempotency-Key': idempotencyKey},
      ),
    );
    return Map<String, dynamic>.from(response.data!);
  }

  Future<List<AppNotification>> fetchNotifications() async {
    final response = await _dio.get<dynamic>('/notifications/');
    final data = response.data;
    if (data is List) {
      return data
          .map((e) => AppNotification.fromJson(Map<String, dynamic>.from(e as Map)))
          .toList();
    }
    if (data is Map && data['results'] is List) {
      final results = data['results'] as List<dynamic>;
      return results
          .map((e) => AppNotification.fromJson(Map<String, dynamic>.from(e as Map)))
          .toList();
    }
    return const [];
  }

  Future<int> fetchUnreadNotificationCount() async {
    final response = await _dio.get<Map<String, dynamic>>('/notifications/unread_count/');
    final data = response.data ?? const <String, dynamic>{};
    final count = data['count'];
    if (count is int) return count;
    if (count is num) return count.toInt();
    return 0;
  }

  Future<void> markNotificationRead(int id) async {
    await _dio.post('/notifications/$id/mark_read/');
  }

  Future<void> markAllNotificationsRead() async {
    await _dio.post('/notifications/mark_all_read/');
  }

  Future<Map<String, dynamic>> fetchCurrentUser() async {
    final response = await _dio.get<Map<String, dynamic>>('/users/me/');
    return Map<String, dynamic>.from(response.data ?? const <String, dynamic>{});
  }

  Future<Map<String, dynamic>> updateCurrentUser({
    required String firstName,
    required String lastName,
    required String email,
  }) async {
    final response = await _dio.patch<Map<String, dynamic>>(
      '/users/me/',
      data: {
        'first_name': firstName,
        'last_name': lastName,
        'email': email,
      },
    );
    return Map<String, dynamic>.from(response.data ?? const <String, dynamic>{});
  }

  Future<void> changePassword({
    required String currentPassword,
    required String newPassword,
  }) async {
    await _dio.post(
      '/users/change-password/',
      data: {
        'current_password': currentPassword,
        'new_password': newPassword,
      },
    );
  }

  Future<List<RequestMessageItem>> fetchRequestMessages(int requestId) async {
    final response = await _dio.get<List<dynamic>>('/requests/$requestId/messages/');
    final list = response.data ?? [];
    return list
        .map((e) => RequestMessageItem.fromJson(Map<String, dynamic>.from(e as Map)))
        .toList();
  }

  Future<RequestMessageItem> postRequestMessage(int requestId, String message) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/requests/$requestId/messages/',
      data: {'message': message},
    );
    return RequestMessageItem.fromJson(
      Map<String, dynamic>.from(response.data ?? const <String, dynamic>{}),
    );
  }

  Future<List<MaterialRequestItem>> fetchRequestMaterialRequests(int requestId) async {
    final response = await _dio.get<List<dynamic>>('/requests/$requestId/material-requests/');
    final list = response.data ?? [];
    return list
        .map((e) => MaterialRequestItem.fromJson(Map<String, dynamic>.from(e as Map)))
        .toList();
  }

  Future<MaterialRequestItem> submitMaterialRequest({
    required int requestId,
    required int itemId,
    required int quantity,
    String? notes,
  }) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/requests/$requestId/material-requests/',
      data: {
        'item_id': itemId,
        'quantity': quantity,
        'notes': (notes ?? '').trim(),
      },
    );
    return MaterialRequestItem.fromJson(
      Map<String, dynamic>.from(response.data ?? const <String, dynamic>{}),
    );
  }

  Future<List<Map<String, dynamic>>> fetchInventoryItems() async {
    final response = await _dio.get<dynamic>('/inventory/');
    final data = response.data;
    if (data is List) {
      return data.map((e) => Map<String, dynamic>.from(e as Map)).toList();
    }
    if (data is Map && data['results'] is List) {
      final results = data['results'] as List<dynamic>;
      return results.map((e) => Map<String, dynamic>.from(e as Map)).toList();
    }
    return const [];
  }

  String messageFromError(Object e) {
    if (e is DioException) {
      final data = e.response?.data;
      if (data is Map && data['detail'] != null) {
        return data['detail'].toString();
      }
      if (e.type == DioExceptionType.connectionTimeout ||
          e.type == DioExceptionType.receiveTimeout ||
          e.type == DioExceptionType.sendTimeout) {
        return 'Connection timed out.';
      }
      if (e.type == DioExceptionType.connectionError) {
        return 'No internet connection.';
      }
      return e.message ?? 'Request failed.';
    }
    return e.toString();
  }

  /// True when the failure is likely offline / transport (safe to enqueue), not HTTP 4xx validation.
  static bool isEnqueueableNetworkFailure(DioException e) {
    final code = e.response?.statusCode;
    if (code != null && code >= 400 && code < 500) return false;
    return e.type == DioExceptionType.connectionTimeout ||
        e.type == DioExceptionType.receiveTimeout ||
        e.type == DioExceptionType.sendTimeout ||
        e.type == DioExceptionType.connectionError;
  }

  /// For list refresh: distinguish transport failure vs 4xx/5xx bodies.
  static bool isConnectivityFailure(Object e) {
    if (e is DioException) return isEnqueueableNetworkFailure(e);
    return false;
  }

  /// Outbox replay: drop the op — server rejected it (re-apply from UI if needed). Keeps 401 for retry/backoff.
  static bool shouldDropOutboxOpAfterFailure(DioException e) {
    final c = e.response?.statusCode;
    if (c == null) return false;
    if (c == 401) return false;
    if (c >= 500) return false;
    if (c == 408 || c == 429) return false;
    return c >= 400 && c < 500;
  }
}
