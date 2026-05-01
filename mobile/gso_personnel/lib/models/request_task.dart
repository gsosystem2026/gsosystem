/// One row from `RequestListSerializer` / `RequestDetailSerializer`.
class RequestTask {
  const RequestTask({
    required this.id,
    required this.displayId,
    this.title,
    this.description,
    this.location,
    required this.status,
    required this.statusDisplay,
    this.isEmergency = false,
    this.requestorName,
    this.unitName,
    this.updatedAt,
  });

  final int id;
  final String displayId;
  final String? title;
  final String? description;
  final String? location;
  final String status;
  final String statusDisplay;
  final bool isEmergency;
  final String? requestorName;
  final String? unitName;
  final DateTime? updatedAt;

  factory RequestTask.fromJson(Map<String, dynamic> json) {
    DateTime? updated;
    final raw = json['updated_at'];
    if (raw is String) {
      updated = DateTime.tryParse(raw);
    }
    return RequestTask(
      id: json['id'] as int,
      displayId: (json['display_id'] ?? '').toString(),
      title: json['title'] as String?,
      description: json['description'] as String?,
      location: json['location'] as String?,
      status: (json['status'] ?? '').toString(),
      statusDisplay: (json['status_display'] ?? json['status'] ?? '').toString(),
      isEmergency: json['is_emergency'] == true,
      requestorName: json['requestor_name'] as String?,
      unitName: json['unit_name'] as String?,
      updatedAt: updated,
    );
  }

  String get purposePreview {
    final d = description?.trim();
    if (d == null || d.isEmpty) return '—';
    return d.length > 90 ? '${d.substring(0, 90)}…' : d;
  }

  /// Mirrors Django-ish labels for optimistic offline UI after a status tap.
  static String labelForStatusCode(String code) {
    switch (code) {
      case 'SUBMITTED':
        return 'Submitted';
      case 'ASSIGNED':
        return 'Assigned';
      case 'DIRECTOR_APPROVED':
        return 'Approved';
      case 'INSPECTION':
        return 'Inspection';
      case 'IN_PROGRESS':
        return 'In progress';
      case 'ON_HOLD':
        return 'On hold';
      case 'DONE_WORKING':
        return 'Done working';
      case 'COMPLETED':
        return 'Completed';
      case 'CANCELLED':
        return 'Cancelled';
      default:
        return code.replaceAll('_', ' ');
    }
  }

  RequestTask copyWith({
    int? id,
    String? displayId,
    String? title,
    String? description,
    String? location,
    String? status,
    String? statusDisplay,
    bool? isEmergency,
    String? requestorName,
    String? unitName,
    DateTime? updatedAt,
  }) {
    return RequestTask(
      id: id ?? this.id,
      displayId: displayId ?? this.displayId,
      title: title ?? this.title,
      description: description ?? this.description,
      location: location ?? this.location,
      status: status ?? this.status,
      statusDisplay: statusDisplay ?? this.statusDisplay,
      isEmergency: isEmergency ?? this.isEmergency,
      requestorName: requestorName ?? this.requestorName,
      unitName: unitName ?? this.unitName,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }
}
