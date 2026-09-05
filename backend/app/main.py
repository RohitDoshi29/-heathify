"""
FastAPI application entry point.

Architecture (per master plan section 13):
  Frontend -> FastAPI -> orchestration layer -> ML services + nutrition
  service + PostgreSQL/SQLite + object storage.

Run locally:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()


from app.models.database import init_db, SessionLocal, Food
from app.routers import analyze, meals, correction, health
from scripts.seed_nutrition import seed_nutrition_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize tables and seed default nutrition data if empty
    init_db()
    db = SessionLocal()
    try:
        food_count = db.query(Food).count()
        if food_count == 0:
            print("[Lifespan] Seeding initial nutrition database...")
            seed_nutrition_data(db)
    except Exception as e:
        print(f"[Lifespan] DB startup check warning: {e}")
    finally:
        db.close()

    yield
    # Shutdown logic (if any)


app = FastAPI(
    title="AI Food Calorie Detection API",
    description="Multi-engine visual food energy estimation service.",
    version="0.1.0",
    lifespan=lifespan,
)

# Allow Flutter app (web/desktop/mobile) to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(analyze.router, prefix="/api", tags=["analyze"])
app.include_router(meals.router, prefix="/api", tags=["meals"])
app.include_router(correction.router, prefix="/api", tags=["correction"])


@app.get("/")
def root():
    return {"service": "food-calorie-detection", "status": "ok"}
