import 'dart:io';
import 'package:flutter/material.dart';

import '../models/meal.dart';
import 'results_screen.dart';
import 'camera_screen.dart';

/// Analysis screen: shows live pipeline progress. If low confidence is detected
/// (retry_recommended == true), prompts user to retake with Reference Mode or proceed.
class AnalysisScreen extends StatelessWidget {
  final File imageFile;
  final Future<Meal> analyzeFuture;

  const AnalysisScreen({
    super.key,
    required this.imageFile,
    required this.analyzeFuture,
  });

  static const _stages = [
    'Detecting food & bounding boxes...',
    'Segmenting foreground masks...',
    'Estimating 3D depth & volume...',
    'Fusing multi-engine estimates & verifying...',
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Analyzing Meal')),
      body: FutureBuilder<Meal>(
        future: analyzeFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return _ProgressView(imageFile: imageFile, stages: _stages);
          }

          if (snapshot.hasError) {
            return _ErrorView(error: snapshot.error.toString());
          }

          final meal = snapshot.data!;

          // Automatic retry prompt for low confidence results
          if (meal.retryRecommended) {
            return _RetryPromptView(imageFile: imageFile, meal: meal);
          }

          // High / Medium confidence -> auto-navigate to Results screen
          WidgetsBinding.instance.addPostFrameCallback((_) {
            Navigator.of(context).pushReplacement(
              MaterialPageRoute(builder: (_) => ResultsScreen(meal: meal)),
            );
          });
          return const Center(child: CircularProgressIndicator());
        },
      ),
    );
  }
}

class _RetryPromptView extends StatelessWidget {
  final File imageFile;
  final Meal meal;

  const _RetryPromptView({required this.imageFile, required this.meal});

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(16),
              child: Image.file(imageFile, height: 180, fit: BoxFit.cover),
            ),
            const SizedBox(height: 20),
            Icon(Icons.warning_amber_rounded, size: 48, color: Colors.amber.shade700),
            const SizedBox(height: 12),
            Text(
              'Low Confidence Detected (${(meal.confidence * 100).toInt()}%)',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              meal.retryReason ??
                  'The image scale or angles are ambiguous. Retaking the photo with Reference Mode (e.g. placing a coin next to the plate) will significantly improve portion accuracy.',
              style: Theme.of(context).textTheme.bodyMedium,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 28),
            FilledButton.icon(
              icon: const Icon(Icons.camera_alt),
              label: const Text('Retake with Reference Mode'),
              onPressed: () {
                Navigator.of(context).pushReplacement(
                  MaterialPageRoute(builder: (_) => const CameraScreen()),
                );
              },
            ),
            const SizedBox(height: 12),
            OutlinedButton.icon(
              icon: const Icon(Icons.arrow_forward),
              label: const Text('Proceed & Adjust Manually'),
              onPressed: () {
                Navigator.of(context).pushReplacement(
                  MaterialPageRoute(builder: (_) => ResultsScreen(meal: meal)),
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}

class _ProgressView extends StatelessWidget {
  final File imageFile;
  final List<String> stages;

  const _ProgressView({required this.imageFile, required this.stages});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(16),
            child: Image.file(imageFile, height: 200, fit: BoxFit.cover),
          ),
          const SizedBox(height: 28),
          const CircularProgressIndicator(),
          const SizedBox(height: 24),
          ...stages.map(
            (s) => Padding(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Text(s, style: Theme.of(context).textTheme.bodyMedium),
            ),
          ),
        ],
      ),
    );
  }
}

class _ErrorView extends StatelessWidget {
  final String error;
  const _ErrorView({required this.error});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.error_outline, size: 64, color: Colors.redAccent),
          const SizedBox(height: 16),
          Text('Analysis failed', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          Text(error, textAlign: TextAlign.center),
          const SizedBox(height: 24),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Try Again'),
          ),
        ],
      ),
    );
  }
}
