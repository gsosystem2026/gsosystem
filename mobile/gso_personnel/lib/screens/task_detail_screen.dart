import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:uuid/uuid.dart';

import '../data/outbox_database.dart';
import '../models/material_request_item.dart';
import '../models/motorpool_trip.dart';
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
  static final _motorpoolUnitNameRe = RegExp(
    r'(?<![\w-])motorpool(?![\w-])',
    caseSensitive: false,
  );
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
  MotorpoolEnvelope? _motorpool;
  bool _loadingMotorpool = false;
  bool _savingMotorpool = false;
  /// Set when GET /requests/:id/ fails (network/auth); avoids a blank screen with no trip card.
  String? _motorpoolDetailError;
  final _driverCtrl = TextEditingController();
  final _plateCtrl = TextEditingController();
  final _stampCtrl = TextEditingController();
  final _transCtrl = TextEditingController();
  final _fuelBeginningCtrl = TextEditingController();
  final _fuelReceivedCtrl = TextEditingController();
  final _fuelAddedCtrl = TextEditingController();
  final _fuelTotalCtrl = TextEditingController();
  final _fuelUsedCtrl = TextEditingController();
  final _fuelEndingCtrl = TextEditingController();
  final _consumablesNotesCtrl = TextEditingController();

  bool get _isMotorpoolUnit {
    var code = (_task.unitCode ?? '').trim().toLowerCase();
    code = code.replaceAll('_', '-');
    if (code.startsWith('motorpool')) return true;
    final name = _task.unitName ?? '';
    final n = name.trim().toLowerCase();
    if (n == 'motorpool') return true;
    return _motorpoolUnitNameRe.hasMatch(n);
  }

  bool get _requiresInspectionFirst {
    final unit = (_task.unitName ?? '').toLowerCase();
    return unit.contains('repair') || unit.contains('electrical');
  }

  /// Same as web `can_request_materials` (`gso_requests/views.py`).
  bool get _canRequestMaterials {
    const allowed = {
      'DIRECTOR_APPROVED',
      'INSPECTION',
      'IN_PROGRESS',
      'ON_HOLD',
    };
    return allowed.contains(_task.status);
  }

  bool get _showMaterialsCard =>
      !_isMotorpoolUnit &&
      (_canRequestMaterials || _materialRequests.isNotEmpty);

  bool get _showMotorpoolCard =>
      _loadingMotorpool || _motorpool != null || _isMotorpoolUnit;

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
    if (_canRequestMaterials && !_isMotorpoolUnit) {
      _loadingMaterials = true;
    }
    _loadFullRequestDetail();
    _loadMaterialSection();
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
    _driverCtrl.dispose();
    _plateCtrl.dispose();
    _stampCtrl.dispose();
    _transCtrl.dispose();
    _fuelBeginningCtrl.dispose();
    _fuelReceivedCtrl.dispose();
    _fuelAddedCtrl.dispose();
    _fuelTotalCtrl.dispose();
    _fuelUsedCtrl.dispose();
    _fuelEndingCtrl.dispose();
    _consumablesNotesCtrl.dispose();
    super.dispose();
  }

  /// Offline / transport failures (not validation or 4xx from server).
  bool _isConnectivityStyleMessage(String? msg) {
    if (msg == null || msg.trim().isEmpty) return false;
    final m = msg.toLowerCase();
    return m.contains('no internet') ||
        m.contains('connection') ||
        m.contains('timed out') ||
        m.contains('timeout') ||
        m.contains('network') ||
        m.contains('offline') ||
        m.contains('socket') ||
        m.contains('failed host lookup');
  }

  Future<void> _loadFullRequestDetail() async {
    if (_isMotorpoolUnit || _motorpool != null) {
      setState(() => _loadingMotorpool = true);
    }
    try {
      final payload = await _api.fetchRequestDetailPayload(_task.id);
      if (!mounted) return;
      setState(() {
        _task = payload.task;
        _motorpool = payload.motorpool;
        _loadingMotorpool = false;
        _motorpoolDetailError = null;
        _syncMotorpoolControllersFromTrip();
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loadingMotorpool = false;
        _motorpoolDetailError = _api.messageFromError(e);
      });
    }
  }

  void _syncMotorpoolControllersFromTrip() {
    final trip = _motorpool?.trip;
    if (trip == null) {
      _driverCtrl.clear();
      _plateCtrl.clear();
      _stampCtrl.clear();
      _transCtrl.clear();
      _fuelBeginningCtrl.clear();
      _fuelReceivedCtrl.clear();
      _fuelAddedCtrl.clear();
      _fuelTotalCtrl.clear();
      _fuelUsedCtrl.clear();
      _fuelEndingCtrl.clear();
      _consumablesNotesCtrl.clear();
      return;
    }
    _driverCtrl.text = trip.driverName ?? '';
    _plateCtrl.text = trip.vehiclePlate ?? '';
    _stampCtrl.text = trip.vehicleStampOrContractNo ?? '';
    _transCtrl.text = trip.vehicleTrans ?? '';
    _fuelBeginningCtrl.text = trip.fuelBeginningLiters ?? '';
    _fuelReceivedCtrl.text = trip.fuelReceivedIssuedLiters ?? '';
    _fuelAddedCtrl.text = trip.fuelAddedPurchasedLiters ?? '';
    _fuelTotalCtrl.text = trip.fuelTotalAvailableLiters ?? '';
    _fuelUsedCtrl.text = trip.fuelUsedLiters ?? '';
    _fuelEndingCtrl.text = trip.fuelEndingLiters ?? '';
    _consumablesNotesCtrl.text = trip.otherConsumablesNotes ?? '';
  }

  Future<void> _saveMotorpoolEdits() async {
    if (_motorpool == null || _savingMotorpool) return;
    final canV = _motorpool!.canEditVehicle;
    final canA = _motorpool!.canEditActuals;
    if (!canV && !canA) return;
    final body = <String, dynamic>{};
    if (canV) {
      body['driver_name'] = _driverCtrl.text.trim();
      body['vehicle_plate'] = _plateCtrl.text.trim();
      body['vehicle_stamp_or_contract_no'] = _stampCtrl.text.trim();
      body['vehicle_trans'] = _transCtrl.text.trim();
    }
    if (canA) {
      body['fuel_beginning_liters'] = _fuelBeginningCtrl.text.trim();
      body['fuel_received_issued_liters'] = _fuelReceivedCtrl.text.trim();
      body['fuel_added_purchased_liters'] = _fuelAddedCtrl.text.trim();
      body['fuel_total_available_liters'] = _fuelTotalCtrl.text.trim();
      body['fuel_used_liters'] = _fuelUsedCtrl.text.trim();
      body['fuel_ending_liters'] = _fuelEndingCtrl.text.trim();
      body['other_consumables_notes'] = _consumablesNotesCtrl.text.trim();
    }
    setState(() => _savingMotorpool = true);
    try {
      final env = await _api.patchMotorpoolTrip(_task.id, body);
      if (!mounted) return;
      setState(() {
        _motorpool = env;
        _savingMotorpool = false;
        _syncMotorpoolControllersFromTrip();
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Trip ticket saved.')),
      );
    } catch (e) {
      if (!mounted) return;
      setState(() => _savingMotorpool = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(_api.messageFromError(e))),
      );
    }
  }

  Future<void> _loadMaterialSection() async {
    if (_isMotorpoolUnit) {
      if (mounted) {
        setState(() {
          _loadingMaterials = false;
          _materialRequests = [];
          _inventoryItems = [];
          _selectedItemId = null;
        });
      }
      return;
    }
    if (_canRequestMaterials && mounted) {
      setState(() => _loadingMaterials = true);
    }
    try {
      final requests = await _api.fetchRequestMaterialRequests(_task.id);
      List<Map<String, dynamic>> available = [];
      if (_canRequestMaterials) {
        final inventory = await _api.fetchInventoryItems();
        available = inventory
            .where((e) => ((e['quantity'] as num?)?.toInt() ?? 0) > 0)
            .toList();
      }
      if (!mounted) return;
      setState(() {
        _materialRequests = requests;
        if (_canRequestMaterials) {
          _inventoryItems = available;
          final hasSelected = available.any(
            (it) => (it['id'] as num?)?.toInt() == _selectedItemId,
          );
          if (!hasSelected) {
            _selectedItemId =
                available.isEmpty ? null : (available.first['id'] as num?)?.toInt();
          }
        } else {
          _inventoryItems = [];
          _selectedItemId = null;
        }
        _loadingMaterials = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _loadingMaterials = false);
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
      final mp = MotorpoolEnvelope.tryParse(Map<String, dynamic>.from(data));
      if (!mounted) return;
      setState(() {
        _task = updated;
        _motorpool = mp;
        _syncMotorpoolControllersFromTrip();
      });
      await _loadMaterialSection();
      if (!mounted) return;
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
        await _loadMaterialSection();
        if (!mounted) return;
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

  Widget _motorpoolFuelField(TextEditingController c, String label) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: TextField(
        controller: c,
        keyboardType: const TextInputType.numberWithOptions(decimal: true),
        decoration: InputDecoration(
          labelText: label,
          border: const OutlineInputBorder(),
        ),
      ),
    );
  }

  Widget _buildMotorpoolCard(BuildContext context) {
    final t = Theme.of(context).textTheme;
    final mp = _motorpool;
    return Container(
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
                  'Trip ticket',
                  style: t.titleSmall?.copyWith(fontWeight: FontWeight.w700),
                ),
              ),
              IconButton(
                tooltip: 'Refresh',
                onPressed: _loadingMotorpool ? null : _loadFullRequestDetail,
                icon: const Icon(Icons.refresh_rounded, size: 20),
              ),
            ],
          ),
          if (_loadingMotorpool && mp == null)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 16),
              child: Center(child: CircularProgressIndicator()),
            ),
          if (!_loadingMotorpool && mp == null && _isMotorpoolUnit) ...[
            const SizedBox(height: 8),
            Text(
              _motorpoolDetailError ??
                  'Trip ticket data was not returned. Try refresh, or ensure this request is on the Motorpool unit.',
              style: t.bodySmall?.copyWith(
                color: _motorpoolDetailError != null && !_isConnectivityStyleMessage(_motorpoolDetailError)
                    ? Colors.red.shade800
                    : AppColors.slate600,
                height: 1.35,
              ),
            ),
            const SizedBox(height: 8),
            TextButton.icon(
              onPressed: _loadingMotorpool ? null : _loadFullRequestDetail,
              icon: const Icon(Icons.refresh_rounded, size: 18),
              label: const Text('Try again'),
            ),
          ],
          if (mp != null) ...[
            if (_loadingMotorpool) ...[
              const SizedBox(height: 8),
              const Center(
                child: SizedBox(
                  width: 22,
                  height: 22,
                  child: CircularProgressIndicator(strokeWidth: 2),
                ),
              ),
              const SizedBox(height: 8),
            ],
            Text(
              'Planned trip',
              style: t.labelLarge?.copyWith(
                color: AppColors.slate600,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 10),
            _infoTile(context, 'Office / requesting party', mp.trip.requestingOffice),
            const SizedBox(height: 12),
            _infoTile(context, 'Places to visit', mp.trip.placesToBeVisited),
            const SizedBox(height: 12),
            _infoTile(context, 'Itinerary', mp.trip.itineraryOfTravel),
            const SizedBox(height: 12),
            _infoTile(context, 'Trip date / time', mp.trip.tripDatetime),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: _infoTile(
                    context,
                    'Days',
                    mp.trip.numberOfDays != null ? '${mp.trip.numberOfDays}' : null,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _infoTile(
                    context,
                    'Passengers',
                    mp.trip.numberOfPassengers != null ? '${mp.trip.numberOfPassengers}' : null,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            _infoTile(context, 'Contact person', mp.trip.contactPerson),
            const SizedBox(height: 12),
            _infoTile(context, 'Contact number', mp.trip.contactNumber),
            const SizedBox(height: 16),
            Text(
              'Vehicle',
              style: t.labelLarge?.copyWith(
                color: AppColors.slate600,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 10),
            if (mp.canEditVehicle) ...[
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: TextField(
                  controller: _driverCtrl,
                  decoration: const InputDecoration(
                    labelText: 'Driver',
                    border: OutlineInputBorder(),
                  ),
                ),
              ),
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: TextField(
                  controller: _plateCtrl,
                  decoration: const InputDecoration(
                    labelText: 'Plate no.',
                    border: OutlineInputBorder(),
                  ),
                ),
              ),
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: TextField(
                  controller: _stampCtrl,
                  decoration: const InputDecoration(
                    labelText: 'Sticker / stamp / contract',
                    border: OutlineInputBorder(),
                  ),
                ),
              ),
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: TextField(
                  controller: _transCtrl,
                  decoration: const InputDecoration(
                    labelText: 'AC / Transmission',
                    border: OutlineInputBorder(),
                  ),
                ),
              ),
            ] else ...[
              _infoTile(context, 'Driver', mp.trip.driverName),
              const SizedBox(height: 12),
              _infoTile(context, 'Plate no.', mp.trip.vehiclePlate),
              const SizedBox(height: 12),
              _infoTile(context, 'Sticker / stamp / contract', mp.trip.vehicleStampOrContractNo),
              const SizedBox(height: 12),
              _infoTile(context, 'AC / Transmission', mp.trip.vehicleTrans),
            ],
            const SizedBox(height: 16),
            Text(
              'Fuel (liters) & consumables',
              style: t.labelLarge?.copyWith(
                color: AppColors.slate600,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              'Printing the official trip ticket is available to Unit Heads on the web.',
              style: t.bodySmall?.copyWith(color: AppColors.slate500),
            ),
            const SizedBox(height: 10),
            if (mp.canEditActuals) ...[
              _motorpoolFuelField(_fuelBeginningCtrl, 'Beginning balance'),
              _motorpoolFuelField(_fuelReceivedCtrl, 'Fuel received'),
              _motorpoolFuelField(_fuelAddedCtrl, 'Added / purchased'),
              _motorpoolFuelField(_fuelTotalCtrl, 'Total available'),
              _motorpoolFuelField(_fuelUsedCtrl, 'Fuel used'),
              _motorpoolFuelField(_fuelEndingCtrl, 'Ending balance'),
              TextField(
                controller: _consumablesNotesCtrl,
                minLines: 2,
                maxLines: 4,
                decoration: const InputDecoration(
                  labelText: 'Oil, tolls & other notes',
                  alignLabelWithHint: true,
                  border: OutlineInputBorder(),
                ),
              ),
            ] else ...[
              _infoTile(context, 'Beginning balance', mp.trip.fuelBeginningLiters),
              const SizedBox(height: 12),
              _infoTile(context, 'Fuel received', mp.trip.fuelReceivedIssuedLiters),
              const SizedBox(height: 12),
              _infoTile(context, 'Added / purchased', mp.trip.fuelAddedPurchasedLiters),
              const SizedBox(height: 12),
              _infoTile(context, 'Total available', mp.trip.fuelTotalAvailableLiters),
              const SizedBox(height: 12),
              _infoTile(context, 'Fuel used', mp.trip.fuelUsedLiters),
              const SizedBox(height: 12),
              _infoTile(context, 'Ending balance', mp.trip.fuelEndingLiters),
              const SizedBox(height: 12),
              _infoTile(context, 'Oil, tolls & other notes', mp.trip.otherConsumablesNotes),
            ],
            if (mp.canEditVehicle || mp.canEditActuals) ...[
              const SizedBox(height: 12),
              Align(
                alignment: Alignment.centerLeft,
                child: FilledButton.icon(
                  onPressed:
                      (_savingMotorpool || _loadingMotorpool) ? null : _saveMotorpoolEdits,
                  icon: _savingMotorpool
                      ? const SizedBox(
                          width: 14,
                          height: 14,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.save_rounded),
                  label: const Text('Save trip ticket'),
                ),
              ),
            ],
          ],
        ],
      ),
    );
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
              if (_showMotorpoolCard) ...[
                const SizedBox(height: 14),
                _buildMotorpoolCard(context),
              ],
              if (_showMaterialsCard) ...[
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
                          Expanded(
                            child: Text(
                              _canRequestMaterials
                                  ? 'Request materials'
                                  : 'Material requests',
                              style: t.titleSmall?.copyWith(fontWeight: FontWeight.w700),
                            ),
                          ),
                          IconButton(
                            tooltip: 'Refresh',
                            onPressed: _loadMaterialSection,
                            icon: const Icon(Icons.refresh_rounded, size: 20),
                          ),
                        ],
                      ),
                      if (_canRequestMaterials) ...[
                        const SizedBox(height: 4),
                        Text(
                          'Request items from unit inventory. Unit Head must approve before stock is deducted.',
                          style: t.bodySmall?.copyWith(color: AppColors.slate500),
                        ),
                      ],
                      if (_canRequestMaterials && _loadingMaterials)
                        const Padding(
                          padding: EdgeInsets.symmetric(vertical: 10),
                          child: Center(child: CircularProgressIndicator()),
                        )
                      else ...[
                        if (_canRequestMaterials) ...[
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
                          if (_materialRequests.isNotEmpty) const SizedBox(height: 12),
                        ],
                        if (_canRequestMaterials || _materialRequests.isNotEmpty) ...[
                          if (_canRequestMaterials) ...[
                            Text(
                              'Request history',
                              style: t.labelLarge?.copyWith(
                                color: AppColors.slate600,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            const SizedBox(height: 6),
                          ],
                          if (_materialRequests.isEmpty && _canRequestMaterials)
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
                    ],
                  ),
                ),
                const SizedBox(height: 14),
              ],
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
