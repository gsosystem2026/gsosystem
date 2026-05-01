import 'package:flutter/material.dart';

import '../services/api_client.dart';
import '../services/auth_repository.dart';
import '../theme/app_colors.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({
    super.key,
    required this.auth,
    required this.onLogout,
  });

  final AuthRepository auth;
  final Future<void> Function() onLogout;

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  late final ApiClient _api;
  Map<String, dynamic>? _me;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _api = ApiClient(
      accessToken: widget.auth.readAccessToken,
      refreshAccessToken: widget.auth.refreshAccessToken,
    );
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final me = await _api.fetchCurrentUser();
      if (!mounted) return;
      setState(() {
        _me = me;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = _api.messageFromError(e);
        _loading = false;
      });
    }
  }

  String get _fullName {
    final first = (_me?['first_name'] ?? '').toString().trim();
    final last = (_me?['last_name'] ?? '').toString().trim();
    final n = '$first $last'.trim();
    if (n.isNotEmpty) return n;
    return (_me?['username'] ?? 'User').toString();
  }

  String get _roleLabel {
    final raw = (_me?['role'] ?? '').toString();
    if (raw.isEmpty) return '—';
    return raw.replaceAll('_', ' ').toLowerCase().split(' ').map((w) {
      if (w.isEmpty) return w;
      return '${w[0].toUpperCase()}${w.substring(1)}';
    }).join(' ');
  }

  Future<void> _openEditProfileDialog() async {
    final first = TextEditingController(text: (_me?['first_name'] ?? '').toString());
    final last = TextEditingController(text: (_me?['last_name'] ?? '').toString());
    final email = TextEditingController(text: (_me?['email'] ?? '').toString());
    final form = GlobalKey<FormState>();
    bool saving = false;

    await showDialog<void>(
      context: context,
      builder: (dialogContext) {
        return StatefulBuilder(
          builder: (context, setLocal) {
            return AlertDialog(
              title: const Text('Edit profile'),
              content: Form(
                key: form,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    TextFormField(
                      controller: first,
                      decoration: const InputDecoration(labelText: 'First name'),
                      validator: (v) =>
                          (v == null || v.trim().isEmpty) ? 'Required' : null,
                    ),
                    const SizedBox(height: 10),
                    TextFormField(
                      controller: last,
                      decoration: const InputDecoration(labelText: 'Last name'),
                      validator: (v) =>
                          (v == null || v.trim().isEmpty) ? 'Required' : null,
                    ),
                    const SizedBox(height: 10),
                    TextFormField(
                      controller: email,
                      decoration: const InputDecoration(labelText: 'Email'),
                      keyboardType: TextInputType.emailAddress,
                      validator: (v) {
                        final s = (v ?? '').trim();
                        if (s.isEmpty) return 'Required';
                        if (!s.contains('@')) return 'Invalid email';
                        return null;
                      },
                    ),
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: saving ? null : () => Navigator.of(dialogContext).pop(),
                  child: const Text('Cancel'),
                ),
                FilledButton(
                  onPressed: saving
                      ? null
                      : () async {
                          if (!(form.currentState?.validate() ?? false)) return;
                          setLocal(() => saving = true);
                          try {
                            final updated = await _api.updateCurrentUser(
                              firstName: first.text.trim(),
                              lastName: last.text.trim(),
                              email: email.text.trim(),
                            );
                            if (!mounted || !dialogContext.mounted) return;
                            setState(() => _me = updated);
                            Navigator.of(dialogContext).pop();
                            ScaffoldMessenger.of(this.context).showSnackBar(
                              const SnackBar(content: Text('Profile updated.')),
                            );
                          } catch (e) {
                            if (!mounted) return;
                            setLocal(() => saving = false);
                            ScaffoldMessenger.of(this.context).showSnackBar(
                              SnackBar(content: Text(_api.messageFromError(e))),
                            );
                          }
                        },
                  child: saving
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Text('Save'),
                ),
              ],
            );
          },
        );
      },
    );
  }

  Future<void> _openChangePasswordDialog() async {
    final current = TextEditingController();
    final next = TextEditingController();
    final confirm = TextEditingController();
    final form = GlobalKey<FormState>();
    bool saving = false;

    await showDialog<void>(
      context: context,
      builder: (dialogContext) {
        return StatefulBuilder(
          builder: (context, setLocal) {
            return AlertDialog(
              title: const Text('Change password'),
              content: Form(
                key: form,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    TextFormField(
                      controller: current,
                      decoration: const InputDecoration(labelText: 'Current password'),
                      obscureText: true,
                      validator: (v) => (v == null || v.isEmpty) ? 'Required' : null,
                    ),
                    const SizedBox(height: 10),
                    TextFormField(
                      controller: next,
                      decoration: const InputDecoration(labelText: 'New password'),
                      obscureText: true,
                      validator: (v) => (v == null || v.length < 8)
                          ? 'Use at least 8 characters'
                          : null,
                    ),
                    const SizedBox(height: 10),
                    TextFormField(
                      controller: confirm,
                      decoration: const InputDecoration(labelText: 'Confirm new password'),
                      obscureText: true,
                      validator: (v) =>
                          v != next.text ? 'Passwords do not match' : null,
                    ),
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: saving ? null : () => Navigator.of(dialogContext).pop(),
                  child: const Text('Cancel'),
                ),
                FilledButton(
                  onPressed: saving
                      ? null
                      : () async {
                          if (!(form.currentState?.validate() ?? false)) return;
                          setLocal(() => saving = true);
                          try {
                            await _api.changePassword(
                              currentPassword: current.text,
                              newPassword: next.text,
                            );
                            if (!mounted || !dialogContext.mounted) return;
                            Navigator.of(dialogContext).pop();
                            ScaffoldMessenger.of(this.context).showSnackBar(
                              const SnackBar(content: Text('Password updated.')),
                            );
                          } catch (e) {
                            if (!mounted) return;
                            setLocal(() => saving = false);
                            ScaffoldMessenger.of(this.context).showSnackBar(
                              SnackBar(content: Text(_api.messageFromError(e))),
                            );
                          }
                        },
                  child: saving
                      ? const SizedBox(
                          width: 18,
                          height: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Text('Update'),
                ),
              ],
            );
          },
        );
      },
    );
  }

  Future<void> _logout() async {
    await widget.onLogout();
    if (!mounted) return;
    Navigator.of(context).pop();
  }

  @override
  Widget build(BuildContext context) {
    final t = Theme.of(context).textTheme;
    return Scaffold(
      body: SafeArea(
        child: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(_error!, textAlign: TextAlign.center),
                        const SizedBox(height: 16),
                        FilledButton(onPressed: _load, child: const Text('Retry')),
                      ],
                    ),
                  ),
                )
              : Column(
                  children: [
                    Container(
                      padding: const EdgeInsets.fromLTRB(16, 14, 16, 12),
                      child: Row(
                        children: [
                          IconButton(
                            onPressed: () => Navigator.of(context).pop(),
                            icon: const Icon(Icons.arrow_back_rounded),
                          ),
                          const SizedBox(width: 6),
                          Text(
                            'My Profile',
                            style: t.headlineSmall?.copyWith(
                              color: AppColors.slate900,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ],
                      ),
                    ),
                    Expanded(
                      child: ListView(
                        padding: const EdgeInsets.all(16),
                        children: [
                          Container(
                            decoration: BoxDecoration(
                              color: Colors.white,
                              borderRadius: BorderRadius.circular(14),
                              border: Border.all(color: AppColors.slate200),
                              boxShadow: [
                                BoxShadow(
                                  color: Colors.black.withOpacity(0.05),
                                  blurRadius: 18,
                                  offset: const Offset(0, 8),
                                ),
                              ],
                            ),
                            child: Padding(
                              padding: const EdgeInsets.fromLTRB(20, 20, 20, 22),
                              child: Column(
                                children: [
                                  CircleAvatar(
                                    radius: 56,
                                    backgroundColor: AppColors.primary.withOpacity(0.12),
                                    child: const Icon(
                                      Icons.person_rounded,
                                      size: 62,
                                      color: AppColors.primary,
                                    ),
                                  ),
                                  const SizedBox(height: 18),
                                  Text(
                                    _fullName,
                                    textAlign: TextAlign.center,
                                    style: t.headlineMedium?.copyWith(
                                      fontWeight: FontWeight.w700,
                                      color: AppColors.slate900,
                                    ),
                                  ),
                                  const SizedBox(height: 8),
                                  Text(
                                    _roleLabel,
                                    style: t.titleMedium?.copyWith(color: AppColors.slate500),
                                  ),
                                  const SizedBox(height: 20),
                                  Row(
                                    children: [
                                      Expanded(
                                        child: FilledButton.icon(
                                          onPressed: _openEditProfileDialog,
                                          icon: const Icon(Icons.edit_rounded),
                                          label: const Text('Edit profile'),
                                        ),
                                      ),
                                      const SizedBox(width: 12),
                                      Expanded(
                                        child: OutlinedButton.icon(
                                          onPressed: _openChangePasswordDialog,
                                          icon: const Icon(Icons.key_rounded),
                                          label: const Text('Change password'),
                                        ),
                                      ),
                                    ],
                                  ),
                                ],
                              ),
                            ),
                          ),
                          const SizedBox(height: 12),
                          OutlinedButton.icon(
                            onPressed: _logout,
                            icon: const Icon(Icons.logout_rounded),
                            label: const Text('Logout'),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
      ),
    );
  }
}

