"""
Engine 4 - Portion & Weight Estimation Model.

Converts segmented pixel area, relative plate occupancy, and physical food-density
priors into accurate weight estimates in grams.
"""
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class PortionEstimate:
    food_id: str
    estimated_weight_g: float
    confidence: float
    method: str
    density_g_per_cm3: float


# Physical density priors (g / cm³) and typical plate serving characteristics
DENSITY_PRIORS: Dict[str, float] = {
    # Grains & Rice Dishes
    "steamed_rice": 0.85,
    "brown_rice": 0.82,
    "chicken_biryani": 0.88,
    "veg_biryani": 0.84,
    "poha": 0.65,
    "upma": 0.75,
    # Legumes & Dals
    "dal_tadka": 1.05,
    "dal_makhani": 1.10,
    "chana_masala": 0.98,
    "rajma_curry": 1.02,
    "sambar": 1.02,
    # Curries & Gravies
    "paneer_butter_masala": 1.08,
    "palak_paneer": 1.04,
    "butter_chicken": 1.12,
    # Vegetables
    "aloo_gobi": 0.78,
    "bhindi_masala": 0.72,
    "salad_greens": 0.35,
    "cucumber": 0.70,
    "tomato": 0.80,
    # Breads (flat surface area scaling)
    "roti_chapati": 0.55,
    "naan": 0.60,
    "paratha": 0.68,
    "masala_dosa": 0.50,
    # Proteins & Eggs
    "tandoori_chicken": 1.05,
    "grilled_chicken_breast": 1.10,
    "boiled_egg": 1.08,
    "egg_omelette": 0.75,
    "idli": 0.72,
    # Snacks & Desserts
    "samosa": 0.68,
    "gulab_jamun": 1.15,
    "french_fries": 0.58,
    "pizza_slice": 0.75,
    "pasta_tomato": 0.90,
    # Fruits & Dairy
    "apple": 0.82,
    "banana": 0.85,
    "orange": 0.84,
    "plain_yogurt_curd": 1.05,
}

# Category fallback densities
CATEGORY_DEFAULTS: Dict[str, float] = {
    "grains": 0.85,
    "legumes": 1.02,
    "curries": 1.06,
    "vegetables": 0.75,
    "breads": 0.58,
    "poultry": 1.08,
    "eggs": 0.95,
    "breakfast": 0.70,
    "snacks": 0.65,
    "fruits": 0.82,
    "dairy": 1.05,
}


class PortionEstimationService:
    def __init__(self):
        # Baseline reference: standard 25cm dinner plate occupies ~50-60% of frame
        self.standard_plate_area_px = 350.0 * 350.0  # reference frame pixels

    def get_density(self, food_id: str, category: Optional[str] = None) -> float:
        """Looks up physical density prior (g/cm³) for food class."""
        clean_id = food_id.lower().strip().replace(" ", "_")
        if clean_id in DENSITY_PRIORS:
            return DENSITY_PRIORS[clean_id]
        if category and category.lower() in CATEGORY_DEFAULTS:
            return CATEGORY_DEFAULTS[category.lower()]
        return 0.85  # default food density

    def estimate_weight(
        self,
        food_id: str,
        pixel_area: int,
        image_total_pixels: int = 400 * 400,
        reference_mode: bool = False,
        category: Optional[str] = None,
    ) -> PortionEstimate:
        """Estimates portion weight in grams from segmented pixel area and density priors."""
        density = self.get_density(food_id, category)

        # Normalize pixel area relative to frame
        img_pixels = max(10000, image_total_pixels)
        area_ratio = pixel_area / img_pixels

        # Area-to-volume power-law exponent (V ~ A^(1.35) for 3D mounded food portions)
        # Breads/flatbreads follow linear area scaling (V ~ A^(1.05))
        is_flatbread = any(k in food_id for k in ["roti", "chapati", "naan", "paratha", "dosa", "pizza"])
        
        if is_flatbread:
            # Typical single flatbread is ~50-120g
            volume_factor = (area_ratio / 0.25) ** 1.05
            base_mass = 75.0 * volume_factor
        else:
            # Mounded items (rice, dal, curries, meats)
            volume_factor = (area_ratio / 0.30) ** 1.30
            base_mass = 180.0 * volume_factor * (density / 0.85)

        # Apply reference mode precision multiplier if present
        confidence = 0.84 if not reference_mode else 0.92

        # Sanity clamping for standard plate portions (20g to 600g)
        estimated_grams = max(25.0, min(650.0, base_mass))

        return PortionEstimate(
            food_id=food_id,
            estimated_weight_g=round(estimated_grams, 1),
            confidence=round(confidence, 2),
            method="density_scaled_segmentation_v2",
            density_g_per_cm3=density,
        )


# Singleton instance
portion_service = PortionEstimationService()

