import io
import pytest
from PIL import Image
from starlette.testclient import TestClient
from app.main import app
from app.models.database import init_db
from scripts.seed_nutrition import seed_nutrition_data

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    init_db()
    seed_nutrition_data()

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_analyze_meal_and_persistence(client):
    img = Image.new("RGB", (200, 200), color=(220, 200, 160))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)

    # Analyze
    response = client.post(
        "/api/analyze",
        files={"image": ("test_dish.jpg", buf.getvalue(), "image/jpeg")},
        data={"reference_mode": "false"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert len(data["items"]) > 0
    assert "confidence_band" in data
    assert "retry_recommended" in data
    assert data["confidence_band"] in ["high", "medium", "low"]
    
    meal_id = data["id"]
    first_item = data["items"][0]
    assert first_item["estimated_calories"] > 0
    assert first_item["estimated_weight_g"] > 0

    # Retrieve from meals list
    meals_response = client.get("/api/meals")
    assert meals_response.status_code == 200
    meals = meals_response.json()
    assert any(m["id"] == meal_id for m in meals)

    # Retrieve by detail endpoint
    detail_response = client.get(f"/api/meal/{meal_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == meal_id
    assert "confidence_band" in detail_response.json()

    # Test user correction
    correction_res = client.post(
        "/api/correction",
        json={
            "meal_item_id": first_item["food_id"],
            "corrected_weight_g": 250.0,
            "correction_type": "weight_adjustment",
        },
    )
    assert correction_res.status_code == 200
    assert correction_res.json()["status"] == "recorded"
    assert correction_res.json()["corrected_weight_g"] == 250.0
