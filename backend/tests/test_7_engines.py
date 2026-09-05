import io
from fastapi.testclient import TestClient
from app.main import app
from app.services.engine4_flash_context import engine4_flash
from app.services.engine6_expert_verifier import engine6_expert

client = TestClient(app)


def test_engine4_flash_context():
    context = engine4_flash.analyze_context(b"dummy_bytes", initial_detections=["steamed_rice", "dal_tadka"])
    assert context.cuisine_style == "indian"
    assert "steamed" in context.preparation_cues
    assert context.confidence > 0.8


def test_engine6_expert_verifier_trigger_and_resolution():
    # Should escalate on low confidence or complex dish
    assert engine6_expert.should_escalate_to_expert(0.60, "unknown_curry", False) is True
    assert engine6_expert.should_escalate_to_expert(0.95, "paneer_butter_masala", False) is True

    # Verification result
    result = engine6_expert.verify_difficult_case(b"dummy_bytes", "paneer_butter_masala", 0.70)
    assert result.verified_food_id == "paneer_butter_masala"
    assert result.has_hidden_fats is True
    assert result.density_adjustment_factor >= 1.0


def test_7_engine_pipeline_end_to_end():
    dummy_image = io.BytesIO(b"fake_jpg_content_1234567890")
    response = client.post(
        "/api/analyze",
        files={"image": ("meal.jpg", dummy_image, "image/jpeg")},
        data={"reference_mode": "false"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) > 0
    assert data["confidence"] > 0.0
    assert data["confidence_band"] in ["high", "medium", "low"]
    assert "calorie_range_low" in data
    assert "calorie_range_high" in data


def test_health_7_engines():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "engines" in data
    assert len(data["engines"]) == 7
    assert "engine_1_yolo_segmentation" in data["engines"]
    assert "engine_2_depth_3d" in data["engines"]
    assert "engine_3_portion_model" in data["engines"]
    assert "engine_4_gemini_flash_context" in data["engines"]
    assert "engine_5_nutrition_db" in data["engines"]
    assert "engine_6_expert_verifier" in data["engines"]
    assert "engine_7_custom_fusion" in data["engines"]

