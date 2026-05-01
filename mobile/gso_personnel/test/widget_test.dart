import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gso_personnel/screens/login_screen.dart';

void main() {
  testWidgets('Login screen shows GSO Login', (WidgetTester tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: LoginScreen(onSuccess: () {}),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('GSO Login'), findsOneWidget);
    expect(find.text('GSO Request Management'), findsOneWidget);
    expect(find.textContaining('Email / Username'), findsOneWidget);
  });
}
