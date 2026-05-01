import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../config/env.dart';

/// JWT auth against Django `POST /api/v1/auth/token/` (SimpleJWT).
class AuthRepository {
  AuthRepository({FlutterSecureStorage? storage})
      : _storage = storage ?? const FlutterSecureStorage();

  static const _kAccess = 'gso_jwt_access';
  static const _kRefresh = 'gso_jwt_refresh';

  final FlutterSecureStorage _storage;

  Dio get _api => Dio(
        BaseOptions(
          baseUrl: '$kGsoApiBase/api/v1',
          connectTimeout: const Duration(seconds: 25),
          receiveTimeout: const Duration(seconds: 25),
          headers: {'Content-Type': 'application/json'},
        ),
      );

  Future<bool> hasToken() async {
    final a = await _storage.read(key: _kAccess);
    return a != null && a.isNotEmpty;
  }

  Future<String?> readAccessToken() => _storage.read(key: _kAccess);

  Future<String?> readRefreshToken() => _storage.read(key: _kRefresh);

  Future<void> signInWithPassword({
    required String username,
    required String password,
  }) async {
    try {
      final response = await _api.post<Map<String, dynamic>>(
        '/auth/token/',
        data: {'username': username.trim(), 'password': password},
      );
      final data = response.data;
      if (data == null ||
          data['access'] is! String ||
          data['refresh'] is! String) {
        throw const AuthException('Invalid response from server.');
      }
      await _storage.write(key: _kAccess, value: data['access'] as String);
      await _storage.write(key: _kRefresh, value: data['refresh'] as String);
    } on DioException catch (e) {
      final msg = _messageFromDio(e);
      throw AuthException(msg);
    }
  }

  Future<void> signOut() async {
    await _storage.delete(key: _kAccess);
    await _storage.delete(key: _kRefresh);
  }

  /// Attempts to refresh access token using stored refresh token.
  /// Returns new access token on success, or null when refresh is not possible.
  Future<String?> refreshAccessToken() async {
    final refresh = await readRefreshToken();
    if (refresh == null || refresh.isEmpty) return null;
    try {
      final response = await _api.post<Map<String, dynamic>>(
        '/auth/token/refresh/',
        data: {'refresh': refresh},
      );
      final data = response.data;
      final access = data?['access'];
      if (access is! String || access.isEmpty) return null;
      await _storage.write(key: _kAccess, value: access);
      final maybeRefresh = data?['refresh'];
      if (maybeRefresh is String && maybeRefresh.isNotEmpty) {
        await _storage.write(key: _kRefresh, value: maybeRefresh);
      }
      return access;
    } on DioException catch (e) {
      final code = e.response?.statusCode;
      if (code == 400 || code == 401) {
        await signOut();
      }
      return null;
    }
  }

  String _messageFromDio(DioException e) {
    final status = e.response?.statusCode;
    if (status == 401 || status == 400) {
      return 'Invalid username or password.';
    }
    if (e.type == DioExceptionType.connectionTimeout ||
        e.type == DioExceptionType.receiveTimeout) {
      return 'Connection timed out. Check your internet.';
    }
    if (e.type == DioExceptionType.connectionError) {
      if (kIsWeb) {
        return 'Browser blocked the request (likely CORS). Use Android build for full testing, or allow localhost origin on the API server.';
      }
      return 'No internet connection.';
    }
    return e.message ?? 'Sign in failed. Try again.';
  }
}

class AuthException implements Exception {
  const AuthException(this.message);
  final String message;

  @override
  String toString() => message;
}
