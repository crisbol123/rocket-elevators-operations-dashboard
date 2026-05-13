# Rocket Elevators Operations Dashboard

Internal operations dashboard that replaces a manual spreadsheet workflow, showing the elevator fleet at a glance and enabling unified, filterable lookup across licenses, installations, alterations, and inspections.

## Tech Stack

- **Frontend:** HTML, Tailwind CSS, HTMLX
- **Backend:** Python(FastAPI)
- **Notebooks:** Python (Jupyter)
- **Data:** CSV and JSON files

## Directory Structure

/platform      # HTML for the operations dashboard UI
/intelligence  # Jupyter notebooks for analytics and data exploration
/data          # Shared datasets used by platform and intelligence
/docs          # Specs, reports, and project documentation

## Data Files (`/data`)

- `license.csv` — CSV — Elevator license records with status and expiry
- `inspection.csv` — CSV — Inspection history with outcomes
- `order.csv` — CSV — Compliance orders with risk scores
- `installed.json` — JSON — Installed elevating devices
- `altered.json` — JSON — Altered device records
- `incident.json` — JSON — Incident reports

## Server

- FastAPI server is in `platform/server.py`
- Run with: `cd platform && python3 -m uvicorn server:app --reload`
- Dashboard served at `http://localhost:8000/`
- HTMX endpoints return HTML fragments, not JSON
- `platform/elevator_fleet.csv` is loaded into memory on startup as a pandas DataFrame (`DF`)
- Jinja2 templates are in `platform/templates/`
- `GET /fragments/table` — returns paginated, filtered, sorted table HTML fragment (10 rows per page). Params: `page`, `status` (all/ACTIVE/PENDING_RENEWAL), `expired` (all/yes/no), `sort_by` (elevator_id/license_expiry_date), `sort_dir` (asc/desc)



## Coding Conventions
- Use Python type hints in all function signatures
- Use HTMX attributes (hx-get, hx-post, etc.) for all dynamic interactions
- When asked about code, do not edit it unless explicitly instructed to do so
- Jinja2 comments use `{# comment #}`, not `{{# comment #}}`. 
- Never run `git commit` or `git push` unless the user explicitly says to commit or push.
