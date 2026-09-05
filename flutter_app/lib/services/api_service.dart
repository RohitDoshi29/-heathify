import 'dart:io';
import 'package:dio/dio.dart';

import '../models/meal.dart';

/// Thin wrapper around the backend's core API, per the master plan:
///   POST /api/analyze     - upload image, run end-to-end analysis
///   POST /api/correction  - record a user-corrected food/quantity
///   GET  /api/meals       - meal history
///   GET  /api/meal/{id}   - detailed prediction + evidence
///   GET  /api/health      - service health check
class ApiService {
  final Dio _dio;
  final String baseUrl;

  ApiService({required this.baseUrl})
      : _dio = Dio(BaseOptions(
          baseUrl: baseUrl,
          connectTimeout: const Duration(seconds: 10),
          receiveTimeout: const Duration(seconds: 30),
        ));

  /// Uploads a captured/selected image and returns the fused analysis result.
  ///
  /// [referenceMode] flags whether a known-size reference object is present
  /// in frame, which the backend's portion engine can use to improve scale
  /// estimation (see plan section 5, "Reference-Assisted Modes").
  Future<Meal> analyzeMeal(File image, {bool referenceMode = false}) async {
    final formData = FormData.fromMap({
      'reference_mode': referenceMode,
      'image': await MultipartFile.fromFile(image.path,
          filename: image.uri.pathSegments.last),
    });

    final response = await _dio.post('/api/analyze', data: formData);
    return Meal.fromJson(response.data as Map<String, dynamic>);
  }

  /// Sends a user correction (e.g. adjusted weight) back to the feedback
  /// engine so it can be used for retraining/evaluation later.
  Future<void> submitCorrection({
    required String mealItemId,
    required double correctedWeightGrams,
    String correctionType = 'weight_adjustment',
  }) async {
    await _dio.post('/api/correction', data: {
      'meal_item_id': mealItemId,
      'corrected_weight_g': correctedWeightGrams,
      'correction_type': correctionType,
    });
  }

  /// Returns paginated meal history for the History screen.
  Future<List<Meal>> getMealHistory({int limit = 50, int offset = 0}) async {
    final response = await _dio.get('/api/meals', queryParameters: {
      'limit': limit,
      'offset': offset,
    });
    final list = response.data as List<dynamic>;
    return list.map((e) => Meal.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<Meal> getMealDetail(String mealId) async {
    final response = await _dio.get('/api/meal/$mealId');
    return Meal.fromJson(response.data as Map<String, dynamic>);
  }

  Future<bool> checkHealth() async {
    try {
      final response = await _dio.get('/api/health');
      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }
}
