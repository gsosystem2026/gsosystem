import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app.dart';
import '../../data/models/request.dart';
import '../../data/models/user.dart';
import 'new_request_screen.dart';

final _staffStatusFilterProvider = StateProvider<String>((ref) => '');
final _staffSearchProvider = StateProvider<String>((ref) => '');
final _staffUnitFilterProvider = StateProvider<int?>((ref) => null);

final staffRequestsProvider =
    FutureProvider.family<List<GsoRequest>, GsoUser>((ref, user) async {
  final status = ref.watch(_staffStatusFilterProvider);
  final search = ref.watch(_staffSearchProvider);
  final unitId = ref.watch(_staffUnitFilterProvider);
  final repo = ref.read(requestRepositoryProvider);

  int? effectiveUnitId;
  if (user.isUnitHead && user.unitId != null) {
    effectiveUnitId = user.unitId;
  } else if (user.isGsoOffice || user.isDirector) {
    effectiveUnitId = unitId;
  }

  return repo.getRequests(
    status: status.isEmpty ? null : status,
    unitId: effectiveUnitId,
    search: search.isEmpty ? null : search,
  );
});

class StaffRequestListScreen extends ConsumerWidget {
  final GsoUser user;

  const StaffRequestListScreen({super.key, required this.user});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final requestsAsync = ref.watch(staffRequestsProvider(user));
    final unitsAsync = ref.watch(unitsProvider);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      decoration: const InputDecoration(
                        labelText: 'Search',
                        hintText: 'Title or ID',
                        prefixIcon: Icon(Icons.search),
                        border: OutlineInputBorder(),
                      ),
                      onChanged: (v) =>
                          ref.read(_staffSearchProvider.notifier).state = v,
                    ),
                  ),
                  const SizedBox(width: 8),
                  IconButton(
                    icon: const Icon(Icons.search),
                    onPressed: () =>
                        ref.invalidate(staffRequestsProvider(user)),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              if (user.isGsoOffice || user.isDirector)
                unitsAsync.when(
                  data: (units) {
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: DropdownButtonFormField<int?>(
                        decoration: const InputDecoration(
                          labelText: 'Unit',
                          border: OutlineInputBorder(),
                        ),
                        value: ref.watch(_staffUnitFilterProvider),
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
                          ref.read(_staffUnitFilterProvider.notifier).state = v;
                          ref.invalidate(staffRequestsProvider(user));
                        },
                      ),
                    );
                  },
                  loading: () => const SizedBox.shrink(),
                  error: (_, __) => const SizedBox.shrink(),
                ),
              DropdownButtonFormField<String>(
                decoration: const InputDecoration(
                  labelText: 'Status',
                  border: OutlineInputBorder(),
                ),
                value: ref.watch(_staffStatusFilterProvider),
                items: const [
                  DropdownMenuItem(value: '', child: Text('All')),
                  DropdownMenuItem(value: 'SUBMITTED', child: Text('Submitted')),
                  DropdownMenuItem(value: 'ASSIGNED', child: Text('Assigned')),
                  DropdownMenuItem(value: 'DIRECTOR_APPROVED', child: Text('Approved')),
                  DropdownMenuItem(value: 'IN_PROGRESS', child: Text('In Progress')),
                  DropdownMenuItem(value: 'ON_HOLD', child: Text('On Hold')),
                  DropdownMenuItem(value: 'DONE_WORKING', child: Text('Done working')),
                  DropdownMenuItem(value: 'COMPLETED', child: Text('Completed')),
                  DropdownMenuItem(value: 'CANCELLED', child: Text('Cancelled')),
                ],
                onChanged: (v) {
                  ref.read(_staffStatusFilterProvider.notifier).state = v ?? '';
                  ref.invalidate(staffRequestsProvider(user));
                },
              ),
            ],
          ),
        ),
        Expanded(
          child: requestsAsync.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (e, _) => Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text('Error: $e', textAlign: TextAlign.center),
                  const SizedBox(height: 16),
                  TextButton(
                    onPressed: () =>
                        ref.invalidate(staffRequestsProvider(user)),
                    child: const Text('Retry'),
                  ),
                ],
              ),
            ),
            data: (requests) {
              if (requests.isEmpty) {
                return const Center(child: Text('No requests found.'));
              }
              return RefreshIndicator(
                onRefresh: () async =>
                    ref.invalidate(staffRequestsProvider(user)),
                child: ListView.builder(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  itemCount: requests.length,
                  itemBuilder: (context, i) {
                    final r = requests[i];
                    return Card(
                      margin: const EdgeInsets.only(bottom: 8),
                      child: ListTile(
                        title: Text(r.title),
                        subtitle: Text(
                          '${r.displayId} | ${r.statusDisplay}${r.unitName != null ? ' | ${r.unitName}' : ''}',
                          style: TextStyle(
                            color: Colors.grey[600],
                            fontSize: 12,
                          ),
                        ),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () => context.push('/request/${r.id}'),
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
