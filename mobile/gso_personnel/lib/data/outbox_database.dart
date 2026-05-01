import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:path/path.dart' as p;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sqflite/sqflite.dart';

class PendingOp {
  PendingOp({
    required this.id,
    required this.kind,
    required this.endpoint,
    required this.method,
    required this.payload,
    required this.idempotencyKey,
    required this.retryCount,
    required this.nextRetryAfterMs,
    required this.createdAtMs,
  });

  final String id;
  final String kind;
  final String endpoint;
  final String method;
  final Map<String, dynamic> payload;
  final String idempotencyKey;
  final int retryCount;
  final int? nextRetryAfterMs;
  final int createdAtMs;
}

/// Local queue for mutations when offline. SQLite on mobile/desktop; SharedPreferences on web.
class OutboxDatabase {
  OutboxDatabase._();
  static final OutboxDatabase instance = OutboxDatabase._();

  static const _dbName = 'gso_personnel.db';
  static const _dbVersion = 1;
  static const _webPrefsKey = 'gso_personnel_pending_ops_v1';

  Database? _db;

  Future<Database> get database async {
    if (kIsWeb) {
      throw UnsupportedError('Outbox SQLite is not used on web');
    }
    if (_db != null) return _db!;
    _db = await _open();
    return _db!;
  }

  Future<Database> _open() async {
    final dir = await getDatabasesPath();
    final path = p.join(dir, _dbName);
    return openDatabase(
      path,
      version: _dbVersion,
      onCreate: (db, version) async {
        await db.execute('''
CREATE TABLE pending_ops (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  endpoint TEXT NOT NULL,
  method TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  idempotency_key TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  error_message TEXT,
  retry_count INTEGER NOT NULL DEFAULT 0,
  next_retry_after_ms INTEGER,
  created_at_ms INTEGER NOT NULL
)
''');
      },
    );
  }

  /// Returns number of rows with status pending or syncing.
  Future<int> pendingCount() async {
    if (kIsWeb) return _webPendingCount();
    final db = await database;
    final rows = await db.rawQuery(
      "SELECT COUNT(*) AS c FROM pending_ops WHERE status IN ('pending', 'syncing')",
    );
    return Sqflite.firstIntValue(rows) ?? 0;
  }

  /// Returns pending operations that are due for retry, oldest first.
  Future<List<PendingOp>> dueOps({int limit = 25}) async {
    if (kIsWeb) return _webDueOps(limit: limit);
    final db = await database;
    final now = DateTime.now().millisecondsSinceEpoch;
    final rows = await db.query(
      'pending_ops',
      where:
          "status = 'pending' AND (next_retry_after_ms IS NULL OR next_retry_after_ms <= ?)",
      whereArgs: [now],
      orderBy: 'created_at_ms ASC',
      limit: limit,
    );
    return rows.map(_rowToOp).toList();
  }

  Future<void> markSyncing(String id) async {
    if (kIsWeb) return _webMarkSyncing(id);
    final db = await database;
    await db.update(
      'pending_ops',
      {'status': 'syncing', 'error_message': null},
      where: 'id = ?',
      whereArgs: [id],
    );
  }

  Future<void> markSucceeded(String id) async {
    if (kIsWeb) return _webMarkSucceeded(id);
    final db = await database;
    await db.delete('pending_ops', where: 'id = ?', whereArgs: [id]);
  }

  Future<void> markFailed({
    required String id,
    required String errorMessage,
    required int retryCount,
    required int nextRetryAfterMs,
  }) async {
    if (kIsWeb) {
      return _webMarkFailed(
        id: id,
        errorMessage: errorMessage,
        retryCount: retryCount,
        nextRetryAfterMs: nextRetryAfterMs,
      );
    }
    final db = await database;
    await db.update(
      'pending_ops',
      {
        'status': 'pending',
        'error_message': errorMessage,
        'retry_count': retryCount,
        'next_retry_after_ms': nextRetryAfterMs,
      },
      where: 'id = ?',
      whereArgs: [id],
    );
  }

  Future<void> enqueue({
    required String kind,
    required String endpoint,
    String method = 'POST',
    required Map<String, dynamic> payload,
    required String idempotencyKey,
  }) async {
    if (kIsWeb) {
      return _webEnqueue(
        kind: kind,
        endpoint: endpoint,
        method: method,
        payload: payload,
        idempotencyKey: idempotencyKey,
      );
    }
    final db = await database;
    await db.insert('pending_ops', {
      'id': idempotencyKey,
      'kind': kind,
      'endpoint': endpoint,
      'method': method,
      'payload_json': jsonEncode(payload),
      'idempotency_key': idempotencyKey,
      'status': 'pending',
      'retry_count': 0,
      'next_retry_after_ms': null,
      'created_at_ms': DateTime.now().millisecondsSinceEpoch,
    }, conflictAlgorithm: ConflictAlgorithm.replace);
  }

  PendingOp _rowToOp(Map<String, dynamic> r) {
    final payloadJson = (r['payload_json'] as String?) ?? '{}';
    return PendingOp(
      id: r['id'] as String,
      kind: r['kind'] as String,
      endpoint: r['endpoint'] as String,
      method: r['method'] as String,
      payload: Map<String, dynamic>.from(jsonDecode(payloadJson) as Map),
      idempotencyKey: r['idempotency_key'] as String,
      retryCount: (r['retry_count'] as int?) ?? 0,
      nextRetryAfterMs: (r['next_retry_after_ms'] as num?)?.toInt(),
      createdAtMs: r['created_at_ms'] as int,
    );
  }

  PendingOp _mapToOp(Map<String, dynamic> m) {
    return _rowToOp(Map<String, dynamic>.from(m));
  }

  Future<List<Map<String, dynamic>>> _webLoadRows() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_webPrefsKey);
    if (raw == null || raw.isEmpty) return [];
    final decoded = jsonDecode(raw);
    if (decoded is! List<dynamic>) return [];
    return decoded
        .map((e) => Map<String, dynamic>.from(e as Map))
        .toList();
  }

  Future<void> _webSaveRows(List<Map<String, dynamic>> rows) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_webPrefsKey, jsonEncode(rows));
  }

  Future<int> _webPendingCount() async {
    final rows = await _webLoadRows();
    return rows.where((r) {
      final s = (r['status'] as String?) ?? 'pending';
      return s == 'pending' || s == 'syncing';
    }).length;
  }

  Future<List<PendingOp>> _webDueOps({required int limit}) async {
    final rows = await _webLoadRows();
    final now = DateTime.now().millisecondsSinceEpoch;
    final filtered = rows.where((r) {
      if ((r['status'] as String? ?? '') != 'pending') return false;
      final next = r['next_retry_after_ms'];
      if (next == null) return true;
      return (next as num).toInt() <= now;
    }).toList()
      ..sort((a, b) => ((a['created_at_ms'] as num).toInt())
          .compareTo((b['created_at_ms'] as num).toInt()));
    return filtered.take(limit).map(_mapToOp).toList();
  }

  Future<void> _webMarkSyncing(String id) async {
    final rows = await _webLoadRows();
    for (final r in rows) {
      if (r['id'] == id) {
        r['status'] = 'syncing';
        r.remove('error_message');
      }
    }
    await _webSaveRows(rows);
  }

  Future<void> _webMarkSucceeded(String id) async {
    final rows = await _webLoadRows();
    rows.removeWhere((r) => r['id'] == id);
    await _webSaveRows(rows);
  }

  Future<void> _webMarkFailed({
    required String id,
    required String errorMessage,
    required int retryCount,
    required int nextRetryAfterMs,
  }) async {
    final rows = await _webLoadRows();
    for (final r in rows) {
      if (r['id'] == id) {
        r['status'] = 'pending';
        r['error_message'] = errorMessage;
        r['retry_count'] = retryCount;
        r['next_retry_after_ms'] = nextRetryAfterMs;
      }
    }
    await _webSaveRows(rows);
  }

  Future<void> _webEnqueue({
    required String kind,
    required String endpoint,
    required String method,
    required Map<String, dynamic> payload,
    required String idempotencyKey,
  }) async {
    final rows = await _webLoadRows();
    rows.removeWhere((r) => r['id'] == idempotencyKey);
    rows.add({
      'id': idempotencyKey,
      'kind': kind,
      'endpoint': endpoint,
      'method': method,
      'payload_json': jsonEncode(payload),
      'idempotency_key': idempotencyKey,
      'status': 'pending',
      'retry_count': 0,
      'next_retry_after_ms': null,
      'created_at_ms': DateTime.now().millisecondsSinceEpoch,
    });
    await _webSaveRows(rows);
  }
}
