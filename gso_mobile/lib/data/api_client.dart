import 'package:dio/dio.dart';

import '../core/config.dart';
import 'auth_repository.dart';

class ApiClient {
  final Dio _dio;
  final AuthRepository _authRepository;

  ApiClient._(this._dio, this._authRepository);

  factory ApiClient(AuthRepository authRepository) {
    final dio = Dio(BaseOptions(
      baseUrl: AppConfig.apiBaseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 10),
    ));

    dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        final token = await authRepository.getAccessToken();
        if (token != null && token.isNotEmpty) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        return handler.next(options);
      },
      onError: (e, handler) async {
        if (e.response?.statusCode == 401) {
          final refreshed = await authRepository.tryRefreshToken();
          if (refreshed) {
            final token = await authRepository.getAccessToken();
            if (token != null && token.isNotEmpty) {
              e.requestOptions.headers['Authorization'] = 'Bearer $token';
            }
            final cloned = await dio.fetch(e.requestOptions);
            return handler.resolve(cloned);
          }
        }
        return handler.next(e);
      },
    ));

    return ApiClient._(dio, authRepository);
  }

  Dio get dio => _dio;
}
