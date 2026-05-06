# Rocket Elevators Operations Dashboard — Technical Specification

## Purpose

Create a static Operations Dashboard that allows the operations manager to view fleet status at a glance, identify overdue inspections, and look up individual elevators with key details. The dashboard must include a sidebar for navigation, summary metrics, and a detailed table.

---

## Page Layout

- **Overall layout**: Two-column layout.
- **Left column (fixed sidebar)**: Vertical navigation area with the product name at the top and a simple list of links in this exact order: Dashboard, Inspections, Licenses, Reports. The sidebar remains visible at all times.
- **Right column (main content)**: Contains a page header, summary metrics, and the detailed table.
- **Header area (main content, top)**: Page title "Operations Dashboard" and the exact subtitle "Fleet status overview for all registered elevators".
- **Summary metrics row (main content, below header)**: A single row of three summary cards showing key fleet metrics.
- **Detail table (main content, below summary cards)**: Full-width table for elevator lookup with sortable columns and visible row separation.

---

## Data Sources and Join Logic

Three files are used to build the dashboard. Join them on the elevator identifier before rendering any data.

| File | Role | Join Key |
|------|------|----------|
| `installed.json` | Primary device registry — type, status, location | `Elevating devices number` |
| `license.csv` | License number and expiry date | `ElevatingDevicesNumber` |
| `inspection.csv` | Most recent inspection date and outcome | `ElevatingDevicesNumber` |

**Join procedure:**

1. Start with `installed.json` as the base (one row per elevator).
2. Left-join `license.csv` on `ElevatingDevicesNumber` to add license fields. If a device has no license record, leave those fields blank.
3. For `inspection.csv`, first reduce it to one row per elevator by taking the row with the latest `Latest_INSPECTION_Date` for each `ElevatingDevicesNumber`. Then left-join that reduced table onto the base. If a device has no inspection record, leave those fields blank.
4. The final joined dataset has one row per elevator and is the source for both the summary cards and the detail table.

**Date parsing:**
- `LICENSEEXPIRYDATE` in `license.csv` is stored as `DD-MMM-YY`. Parse it as a date before any comparison or display.
- `Latest_INSPECTION_Date` in `inspection.csv` is stored as `M/D/YYYY`. Parse it as a date before any comparison or display.
- Display all dates in the dashboard as `YYYY-MM-DD`.

---

## Summary Cards

Provide three summary cards in a single horizontal row. Each card includes a label and a numeric value.

### Card 1 — Total Elevators

- **Label**: "Total Elevators"
- **Definition**: Count of all elevators in the dataset.
- **Calculation**: Count of distinct rows in `installed.json` (each row is one device). Do not deduplicate further; the file already has one record per device.

### Card 2 — Active Elevators

- **Label**: "Active Elevators"
- **Definition**: Count of elevators currently in active service.
- **Calculation**: Count rows from `installed.json` where `DeviceStatus` equals `"Active"` (case-insensitive comparison).

### Card 3 — Overdue Inspections

- **Label**: "Overdue Inspections"
- **Definition**: Count of elevators whose last inspection happened more than one year ago.
- **Calculation**: For each elevator, take its most recent `Latest_INSPECTION_Date` from `inspection.csv`. Count elevators where that date is strictly earlier than today minus 365 days. Elevators with no inspection record at all are also counted as overdue.

---

## Detail Table

The table must allow the manager to look up any elevator and see its key details. Display one row per elevator. All columns listed below are required; if a value is missing from the source data, display an empty cell rather than inventing a value.

### Columns

| # | Column Name | Source Field | Source File | Type | Display Format |
|---|-------------|-------------|-------------|------|----------------|
| 1 | Elevator ID | `Elevating devices number` | `installed.json` | Number | Integer, no decimals, no thousand separators |
| 2 | License Number | `ElevatingDevicesLicenseNumber` | `license.csv` | Text | Exact value as stored; preserve the full alphanumeric format including the `EDLIC-` prefix and zero padding |
| 3 | Location | `Location of Device` | `installed.json` | Text | Single line, exact value as stored |
| 4 | Elevator Type | `Device Type` | `installed.json` | Text | Exact value as stored; do not translate or normalize values |
| 5 | Status | `DeviceStatus` | `installed.json` | Text | Exact value as stored; do not translate or normalize values |
| 6 | License Expiry Date | `LICENSEEXPIRYDATE` | `license.csv` | Date | `YYYY-MM-DD` (parse from `DD-MMM-YY` before display) |
| 7 | Last Inspection Date | `Latest_INSPECTION_Date` | `inspection.csv` | Date | `YYYY-MM-DD` (parse from `M/D/YYYY` before display) |
| 8 | Overdue Inspection | Derived | — | Text | `"Yes"` if the last inspection date is earlier than today minus 365 days, or if there is no inspection record; `"No"` otherwise |

### Table Behavior

- **Default sort**: By Elevator ID ascending.
- **Sortable columns**: Every column must be sortable by clicking its header. Clicking once sorts ascending; clicking again sorts descending.
- **Row count**: Display all elevators; no pagination is required for the initial version.
- **Row shading**: Alternate between a white and a light-grey background on each row to aid scanning.
- **Header row**: Bold text, visually distinct background (slightly darker than the alternating row colors).

---

## Visual Style

- Clean, minimal style suitable for an internal operations tool.
- **Sidebar**: Dark charcoal background `#1E2430`, white text `#FFFFFF`, active link highlighted with background `#2B3548` and left border `4px solid #4DA3FF`.
- **Summary cards**: White background `#FFFFFF`, subtle border `1px solid #E5E7EB`, card label in small grey text `#6B7280` above the large bold numeric value. Cards are equal width and arranged horizontally in a single row.
- **Typography**: Sans-serif font throughout using `Inter, system-ui, -apple-system, "Segoe UI", Arial, sans-serif`. Card values must be `2rem` and bold. Table body text must be `0.9rem` and regular weight.
- **Overdue Inspection column**: Cells displaying `"Yes"` must be highlighted with background `#FDE2E2` and text color `#B91C1C`.
- **Spacing**: Table cell padding must be exactly `8px` vertical and `12px` horizontal.

---

## Data Assumptions

- The dashboard is static: all data is loaded from the files at build time. There is no live database connection.
- If a device appears in `installed.json` but not in `license.csv`, columns 2 and 6 are left blank for that row.
- If a device appears in `installed.json` but not in `inspection.csv`, columns 7 and 8 are left blank and `"Yes"` respectively (no inspection record means the inspection is considered overdue).
- A device may have multiple rows in `inspection.csv` (one per inspection event). Only the row with the latest `Latest_INSPECTION_Date` is used per device.
- `LICENSEEXPIRYDATE` values like `28-Apr-17` use a two-digit year. Treat years 00–29 as 2000–2029 and years 30–99 as 1930–1999 when parsing.
- Do not use `order.csv`, `altered.json`, or `incident.json` for this dashboard; they are reserved for future sections (Inspections, Reports).
