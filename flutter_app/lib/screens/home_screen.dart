import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/meal.dart';
import '../services/api_service.dart';
import 'camera_screen.dart';
import 'history_screen.dart';
import 'results_screen.dart';
import '../widgets/macro_summary.dart';

/// Home screen: "Scan Meal" entry point, daily calories, macro summary,
/// and real recent meals loaded from the database.
class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  List<Meal> _recentMeals = [];
  bool _isLoading = true;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _loadMeals();
  }

  Future<void> _loadMeals() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final api = context.read<ApiService>();
      final meals = await api.getMealHistory(limit: 20);
      if (mounted) {
        setState(() {
          _recentMeals = meals;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = e.toString();
          _isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    const calorieGoal = 2000.0;

    // Filter today's meals to calculate daily totals
    final now = DateTime.now();
    final todayMeals = _recentMeals.where((m) {
      final dt = m.createdAt.toLocal();
      return dt.year == now.year && dt.month == now.month && dt.day == now.day;
    }).toList();

    double dailyCalories = 0.0;
    double protein = 0.0;
    double carbs = 0.0;
    double fat = 0.0;

    for (final m in todayMeals) {
      dailyCalories += m.totalCalories;
      for (final item in m.items) {
        protein += item.proteinGrams;
        carbs += item.carbsGrams;
        fat += item.fatGrams;
      }
    }

    return Scaffold(
      appBar: AppBar(
        title: const Text('Today'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh',
            onPressed: _loadMeals,
          ),
          IconButton(
            icon: const Icon(Icons.history),
            tooltip: 'Meal history',
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute(builder: (_) => const HistoryScreen()),
            ).then((_) => _loadMeals()),
          ),
        ],
      ),
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: _loadMeals,
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              if (_errorMessage != null)
                Card(
                  color: Theme.of(context).colorScheme.errorContainer,
                  margin: const EdgeInsets.only(bottom: 12),
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Row(
                      children: [
                        Icon(Icons.warning_amber_rounded,
                            color: Theme.of(context).colorScheme.onErrorContainer),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            'Could not refresh meals: $_errorMessage',
                            style: TextStyle(
                              color: Theme.of(context).colorScheme.onErrorContainer,
                              fontSize: 12,
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
                          Text('Calories today',
                              style: Theme.of(context).textTheme.titleMedium),
                          if (todayMeals.isNotEmpty)
                            Badge(
                              label: Text('${todayMeals.length} logged'),
                            ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.baseline,
                        textBaseline: TextBaseline.alphabetic,
                        children: [
                          Text('${dailyCalories.toInt()}',
                              style: Theme.of(context)
                                  .textTheme
                                  .displaySmall
                                  ?.copyWith(fontWeight: FontWeight.bold)),
                          Text(' / ${calorieGoal.toInt()} kcal',
                              style: Theme.of(context).textTheme.bodyMedium),
                        ],
                      ),
                      const SizedBox(height: 12),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(8),
                        child: LinearProgressIndicator(
                          value: (dailyCalories / calorieGoal).clamp(0.0, 1.0),
                          minHeight: 8,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
              MacroSummary(protein: protein, carbs: carbs, fat: fat),
              const SizedBox(height: 24),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text('Recent meals', style: Theme.of(context).textTheme.titleMedium),
                  if (_recentMeals.isNotEmpty)
                    TextButton(
                      onPressed: () => Navigator.of(context).push(
                        MaterialPageRoute(builder: (_) => const HistoryScreen()),
                      ).then((_) => _loadMeals()),
                      child: const Text('View all'),
                    ),
                ],
              ),
              const SizedBox(height: 8),
              if (_isLoading && _recentMeals.isEmpty)
                const Center(
                  child: Padding(
                    padding: EdgeInsets.all(32),
                    child: CircularProgressIndicator(),
                  ),
                )
              else if (_recentMeals.isEmpty)
                const _EmptyRecentMeals()
              else
                ..._recentMeals.take(5).map((meal) {
                  return Card(
                    margin: const EdgeInsets.only(bottom: 8),
                    child: ListTile(
                      leading: CircleAvatar(
                        backgroundColor: Theme.of(context).colorScheme.primaryContainer,
                        child: const Icon(Icons.restaurant),
                      ),
                      title: Text('${meal.totalCalories.toInt()} kcal'),
                      subtitle: Text(
                        meal.items.map((i) => i.name).join(', '),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                      trailing: Text('${(meal.confidence * 100).toInt()}% conf'),
                      onTap: () {
                        Navigator.of(context).push(
                          MaterialPageRoute(builder: (_) => ResultsScreen(meal: meal)),
                        ).then((_) => _loadMeals());
                      },
                    ),
                  );
                }),
            ],
          ),
        ),
      ),
      floatingActionButton: FloatingActionButton.extended(
        icon: const Icon(Icons.camera_alt),
        label: const Text('Scan Meal'),
        onPressed: () => Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => const CameraScreen()),
        ).then((_) => _loadMeals()),
      ),
    );
  }
}

class _EmptyRecentMeals extends StatelessWidget {
  const _EmptyRecentMeals();

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Row(
          children: [
            const Icon(Icons.restaurant, color: Colors.grey),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                'No meals logged yet. Tap "Scan Meal" to analyze your first food photo.',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
