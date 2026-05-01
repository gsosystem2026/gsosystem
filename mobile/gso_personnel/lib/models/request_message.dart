class RequestMessageItem {
  const RequestMessageItem({
    required this.id,
    required this.message,
    required this.userId,
    required this.userName,
    this.createdAt,
  });

  final int id;
  final String message;
  final int userId;
  final String userName;
  final DateTime? createdAt;

  factory RequestMessageItem.fromJson(Map<String, dynamic> json) {
    DateTime? created;
    final raw = json['created_at'];
    if (raw is String) created = DateTime.tryParse(raw);
    return RequestMessageItem(
      id: json['id'] as int,
      message: (json['message'] ?? '').toString(),
      userId: (json['user'] as num).toInt(),
      userName: (json['user_name'] ?? '').toString(),
      createdAt: created,
    );
  }
}

