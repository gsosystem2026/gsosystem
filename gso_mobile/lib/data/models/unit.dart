class Unit {
  final int id;
  final String name;
  final String code;
  final bool isActive;

  Unit({
    required this.id,
    required this.name,
    required this.code,
    required this.isActive,
  });

  factory Unit.fromJson(Map<String, dynamic> json) {
    return Unit(
      id: json['id'] as int,
      name: json['name'] as String,
      code: json['code'] as String,
      isActive: json['is_active'] as bool? ?? true,
    );
  }
}
