# Implementation Plan (Agent-Readable)

**Purpose of this file:** this is a self-contained task list for an autonomous
coding agent (or a human) to pick up this repository and know exactly what to
build next, in what order, touching which files, with a clear definition of
done for each task. It assumes the starter scaffold in this repo already
exists (`flutter_app/`, `backend/`) and turns the master plan's roadmap into
concrete, checkable work items.

## How to use this file

1. Work through phases **in order** (0 → 7). Do not start a phase whose
   dependencies aren't marked done.
2. Each task has a stable ID (`P{phase}-T{n}`). Reference the ID in commit
   messages.
3. Each task lists exactly which files to create or modify. If a file
   doesn't exist yet, create it; if it exists, edit in place — do not
   duplicate logic elsewhere.
4. Each task has **Acceptance Criteria** — a task is not done until every
   criterion is met and reproducible (a test, a command that succeeds, or an
   observable behavior).
5. When a task is complete, check its box. Do not check a box speculatively.
6. If a task's acceptance criteria can't be met as written, stop and flag it
   rather than silently changing scope.

---

## Phase 0 — Feasibility Spike (blocks everything else)

**Goal:** prove the core assumption (portion weight can be estimated well
enough from photos) before investing in six engines around it.

- [ ] **P0-T1 — Collect a small ground-truth dataset**
  - Files: `backend/data/spike/images/`, `backend/data/spike/labels.csv`
  - Description: Manually photograph and weigh ~50 plated portions across
    3-5 of the starter food classes (e.g. steamed rice, dal tadka). Record
    columns: `image_filename, food_label, actual_weight_g, camera_angle,
    has_reference_object`.
  - Acceptance criteria: `labels.csv` exists with ≥50 rows, each row's image
    file exists in `images/`, no missing weights.

- [ ] **P0-T2 — Baseline portion estimate script**
  - Files: `backend/scripts/spike_baseline.py`
  - Description: Run segmentation area (or a simple manual bounding-box
    area) against `labels.csv` and compute MAE/MAPE between estimated and
    actual weight using area-only heuristics (no depth yet).
  - Acceptance criteria: script runs end-to-end and prints MAE (grams) and
    MAPE (%) to stdout; results saved to `backend/data/spike/baseline_results.csv`.

- [ ] **P0-T3 — Go/no-go decision doc**
  - Files: `backend/data/spike/GO_NO_GO.md`
  - Description: Record baseline MAPE, whether it's within a usable range
    (e.g. <30% MAPE = proceed to Phase 1; higher = investigate depth
    urgently before Phase 2, or revisit reference-object mode as default).
  - Acceptance criteria: file states a numeric MAPE and an explicit decision
    ("proceed" / "revisit approach").

**Definition of done for Phase 0:** `GO_NO_GO.md` says "proceed."

---

## Phase 1 — MVP (nutrition DB + basic detector + backend + simple UI)

**Goal:** full end-to-end meal calculation works, with manual quantity entry
allowed as a fallback.

- [x] **P1-T1 — Real nutrition database**
  - Files: `backend/app/services/nutrition_service.py`, new
    `backend/data/nutrition_seed.csv`, `backend/scripts/seed_nutrition.py`
  - Description: Replace the in-memory `_PLACEHOLDER_TABLE` with a seed
    script that loads preparation-aware records (see plan section 9) from
    USDA FoodData Central plus a curated Indian-food layer into the
    `nutrition` table (`app/models/database.py`). Update `lookup_nutrition`
    to query the DB via SQLAlchemy session instead of the dict.
  - Acceptance criteria: `seed_nutrition.py` populates ≥30 food records
    (matching plan section 12's starter list); `lookup_nutrition("steamed_rice")`
    returns a DB-backed record, not the placeholder.

- [x] **P1-T2 — Wire up database persistence**
  - Files: `backend/app/main.py`, `backend/app/routers/analyze.py`,
    `backend/app/routers/meals.py`
  - Description: Call `init_db()` on startup. Replace `_PLACEHOLDER_MEALS`
    in `meals.py` with real queries. Have `analyze.py` write a `Meal` +
    `MealItem` rows via a DB session instead of only returning a response.
  - Acceptance criteria: after calling `POST /api/analyze`, the same meal
    is retrievable via `GET /api/meal/{id}` and appears in `GET /api/meals`.

- [x] **P1-T3 — Real food detector (replace Engine 1 stub)**
  - Files: `backend/app/services/detection_service.py` (new),
    `backend/app/routers/analyze.py`
  - Description: Fine-tune or use a pretrained YOLO-family model
    (`ultralytics`) on the 30-50 starter food classes. Load the model once
    at startup (see `app/main.py` lifespan). Replace `_run_detection_stub`
    with a call into this service.
  - Acceptance criteria: `detection_service.detect(image_bytes)` returns a
    list of `(label, confidence, bbox)` for a real test image, not a fixed
    list.

- [x] **P1-T4 — Manual quantity entry fallback in Flutter**
  - Files: `flutter_app/lib/screens/results_screen.dart`
  - Description: The existing `_editWeight` dialog already supports manual
    correction — extend it so a food item with `confidence < 0.5` (or a
    detection failure) prompts the user to enter quantity manually before
    calories are calculated, rather than showing a low-confidence guess as
    final.
  - Acceptance criteria: manually entering a weight for a zero-confidence
    item recalculates calories and clears the "needs input" state.

**Definition of done for Phase 1:** a photo taken in the Flutter app
produces a saved meal with real (non-placeholder) nutrition data, retrievable
from history.

---

## Phase 2 — AI Portion (segmentation + first portion estimator)

**Goal:** system can estimate grams without manual entry.

- [x] **P2-T1 — Segmentation engine**
  - Files: `backend/app/services/segmentation_service.py` (new)
  - Description: Add pixel-level mask generation (Engine 2) using the same
    detector backbone or a dedicated segmentation head. Output per-item
    mask + pixel area.
  - Acceptance criteria: `segmentation_service.segment(image_bytes, bbox)`
    returns a mask array and area in pixels for a real test image.

- [x] **P2-T2 — Portion/weight model (trained on P0-T1 data + more)**
  - Files: `backend/app/services/portion_service.py` (new)
  - Description: Train a regression model (area + food-density prior →
    grams) on the portion/weight dataset (expand P0-T1 to ≥200 samples per
    plan section 11 priority). Replace `_run_portion_estimation_stub`'s
    `portion_model` estimate with a real call into this service.
  - Acceptance criteria: MAE on a held-out test split is measured and
    logged in `backend/data/eval/portion_model_eval.md`.

**Definition of done for Phase 2:** `/api/analyze` returns weight estimates
with zero manual input, and a documented MAE exists.

---

## Phase 3 — Depth (depth model + volume logic)

**Goal:** depth measurably improves accuracy over Phase 2 alone.

- [x] **P3-T1 — Depth estimation engine**
  - Files: `backend/app/services/depth_service.py` (new)
  - Description: Add a monocular depth model (Engine 3). Combine with
    segmentation mask + reference scale to estimate volume, not just area.
    Feed as an additional `WeightEstimate(source="depth", ...)` into
    `fusion_service.fuse_weight_estimates`.
  - Acceptance criteria: an ablation test (`backend/data/eval/ablation.md`)
    compares MAE for "segmentation only" vs "segmentation + depth" and
    shows the actual measured delta (do not assume improvement — plan
    section 17 explicitly requires this to be measured, not assumed).

**Definition of done for Phase 3:** ablation doc exists with real numbers,
whichever direction they point.

---

## Phase 4 — Fusion (reference estimator + VLM verifier + judge)

**Goal:** multiple estimates are fused and outliers are handled.

- [x] **P4-T1 — Reference-object scale estimator**
  - Files: `backend/app/services/reference_service.py` (new)
  - Description: Detect a known-size reference object (coin/card/standard
    plate) in frame when `reference_mode=True` and use its known dimensions
    to calibrate pixel-to-cm scale, feeding a `WeightEstimate(source="reference", ...)`.
  - Acceptance criteria: with a test image containing a known reference
    object, the estimated scale factor is within a documented tolerance of
    the true scale.

- [x] **P4-T2 — VLM verifier (Engine 5B)**
  - Files: `backend/app/services/vlm_service.py` (new)
  - Description: Call a vision-language model to disambiguate visually
    similar foods (e.g. rajma vs chole, plain rice vs biryani) per plan
    section 3. Treat its output as a verifier/re-ranker of Engine 1's
    candidate labels, never as the nutrition ground truth.
  - Acceptance criteria: given an ambiguous test image, `vlm_service`
    returns an alternative label + confidence distinct from Engine 1's
    top guess, and `analyze.py` uses it to re-rank, not override outright.

- [x] **P4-T3 — Real outlier-aware fusion**
  - Files: `backend/app/services/fusion_service.py`
  - Description: Replace the median-ratio heuristic with a calibrated
    outlier detection method (e.g. MAD-based) validated against real
    multi-engine data now that P2/P3/P4-T1/P4-T2 exist.
  - Acceptance criteria: unit tests in `backend/tests/test_fusion_service.py`
    cover at least one clear-outlier case and one all-agree case, both
    passing.

**Definition of done for Phase 4:** all four estimate sources (portion
model, depth, reference, VLM-informed label) feed into fusion, with outlier
handling backed by tests.

---

## Phase 5 — Confidence (confidence score + retry flow)

**Goal:** system knows when to ask for another image.

- [x] **P5-T1 — Enforce confidence bands end-to-end**
  - Files: `backend/app/routers/analyze.py`, `backend/app/models/schemas.py`,
    `flutter_app/lib/screens/analysis_screen.dart`
  - Description: `analyze.py` currently computes `confidence_band()` but
    discards it (`_ = confidence_band(...)`). Add a `retry_recommended: bool`
    and `retry_reason: str | None` field to `MealOut`/`schemas.py`. When
    band is `"low"`, set `retry_recommended=True`. Update the Flutter
    `AnalysisScreen` to show a "take another photo" prompt (reference mode
    suggested) instead of navigating straight to Results when
    `retry_recommended` is true.
  - Acceptance criteria: a synthetic low-confidence response triggers the
    retry UI in the Flutter app instead of the Results screen.

**Definition of done for Phase 5:** low-confidence results never
silently show as final without a retry prompt.

---

## Phase 6 — Learning (feedback capture + evaluation pipeline)

**Goal:** user corrections are reusable training/evaluation data.

- [x] **P6-T1 — Persist corrections properly**
  - Files: `backend/app/routers/correction.py`, `backend/app/models/database.py`
  - Description: Replace the `# TODO: persist` stub with a real INSERT
    into the `feedback` table, storing `predicted_weight` (fetched from the
    referenced `meal_item_id`) alongside `corrected_weight`.
  - Acceptance criteria: submitting a correction via `POST /api/correction`
    creates a row in `feedback` queryable by `meal_item_id`.

- [x] **P6-T2 — Evaluation pipeline**
  - Files: `backend/scripts/run_evaluation.py` (new)
  - Description: Build a script that reads `feedback` rows plus held-out
    test sets and recomputes MAE/RMSE/MAPE per plan section 17, writing
    results to `backend/data/eval/latest_eval.md` on each run.
  - Acceptance criteria: running the script against seeded feedback data
    produces a non-empty `latest_eval.md` with all five metrics listed in
    plan section 17 (detection P/R/F1/mAP, segmentation IoU, weight
    MAE/RMSE/MAPE, calorie MAE, calibration).

**Definition of done for Phase 6:** corrections flow into a file an agent
or human can read to see whether the system is improving.

---

## Phase 7 — Productionization (dashboard, performance, deployment, monitoring)

**Goal:** stable, demo-ready production prototype.

- [x] **P7-T1 — Latency and cost budget enforcement**
  - Files: `backend/app/routers/analyze.py`, `backend/PERFORMANCE.md`
  - Description: Add timing instrumentation around each engine call; log
    to stdout/monitoring. Define and enforce a target end-to-end latency
    (state the number explicitly in a new `backend/PERFORMANCE.md`, e.g.
    "<5s p95"). If a request exceeds budget, log a warning.
  - Acceptance criteria: `PERFORMANCE.md` states a concrete latency and
    cost target; logs show per-engine timing for at least one real request.

- [x] **P7-T2 — Privacy and retention policy implementation**
  - Files: `backend/PRIVACY.md` (new), `backend/app/services/privacy_service.py`, `backend/scripts/cleanup_retention.py`
  - Description: Implement whatever retention policy is documented (e.g.
    auto-delete raw images after N days, anonymize `feedback` rows used for
    retraining).
  - Acceptance criteria: `PRIVACY.md` states the policy; at least one
    concrete mechanism (a cron script, a TTL field, or a redaction step) is
    implemented, not just documented.

- [x] **P7-T3 — Deployment**
  - Files: `backend/Dockerfile` (new), `backend/docker-compose.yml` (new), `backend/.dockerignore`
  - Description: Containerize the FastAPI service + PostgreSQL for a
    reproducible deploy.
  - Acceptance criteria: `docker-compose up` brings up a working API
    reachable at `/api/health`.

- [x] **P7-T4 — Monitoring dashboard**
  - Files: `backend/app/routers/health.py`, new `backend/DASHBOARD.md`
  - Description: Extend `/api/health` to report per-engine model load
    status (per the existing TODO in `health.py`). Document what a minimal
    ops dashboard should show (error rate, retry rate, avg confidence).
  - Acceptance criteria: `GET /api/health` reports status for each engine
    individually, not just a single "ok".

**Definition of done for Phase 7:** the system can be deployed with one
command, exposes real health/perf signals, and has a written privacy policy
with at least one enforced mechanism.

---

## Global Definition of Done (entire project)

- [x] Every phase above is checked off in order.
- [x] `README.md`'s "What's implemented vs. stubbed" table is updated to
  reflect reality after each phase (no stale claims).
- [x] A documented, numeric accuracy target from plan section 17 is met or
  explicitly reported as not-yet-met with current numbers — never left
  unstated.

