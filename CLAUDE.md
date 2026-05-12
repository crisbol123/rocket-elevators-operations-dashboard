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

## Coding Conventions
- Use Python type hints in all function signatures
- Use HTMX attributes (hx-get, hx-post, etc.) for all dynamic interactions
- When asked about code, do not edit it unless explicitly instructed to do so
