import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../app.dart';

// CampusBites-style colors (GSO branded)
const _primary = Color(0xFFFF6933);
const _bgLight = Color(0xFFF8F6F5);
const _slate900 = Color(0xFF0F172A);
const _slate600 = Color(0xFF475569);
const _slate400 = Color(0xFF94A3B8);
const _slate200 = Color(0xFFE2E8F0);

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _loading = false;
  bool _obscurePassword = true;
  String? _error;

  @override
  void dispose() {
    _usernameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _handleLogin() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final authRepo = ref.read(authRepositoryProvider);
      await authRepo.login(
        username: _usernameController.text.trim(),
        password: _passwordController.text,
      );
      await Future.delayed(const Duration(milliseconds: 300));
      if (!mounted) return;
      ref.invalidate(currentUserProvider);
      ref.read(pushServiceProvider).init();
      if (!mounted) return;
      context.go('/home');
    } catch (e) {
      if (mounted) {
        String msg = 'Login failed. Please check your credentials.';
        if (e.toString().contains('Connection refused') ||
            e.toString().contains('Failed host lookup')) {
          msg = 'Cannot reach server. Is Django running? (python manage.py runserver)';
        } else if (e.toString().contains('401') ||
            e.toString().contains('Invalid credentials')) {
          msg = 'Invalid username or password.';
        }
        setState(() => _error = msg);
      }
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _bgLight,
      body: SafeArea(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 400),
          child: Column(
            children: [
              // Header
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
                child: Row(
                  children: [
                    GestureDetector(
                      onTap: () => context.go('/splash'),
                      child: Icon(Icons.arrow_back, color: _slate900, size: 24),
                    ),
                    Expanded(
                      child: Text(
                        'GSO',
                        textAlign: TextAlign.center,
                        style: GoogleFonts.plusJakartaSans(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                          color: _slate900,
                        ),
                      ),
                    ),
                    const SizedBox(width: 24),
                  ],
                ),
              ),
              // Hero illustration
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(16),
                  child: SizedBox(
                    height: 200,
                    width: double.infinity,
                    child: Stack(
                      fit: StackFit.expand,
                      children: [
                        Container(
                          color: _primary.withOpacity(0.1),
                          child: Image.network(
                            'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=800',
                            fit: BoxFit.cover,
                            errorBuilder: (_, __, ___) => Container(
                              color: _primary.withOpacity(0.15),
                              child: Center(
                                child: Icon(
                                  Icons.business,
                                  size: 80,
                                  color: _primary.withOpacity(0.5),
                                ),
                              ),
                            ),
                          ),
                        ),
                        Container(
                          decoration: BoxDecoration(
                            gradient: LinearGradient(
                              begin: Alignment.topCenter,
                              end: Alignment.bottomCenter,
                              colors: [
                                Colors.transparent,
                                _primary.withOpacity(0.08),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
              // Welcome text
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 24, 16, 12),
                child: Column(
                  children: [
                    Text(
                      'Welcome back!',
                      style: GoogleFonts.plusJakartaSans(
                        fontSize: 28,
                        fontWeight: FontWeight.bold,
                        color: _slate900,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Log in to access the GSO Request Portal',
                      style: GoogleFonts.plusJakartaSans(
                        fontSize: 15,
                        color: _slate600,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ],
                ),
              ),
              // Form
              Expanded(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      // Username
                      Text(
                        'Username',
                        style: GoogleFonts.plusJakartaSans(
                          fontSize: 16,
                          fontWeight: FontWeight.w500,
                          color: _slate900,
                        ),
                      ),
                      const SizedBox(height: 8),
                      TextField(
                        controller: _usernameController,
                        style: GoogleFonts.plusJakartaSans(fontSize: 16),
                        decoration: InputDecoration(
                          hintText: 'Enter your username',
                          hintStyle: GoogleFonts.plusJakartaSans(color: _slate400),
                          filled: true,
                          fillColor: Colors.white,
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(16),
                            borderSide: const BorderSide(color: _slate200),
                          ),
                          enabledBorder: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(16),
                            borderSide: const BorderSide(color: _slate200),
                          ),
                          focusedBorder: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(16),
                            borderSide: const BorderSide(color: _primary, width: 2),
                          ),
                          contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 18),
                        ),
                      ),
                      const SizedBox(height: 20),
                      // Password
                      Text(
                        'Password',
                        style: GoogleFonts.plusJakartaSans(
                          fontSize: 16,
                          fontWeight: FontWeight.w500,
                          color: _slate900,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Container(
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(color: _slate200),
                          boxShadow: [
                            BoxShadow(
                              color: _primary.withOpacity(0.1),
                              blurRadius: 8,
                              offset: const Offset(0, 2),
                            ),
                          ],
                        ),
                        child: TextField(
                            controller: _passwordController,
                            obscureText: _obscurePassword,
                            style: GoogleFonts.plusJakartaSans(fontSize: 16),
                            decoration: InputDecoration(
                              hintText: 'Enter your password',
                              hintStyle: GoogleFonts.plusJakartaSans(color: _slate400),
                              border: InputBorder.none,
                              contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 18),
                              suffixIcon: IconButton(
                                icon: Icon(
                                  _obscurePassword ? Icons.visibility_outlined : Icons.visibility_off_outlined,
                                  color: _slate400,
                                  size: 22,
                                ),
                                onPressed: () => setState(() => _obscurePassword = !_obscurePassword),
                              ),
                            ),
                          ),
                        ),
                      // Forgot password
                      const SizedBox(height: 12),
                      Align(
                        alignment: Alignment.centerRight,
                        child: GestureDetector(
                          onTap: () {},
                          child: Text(
                            'Forgot password?',
                            style: GoogleFonts.plusJakartaSans(
                              fontSize: 14,
                              fontWeight: FontWeight.w600,
                              color: _primary,
                            ),
                          ),
                        ),
                      ),
                      if (_error != null) ...[
                        const SizedBox(height: 12),
                        Text(
                          _error!,
                          style: GoogleFonts.plusJakartaSans(
                            fontSize: 14,
                            color: Colors.red,
                          ),
                        ),
                      ],
                      // Login button
                      const SizedBox(height: 32),
                      SizedBox(
                        height: 56,
                        child: ElevatedButton(
                          onPressed: _loading ? null : _handleLogin,
                          style: ElevatedButton.styleFrom(
                            backgroundColor: _primary,
                            foregroundColor: Colors.white,
                            elevation: 4,
                            shadowColor: _primary.withOpacity(0.3),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(16),
                            ),
                          ),
                          child: _loading
                              ? const SizedBox(
                                  width: 24,
                                  height: 24,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                    color: Colors.white,
                                  ),
                                )
                              : Text(
                                  'Login',
                                  style: GoogleFonts.plusJakartaSans(
                                    fontSize: 16,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              // Footer
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 0, 16, 32),
                child: Text.rich(
                  TextSpan(
                    text: 'By logging in, you agree to our ',
                    style: GoogleFonts.plusJakartaSans(
                      fontSize: 13,
                      color: _slate600,
                    ),
                    children: [
                      TextSpan(
                        text: 'Terms of Service',
                        style: GoogleFonts.plusJakartaSans(
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                          color: _slate900,
                          decoration: TextDecoration.underline,
                        ),
                      ),
                    ],
                  ),
                  textAlign: TextAlign.center,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
