class AppNotification {
  const AppNotification({
    required this.id,
    required this.title,
    required this.message,
    this.link,
    required this.read,
    this.createdAt,
  });

  final int id;
  final String title;
  final String message;
  final String? link;
  final bool read;
  final DateTime? createdAt;

  factory AppNotification.fromJson(Map<String, dynamic> json) {
    DateTime? created;
    final raw = json['created_at'];
    if (raw is String) created = DateTime.tryParse(raw);
    return AppNotification(
      id: json['id'] as int,
      title: (json['title'] ?? '').toString(),
      message: (json['message'] ?? '').toString(),
      link: json['link']?.toString(),
      read: json['read'] == true,
      createdAt: created,
    );
  }
}

