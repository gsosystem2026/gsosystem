import 'api_client.dart';
import 'models/inventory_item.dart';

class InventoryRepository {
  final ApiClient _apiClient;

  InventoryRepository({required ApiClient apiClient}) : _apiClient = apiClient;

  /// List inventory. Role-filtered by backend. GSO/Director can pass unitId.
  Future<List<InventoryItem>> getInventory({int? unitId}) async {
    final queryParams = <String, dynamic>{};
    if (unitId != null) queryParams['unit'] = unitId;

    final response = await _apiClient.dio.get(
      'inventory/',
      queryParameters: queryParams.isNotEmpty ? queryParams : null,
    );
    final data = response.data;
    final list = data is Map && data.containsKey('results')
        ? data['results']
        : (data is List ? data : <dynamic>[]);
    final items = list is List ? list : <dynamic>[];
    return items
        .map((e) => InventoryItem.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// Get single inventory item.
  Future<InventoryItem> getInventoryItem(int id) async {
    final response = await _apiClient.dio.get('inventory/$id/');
    return InventoryItem.fromJson(response.data as Map<String, dynamic>);
  }
}
