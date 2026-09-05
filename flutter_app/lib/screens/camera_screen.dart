import 'dart:io';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';

import '../services/api_service.dart';
import 'analysis_screen.dart';

/// Camera screen: live frame, capture, and an optional "reference mode"
/// toggle (per plan section 15). Uses image_picker for the basic scaffold;
/// swap in the `camera` package for a fully custom live-preview UI later.
class CameraScreen extends StatefulWidget {
  const CameraScreen({super.key});

  @override
  State<CameraScreen> createState() => _CameraScreenState();
}

class _CameraScreenState extends State<CameraScreen> {
  bool _referenceMode = false;
  bool _isCapturing = false;

  Future<void> _captureAndAnalyze(ImageSource source) async {
    setState(() => _isCapturing = true);
    final api = context.read<ApiService>();
    final navigator = Navigator.of(context);
    final messenger = ScaffoldMessenger.of(context);

    try {
      final picker = ImagePicker();
      XFile? picked;
      try {
        picked = await picker.pickImage(source: source, imageQuality: 90);
      } catch (e) {
        if (source == ImageSource.camera) {
          messenger.showSnackBar(
            const SnackBar(content: Text('Direct camera capture is only available on mobile. Opening file picker...')),
          );
          picked = await picker.pickImage(source: ImageSource.gallery, imageQuality: 90);
        } else {
          rethrow;
        }
      }

      if (picked == null || !mounted) return;

      navigator.push(
        MaterialPageRoute(
          builder: (_) => AnalysisScreen(
            imageFile: File(picked!.path),
            analyzeFuture:
                api.analyzeMeal(File(picked.path), referenceMode: _referenceMode),
          ),
        ),
      );
    } catch (e) {
      if (mounted) {
        messenger.showSnackBar(
          SnackBar(content: Text('Error picking image: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _isCapturing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Scan Meal')),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.restaurant_menu, size: 96, color: Colors.grey),
              const SizedBox(height: 24),
              SwitchListTile(
                title: const Text('Reference mode'),
                subtitle: const Text(
                    'Place a known-size object (e.g. a coin) near the plate to improve portion accuracy'),
                value: _referenceMode,
                onChanged: (v) => setState(() => _referenceMode = v),
              ),
              const SizedBox(height: 24),
              FilledButton.icon(
                icon: const Icon(Icons.camera_alt),
                label: const Text('Take Photo'),
                onPressed: _isCapturing
                    ? null
                    : () => _captureAndAnalyze(ImageSource.camera),
              ),
              const SizedBox(height: 12),
              OutlinedButton.icon(
                icon: const Icon(Icons.photo_library),
                label: const Text('Choose from Gallery'),
                onPressed: _isCapturing
                    ? null
                    : () => _captureAndAnalyze(ImageSource.gallery),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
