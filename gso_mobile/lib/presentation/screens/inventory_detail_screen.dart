import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app.dart';
import '../../data/models/inventory_item.dart';

final inventoryDetailProvider =
    FutureProvider.family<InventoryItem?, int>((ref, id) async {
  try {
    final repo = ref.read(inventoryRepositoryProvider);
    return await repo.getInventoryItem(id);
  } catch (_) {
    return null;
  }
});

class InventoryDetailScreen extends ConsumerWidget {
  final int itemId;

  const InventoryDetailScreen({super.key, required this.itemId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final itemAsync = ref.watch(inventoryDetailProvider(itemId));

    return Scaffold(
      appBar: AppBar(
        title: const Text('Inventory Detail'),
      ),
      body: itemAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('Error: $e'),
              const SizedBox(height: 16),
              TextButton(
                onPressed: () =>
                    ref.invalidate(inventoryDetailProvider(itemId)),
                child: const Text('Retry'),
              ),
            ],
          ),
        ),
        data: (item) {
          if (item == null) {
            return const Center(child: Text('Item not found.'));
          }
          return SingleChildScrollView(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (item.isLowStock)
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(12),
                    margin: const EdgeInsets.only(bottom: 16),
                    decoration: BoxDecoration(
                      color: Colors.orange.shade100,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Row(
                      children: [
                        Icon(Icons.warning_amber, color: Colors.orange.shade800),
                        const SizedBox(width: 8),
                        Text(
                          'Low stock',
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            color: Colors.orange.shade900,
                          ),
                        ),
                      ],
                    ),
                  ),
                _Section(
                  title: 'Item',
                  children: [
                    _Row(label: 'Name', value: item.name),
                    _Row(label: 'Unit', value: item.unitName ?? '—'),
                    if (item.description.isNotEmpty)
                      _Row(label: 'Description', value: item.description),
                    if (item.category.isNotEmpty)
                      _Row(label: 'Category', value: item.category),
                  ],
                ),
                const SizedBox(height: 16),
                _Section(
                  title: 'Stock',
                  children: [
                    _Row(
                        label: 'Quantity',
                        value: '${item.quantity} ${item.unitOfMeasure}'),
                    _Row(label: 'Reorder level', value: '${item.reorderLevel}'),
                  ],
                ),
                if (item.location.isNotEmpty ||
                    (item.serialOrAssetNumber != null &&
                        item.serialOrAssetNumber!.isNotEmpty)) ...[
                  const SizedBox(height: 16),
                  _Section(
                    title: 'Details',
                    children: [
                      if (item.location.isNotEmpty)
                        _Row(label: 'Location', value: item.location),
                      if (item.serialOrAssetNumber != null &&
                          item.serialOrAssetNumber!.isNotEmpty)
                        _Row(
                            label: 'Serial/Asset',
                            value: item.serialOrAssetNumber!),
                    ],
                  ),
                ],
                if (item.createdAt != null) ...[
                  const SizedBox(height: 16),
                  _Section(
                    title: 'Dates',
                    children: [
                      _Row(label: 'Created', value: item.createdAt!),
                      if (item.updatedAt != null)
                        _Row(label: 'Updated', value: item.updatedAt!),
                    ],
                  ),
                ],
              ],
            ),
          );
        },
      ),
    );
  }
}

class _Section extends StatelessWidget {
  final String title;
  final List<Widget> children;

  const _Section({required this.title, required this.children});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title,
            style: const TextStyle(
                fontWeight: FontWeight.bold, fontSize: 16)),
        const SizedBox(height: 8),
        ...children,
      ],
    );
  }
}

class _Row extends StatelessWidget {
  final String label;
  final String value;

  const _Row({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 120,
            child: Text(
              label,
              style: TextStyle(color: Colors.grey[600], fontSize: 14),
            ),
          ),
          Expanded(child: Text(value)),
        ],
      ),
    );
  }
}
