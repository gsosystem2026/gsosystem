class MaterialRequestItem {
  const MaterialRequestItem({
    required this.id,
    required this.requestId,
    required this.itemId,
    required this.itemName,
    required this.unitOfMeasure,
    required this.quantity,
    required this.status,
    required this.statusDisplay,
    this.notes,
    this.requestedByName,
    this.approvedByName,
    this.createdAt,
  });

  final int id;
  final int requestId;
  final int itemId;
  final String itemName;
  final String unitOfMeasure;
  final int quantity;
  final String status;
  final String statusDisplay;
  final String? notes;
  final String? requestedByName;
  final String? approvedByName;
  final DateTime? createdAt;

  factory MaterialRequestItem.fromJson(Map<String, dynamic> json) {
    DateTime? created;
    final raw = json['created_at'];
    if (raw is String) created = DateTime.tryParse(raw);
    return MaterialRequestItem(
      id: (json['id'] as num).toInt(),
      requestId: (json['request'] as num).toInt(),
      itemId: (json['item'] as num).toInt(),
      itemName: (json['item_name'] ?? '').toString(),
      unitOfMeasure: (json['unit_of_measure'] ?? '').toString(),
      quantity: (json['quantity'] as num).toInt(),
      status: (json['status'] ?? '').toString(),
      statusDisplay: (json['status_display'] ?? '').toString(),
      notes: json['notes']?.toString(),
      requestedByName: json['requested_by_name']?.toString(),
      approvedByName: json['approved_by_name']?.toString(),
      createdAt: created,
    );
  }
}

