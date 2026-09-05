# Heathify — Detailed Remediation & Implementation Plan

**Repo:** `RohitDoshi29/-heathify`
**Prepared from:** direct review of `backend/app/services/*.py` and `backend/app/routers/analyze.py`
**Core problem:** the README claims 6 ML "engines" are Implemented; in reality only one has a real-model code path (Gemini Vision), and it's silently disabled unless an API key is set. Everything else is hardcoded heuristics (average RGB color, fixed density tables, fixed "mound height" tables). This is why food photos return wrong results.

---

## Guiding principle

Don't try to build 6 real computer-vision models before you ship something correct. Get one real signal working end-to-end first (Tier 0–1), verify accuracy on real photos, then decide if you actually need offline/no-API computer vision (Tier 2) or if the VLM-based approach is good enough for your use case.

---

## Tier 0 — Immediate fix (target: same day)

**Goal:** confirm whether the accuracy problem is simply "no API key configured," and stop it from failing silently again.

| # | Task | File(s) | Details |
|---|------|---------|---------|
| 0.1 | Get a Gemini API key | `backend/.env` | Google AI Studio → create key → `GEMINI_API_KEY=...` in `.env` (copy from `.env.example`) |
| 0.2 | Restart backend, re-test | — | Re-upload the egg photo and 3–4 other test photos. Confirm `detect()` is hitting `_detect_via_gemini_flash` (check logs for `[Engine 1 Detection] Gemini 2.5 Flash detected:`) |
| 0.3 | Fail loudly instead of silently | `detection_service.py`, `main.py` | On startup, log a clear warning if `GEMINI_API_KEY` is missing or too short. Currently `detect()` just falls through to the color heuristic with no visible signal to the developer. Add: `logger.warning("GEMINI_API_KEY not set — using placeholder color-detection fallback, accuracy will be poor")` |
| 0.4 | Surface fallback status in the API response | `models/schemas.py`, `analyze.py` | Add a `detection_method` field to the response (`"vlm"` vs `"heuristic_fallback"`) so the Flutter app / you can see when a result came from the fake path |
| 0.5 | Add a timeout/retry guard | `detection_service.py` | Current Gemini call has an 8s timeout with no retry; on transient failure it silently drops to the fallback. Add one retry before falling back, and log the failure reason distinctly from "no key configured" |

**Acceptance criteria:** every `/api/analyze` response tells you which detection path was used, and you can no longer accidentally test against the fake path without knowing it.

---

## Tier 1 — Architectural fix: collapse the fake pipeline into one real signal (target: 3–5 days)

**Problem:** `analyze.py` chains detection → segmentation → depth → portion → VLM-verify → fusion. Only detection *can* be real; segmentation/depth/portion are pure heuristics dressed up as "Engine 2/3/4." Chaining fake numbers through a real statistical fusion step (MAD outlier rejection) doesn't make them accurate — garbage in, garbage out.

**Fix:** make the VLM the primary source of truth for identification *and* a first-pass weight/calorie estimate, and treat the heuristic engines as a secondary cross-check only, not a co-equal "engine."

| # | Task | File(s) | Details |
|---|------|---------|---------|
| 1.1 | Extend the Gemini prompt to also return portion/weight estimate | `detection_service.py` | Add `estimated_weight_g` (with a plausible range) to the JSON schema Gemini already returns. Gemini/VLMs are reasonably good at "this looks like ~150g of rice" from visual portion cues — better than a fixed density-times-fixed-height calculation. |
| 1.2 | Add a second, independent VLM call for weight/calorie sanity-check | `engine6_expert_verifier.py` (repurpose existing file) | Use a stronger model (Gemini 2.5 Pro / Claude) as a genuine second opinion on total plate calories, not just a rule-based "confusing pairs" dictionary as it is today. |
| 1.3 | Rename heuristic services honestly in code and API output | `segmentation_service.py`, `depth_service.py`, `portion_service.py` | Change `method` field values from implying real CV (e.g. `"sam_segmentation"`) to explicit `"heuristic_estimate"` / `"density_prior_fallback"`. This prevents future-you (or a teammate) from trusting these numbers as if a real model produced them. |
| 1.4 | Feed heuristic estimates into fusion only as a low-weight sanity check | `fusion_service.py` | Lower the confidence weight assigned to heuristic-sourced `WeightEstimate` entries so real VLM numbers dominate the fused result when both are present. |
| 1.5 | Simplify `analyze.py` control flow | `routers/analyze.py` | Reduce from a 6-stage sequential chain to: (a) VLM identify + estimate, (b) heuristic cross-check in parallel, (c) fusion, (d) nutrition lookup. Fewer sequential stages = lower latency and fewer places for silent fallback. |
| 1.6 | Update README to match reality | `README.md` | Replace the "Implemented" table with accurate status per engine (e.g. "Detection: VLM-based, requires API key; heuristic fallback exists but is low-accuracy"). |

**Acceptance criteria:** a test set of ~20 varied food photos (see Tier 3 testing) gets correct food identification in the large majority of cases, and you can see confidence + method for each item in the response.

---

## Tier 2 — Real offline computer vision (only if you need to remove the API dependency)

Do this tier **only if** you specifically need the app to work without a paid/rate-limited external API call (cost, offline use, latency, or privacy reasons). It is materially more engineering work than Tier 0–1.

| # | Task | Effort | Details |
|---|------|--------|---------|
| 2.1 | Real object detection | Medium–High | Fine-tune YOLOv8 (or use a pretrained food-detection checkpoint) on a labeled food dataset. Food-101 covers general dishes; for Indian food specifically (your density table is India-focused: dal, roti, paneer, biryani) you'll want an Indian-food dataset or to label your own ~500–1000 images. |
| 2.2 | Real segmentation | Medium | Integrate Segment Anything (SAM) or MobileSAM, feeding in the YOLO bounding boxes as prompts, to replace the Pillow contour heuristic in `segmentation_service.py`. |
| 2.3 | Real depth/volume estimation | Medium–High | Integrate a monocular depth model (MiDaS or Depth Anything) to replace the hardcoded "typical mound height per food category" table in `depth_service.py`. Calibrate pixel-to-cm scale using the existing `reference_service.py` fiducial-object logic (that part's design is reasonable, just needs a real detector behind it instead of the average-brightness heuristic). |
| 2.4 | Retrain portion/density model on real data | Medium | You already have `backend/data/portion_training_data.csv` — check whether it has enough labeled samples to fit a proper regression instead of the fixed dictionary in `portion_service.py`. |
| 2.5 | Model hosting/inference infra | Medium | Decide GPU vs CPU inference, containerize model weights (don't commit them to git), add a model-download step to `Dockerfile`. |

**Note:** this tier is a multi-week project on its own, not a bugfix. Treat Tier 0–1 as the thing to ship first; revisit Tier 2 based on real usage/cost data.

---

## Tier 3 — Make it honest, testable, and hard to silently regress

| # | Task | File(s) | Details |
|---|------|---------|---------|
| 3.1 | Build a fixed test image set | new: `backend/tests/fixtures/` | 15–20 photos spanning your supported categories (egg, rice, dal, roti, paneer curry, salad, biryani, mixed plates, poor lighting, cluttered background). Include the exact egg photo that failed. |
| 3.2 | Add regression tests asserting expected labels | `backend/tests/` | For each fixture image, assert the returned `food_id` matches expectation and confidence is above a threshold. Run this in CI on every PR so a future "oops, forgot the API key" doesn't ship silently again. |
| 3.3 | Expand nutrition DB coverage | `backend/data/nutrition_seed.csv` | README claims "seeded USDA FoodData Central + Indian food database" — currently it's a small CSV. Pull a broader USDA FDC export and merge, dedupe against your existing IDs. |
| 3.4 | Wire up `init_db()` properly | `models/database.py`, deployment scripts | README notes tables aren't auto-created on startup. Add an Alembic migration or startup hook so this isn't a manual step someone forgets in production. |
| 3.5 | Replace in-memory `/api/meals` placeholder with real persistence | `routers/meals.py` | Currently serves an in-memory placeholder list per the README — wire it to the actual DB models that already exist. |
| 3.6 | Add a confidence-based UI warning | Flutter app | The Flutter app already has "low-confidence retry prompts" per the README — make sure this is actually wired to the `detection_method`/confidence fields so users see "low confidence, please confirm" instead of trusting a fallback guess silently. |

---

## Suggested execution order

1. **Today:** Tier 0 (API key + logging) — find out if this alone fixes it.
2. **This week:** Tier 1 (collapse to VLM-primary pipeline, honest labeling, README fix).
3. **Ongoing:** Tier 3.1–3.2 (test fixtures + regression tests) — do this *before* Tier 2 so you have a baseline to measure real-model improvements against.
4. **Only if needed:** Tier 2 (real offline CV models) — treat as a separate project phase, not a quick fix.

---

## Quick reference: what's real vs. fake today

| Engine | README claims | Actually is |
|---|---|---|
| Detection | Implemented (YOLO) | Gemini Vision call *if* API key set, else average-RGB-color bucket match, defaulting to "Boiled Egg" |
| Segmentation | Implemented (SAM/UNet) | Pillow edge heuristics, fixed 78% foreground-ratio fallback |
| Depth | Implemented | Hardcoded per-category mound-height lookup table |
| Portion/Density | Implemented | Hardcoded density dictionary (reasonable values, but not measured/learned) |
| VLM Verifier | Implemented | Rule-based dictionary of "confusing food pairs," no actual VLM call |
| Fusion | Implemented | **Genuinely real** — proper MAD-based outlier rejection math |
| Nutrition DB | USDA FDC + Indian DB | Small seeded CSV with reasonable fallback logic |