import 'dart:async';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/material.dart';

import '../data/outbox_database.dart';
import '../models/request_task.dart';
import '../services/api_client.dart';
import '../services/auth_repository.dart';
import '../services/offline_sync_service.dart';
import '../theme/app_colors.dart';
import 'notifications_screen.dart';
import 'profile_screen.dart';
import 'task_detail_screen.dart';
import 'task_history_screen.dart';

/// Personnel task list — matches web Task Management scope (`my-tasks` API).
class TaskListScreen extends StatefulWidget {
  const TaskListScreen({
    super.key,
    required this.auth,
    required this.onLogout,
  });

  final AuthRepository auth;
  final VoidCallback onLogout;

  @override
  State<TaskListScreen> createState() => _TaskListScreenState();
}

class _TaskListScreenState extends State<TaskListScreen> with WidgetsBindingObserver {
  final Connectivity _connectivity = Connectivity();
  late final ApiClient _api;
  ConnectivityResult _connectivityResult = ConnectivityResult.none;
  StreamSubscription<List<ConnectivityResult>>? _connectivitySub;
  Timer? _autoRefreshTimer;

  List<RequestTask> _tasks = [];
  bool _loading = true;
  String? _error;
  int _queued = 0;
  bool _syncing = false;
  int _unreadNotifications = 0;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _api = ApiClient(
      accessToken: widget.auth.readAccessToken,
      refreshAccessToken: widget.auth.refreshAccessToken,
    );
    OfflineSyncService.instance.bind(
      accessToken: widget.auth.readAccessToken,
      refreshAccessToken: widget.auth.refreshAccessToken,
    );
    _initConnectivity();
    _refreshQueued();
    _refreshUnreadNotifications();
    _loadTasks();
    _startAutoRefresh();
  }

  Future<void> _initConnectivity() async {
    final initial = await _connectivity.checkConnectivity();
    _applyConnectivity(initial);
    _connectivitySub = _connectivity.onConnectivityChanged.listen(_applyConnectivity);
  }

  void _applyConnectivity(List<ConnectivityResult> results) {
    if (!mounted || results.isEmpty) return;
    final wasOnline = _online;
    setState(() => _connectivityResult = results.first);
    if (!wasOnline && _online) {
      _syncNow(showToast: false);
      _autoRefreshTick();
    }
  }

  void _startAutoRefresh() {
    _autoRefreshTimer?.cancel();
    _autoRefreshTimer = Timer.periodic(
      const Duration(seconds: 20),
      (_) => _autoRefreshTick(),
    );
  }

  Future<void> _autoRefreshTick() async {
    if (!mounted || !_online || _loading || _syncing) return;
    await _refreshUnreadNotifications();
    await _loadTasks(showLoading: false);
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      _autoRefreshTick();
    }
  }

  Future<void> _syncNow({bool showToast = true}) async {
    if (!_online) {
      if (showToast && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Still offline. Sync will resume when online.')),
        );
      }
      return;
    }
    if (_syncing) return;
    setState(() => _syncing = true);
    try {
      await OfflineSyncService.instance.syncOnce();
      await _refreshQueued();
      await _refreshUnreadNotifications();
      await _loadTasks();
      if (showToast && mounted) {
        final queued = _queued;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              queued == 0 ? 'Sync complete.' : 'Sync attempted. $queued still queued.',
            ),
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _syncing = false);
    }
  }

  Future<void> _refreshQueued() async {
    try {
      final n = await OutboxDatabase.instance.pendingCount();
      if (mounted) setState(() => _queued = n);
    } catch (_) {
      if (mounted) setState(() => _queued = 0);
    }
  }

  Future<void> _refreshUnreadNotifications() async {
    try {
      final count = await _api.fetchUnreadNotificationCount();
      if (mounted) setState(() => _unreadNotifications = count);
    } catch (_) {
      if (mounted) setState(() => _unreadNotifications = 0);
    }
  }

  bool get _online =>
      _connectivityResult != ConnectivityResult.none &&
      _connectivityResult != ConnectivityResult.bluetooth;

  @override
  void dispose() {
    _connectivitySub?.cancel();
    _autoRefreshTimer?.cancel();
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  Future<void> _loadTasks({bool showLoading = true}) async {
    if (showLoading) {
      setState(() {
        _loading = true;
        _error = null;
      });
    }
    if (_online) {
      await OfflineSyncService.instance.syncOnce();
      if (mounted) await _refreshQueued();
    }
    try {
      final list = await _api.fetchMyTasks();
      if (mounted) {
        setState(() {
          _tasks = list;
          if (showLoading) _loading = false;
          _error = null;
        });
      }
      if (_online) {
        await OfflineSyncService.instance.syncOnce();
        if (mounted) await _refreshQueued();
        if (mounted) await _refreshUnreadNotifications();
      }
    } catch (e) {
      if (mounted) {
        final keepCachedList =
            ApiClient.isConnectivityFailure(e) && _tasks.isNotEmpty;
        if (!showLoading) return;
        setState(() {
          _error = keepCachedList ? null : _api.messageFromError(e);
          if (showLoading) _loading = false;
        });
      }
    }
  }

  Future<void> _openDetail(RequestTask task) async {
    final popped = await Navigator.push<RequestTask>(
      context,
      MaterialPageRoute<RequestTask>(
        builder: (context) => TaskDetailScreen(task: task, auth: widget.auth),
      ),
    );
    await _refreshQueued();
    if (mounted && popped != null) {
      final i = _tasks.indexWhere((t) => t.id == popped.id);
      if (i >= 0) {
        setState(() => _tasks = List<RequestTask>.of(_tasks)..[i] = popped);
      }
    }
    await _loadTasks();
    await _refreshQueued();
  }

  Future<void> _openHistory() async {
    await Navigator.push<void>(
      context,
      MaterialPageRoute<void>(
        builder: (context) => TaskHistoryScreen(auth: widget.auth),
      ),
    );
  }

  Future<void> _openNotifications() async {
    final changed = await Navigator.push<bool>(
      context,
      MaterialPageRoute<bool>(
        builder: (context) => NotificationsScreen(auth: widget.auth),
      ),
    );
    if (changed == true) {
      await _refreshUnreadNotifications();
    }
  }

  Future<void> _openProfile() async {
    await Navigator.push<void>(
      context,
      MaterialPageRoute<void>(
        builder: (context) => ProfileScreen(
          auth: widget.auth,
          onLogout: () async => widget.onLogout(),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final connectivityLabel = _online
        ? (_queued > 0 ? 'Online · $_queued queued for sync' : 'Online')
        : (_tasks.isNotEmpty
            ? 'Offline · $_queued queued · showing last loaded tasks'
            : 'Offline · $_queued queued');

    return Scaffold(
      appBar: AppBar(
        toolbarHeight: 72,
        titleSpacing: 16,
        title: Text(
          'Task Management',
          style: t.headlineSmall?.copyWith(
            fontWeight: FontWeight.w700,
            color: AppColors.slate900,
          ),
        ),
        actions: [
          _FloatingActionIconButton(
            tooltip: 'Task history',
            icon: const Icon(Icons.history_rounded, size: 20),
            onPressed: _openHistory,
          ),
          _FloatingActionIconButton(
            tooltip: 'Notifications',
            onPressed: _openNotifications,
            icon: Stack(
              clipBehavior: Clip.none,
              children: [
                const Icon(Icons.notifications_none_rounded, size: 20),
                if (_unreadNotifications > 0)
                  Positioned(
                    right: -3,
                    top: -3,
                    child: Container(
                      constraints: const BoxConstraints(minWidth: 16, minHeight: 16),
                      padding: const EdgeInsets.symmetric(horizontal: 4),
                      decoration: const BoxDecoration(
                        color: AppColors.red600,
                        shape: BoxShape.circle,
                      ),
                      child: Center(
                        child: Text(
                          _unreadNotifications > 99 ? '99+' : '$_unreadNotifications',
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 9,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                    ),
                  ),
              ],
            ),
          ),
          _FloatingActionIconButton(
            tooltip: 'Sync now',
            icon: _syncing
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.sync_rounded, size: 20),
            onPressed: _syncing ? null : () => _syncNow(),
          ),
          PopupMenuButton<String>(
            tooltip: 'Profile menu',
            onSelected: (value) {
              if (value == 'profile') _openProfile();
              if (value == 'logout') widget.onLogout();
            },
            itemBuilder: (context) => const [
              PopupMenuItem<String>(
                value: 'profile',
                child: Row(
                  children: [
                    Icon(Icons.person_outline_rounded, size: 18),
                    SizedBox(width: 10),
                    Text('My profile'),
                  ],
                ),
              ),
              PopupMenuItem<String>(
                value: 'logout',
                child: Row(
                  children: [
                    Icon(Icons.logout_rounded, size: 18),
                    SizedBox(width: 10),
                    Text('Logout'),
                  ],
                ),
              ),
            ],
            child: const Padding(
              padding: EdgeInsets.symmetric(horizontal: 8),
              child: _FloatingIconShell(
                child: Icon(Icons.account_circle_outlined, size: 20),
              ),
            ),
          ),
          const SizedBox(width: 6),
        ],
      ),
      body: Stack(
        children: [
          _loading
              ? const Center(child: CircularProgressIndicator())
              : _error != null
                  ? Center(
                      child: Padding(
                        padding: const EdgeInsets.all(24),
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Text(_error!, textAlign: TextAlign.center),
                            const SizedBox(height: 16),
                            FilledButton(
                              onPressed: _loadTasks,
                              child: const Text('Retry'),
                            ),
                          ],
                        ),
                      ),
                    )
                  : _tasks.isEmpty
                      ? Center(
                          child: Padding(
                            padding: const EdgeInsets.all(24),
                            child: Text(
                              'No assigned tasks. When the Director approves a request you’re assigned to, it will appear here.',
                              textAlign: TextAlign.center,
                              style: t.bodyMedium?.copyWith(color: AppColors.slate500),
                            ),
                          ),
                        )
                      : RefreshIndicator(
                          onRefresh: _loadTasks,
                          child: ListView.separated(
                            padding: const EdgeInsets.all(16),
                            itemCount: _tasks.length,
                            separatorBuilder: (_, __) => const SizedBox(height: 10),
                            itemBuilder: (context, index) {
                              final req = _tasks[index];
                              return Card(
                                elevation: 0,
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(12),
                                  side: const BorderSide(color: AppColors.slate200),
                                ),
                                child: InkWell(
                                  borderRadius: BorderRadius.circular(12),
                                  onTap: () => _openDetail(req),
                                  child: Padding(
                                    padding: const EdgeInsets.all(16),
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Row(
                                          children: [
                                            Text(
                                              req.displayId,
                                              style: t.titleSmall?.copyWith(
                                                fontWeight: FontWeight.w700,
                                              ),
                                            ),
                                            if (req.isEmergency) ...[
                                              const SizedBox(width: 8),
                                              Container(
                                                padding: const EdgeInsets.symmetric(
                                                  horizontal: 6,
                                                  vertical: 2,
                                                ),
                                                decoration: BoxDecoration(
                                                  color: Colors.red.shade100,
                                                  borderRadius: BorderRadius.circular(6),
                                                ),
                                                child: Text(
                                                  'Emergency',
                                                  style: t.labelSmall?.copyWith(
                                                    color: Colors.red.shade900,
                                                    fontWeight: FontWeight.w800,
                                                  ),
                                                ),
                                              ),
                                            ],
                                          ],
                                        ),
                                        const SizedBox(height: 6),
                                        Text(
                                          req.purposePreview,
                                          style: t.bodySmall?.copyWith(
                                            color: AppColors.slate600,
                                          ),
                                        ),
                                        const SizedBox(height: 8),
                                        Row(
                                          children: [
                                            Expanded(
                                              child: Text(
                                                req.requestorName ?? '—',
                                                style: t.bodySmall?.copyWith(
                                                  color: AppColors.slate500,
                                                ),
                                              ),
                                            ),
                                            Container(
                                              padding: const EdgeInsets.symmetric(
                                                horizontal: 10,
                                                vertical: 4,
                                              ),
                                              decoration: BoxDecoration(
                                                color: AppColors.primary.withOpacity(0.1),
                                                borderRadius: BorderRadius.circular(20),
                                              ),
                                              child: Text(
                                                req.statusDisplay,
                                                style: t.labelSmall?.copyWith(
                                                  color: AppColors.primary,
                                                  fontWeight: FontWeight.w700,
                                                ),
                                              ),
                                            ),
                                          ],
                                        ),
                                      ],
                                    ),
                                  ),
                                ),
                              );
                            },
                          ),
                        ),
          Positioned(
            right: 16,
            bottom: 16,
            child: IgnorePointer(
              ignoring: true,
              child: AnimatedOpacity(
                duration: const Duration(milliseconds: 250),
                opacity: 1,
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    color: _online ? Colors.green.shade600 : Colors.orange.shade700,
                    borderRadius: BorderRadius.circular(999),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withOpacity(0.15),
                        blurRadius: 8,
                        offset: const Offset(0, 3),
                      ),
                    ],
                  ),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          _online ? Icons.wifi_rounded : Icons.wifi_off_rounded,
                          color: Colors.white,
                          size: 16,
                        ),
                        const SizedBox(width: 6),
                        Text(
                          connectivityLabel,
                          style: t.labelMedium?.copyWith(
                            color: Colors.white,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _FloatingActionIconButton extends StatelessWidget {
  const _FloatingActionIconButton({
    required this.tooltip,
    required this.icon,
    required this.onPressed,
  });

  final String tooltip;
  final Widget icon;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: _FloatingIconShell(
        child: IconButton(
          tooltip: tooltip,
          icon: icon,
          onPressed: onPressed,
        ),
      ),
    );
  }
}

class _FloatingIconShell extends StatelessWidget {
  const _FloatingIconShell({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.white,
      elevation: 0,
      shape: const CircleBorder(side: BorderSide(color: AppColors.slate200)),
      child: child,
    );
  }
}
