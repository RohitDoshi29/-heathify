"""
Data Retention Maintenance Script (cleanup_retention.py).

Enforces storage retention policies by purging expired images and anonymizing feedback data.
"""
import os
import sys
from pathlib import Path

backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from app.services.privacy_service import privacy_service


def run_retention_cleanup(retention_days: int = 30) -> dict:
    uploads_dir = backend_root / "data" / "uploads"
    os.makedirs(uploads_dir, exist_ok=True)

    cleaned = privacy_service.cleanup_expired_files(uploads_dir, retention_days=retention_days)
    print(f"[Retention] Swept '{uploads_dir}': removed {cleaned} expired files older than {retention_days} days.")
    return {"cleaned_files": cleaned, "retention_days": retention_days}


if __name__ == "__main__":
    run_retention_cleanup()

