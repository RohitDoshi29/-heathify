# AI Food Calorie Detection - Starter Project

Basic scaffold implementing the architecture from the master plan:
a **Flutter/Dart** mobile app talking to a **Python/FastAPI** backend.

This is a runnable skeleton, not a finished product. Every ML "engine"
(detection, segmentation, depth, portion, VLM) is stubbed with clearly
marked `TODO`s and placeholder logic so the full request/response loop
works end-to-end before real models are plugged in.

```
food_calorie_app/
├── flutter_app/          # Mobile client
│   ├── pubspec.yaml
│   └── lib/
│       ├── main.dart
│       ├── models/        # Meal, FoodItem (mirrors backend schema)
│       ├── services/      # ApiService (talks to FastAPI)
│       ├── screens/       # Home, Camera, Analysis, Results, History
│       └── widgets/       # ConfidenceBadge, MacroSummary
└── backend/               # API + orchestration
    ├── requirements.txt
    ├── .env.example
    └── app/
        ├── main.py         # FastAPI app + router wiring
        ├── routers/        # analyze, meals, correction, health
        ├── models/         # Pydantic schemas + SQLAlchemy ORM
        └── services/       # nutrition_service, fusion_service
```

## Running the backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit DATABASE_URL etc.
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Visit `http://localhost:8000/docs` for interactive API docs (Swagger UI).

The database tables are defined in `app/models/database.py` but are not
auto-created on startup — call `init_db()` once (e.g. from a small setup
script or an Alembic migration) before relying on persistence. The
`/api/meals` and `/api/meal/{id}` endpoints currently serve an in-memory
placeholder list so the app is testable before that wiring is done.

## Running the Flutter app

```bash
cd flutter_app
flutter pub get
flutter run
```

By default `ApiService` points at `http://10.0.2.2:8000`, which is the
Android emulator's alias for the host machine's `localhost`. Update the
`baseUrl` in `lib/main.dart` if you're running on iOS simulator
(`http://localhost:8000`) or a physical device (your machine's LAN IP).

## What's implemented

| Component / Engine | Status | Architecture & Implementation Details |
|---|---|---|
| **Primary Food Detection & Portions (Engine 1)** | **Implemented (VLM Primary)** | Real-time multimodal vision via Gemini 2.5 Flash (`gemini-2.5-flash`). Detects exact food items, bounding boxes, and visual portion weights (grams). Robust retry guard and fallback with explicit status reporting. |
| **Context & Preparation Reasoner (Engine 4)** | **Implemented (VLM)** | Multimodal scene understanding for global meal context (Indian thali vs bowl), side dishes, and cooking cues. |
| **Monocular Depth & Voxel Relief (Engine 2)** | **Implemented (Cross-Check)** | Monocular depth relief map and 3D height variation profile ($H_{mean}$) used as a secondary geometric sanity-check. |
| **Portion Density Priors (Engine 3)** | **Implemented (Cross-Check)** | Empirical physical density priors ($\rho \in [0.38, 1.15]\text{ g/cm}^3$) across 10 food categories. |
| **Nutrition Database (Engine 5)** | **Implemented (Authoritative)** | Seeded USDA FoodData Central + Indian food database with SQLite/Postgres persistence and fuzzy name matching. |
| **Frontier Expert Verifier (Engine 6)** | **Implemented (Frontier LLM)** | Gemini 2.5 Pro / Claude Sonnet verifier conditionally escalated for ambiguous dishes or high portion discrepancies ($>30\%$). |
| **Custom Fusion Engine (Engine 7)** | **Implemented (Real Math)** | Median Absolute Deviation (MAD) modified Z-score outlier filtering, inter-engine consensus scoring, and dynamic confidence bands. |
| **Flutter Mobile Client** | **Implemented (Live)** | Full navigation, camera/gallery scanner, history, macro charts, low-confidence retry prompts, live on physical Android devices. |
| **Production & Telemetry** | **Implemented** | Dockerfile, docker-compose, latency budgets (`PERFORMANCE.md`), privacy TTL cleanup (`PRIVACY.md`), and diagnostic health checks. |


