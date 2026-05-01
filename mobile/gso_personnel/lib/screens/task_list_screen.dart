import 'dart:async';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/material.dart';

import '../data/outbox_database.dart';
import '../models/request_task.dart';
import '../services/api_client.dart';
import '../services/auth_repository.dart';
import '../services/offline_sync_service.dart';
import '../theme/app_colors.dart';
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

class _TaskListScreenState extends State<TaskListScreen> {
  final Connectivity _connectivity = Connectivity();
  late final ApiClient _api;
  ConnectivityResult _connectivityResult = ConnectivityResult.none;
  StreamSubscription<List<ConnectivityResult>>? _connectivitySub;

  List<RequestTask> _tasks = [];
  bool _loading = true;
  String? _error;
  int _queued = 0;
  bool _syncing = false;

  @override
  void initState() {
    super.initState();
    _api = ApiClient(accessToken: widget.auth.readAccessToken);
    OfflineSyncService.instance.bind(accessToken: widget.auth.readAccessToken);
    _initConnectivity();
    _refreshQueued();
    _loadTasks();
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

  bool get _online =>
      _connectivityResult != ConnectivityResult.none &&
      _connectivityResult != ConnectivityResult.bluetooth;

  @override
  void dispose() {
    _connectivitySub?.cancel();
    super.dispose();
  }

  Future<void> _loadTasks() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    if (_online) {
      await OfflineSyncService.instance.syncOnce();
      if (mounted) await _refreshQueued();
    }
    try {
      final list = await _api.fetchMyTasks();
      if (mounted) {
        setState(() {
          _tasks = list;
          _loading = false;
        });
      }
      if (_online) {
        await OfflineSyncService.instance.syncOnce();
        if (mounted) await _refreshQueued();
      }
    } catch (e) {
      if (mounted) {
        final keepCachedList =
            ApiClient.isConnectivityFailure(e) && _tasks.isNotEmpty;
        setState(() {
          _error = keepCachedList ? null : _api.messageFromError(e);
          _loading = false;
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

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Task Management'),
        actions: [
          IconButton(
            tooltip: 'Task history',
            icon: const Icon(Icons.history_rounded),
            onPressed: _openHistory,
          ),
          IconButton(
            tooltip: 'Sync now',
            icon: _syncing
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.sync_rounded),
            onPressed: _syncing ? null : () => _syncNow(),
          ),
          IconButton(
            tooltip: 'Refresh',
            icon: const Icon(Icons.refresh_rounded),
            onPressed: () {
              _loadTasks();
              _refreshQueued();
            },
          ),
          IconButton(
            tooltip: 'Sign out',
            icon: const Icon(Icons.logout_rounded),
            onPressed: widget.onLogout,
          ),
        ],
      ),
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Material(
            color: _online ? Colors.green.shade50 : Colors.orange.shade50,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              child: Row(
                children: [
                  Icon(
                    _online ? Icons.wifi_rounded : Icons.wifi_off_rounded,
                    size: 20,
                    color: _online ? Colors.green.shade800 : Colors.orange.shade900,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      _online
                          ? (_queued > 0
                              ? 'Online · $_queued queued for sync'
                              : 'Online')
                          : (_tasks.isNotEmpty
                              ? 'Offline · $_queued queued · showing last loaded tasks'
                              : 'Offline · $_queued queued'),
                      style: t.labelLarge?.copyWith(
                        color: _online ? Colors.green.shade900 : Colors.orange.shade900,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
          Expanded(
            child: _loading
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
          ),
        ],
      ),
    );
  }
}
