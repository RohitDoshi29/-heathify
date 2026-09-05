import io
import pytest
from PIL import Image
from app.services.depth_service import depth_service

def test_depth_estimation_synthetic():
    img = Image.new("RGB", (300, 300), color=(230, 230, 230))
    # Draw central shaded mound
    for x in range(50, 250):
        for y in range(50, 250):
            dist = ((x - 150) ** 2 + (y - 150) ** 2) ** 0.5
            val = max(50, int(255 - dist))
            img.putpixel((x, y), (val, val // 2, 40))

    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    img_bytes = buf.getvalue()

    bbox = (50, 50, 250, 250)
    pixel_area = 30000

    depth_est = depth_service.estimate_depth_and_volume(
        image_bytes=img_bytes,
        bbox=bbox,
        pixel_area=pixel_area,
        food_id="steamed_rice",
        reference_mode=False,
    )

    assert depth_est.estimated_volume_cm3 > 0
    assert depth_est.estimated_weight_g > 0
    assert depth_est.mean_height_cm > 0.5
    assert depth_est.confidence > 0.70

def test_flatbread_vs_mounded_depth_height():
    # Breads have lower relief height than mounded rice
    dummy_bbox = (0, 0, 200, 200)
    area = 25000

    bread_est = depth_service.estimate_depth_and_volume(
        image_bytes=b"",
        bbox=dummy_bbox,
        pixel_area=area,
        food_id="roti_chapati",
    )
    rice_est = depth_service.estimate_depth_and_volume(
        image_bytes=b"",
        bbox=dummy_bbox,
        pixel_area=area,
        food_id="steamed_rice",
    )

    assert bread_est.mean_height_cm < rice_est.mean_height_cm
    assert bread_est.max_height_cm < rice_est.max_height_cm

