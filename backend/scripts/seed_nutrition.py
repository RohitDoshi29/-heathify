"""
Seed script: populates the foods and nutrition tables from backend/data/nutrition_seed.csv.
Can be executed directly:
    python scripts/seed_nutrition.py
Or imported and invoked on startup:
    seed_nutrition_data(db)
"""
import csv
import os
import sys
from pathlib import Path

# Add backend root to sys.path so app.* imports work cleanly
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from app.models.database import SessionLocal, init_db, Food, Nutrition


def seed_nutrition_data(db=None, csv_path=None) -> int:
    """Reads nutrition_seed.csv and populates the database."""
    if csv_path is None:
        csv_path = backend_root / "data" / "nutrition_seed.csv"

    if not os.path.exists(csv_path):
        print(f"[Seed] CSV file not found at: {csv_path}")
        return 0

    init_db()
    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True

    count = 0
    try:
        with open(csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                food_id = row["food_id"].strip()
                name = row["name"].strip()
                category = row.get("category", "").strip() or None
                preparation = row.get("preparation", "").strip() or None
                calories = float(row["calories_100g"])
                protein = float(row.get("protein_100g", 0))
                carbs = float(row.get("carbs_100g", 0))
                fat = float(row.get("fat_100g", 0))
                fiber = float(row.get("fiber_100g", 0))
                source = row.get("source", "seed_data").strip()

                food = db.query(Food).filter(Food.id == food_id).first()
                if not food:
                    food = Food(
                        id=food_id,
                        name=name,
                        category=category,
                        preparation=preparation,
                    )
                    db.add(food)
                    db.flush()

                nutrition = db.query(Nutrition).filter(Nutrition.food_id == food.id).first()
                if not nutrition:
                    nutrition = Nutrition(
                        food_id=food.id,
                        calories_100g=calories,
                        protein_100g=protein,
                        carbs_100g=carbs,
                        fat_100g=fat,
                        fiber_100g=fiber,
                        source=source,
                    )
                    db.add(nutrition)
                else:
                    nutrition.calories_100g = calories
                    nutrition.protein_100g = protein
                    nutrition.carbs_100g = carbs
                    nutrition.fat_100g = fat
                    nutrition.fiber_100g = fiber
                    nutrition.source = source

                count += 1

            db.commit()
            print(f"[Seed] Successfully seeded/updated {count} nutrition records.")
    except Exception as e:
        db.rollback()
        print(f"[Seed] Error seeding nutrition database: {e}")
        raise
    finally:
        if close_session:
            db.close()

    return count


if __name__ == "__main__":
    seed_nutrition_data()

