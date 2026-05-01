import 'dart:async';

import 'package:flutter/material.dart';

import '../models/app_notification.dart';
import '../services/api_client.dart';
import '../services/auth_repository.dart';
import '../theme/app_colors.dart';
import 'task_detail_screen.dart';

class NotificationsScreen extends StatefulWidget {
  const NotificationsScreen({super.key, required this.auth});

  final AuthRepository auth;

  @override
  State<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends State<NotificationsScreen> with WidgetsBindingObserver {
  late final ApiClient _api;
  List<AppNotification> _items = [];
  bool _loading = true;
  String? _error;
  bool _changed = false;
  Timer? _autoRefreshTimer;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _api = ApiClient(
      accessToken: widget.auth.readAccessToken,
      refreshAccessToken: widget.auth.refreshAccessToken,
    );
    _load();
    _autoRefreshTimer = Timer.periodic(
      const Duration(seconds: 20),
      (_) => _load(showLoading: false),
    );
  }

  @override
  void dispose() {
    _autoRefreshTimer?.cancel();
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      _load(showLoading: false);
    }
  }

  Future<void> _load({bool showLoading = true}) async {
    if (showLoading) {
      setState(() {
        _loading = true;
        _error = null;
      });
    }
    try {
      final list = await _api.fetchNotifications();
      if (!mounted) return;
      setState(() {
        _items = list;
        if (showLoading) _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      if (!showLoading) return;
      setState(() {
        _error = _api.messageFromError(e);
        if (showLoading) _loading = false;
      });
    }
  }

  Future<void> _markAllRead() async {
    try {
      await _api.markAllNotificationsRead();
      if (!mounted) return;
      setState(() {
        _items = _items.map((n) => AppNotification(
          id: n.id,
          title: n.title,
          message: n.message,
          link: n.link,
          read: true,
          createdAt: n.createdAt,
        )).toList();
        _changed = true;
      });
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(_api.messageFromError(e))),
      );
    }
  }

  Future<void> _markOneRead(AppNotification item) async {
    if (item.read) return;
    try {
      await _api.markNotificationRead(item.id);
      if (!mounted) return;
      setState(() {
        _items = _items.map((n) {
          if (n.id != item.id) return n;
          return AppNotification(
            id: n.id,
            title: n.title,
            message: n.message,
            link: n.link,
            read: true,
            createdAt: n.createdAt,
          );
        }).toList();
        _changed = true;
      });
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(_api.messageFromError(e))),
      );
    }
  }

  int? _extractRequestId(String? link) {
    if (link == null || link.trim().isEmpty) return null;
    final uri = Uri.tryParse(link.trim());
    final segments = (uri?.pathSegments ?? const <String>[])
        .where((s) => s.trim().isNotEmpty)
        .toList();
    for (var i = segments.length - 1; i >= 0; i--) {
      final parsed = int.tryParse(segments[i]);
      if (parsed != null) return parsed;
    }
    return null;
  }

  Future<void> _openNotification(AppNotification item) async {
    await _markOneRead(item);
    final requestId = _extractRequestId(item.link);
    if (requestId == null) return;
    try {
      final task = await _api.fetchRequestDetail(requestId);
      if (!mounted) return;
      await Navigator.push<void>(
        context,
        MaterialPageRoute<void>(
          builder: (context) => TaskDetailScreen(task: task, auth: widget.auth),
        ),
      );
      _changed = true;
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(_api.messageFromError(e))),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop) Navigator.of(context).pop(_changed);
      },
      child: Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_rounded),
          onPressed: () => Navigator.of(context).pop(_changed),
        ),
        title: const Text('Notifications'),
        actions: [
          TextButton(
            onPressed: _items.any((i) => !i.read) ? _markAllRead : null,
            child: const Text('Mark all read'),
          ),
        ],
      ),
      body: _loading
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
                        FilledButton(onPressed: _load, child: const Text('Retry')),
                      ],
                    ),
                  ),
                )
              : _items.isEmpty
                  ? Center(
                      child: Text(
                        'No notifications yet.',
                        style: t.bodyMedium?.copyWith(color: AppColors.slate500),
                      ),
                    )
                  : RefreshIndicator(
                      onRefresh: _load,
                      child: ListView.separated(
                        padding: const EdgeInsets.all(16),
                        itemCount: _items.length,
                        separatorBuilder: (_, __) => const SizedBox(height: 10),
                        itemBuilder: (context, index) {
                          final item = _items[index];
                          return Card(
                            elevation: 0,
                            color: item.read ? Colors.white : AppColors.primary.withOpacity(0.05),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(12),
                              side: const BorderSide(color: AppColors.slate200),
                            ),
                            child: InkWell(
                              borderRadius: BorderRadius.circular(12),
                              onTap: () => _openNotification(item),
                              child: Padding(
                                padding: const EdgeInsets.all(14),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Row(
                                      children: [
                                        Expanded(
                                          child: Text(
                                            item.title,
                                            style: t.titleSmall?.copyWith(
                                              fontWeight: FontWeight.w700,
                                            ),
                                          ),
                                        ),
                                        if (!item.read)
                                          Container(
                                            width: 8,
                                            height: 8,
                                            decoration: const BoxDecoration(
                                              color: AppColors.primary,
                                              shape: BoxShape.circle,
                                            ),
                                          ),
                                      ],
                                    ),
                                    const SizedBox(height: 6),
                                    Text(
                                      item.message,
                                      style: t.bodySmall?.copyWith(color: AppColors.slate600),
                                    ),
                                    if (item.createdAt != null) ...[
                                      const SizedBox(height: 8),
                                      Text(
                                        item.createdAt!.toLocal().toString().replaceFirst('.000', ''),
                                        style: t.labelSmall?.copyWith(color: AppColors.slate500),
                                      ),
                                    ],
                                  ],
                                ),
                              ),
                            ),
                          );
                        },
                      ),
                    ),
      ),
    );
  }
}

