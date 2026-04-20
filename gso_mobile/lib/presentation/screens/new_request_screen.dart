import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app.dart';
import '../../data/models/unit.dart';
import 'my_requests_screen.dart';

final unitsProvider = FutureProvider<List<Unit>>((ref) async {
  final repo = ref.read(requestRepositoryProvider);
  return repo.getUnits();
});

class NewRequestScreen extends ConsumerStatefulWidget {
  const NewRequestScreen({super.key});

  @override
  ConsumerState<NewRequestScreen> createState() => _NewRequestScreenState();
}

class _NewRequestScreenState extends ConsumerState<NewRequestScreen> {
  final _formKey = GlobalKey<FormState>();
  final _titleController = TextEditingController();
  final _descriptionController = TextEditingController();
  final _customNameController = TextEditingController();
  final _customEmailController = TextEditingController();
  final _customContactController = TextEditingController();

  int? _selectedUnitId;
  bool _labor = false;
  bool _materials = false;
  bool _others = false;
  bool _loading = false;
  String? _error;

  @override
  void dispose() {
    _titleController.dispose();
    _descriptionController.dispose();
    _customNameController.dispose();
    _customEmailController.dispose();
    _customContactController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    if (_selectedUnitId == null) {
      setState(() => _error = 'Please select a unit.');
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final repo = ref.read(requestRepositoryProvider);
      await repo.createRequest(
        unitId: _selectedUnitId!,
        title: _titleController.text.trim(),
        description: _descriptionController.text.trim(),
        labor: _labor,
        materials: _materials,
        others: _others,
        customFullName: _customNameController.text.trim().isEmpty
            ? null
            : _customNameController.text.trim(),
        customEmail: _customEmailController.text.trim().isEmpty
            ? null
            : _customEmailController.text.trim(),
        customContactNumber: _customContactController.text.trim().isEmpty
            ? null
            : _customContactController.text.trim(),
      );
      if (!mounted) return;
      _titleController.clear();
      _descriptionController.clear();
      _customNameController.clear();
      _customEmailController.clear();
      _customContactController.clear();
      setState(() {
        _selectedUnitId = null;
        _labor = false;
        _materials = false;
        _others = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Request submitted successfully.')),
      );
      ref.invalidate(myRequestsProvider(null));
    } catch (e) {
      setState(() => _error = 'Failed to submit: $e');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final unitsAsync = ref.watch(unitsProvider);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            unitsAsync.when(
              loading: () => const Center(
                child: Padding(
                  padding: EdgeInsets.all(24),
                  child: CircularProgressIndicator(),
                ),
              ),
              error: (e, _) => Text('Failed to load units: $e'),
              data: (units) {
                if (units.isEmpty) {
                  return const Text('No units available.');
                }
                return DropdownButtonFormField<int>(
                  decoration: const InputDecoration(
                    labelText: 'Unit *',
                    border: OutlineInputBorder(),
                  ),
                  value: _selectedUnitId,
                  items: units
                      .map((u) => DropdownMenuItem(
                            value: u.id,
                            child: Text(u.name),
                          ))
                      .toList(),
                  onChanged: (v) => setState(() => _selectedUnitId = v),
                  validator: (v) =>
                      v == null ? 'Please select a unit' : null,
                );
              },
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _titleController,
              decoration: const InputDecoration(
                labelText: 'Title *',
                border: OutlineInputBorder(),
              ),
              validator: (v) =>
                  (v == null || v.trim().isEmpty) ? 'Required' : null,
            ),
            const SizedBox(height: 16),
            TextFormField(
              controller: _descriptionController,
              decoration: const InputDecoration(
                labelText: 'Description',
                border: OutlineInputBorder(),
                alignLabelWithHint: true,
              ),
              maxLines: 3,
            ),
            const SizedBox(height: 16),
            const Text('Request type:', style: TextStyle(fontWeight: FontWeight.w500)),
            CheckboxListTile(
              title: const Text('Labor'),
              value: _labor,
              onChanged: (v) => setState(() => _labor = v ?? false),
              controlAffinity: ListTileControlAffinity.leading,
            ),
            CheckboxListTile(
              title: const Text('Materials'),
              value: _materials,
              onChanged: (v) => setState(() => _materials = v ?? false),
              controlAffinity: ListTileControlAffinity.leading,
            ),
            CheckboxListTile(
              title: const Text('Others'),
              value: _others,
              onChanged: (v) => setState(() => _others = v ?? false),
              controlAffinity: ListTileControlAffinity.leading,
            ),
            const SizedBox(height: 16),
            const Text('Contact (optional)', style: TextStyle(fontWeight: FontWeight.w500)),
            const SizedBox(height: 8),
            TextFormField(
              controller: _customNameController,
              decoration: const InputDecoration(
                labelText: 'Full name',
                hintText: 'John Doe',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _customEmailController,
              decoration: const InputDecoration(
                labelText: 'Email',
                hintText: 'name@psu.palawan.edu.ph',
                border: OutlineInputBorder(),
              ),
              keyboardType: TextInputType.emailAddress,
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _customContactController,
              decoration: const InputDecoration(
                labelText: 'Contact number',
                hintText: '09XX XXX XXXX',
                border: OutlineInputBorder(),
              ),
              keyboardType: TextInputType.phone,
            ),
            if (_error != null) ...[
              const SizedBox(height: 16),
              Text(_error!, style: const TextStyle(color: Colors.red)),
            ],
            const SizedBox(height: 24),
            FilledButton(
              onPressed: _loading ? null : _submit,
              child: _loading
                  ? const SizedBox(
                      height: 20,
                      width: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text('Submit Request'),
            ),
          ],
        ),
      ),
    );
  }
}
