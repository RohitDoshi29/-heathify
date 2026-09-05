import io
import pytest
from PIL import Image
from app.services.fusion_service import WeightEstimate, fuse_weight_estimates, confidence_band
from app.services.reference_service import reference_service
from app.services.vlm_service import vlm_service

def test_mad_outlier_rejection():
    # 3 engines agree around 180-190g, 1 engine outputs 950g wild outlier
    estimates = [
        WeightEstimate(source="portion_model", grams=180.0, confidence=0.85),
        WeightEstimate(source="depth", grams=188.0, confidence=0.80),
        WeightEstimate(source="reference", grams=184.0, confidence=0.90),
        WeightEstimate(source="faulty_sensor", grams=950.0, confidence=0.70),
    ]

    fused_weight, fused_conf = fuse_weight_estimates(estimates)

    # Outlier rejected -> fused weight is within 180-190 range
    assert 180.0 <= fused_weight <= 190.0
    assert fused_conf > 0.65

def test_all_agree_consensus():
    estimates = [
        WeightEstimate(source="portion_model", grams=200.0, confidence=0.88),
        WeightEstimate(source="depth", grams=204.0, confidence=0.85),
        WeightEstimate(source="reference", grams=201.0, confidence=0.92),
    ]

    fused_weight, fused_conf = fuse_weight_estimates(estimates)

    assert 200.0 <= fused_weight <= 203.0
    # High agreement boosts confidence
    assert fused_conf >= 0.85

def test_confidence_bands():
    assert confidence_band(0.95) == "high"
    assert confidence_band(0.82) == "medium"
    assert confidence_band(0.60) == "low"

def test_reference_service():
    img = Image.new("RGB", (400, 400), color=(240, 240, 240))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    img_bytes = buf.getvalue()

    # Default mode
    res_default = reference_service.detect_reference_scale(img_bytes, reference_mode=False)
    assert res_default.is_detected is False
    assert res_default.cm_per_pixel > 0

    # Reference mode active
    res_ref = reference_service.detect_reference_scale(img_bytes, reference_mode=True)
    assert res_ref.is_detected is True
    assert res_ref.confidence >= 0.85

def test_vlm_verifier_palak_paneer():
    # Green dominant image
    img = Image.new("RGB", (200, 200), color=(40, 160, 40))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    img_bytes = buf.getvalue()

    # Candidate was erroneously paneer butter masala (red gravy), VLM re-ranks to palak paneer
    vlm_res = vlm_service.verify_and_rerank(
        image_bytes=img_bytes,
        candidate_label="paneer_butter_masala",
        initial_confidence=0.75,
    )

    assert vlm_res.is_reranked is True
    assert vlm_res.verified_label == "palak_paneer"
    assert vlm_res.confidence >= 0.85

