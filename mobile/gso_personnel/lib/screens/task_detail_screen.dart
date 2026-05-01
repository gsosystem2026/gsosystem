import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:uuid/uuid.dart';

import '../data/outbox_database.dart';
import '../models/material_request_item.dart';
import '../models/request_message.dart';
import '../models/request_task.dart';
import '../services/api_client.dart';
import '../services/auth_repository.dart';
import '../services/offline_sync_service.dart';
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
  final _messageCtrl = TextEditingController();
  final _qtyCtrl = TextEditingController(text: '1');
  final _materialNotesCtrl = TextEditingController();
  List<RequestMessageItem> _messages = const [];
  List<MaterialRequestItem> _materialRequests = const [];
  List<Map<String, dynamic>> _inventoryItems = const [];
  int? _selectedItemId;
  bool _loadingMaterials = false;
  bool _submittingMaterial = false;
  bool _loadingMessages = false;
  bool _sendingMessage = false;
  Timer? _chatPollTimer;

  bool get _requiresInspectionFirst {
    final unit = (_task.unitName ?? '').toLowerCase();
    return unit.contains('repair') || unit.contains('electrical');
  }

  List<_StatusAction> _availableActions() {
    switch (_task.status) {
      case 'DIRECTOR_APPROVED':
        if (_requiresInspectionFirst) {
          return const [
            _StatusAction(
              label: 'Start inspection',
              code: 'INSPECTION',
              variant: _StatusActionVariant.inspection,
            ),
            _StatusAction(
              label: 'Start work',
              code: 'IN_PROGRESS',
              variant: _StatusActionVariant.primary,
            ),
          ];
        }
        return const [
          _StatusAction(
            label: 'Start work',
            code: 'IN_PROGRESS',
            variant: _StatusActionVariant.primary,
          ),
          _StatusAction(
            label: 'On hold',
            code: 'ON_HOLD',
            variant: _StatusActionVariant.secondary,
          ),
        ];
      case 'INSPECTION':
        return const [
          _StatusAction(
            label: 'Start work',
            code: 'IN_PROGRESS',
            variant: _StatusActionVariant.primary,
          ),
          _StatusAction(
            label: 'On hold',
            code: 'ON_HOLD',
            variant: _StatusActionVariant.secondary,
          ),
        ];
      case 'IN_PROGRESS':
        return const [
          _StatusAction(
            label: 'On hold',
            code: 'ON_HOLD',
            variant: _StatusActionVariant.secondary,
          ),
          _StatusAction(
            label: 'Done working',
            code: 'DONE_WORKING',
            variant: _StatusActionVariant.success,
          ),
        ];
      case 'ON_HOLD':
        return const [
          _StatusAction(
            label: 'Continue work',
            code: 'IN_PROGRESS',
            variant: _StatusActionVariant.primary,
          ),
          _StatusAction(
            label: 'Done working',
            code: 'DONE_WORKING',
            variant: _StatusActionVariant.success,
          ),
        ];
      default:
        return const [];
    }
  }

  @override
  void initState() {
    super.initState();
    _task = widget.task;
    _api = ApiClient(
      accessToken: widget.auth.readAccessToken,
      refreshAccessToken: widget.auth.refreshAccessToken,
    );
    _loadMaterialData();
    _loadMessages();
    _chatPollTimer = Timer.periodic(
      const Duration(seconds: 15),
      (_) => _loadMessages(showLoading: false),
    );
  }

  @override
  void dispose() {
    _chatPollTimer?.cancel();
    _messageCtrl.dispose();
    _qtyCtrl.dispose();
    _materialNotesCtrl.dispose();
    super.dispose();
  }

  Future<void> _loadMaterialData({bool showLoading = true}) async {
    if (showLoading) {
      setState(() => _loadingMaterials = true);
    }
    try {
      final inventory = await _api.fetchInventoryItems();
      final requests = await _api.fetchRequestMaterialRequests(_task.id);
      if (!mounted) return;
      final available = inventory
          .where((e) => ((e['quantity'] as num?)?.toInt() ?? 0) > 0)
          .toList();
      setState(() {
        _inventoryItems = available;
        _materialRequests = requests;
        final hasSelected = available.any(
          (it) => (it['id'] as num?)?.toInt() == _selectedItemId,
        );
        if (!hasSelected) {
          _selectedItemId = available.isEmpty ? null : (available.first['id'] as num?)?.toInt();
        }
        if (showLoading) _loadingMaterials = false;
      });
    } catch (_) {
      if (!mounted) return;
      if (showLoading) setState(() => _loadingMaterials = false);
    }
  }

  Future<void> _submitMaterialRequest() async {
    if (_submittingMaterial || _selectedItemId == null) return;
    final qty = int.tryParse(_qtyCtrl.text.trim()) ?? 0;
    if (qty <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Quantity must be at least 1.')),
      );
      return;
    }
    setState(() => _submittingMaterial = true);
    try {
      final item = await _api.submitMaterialRequest(
        requestId: _task.id,
        itemId: _selectedItemId!,
        quantity: qty,
        notes: _materialNotesCtrl.text,
      );
      if (!mounted) return;
      _qtyCtrl.text = '1';
      _materialNotesCtrl.clear();
      setState(() {
        _materialRequests = [item, ..._materialRequests];
        _submittingMaterial = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Material request submitted.')),
      );
    } catch (e) {
      if (!mounted) return;
      setState(() => _submittingMaterial = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(_api.messageFromError(e))),
      );
    }
  }

  Future<void> _loadMessages({bool showLoading = true}) async {
    if (showLoading) {
      setState(() => _loadingMessages = true);
    }
    try {
      final list = await _api.fetchRequestMessages(_task.id);
      if (!mounted) return;
      setState(() {
        _messages = list;
        if (showLoading) _loadingMessages = false;
      });
    } catch (_) {
      if (!mounted) return;
      if (showLoading) {
        setState(() => _loadingMessages = false);
      }
    }
  }

  Future<void> _sendMessage() async {
    final text = _messageCtrl.text.trim();
    if (text.isEmpty || _sendingMessage) return;
    setState(() => _sendingMessage = true);
    try {
      final item = await _api.postRequestMessage(_task.id, text);
      if (!mounted) return;
      _messageCtrl.clear();
      setState(() {
        _messages = [..._messages, item];
        _sendingMessage = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _sendingMessage = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(_api.messageFromError(e))),
      );
    }
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
    await OfflineSyncService.instance.triggerSyncNow();
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
              Container(
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: AppColors.slate200),
                ),
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
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
                    const SizedBox(height: 14),
                    _infoTile(context, 'Purpose / description', _task.description),
                    const SizedBox(height: 12),
                    _infoTile(context, 'Location', _task.location),
                    const SizedBox(height: 12),
                    _infoTile(context, 'Requestor', _task.requestorName),
                    if (_task.unitName != null) ...[
                      const SizedBox(height: 12),
                      _infoTile(context, 'Unit', _task.unitName),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: 14),
              Container(
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: AppColors.slate200),
                  ),
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Text(
                            'Request materials',
                            style: t.titleSmall?.copyWith(fontWeight: FontWeight.w700),
                          ),
                          const Spacer(),
                          IconButton(
                            tooltip: 'Refresh materials',
                            onPressed: _loadMaterialData,
                            icon: const Icon(Icons.refresh_rounded, size: 20),
                          ),
                        ],
                      ),
                      if (_loadingMaterials)
                        const Padding(
                          padding: EdgeInsets.symmetric(vertical: 10),
                          child: Center(child: CircularProgressIndicator()),
                        )
                      else ...[
                        DropdownButtonFormField<int>(
                          value: _selectedItemId,
                          items: _inventoryItems
                              .map(
                                (it) => DropdownMenuItem<int>(
                                  value: (it['id'] as num).toInt(),
                                  child: Text(
                                    '${it['name']} (stock: ${it['quantity']} ${it['unit_of_measure'] ?? ''})',
                                  ),
                                ),
                              )
                              .toList(),
                          onChanged: _inventoryItems.isEmpty
                              ? null
                              : (v) => setState(() => _selectedItemId = v),
                          decoration: const InputDecoration(
                            labelText: 'Item',
                            border: OutlineInputBorder(),
                          ),
                        ),
                        const SizedBox(height: 10),
                        Row(
                          children: [
                            SizedBox(
                              width: 110,
                              child: TextField(
                                controller: _qtyCtrl,
                                keyboardType: TextInputType.number,
                                decoration: const InputDecoration(
                                  labelText: 'Quantity',
                                  border: OutlineInputBorder(),
                                ),
                              ),
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: TextField(
                                controller: _materialNotesCtrl,
                                decoration: const InputDecoration(
                                  labelText: 'Notes (optional)',
                                  border: OutlineInputBorder(),
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 10),
                        Align(
                          alignment: Alignment.centerLeft,
                          child: FilledButton.icon(
                            onPressed: (_submittingMaterial || _inventoryItems.isEmpty)
                                ? null
                                : _submitMaterialRequest,
                            icon: _submittingMaterial
                                ? const SizedBox(
                                    width: 14,
                                    height: 14,
                                    child: CircularProgressIndicator(strokeWidth: 2),
                                  )
                                : const Icon(Icons.add_shopping_cart_rounded),
                            label: const Text('Submit material request'),
                          ),
                        ),
                        const SizedBox(height: 12),
                        Text(
                          'Request history',
                          style: t.labelLarge?.copyWith(
                            color: AppColors.slate600,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        const SizedBox(height: 6),
                        if (_materialRequests.isEmpty)
                          Text(
                            'No material requests yet.',
                            style: t.bodySmall?.copyWith(color: AppColors.slate500),
                          )
                        else
                          ..._materialRequests.take(5).map(
                                (mr) => Padding(
                                  padding: const EdgeInsets.only(bottom: 8),
                                  child: Container(
                                    width: double.infinity,
                                    padding: const EdgeInsets.all(10),
                                    decoration: BoxDecoration(
                                      color: AppColors.slate100,
                                      borderRadius: BorderRadius.circular(10),
                                      border: Border.all(color: AppColors.slate200),
                                    ),
                                    child: Text(
                                      '${mr.itemName} x${mr.quantity} • ${mr.statusDisplay}',
                                      style: t.bodySmall,
                                    ),
                                  ),
                                ),
                              ),
                      ],
                    ],
                  ),
                ),
              const SizedBox(height: 14),
              Container(
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: AppColors.slate200),
                ),
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
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
              Builder(
                builder: (context) {
                  final actions = _availableActions();
                  if (actions.isEmpty) {
                    return Container(
                      width: double.infinity,
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                      decoration: BoxDecoration(
                        color: AppColors.slate100,
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(color: AppColors.slate200),
                      ),
                      child: Text(
                        'No next action available for the current status.',
                        style: t.bodySmall?.copyWith(
                          color: AppColors.slate600,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    );
                  }
                  return Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: actions
                        .map(
                          (a) => _StatusChip(
                            label: a.label,
                            variant: a.variant,
                            onPressed: _busy ? null : () => _applyStatus(a.code),
                          ),
                        )
                        .toList(),
                  );
                },
              ),
                  ],
                ),
              ),
              const SizedBox(height: 14),
              Container(
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: AppColors.slate200),
                ),
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Text(
                          'Request chat',
                          style: t.titleSmall?.copyWith(fontWeight: FontWeight.w700),
                        ),
                        const Spacer(),
                        IconButton(
                          tooltip: 'Refresh chat',
                          onPressed: _loadMessages,
                          icon: const Icon(Icons.refresh_rounded, size: 20),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    if (_loadingMessages)
                      const Padding(
                        padding: EdgeInsets.symmetric(vertical: 12),
                        child: Center(child: CircularProgressIndicator()),
                      )
                    else if (_messages.isEmpty)
                      Text(
                        'No messages yet.',
                        style: t.bodySmall?.copyWith(color: AppColors.slate500),
                      )
                    else
                      Container(
                        constraints: const BoxConstraints(maxHeight: 220),
                        child: ListView.separated(
                          shrinkWrap: true,
                          itemCount: _messages.length,
                          separatorBuilder: (_, __) => const SizedBox(height: 8),
                          itemBuilder: (context, index) {
                            final m = _messages[index];
                            return Container(
                              padding: const EdgeInsets.all(10),
                              decoration: BoxDecoration(
                                color: AppColors.slate100,
                                borderRadius: BorderRadius.circular(10),
                                border: Border.all(color: AppColors.slate200),
                              ),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    m.userName.isEmpty ? 'Staff' : m.userName,
                                    style: t.labelSmall?.copyWith(
                                      color: AppColors.slate600,
                                      fontWeight: FontWeight.w700,
                                    ),
                                  ),
                                  const SizedBox(height: 3),
                                  Text(m.message, style: t.bodyMedium),
                                ],
                              ),
                            );
                          },
                        ),
                      ),
                    const SizedBox(height: 10),
                    Row(
                      children: [
                        Expanded(
                          child: TextField(
                            controller: _messageCtrl,
                            minLines: 1,
                            maxLines: 3,
                            decoration: const InputDecoration(
                              hintText: 'Type a message...',
                              border: OutlineInputBorder(),
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        FilledButton(
                          onPressed: _sendingMessage ? null : _sendMessage,
                          child: _sendingMessage
                              ? const SizedBox(
                                  width: 16,
                                  height: 16,
                                  child: CircularProgressIndicator(strokeWidth: 2),
                                )
                              : const Icon(Icons.send_rounded),
                        ),
                      ],
                    ),
                  ],
                ),
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

  Widget _infoTile(BuildContext context, String label, String? value) {
    final t = Theme.of(context).textTheme;
    final v = (value ?? '').trim();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: t.labelLarge?.copyWith(
            color: AppColors.slate500,
            fontWeight: FontWeight.w700,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          v.isEmpty ? '—' : v,
          style: t.bodyLarge?.copyWith(
            color: AppColors.slate900,
            height: 1.3,
          ),
        ),
      ],
    );
  }
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({
    required this.label,
    required this.variant,
    required this.onPressed,
  });

  final String label;
  final _StatusActionVariant variant;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    const stylePadding = EdgeInsets.symmetric(horizontal: 14, vertical: 10);
    switch (variant) {
      case _StatusActionVariant.secondary:
        return OutlinedButton(
          onPressed: onPressed,
          style: OutlinedButton.styleFrom(
            padding: stylePadding,
            foregroundColor: AppColors.slate700,
            side: const BorderSide(color: AppColors.slate200),
          ),
          child: Text(label),
        );
      case _StatusActionVariant.primary:
        return FilledButton(
          onPressed: onPressed,
          style: FilledButton.styleFrom(
            padding: stylePadding,
            backgroundColor: AppColors.primary,
            foregroundColor: Colors.white,
          ),
          child: Text(label),
        );
      case _StatusActionVariant.success:
        return FilledButton(
          onPressed: onPressed,
          style: FilledButton.styleFrom(
            padding: stylePadding,
            backgroundColor: Colors.green.shade600,
            foregroundColor: Colors.white,
          ),
          child: Text(label),
        );
      case _StatusActionVariant.inspection:
        return FilledButton(
          onPressed: onPressed,
          style: FilledButton.styleFrom(
            padding: stylePadding,
            backgroundColor: Colors.cyan.shade600,
            foregroundColor: Colors.white,
          ),
          child: Text(label),
        );
    }
  }
}

class _StatusAction {
  const _StatusAction({
    required this.label,
    required this.code,
    required this.variant,
  });

  final String label;
  final String code;
  final _StatusActionVariant variant;
}

enum _StatusActionVariant { primary, secondary, success, inspection }
