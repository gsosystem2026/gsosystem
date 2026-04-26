import 'api_client.dart';
import 'auth_repository.dart';
import 'models/user.dart';

class UserRepository {
  final ApiClient _apiClient;
  final AuthRepository _authRepository;

  UserRepository({
    required ApiClient apiClient,
    required AuthRepository authRepository,
  })  : _apiClient = apiClient,
        _authRepository = authRepository;

  Future<GsoUser> getMe() async {
    final response = await _apiClient.dio.get('users/me/');
    return GsoUser.fromJson(response.data as Map<String, dynamic>);
  }

  /// List personnel for a unit (for assign form). Unit Head, GSO, Director only.
  Future<List<PersonnelItem>> getPersonnel(int unitId) async {
    final response = await _apiClient.dio.get(
      'users/',
      queryParameters: {'role': 'personnel', 'unit': unitId},
    );
    final list = response.data as List;
    return list
        .map((e) => PersonnelItem.fromJson(e as Map<String, dynamic>))
        .toList();
  }
}

class PersonnelItem {
  final int id;
  final String username;
  final String? firstName;
  final String? lastName;

  PersonnelItem({
    required this.id,
    required this.username,
    this.firstName,
    this.lastName,
  });

  factory PersonnelItem.fromJson(Map<String, dynamic> json) {
    return PersonnelItem(
      id: json['id'] as int,
      username: json['username'] as String? ?? '',
      firstName: json['first_name'] as String?,
      lastName: json['last_name'] as String?,
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
}
