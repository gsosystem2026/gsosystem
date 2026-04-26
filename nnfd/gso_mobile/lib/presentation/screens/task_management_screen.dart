import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app.dart';
import '../../data/models/request.dart';
import '../../data/models/user.dart';

final _taskSearchProvider = StateProvider<String>((ref) => '');

/// Personnel's active tasks (assigned, not yet completed/cancelled).
final taskManagementProvider =
    FutureProvider.family<List<GsoRequest>, GsoUser>((ref, user) async {
  if (!user.isPersonnel) return [];
  final search = ref.watch(_taskSearchProvider);
  final repo = ref.read(requestRepositoryProvider);
  final all = await repo.getRequests(search: search.isEmpty ? null : search);
  const activeStatuses = [
    'DIRECTOR_APPROVED',
    'IN_PROGRESS',
    'ON_HOLD',
    'DONE_WORKING',
  ];
  return all.where((r) => activeStatuses.contains(r.status)).toList();
});

class TaskManagementScreen extends ConsumerWidget {
  final GsoUser user;

  const TaskManagementScreen({super.key, required this.user});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final tasksAsync = ref.watch(taskManagementProvider(user));

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
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
                      ref.read(_taskSearchProvider.notifier).state = v,
                ),
              ),
              const SizedBox(width: 8),
              IconButton(
                icon: const Icon(Icons.search),
                onPressed: () =>
                    ref.invalidate(taskManagementProvider(user)),
              ),
            ],
          ),
        ),
        Expanded(
          child: tasksAsync.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (e, _) => Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text('Error: $e', textAlign: TextAlign.center),
                  const SizedBox(height: 16),
                  TextButton(
                    onPressed: () =>
                        ref.invalidate(taskManagementProvider(user)),
                    child: const Text('Retry'),
                  ),
                ],
              ),
            ),
            data: (tasks) {
              if (tasks.isEmpty) {
                return const Center(
                  child: Text('No assigned tasks.'),
                );
              }
              return RefreshIndicator(
                onRefresh: () async =>
                    ref.invalidate(taskManagementProvider(user)),
                child: ListView.builder(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  itemCount: tasks.length,
                  itemBuilder: (context, i) {
                    final r = tasks[i];
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
