"""
POST /api/correction - record a user-corrected food or quantity.

Persists to the `FEEDBACK` table so corrections become reusable training data.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models.database import get_db, Feedback, MealItem, Meal
from app.models.schemas import CorrectionIn
from app.services.nutrition_service import calculate_calories

router = APIRouter()


@router.post("/correction")
def submit_correction(correction: CorrectionIn, db: Session = Depends(get_db)):
    # 1. Lookup the referenced meal item
    meal_item = db.query(MealItem).filter(MealItem.id == correction.meal_item_id).first()
    predicted_weight = meal_item.estimated_weight if meal_item else 0.0

    # 2. Insert feedback record
    fb = Feedback(
        meal_item_id=correction.meal_item_id,
        predicted_weight=predicted_weight,
        corrected_weight=correction.corrected_weight_g,
        correction_type=correction.correction_type,
    )
    db.add(fb)

    # 3. Update the meal_item row and parent meal total calories if found
    if meal_item:
        meal_item.estimated_weight = correction.corrected_weight_g
        if meal_item.food and meal_item.food.nutrition:
            new_cal = calculate_calories(
                correction.corrected_weight_g, meal_item.food.nutrition.calories_100g
            )
            meal_item.estimated_calories = round(new_cal, 1)

        # Update parent meal total calories
        meal = db.query(Meal).filter(Meal.id == meal_item.meal_id).first()
        if meal:
            total_cal = sum(it.estimated_calories for it in meal.items)
            meal.total_calories = round(total_cal, 1)

    db.commit()

    return {
        "status": "recorded",
        "meal_item_id": correction.meal_item_id,
        "predicted_weight_g": predicted_weight,
        "corrected_weight_g": correction.corrected_weight_g,
    }
