"""
Portion Model Evaluation Script.

Evaluates portion estimation accuracy against ground-truth weighed portion samples
and logs MAE, RMSE, and MAPE metrics to backend/data/eval/portion_model_eval.md.
"""
import csv
import math
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from app.services.portion_service import portion_service


def run_portion_evaluation() -> dict:
    csv_path = backend_root / "data" / "portion_training_data.csv"
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Evaluation dataset not found at {csv_path}")

    total_image_pixels = 400 * 400
    samples = []
    errors = []
    pct_errors = []
    sq_errors = []
    category_metrics = defaultdict(lambda: {"errors": [], "pct_errors": []})

    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            food_id = row["food_id"].strip()
            category = row["category"].strip()
            area_ratio = float(row["area_ratio"])
            has_ref = row["has_reference"].strip().lower() == "true"
            actual_weight = float(row["actual_weight_g"])

            pixel_area = int(area_ratio * total_image_pixels)
            est = portion_service.estimate_weight(
                food_id=food_id,
                pixel_area=pixel_area,
                image_total_pixels=total_image_pixels,
                reference_mode=has_ref,
                category=category,
            )
            pred_weight = est.estimated_weight_g
            abs_err = abs(pred_weight - actual_weight)
            pct_err = (abs_err / actual_weight) * 100.0
            sq_err = (pred_weight - actual_weight) ** 2

            errors.append(abs_err)
            pct_errors.append(pct_err)
            sq_errors.append(sq_err)

            category_metrics[category]["errors"].append(abs_err)
            category_metrics[category]["pct_errors"].append(pct_err)

            samples.append({
                "sample_id": row["sample_id"],
                "food_id": food_id,
                "category": category,
                "actual": actual_weight,
                "predicted": pred_weight,
                "abs_error": round(abs_err, 1),
                "pct_error": round(pct_err, 1),
            })

    mae = sum(errors) / len(errors)
    mape = sum(pct_errors) / len(pct_errors)
    rmse = math.sqrt(sum(sq_errors) / len(sq_errors))

    # Generate Markdown Evaluation Report
    eval_dir = backend_root / "data" / "eval"
    os.makedirs(eval_dir, exist_ok=True)
    report_path = eval_dir / "portion_model_eval.md"

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    report_lines = [
        "# Portion Model Benchmark & Evaluation Report",
        f"**Generated:** {now_str}",
        f"**Samples Evaluated:** {len(samples)} plated portions across {len(category_metrics)} categories",
        "",
        "## Overall Accuracy Metrics",
        f"- **MAE (Mean Absolute Error):** {mae:.2f} g",
        f"- **MAPE (Mean Absolute Percentage Error):** {mape:.2f} %",
        f"- **RMSE (Root Mean Square Error):** {rmse:.2f} g",
        "",
        "## Category-Wise Breakdown",
        "| Category | Samples | MAE (g) | MAPE (%) |",
        "|---|---|---|---|",
    ]

    for cat, data in sorted(category_metrics.items()):
        c_mae = sum(data["errors"]) / len(data["errors"])
        c_mape = sum(data["pct_errors"]) / len(data["pct_errors"])
        report_lines.append(f"| {cat} | {len(data['errors'])} | {c_mae:.1f} g | {c_mape:.1f} % |")

    report_lines.extend([
        "",
        "## Sample Predictions Table",
        "| Sample | Food ID | Actual (g) | Predicted (g) | Error (g) | Error (%) |",
        "|---|---|---|---|---|---|",
    ])
    for s in samples[:15]:
        report_lines.append(f"| {s['sample_id']} | {s['food_id']} | {s['actual']} | {s['predicted']} | {s['abs_error']} | {s['pct_error']}% |")

    with open(report_path, mode="w", encoding="utf-8") as f:
        f.write("\n".join(report_lines) + "\n")

    print(f"[PortionEval] Evaluated {len(samples)} samples:")
    print(f"  MAE:  {mae:.2f} g")
    print(f"  MAPE: {mape:.2f} %")
    print(f"  RMSE: {rmse:.2f} g")
    print(f"  Report written to: {report_path}")

    return {
        "mae": round(mae, 2),
        "mape": round(mape, 2),
        "rmse": round(rmse, 2),
        "sample_count": len(samples),
    }


if __name__ == "__main__":
    run_portion_evaluation()

