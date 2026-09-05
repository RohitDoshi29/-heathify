import io
import pytest
from PIL import Image
from app.services.segmentation_service import segmentation_service
from app.services.portion_service import portion_service

def test_segmentation_service():
    img = Image.new("RGB", (300, 300), color=(240, 240, 240))
    # Draw a colored region simulating food
    for x in range(50, 200):
        for y in range(50, 200):
            img.putpixel((x, y), (180, 100, 50))

    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    img_bytes = buf.getvalue()

    bbox = (40, 40, 210, 210)
    seg_result = segmentation_service.segment(img_bytes, bbox)

    assert seg_result.pixel_area > 0
    assert 0.40 <= seg_result.foreground_ratio <= 0.95
    assert len(seg_result.contour_points) >= 4
    assert seg_result.confidence > 0.5

def test_portion_service_densities():
    # Rice vs Bread vs Salad
    rice_est = portion_service.estimate_weight("steamed_rice", pixel_area=40000, image_total_pixels=160000)
    salad_est = portion_service.estimate_weight("salad_greens", pixel_area=40000, image_total_pixels=160000)
    roti_est = portion_service.estimate_weight("roti_chapati", pixel_area=40000, image_total_pixels=160000)

    assert rice_est.estimated_weight_g > salad_est.estimated_weight_g
    assert roti_est.estimated_weight_g < rice_est.estimated_weight_g
    assert rice_est.density_g_per_cm3 == 0.85
    assert salad_est.density_g_per_cm3 == 0.35
    assert roti_est.density_g_per_cm3 == 0.55

def test_portion_service_reference_mode():
    est_normal = portion_service.estimate_weight("steamed_rice", pixel_area=45000, reference_mode=False)
    est_ref = portion_service.estimate_weight("steamed_rice", pixel_area=45000, reference_mode=True)

    assert est_ref.confidence >= est_normal.confidence

