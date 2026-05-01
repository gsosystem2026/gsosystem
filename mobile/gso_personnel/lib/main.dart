import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import 'screens/task_list_screen.dart';
import 'screens/login_screen.dart';
import 'services/auth_repository.dart';
import 'theme/app_colors.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const GsoPersonnelApp());
}

class GsoPersonnelApp extends StatelessWidget {
  const GsoPersonnelApp({super.key});

  @override
  Widget build(BuildContext context) {
    final baseText = GoogleFonts.publicSansTextTheme();
    return MaterialApp(
      title: 'GSO Personnel',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: AppColors.primary,
          primary: AppColors.primary,
        ),
        textTheme: baseText,
        inputDecorationTheme: InputDecorationTheme(
          labelStyle: baseText.bodyMedium,
          hintStyle: baseText.bodySmall?.copyWith(color: AppColors.slate400),
        ),
      ),
      home: const _AuthGate(),
    );
  }
}

class _AuthGate extends StatefulWidget {
  const _AuthGate();

  @override
  State<_AuthGate> createState() => _AuthGateState();
}

class _AuthGateState extends State<_AuthGate> {
  final _auth = AuthRepository();
  bool? _loggedIn;

  @override
  void initState() {
    super.initState();
    _checkSession();
  }

  Future<void> _checkSession() async {
    final ok = await _auth.hasValidPersonnelSession();
    if (mounted) setState(() => _loggedIn = ok);
  }

  Future<void> _logout() async {
    await _auth.signOut();
    if (mounted) setState(() => _loggedIn = false);
  }

  @override
  Widget build(BuildContext context) {
    if (_loggedIn == null) {
      return Scaffold(
        body: Center(
          child: CircularProgressIndicator(color: Theme.of(context).colorScheme.primary),
        ),
      );
    }
    if (_loggedIn!) {
      return TaskListScreen(
        auth: _auth,
        onLogout: _logout,
      );
    }
    return LoginScreen(
      onSuccess: () => setState(() => _loggedIn = true),
    );
  }
}
