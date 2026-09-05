"""
Engine 5 - Nutrition Database.

Maps a detected food/preparation label to a verified nutrition record.
AI selects or ranks candidate records; verified nutritional facts come from the database
(per master plan section 3).
"""
from dataclasses import dataclass
from typing import Optional
from sqlalchemy.orm import Session

from app.models.database import SessionLocal, Food, Nutrition


@dataclass
class NutritionRecord:
    food_id: str
    name: str
    calories_100g: float
    protein_100g: float
    carbs_100g: float
    fat_100g: float
    fiber_100g: float = 0.0
    source: str = "usda_fdc"


def lookup_nutrition(food_label: str, db: Optional[Session] = None) -> NutritionRecord:
    """Returns the best-matching nutrition record for a food label from the database.

    Supports exact ID lookup, normalized matching, and case-insensitive name matching.
    Falls back to a generic estimate if not found.
    """
    clean_label = food_label.strip().lower().replace("-", "_").replace(" ", "_")
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        # 1. Exact ID match
        food = db.query(Food).filter(Food.id == clean_label).first()

        # 2. Search by substring/name match
        if not food:
            search_pattern = f"%{food_label.replace('_', ' ')}%"
            food = db.query(Food).filter(Food.name.ilike(search_pattern)).first()

        # 3. Match without prefix/suffix (e.g., 'rice' -> 'steamed_rice')
        if not food:
            food = db.query(Food).filter(Food.id.ilike(f"%{clean_label}%")).first()

        if food and food.nutrition:
            n = food.nutrition
            return NutritionRecord(
                food_id=food.id,
                name=food.name,
                calories_100g=n.calories_100g,
                protein_100g=n.protein_100g,
                carbs_100g=n.carbs_100g,
                fat_100g=n.fat_100g,
                fiber_100g=n.fiber_100g,
                source=n.source or "database",
            )
    except Exception as e:
        print(f"[NutritionService] Warning: DB lookup failed for '{food_label}': {e}")
    finally:
        if close_db:
            db.close()

    # Generic fallback if not recognized
    return NutritionRecord(
        food_id=clean_label,
        name=food_label.replace("_", " ").title(),
        calories_100g=150.0,
        protein_100g=5.0,
        carbs_100g=20.0,
        fat_100g=5.0,
        fiber_100g=1.0,
        source="unrecognized_estimate",
    )


def calculate_calories(weight_g: float, calories_100g: float) -> float:
    """calories = weight_g * calories_per_100g / 100 (plan section 9)."""
    return (weight_g * calories_100g) / 100.0
