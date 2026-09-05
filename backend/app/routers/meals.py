"""
GET /api/meals       - return meal history
GET /api/meal/{id}   - return detailed prediction, nutrition, confidence, evidence
"""
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.models.database import get_db, Meal as DBMeal, MealItem as DBMealItem, Food as DBFood
from app.models.schemas import MealOut, FoodItemOut

router = APIRouter()


def _db_meal_to_mealout(meal: DBMeal) -> MealOut:
    items_out: list[FoodItemOut] = []
    for item in meal.items:
        food_name = item.food.name if item.food else "Unknown food"
        protein = 0.0
        carbs = 0.0
        fat = 0.0
        if item.food and item.food.nutrition:
            n = item.food.nutrition
            protein = round(n.protein_100g * item.estimated_weight / 100.0, 1)
            carbs = round(n.carbs_100g * item.estimated_weight / 100.0, 1)
            fat = round(n.fat_100g * item.estimated_weight / 100.0, 1)

        items_out.append(
            FoodItemOut(
                food_id=item.id,
                name=food_name,
                estimated_weight_g=round(item.estimated_weight, 1),
                estimated_calories=round(item.estimated_calories, 1),
                protein_g=protein,
                carbs_g=carbs,
                fat_g=fat,
                confidence=round(item.confidence, 2),
            )
        )

    tot_cal = meal.total_calories or sum(i.estimated_calories for i in items_out)
    conf = round(meal.confidence or 0.85, 2)
    band = "high" if conf >= 0.90 else ("medium" if conf >= 0.75 else "low")
    return MealOut(
        id=meal.id,
        created_at=meal.created_at or datetime.now(timezone.utc),
        image_url=meal.image,
        items=items_out,
        confidence=conf,
        calorie_range_low=round(tot_cal * 0.9, 1),
        calorie_range_high=round(tot_cal * 1.1, 1),
        confidence_band=band,
        retry_recommended=(band == "low"),
        retry_reason=None,
    )


@router.get("/meals", response_model=list[MealOut])
def get_meal_history(limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    meals = (
        db.query(DBMeal)
        .order_by(DBMeal.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [_db_meal_to_mealout(m) for m in meals]


@router.get("/meal/{meal_id}", response_model=MealOut)
def get_meal_detail(meal_id: str, db: Session = Depends(get_db)):
    meal = db.query(DBMeal).filter(DBMeal.id == meal_id).first()
    if not meal:
        raise HTTPException(status_code=404, detail="Meal not found")
    return _db_meal_to_mealout(meal)
