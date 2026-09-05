"""
Engine 6 - Multi-Engine Fusion & Consensus Judge.

Combines independent weight estimates from Portion Model (Engine 4), Monocular Depth (Engine 3),
Reference Fiducial Scale, and VLM Verifier. Rejects statistical outliers using Median Absolute Deviation (MAD),
calculates inter-engine consensus, and produces a calibrated confidence-weighted final estimate.
"""
from dataclasses import dataclass
from statistics import median
from typing import List, Tuple


@dataclass
class WeightEstimate:
    source: str          # e.g. "portion_model", "depth", "reference", "vlm"
    grams: float
    confidence: float    # 0.0 - 1.0


def _compute_mad(values: List[float], med: float) -> float:
    """Calculates Median Absolute Deviation (MAD)."""
    return median(abs(v - med) for v in values)


def fuse_weight_estimates(
    estimates: List[WeightEstimate],
    z_score_threshold: float = 2.5,
) -> Tuple[float, float]:
    """Combines multi-engine estimates using MAD outlier rejection and consensus weighting.

    Returns:
        (fused_weight_grams, fused_confidence)
    """
    if not estimates:
        raise ValueError("fuse_weight_estimates requires at least one estimate")

    if len(estimates) == 1:
        e = estimates[0]
        return round(e.grams, 1), round(e.confidence, 2)

    values = [e.grams for e in estimates]
    med = median(values)
    mad = _compute_mad(values, med)

    kept: List[WeightEstimate] = []

    if mad == 0.0 or len(estimates) <= 2:
        # Fallback to ratio from median when variance is zero or small sample
        for e in estimates:
            ratio = (e.grams / med) if med > 0 else 1.0
            if 0.40 <= ratio <= 2.50:
                kept.append(e)
    else:
        # Modified Z-Score based on MAD: M_i = 0.6745 * |x_i - med| / MAD
        for e in estimates:
            modified_z = (0.6745 * abs(e.grams - med)) / mad
            if modified_z <= z_score_threshold:
                kept.append(e)

    # Fallback to all if all were rejected
    if not kept:
        kept = estimates

    # Confidence-weighted average
    total_weight_conf = sum(e.confidence for e in kept)
    if total_weight_conf == 0.0:
        fused_weight = sum(e.grams for e in kept) / len(kept)
        base_confidence = 0.50
    else:
        fused_weight = sum(e.grams * e.confidence for e in kept) / total_weight_conf
        base_confidence = total_weight_conf / len(kept)

    # Inter-engine consensus scoring:
    # Measure coefficient of variation among kept estimates: CV = std_dev / mean
    mean_val = sum(e.grams for e in kept) / len(kept)
    if len(kept) > 1 and mean_val > 0:
        variance = sum((e.grams - mean_val) ** 2 for e in kept) / len(kept)
        std_dev = variance ** 0.5
        cv = std_dev / mean_val  # relative dispersion (0.0 = perfect consensus)
        
        # High consensus (cv < 0.08) boosts confidence up to +0.06
        # Divergence (cv > 0.25) penalizes confidence up to -0.15
        if cv < 0.08:
            consensus_mod = 0.05
        elif cv > 0.25:
            consensus_mod = -0.12
        else:
            consensus_mod = 0.0

        # Outlier rejection penalty
        outlier_penalty = 0.10 if len(kept) < len(estimates) else 0.0
        final_confidence = max(0.10, min(0.98, base_confidence + consensus_mod - outlier_penalty))
    else:
        final_confidence = base_confidence

    return round(fused_weight, 1), round(final_confidence, 2)


def confidence_band(confidence: float) -> str:
    """Automatic retry policy bands (plan section 8):
    >90% high (auto-accept), 75-90% medium (accept + easy adjustment), <75% low (retry prompt)."""
    if confidence >= 0.90:
        return "high"
    if confidence >= 0.75:
        return "medium"
    return "low"
