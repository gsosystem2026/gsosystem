class GsoNotification {
  final int id;
  final String title;
  final String message;
  final String? link;
  final bool read;
  final String? createdAt;

  GsoNotification({
    required this.id,
    required this.title,
    this.message = '',
    this.link,
    required this.read,
    this.createdAt,
  });

  factory GsoNotification.fromJson(Map<String, dynamic> json) {
    return GsoNotification(
      id: json['id'] as int,
      title: json['title'] as String? ?? '',
      message: json['message'] as String? ?? '',
      link: json['link'] as String?,
      read: json['read'] as bool? ?? false,
      createdAt: json['created_at'] as String?,
    );
  }

  /// Extract request id from link (e.g. /request/123, /requests/123/, /.../request-management/123/).
  int? get requestIdFromLink {
    if (link == null || link!.isEmpty) return null;
    // Match request-management/123 or /request(s)/123
    var match = RegExp(r'request-management/(\d+)').firstMatch(link!);
    match ??= RegExp(r'/request[s]?/(\d+)').firstMatch(link!);
    return match != null ? int.tryParse(match.group(1)!) : null;
  }
}
