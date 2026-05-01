import 'package:dio/dio.dart';

import '../config/env.dart';
import '../models/request_task.dart';

typedef AccessTokenProvider = Future<String?> Function();

class ApiClient {
  ApiClient({required AccessTokenProvider accessToken})
      : _accessToken = accessToken {
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
      ),
    );
  }

  final AccessTokenProvider _accessToken;
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
