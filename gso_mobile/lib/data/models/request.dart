class GsoRequest {
  final int id;
  final String displayId;
  final String title;
  final String description;
  final int unit;
  final String? unitName;
  final String? requestorName;
  final String status;
  final String statusDisplay;
  final bool isEmergency;
  final bool labor;
  final bool materials;
  final bool others;
  final String? customFullName;
  final String? customEmail;
  final String? customContactNumber;
  final String? createdAt;
  final String? updatedAt;
  final List<RequestAssignment>? assignments;
  final String? attachment;

  GsoRequest({
    required this.id,
    required this.displayId,
    required this.title,
    this.description = '',
    required this.unit,
    this.unitName,
    this.requestorName,
    required this.status,
    required this.statusDisplay,
    this.isEmergency = false,
    this.labor = false,
    this.materials = false,
    this.others = false,
    this.customFullName,
    this.customEmail,
    this.customContactNumber,
    this.createdAt,
    this.updatedAt,
    this.assignments,
    this.attachment,
  });

  factory GsoRequest.fromJson(Map<String, dynamic> json) {
    List<RequestAssignment>? assignments;
    if (json['assignments'] != null) {
      assignments = (json['assignments'] as List)
          .map((a) => RequestAssignment.fromJson(a as Map<String, dynamic>))
          .toList();
    }
    return GsoRequest(
      id: json['id'] as int,
      displayId: json['display_id'] as String? ?? '—',
      title: json['title'] as String? ?? '',
      description: json['description'] as String? ?? '',
      unit: json['unit'] as int,
      unitName: json['unit_name'] as String?,
      requestorName: json['requestor_name'] as String?,
      status: json['status'] as String? ?? '',
      statusDisplay: json['status_display'] as String? ?? '',
      isEmergency: json['is_emergency'] as bool? ?? false,
      labor: json['labor'] as bool? ?? false,
      materials: json['materials'] as bool? ?? false,
      others: json['others'] as bool? ?? false,
      customFullName: json['custom_full_name'] as String?,
      customEmail: json['custom_email'] as String?,
      customContactNumber: json['custom_contact_number'] as String?,
      createdAt: json['created_at'] as String?,
      updatedAt: json['updated_at'] as String?,
      assignments: assignments,
      attachment: json['attachment'] as String?,
    );
  }
}

class RequestAssignment {
  final int personnelId;
  final String personnelName;

  RequestAssignment({
    required this.personnelId,
    required this.personnelName,
  });

  factory RequestAssignment.fromJson(Map<String, dynamic> json) {
    return RequestAssignment(
      personnelId: json['personnel_id'] as int,
      personnelName: json['personnel_name'] as String? ?? '',
    );
  }
}
