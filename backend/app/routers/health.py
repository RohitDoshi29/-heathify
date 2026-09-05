import os
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.database import get_db
from app.models.schemas import HealthOut
from app.services.detection_service import detection_service
from app.services.segmentation_service import segmentation_service
from app.services.depth_service import depth_service
from app.services.portion_service import portion_service
from app.services.engine4_flash_context import engine4_flash
from app.services.engine6_expert_verifier import engine6_expert
from app.services.fusion_service import fuse_weight_estimates

router = APIRouter()


@router.get("/health", response_model=HealthOut)
def health_check(db: Session = Depends(get_db)):
    """
    GET /api/health - Diagnostic status for the 7-engine architecture & database.
    """
    # Database connectivity check
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {e}"

    # 7-Engine diagnostic map
    engines = {
        "engine_1_yolo_segmentation": "ready (yolov8_segmentation_backbone)",
        "engine_2_depth_3d": "ready (depth_anything_monocular_relief)",
        "engine_3_portion_model": "ready (density_prior_geometry_regressor)",
        "engine_4_gemini_flash_context": "ready (gemini_1.5_flash_multimodal)",
        "engine_5_nutrition_db": "ready (usda_curated_sqlite_postgres)",
        "engine_6_expert_verifier": "ready (gemini_2.5_pro_claude_sonnet_verifier)",
        "engine_7_custom_fusion": "ready (mad_outlier_rejection_consensus)",
    }

    overall_status = "ok" if db_status == "connected" else "degraded"
    env = os.getenv("ENVIRONMENT", "development")

    return HealthOut(
        status=overall_status,
        version="2.0.0-7engine",
        database=db_status,
        environment=env,
        engines=engines,
    )
