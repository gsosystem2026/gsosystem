/// MotorpoolTripData serializer shape from Django API.
class MotorpoolTripData {
  const MotorpoolTripData({
    this.requestingOffice,
    this.placesToBeVisited,
    this.itineraryOfTravel,
    this.tripDatetime,
    this.numberOfDays,
    this.numberOfPassengers,
    this.contactPerson,
    this.contactNumber,
    this.driverName,
    this.vehiclePlate,
    this.vehicleStampOrContractNo,
    this.vehicleTrans,
    this.otherConsumablesNotes,
    this.fuelBeginningLiters,
    this.fuelReceivedIssuedLiters,
    this.fuelAddedPurchasedLiters,
    this.fuelTotalAvailableLiters,
    this.fuelUsedLiters,
    this.fuelEndingLiters,
  });

  final String? requestingOffice;
  final String? placesToBeVisited;
  final String? itineraryOfTravel;
  final String? tripDatetime;
  final int? numberOfDays;
  final int? numberOfPassengers;
  final String? contactPerson;
  final String? contactNumber;
  final String? driverName;
  final String? vehiclePlate;
  final String? vehicleStampOrContractNo;
  final String? vehicleTrans;
  final String? otherConsumablesNotes;
  final String? fuelBeginningLiters;
  final String? fuelReceivedIssuedLiters;
  final String? fuelAddedPurchasedLiters;
  final String? fuelTotalAvailableLiters;
  final String? fuelUsedLiters;
  final String? fuelEndingLiters;

  static String? _s(dynamic v) {
    if (v == null) return null;
    final t = v.toString().trim();
    return t.isEmpty ? null : t;
  }

  static int? _i(dynamic v) {
    if (v == null) return null;
    if (v is int) return v;
    return int.tryParse(v.toString());
  }

  factory MotorpoolTripData.fromJson(Map<String, dynamic> json) {
    return MotorpoolTripData(
      requestingOffice: _s(json['requesting_office']),
      placesToBeVisited: _s(json['places_to_be_visited']),
      itineraryOfTravel: _s(json['itinerary_of_travel']),
      tripDatetime: _s(json['trip_datetime']),
      numberOfDays: _i(json['number_of_days']),
      numberOfPassengers: _i(json['number_of_passengers']),
      contactPerson: _s(json['contact_person']),
      contactNumber: _s(json['contact_number']),
      driverName: _s(json['driver_name']),
      vehiclePlate: _s(json['vehicle_plate']),
      vehicleStampOrContractNo: _s(json['vehicle_stamp_or_contract_no']),
      vehicleTrans: _s(json['vehicle_trans']),
      otherConsumablesNotes: _s(json['other_consumables_notes']),
      fuelBeginningLiters: _s(json['fuel_beginning_liters']),
      fuelReceivedIssuedLiters: _s(json['fuel_received_issued_liters']),
      fuelAddedPurchasedLiters: _s(json['fuel_added_purchased_liters']),
      fuelTotalAvailableLiters: _s(json['fuel_total_available_liters']),
      fuelUsedLiters: _s(json['fuel_used_liters']),
      fuelEndingLiters: _s(json['fuel_ending_liters']),
    );
  }
}

class MotorpoolEnvelope {
  const MotorpoolEnvelope({
    required this.trip,
    required this.canEditVehicle,
    required this.canEditActuals,
  });

  final MotorpoolTripData trip;
  final bool canEditVehicle;
  final bool canEditActuals;

  factory MotorpoolEnvelope.fromJson(Map<String, dynamic> json) {
    final tripRaw = json['trip'];
    return MotorpoolEnvelope(
      trip: MotorpoolTripData.fromJson(
        Map<String, dynamic>.from(tripRaw as Map),
      ),
      canEditVehicle: json['can_edit_vehicle'] == true,
      canEditActuals: json['can_edit_actuals'] == true,
    );
  }

  static MotorpoolEnvelope? tryParse(Map<String, dynamic> detailJson) {
    final raw = detailJson['motorpool'];
    if (raw is! Map) return null;
    return MotorpoolEnvelope.fromJson(Map<String, dynamic>.from(raw));
  }
}
