import 'dart:async';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:dio/dio.dart';

import '../config/env.dart';

/// Computes "actually online" by combining interface state with a quick API probe.
class NetworkReachabilityService {
  NetworkReachabilityService._();
  static final NetworkReachabilityService instance = NetworkReachabilityService._();

  final _controller = StreamController<bool>.broadcast();
  StreamSubscription<List<ConnectivityResult>>? _connectivitySub;
  Timer? _timer;
  bool _runningCheck = false;
  bool _started = false;
  bool _isOnline = false;

  bool get isOnline => _isOnline;
  Stream<bool> get stream => _controller.stream;

  void start() {
    if (_started) return;
    _started = true;
    _connectivitySub = Connectivity().onConnectivityChanged.listen((_) => refresh());
    _timer = Timer.periodic(const Duration(seconds: 12), (_) => refresh());
    refresh();
  }

  Future<void> refresh() async {
    if (_runningCheck) return;
    _runningCheck = true;
    try {
      final results = await Connectivity().checkConnectivity();
      final hasTransport = results.any(
        (r) => r != ConnectivityResult.none && r != ConnectivityResult.bluetooth,
      );
      if (!hasTransport) {
        _setOnline(false);
        return;
      }

      final reachable = await _probeApi();
      _setOnline(reachable);
    } finally {
      _runningCheck = false;
    }
  }

  Future<bool> _probeApi() async {
    final dio = Dio(
      BaseOptions(
        connectTimeout: const Duration(seconds: 4),
        receiveTimeout: const Duration(seconds: 4),
        sendTimeout: const Duration(seconds: 4),
        validateStatus: (_) => true,
      ),
    );
    try {
      final response = await dio.get('$kGsoApiBase/api/v1/requests/');
      // 2xx/3xx/4xx means we reached the server; only transport failures should read as offline.
      return response.statusCode != null;
    } on DioException catch (e) {
      return e.response != null;
    } catch (_) {
      return false;
    }
  }

  void _setOnline(bool next) {
    if (_isOnline == next) return;
    _isOnline = next;
    _controller.add(_isOnline);
  }

  void dispose() {
    _timer?.cancel();
    _connectivitySub?.cancel();
    _controller.close();
    _started = false;
  }
}
