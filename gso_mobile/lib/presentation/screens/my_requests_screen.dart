import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app.dart';
import '../../data/models/request.dart';

final _statusFilterProvider = StateProvider<String>((ref) => '');
final _searchQueryProvider = StateProvider<String>((ref) => '');

final myRequestsProvider = FutureProvider.family<List<GsoRequest>, void>((ref, _) async {
  final authRepo = ref.read(authRepositoryProvider);
  final isLoggedIn = await authRepo.isLoggedIn();
  if (!isLoggedIn) return [];
  final status = ref.watch(_statusFilterProvider);
  final search = ref.watch(_searchQueryProvider);
  final repo = ref.read(requestRepositoryProvider);
  return repo.getRequests(
    status: status.isEmpty ? null : status,
    search: search.isEmpty ? null : search,
  );
});

class MyRequestsScreen extends ConsumerWidget {
  const MyRequestsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final requestsAsync = ref.watch(myRequestsProvider(null));

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
                          ref.read(_searchQueryProvider.notifier).state = v,
                    ),
                  ),
                  const SizedBox(width: 8),
                  IconButton(
                    icon: const Icon(Icons.search),
                    onPressed: () => ref.invalidate(myRequestsProvider(null)),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                decoration: const InputDecoration(
                  labelText: 'Status',
                  border: OutlineInputBorder(),
                ),
                value: ref.watch(_statusFilterProvider),
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
                  ref.read(_statusFilterProvider.notifier).state = v ?? '';
                  ref.invalidate(myRequestsProvider(null));
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
                    onPressed: () => ref.invalidate(myRequestsProvider(null)),
                    child: const Text('Retry'),
                  ),
                ],
              ),
            ),
            data: (requests) {
              if (requests.isEmpty) {
                return const Center(
                  child: Text('No requests found.'),
                );
              }
              return RefreshIndicator(
                onRefresh: () async {
                  ref.invalidate(myRequestsProvider(null));
                },
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
                          '${r.displayId} | ${r.statusDisplay}',
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
