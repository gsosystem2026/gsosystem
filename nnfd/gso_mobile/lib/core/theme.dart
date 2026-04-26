import 'package:flutter/material.dart';

class AppTheme {
  static ThemeData get light => ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFFFF6933)),
        useMaterial3: true,
        scaffoldBackgroundColor: const Color(0xFFF8F6F5),
      );
}
