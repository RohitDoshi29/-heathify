import 'package:flutter/material.dart';
import '../models/meal.dart';

/// Small pill showing confidence %, colored by band:
/// green (>90%), amber (75-90%), red (<75%) — mirrors the plan's
/// automatic retry policy in section 8.
class ConfidenceBadge extends StatelessWidget {
  final double confidence; // 0.0 - 1.0

  const ConfidenceBadge({super.key, required this.confidence});

  @override
  Widget build(BuildContext context) {
    final band = bandForConfidence(confidence);
    final Color color = switch (band) {
      ConfidenceBand.high => Colors.green,
      ConfidenceBand.medium => Colors.amber.shade700,
      ConfidenceBand.low => Colors.redAccent,
    };

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.circle, size: 8, color: color),
          const SizedBox(width: 6),
          Text(
            '${(confidence * 100).toInt()}% confident',
            style: TextStyle(color: color, fontWeight: FontWeight.w600, fontSize: 12),
          ),
        ],
      ),
    );
  }
}
