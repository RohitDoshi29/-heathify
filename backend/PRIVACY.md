# Privacy & Data Retention Policy

## 1. Principles & Commitments
1. **User Ownership**: All uploaded food images and dietary logs belong to the user.
2. **Data Minimization**: No biometric, facial, or background location data is stored.
3. **Pseudonymization**: User identifiers and correction records are hashed before entering machine learning analytics pools.

---

## 2. Retention Lifecycles & Automatic Purging

| Data Category | Retention Window | Storage Medium | Automated Mechanism |
|---|---|---|---|
| **Raw Uploaded Food Photos** | **30 Days TTL** | Encrypted Object Store / Local Cache | Purged via `cleanup_retention.py` cron sweep |
| **Volumetric Depth Maps & Masks** | **7 Days TTL** | Ephemeral Temporary Cache | Auto-deleted upon meal inference completion |
| **Logged Meal Nutrition Records** | **Permanent (or User Deleted)** | Database (`meals`, `meal_items`) | Retained for user diary history |
| **User Feedback / Weight Adjustments**| **Permanent (Anonymized)** | Database (`feedback`) | SHA-256 hashed user ID for ML retraining |

---

## 3. EXIF & Geolocation Sanitization
All client-submitted meal images undergo EXIF metadata stripping upon ingestion. GPS coordinates, device serial numbers, and camera timestamps are discarded before image processing.

---

## 4. Operational Maintenance
To run the automated retention cleanup sweep manually or via periodic scheduler:
```bash
python backend/scripts/cleanup_retention.py
```

