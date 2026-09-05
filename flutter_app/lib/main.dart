import 'dart:io' show Platform;
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'services/api_service.dart';
import 'screens/home_screen.dart';

const String customApiUrl = String.fromEnvironment('API_URL');

String get defaultBaseUrl {
  if (customApiUrl.isNotEmpty) {
    return customApiUrl;
  }
  if (kIsWeb) {
    return 'http://localhost:8000';
  }
  try {
    if (Platform.isAndroid || Platform.isIOS) {
      // Physical mobile device default (Mac LAN IP on Wi-Fi)
      return 'http://192.168.1.246:8000';
    }
  } catch (_) {}
  return 'http://127.0.0.1:8000';
}

void main() {
  runApp(const FoodCalorieApp());
}

class FoodCalorieApp extends StatelessWidget {
  const FoodCalorieApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        // Single shared API client for the whole app.
        Provider<ApiService>(
          create: (_) => ApiService(baseUrl: defaultBaseUrl),
        ),
      ],
      child: MaterialApp(
        title: 'Food Calorie Detector',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          colorSchemeSeed: const Color(0xFF2E7D32),
          useMaterial3: true,
        ),
        darkTheme: ThemeData(
          colorSchemeSeed: const Color(0xFF2E7D32),
          brightness: Brightness.dark,
          useMaterial3: true,
        ),
        home: const HomeScreen(),
      ),
    );
  }
}
