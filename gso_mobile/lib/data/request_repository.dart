import 'api_client.dart';
import 'models/request.dart';
import 'models/unit.dart';

class RequestRepository {
  final ApiClient _apiClient;

  RequestRepository({required ApiClient apiClient}) : _apiClient = apiClient;

  /// Units list (public, no auth).
  Future<List<Unit>> getUnits() async {
    final response = await _apiClient.dio.get('units/');
    final data = response.data;
    final list = data is Map && data.containsKey('results')
        ? data['results']
        : (data is List ? data : <dynamic>[]);
    final items = list is List ? list : <dynamic>[];
    return items.map((e) => Unit.fromJson(e as Map<String, dynamic>)).toList();
  }

  /// My requests (for requestor) or staff list. Filter by status, unit, search.
  Future<List<GsoRequest>> getRequests({
    String? status,
    int? unitId,
    String? search,
  }) async {
    final queryParams = <String, dynamic>{};
    if (status != null && status.isNotEmpty) queryParams['status'] = status;
    if (unitId != null) queryParams['unit'] = unitId;
    if (search != null && search.isNotEmpty) queryParams['q'] = search;

    final response = await _apiClient.dio.get(
      'requests/',
      queryParameters: queryParams.isNotEmpty ? queryParams : null,
    );
    final data = response.data;
    final list = data is Map && data.containsKey('results')
        ? data['results']
        : (data is List ? data : <dynamic>[]);
    final items = list is List ? list : <dynamic>[];
    return items.map((e) => GsoRequest.fromJson(e as Map<String, dynamic>)).toList();
  }

  /// Request detail by id.
  Future<GsoRequest> getRequest(int id) async {
    final response = await _apiClient.dio.get('requests/$id/');
    return GsoRequest.fromJson(response.data as Map<String, dynamic>);
  }

  /// Unit Head: assign personnel. personnelIds: list of user ids.
  Future<GsoRequest> assignPersonnel(int requestId, List<int> personnelIds) async {
    final response = await _apiClient.dio.post(
      'requests/$requestId/assign/',
      data: {'personnel_ids': personnelIds},
    );
    return GsoRequest.fromJson(response.data as Map<String, dynamic>);
  }

  /// Director/OIC: approve request.
  Future<GsoRequest> approveRequest(int requestId) async {
    final response = await _apiClient.dio.post('requests/$requestId/approve/');
    return GsoRequest.fromJson(response.data as Map<String, dynamic>);
  }

  /// Personnel: update work status (IN_PROGRESS, ON_HOLD, DONE_WORKING).
  Future<GsoRequest> updateWorkStatus(int requestId, String newStatus) async {
    final response = await _apiClient.dio.post(
      'requests/$requestId/status/',
      data: {'status': newStatus},
    );
    return GsoRequest.fromJson(response.data as Map<String, dynamic>);
  }

  /// Unit Head: mark request complete.
  Future<GsoRequest> completeRequest(int requestId) async {
    final response = await _apiClient.dio.post('requests/$requestId/complete/');
    return GsoRequest.fromJson(response.data as Map<String, dynamic>);
  }

  /// Unit Head: return for rework.
  Future<GsoRequest> returnForRework(int requestId) async {
    final response = await _apiClient.dio.post('requests/$requestId/return_rework/');
    return GsoRequest.fromJson(response.data as Map<String, dynamic>);
  }

  /// Create new request (creates as SUBMITTED).
  Future<GsoRequest> createRequest({
    required int unitId,
    required String title,
    String description = '',
    bool labor = false,
    bool materials = false,
    bool others = false,
    String? customFullName,
    String? customEmail,
    String? customContactNumber,
  }) async {
    final data = {
      'unit': unitId,
      'title': title,
      'description': description,
      'labor': labor,
      'materials': materials,
      'others': others,
      if (customFullName != null && customFullName.isNotEmpty) 'custom_full_name': customFullName,
      if (customEmail != null && customEmail.isNotEmpty) 'custom_email': customEmail,
      if (customContactNumber != null && customContactNumber.isNotEmpty)
        'custom_contact_number': customContactNumber,
    };
    final response = await _apiClient.dio.post('requests/', data: data);
    return GsoRequest.fromJson(response.data as Map<String, dynamic>);
  }
}
