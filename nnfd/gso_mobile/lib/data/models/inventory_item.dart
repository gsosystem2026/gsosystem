class InventoryItem {
  final int id;
  final int unit;
  final String? unitName;
  final String name;
  final String description;
  final String category;
  final int quantity;
  final String unitOfMeasure;
  final int reorderLevel;
  final bool isLowStock;
  final String location;
  final String? serialOrAssetNumber;
  final String? createdAt;
  final String? updatedAt;

  InventoryItem({
    required this.id,
    required this.unit,
    this.unitName,
    required this.name,
    this.description = '',
    this.category = '',
    this.quantity = 0,
    this.unitOfMeasure = 'pcs',
    this.reorderLevel = 0,
    this.isLowStock = false,
    this.location = '',
    this.serialOrAssetNumber,
    this.createdAt,
    this.updatedAt,
  });

  factory InventoryItem.fromJson(Map<String, dynamic> json) {
    return InventoryItem(
      id: json['id'] as int,
      unit: json['unit'] as int,
      unitName: json['unit_name'] as String?,
      name: json['name'] as String? ?? '',
      description: json['description'] as String? ?? '',
      category: json['category'] as String? ?? '',
      quantity: json['quantity'] as int? ?? 0,
      unitOfMeasure: json['unit_of_measure'] as String? ?? 'pcs',
      reorderLevel: json['reorder_level'] as int? ?? 0,
      isLowStock: json['is_low_stock'] as bool? ?? false,
      location: json['location'] as String? ?? '',
      serialOrAssetNumber: json['serial_or_asset_number'] as String?,
      createdAt: json['created_at'] as String?,
      updatedAt: json['updated_at'] as String?,
    );
  }
}
