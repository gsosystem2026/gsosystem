import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:uuid/uuid.dart';

import '../data/outbox_database.dart';
import '../models/request_task.dart';
import '../services/api_client.dart';
import '../services/auth_repository.dart';
import '../theme/app_colors.dart';

/// Request detail + personnel work status actions (API validates transitions).
class TaskDetailScreen extends StatefulWidget {
  const TaskDetailScreen({
    super.key,
    required this.task,
    required this.auth,
  });

  final RequestTask task;
  final AuthRepository auth;

  @override
  State<TaskDetailScreen> createState() => _TaskDetailScreenState();
}

class _TaskDetailScreenState extends State<TaskDetailScreen> {
  static const _uuid = Uuid();
  late RequestTask _task;
  late ApiClient _api;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _task = widget.task;
    _api = ApiClient(accessToken: widget.auth.readAccessToken);
  }

  Future<void> _enqueueStatus(String status) async {
    final key = _uuid.v4();
    await OutboxDatabase.instance.enqueue(
      kind: 'work_status',
      endpoint: '/requests/${_task.id}/status/',
      method: 'POST',
      payload: {
        'request_id': _task.id,
        'status': status,
      },
      idempotencyKey: key,
    );
  }

  Future<void> _applyStatus(String status) async {
    setState(() => _busy = true);
    try {
      final data = await _api.postWorkStatus(_task.id, status);
      final updated = RequestTask.fromJson(data);
      if (!mounted) return;
      setState(() => _task = updated);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Status: ${updated.statusDisplay}')),
      );
    } on DioException catch (e) {
      if (!mounted) return;
      if (ApiClient.isEnqueueableNetworkFailure(e)) {
        await _enqueueStatus(status);
        if (!mounted) return;
        final label = RequestTask.labelForStatusCode(status);
        setState(() {
          _task = _task.copyWith(
            status: status,
            statusDisplay: '$label (pending sync)',
            updatedAt: DateTime.now(),
          );
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              '$label queued — updates when you are back online.',
            ),
          ),
        );
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(_api.messageFromError(e))),
        );
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Update failed: $e')),
      );
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop) Navigator.of(context).pop(_task);
      },
      child: Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_rounded),
          onPressed: () => Navigator.of(context).pop(_task),
        ),
        title: Text(_task.displayId),
      ),
      body: Stack(
        children: [
          ListView(
            padding: const EdgeInsets.all(20),
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      _task.statusDisplay,
                      style: t.titleMedium?.copyWith(
                        fontWeight: FontWeight.w700,
                        color: AppColors.primary,
                      ),
                    ),
                  ),
                  if (_task.isEmergency)
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: Colors.red.shade50,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        'Emergency',
                        style: t.labelSmall?.copyWith(
                          color: Colors.red.shade800,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ),
                ],
              ),
              const SizedBox(height: 16),
              _label(context, 'Purpose / description'),
              Text(_task.description?.trim().isNotEmpty == true ? _task.description! : '—', style: t.bodyMedium),
              const SizedBox(height: 14),
              _label(context, 'Location'),
              Text(_task.location?.trim().isNotEmpty == true ? _task.location! : '—', style: t.bodyMedium),
              const SizedBox(height: 14),
              _label(context, 'Requestor'),
              Text(_task.requestorName ?? '—', style: t.bodyMedium),
              if (_task.unitName != null) ...[
                const SizedBox(height: 14),
                _label(context, 'Unit'),
                Text(_task.unitName!, style: t.bodyMedium),
              ],
              const SizedBox(height: 28),
              Text(
                'Update work status',
                style: t.titleSmall?.copyWith(fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 8),
              Text(
                'Choose the next step. The server will reject invalid transitions.',
                style: t.bodySmall?.copyWith(color: AppColors.slate500),
              ),
              const SizedBox(height: 16),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  _StatusChip(
                    label: 'Inspection',
                    onPressed: _busy ? null : () => _applyStatus('INSPECTION'),
                  ),
                  _StatusChip(
                    label: 'In progress',
                    onPressed: _busy ? null : () => _applyStatus('IN_PROGRESS'),
                  ),
                  _StatusChip(
                    label: 'On hold',
                    onPressed: _busy ? null : () => _applyStatus('ON_HOLD'),
                  ),
                  _StatusChip(
                    label: 'Done working',
                    onPressed: _busy ? null : () => _applyStatus('DONE_WORKING'),
                  ),
                ],
              ),
            ],
          ),
          if (_busy)
            const Positioned.fill(
              child: ColoredBox(
                color: Color(0x33000000),
                child: Center(
                  child: CircularProgressIndicator(),
                ),
              ),
            ),
        ],
      ),
    ),
    );
  }

  Widget _label(BuildContext context, String text) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Text(
        text,
        style: Theme.of(context).textTheme.labelMedium?.copyWith(
              color: AppColors.slate500,
              fontWeight: FontWeight.w600,
            ),
      ),
    );
  }
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({
    required this.label,
    required this.onPressed,
  });

  final String label;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    return FilledButton.tonal(
      onPressed: onPressed,
      style: FilledButton.styleFrom(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      ),
      child: Text(label),
    );
  }
}
