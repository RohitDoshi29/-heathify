import 'package:flutter/material.dart';

/// Simple protein / carbs / fat summary row, reused on Home and Results.
class MacroSummary extends StatelessWidget {
  final double protein;
  final double carbs;
  final double fat;

  const MacroSummary({
    super.key,
    required this.protein,
    required this.carbs,
    required this.fat,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Expanded(child: _MacroTile(label: 'Protein', grams: protein, color: Colors.redAccent)),
            Expanded(child: _MacroTile(label: 'Carbs', grams: carbs, color: Colors.orangeAccent)),
            Expanded(child: _MacroTile(label: 'Fat', grams: fat, color: Colors.blueAccent)),
          ],
        ),
      ),
    );
  }
}

class _MacroTile extends StatelessWidget {
  final String label;
  final double grams;
  final Color color;

  const _MacroTile({required this.label, required this.grams, required this.color});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Icon(Icons.circle, size: 10, color: color),
        const SizedBox(height: 6),
        Text('${grams.toInt()}g',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
        Text(label, style: Theme.of(context).textTheme.bodySmall),
      ],
    );
  }
}
