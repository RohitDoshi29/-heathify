"""
POST /api/analyze - Complete 7-Engine Multi-Stage AI Pipeline:

  Image -> [Engine 1: YOLO Segmentation] (BBoxes + Masks + Food Classes)
        -> [Engine 2: Depth Model] (3D Relief Height & Voxel Volume)
        -> [Engine 3: Portion Model] (Density Priors & 2D/3D Geometry)
        -> [Engine 4: Gemini 1.5 Flash] (Fast Food & Context Understanding)
        -> [Engine 5: Nutrition DB] (Authoritative USDA & Curated Nutrition)
        -> [Engine 6: Gemini 2.5 Pro / Claude Sonnet 4.6] (Difficult-Case Deep Verifier)
        -> [Engine 7: Custom Fusion Engine] (MAD Outlier Rejection, Uncertainty & Calibration)
        -> DB Persistence (Meal + MealItems)
        -> API Response.
"""
import logging
import time
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, UploadFile, File, Form, Depends
from sqlalchemy.orm import Session

from app.models.database import get_db, Meal as DBMeal, MealItem as DBMealItem, Food as DBFood
from app.models.schemas import MealOut, FoodItemOut
from app.services.detection_service import detection_service
from app.services.segmentation_service import segmentation_service
from app.services.depth_service import depth_service
from app.services.portion_service import portion_service
from app.services.engine4_flash_context import engine4_flash
from app.services.nutrition_service import lookup_nutrition, calculate_calories
from app.services.engine6_expert_verifier import engine6_expert
from app.services.fusion_service import WeightEstimate, fuse_weight_estimates, confidence_band
from app.services.reference_service import reference_service

logger = logging.getLogger("app.analyze")
router = APIRouter()

LATENCY_BUDGET_SECONDS = 5.0


@router.post("/analyze", response_model=MealOut)
async def analyze_meal(
    image: UploadFile = File(...),
    reference_mode: bool = Form(False),
    db: Session = Depends(get_db),
):
    t_start = time.perf_counter()
    image_bytes = await image.read()

    # Reject empty payloads
    if len(image_bytes) == 0:
        return MealOut(
            id=str(uuid.uuid4()),
            created_at=datetime.now(timezone.utc),
            items=[],
            confidence=0.0,
            calorie_range_low=0.0,
            calorie_range_high=0.0,
        )

    timings = {}

    # Optional Fiducial Reference Scale
    t0 = time.perf_counter()
    ref_scale = reference_service.detect_reference_scale(image_bytes, reference_mode=reference_mode)
    timings["ref_scale_ms"] = round((time.perf_counter() - t0) * 1000, 2)

    # 1. Engine 1: YOLO Segmentation (BBoxes, Classes, Foreground Masks)
    t0 = time.perf_counter()
    detected_items = detection_service.detect(image_bytes)
    initial_labels = [item.food_id for item in detected_items]
    timings["engine_1_yolo_seg_ms"] = round((time.perf_counter() - t0) * 1000, 2)

    # 2. Engine 4: Gemini 1.5 Flash (Global Food & Context Understanding)
    t0 = time.perf_counter()
    flash_context = engine4_flash.analyze_context(image_bytes, initial_detections=initial_labels)
    timings["engine_4_flash_context_ms"] = round((time.perf_counter() - t0) * 1000, 2)

    meal_id = str(uuid.uuid4())
    items_out: list[FoodItemOut] = []
    db_items: list[DBMealItem] = []
    weighted_confidences: list[float] = []

    timings["engine_2_depth_ms"] = 0.0
    timings["engine_3_portion_ms"] = 0.0
    timings["engine_5_nutrition_db_ms"] = 0.0
    timings["engine_6_expert_verifier_ms"] = 0.0
    timings["engine_7_custom_fusion_ms"] = 0.0

    for item in detected_items:
        # Engine 1 Segmentation Mask
        seg = segmentation_service.segment(image_bytes, item.bbox)

        # Engine 2: Depth Model (3D Height & Voxel Volume)
        t0 = time.perf_counter()
        depth_est = depth_service.estimate_depth_and_volume(
            image_bytes=image_bytes,
            bbox=item.bbox,
            pixel_area=seg.pixel_area,
            food_id=item.food_id,
            reference_mode=ref_scale.is_detected,
        )
        timings["engine_2_depth_ms"] += (time.perf_counter() - t0) * 1000

        # Engine 3: Portion Model (Physical Density Priors)
        t0 = time.perf_counter()
        portion_est = portion_service.estimate_weight(
            food_id=item.food_id,
            pixel_area=seg.pixel_area,
            reference_mode=ref_scale.is_detected,
        )
        timings["engine_3_portion_ms"] += (time.perf_counter() - t0) * 1000

        # Discrepancy check between depth volume and portion prior
        discrepancy_pct = (
            abs(depth_est.estimated_weight_g - portion_est.estimated_weight_g)
            / max(1.0, portion_est.estimated_weight_g)
            * 100.0
        )

        active_food_id = item.food_id
        active_confidence = item.confidence
        density_factor = 1.0

        # Engine 6: Gemini 2.5 Pro / Claude Sonnet 4.6 (Selective Escalation for Difficult Cases)
        if engine6_expert.should_escalate_to_expert(
            initial_confidence=item.confidence,
            candidate_label=item.food_id,
            flash_context_ambiguous=flash_context.is_ambiguous,
            portion_vs_depth_discrepancy_pct=discrepancy_pct,
        ):
            t0 = time.perf_counter()
            expert_res = engine6_expert.verify_difficult_case(
                image_bytes=image_bytes,
                candidate_label=item.food_id,
                initial_confidence=item.confidence,
                context_cues=flash_context.preparation_cues,
                bbox=item.bbox,
            )
            active_food_id = expert_res.verified_food_id
            active_confidence = expert_res.confidence
            density_factor = expert_res.density_adjustment_factor
            timings["engine_6_expert_verifier_ms"] += (time.perf_counter() - t0) * 1000

        # Engine 7: Custom Fusion Engine (MAD Outlier Rejection & Weight Consensus)
        t0 = time.perf_counter()
        adjusted_portion_w = portion_est.estimated_weight_g * density_factor
        adjusted_depth_w = depth_est.estimated_weight_g * density_factor

        estimates = [
            WeightEstimate(
                source="portion_model",
                grams=round(adjusted_portion_w, 1),
                confidence=portion_est.confidence,
            ),
            WeightEstimate(
                source="depth",
                grams=round(adjusted_depth_w, 1),
                confidence=depth_est.confidence,
            ),
        ]
        if ref_scale.is_detected:
            density = portion_service.get_density(active_food_id) * density_factor
            calibrated_area_cm2 = seg.pixel_area * (ref_scale.cm_per_pixel ** 2)
            ref_weight = max(25.0, calibrated_area_cm2 * depth_est.mean_height_cm * density)
            estimates.append(
                WeightEstimate(
                    source="reference",
                    grams=round(ref_weight, 1),
                    confidence=ref_scale.confidence,
                )
            )

        fused_weight, fused_confidence = fuse_weight_estimates(estimates)
        timings["engine_7_custom_fusion_ms"] += (time.perf_counter() - t0) * 1000

        # Engine 5: Nutrition DB (Authoritative USDA & Curated Nutrition Facts)
        t0 = time.perf_counter()
        nutrition = lookup_nutrition(active_food_id, db=db)
        calories = calculate_calories(fused_weight, nutrition.calories_100g)
        timings["engine_5_nutrition_db_ms"] += (time.perf_counter() - t0) * 1000

        protein_g = round(nutrition.protein_100g * fused_weight / 100.0, 1)
        carbs_g = round(nutrition.carbs_100g * fused_weight / 100.0, 1)
        fat_g = round(nutrition.fat_100g * fused_weight / 100.0, 1)

        item_id = str(uuid.uuid4())

        # Ensure food exists in DB for foreign key constraint
        db_food = db.query(DBFood).filter(DBFood.id == nutrition.food_id).first()
        if not db_food:
            db_food = DBFood(id=nutrition.food_id, name=nutrition.name)
            db.add(db_food)
            db.flush()

        db_meal_item = DBMealItem(
            id=item_id,
            meal_id=meal_id,
            food_id=db_food.id,
            estimated_weight=round(fused_weight, 1),
            estimated_calories=round(calories, 1),
            confidence=round(fused_confidence, 2),
        )
        db_items.append(db_meal_item)

        items_out.append(
            FoodItemOut(
                food_id=item_id,
                name=nutrition.name,
                estimated_weight_g=round(fused_weight, 1),
                estimated_calories=round(calories, 1),
                protein_g=protein_g,
                carbs_g=carbs_g,
                fat_g=fat_g,
                confidence=round(fused_confidence, 2),
            )
        )
        weighted_confidences.append(fused_confidence)

    # Round loop timings
    for k in [
        "engine_2_depth_ms",
        "engine_3_portion_ms",
        "engine_5_nutrition_db_ms",
        "engine_6_expert_verifier_ms",
        "engine_7_custom_fusion_ms",
    ]:
        timings[k] = round(timings[k], 2)

    overall_confidence = (
        sum(weighted_confidences) / len(weighted_confidences) if weighted_confidences else 0.0
    )
    total_calories = sum(i.estimated_calories for i in items_out)
    band = confidence_band(overall_confidence)
    retry_recommended = (band == "low")
    retry_reason = (
        "Low confidence detected across multi-engine consensus. "
        "Enabling Reference Mode or retaking a clear top-down photo is recommended."
        if retry_recommended else None
    )

    # Persist Meal and MealItems into DB
    try:
        db_meal = DBMeal(
            id=meal_id,
            total_calories=round(total_calories, 1),
            confidence=round(overall_confidence, 2),
        )
        db.add(db_meal)
        for dbi in db_items:
            db.add(dbi)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning(f"[Analyze] DB persistence error: {e}")

    total_latency = time.perf_counter() - t_start
    timings["total_pipeline_ms"] = round(total_latency * 1000, 2)

    logger.info(f"[Analyze 7-Engine] Finished in {timings['total_pipeline_ms']}ms | Engine timings: {timings}")

    return MealOut(
        id=meal_id,
        created_at=datetime.now(timezone.utc),
        items=items_out,
        confidence=round(overall_confidence, 2),
        calorie_range_low=round(total_calories * 0.9, 1),
        calorie_range_high=round(total_calories * 1.1, 1),
        confidence_band=band,
        retry_recommended=retry_recommended,
        retry_reason=retry_reason,
    )
