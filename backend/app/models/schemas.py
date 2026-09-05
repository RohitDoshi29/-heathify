"""
Pydantic schemas shared across routers.

These mirror the response shape expected by the Flutter app's
`Meal`/`FoodItem` models (lib/models/meal.dart, lib/models/food_item.dart).
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class FoodItemOut(BaseModel):
    food_id: str
    name: str
    estimated_weight_g: float
    estimated_calories: float
    protein_g: float = 0.0
    carbs_g: float = 0.0
    fat_g: float = 0.0
    confidence: float = Field(ge=0.0, le=1.0)


class MealOut(BaseModel):
    id: str
    created_at: datetime
    image_url: Optional[str] = None
    items: List[FoodItemOut]
    confidence: float = Field(ge=0.0, le=1.0)
    calorie_range_low: float
    calorie_range_high: float
    confidence_band: str = "high"  # "high", "medium", "low"
    retry_recommended: bool = False
    retry_reason: Optional[str] = None


class CorrectionIn(BaseModel):
    meal_item_id: str
    corrected_weight_g: float
    correction_type: str = "weight_adjustment"


class HealthOut(BaseModel):
    status: str
    version: str
    database: str = "connected"
    environment: str = "production"
    engines: dict[str, str] = Field(default_factory=dict)
