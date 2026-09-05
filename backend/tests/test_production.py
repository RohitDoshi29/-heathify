import tempfile
import time
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.services.privacy_service import privacy_service
from scripts.cleanup_retention import run_retention_cleanup

client = TestClient(app)


def test_health_check_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"
    assert "engines" in data
    assert "engine_1_yolo_segmentation" in data["engines"]
    assert "engine_2_depth_3d" in data["engines"]
    assert "engine_3_portion_model" in data["engines"]
    assert "engine_7_custom_fusion" in data["engines"]



def test_privacy_service_anonymization():
    raw_id = "user_secret_uuid_12345"
    anon1 = privacy_service.anonymize_user_id(raw_id)
    anon2 = privacy_service.anonymize_user_id(raw_id)
    assert anon1.startswith("anon_")
    assert anon1 == anon2
    assert "secret" not in anon1


def test_privacy_service_retention_cleanup():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        old_file = tmp_path / "old_image.jpg"
        old_file.write_text("dummy")

        # Set mtime to 40 days ago
        old_time = time.time() - (40 * 86400)
        import os
        os.utime(old_file, (old_time, old_time))

        new_file = tmp_path / "new_image.jpg"
        new_file.write_text("dummy_new")

        cleaned = privacy_service.cleanup_expired_files(tmp_path, retention_days=30)
        assert cleaned == 1
        assert not old_file.exists()
        assert new_file.exists()


def test_cleanup_retention_script():
    res = run_retention_cleanup(retention_days=30)
    assert "cleaned_files" in res
    assert res["retention_days"] == 30

