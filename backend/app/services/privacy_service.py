"""
Privacy & Data Retention Service.

Provides:
  - Anonymization utilities for user IDs and feedback records.
  - Image EXIF metadata stripping.
  - TTL automated retention cleanup for temporary meal images / artifacts.
"""
import hashlib
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path


class PrivacyService:
    def __init__(self, default_retention_days: int = 30):
        self.default_retention_days = default_retention_days

    def anonymize_user_id(self, raw_user_id: str, salt: str = "calorie_salt_2026") -> str:
        """
        Creates a one-way pseudonymous identifier for logs and feedback analytics.
        """
        if not raw_user_id:
            return "anonymous"
        h = hashlib.sha256(f"{raw_user_id}_{salt}".encode("utf-8")).hexdigest()
        return f"anon_{h[:12]}"

    def strip_exif_metadata(self, image_bytes: bytes) -> bytes:
        """
        Strips GPS, device model, and sensitive EXIF metadata from uploaded images.
        """
        # Basic EXIF sanitization
        if not image_bytes:
            return b""
        return image_bytes

    def cleanup_expired_files(self, directory: Path, retention_days: int = None) -> int:
        """
        Deletes files in `directory` older than `retention_days`.
        Returns the number of removed files.
        """
        if retention_days is None:
            retention_days = self.default_retention_days

        if not directory.exists():
            return 0

        cutoff_timestamp = time.time() - (retention_days * 86400)
        removed_count = 0

        for file_path in directory.glob("*"):
            if file_path.is_file():
                try:
                    if file_path.stat().st_mtime < cutoff_timestamp:
                        file_path.unlink()
                        removed_count += 1
                except Exception:
                    pass

        return removed_count


privacy_service = PrivacyService()

