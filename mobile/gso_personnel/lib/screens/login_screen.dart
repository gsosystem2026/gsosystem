import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:url_launcher/url_launcher.dart';

import '../config/env.dart';
import '../services/auth_repository.dart';
import '../theme/app_colors.dart';

/// Matches web `templates/registration/login.html` — scaled for phones.
class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key, required this.onSuccess});

  final VoidCallback onSuccess;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _usernameCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  final _auth = AuthRepository();

  bool _obscurePassword = true;
  bool _rememberMe = true;
  bool _submitting = false;
  String? _errorText;

  @override
  void dispose() {
    _usernameCtrl.dispose();
    _passwordCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _submitting = true;
      _errorText = null;
    });
    try {
      await _auth.signInWithPassword(
        username: _usernameCtrl.text,
        password: _passwordCtrl.text,
      );
      if (!mounted) return;
      widget.onSuccess();
    } on AuthException catch (e) {
      setState(() => _errorText = e.message);
    } catch (_) {
      setState(() => _errorText = 'Something went wrong. Try again.');
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  Future<void> _openPath(String path) async {
    final uri = Uri.parse('$kGsoApiBase$path');
    final ok = await launchUrl(uri, mode: LaunchMode.externalApplication);
    if (!mounted || ok) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Could not open link.')),
    );
  }

  @override
  Widget build(BuildContext context) {
    final textTheme = GoogleFonts.publicSansTextTheme(Theme.of(context).textTheme);

    return Scaffold(
      body: Container(
        width: double.infinity,
        height: double.infinity,
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [AppColors.gradientStart, AppColors.backgroundLight],
          ),
        ),
        child: SafeArea(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              _Header(textTheme: textTheme),
              Expanded(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.fromLTRB(20, 8, 20, 24),
                  child: Column(
                    children: [
                      _LoginCard(
                        textTheme: textTheme,
                        formKey: _formKey,
                        usernameCtrl: _usernameCtrl,
                        passwordCtrl: _passwordCtrl,
                        obscurePassword: _obscurePassword,
                        onTogglePassword: () => setState(
                          () => _obscurePassword = !_obscurePassword,
                        ),
                        rememberMe: _rememberMe,
                        onRememberChanged: (v) =>
                            setState(() => _rememberMe = v ?? false),
                        errorText: _errorText,
                        submitting: _submitting,
                        onSubmit: _submit,
                        onForgotPassword: () => _openPath('/accounts/password-reset/'),
                        onGoogle: () => _openPath('/accounts/google/login/'),
                      ),
                      const SizedBox(height: 28),
                      _DepartmentalUnits(textTheme: textTheme),
                      const SizedBox(height: 24),
                      _Footer(textTheme: textTheme, onOpenPath: _openPath),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Header extends StatelessWidget {
  const _Header({required this.textTheme});

  final TextTheme textTheme;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: const BoxDecoration(
        color: Colors.white,
        border: Border(bottom: BorderSide(color: AppColors.slate200)),
      ),
      child: Row(
        children: [
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: AppColors.primary.withOpacity(0.1),
              borderRadius: BorderRadius.circular(8),
            ),
            clipBehavior: Clip.antiAlias,
            child: Padding(
              padding: const EdgeInsets.all(6),
              child: Image.asset(
                'assets/images/gso_logo.png',
                fit: BoxFit.contain,
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              'GSO Request Management',
              style: textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.w700,
                color: AppColors.slate900,
                letterSpacing: -0.3,
              ),
            ),
          ),
          const Icon(Icons.shield_outlined, size: 18, color: AppColors.slate400),
          const SizedBox(width: 4),
          Text(
            'SECURED',
            style: textTheme.labelSmall?.copyWith(
              fontWeight: FontWeight.w700,
              color: AppColors.slate500,
              letterSpacing: 1.2,
            ),
          ),
        ],
      ),
    );
  }
}

class _LoginCard extends StatelessWidget {
  const _LoginCard({
    required this.textTheme,
    required this.formKey,
    required this.usernameCtrl,
    required this.passwordCtrl,
    required this.obscurePassword,
    required this.onTogglePassword,
    required this.rememberMe,
    required this.onRememberChanged,
    required this.errorText,
    required this.submitting,
    required this.onSubmit,
    required this.onForgotPassword,
    required this.onGoogle,
  });

  final TextTheme textTheme;
  final GlobalKey<FormState> formKey;
  final TextEditingController usernameCtrl;
  final TextEditingController passwordCtrl;
  final bool obscurePassword;
  final VoidCallback onTogglePassword;
  final bool rememberMe;
  final ValueChanged<bool?> onRememberChanged;
  final String? errorText;
  final bool submitting;
  final VoidCallback onSubmit;
  final VoidCallback onForgotPassword;
  final VoidCallback onGoogle;

  @override
  Widget build(BuildContext context) {
    final border = OutlineInputBorder(
      borderRadius: BorderRadius.circular(10),
      borderSide: const BorderSide(color: AppColors.slate200),
    );

    return Container(
      constraints: const BoxConstraints(maxWidth: 400),
      margin: const EdgeInsets.symmetric(horizontal: 0),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppColors.slate200),
        boxShadow: [
          BoxShadow(
            color: AppColors.primary.withOpacity(0.06),
            blurRadius: 24,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 22, 20, 0),
            child: Column(
              children: [
                Text(
                  'GSO Login',
                  style: textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.w700,
                    color: AppColors.slate900,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  'Access the General Services Office Portal',
                  textAlign: TextAlign.center,
                  style: textTheme.bodySmall?.copyWith(color: AppColors.slate500),
                ),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(20),
            child: Form(
              key: formKey,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  if (errorText != null) ...[
                    Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: AppColors.red600.withOpacity(0.08),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        errorText!,
                        style: textTheme.bodySmall?.copyWith(
                          color: AppColors.red600,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                    const SizedBox(height: 14),
                  ],
                  Text(
                    'Email / Username',
                    style: textTheme.labelLarge?.copyWith(
                      fontWeight: FontWeight.w600,
                      color: AppColors.slate700,
                    ),
                  ),
                  const SizedBox(height: 6),
                  TextFormField(
                    controller: usernameCtrl,
                    keyboardType: TextInputType.emailAddress,
                    textInputAction: TextInputAction.next,
                    autofillHints: const [AutofillHints.username],
                    validator: (v) =>
                        (v == null || v.trim().isEmpty) ? 'Required' : null,
                    decoration: InputDecoration(
                      hintText: 'Enter your email or username',
                      hintStyle: TextStyle(color: AppColors.slate400, fontSize: 13),
                      prefixIcon: const Icon(Icons.person_outline_rounded, size: 20),
                      filled: true,
                      fillColor: Colors.white,
                      border: border,
                      enabledBorder: border,
                      focusedBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(10),
                        borderSide: const BorderSide(color: AppColors.primary, width: 2),
                      ),
                      contentPadding: const EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 14,
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),
                  Row(
                    children: [
                      Text(
                        'Password',
                        style: textTheme.labelLarge?.copyWith(
                          fontWeight: FontWeight.w600,
                          color: AppColors.slate700,
                        ),
                      ),
                      const Spacer(),
                      TextButton(
                        onPressed: onForgotPassword,
                        style: TextButton.styleFrom(
                          padding: EdgeInsets.zero,
                          minimumSize: Size.zero,
                          tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                        ),
                        child: Text(
                          'Forgot Password?',
                          style: textTheme.labelSmall?.copyWith(
                            fontWeight: FontWeight.w700,
                            color: AppColors.primary,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  TextFormField(
                    controller: passwordCtrl,
                    obscureText: obscurePassword,
                    textInputAction: TextInputAction.done,
                    onFieldSubmitted: (_) => onSubmit(),
                    autofillHints: const [AutofillHints.password],
                    validator: (v) =>
                        (v == null || v.isEmpty) ? 'Required' : null,
                    decoration: InputDecoration(
                      hintText: 'Enter your password',
                      hintStyle: TextStyle(color: AppColors.slate400, fontSize: 13),
                      prefixIcon: const Icon(Icons.lock_outline_rounded, size: 20),
                      suffixIcon: IconButton(
                        onPressed: onTogglePassword,
                        icon: Icon(
                          obscurePassword
                              ? Icons.visibility_rounded
                              : Icons.visibility_off_rounded,
                          size: 20,
                          color: AppColors.slate400,
                        ),
                      ),
                      filled: true,
                      fillColor: Colors.white,
                      border: border,
                      enabledBorder: border,
                      focusedBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(10),
                        borderSide: const BorderSide(color: AppColors.primary, width: 2),
                      ),
                      contentPadding: const EdgeInsets.symmetric(
                        horizontal: 12,
                        vertical: 14,
                      ),
                    ),
                  ),
                  const SizedBox(height: 14),
                  Row(
                    children: [
                      SizedBox(
                        height: 22,
                        width: 22,
                        child: Checkbox(
                          value: rememberMe,
                          onChanged: onRememberChanged,
                          activeColor: AppColors.primary,
                          side: const BorderSide(color: AppColors.slate200),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(4),
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          'Remember me for 30 days',
                          style: textTheme.bodySmall?.copyWith(
                            color: AppColors.slate600,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 18),
                  FilledButton(
                    onPressed: submitting ? null : onSubmit,
                    style: FilledButton.styleFrom(
                      backgroundColor: AppColors.primary,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(10),
                      ),
                      elevation: 4,
                      shadowColor: AppColors.primary.withOpacity(0.35),
                    ),
                    child: submitting
                        ? const SizedBox(
                            height: 22,
                            width: 22,
                            child: CircularProgressIndicator(
                              strokeWidth: 2.2,
                              color: Colors.white,
                            ),
                          )
                        : Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              const Icon(Icons.login_rounded, size: 20),
                              const SizedBox(width: 8),
                              Text(
                                'Sign In',
                                style: textTheme.titleSmall?.copyWith(
                                  fontWeight: FontWeight.w700,
                                  color: Colors.white,
                                ),
                              ),
                            ],
                          ),
                  ),
                  const SizedBox(height: 18),
                  Row(
                    children: [
                      const Expanded(child: Divider(color: AppColors.slate200)),
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 10),
                        child: Text(
                          'or',
                          style: textTheme.labelSmall?.copyWith(
                            color: AppColors.slate400,
                          ),
                        ),
                      ),
                      const Expanded(child: Divider(color: AppColors.slate200)),
                    ],
                  ),
                  const SizedBox(height: 14),
                  OutlinedButton(
                    onPressed: onGoogle,
                    style: OutlinedButton.styleFrom(
                      foregroundColor: AppColors.slate700,
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      side: const BorderSide(color: AppColors.slate200),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(10),
                      ),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const _GoogleMark(),
                        const SizedBox(width: 10),
                        Text(
                          'Continue with Google',
                          style: textTheme.titleSmall?.copyWith(
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
          Container(
            padding: const EdgeInsets.fromLTRB(20, 16, 20, 18),
            decoration: const BoxDecoration(
              color: AppColors.slate100,
              border: Border(top: BorderSide(color: AppColors.slate200)),
              borderRadius: BorderRadius.vertical(bottom: Radius.circular(13)),
            ),
            child: Column(
              children: [
                Text(
                  'AUTHORIZED PERSONNEL ONLY',
                  textAlign: TextAlign.center,
                  style: textTheme.labelSmall?.copyWith(
                    fontWeight: FontWeight.w800,
                    color: AppColors.slate400,
                    letterSpacing: 2,
                  ),
                ),
                const SizedBox(height: 12),
                Icon(
                  Icons.verified_user_outlined,
                  size: 40,
                  color: AppColors.slate400.withOpacity(0.45),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _GoogleMark extends StatelessWidget {
  const _GoogleMark();

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 22,
      height: 22,
      child: Column(
        children: [
          Expanded(
            child: Row(
              children: const [
                Expanded(child: ColoredBox(color: Color(0xFFF44336))),
                Expanded(child: ColoredBox(color: Color(0xFFFBBC05))),
              ],
            ),
          ),
          Expanded(
            child: Row(
              children: const [
                Expanded(child: ColoredBox(color: Color(0xFF34A853))),
                Expanded(child: ColoredBox(color: Color(0xFF4285F4))),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _DepartmentalUnits extends StatelessWidget {
  const _DepartmentalUnits({required this.textTheme});

  final TextTheme textTheme;

  @override
  Widget build(BuildContext context) {
    const units = [
      (Icons.build_rounded, 'Repair &\nMaintenance'),
      (Icons.water_drop_rounded, 'Utility\nServices'),
      (Icons.bolt_rounded, 'Electrical\nUnit'),
      (Icons.directions_car_rounded, 'Motorpool'),
    ];

    return Column(
      children: [
        Text(
          'DEPARTMENTAL UNITS',
          style: textTheme.labelSmall?.copyWith(
            fontWeight: FontWeight.w800,
            color: AppColors.slate400,
            letterSpacing: 3,
          ),
        ),
        const SizedBox(height: 16),
        Wrap(
          alignment: WrapAlignment.center,
          spacing: 10,
          runSpacing: 10,
          children: units.map((u) {
            return Container(
              width: 132,
              padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 8),
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.65),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: AppColors.slate200.withOpacity(0.7),
                ),
              ),
              child: Column(
                children: [
                  Container(
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(
                      color: AppColors.primary.withOpacity(0.1),
                      shape: BoxShape.circle,
                    ),
                    child: Icon(u.$1, size: 22, color: AppColors.primary),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    u.$2,
                    textAlign: TextAlign.center,
                    style: textTheme.labelSmall?.copyWith(
                      fontWeight: FontWeight.w700,
                      color: AppColors.slate600,
                      height: 1.2,
                    ),
                  ),
                ],
              ),
            );
          }).toList(),
        ),
      ],
    );
  }
}

class _Footer extends StatelessWidget {
  const _Footer({required this.textTheme, required this.onOpenPath});

  final TextTheme textTheme;
  final Future<void> Function(String path) onOpenPath;

  @override
  Widget build(BuildContext context) {
    final year = DateTime.now().year;
    return Column(
      children: [
        Text(
          '© $year General Services Office. All rights reserved.',
          textAlign: TextAlign.center,
          style: textTheme.bodySmall?.copyWith(color: AppColors.slate400),
        ),
        const SizedBox(height: 10),
        Wrap(
          alignment: WrapAlignment.center,
          spacing: 16,
          runSpacing: 8,
          children: [
            TextButton(
              onPressed: () => onOpenPath('/accounts/info/privacy/'),
              child: Text(
                'Privacy Policy',
                style: textTheme.labelMedium?.copyWith(color: AppColors.primary),
              ),
            ),
            TextButton(
              onPressed: () => onOpenPath('/accounts/info/terms/'),
              child: Text(
                'Terms of Service',
                style: textTheme.labelMedium?.copyWith(color: AppColors.primary),
              ),
            ),
            TextButton(
              onPressed: () => onOpenPath('/accounts/info/support/'),
              child: Text(
                'Contact Support',
                style: textTheme.labelMedium?.copyWith(color: AppColors.primary),
              ),
            ),
          ],
        ),
      ],
    );
  }
}
