import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app.dart';
import '../../data/models/request.dart';
import '../../data/models/user.dart';

final _taskHistorySearchProvider = StateProvider<String>((ref) => '');

/// Personnel's completed/cancelled assigned tasks.
final taskHistoryProvider =
    FutureProvider.family<List<GsoRequest>, GsoUser>((ref, user) async {
  if (!user.isPersonnel) return [];
  final search = ref.watch(_taskHistorySearchProvider);
  final repo = ref.read(requestRepositoryProvider);
  final all = await repo.getRequests(search: search.isEmpty ? null : search);
  const historyStatuses = ['COMPLETED', 'CANCELLED'];
  return all.where((r) => historyStatuses.contains(r.status)).toList();
});

class TaskHistoryScreen extends ConsumerWidget {
  final GsoUser user;

  const TaskHistoryScreen({super.key, required this.user});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final tasksAsync = ref.watch(taskHistoryProvider(user));

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
                      ref.read(_taskHistorySearchProvider.notifier).state = v,
                ),
              ),
              const SizedBox(width: 8),
              IconButton(
                icon: const Icon(Icons.search),
                onPressed: () =>
                    ref.invalidate(taskHistoryProvider(user)),
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
                        ref.invalidate(taskHistoryProvider(user)),
                    child: const Text('Retry'),
                  ),
                ],
              ),
            ),
            data: (tasks) {
              if (tasks.isEmpty) {
                return const Center(
                  child: Text('No completed tasks.'),
                );
              }
              return RefreshIndicator(
                onRefresh: () async =>
                    ref.invalidate(taskHistoryProvider(user)),
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
