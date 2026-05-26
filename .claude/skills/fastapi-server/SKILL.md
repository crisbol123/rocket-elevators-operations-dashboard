---
description: Load when editing platform/server.py or Python files in platform/ — FastAPI server conventions and endpoint reference for the Rocket Elevators operations dashboard.
---

# FastAPI Server Conventions

## Server Reference

- FastAPI server is in `platform/server.py`
- Run with: `cd platform && python3 -m uvicorn server:app --reload`
- Dashboard served at `http://localhost:8000/`
- `platform/elevator_fleet.csv` is loaded into memory on startup as a pandas DataFrame (`DF`)

## Endpoints

- `GET /fragments/table` — returns paginated, filtered, sorted table HTML fragment (10 rows per page)
  - Params: `page`, `status` (all/ACTIVE/PENDING_RENEWAL), `expired` (all/yes/no), `sort_by` (elevator_id/license_expiry_date), `sort_dir` (asc/desc)
- HTMX endpoints return HTML fragments, not JSON
