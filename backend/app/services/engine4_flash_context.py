"""
Engine 4: Gemini 1.5 Flash - Food & Context Understanding Service.

Analyzes the full image context to identify:
  - Global meal setting (Indian thali, breakfast bowl, dinner plate, buffet)
  - Secondary food candidates and sauce styles
  - Plating and container context (bowl vs flat plate)
  - Preparation clues (fried, steamed, grilled, gravy)
Uses standard library urllib REST calls for zero-overhead cloud execution.
"""
import base64
import json
import logging
import os
import urllib.request
import urllib.error
from typing import List, Optional
from pydantic import BaseModel

logger = logging.getLogger("app.engine4_flash")


class ContextUnderstanding(BaseModel):
    cuisine_style: str = "general"
    meal_type: str = "plated_meal"
    plating_container: str = "standard_plate"
    identified_items: List[str] = []
    preparation_cues: List[str] = []
    confidence: float = 0.85
    is_ambiguous: bool = False


class Engine4FlashService:
    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key

    @property
    def api_key(self) -> Optional[str]:
        return self._api_key or os.getenv("GEMINI_API_KEY")

    def analyze_context(self, image_bytes: bytes, initial_detections: List[str] = None) -> ContextUnderstanding:
        """
        Fast multimodal context understanding via Gemini 1.5 Flash REST API with local fallback.
        """
        if not image_bytes or len(image_bytes) == 0:
            return ContextUnderstanding()

        key = self.api_key
        if key and len(key.strip()) > 5:
            try:
                b64_image = base64.b64encode(image_bytes).decode("utf-8")
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key.strip()}"
                
                payload = {
                    "contents": [{
                        "parts": [
                            {"text": (
                                "You are a culinary nutritionist. Analyze this meal image. "
                                "Respond strictly with valid JSON only in this format: "
                                "{\"cuisine_style\": \"indian/continental/etc\", \"meal_type\": \"lunch/dinner/snack\", "
                                "\"plating_container\": \"plate/bowl/thali\", \"identified_items\": [\"item1\", \"item2\"], "
                                "\"preparation_cues\": [\"steamed\", \"fried\", \"rich_gravy\"], "
                                "\"confidence\": 0.90, \"is_ambiguous\": false}"
                            )},
                            {
                                "inline_data": {
                                    "mime_type": "image/jpeg",
                                    "data": b64_image
                                }
                            }
                        ]
                    }],
                    "generationConfig": {
                        "response_mime_type": "application/json",
                        "temperature": 0.2,
                    }
                }
                
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                
                with urllib.request.urlopen(req, timeout=8.0) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
                    text_content = resp_data["candidates"][0]["content"]["parts"][0]["text"]
                    clean_json = text_content.strip()
                    if "```json" in clean_json:
                        clean_json = clean_json.split("```json")[1].split("```")[0].strip()
                    parsed = json.loads(clean_json)
                    logger.info(f"[Engine 4 Flash] Live Gemini Flash response: {parsed}")
                    return ContextUnderstanding(**parsed)
            except Exception as e:
                logger.warning(f"[Engine 4 Flash] Live Gemini REST call failed, using local context: {e}")

        # Local context understanding heuristics
        detections = initial_detections or []
        cuisine = "indian" if any(d in ["steamed_rice", "dal_tadka", "roti", "chicken_biryani", "paneer_butter_masala", "idli", "chole", "rajma"] for d in detections) else "general"

        preps = []
        if "steamed_rice" in detections or "idli" in detections:
            preps.append("steamed")
        if "paneer_butter_masala" in detections or "dal_makhani" in detections:
            preps.append("rich_dairy_gravy")
        if "dal_tadka" in detections or "rajma" in detections or "chole" in detections:
            preps.append("spiced_legume_curry")

        return ContextUnderstanding(
            cuisine_style=cuisine,
            meal_type="lunch_dinner" if "steamed_rice" in detections else "standard_meal",
            plating_container="thali_or_plate",
            identified_items=detections if detections else ["steamed_rice"],
            preparation_cues=preps if preps else ["standard_prep"],
            confidence=0.88,
            is_ambiguous=False,
        )


engine4_flash = Engine4FlashService()
