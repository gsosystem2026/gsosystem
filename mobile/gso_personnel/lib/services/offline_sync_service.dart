import 'dart:async';

import 'package:dio/dio.dart';

import '../data/outbox_database.dart';
import 'api_client.dart';

class OfflineSyncService {
  OfflineSyncService._();
  static final OfflineSyncService instance = OfflineSyncService._();

  AccessTokenProvider? _accessToken;
  Timer? _timer;
  bool _running = false;

  void bind({required AccessTokenProvider accessToken}) {
    _accessToken = accessToken;
    _timer ??= Timer.periodic(const Duration(seconds: 20), (_) => syncOnce());
  }

  Future<void> syncOnce() async {
    if (_running) return;
    final accessToken = _accessToken;
    if (accessToken == null) return;

    _running = true;
    try {
      final api = ApiClient(accessToken: accessToken);
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

