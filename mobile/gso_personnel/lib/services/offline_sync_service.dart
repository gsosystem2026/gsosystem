import 'dart:async';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:dio/dio.dart';

import '../data/outbox_database.dart';
import 'api_client.dart';

class OfflineSyncService {
  OfflineSyncService._();
  static final OfflineSyncService instance = OfflineSyncService._();

  AccessTokenProvider? _accessToken;
  RefreshAccessToken? _refreshAccessToken;
  Timer? _timer;
  StreamSubscription<List<ConnectivityResult>>? _connectivitySub;
  ConnectivityResult _connectivity = ConnectivityResult.none;
  bool _running = false;

  void bind({
    required AccessTokenProvider accessToken,
    RefreshAccessToken? refreshAccessToken,
  }) {
    _accessToken = accessToken;
    _refreshAccessToken = refreshAccessToken;
    _timer ??= Timer.periodic(const Duration(seconds: 20), (_) => syncOnce());
    _connectivitySub ??= Connectivity().onConnectivityChanged.listen(_handleConnectivity);
    Connectivity().checkConnectivity().then((results) {
      if (results.isEmpty) return;
      _connectivity = results.first;
      if (_isOnline) {
        syncOnce();
      }
    });
  }

  void _handleConnectivity(List<ConnectivityResult> results) {
    if (results.isEmpty) return;
    final previous = _isOnline;
    _connectivity = results.first;
    if (!previous && _isOnline) {
      syncOnce();
    }
  }

  bool get _isOnline =>
      _connectivity != ConnectivityResult.none &&
      _connectivity != ConnectivityResult.bluetooth;

  Future<void> triggerSyncNow() => syncOnce();

  Future<void> syncOnce() async {
    if (_running) return;
    final accessToken = _accessToken;
    if (accessToken == null) return;

    _running = true;
    try {
      final api = ApiClient(
        accessToken: accessToken,
        refreshAccessToken: _refreshAccessToken,
      );
      final due = await OutboxDatabase.instance.dueOps(limit: 20);
      for (final op in due) {
        await OutboxDatabase.instance.markSyncing(op.id);
        try {
          if (op.kind == 'work_status') {
            final id = (op.payload['request_id'] as num).toInt();
            final status = op.payload['status'] as String;
            await api.postWorkStatus(
              id,
              status,
              idempotencyKey: op.idempotencyKey,
            );
            await OutboxDatabase.instance.markSucceeded(op.id);
            continue;
          }

          // Unknown op kind: drop it to avoid a permanent sync loop.
          await OutboxDatabase.instance.markSucceeded(op.id);
        } catch (e) {
          if (e is DioException && ApiClient.shouldDropOutboxOpAfterFailure(e)) {
            await OutboxDatabase.instance.markSucceeded(op.id);
            continue;
          }
          final nextRetryCount = op.retryCount + 1;
          if (nextRetryCount > 24) {
            await OutboxDatabase.instance.markSucceeded(op.id);
            continue;
          }
          final msg = api.messageFromError(e);
          final backoffSeconds = switch (nextRetryCount) {
            <= 1 => 5,
            2 => 15,
            3 => 30,
            4 => 60,
            _ => 120,
          };
          final nextRetryAfterMs =
              DateTime.now().add(Duration(seconds: backoffSeconds)).millisecondsSinceEpoch;
          await OutboxDatabase.instance.markFailed(
            id: op.id,
            errorMessage: msg,
            retryCount: nextRetryCount,
            nextRetryAfterMs: nextRetryAfterMs,
          );
        }
      }
    } on DioException {
      // If we're offline, Dio will throw; we just try again on the next tick.
    } finally {
      _running = false;
    }
  }
}

