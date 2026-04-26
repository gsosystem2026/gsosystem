class GsoUser {
  final int id;
  final String username;
  final String? firstName;
  final String? lastName;
  final String role;
  final int? unitId;
  final String? unitName;
  final bool canApprove;

  GsoUser({
    required this.id,
    required this.username,
    this.firstName,
    this.lastName,
    required this.role,
    this.unitId,
    this.unitName,
    this.canApprove = false,
  });

  factory GsoUser.fromJson(Map<String, dynamic> json) {
    return GsoUser(
      id: json['id'] as int,
      username: json['username'] as String,
      firstName: json['first_name'] as String?,
      lastName: json['last_name'] as String?,
      role: json['role'] as String,
      unitId: json['unit_id'] as int?,
      unitName: json['unit_name'] as String?,
      canApprove: json['can_approve'] as bool? ?? false,
    );
  }

  String get displayName {
    if (firstName != null && lastName != null) {
      return '$firstName $lastName'.trim();
    }
    if (firstName != null) return firstName!;
    if (lastName != null) return lastName!;
    return username;
  }

  bool get isRequestor => role == 'REQUESTOR';
  bool get isUnitHead => role == 'UNIT_HEAD';
  bool get isPersonnel => role == 'PERSONNEL';
  bool get isGsoOffice => role == 'GSO_OFFICE';
  bool get isDirector => role == 'DIRECTOR';
}
