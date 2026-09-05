import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:food_calorie_app/models/meal.dart';
import 'package:food_calorie_app/screens/home_screen.dart';
import 'package:food_calorie_app/services/api_service.dart';

class FakeApiService extends ApiService {
  FakeApiService() : super(baseUrl: 'http://localhost:8000');

  @override
  Future<List<Meal>> getMealHistory({int limit = 50, int offset = 0}) async {
    return [];
  }
}

void main() {
  testWidgets('App smoke test builds HomeScreen', (WidgetTester tester) async {
    await tester.pumpWidget(
      Provider<ApiService>(
        create: (_) => FakeApiService(),
        child: const MaterialApp(
          home: HomeScreen(),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Today'), findsOneWidget);
    expect(find.text('Scan Meal'), findsOneWidget);
  });
}
