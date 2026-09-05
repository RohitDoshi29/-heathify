import 'food_item.dart';

/// Confidence banding, matching the plan's automatic retry policy:
/// >90% auto-show, 75-90% show + easy correction, <75% ask for another photo.
enum ConfidenceBand { high, medium, low }

ConfidenceBand bandForConfidence(double confidence) {
  if (confidence >= 0.90) return ConfidenceBand.high;
  if (confidence >= 0.75) return ConfidenceBand.medium;
  return ConfidenceBand.low;
}

/// A single analyzed meal, corresponding to the `MEALS` table plus its
/// associated `MEAL_ITEMS`.
class Meal {
  final String id;
  final DateTime createdAt;
  final String? imageUrl;
  final List<FoodItem> items;
  final double confidence; // overall fused confidence
  final double calorieRangeLowKcal;
  final double calorieRangeHighKcal;
  final bool retryRecommended;
  final String? retryReason;

  const Meal({
    required this.id,
    required this.createdAt,
    required this.items,
    required this.confidence,
    required this.calorieRangeLowKcal,
    required this.calorieRangeHighKcal,
    this.imageUrl,
    this.retryRecommended = false,
    this.retryReason,
  });

  double get totalCalories =>
      items.fold(0.0, (sum, item) => sum + item.estimatedCalories);

  double get totalProtein =>
      items.fold(0.0, (sum, item) => sum + item.proteinGrams);

  double get totalCarbs =>
      items.fold(0.0, (sum, item) => sum + item.carbsGrams);

  double get totalFat => items.fold(0.0, (sum, item) => sum + item.fatGrams);

  ConfidenceBand get confidenceBand => bandForConfidence(confidence);

  factory Meal.fromJson(Map<String, dynamic> json) {
    return Meal(
      id: json['id'] as String,
      createdAt: DateTime.parse(json['created_at'] as String),
      imageUrl: json['image_url'] as String?,
      items: (json['items'] as List<dynamic>)
          .map((e) => FoodItem.fromJson(e as Map<String, dynamic>))
          .toList(),
      confidence: (json['confidence'] as num).toDouble(),
      calorieRangeLowKcal: (json['calorie_range_low'] as num).toDouble(),
      calorieRangeHighKcal: (json['calorie_range_high'] as num).toDouble(),
      retryRecommended: json['retry_recommended'] as bool? ?? false,
      retryReason: json['retry_reason'] as String?,
    );
  }
}
