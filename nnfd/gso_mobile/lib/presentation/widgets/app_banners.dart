import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app.dart';
import '../../data/version_repository.dart';

/// Version check - call on app start. Returns true if update required.
final updateRequiredProvider = FutureProvider<bool>((ref) async {
  try {
    final repo = VersionRepository(apiClient: ref.read(apiClientProvider));
    return await repo.isUpdateRequired();
  } catch (_) {
    return false;
  }
});

/// Connectivity - assume online (connectivity_plus removed due to Android build issue).
final connectivityProvider = StreamProvider<bool>((ref) async* {
  yield true;
});

/// Banner shown when update is required.
class UpdateRequiredBanner extends ConsumerWidget {
  const UpdateRequiredBanner({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final updateAsync = ref.watch(updateRequiredProvider);
    return updateAsync.when(
      data: (required) => required
          ? Material(
              color: Colors.orange.shade700,
              child: SafeArea(
                bottom: false,
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  child: Row(
                    children: [
                      const Icon(Icons.info_outline, color: Colors.white, size: 20),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          'A new version is available. Please update the app.',
                          style: const TextStyle(color: Colors.white, fontSize: 13),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            )
          : const SizedBox.shrink(),
      loading: () => const SizedBox.shrink(),
      error: (_, __) => const SizedBox.shrink(),
    );
  }
}

/// Banner shown when offline.
class OfflineBanner extends ConsumerWidget {
  const OfflineBanner({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final onlineAsync = ref.watch(connectivityProvider);
    return onlineAsync.when(
      data: (online) => !online
          ? Material(
              color: Colors.grey.shade700,
              child: SafeArea(
                bottom: false,
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  child: Row(
                    children: [
                      Icon(Icons.cloud_off, color: Colors.grey.shade300, size: 20),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          'No connection. Some features may be unavailable.',
                          style: TextStyle(color: Colors.grey.shade300, fontSize: 13),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            )
          : const SizedBox.shrink(),
      loading: () => const SizedBox.shrink(),
      error: (_, __) => const SizedBox.shrink(),
    );
  }
}
