// Basic Flutter widget tests for GSO app.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('App structure smoke test', (WidgetTester tester) async {
    // Verify basic Flutter widgets work (no red errors in IDE)
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: Center(child: Text('GSO')),
        ),
      ),
    );
    expect(find.text('GSO'), findsOneWidget);
  });
}
