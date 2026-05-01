/// API base URL for the Django backend (HTTPS, no trailing slash).
///
/// Override at build/run time:
///   flutter run --dart-define=GSO_API_BASE=https://your-site.example
///
/// Fallback is for local dev only.
const String kGsoApiBase = String.fromEnvironment(
  'GSO_API_BASE',
  defaultValue: 'https://palsugso.site',
);
