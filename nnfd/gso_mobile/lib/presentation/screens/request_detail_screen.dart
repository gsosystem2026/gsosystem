import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app.dart';
import '../../data/models/request.dart';
import '../../data/models/user.dart';
import '../../data/user_repository.dart';

final requestDetailProvider =
    FutureProvider.family<GsoRequest?, int>((ref, id) async {
  try {
    final repo = ref.read(requestRepositoryProvider);
    return await repo.getRequest(id);
  } catch (_) {
    return null;
  }
});

class RequestDetailScreen extends ConsumerStatefulWidget {
  final int requestId;

  const RequestDetailScreen({super.key, required this.requestId});

  @override
  ConsumerState<RequestDetailScreen> createState() => _RequestDetailScreenState();
}

class _RequestDetailScreenState extends ConsumerState<RequestDetailScreen> {
  bool _actionLoading = false;

  Future<void> _runAction(Future<void> Function() fn) async {
    if (_actionLoading) return;
    setState(() => _actionLoading = true);
    try {
      await fn();
      if (mounted) {
        ref.invalidate(requestDetailProvider(widget.requestId));
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Done')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _actionLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final requestAsync = ref.watch(requestDetailProvider(widget.requestId));
    final userAsync = ref.watch(currentUserProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Request Detail'),
      ),
      body: requestAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('Error: $e'),
              const SizedBox(height: 16),
              TextButton(
                onPressed: () =>
                    ref.invalidate(requestDetailProvider(widget.requestId)),
                child: const Text('Retry'),
              ),
            ],
          ),
        ),
        data: (request) {
          if (request == null) {
            return const Center(child: Text('Request not found.'));
          }
          final user = userAsync.valueOrNull;
          return SingleChildScrollView(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                _Section(
                  title: 'Request',
                  children: [
                    _Row(label: 'ID', value: request.displayId),
                    _Row(label: 'Title', value: request.title),
                    _Row(label: 'Status', value: request.statusDisplay),
                    _Row(label: 'Unit', value: request.unitName ?? '—'),
                    if (request.description.isNotEmpty)
                      _Row(label: 'Description', value: request.description),
                  ],
                ),
                const SizedBox(height: 16),
                _Section(
                  title: 'Request type',
                  children: [
                    _Row(label: 'Labor', value: request.labor ? 'Yes' : 'No'),
                    _Row(
                        label: 'Materials',
                        value: request.materials ? 'Yes' : 'No'),
                    _Row(label: 'Others', value: request.others ? 'Yes' : 'No'),
                  ],
                ),
                if (request.customFullName != null ||
                    request.customEmail != null ||
                    request.customContactNumber != null) ...[
                  const SizedBox(height: 16),
                  _Section(
                    title: 'Contact',
                    children: [
                      if (request.customFullName != null)
                        _Row(
                            label: 'Name',
                            value: request.customFullName!),
                      if (request.customEmail != null)
                        _Row(
                            label: 'Email',
                            value: request.customEmail!),
                      if (request.customContactNumber != null)
                        _Row(
                            label: 'Contact',
                            value: request.customContactNumber!),
                    ],
                  ),
                ],
                if (request.assignments != null &&
                    request.assignments!.isNotEmpty) ...[
                  const SizedBox(height: 16),
                  const Text('Assigned personnel',
                      style: TextStyle(
                          fontWeight: FontWeight.bold, fontSize: 16)),
                  const SizedBox(height: 8),
                  ...request.assignments!
                      .map((a) => Padding(
                            padding: const EdgeInsets.only(bottom: 4),
                            child: Text('• ${a.personnelName}'),
                          )),
                ],
                if (request.createdAt != null) ...[
                  const SizedBox(height: 16),
                  _Section(
                    title: 'Dates',
                    children: [
                      _Row(label: 'Created', value: request.createdAt!),
                      if (request.updatedAt != null)
                        _Row(label: 'Updated', value: request.updatedAt!),
                    ],
                  ),
                ],
                if (request.attachment != null &&
                    request.attachment!.isNotEmpty) ...[
                  const SizedBox(height: 16),
                  const Text('Attachment',
                      style: TextStyle(
                          fontWeight: FontWeight.bold, fontSize: 16)),
                  const SizedBox(height: 8),
                  Text(
                    'Attachment available (download via web app)',
                    style: TextStyle(color: Colors.grey[600]),
                  ),
                ],
                if (user != null) ...[
                  const SizedBox(height: 24),
                  _StaffActions(
                    request: request,
                    user: user,
                    loading: _actionLoading,
                    onAssign: () => _showAssignDialog(context, request),
                    onApprove: () => _runAction(() async {
                      await ref
                          .read(requestRepositoryProvider)
                          .approveRequest(widget.requestId);
                    }),
                    onStatus: (status) => _runAction(() async {
                      await ref
                          .read(requestRepositoryProvider)
                          .updateWorkStatus(widget.requestId, status);
                    }),
                    onComplete: () => _runAction(() async {
                      await ref
                          .read(requestRepositoryProvider)
                          .completeRequest(widget.requestId);
                    }),
                    onReturnRework: () => _runAction(() async {
                      await ref
                          .read(requestRepositoryProvider)
                          .returnForRework(widget.requestId);
                    }),
                  ),
                ],
              ],
            ),
          );
        },
      ),
    );
  }

  void _showAssignDialog(BuildContext context, GsoRequest request) {
    showDialog<void>(
      context: context,
      builder: (ctx) => _AssignPersonnelDialog(
        requestId: widget.requestId,
        unitId: request.unit,
        onDone: () {
          Navigator.of(ctx).pop();
          ref.invalidate(requestDetailProvider(widget.requestId));
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Personnel assigned')),
          );
        },
      ),
    );
  }
}

class _StaffActions extends StatelessWidget {
  final GsoRequest request;
  final GsoUser user;
  final bool loading;
  final VoidCallback onAssign;
  final VoidCallback onApprove;
  final void Function(String status) onStatus;
  final VoidCallback onComplete;
  final VoidCallback onReturnRework;

  const _StaffActions({
    required this.request,
    required this.user,
    required this.loading,
    required this.onAssign,
    required this.onApprove,
    required this.onStatus,
    required this.onComplete,
    required this.onReturnRework,
  });

  @override
  Widget build(BuildContext context) {
    final buttons = <Widget>[];

    // Unit Head: Assign (SUBMITTED/ASSIGNED), Complete/Return (DONE_WORKING)
    if (user.isUnitHead &&
        user.unitId == request.unit &&
        (request.status == 'SUBMITTED' || request.status == 'ASSIGNED')) {
      buttons.add(ElevatedButton.icon(
        onPressed: loading ? null : onAssign,
        icon: const Icon(Icons.person_add),
        label: const Text('Assign personnel'),
      ));
    }
    if (user.isUnitHead &&
        user.unitId == request.unit &&
        request.status == 'DONE_WORKING') {
      buttons.add(ElevatedButton.icon(
        onPressed: loading ? null : onComplete,
        icon: const Icon(Icons.check_circle),
        label: const Text('Complete'),
      ));
      buttons.add(OutlinedButton.icon(
        onPressed: loading ? null : onReturnRework,
        icon: const Icon(Icons.replay),
        label: const Text('Return for rework'),
      ));
    }

    // Director/OIC: Approve (ASSIGNED)
    if (user.canApprove && request.status == 'ASSIGNED') {
      buttons.add(ElevatedButton.icon(
        onPressed: loading ? null : onApprove,
        icon: const Icon(Icons.thumb_up),
        label: const Text('Approve'),
      ));
    }

    // Personnel: work status (DIRECTOR_APPROVED, IN_PROGRESS, ON_HOLD)
    final isAssigned = request.assignments?.any((a) => a.personnelId == user.id) ?? false;
    if (user.isPersonnel && isAssigned) {
      if (request.status == 'DIRECTOR_APPROVED') {
        buttons.add(ElevatedButton.icon(
          onPressed: loading ? null : () => onStatus('IN_PROGRESS'),
          icon: const Icon(Icons.play_arrow),
          label: const Text('Start (In Progress)'),
        ));
        buttons.add(OutlinedButton.icon(
          onPressed: loading ? null : () => onStatus('ON_HOLD'),
          icon: const Icon(Icons.pause),
          label: const Text('On Hold'),
        ));
      } else if (request.status == 'IN_PROGRESS') {
        buttons.add(ElevatedButton.icon(
          onPressed: loading ? null : () => onStatus('DONE_WORKING'),
          icon: const Icon(Icons.done_all),
          label: const Text('Done working'),
        ));
        buttons.add(OutlinedButton.icon(
          onPressed: loading ? null : () => onStatus('ON_HOLD'),
          icon: const Icon(Icons.pause),
          label: const Text('On Hold'),
        ));
      } else if (request.status == 'ON_HOLD') {
        buttons.add(ElevatedButton.icon(
          onPressed: loading ? null : () => onStatus('IN_PROGRESS'),
          icon: const Icon(Icons.play_arrow),
          label: const Text('Resume (In Progress)'),
        ));
        buttons.add(OutlinedButton.icon(
          onPressed: loading ? null : () => onStatus('DONE_WORKING'),
          icon: const Icon(Icons.done_all),
          label: const Text('Done working'),
        ));
      }
    }

    if (buttons.isEmpty) return const SizedBox.shrink();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Text('Actions',
            style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: buttons,
        ),
      ],
    );
  }
}

class _AssignPersonnelDialog extends ConsumerStatefulWidget {
  final int requestId;
  final int unitId;
  final VoidCallback onDone;

  const _AssignPersonnelDialog({
    required this.requestId,
    required this.unitId,
    required this.onDone,
  });

  @override
  ConsumerState<_AssignPersonnelDialog> createState() =>
      _AssignPersonnelDialogState();
}

class _AssignPersonnelDialogState extends ConsumerState<_AssignPersonnelDialog> {
  List<PersonnelItem> _personnel = [];
  final Set<int> _selected = {};
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadPersonnel();
  }

  Future<void> _loadPersonnel() async {
    try {
      final list = await ref.read(userRepositoryProvider).getPersonnel(widget.unitId);
      if (mounted) {
        setState(() {
          _personnel = list;
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = '$e';
          _loading = false;
        });
      }
    }
  }

  Future<void> _submit() async {
    if (_selected.isEmpty) return;
    setState(() => _loading = true);
    try {
      await ref
          .read(requestRepositoryProvider)
          .assignPersonnel(widget.requestId, _selected.toList());
      if (mounted) widget.onDone();
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = '$e';
          _loading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Assign personnel'),
      content: SizedBox(
        width: double.maxFinite,
        child: _loading && _personnel.isEmpty
            ? const Center(child: CircularProgressIndicator())
            : _error != null && _personnel.isEmpty
                ? Text('Error: $_error')
                : Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      if (_error != null && _personnel.isNotEmpty)
                        Padding(
                          padding: const EdgeInsets.only(bottom: 8),
                          child: Text(
                            _error!,
                            style: TextStyle(color: Colors.red[700]),
                          ),
                        ),
                      if (_personnel.isEmpty && !_loading)
                        const Text('No personnel in this unit.'),
                      if (_personnel.isNotEmpty)
                        ..._personnel.map((p) => CheckboxListTile(
                              value: _selected.contains(p.id),
                              onChanged: _loading
                                  ? null
                                  : (v) {
                                      setState(() {
                                        if (v == true) {
                                          _selected.add(p.id);
                                        } else {
                                          _selected.remove(p.id);
                                        }
                                      });
                                    },
                              title: Text(p.displayName),
                            )),
                    ],
                  ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        ElevatedButton(
          onPressed: _loading || _selected.isEmpty
              ? null
              : () => _submit(),
          child: _loading && _personnel.isNotEmpty
              ? const SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : Text('Assign (${_selected.length})'),
        ),
      ],
    );
  }
}

class _Section extends StatelessWidget {
  final String title;
  final List<Widget> children;

  const _Section({required this.title, required this.children});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title,
            style: const TextStyle(
                fontWeight: FontWeight.bold, fontSize: 16)),
        const SizedBox(height: 8),
        ...children,
      ],
    );
  }
}

class _Row extends StatelessWidget {
  final String label;
  final String value;

  const _Row({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 100,
            child: Text(
              label,
              style: TextStyle(color: Colors.grey[600], fontSize: 14),
            ),
          ),
          Expanded(
            child: Text(value.isEmpty ? '—' : value),
          ),
        ],
      ),
    );
  }
}
