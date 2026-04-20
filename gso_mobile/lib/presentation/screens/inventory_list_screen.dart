import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app.dart';
import '../../data/models/inventory_item.dart';
import '../../data/models/user.dart';
import 'new_request_screen.dart';

final _inventoryUnitFilterProvider = StateProvider<int?>((ref) => null);

final inventoryListProvider =
    FutureProvider.family<List<InventoryItem>, GsoUser>((ref, user) async {
  int? unitId;
  if (user.isUnitHead && user.unitId != null) {
    unitId = user.unitId;
  } else if (user.isGsoOffice || user.isDirector) {
    unitId = ref.watch(_inventoryUnitFilterProvider);
  }
  final repo = ref.read(inventoryRepositoryProvider);
  return repo.getInventory(unitId: unitId);
});

class InventoryListScreen extends ConsumerWidget {
  final GsoUser user;

  const InventoryListScreen({super.key, required this.user});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final inventoryAsync = ref.watch(inventoryListProvider(user));
    final unitsAsync = ref.watch(unitsProvider);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (user.isGsoOffice || user.isDirector)
          Padding(
            padding: const EdgeInsets.all(16),
            child: unitsAsync.when(
              data: (units) => DropdownButtonFormField<int?>(
                decoration: const InputDecoration(
                  labelText: 'Unit',
                  border: OutlineInputBorder(),
                ),
                value: ref.watch(_inventoryUnitFilterProvider),
                items: [
                  const DropdownMenuItem<int?>(
                    value: null,
                    child: Text('All units'),
                  ),
                  ...units.map(
                    (u) => DropdownMenuItem<int?>(
                      value: u.id,
                      child: Text(u.name),
                    ),
                  ),
                ],
                onChanged: (v) {
                  ref.read(_inventoryUnitFilterProvider.notifier).state = v;
                  ref.invalidate(inventoryListProvider(user));
                },
              ),
              loading: () => const SizedBox.shrink(),
              error: (_, __) => const SizedBox.shrink(),
            ),
          ),
        Expanded(
          child: inventoryAsync.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (e, _) => Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text('Error: $e', textAlign: TextAlign.center),
                  const SizedBox(height: 16),
                  TextButton(
                    onPressed: () =>
                        ref.invalidate(inventoryListProvider(user)),
                    child: const Text('Retry'),
                  ),
                ],
              ),
            ),
            data: (items) {
              if (items.isEmpty) {
                return const Center(child: Text('No inventory items.'));
              }
              return RefreshIndicator(
                onRefresh: () async =>
                    ref.invalidate(inventoryListProvider(user)),
                child: ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: items.length,
                  itemBuilder: (context, i) {
                    final item = items[i];
                    return Card(
                      margin: const EdgeInsets.only(bottom: 8),
                      child: ListTile(
                        title: Row(
                          children: [
                            Expanded(child: Text(item.name)),
                            if (item.isLowStock)
                              Container(
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 8, vertical: 2),
                                decoration: BoxDecoration(
                                  color: Colors.orange.shade100,
                                  borderRadius: BorderRadius.circular(4),
                                ),
                                child: Text(
                                  'Low stock',
                                  style: TextStyle(
                                    fontSize: 11,
                                    color: Colors.orange.shade900,
                                  ),
                                ),
                              ),
                          ],
                        ),
                        subtitle: Text(
                          '${item.quantity} ${item.unitOfMeasure}${item.unitName != null ? ' | ${item.unitName}' : ''}',
                          style: TextStyle(
                            color: Colors.grey[600],
                            fontSize: 12,
                          ),
                        ),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () => context.push('/inventory/${item.id}'),
                      ),
                    );
                  },
                ),
              );
            },
          ),
        ),
      ],
    );
  }
}
