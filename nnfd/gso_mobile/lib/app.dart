import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:dio/dio.dart';
import 'package:go_router/go_router.dart';

import 'core/config.dart';
import 'core/theme.dart';
import 'data/auth_repository.dart';
import 'data/api_client.dart';
import 'data/user_repository.dart';
import 'data/request_repository.dart';
import 'data/inventory_repository.dart';
import 'data/notification_repository.dart';
import 'data/push_service.dart';
import 'data/models/user.dart';
import 'presentation/screens/splash_screen.dart';
import 'presentation/screens/login_screen.dart';
import 'presentation/screens/home_screen.dart';
import 'presentation/screens/request_detail_screen.dart';
import 'presentation/screens/inventory_detail_screen.dart';
import 'presentation/screens/notifications_screen.dart';
import 'presentation/widgets/app_banners.dart';

final secureStorageProvider =
    Provider<FlutterSecureStorage>((ref) => const FlutterSecureStorage());

final dioProvider = Provider<Dio>((ref) {
  return Dio(BaseOptions(baseUrl: AppConfig.apiBaseUrl));
});

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  return AuthRepository(
    storage: ref.read(secureStorageProvider),
    dio: ref.read(dioProvider),
  );
});

final apiClientProvider = Provider<ApiClient>((ref) {
  return ApiClient(ref.read(authRepositoryProvider));
});

final userRepositoryProvider = Provider<UserRepository>((ref) {
  return UserRepository(
    apiClient: ref.read(apiClientProvider),
    authRepository: ref.read(authRepositoryProvider),
  );
});

final requestRepositoryProvider = Provider<RequestRepository>((ref) {
  return RequestRepository(apiClient: ref.read(apiClientProvider));
});

final inventoryRepositoryProvider = Provider<InventoryRepository>((ref) {
  return InventoryRepository(apiClient: ref.read(apiClientProvider));
});

final notificationRepositoryProvider = Provider<NotificationRepository>((ref) {
  return NotificationRepository(apiClient: ref.read(apiClientProvider));
});

final pushServiceProvider = Provider<PushService>((ref) {
  return PushService(
    apiClient: ref.read(apiClientProvider),
    authRepository: ref.read(authRepositoryProvider),
  );
});

/// Current user (fetched after login). Null until loaded.
final currentUserProvider = FutureProvider<GsoUser?>((ref) async {
  final authRepo = ref.read(authRepositoryProvider);
  final isLoggedIn = await authRepo.isLoggedIn();
  if (!isLoggedIn) return null;
  try {
    final userRepo = ref.read(userRepositoryProvider);
    return await userRepo.getMe();
  } catch (_) {
    return null;
  }
});

final routerProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: '/splash',
    routes: [
      GoRoute(
        path: '/splash',
        builder: (context, state) => const SplashScreen(),
      ),
      GoRoute(
        path: '/login',
        builder: (context, state) => const LoginScreen(),
      ),
      GoRoute(
        path: '/home',
        builder: (context, state) => const HomeScreen(),
      ),
      GoRoute(
        path: '/request/:id',
        builder: (context, state) {
          final id = state.pathParameters['id']!;
          return RequestDetailScreen(requestId: int.parse(id));
        },
      ),
      GoRoute(
        path: '/inventory/:id',
        builder: (context, state) {
          final id = state.pathParameters['id']!;
          return InventoryDetailScreen(itemId: int.parse(id));
        },
      ),
      GoRoute(
        path: '/notifications',
        builder: (context, state) => const NotificationsScreen(),
      ),
    ],
  );
});

class _AppBannerWrapper extends ConsumerWidget {
  final Widget? child;

  const _AppBannerWrapper({this.child});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Column(
      children: [
        const UpdateRequiredBanner(),
        const OfflineBanner(),
        Expanded(child: child ?? const SizedBox.shrink()),
      ],
    );
  }
}

class GsoApp extends ConsumerWidget {
  const GsoApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(routerProvider);

    return MaterialApp.router(
      title: 'GSO Mobile',
      theme: AppTheme.light,
      routerConfig: router,
      builder: (context, child) => _AppBannerWrapper(child: child),
    );
  }
}
