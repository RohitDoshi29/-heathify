/// A single detected/estimated food item within a meal.
///
/// Mirrors the `MEAL_ITEMS` table described in the master plan:
/// meal_id, food_id, estimated_weight, estimated_calories, confidence.
class FoodItem {
  final String foodId;
  final String name;
  final double estimatedWeightGrams;
  final double estimatedCalories;
  final double proteinGrams;
  final double carbsGrams;
  final double fatGrams;
  final double confidence; // 0.0 - 1.0

  const FoodItem({
    required this.foodId,
    required this.name,
    required this.estimatedWeightGrams,
    required this.estimatedCalories,
    required this.proteinGrams,
    required this.carbsGrams,
    required this.fatGrams,
    required this.confidence,
  });

  factory FoodItem.fromJson(Map<String, dynamic> json) {
    return FoodItem(
      foodId: json['food_id'] as String,
      name: json['name'] as String,
      estimatedWeightGrams: (json['estimated_weight_g'] as num).toDouble(),
      estimatedCalories: (json['estimated_calories'] as num).toDouble(),
      proteinGrams: (json['protein_g'] as num?)?.toDouble() ?? 0,
      carbsGrams: (json['carbs_g'] as num?)?.toDouble() ?? 0,
      fatGrams: (json['fat_g'] as num?)?.toDouble() ?? 0,
      confidence: (json['confidence'] as num).toDouble(),
    );
  }

  Map<String, dynamic> toJson() => {
        'food_id': foodId,
        'name': name,
        'estimated_weight_g': estimatedWeightGrams,
        'estimated_calories': estimatedCalories,
        'protein_g': proteinGrams,
        'carbs_g': carbsGrams,
        'fat_g': fatGrams,
        'confidence': confidence,
      };

  /// Returns a copy with a user-corrected weight, recalculating calories
  /// proportionally (mirrors calories = weight_g * calories_per_100g / 100).
  FoodItem withCorrectedWeight(double newWeightGrams) {
    final ratio = estimatedWeightGrams == 0
        ? 0
        : newWeightGrams / estimatedWeightGrams;
    return FoodItem(
      foodId: foodId,
      name: name,
      estimatedWeightGrams: newWeightGrams,
      estimatedCalories: estimatedCalories * ratio,
      proteinGrams: proteinGrams * ratio,
      carbsGrams: carbsGrams * ratio,
      fatGrams: fatGrams * ratio,
      confidence: 1.0, // user-confirmed
    );
  }
}
