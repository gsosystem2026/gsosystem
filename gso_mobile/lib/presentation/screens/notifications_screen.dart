import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app.dart';
import '../../data/models/notification.dart';

final notificationsProvider = FutureProvider<List<GsoNotification>>((ref) async {
  try {
    return await ref.read(notificationRepositoryProvider).getNotifications();
  } catch (_) {
    return [];
  }
});

final unreadCountProvider = FutureProvider<int>((ref) async {
  try {
    return await ref.read(notificationRepositoryProvider).getUnreadCount();
  } catch (_) {
    return 0;
  }
});

/// Interval in seconds for auto-refreshing notifications and badge.
const _notificationsRefreshSeconds = 30;

class NotificationsScreen extends ConsumerStatefulWidget {
  const NotificationsScreen({super.key});

  @override
  ConsumerState<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends ConsumerState<NotificationsScreen> {
  Timer? _refreshTimer;

  @override
  void initState() {
    super.initState();
    _refreshTimer = Timer.periodic(
      const Duration(seconds: _notificationsRefreshSeconds),
      (_) {
        if (!mounted) return;
        ref.invalidate(notificationsProvider);
        ref.invalidate(unreadCountProvider);
      },
    );
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final notificationsAsync = ref.watch(notificationsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Notifications'),
        actions: [
          notificationsAsync.when(
            data: (list) {
              final unread = list.where((n) => !n.read).length;
              if (unread == 0) return const SizedBox.shrink();
              return TextButton(
                onPressed: () async {
                  await ref.read(notificationRepositoryProvider).markAllRead();
                  ref.invalidate(notificationsProvider);
                  ref.invalidate(unreadCountProvider);
                },
                child: const Text('Mark all read'),
              );
            },
            loading: () => const SizedBox.shrink(),
            error: (_, __) => const SizedBox.shrink(),
          ),
        ],
      ),
      body: notificationsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('Error: $e'),
              const SizedBox(height: 16),
              TextButton(
                onPressed: () => ref.invalidate(notificationsProvider),
                child: const Text('Retry'),
              ),
            ],
          ),
        ),
        data: (list) {
          if (list.isEmpty) {
            return Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.notifications_none, size: 64, color: Colors.grey[400]),
                  const SizedBox(height: 16),
                  Text(
                    'No notifications',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          color: Colors.grey[600],
                        ),
                  ),
                ],
              ),
            );
          }
          return RefreshIndicator(
            onRefresh: () async {
              ref.invalidate(notificationsProvider);
              ref.invalidate(unreadCountProvider);
            },
            child: ListView.builder(
              itemCount: list.length,
              itemBuilder: (context, i) {
                final n = list[i];
                return ListTile(
                  leading: Icon(
                    n.read ? Icons.notifications_outlined : Icons.notifications,
                    color: n.read ? Colors.grey : Theme.of(context).colorScheme.primary,
                  ),
                  title: Text(
                    n.title,
                    style: TextStyle(
                      fontWeight: n.read ? FontWeight.normal : FontWeight.w600,
                    ),
                  ),
                  subtitle: n.message.isNotEmpty
                      ? Text(
                          n.message,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        )
                      : null,
                  trailing: n.createdAt != null
                      ? Text(
                          _formatDate(n.createdAt!),
                          style: TextStyle(
                            fontSize: 12,
                            color: Colors.grey[600],
                          ),
                        )
                      : null,
                  onTap: () => _onNotificationTap(context, n),
                );
              },
            ),
          );
        },
      ),
    );
  }

  void _onNotificationTap(BuildContext context, GsoNotification n) async {
    if (!n.read) {
      await ref.read(notificationRepositoryProvider).markRead(n.id);
      ref.invalidate(notificationsProvider);
      ref.invalidate(unreadCountProvider);
    }
    final requestId = n.requestIdFromLink;
    if (requestId != null && context.mounted) {
      context.push('/request/$requestId');
    }
  }

  String _formatDate(String s) {
    try {
      final dt = DateTime.parse(s);
      final now = DateTime.now();
      final diff = now.difference(dt);
      if (diff.inDays > 0) return '${diff.inDays}d ago';
      if (diff.inHours > 0) return '${diff.inHours}h ago';
      if (diff.inMinutes > 0) return '${diff.inMinutes}m ago';
      return 'Just now';
    } catch (_) {
      return s;
    }
  }
}
