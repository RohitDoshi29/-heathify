import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/meal.dart';
import '../models/food_item.dart';
import '../services/api_service.dart';
import '../widgets/confidence_badge.dart';
import '../widgets/macro_summary.dart';

/// Results screen: foods, grams, calories, macros, confidence, likely range,
/// and instant portion edit controls with low-confidence prompting.
class ResultsScreen extends StatefulWidget {
  final Meal meal;
  const ResultsScreen({super.key, required this.meal});

  @override
  State<ResultsScreen> createState() => _ResultsScreenState();
}

class _ResultsScreenState extends State<ResultsScreen> {
  late List<FoodItem> _items;

  @override
  void initState() {
    super.initState();
    _items = List.of(widget.meal.items);
  }

  double get _totalCalories =>
      _items.fold(0.0, (sum, i) => sum + i.estimatedCalories);

  bool get _hasLowConfidenceItem =>
      _items.any((i) => i.confidence < 0.60) || widget.meal.confidence < 0.60;

  Future<void> _editWeight(int index) async {
    final item = _items[index];
    final controller =
        TextEditingController(text: item.estimatedWeightGrams.toStringAsFixed(0));

    final newWeight = await showDialog<double>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Adjust Weight: ${item.name}'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Enter exact weight in grams to recalculate calories & macros:',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 12),
            TextField(
              controller: controller,
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
              decoration: const InputDecoration(
                labelText: 'Portion Weight',
                suffixText: 'g',
                border: OutlineInputBorder(),
              ),
              autofocus: true,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () {
              final parsed = double.tryParse(controller.text);
              Navigator.pop(context, parsed);
            },
            child: const Text('Save'),
          ),
        ],
      ),
    );

    if (newWeight == null || !mounted) return;

    setState(() {
      _items[index] = item.withCorrectedWeight(newWeight);
    });

    // Send the correction to the backend feedback engine
    try {
      context.read<ApiService>().submitCorrection(
            mealItemId: item.foodId,
            correctedWeightGrams: newWeight,
          );
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Updated ${item.name} to ${newWeight.toInt()}g'),
          duration: const Duration(seconds: 1),
        ),
      );
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    final meal = widget.meal;

    return Scaffold(
      appBar: AppBar(title: const Text('Meal Analysis')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (_hasLowConfidenceItem)
            Card(
              color: Theme.of(context).colorScheme.errorContainer.withValues(alpha: 0.4),
              margin: const EdgeInsets.only(bottom: 16),
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Row(
                  children: [
                    Icon(Icons.info_outline, color: Theme.of(context).colorScheme.error),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        'Lower confidence detected. Please verify or adjust portions below for maximum accuracy.',
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: Theme.of(context).colorScheme.onErrorContainer,
                            ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text('${_totalCalories.toInt()} kcal',
                          style: Theme.of(context)
                              .textTheme
                              .headlineMedium
                              ?.copyWith(fontWeight: FontWeight.bold)),
                      ConfidenceBadge(confidence: meal.confidence),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Estimated range: ${meal.calorieRangeLowKcal.toInt()} - ${meal.calorieRangeHighKcal.toInt()} kcal',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          MacroSummary(
            protein: _items.fold(0.0, (s, i) => s + i.proteinGrams),
            carbs: _items.fold(0.0, (s, i) => s + i.carbsGrams),
            fat: _items.fold(0.0, (s, i) => s + i.fatGrams),
          ),
          const SizedBox(height: 24),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('Detected items', style: Theme.of(context).textTheme.titleMedium),
              Text(
                'Tap edit to adjust',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(color: Colors.grey),
              ),
            ],
          ),
          const SizedBox(height: 8),
          ..._items.asMap().entries.map((entry) {
            final index = entry.key;
            final item = entry.value;
            final isLowConf = item.confidence < 0.60;

            return Card(
              child: ListTile(
                leading: CircleAvatar(
                  backgroundColor: isLowConf
                      ? Colors.orange.withValues(alpha: 0.2)
                      : Theme.of(context).colorScheme.primaryContainer,
                  child: Icon(
                    Icons.fastfood,
                    color: isLowConf ? Colors.orange : Theme.of(context).colorScheme.primary,
                  ),
                ),
                title: Text(item.name),
                subtitle: Text(
                  '${item.estimatedWeightGrams.toInt()} g  \u2022  ${item.estimatedCalories.toInt()} kcal  \u2022  ${(item.confidence * 100).toInt()}% conf',
                ),
                trailing: IconButton(
                  icon: const Icon(Icons.edit_outlined),
                  tooltip: 'Adjust weight',
                  onPressed: () => _editWeight(index),
                ),
                onTap: () => _editWeight(index),
              ),
            );
          }),
          const SizedBox(height: 24),
          FilledButton.icon(
            icon: const Icon(Icons.check_circle_outline),
            label: const Text('Save & Done'),
            onPressed: () {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('Meal saved successfully!'),
                  duration: Duration(seconds: 2),
                ),
              );
              Navigator.of(context).popUntil((route) => route.isFirst);
            },
          ),
        ],
      ),
    );
  }
}
