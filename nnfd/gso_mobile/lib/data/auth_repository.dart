import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../core/config.dart';
import 'models/auth_tokens.dart';

class AuthRepository {
  static const _keyAccess = 'access_token';
  static const _keyRefresh = 'refresh_token';

  final FlutterSecureStorage _storage;
  final Dio _dio;

  AuthRepository({
    required FlutterSecureStorage storage,
    required Dio dio,
  })  : _storage = storage,
        _dio = dio;

  Future<AuthTokens> login({
    required String username,
    required String password,
  }) async {
    final response = await _dio.post(
      AppConfig.tokenEndpoint,
      data: {
        'username': username,
        'password': password,
      },
    );

    final tokens = AuthTokens.fromJson(response.data as Map<String, dynamic>);
    await _storage.write(key: _keyAccess, value: tokens.accessToken);
    await _storage.write(key: _keyRefresh, value: tokens.refreshToken);
    return tokens;
  }

  Future<String?> getAccessToken() async {
    return _storage.read(key: _keyAccess);
  }

  Future<String?> getRefreshToken() async {
    return _storage.read(key: _keyRefresh);
  }

  Future<bool> tryRefreshToken() async {
    final refresh = await getRefreshToken();
    if (refresh == null) return false;

    try {
      final response = await _dio.post(
        AppConfig.tokenRefreshEndpoint,
        data: {'refresh': refresh},
      );
      final access = response.data['access'] as String;
      await _storage.write(key: _keyAccess, value: access);
      return true;
    } catch (_) {
      await logout();
      return false;
    }
  }

  Future<void> logout() async {
    await _storage.delete(key: _keyAccess);
    await _storage.delete(key: _keyRefresh);
  }

  Future<bool> isLoggedIn() async {
    final token = await getAccessToken();
    return token != null && token.isNotEmpty;
  }
}
