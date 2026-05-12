# Rocket Elevators Operations Dashboard — Technical Specification

## Purpose

Create a static Operations Dashboard that allows the operations manager to view fleet status at a glance, identify overdue inspections, and look up individual elevators with key details. The dashboard must include a sidebar for navigation, summary metrics, and a detailed table.

---

## Technology Stack

- **Implementation**: A single static HTML file. No frameworks, no build step.
- **CSS**: Tailwind CSS loaded via CDN (`<script src="https://cdn.tailwindcss.com"></script>`). No local Tailwind installation.
- **Sorting**: Implemented with vanilla JavaScript embedded in a `<script>` tag at the bottom of the HTML file. No external JS libraries.
- **Data**: All data is loaded at runtime via `fetch()` directly from the source files in the `../data/` directory (relative to `platform/index.html`). Data is **never** embedded or hardcoded in the HTML. No build step, no backend — the browser fetches the files and joins them client-side in JavaScript.
- **Output file**: Save the finished dashboard as `platform/index.html`.

---

## Page Layout

- **Overall layout**: Two-column layout.
- **Left column (fixed sidebar)**: Vertical navigation area with the product name at the top and a simple list of links in this exact order: Dashboard, Inspections, Licenses, Reports. The sidebar remains visible at all times. The **Dashboard** link is always rendered in the active style; the remaining three links are rendered in the default style.
- **Right column (main content)**: Contains a page header, summary metrics, and the detailed table.
- **Header area (main content, top)**: Page title "Operations Dashboard" and the exact subtitle "Fleet status overview for all registered elevators".
- **Summary metrics row (main content, below header)**: A single row of three summary cards showing key fleet metrics.
- **Detail table (main content, below summary cards)**: Full-width table for elevator lookup with sortable columns and visible row separation.

---

## Data Sources and Join Logic

Three files are used to build the dashboard. Join them on the elevator identifier before rendering any data.

- `installed.json` — Role: Primary device registry (type, status, location). Join key: `Elevating devices number`.
- `license.csv` — Role: License number and expiry date. Join key: `ElevatingDevicesNumber`.
- `inspection.csv` — Role: Most recent inspection date and outcome. Join key: `ElevatingDevicesNumber`.

**Join procedure:**

1. Start with `installed.json` as the base (one row per elevator).
2. Left-join `license.csv` on `ElevatingDevicesNumber` to add license fields. If a device has no license record, leave those fields blank.
3. For `inspection.csv`, first reduce it to one row per elevator by taking the row with the latest `Latest_INSPECTION_Date` for each `ElevatingDevicesNumber`. Then left-join that reduced table onto the base. If a device has no inspection record, leave those fields blank.
4. The final joined dataset has one row per elevator and is the source for both the summary cards and the detail table.

**Date parsing:**
- `LICENSEEXPIRYDATE` in `license.csv` is stored as `DD-MMM-YY`. Two-digit years: treat 00–29 as 2000–2029 and 30–99 as 1930–1999.
- `Latest_INSPECTION_Date` in `inspection.csv` is stored as `M/D/YYYY`.
- Parse all dates before any comparison or display. Display all dates in the dashboard as `YYYY-MM-DD`.


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

1. Elevator ID — Source field: `Elevating devices number` (installed.json). Type: Number. Display: Integer, no decimals, no thousand separators.
2. License Number — Source field: `ElevatingDevicesLicenseNumber` (license.csv). Type: Text. Display: Exact value as stored; do not normalize, reformat, or add any prefix.
3. Location — Source field: `Location of Device` (installed.json). Type: Text. Display: Single line, exact value as stored.
4. Elevator Type — Source field: `Device Type` (installed.json). Type: Text. Display: Exact value as stored; do not translate or normalize values.
5. Status — Source field: `DeviceStatus` (installed.json). Type: Text. Display: Exact value as stored; do not translate or normalize values.
6. License Expiry Date — Source field: `LICENSEEXPIRYDATE` (license.csv). Type: Date. Display: `YYYY-MM-DD` (parse from `DD-MMM-YY` before display).
7. Last Inspection Date — Source field: `Latest_INSPECTION_Date` (inspection.csv). Type: Date. Display: `YYYY-MM-DD` (parse from `M/D/YYYY` before display).
8. Overdue Inspection — Source: Derived. Type: Text. Display: "Yes" if the last inspection date is earlier than today minus 365 days, or if there is no inspection record; "No" otherwise.

### Table Behavior

- **Default sort**: By Elevator ID ascending.
- **Sortable columns**: Every column must be sortable by clicking its header. Clicking once sorts ascending; clicking again sorts descending. Changing the sort column or direction must always reset the view to page 1.
- **Row count**: Display records paginated — 30 rows per page. Do not render all rows at once.
- **Pagination controls**: Render a pagination bar below the table with Previous and Next buttons and the current page indicator in the format `Page X of Y`. Disable Previous on the first page and Next on the last page.
- **Total count label**: Above the pagination bar, show a single line with the total number of records in the format `Showing X–Y of Z elevators` (e.g. `Showing 1–30 of 46,936 elevators`), updating it on every page change.
- **Row shading**: Alternate between a white and a light-grey background on each row to aid scanning.
- **Header row**: Bold text, visually distinct background (slightly darker than the alternating row colors).

---

## Visual Style

Clean, minimal style suitable for an internal operations tool. All colors are defined in the Color Palette section below — do not use any color not listed there.

- **Typography**: Sans-serif font throughout using `Inter, system-ui, -apple-system, "Segoe UI", Arial, sans-serif`. Card values must be `1.875rem` (`text-3xl`) and bold. Table body text must be `0.9rem` and regular weight.
- **Spacing**: Table cell padding must be exactly `8px` vertical and `12px` horizontal.

---

## Color Palette

Every color used in the dashboard is listed below. Use these exact values — do not substitute, approximate, or invent colors.

### Brand / Custom Colors

- Token: `sidebar-bg` — Hex: `#1E2430` — Usage: Sidebar background
- Token: `sidebar-active-bg` — Hex: `#2B3548` — Usage: Active nav link background; default link hover background
- Token: `sidebar-accent` — Hex: `#4DA3FF` — Usage: Active nav link left border
- Token: `overdue-bg` — Hex: `#FDE2E2` — Usage: Background of "Yes" cells in the Overdue Inspection column
- Token: `overdue-text` — Hex: `#B91C1C` — Usage: Text color of "Yes" cells in the Overdue Inspection column

### Neutral Colors (Tailwind Slate Scale)

- Tailwind class: `bg-white` / `text-white` — Usage: Sidebar text; card backgrounds; table odd row background; pagination button background
- Tailwind class: `bg-slate-50` — Usage: Table even row background; pagination button hover background
- Tailwind class: `bg-slate-100` — Usage: Page background
- Tailwind class: `bg-slate-200` / `border-slate-200` — Usage: Table header background; all border colors (cards, table, pagination footer)
- Tailwind class: `border-slate-300` — Usage: Pagination button border
- Tailwind class: `text-slate-500` — Usage: Card label text
- Tailwind class: `text-slate-600` — Usage: Page subtitle; pagination "Showing X–Y" label
- Tailwind class: `text-slate-700` — Usage: Table header text; table section title; pagination "Page X of Y" text; pagination button text
- Tailwind class: `text-slate-900` — Usage: Body text (default)

---

## Tailwind CSS Class Definitions

Use these exact Tailwind class lists for each element to avoid ambiguity. Do not add or remove classes unless explicitly required in this spec.

### Global

- **Page body**: `min-h-screen bg-slate-100 font-sans text-slate-900`
- **Root layout wrapper**: `flex min-h-screen`

### Sidebar

- **Sidebar container**: `w-64 shrink-0 bg-[#1E2430] text-white`
- **Sidebar product name**: `px-6 py-6 text-lg font-semibold`
- **Sidebar nav container**: `flex flex-col gap-1 px-2`
- **Sidebar link (default)**: `rounded-md px-4 py-2 text-sm text-slate-200 hover:bg-[#2B3548]`
- **Sidebar link (active)**: `flex items-center rounded-md bg-[#2B3548] px-4 py-2 text-sm font-medium border-l-4 border-[#4DA3FF]`

### Main Content

- **Main content container**: `flex-1 p-8`
- **Header container**: `mb-6`
- **Page title**: `text-2xl font-semibold`
- **Subtitle**: `mt-1 text-sm text-slate-600`

### Summary Cards

- **Cards row**: `mb-8 grid gap-4 md:grid-cols-3`
- **Card container**: `rounded-lg border border-slate-200 bg-white p-5`
- **Card label**: `text-xs uppercase tracking-wide text-slate-500`
- **Card value**: `mt-2 text-3xl font-bold`

### Table

- **Table section container**: `rounded-lg border border-slate-200 bg-white`
- **Table section header**: `border-b border-slate-200 px-4 py-3`
- **Table section title**: `text-sm font-semibold text-slate-700` — display the text **"Elevator Fleet"**
- **Table wrapper**: `overflow-x-auto`
- **Table element**: `min-w-full text-left text-sm`
- **Table header row**: `bg-slate-200 text-slate-700`
- **Table header cell**: `px-3 py-2 font-semibold`
- **Table body row (odd)**: `border-b border-slate-200 bg-white`
- **Table body row (even)**: `border-b border-slate-200 bg-slate-50`
- **Table body cell**: `px-3 py-2`

### Overdue Inspection Cell

- **Overdue "Yes" cell**: `bg-[#FDE2E2] text-[#B91C1C]`

### Pagination

- **Pagination footer container**: `flex items-center justify-between border-t border-slate-200 px-4 py-3`
- **Showing label** (left side): `text-sm text-slate-600`
- **Pagination controls wrapper** (right side): `flex items-center gap-3`
- **Previous / Next button**: `rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40`
- **Page indicator** (`Page X of Y`): `text-sm text-slate-700`

