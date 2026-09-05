import os
import pytest
from pathlib import Path
from scripts.run_evaluation import run_full_evaluation, evaluate_detection_and_segmentation


def test_evaluate_detection_and_segmentation():
    metrics = evaluate_detection_and_segmentation()
    assert "detection_precision" in metrics
    assert "segmentation_miou" in metrics
    assert metrics["detection_precision"] > 0.85
    assert metrics["segmentation_miou"] > 0.80


def test_run_full_evaluation():
    results = run_full_evaluation()
    assert "weight_mae" in results
    assert "weight_mape" in results
    assert "calorie_mae" in results
    assert "report_file" in results
    assert os.path.exists(results["report_file"])
    assert results["weight_mae"] < 25.0
    assert results["weight_mape"] < 20.0
    assert results["calorie_mae"] < 35.0

