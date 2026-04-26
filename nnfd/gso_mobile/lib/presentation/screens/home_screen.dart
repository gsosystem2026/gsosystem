import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app.dart';
import 'notifications_screen.dart';
import '../../data/models/user.dart';
import 'my_requests_screen.dart';
import 'new_request_screen.dart';
import 'staff_request_list_screen.dart';
import 'task_management_screen.dart';
import 'task_history_screen.dart';
import 'inventory_list_screen.dart';

/// Menu item for drawer navigation.
class _NavItem {
  final String id;
  final String label;
  final IconData icon;

  const _NavItem({required this.id, required this.label, required this.icon});
}

/// Role-based nav items.
List<_NavItem> _navItemsForRole(GsoUser user) {
  if (user.isRequestor) {
    return [
      const _NavItem(id: 'my_requests', label: 'My Requests', icon: Icons.list_alt),
      const _NavItem(id: 'new_request', label: 'New Request', icon: Icons.add_circle_outline),
    ];
  }
  if (user.isUnitHead) {
    return [
      const _NavItem(id: 'request_management', label: 'Request Management', icon: Icons.assignment),
      const _NavItem(id: 'inventory', label: 'Inventory', icon: Icons.inventory_2_outlined),
    ];
  }
  if (user.isPersonnel) {
    return [
      const _NavItem(id: 'task_management', label: 'Task Management', icon: Icons.task_alt),
      const _NavItem(id: 'task_history', label: 'Task History', icon: Icons.history),
    ];
  }
  if (user.isGsoOffice || user.isDirector) {
    return [
      const _NavItem(id: 'request_management', label: 'Request Management', icon: Icons.assignment),
      const _NavItem(id: 'inventory', label: 'Inventory', icon: Icons.inventory_2_outlined),
      const _NavItem(id: 'work_reports', label: 'Work Reports', icon: Icons.analytics_outlined),
      const _NavItem(id: 'reports', label: 'Reports', icon: Icons.summarize),
    ];
  }
  return [
    const _NavItem(id: 'home', label: 'Home', icon: Icons.home),
  ];
}

class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen>
    with WidgetsBindingObserver {
  String _selectedId = '';
  Timer? _notificationRefreshTimer;

  void _refreshNotifications() {
    if (!mounted) return;
    ref.invalidate(unreadCountProvider);
    ref.invalidate(notificationsProvider);
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _notificationRefreshTimer = Timer.periodic(
      const Duration(seconds: 30),
      (_) => _refreshNotifications(),
    );
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _notificationRefreshTimer?.cancel();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      _refreshNotifications();
    }
  }

  @override
  Widget build(BuildContext context) {
    final userAsync = ref.watch(currentUserProvider);

    return userAsync.when(
      loading: () => const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      ),
      error: (_, __) => Scaffold(
        body: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text('Failed to load user.'),
              const SizedBox(height: 16),
              TextButton(
                onPressed: () => ref.invalidate(currentUserProvider),
                child: const Text('Retry'),
              ),
            ],
          ),
        ),
      ),
      data: (user) {
        if (user == null) {
          return Scaffold(
            body: Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Text('Could not load your profile.'),
                  const SizedBox(height: 16),
                  TextButton.icon(
                    onPressed: () => ref.invalidate(currentUserProvider),
                    icon: const Icon(Icons.refresh),
                    label: const Text('Retry'),
                  ),
                  const SizedBox(height: 8),
                  TextButton(
                    onPressed: () => _handleLogout(context),
                    child: const Text('Log out'),
                  ),
                ],
              ),
            ),
          );
        }

        final navItems = _navItemsForRole(user);
        final selectedId = _selectedId.isEmpty && navItems.isNotEmpty
            ? navItems.first.id
            : _selectedId;

        return Scaffold(
          appBar: AppBar(
            title: Text(_labelForId(selectedId, navItems)),
            actions: [
              _NotificationBadgeWidget(onTap: () => context.push('/notifications')),
              IconButton(
                icon: const Icon(Icons.logout),
                onPressed: () => _handleLogout(context),
              ),
            ],
          ),
          drawer: Drawer(
            child: ListView(
              padding: EdgeInsets.zero,
              children: [
                DrawerHeader(
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.primaryContainer,
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      CircleAvatar(
                        backgroundColor: Theme.of(context).colorScheme.primary,
                        child: Text(
                          user.displayName.isNotEmpty
                              ? user.displayName[0].toUpperCase()
                              : '?',
                          style: TextStyle(
                            color: Theme.of(context).colorScheme.onPrimary,
                            fontSize: 24,
                          ),
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        user.displayName,
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      Text(
                        _roleDisplayName(user.role),
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                  ),
                ),
                ...navItems.map((item) {
                  final isSelected = selectedId == item.id;
                  return ListTile(
                    leading: Icon(item.icon),
                    title: Text(item.label),
                    selected: isSelected,
                    onTap: () {
                      setState(() => _selectedId = item.id);
                      Navigator.of(context).pop();
                    },
                  );
                }),
              ],
            ),
          ),
          body: _buildBody(selectedId, user),
        );
      },
    );
  }

  String _labelForId(String id, List<_NavItem> items) {
    for (final item in items) {
      if (item.id == id) return item.label;
    }
    return id;
  }

  String _roleDisplayName(String role) {
    switch (role) {
      case 'REQUESTOR':
        return 'Requestor';
      case 'UNIT_HEAD':
        return 'Unit Head';
      case 'PERSONNEL':
        return 'Personnel';
      case 'GSO_OFFICE':
        return 'GSO Office';
      case 'DIRECTOR':
        return 'Director';
      default:
        return role;
    }
  }

  Widget _buildBody(String id, GsoUser user) {
    if (user.isRequestor && id == 'my_requests') {
      return const MyRequestsScreen();
    }
    if (user.isRequestor && id == 'new_request') {
      return const NewRequestScreen();
    }
    if ((user.isUnitHead || user.isGsoOffice || user.isDirector) &&
        id == 'request_management') {
      return StaffRequestListScreen(user: user);
    }
    if (user.isPersonnel && id == 'task_management') {
      return TaskManagementScreen(user: user);
    }
    if (user.isPersonnel && id == 'task_history') {
      return TaskHistoryScreen(user: user);
    }
    if ((user.isUnitHead || user.isGsoOffice || user.isDirector) &&
        id == 'inventory') {
      return InventoryListScreen(user: user);
    }
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.construction, size: 64, color: Colors.grey[400]),
            const SizedBox(height: 16),
            Text(
              _labelForId(id, _navItemsForRole(user)),
              style: Theme.of(context).textTheme.titleLarge,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              'Coming soon.',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Colors.grey[600],
                  ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _handleLogout(BuildContext context) async {
    await ref.read(authRepositoryProvider).logout();
    ref.invalidate(currentUserProvider);
    if (!context.mounted) return;
    context.go('/login');
  }
}

class _NotificationBadgeWidget extends ConsumerWidget {
  final VoidCallback onTap;

  const _NotificationBadgeWidget({required this.onTap});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final countAsync = ref.watch(unreadCountProvider);
    return countAsync.when(
      data: (count) => IconButton(
        icon: count > 0
            ? Badge(
                label: Text(count > 99 ? '99+' : '$count'),
                child: const Icon(Icons.notifications),
              )
            : const Icon(Icons.notifications_outlined),
        onPressed: onTap,
      ),
      loading: () => IconButton(
        icon: const Icon(Icons.notifications_outlined),
        onPressed: onTap,
      ),
      error: (_, __) => IconButton(
        icon: const Icon(Icons.notifications_outlined),
        onPressed: onTap,
      ),
    );
  }
}
