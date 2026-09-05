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

| Component / Engine | Status | Notes |
|---|---|---|
| **Flutter Mobile App** | **Implemented** | Full navigation, camera/gallery scanner, history, macro charts, low-confidence retry prompts, live on Android |
| **API Client (`ApiService`)** | **Implemented** | Dual-mode connectivity (ADB reverse localhost + Wi-Fi LAN IP fallback) |
| **FastAPI Backend & Routers** | **Implemented** | Endpoints `/api/analyze`, `/api/meals`, `/api/correction`, `/api/health` |
| **Food Detection (Engine 1)** | **Implemented** | YOLO-family detector service with bounding box extraction and confidence scoring |
| **Pixel Segmentation (Engine 2)** | **Implemented** | SAM/UNet foreground mask generation and pixel area calculation |
| **Monocular Depth (Engine 3)** | **Implemented** | Depth relief map, voxel volume calculation, and height integration |
| **Portion & Density (Engine 4)** | **Implemented** | Empirical density prior regression across 10 food categories |
| **Nutrition Database (Engine 5)** | **Implemented** | Seeded USDA FoodData Central + Indian food database with SQLite/Postgres persistence |
| **VLM Verifier (Engine 5B)** | **Implemented** | Vision-Language candidate disambiguation and candidate re-ranking |
| **Multi-Engine Fusion (Engine 6)** | **Implemented** | Median Absolute Deviation (MAD) modified Z-score outlier filtering + consensus |
| **Reference Object Scaling** | **Implemented** | Fiducial card/coin detection for metric pixel-to-cm calibration |
| **Continuous Learning (Phase 6)**| **Implemented** | User correction tracking in `FEEDBACK` table & automated benchmark evaluation (`run_evaluation.py`) |
| **Production & Telemetry (Phase 7)**| **Implemented** | Dockerfile, docker-compose, latency budgets (`PERFORMANCE.md`), privacy TTL cleanup (`PRIVACY.md`), diagnostic health checks |

