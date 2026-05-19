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


## AND-102 Task 2

## Data Model

The Elevator is the core entity the dashboard works with. Each record in the joined dataset represents one elevator.

| Field | Type | Source dataset | Source column | Description |
|---|---|---|---|---|
| `elevator_id` | Number | `license.csv` | `ElevatingDevicesNumber` | Unique device identifier |
| `location` | Text | `license.csv` | `LocationoftheElevatingDevice` | Full location of the device |
| `device_type` | Text | `installed.json` | `Device Type` | Category of elevating device |
| `status` | Text | `installed.json` | `DeviceStatus` | Operational state — see enumerated values below |
| `license_number` | Text | `license.csv` | `ElevatingDevicesLicenseNumber` | License identifier; blank if no license record |
| `license_status` | Text | `license.csv` | `LICENSESTATUS` | Current license status — see enumerated values below |
| `license_expiry_date` | Date | `license.csv` | `LICENSEEXPIRYDATE` | Date the license expires; stored as `DD-MMM-YY` |
| `last_inspection_date` | Date | `inspection.csv` | `Latest_INSPECTION_Date` | Date of most recent inspection; stored as `M/D/YYYY` |
| `last_inspection_outcome` | Text | `inspection.csv` | `InspectionOutcome` | Result of most recent inspection — see enumerated values below |

### Enumerated Values

| Field | Known Values |
|---|---|
| `status` | `Active`, `Inactive`, `Customer Shutdown`, `TSSA Shutdown`, `Undergoing Major Alt` |
| `license_status` | `ACTIVE`, `CANCELLED_NOT_RENEWED`, `PENDING_RENEWAL`, `TERMINATED`, `BY REQUEST`, `EXPIRED`, `HOLD_TSD`, `TERMINATED DECEASED`, `CANCELLED_BY_CUST_REQ`, `ENTERED`, `CANCELLED` |
| `last_inspection_outcome` | `Passed`, `Follow up`, `DC Follow up`, `All Orders Resolved`, `Complete`, `Shutdown`, `Follow up Major`, `Follow up Sub Major`, `Follow Up Initial`, `Unable to Inspect`, `Fail Initial`, `Passed Major`, `Incomplete`, `Vol Shut Down`, `Follow up Sub`, `Passed Sub`, `DC Follow up Intial`, `MCP DC Follow up`, `Fail Sub`, `Extend Time to Comply`, `MCP Follow up`, `Undergoing Major Alt`, `Complete Enforcement`, `DC Follow up Sub`, `Not Required`, `Cancelled`, `Dismantled`, `Fail` |
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

### Card 3 — Expireds

- **Label**: "Expireds"
- **Definition**: Count of elevators whose license has expired.
- **Calculation**: Count elevators where `license_expiry_date` is strictly earlier than today, or where there is no license record.

---

## Detail Table

The table must allow the manager to look up any elevator and see its key details. Display one row per elevator. All columns listed below are required; if a value is missing from the source data, display an empty cell rather than inventing a value.

### Columns

| Column | Display rule |
|---|---|
| Elevator ID | Integer, no decimals, no thousand separators |
| Location | Strip everything from the first Canadian postal code pattern (`/[A-Z]\d[A-Z]/`) onwards. Replace the double space separator with `, `. Convert to title case. Example: `111 WELLESLEY ST W  TORONTO M7A 1A2 ON CA` → `111 Wellesley St W, Toronto` |
| City | Text after the double space separator, before the postal code. Convert to title case. Example: `Toronto` |
| License Status | Exact value as stored; do not translate or normalize values |
| License Expiry Date | `YYYY-MM-DD` |
| Expired | "Yes" if `license_expiry_date` is earlier than today; "No" otherwise |

**Date parsing:**
- `LICENSEEXPIRYDATE` in `license.csv` is stored as `DD-MMM-YY`. Two-digit years: treat 00–29 as 2000–2029 and 30–99 as 1930–1999.
- `Latest_INSPECTION_Date` in `inspection.csv` is stored as `M/D/YYYY`.
- Parse all dates before any comparison or display. Display all dates in the dashboard as `YYYY-MM-DD`.

### Table Behavior

- **Default sort**: By Elevator ID ascending.
- **Row count**: Display records paginated — **10 rows per page**. Do not render all rows at once.
- **Pagination controls**: Render a pagination bar below the table with `← Previous` and `Next →` buttons and the current page indicator in the format `Page X of Y`. Disable Previous on the first page and Next on the last page.
- **Total count label**: Show `Showing X–Y of Z elevators` in the pagination bar, updating on every page change.
- **Row shading**: Alternate between white and `bg-slate-50/50`. Add `hover:bg-blue-50/30` on row hover.
- **Header row**: `bg-slate-100`, semibold, `text-slate-600`. Bottom border separates header from body.
- **Empty state**: If no rows match the active filters, show a single centered message: "No elevators match the selected filters."

## AND-102 Task 3

### Filtering

All filters render inside the table fragment above the table. A filter change resets the page to 1 and returns a new fragment. Filter state is preserved across sort and pagination interactions.

| Filter | Type | Options |
|---|---|---|
| License Status | Dropdown | All Statuses / Active (`ACTIVE`) / Pending Renewal (`PENDING_RENEWAL`) |
| Expired | Button group | All / Valid (not expired) / Expired (expiry date < today) |

### Sorting

Sortable columns are clickable headers. Clicking a column sorts ascending; clicking the same column again reverses to descending. A `↑` / `↓` indicator shows the active sort direction; `↕` marks unsorted columns. Sort state is preserved across filter and pagination interactions.

| Column | Default direction |
|---|---|
| Elevator ID | Ascending |
| Expiry Date | Ascending |

### State Management

All interactive state (`status`, `expired`, `sort_by`, `sort_dir`, `page`) is carried as query parameters on every request to `GET /fragments/table`. No client-side JavaScript manages state. Hidden `<input>` elements inside the fragment hold current values; `hx-include` collects them on each interaction; `hx-vals` overrides only the value being changed. The server always receives the full state and returns a fully rendered fragment.

---

## Visual Style

Clean, minimal style suitable for an internal operations tool.

- **Typography**: `Inter, system-ui, -apple-system, "Segoe UI", Arial, sans-serif`. Card values: `text-3xl font-bold`. Table body: `text-sm` (`0.875rem`). Elevator ID and dates: `font-mono`.
- **Spacing**: Table cell padding `px-5 py-3`.
- **Cards**: `rounded-xl border border-slate-200 bg-white shadow-sm` with a `border-t-4` color accent — blue (`#4DA3FF`) for Total, emerald for Active, red for Expired. Card value text is color-coded to match the accent.
- **Sidebar**: Add an `Operations` subtitle below the brand name. Nav links include a small SVG icon to the left of the label.
- **Header**: Title and subtitle on the left.
- **Table section header**: Shows title plus a subtitle with total record count and active filter description.
- **License Status badge**: Colored pill (`rounded-full`, `text-xs font-medium`) — `ACTIVE` → emerald, `PENDING_RENEWAL` → amber, all others → slate.
- **Expired badge**: Colored pill — `Yes` → red, `No` → emerald.
- **Row hover**: `hover:bg-slate-50 transition-colors` on every row.

---

## Color Palette

Every color used in the dashboard is listed below. Use these exact values — do not substitute, approximate, or invent colors.

### Brand / Custom Colors

- Token: `sidebar-bg` — Hex: `#1E2430` — Usage: Sidebar background
- Token: `sidebar-active-bg` — Hex: `#2B3548` — Usage: Active nav link background; default link hover background
- Token: `sidebar-accent` — Hex: `#4DA3FF` — Usage: Active nav link left border
- Token: `overdue-bg` — Hex: `#FDE2E2` — Usage: Background of "Yes" cells in the Expired column
- Token: `overdue-text` — Hex: `#B91C1C` — Usage: Text color of "Yes" cells in the Expired column

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

### Expired Cell

- **Expired "Yes" cell**: `bg-[#FDE2E2] text-[#B91C1C]`

### Pagination

- **Pagination footer container**: `flex items-center justify-between border-t border-slate-200 px-4 py-3`
- **Showing label** (left side): `text-sm text-slate-600`
- **Pagination controls wrapper** (right side): `flex items-center gap-3`
- **Previous / Next button**: `rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40`
- **Page indicator** (`Page X of Y`): `text-sm text-slate-700`

---

## AND-103 Task 1

## Interaction Specification

---

### Interaction 1 — Elevator Detail Panel

#### 1. Outcomes

When a user clicks any row in the elevator table, a detail panel slides in from the right showing the full record for that elevator. The panel contains:

- **Header:** Elevator ID (monospace, large), device type, and current status badge.
- **Basic info section:** License number, license status badge, license expiry date, location (full untruncated string).
- **Inspection history section:** A list of all inspections for that elevator, sorted by date descending. Each row shows: inspection date (`YYYY-MM-DD`), inspection type, and outcome. If no inspections exist, show "No inspection records found."
- **Alterations section:** Total count of alteration records for that elevator. If the count is zero, show "No alterations on record."
- **Incidents section:** Total count of incident records for that elevator. If the count is zero, show "No incidents on record."

The panel remains visible until the user explicitly closes it. Clicking a different row while the panel is open replaces the panel content with the new elevator's data without closing and reopening the panel.

#### 2. Scope Boundaries

**In scope:**
- Rendering the panel and all its sections as described above.
- Updating the panel in place when a different row is clicked.
- Closing the panel via a close button.
- Highlighting the active row (the one whose data is currently shown in the panel).

**Out of scope:**
- Editing any field from within the panel.
- Deep-linking to a specific elevator panel via URL.
- Showing paginated inspection history (all inspection records are listed without pagination).
- Closing the panel by clicking outside it or pressing Escape.

#### 3. Constraints

- The panel sits alongside the table in the main content area. The table does not resize or reflow when the panel opens or closes.
- The panel has a fixed width of 384 px. On viewports narrower than 768 px the panel is not required to work; this is an internal desktop tool.
- The panel does not affect filter, sort, or pagination state. Those interactions remain fully independent of the panel.
- All inspection records for the elevator are shown in the panel without pagination.
- Data sources for each section (resolved — see Prior Decisions): basic info and license data from the main fleet dataset; inspection history from `inspection.csv`; alteration count from `altered.json`; incident count from `incident.json`.

#### 4. Prior Decisions

- **Data source strategy:** Individual source files (`inspection.csv`, `incident.json`, `altered.json`) are used for the panel instead of `merged_elevator_data.csv`. The merged file is denormalized (one row per alteration, ~52 k rows) and contains only aggregated inspection data, making it unsuitable for listing individual inspection records or reliably counting incidents per elevator.
- **Panel is independent of table state:** Changing filters, sorting, or paginating the table does not close or refresh the panel. The panel shows the last clicked elevator until the user explicitly closes it or clicks a different row.
- **Active-row highlight via OOB swap:** When the server responds to a row click, it returns the panel content as the primary swap (into `#detail-panel`) and includes an out-of-band fragment tagged `hx-swap-oob="true"` that updates the table rows — removing the highlight from the previously active row and applying it to the newly clicked one. This keeps highlight state server-driven without requiring a separate JavaScript handler.

#### 5. Task Breakdown

1. Define the panel layout: header strip (Elevator ID, device type, status badge), then four stacked sections (Basic Info, Inspection History, Alterations, Incidents) each with a section label and its content.
2. Define the trigger: clicking a table row opens the panel with that elevator's data. The click target is the full row, not a specific cell.
3. Define the update behavior: if the panel is already open and the user clicks a different row, the panel content is replaced in place — the panel does not close and reopen.
4. Define the close behavior: an ✕ button in the top-right corner of the panel closes it. The active-row highlight is removed when the panel closes.
5. Define active-row highlighting: the row whose elevator is currently displayed in the panel gets a distinct left border accent. Only one row is highlighted at a time.
6. Define the empty state for the panel target: before any row is clicked, the panel area is empty and takes no space in the layout.

#### 6. Verification Criteria

- Clicking any row opens the panel and displays correct data for that elevator across all five sections.
- The inspection list is sorted newest-first.
- Clicking a second row while the panel is open replaces the panel content without the panel closing or flickering.
- The ✕ button closes the panel and removes the active-row highlight from the table.
- After opening or closing the panel, the table's filter, sort, and pagination state are unchanged.
- If an elevator has no inspection records, the Inspection History section shows "No inspection records found."
- If an elevator has no alteration records, the Alterations section shows "No alterations on record."
- If an elevator has no incident records, the Incidents section shows "No incidents on record."
- Before any row is clicked, no panel is visible and the table occupies its full width.

---

### Interaction 2 — Filter and Search

#### 1. Outcomes

A search input is added to the filter bar above the table. As the user types, the table updates to show only elevators that match the query against **Elevator ID** (prefix match) or **Location** (case-insensitive substring match). The search operates simultaneously with the existing License Status dropdown and Expired button group — all active constraints apply together (AND logic). Clearing the search field returns the table to the state defined by the active dropdown and button filters alone. The table resets to page 1 on every search change.

The rest of the dashboard responds as follows:
- The summary cards (Total, Active, Expireds) are **not** affected by search — they always reflect the full fleet.
- The "Showing X–Y of Z elevators" label updates to reflect the combined filter + search result count.
- If the detail panel is open when the user types a search, the panel remains visible and unchanged — it shows the last clicked elevator regardless of whether that elevator is still in the filtered table.
- The active sort column and direction are preserved across search changes.

#### 2. Scope Boundaries

**In scope:**
- A single text search input matching against Elevator ID and Location.
- AND combination with the existing License Status and Expired filters.
- Resetting to page 1 on every new search query.
- Preserving active sort column and direction while searching.
- Updating the "Showing X–Y of Z" count to reflect combined results.
- Empty-state message when no rows match.

**Out of scope:**
- Searching against any field other than Elevator ID and Location.
- Fuzzy or phonetic matching.
- Highlighting matched text within cells.
- Search suggestions or autocomplete.
- Saving or recalling recent searches.
- Affecting the summary cards.

#### 3. Constraints

- The table updates after the user pauses typing, not on every keystroke. The debounce delay is 300 ms.
- Elevator ID match rule: the query must be a prefix of the Elevator ID. For example, `"10"` matches IDs `10`, `100`, and `1001`, but not `210`.
- Location match rule: case-insensitive substring match against the full untruncated location string (not the display-truncated version shown in the table).
- An empty search query means no search constraint is active; only the dropdown and button filters apply.
- Maximum search query length: 100 characters. Input beyond that length is ignored.
- Search state is preserved when the user changes the License Status filter, the Expired filter, the sort column, or navigates between pages.

#### 4. Prior Decisions

- **AND logic for combined filters:** The most operationally useful default. A manager filtering for `ACTIVE` licenses and then typing a location substring expects both constraints to hold simultaneously — narrowing the result, not replacing it.
- **Summary cards are excluded from search:** The cards represent fleet-wide KPIs. Filtering them by search query would make them contextual metrics, which is a different feature. They remain full-fleet aggregates.
- **Panel independence from search:** The detail panel shows a specific elevator's record. Closing or refreshing the panel when the user searches would break the user's workflow (comparing an elevator's detail while scanning filtered results). The panel stays until the user explicitly closes it.
- **State via query params** (established in Task 3): the search query travels as a param on every table request alongside filter and sort state, so that paginating or sorting preserves the active search.

#### 5. Task Breakdown

1. Define search input placement: positioned in the filter bar to the left of the existing License Status dropdown, spanning a fixed width that does not crowd the other controls.
2. Define the match rules as specified in Constraints: prefix on Elevator ID, substring on Location.
3. Define the combination logic: search is applied after the existing dropdown and button filters — rows must satisfy all active constraints simultaneously.
4. Define the debounce: the table does not request new results until 300 ms after the user stops typing.
5. Define page reset: any change to the search query resets the table to page 1.
6. Define sort preservation: the active sort column and direction are carried unchanged when the search changes.
7. Define the "Showing X–Y of Z" label: Z reflects the total count of rows matching the combined filter + search, not the full fleet count.
8. Define the empty state: if the combined result set is zero rows, the table body shows the single centered message "No elevators match the selected filters." (same message used when filters alone produce zero results).

#### 6. Verification Criteria

- Typing `"10"` in the search box shows only elevators whose Elevator ID starts with `10` or whose full location string contains `"10"` (case-insensitive).
- With License Status set to `ACTIVE` and search set to `"toronto"`, only `ACTIVE` elevators whose location contains `"toronto"` are shown.
- Clearing the search field returns the table to the result set defined by the active dropdown and button filters alone.
- The summary cards show the same values before and after searching.
- The "Showing X–Y of Z" label reflects the combined filter + search count, not the total fleet count.
- Active sort column and direction are unchanged after typing a search query.
- The page resets to 1 when the search query changes.
- Paginating through search results keeps the search query active.
- When combined filter + search yields zero rows, the empty-state message appears.
- If the detail panel is open while the user types a search, the panel remains visible and its content does not change.

---

### Interaction 3 — Sort Behavior

#### 1. Outcomes

Two table columns are sortable: **Elevator ID** and **Expiry Date**. The default state on every page load is Elevator ID ascending. Clicking a sortable column header sorts the table by that column; clicking the same header again reverses the direction. Switching to a different column always starts ascending. Only one column is sorted at a time.

Every sortable column header displays a direction indicator at all times:
- **↑** — this column is the active sort, ascending.
- **↓** — this column is the active sort, descending.
- **↕** — this column is sortable but not currently active.

Non-sortable columns (Location, City, License Status, Expired) have no indicator and are not clickable for sorting.

Sort state is preserved when the user changes the License Status filter, the Expired filter, the search query, or navigates between pages. The page resets to 1 whenever the sort column or direction changes.

The rest of the dashboard responds as follows:
- The summary cards are not affected by sort.
- If the detail panel is open when the user changes the sort, the panel remains visible and unchanged.
- The "Showing X–Y of Z" label updates to reflect the new page slice, but Z (total count) does not change from a sort alone.

#### 2. Scope Boundaries

**In scope:**
- Sorting by Elevator ID (numeric) and Expiry Date (date).
- Toggle ascending / descending by clicking the active column header.
- Switching to a different column resets direction to ascending.
- Visual indicators on all sortable column headers.
- Sort preserved across filter, search, and pagination interactions.
- Page reset to 1 on every sort change.

**Out of scope:**
- Multi-column sorting.
- Sorting by Location, City, License Status, or Expired.
- Persisting sort preference across browser sessions or page reloads.
- Keyboard-triggered column sorting.

#### 3. Constraints

- Sort is always single-column. Activating a new column discards any previous sort.
- Elevators with no expiry date sort last in both ascending and descending directions on the Expiry Date column.
- Elevator ID is sorted numerically, not lexicographically (e.g., ID `9` sorts after `8`, not after `89`).
- If `sort_by` or `sort_dir` are absent from a request, the table defaults to Elevator ID ascending.
- Sort state is carried on every table request alongside filter, search, and pagination state so that no interaction silently resets it.

#### 4. Prior Decisions

- **Sortable columns limited to Elevator ID and Expiry Date** (established in Task 3): these are the two columns most relevant to the operations manager's core workflows — locating a specific elevator by ID and identifying licenses approaching expiry.
- **Direction resets to ascending on column switch:** switching columns is a new sort intent, not a continuation of the previous one. Starting ascending is the natural reading direction and avoids surprising the user with a descending sort they did not ask for.
- **Page resets to 1 on sort change:** the row ordering changes, making the current page offset meaningless. Staying on page 3 after a sort change would show a disorienting mid-set slice.
- **State via query params** (established in Task 3): sort state travels as `sort_by` and `sort_dir` params on every request, keeping the server stateless and allowing any interaction to carry the full state forward.

#### 5. Task Breakdown

1. Define the default state: on page load with no explicit sort params, the table renders sorted by Elevator ID ascending, with ↑ on the Elevator ID header and ↕ on the Expiry Date header.
2. Define the click behavior for the active column: if the user clicks the column already sorted, the direction toggles. The next request carries the same `sort_by` and the opposite `sort_dir`.
3. Define the click behavior for an inactive sortable column: the next request carries the new `sort_by` and `sort_dir=asc`, regardless of the previous sort direction.
4. Define null handling for Expiry Date: rows with no expiry date appear after all dated rows in both ascending and descending sorts.
5. Define indicator rendering: each sortable header reads the current `sort_by` and `sort_dir` from the fragment state and renders the correct indicator (↑, ↓, or ↕).
6. Define sort preservation: filter, search, and pagination requests must carry the current `sort_by` and `sort_dir` values so that sorting is not lost when the user changes another control.

#### 6. Verification Criteria

- On page load, the table is sorted by Elevator ID ascending and the Elevator ID header shows ↑; the Expiry Date header shows ↕.
- Clicking the Elevator ID header while it shows ↑ re-sorts descending (↓) and reorders the rows.
- Clicking the Expiry Date header while Elevator ID is active sorts by expiry date ascending, shows ↑ on Expiry Date and ↕ on Elevator ID.
- Clicking the Expiry Date header again reverses to descending (↓).
- Elevators with no expiry date appear last when sorted by Expiry Date in either direction.
- Changing the License Status filter, the Expired filter, or the search query does not reset the sort column or direction.
- Paginating does not reset the sort column or direction.
- The page resets to 1 every time the sort column or direction changes.
- Non-sortable column headers (Location, City, License Status, Expired) show no indicator and produce no sort on click.
- If the detail panel is open when the sort changes, the panel remains visible and its content does not change.

