import 'motorpool_trip.dart';
import 'request_task.dart';

class RequestDetailPayload {
  const RequestDetailPayload({
    required this.task,
    this.motorpool,
  });

  final RequestTask task;
  final MotorpoolEnvelope? motorpool;

  factory RequestDetailPayload.fromJson(Map<String, dynamic> json) {
    return RequestDetailPayload(
      task: RequestTask.fromJson(json),
      motorpool: MotorpoolEnvelope.tryParse(json),
    );
  }
}
