# Comprehensive AI Calorie Estimation Evaluation Report
**Generated:** 2026-09-05 09:44:10 UTC
**Evaluated Samples:** 40 portion ground truth instances across 10 food categories

## Executive Summary
- **Weight Estimation MAE / MAPE**: **21.48 g** / **15.27%**
- **Calorie Estimation MAE / MAPE**: **27.83 kcal** / **15.27%**
- **Accuracy Thresholds**: **60.0%** of predictions within ±15% error; **75.0%** within ±20%
- **Confidence Calibration**: ECE = **0.2575**, Brier Score = **0.2939**

---

## 1. Detection & Segmentation Metrics
| Metric | Value | Status / Benchmark Target |
|---|---|---|
| **Detection Precision** | `94.2%` | Pass (>85%) |
| **Detection Recall** | `91.8%` | Pass (>85%) |
| **Detection F1-Score** | `93.0%` | Pass (>85%) |
| **Detection mAP@0.50** | `92.4%` | Pass (>80%) |
| **Segmentation Mean IoU** | `88.7%` | Pass (>80%) |
| **Dice Coefficient** | `93.6%` | Pass (>85%) |

---

## 2. Weight & Volume Estimation Metrics
| Metric | Measured Value | Standard Target |
|---|---|---|
| **Mean Absolute Error (MAE)** | **21.48 g** | < 25.0 g |
| **Mean Absolute Percentage Error (MAPE)** | **15.27%** | < 15.0% |
| **Root Mean Square Error (RMSE)** | **25.84 g** | < 30.0 g |
| **Mean Prediction Bias** | **+10.68 g** | ± 5.0 g |
| **Accuracy (<= 10% error)** | **47.5%** | - |
| **Accuracy (<= 15% error)** | **60.0%** | > 80.0% |
| **Accuracy (<= 20% error)** | **75.0%** | > 90.0% |

---

## 3. Calorie Estimation Metrics
| Metric | Measured Value | Target |
|---|---|---|
| **Calorie MAE** | **27.83 kcal** | < 35 kcal |
| **Calorie MAPE** | **15.27%** | < 15.0% |
| **Error Percentile P50 (Median)** | **20.2 kcal** | < 20 kcal |
| **Error Percentile P90** | **57.2 kcal** | < 50 kcal |
| **Error Percentile P95** | **64.4 kcal** | < 75 kcal |

---

## 4. Confidence Calibration & Reliability Diagram
**Expected Calibration Error (ECE):** `0.2575` | **Brier Score:** `0.2939`

| Confidence Bin Range | Sample Count | Avg Confidence | Empirical Accuracy (<=15% err) | Calibration Gap |
|---|---|---|---|---|
| 0.0 - 0.2 | 0 | 0.000 | 0.0% | 0.000 |
| 0.2 - 0.4 | 0 | 0.000 | 0.0% | 0.000 |
| 0.4 - 0.6 | 0 | 0.000 | 0.0% | 0.000 |
| 0.6 - 0.8 | 3 | 0.710 | 0.0% | 0.710 |
| 0.8 - 1.0 | 37 | 0.869 | 64.9% | 0.221 |

---

## 5. Continuous Learning & User Corrections
- **Total Stored User Corrections**: `15`
- **Average User Adjustment Delta**: `196.7 g`
- **Training Loop Status**: User corrections are persisted in the `FEEDBACK` table ready for periodic regression re-weighting.

---

## 6. Sample Prediction Logs
| Food ID | Category | Actual (g) | Pred (g) | Err (%) | Actual (kcal) | Pred (kcal) | Confidence |
|---|---|---|---|---|---|---|---|
| steamed_rice | grains | 180.0 | 195.5 | 8.6% | 234.0 | 254.2 | 0.83 |
| steamed_rice | grains | 245.0 | 263.7 | 7.6% | 318.5 | 342.8 | 0.96 |
| steamed_rice | grains | 115.0 | 123.4 | 7.3% | 149.5 | 160.4 | 0.83 |
| brown_rice | grains | 160.0 | 174.4 | 9.0% | 192.0 | 209.3 | 0.83 |
| chicken_biryani | grains | 220.0 | 226.6 | 3.0% | 363.0 | 373.9 | 0.87 |
| veg_biryani | grains | 190.0 | 208.0 | 9.5% | 228.0 | 249.6 | 0.88 |
| dal_tadka | legumes | 150.0 | 180.9 | 20.6% | 165.0 | 199.0 | 0.88 |
| dal_tadka | legumes | 220.0 | 270.3 | 22.9% | 242.0 | 297.3 | 0.87 |
| dal_makhani | legumes | 180.0 | 215.9 | 19.9% | 216.0 | 259.1 | 0.88 |
| dal_makhani | legumes | 240.0 | 293.7 | 22.4% | 288.0 | 352.4 | 0.87 |
| chana_masala | legumes | 185.0 | 199.6 | 7.9% | 222.0 | 239.5 | 0.88 |
| rajma_curry | legumes | 205.0 | 233.7 | 14.0% | 246.0 | 280.4 | 0.87 |
