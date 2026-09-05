"""
Engine 1 - Food Detection, Classification & VLM Portion Extraction.

Detects food items in an image using:
  1. Gemini 2.5 Flash Multimodal Vision (Primary Engine).
     - Identifies food categories & bounding boxes.
     - Extracts visual portion estimates (grams) directly from visual volume cues.
  2. Retry guard with backoff on transient network issues.
  3. Explicit detection_method reporting ('vlm' vs 'heuristic_fallback').
"""
import base64
import io
import json
import logging
import os
import time
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import List, Tuple, Optional
from PIL import Image, ImageStat

logger = logging.getLogger("app.detection_service")


@dataclass
class DetectedItem:
    food_id: str
    label: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    area_ratio: float  # Estimated ratio of image plate occupied
    vlm_weight_g: Optional[float] = None
    detection_method: str = "vlm"  # "vlm" or "heuristic_fallback"
    model_used: str = "gemini-2.5-flash"


class FoodDetectionService:
    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key
        self._check_api_key_on_init()

    @property
    def api_key(self) -> Optional[str]:
        return self._api_key or os.getenv("GEMINI_API_KEY")

    def _check_api_key_on_init(self):
        key = self.api_key
        if not key or len(key.strip()) < 5:
            logger.warning(
                "⚠️ [DetectionService] GEMINI_API_KEY is not configured! "
                "The system will fall back to heuristic color-based estimation, and food identification accuracy will be poor. "
                "Please configure GEMINI_API_KEY in backend/.env"
            )
        else:
            logger.info("✅ [DetectionService] GEMINI_API_KEY is active. Primary VLM vision pipeline enabled.")

    def _detect_via_gemini_flash(self, image_bytes: bytes, width: int, height: int) -> Optional[List[DetectedItem]]:
        key = self.api_key
        if not key or len(key.strip()) < 5:
            logger.warning("[Detection] GEMINI_API_KEY not set — using placeholder color fallback, accuracy will be poor.")
            return None

        # Retry guard: up to 2 attempts with short backoff
        for attempt in range(2):
            try:
                b64_image = base64.b64encode(image_bytes).decode("utf-8")
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key.strip()}"

                prompt = (
                    "You are a computer-vision dietary nutritionist. Analyze this food photo carefully.\n"
                    "1. Identify EVERY distinct food item visible (e.g. boiled_egg, fried_egg, egg_omelette, steamed_rice, "
                    "dal_tadka, roti_chapati, chicken_biryani, salad_greens, paneer_butter_masala, pasta_tomato, apple, banana, etc.).\n"
                    "2. For each food item, provide:\n"
                    "   - food_id: standard snake_case ID\n"
                    "   - label: clean display title\n"
                    "   - confidence: float (0.50 to 1.00)\n"
                    "   - bbox: bounding box [ymin, xmin, ymax, xmax] normalized from 0 to 1000\n"
                    "   - area_ratio: estimated fraction of plate/frame occupied (0.05 to 0.85)\n"
                    "   - estimated_weight_g: visual estimate in grams based on plate proportion and dish density (e.g. 1 egg = ~55g, 1 bowl rice = ~180g, 1 roti = ~40g)\n\n"
                    "Respond strictly with valid JSON only in this exact format:\n"
                    "{\"items\": [{\"food_id\": \"boiled_egg\", \"label\": \"Boiled Egg\", \"confidence\": 0.96, \"bbox\": [100, 100, 800, 800], \"area_ratio\": 0.35, \"estimated_weight_g\": 55.0}]}"
                )

                payload = {
                    "contents": [{
                        "parts": [
                            {"text": prompt},
                            {"inline_data": {"mime_type": "image/jpeg", "data": b64_image}}
                        ]
                    }],
                    "generationConfig": {
                        "response_mime_type": "application/json",
                        "temperature": 0.1,
                    }
                }

                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )

                with urllib.request.urlopen(req, timeout=9.0) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    text_content = resp_data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    if "```json" in text_content:
                        text_content = text_content.split("```json")[1].split("```")[0].strip()
                    data = json.loads(text_content)

                    items = data.get("items", [])
                    if not items:
                        logger.warning("[Detection] Gemini 2.5 Flash returned an empty item list.")
                        return None

                    results = []
                    for it in items:
                        raw_bbox = it.get("bbox", [100, 100, 900, 900])
                        y1 = int(raw_bbox[0] * height / 1000)
                        x1 = int(raw_bbox[1] * width / 1000)
                        y2 = int(raw_bbox[2] * height / 1000)
                        x2 = int(raw_bbox[3] * width / 1000)

                        x1, x2 = min(x1, x2), max(x1, x2)
                        y1, y2 = min(y1, y2), max(y1, y2)
                        if x2 <= x1:
                            x2 = x1 + max(10, width // 4)
                        if y2 <= y1:
                            y2 = y1 + max(10, height // 4)

                        vlm_weight = float(it.get("estimated_weight_g", 150.0))

                        results.append(
                            DetectedItem(
                                food_id=it.get("food_id", "food_item").lower().replace(" ", "_"),
                                label=it.get("label", "Food Item"),
                                confidence=float(it.get("confidence", 0.94)),
                                bbox=(x1, y1, x2, y2),
                                area_ratio=float(it.get("area_ratio", 0.35)),
                                vlm_weight_g=vlm_weight,
                                detection_method="vlm",
                                model_used="gemini-2.5-flash",
                            )
                        )

                    logger.info(f"✨ [Engine 1 Detection] Gemini 2.5 Flash SUCCESS: {[r.food_id for r in results]}")
                    return results

            except urllib.error.HTTPError as e:
                err_msg = e.read().decode("utf-8") if hasattr(e, "read") else str(e)
                logger.warning(f"[Detection Attempt {attempt+1}/2] Gemini HTTP Error {e.code}: {err_msg[:120]}")
                if attempt == 0:
                    time.sleep(0.5)
            except Exception as e:
                logger.warning(f"[Detection Attempt {attempt+1}/2] Gemini API error: {e}")
                if attempt == 0:
                    time.sleep(0.5)

        logger.warning("[Detection] All Gemini VLM attempts failed. Falling back to heuristic mode.")
        return None

    def detect(self, image_bytes: bytes) -> List[DetectedItem]:
        """Runs visual detection on image bytes, returning detected foods and bboxes."""
        if not image_bytes:
            return []

        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            width, height = image.size
        except Exception:
            width, height = 400, 400
            image = None

        # 1. Primary Path: Gemini 2.5 Flash Multimodal Vision
        cloud_results = self._detect_via_gemini_flash(image_bytes, width, height)
        if cloud_results:
            return cloud_results

        # 2. Transparent Fallback (Low-accuracy Heuristics)
        logger.warning("⚠️ [Detection] USING FALLBACK HEURISTICS (Accuracy will be limited).")

        if image is None:
            return [
                DetectedItem(
                    food_id="boiled_egg",
                    label="Boiled Egg",
                    confidence=0.50,
                    bbox=(int(0.1 * width), int(0.1 * height), int(0.9 * width), int(0.9 * height)),
                    area_ratio=0.35,
                    vlm_weight_g=60.0,
                    detection_method="heuristic_fallback",
                    model_used="color_heuristic_v1",
                )
            ]

        stat = ImageStat.Stat(image)
        r, g, b = stat.mean[:3]

        tl_box = (0, 0, width // 2, height // 2)
        tr_box = (width // 2, 0, width, height // 2)
        bot_box = (0, height // 2, width, height)

        if r > 180 and g > 175 and b > 160:
            return [
                DetectedItem(
                    food_id="boiled_egg",
                    label="Boiled Egg (Whole)",
                    confidence=0.55,
                    bbox=(int(0.2 * width), int(0.2 * height), int(0.8 * width), int(0.8 * height)),
                    area_ratio=0.32,
                    vlm_weight_g=55.0,
                    detection_method="heuristic_fallback",
                    model_used="color_heuristic_v1",
                )
            ]

        if r > 150 and g > 150 and b > 140:
            return [
                DetectedItem(
                    food_id="steamed_rice",
                    label="Steamed White Rice",
                    confidence=0.55,
                    bbox=tl_box,
                    area_ratio=0.38,
                    vlm_weight_g=180.0,
                    detection_method="heuristic_fallback",
                    model_used="color_heuristic_v1",
                ),
                DetectedItem(
                    food_id="dal_tadka",
                    label="Yellow Dal Tadka",
                    confidence=0.50,
                    bbox=tr_box,
                    area_ratio=0.26,
                    vlm_weight_g=150.0,
                    detection_method="heuristic_fallback",
                    model_used="color_heuristic_v1",
                ),
            ]

        if r > 130 and r > g and r > b:
            return [
                DetectedItem(
                    food_id="paneer_butter_masala",
                    label="Paneer Butter Masala",
                    confidence=0.52,
                    bbox=tl_box,
                    area_ratio=0.36,
                    vlm_weight_g=200.0,
                    detection_method="heuristic_fallback",
                    model_used="color_heuristic_v1",
                ),
                DetectedItem(
                    food_id="roti_chapati",
                    label="Whole Wheat Roti/Chapati",
                    confidence=0.50,
                    bbox=bot_box,
                    area_ratio=0.30,
                    vlm_weight_g=70.0,
                    detection_method="heuristic_fallback",
                    model_used="color_heuristic_v1",
                ),
            ]

        if g > r and g > b:
            return [
                DetectedItem(
                    food_id="salad_greens",
                    label="Mixed Fresh Salad Greens",
                    confidence=0.52,
                    bbox=tl_box,
                    area_ratio=0.32,
                    vlm_weight_g=120.0,
                    detection_method="heuristic_fallback",
                    model_used="color_heuristic_v1",
                )
            ]

        return [
            DetectedItem(
                food_id="boiled_egg",
                label="Boiled Egg",
                confidence=0.50,
                bbox=(int(0.15 * width), int(0.15 * height), int(0.85 * width), int(0.85 * height)),
                area_ratio=0.35,
                vlm_weight_g=55.0,
                detection_method="heuristic_fallback",
                model_used="color_heuristic_v1",
            )
        ]


# Singleton instance
detection_service = FoodDetectionService()
