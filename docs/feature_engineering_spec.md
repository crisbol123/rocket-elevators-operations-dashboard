# Feature Engineering Specification
## Inspection Outcome Prediction Pipeline

---

## 1. Outcomes

**What we are predicting:**
Binary classification: will this inspection result in **Passed** or **Needs Action**?

The target variable is the inspection outcome column from `inspection.csv` (~34 raw categories), mapped as follows:

| Cleaned label | Raw outcome values |
|---|---|
| `Passed` | Passed, Passed Major, Passed Sub, All Orders Resolved, Complete, Inspection Complete, Complete Enforcement |
| `Needs Action` | Follow Up (all variants), Shutdown, Vol Shut Down, Fail, Fail Initial, Fail Sub |

**Rows excluded from the training set** (ambiguous, administrative, or data entry errors — not meaningful outcomes):
Unable to Inspect, Incomplete, Not Required, Dismantled, Cancelled, Extend Time to Comply, Undergoing Major Alt, Closed by Program, RC Established, Temp Lic Not Needed, Received, Order Transferred.

**Pipeline deliverable:**
A clean, model-ready feature matrix saved from `intelligence/feature_engineering.ipynb`. Each row is one inspection event with a resolved binary outcome. The matrix is not a trained model — it is the labeled dataset required to train one.

**Baseline score:**
Before any model is trained, calculate the majority-class baseline: the accuracy achieved by always predicting the most frequent class. Any downstream model must beat this score to be considered useful. Report it alongside every model result — a score without a baseline is not informative.

**Quality target:**
- Report class distribution after mapping (expected: reasonably balanced between Passed and Needs Action)
- Report how many rows were excluded and why
- Calculate and document the majority-class baseline in the notebook
- Any downstream model must exceed the baseline accuracy to be considered useful

---

## 2. Scope Boundaries

**Datasets in scope:**
| Dataset | Role |
|---|---|
| `data/inspection.csv` | Base table — one row per inspection event; source of target variable and inspection features |
| `data/order.csv` | Order-level details — compliance directives, risk scores, resolution status per inspection |
| `data/merged_elevator_data.csv` | Static device features — equipment type, device class, location |

**Datasets explicitly out of scope:**
- `data/incident.json`
- `data/altered.json`
- `data/installed.json`
- `data/license.csv`

**Timeframe:** All historical records across all three datasets. No date filter applied.

**Columns to exclude (data leakage or post-outcome fields):**
- The raw target variable column before cleaning (replaced by the cleaned version)
- Any column in `inspection.csv` filled in *after* the inspection result is recorded.
- Orders from the *current* inspection (see Section 3)
- From `merged_elevator_data.csv`: completely empty columns (`Inspection number`, `Alteration contractor name`); redundant duplicate columns (see Section 4)

**Join key:**
`ElevatingDevicesNumber` is consistent across all three datasets and is the primary join key.

---

## 3. Constraints

### Data Leakage Prevention

**Rule:** For each inspection row, features must use only data from *prior* inspections and *prior* orders — never data from the current inspection or any future inspection.

**Definition of "prior":**
> A prior inspection is any inspection for the same `ElevatingDevicesNumber` where `inspection_date < current_inspection_date` (strict less than, date-based).

- Inspection number (`InspectionNumber`) is a system-generated ID and is **not** a reliable chronological sequence — do not use it to define order.
- If two inspections for the same elevator share the same date, neither can see the other. Both use the same historical baseline (all inspections with an earlier date).

**Applies to:**
- All temporal features computed from `inspection.csv`
- All order features computed from `order.csv`: only orders where `DateofIssue < current_inspection_date`

**What this means in practice:**
- For the first inspection ever recorded for a given elevator, all temporal and order features will be null or zero. Document this explicitly in the notebook.
- Temporal features are computed per-elevator, not globally.

---

## 4. Prior Decisions

This pipeline builds on Module 2 ETL work. The following decisions and discoveries must be respected:

### merged_elevator_data.csv — Known Issues

| Issue | Detail | Action |
|---|---|---|
| Completely empty columns | `Inspection number` (52,339 nulls), `Alteration contractor name` (52,339 nulls) | Drop before use |
| Duplicate columns — location | `LocationoftheElevatingDevice` and `Location of Device` | Keep one, drop the other |
| Duplicate columns — owner | `LICENSEHOLDER`, `BILLINGCUSTOMER`, `Owner Name` — same info tripled | Keep one |
| Duplicate columns — address | `LICENSEHOLDERADDRESS`, `BILLINGADDRESS`, `Owner Address` | Keep one |
| Duplicate columns — account | `LICENSEHOLDERACCOUNTNUMBER`, `BILLINGACCOUNT`, `Owner Account Number` | Keep one with better coverage; replace "data redacted" / "redacted" strings with `NaN` |
| Inconsistent column name casing | Mix of ALLCAPS, camelCase, Title Case, lowercase with spaces | Normalize all to `snake_case` |
| Mixed date formats | `LICENSEEXPIRYDATE` → `28-Apr-17`; `first_inspection_date` / `last_inspection_date` → `2015-03-27` | Parse all date columns to `datetime64` |
| "redacted" as string | `LICENSEHOLDERACCOUNTNUMBER`, `BILLINGACCOUNT` contain `"data redacted"` / `"redacted"` | Replace with `NaN` before any analysis |

### Column Name Inconsistencies Across Datasets

| Concept | inspection.csv | order.csv | merged_elevator_data.csv |
|---|---|---|---|
| Device number | `ElevatingDevicesNumber` | `ElevatingDevicesNumber` | `ElevatingDevicesNumber` |
| Inspection number | `InspectionNumber` | `inspectionnumber` | `Inspection number` (null) |
| Inspection type | `InspectionType` | `Inspection_type` | — |

Normalize to a consistent name when joining. `Inspection number` in merged is null and should be dropped.

### Relationships Discovered During ETL

- 47,611 unique inspection numbers appear in `order.csv`; all exist in `inspection.csv`. Zero orphaned orders.
- 95,570 inspections have no orders — these are clean pass inspections or inspections that generated no directives.
- 15,973 devices appear in `inspection.csv` but have no orders.

---

## 5. Task Breakdown

Steps from raw data to final feature matrix, in order:

### Step 1 — Load raw data
- Load `inspection.csv` → `df_inspection`
- Load `order.csv` → `df_order`
- Load `merged_elevator_data.csv` → `df_static`

### Step 2 — Clean merged_elevator_data.csv
- Drop completely empty columns: `Inspection number`, `Alteration contractor name`
- Drop redundant duplicate columns (keep the version with best null coverage for each concept)
- Replace `"data redacted"` / `"redacted"` strings with `NaN`
- Normalize all column names to `snake_case`
- Parse date columns to `datetime64`
- Keep for pipeline: `elevating_devices_number`, `equipment_type`, `device_class`, `location`

### Step 3 — Clean inspection outcome (target variable)
- Inspect and report value counts of the raw outcome column
- Drop rows whose outcome falls in the exclusion list (Unable to Inspect, Incomplete, Not Required, Dismantled, Cancelled, Extend Time to Comply, Undergoing Major Alt, Closed by Program, RC Established, Temp Lic Not Needed, Received, Order Transferred, and identified data entry errors)
- Map remaining values to binary labels: `Passed` / `Needs Action` (see Section 1 mapping table)
- Report row count before and after exclusions, and class distribution of the binary target
- Store as `outcome_binary`

### Step 4 — Clean inspection type (feature)
- Inspect and report value counts of `InspectionType` (29 raw categories)
- Fix typo: merge `"ED-Sub  Inspection"` (double space) into `"ED-Sub Inspection"`
- Map to 7 standardized groups:

| Group | Raw values included |
|---|---|
| `Periodic` | ED-Periodic Inspection |
| `Followup` | ED-Followup Inspection, ED-Followup Minor Alt, ED-Followup Ownership Change, ED-MCP Follow up, ED-FU Enforcement Action Insp, ED-Followup Lic Insp, ED-Followup No-Lic Insp, ED-Followup Reg Non-Compliance, ED-Non-Mandated Followup ON, ED-PWGSC Foll-Up |
| `Alteration` | ED-Minor A Inspection, ED-Minor B Inspection, ED-Sub Inspection Major, ED-Major Alteration Inspection |
| `Sub` | ED-Sub Inspection, ED-Sub Failed Initial |
| `Initial` | ED-Initial Inspection |
| `Unscheduled` | ED-Unscheduled Inspection |
| `Enforcement` | ED-Enforcement Action, ED-MCP Enforcement Insp |

- Drop rows with any remaining unmapped type (ED-Re-Activate Inspection, ED-Inspection Temp Lic, ED-Non-Mandated Insp ON, ED-PWGSC Insp, ED-Perform L1 Incident Insp, ED-Reg Non-Compliance, ED-Perform L1 Near Miss Insp — ~100 rows total, <0.1% of data)
- Report row count before and after
- Store as `inspection_type_cleaned`

### Step 5 — Compute temporal features from prior inspections
For each inspection row `i` with device `d` and date `t`, compute from all inspections where `ElevatingDevicesNumber == d` AND `inspection_date < t`:

| Feature | Description |
|---|---|
| `prior_inspection_count` | Total number of prior inspections |
| `prior_outcome_counts_*` | Count per cleaned outcome category |
| `prior_type_counts_*` | Count per cleaned inspection type |
| `days_since_last_inspection` | Days between `t` and the most recent prior inspection date |
| `rolling_pass_rate` | Pass rate over a chosen window (justify window size in the notebook) |
| `most_recent_prior_outcome` | Outcome of the single most recent prior inspection |

Elevators with no prior inspections: set count-based features to `0`, date-based features to `NaN` (document this).

### Step 6 — Aggregate prior order features
For each inspection row `i` with device `d` and date `t`, compute from all orders where `ElevatingDevicesNumber == d` AND `DateofIssue < t`:

**Missing RISKSCORE handling:**
- 41,553 rows (25.6%) have no `RISKSCORE` — likely older records predating the risk scoring system
- Strategy: exclude nulls from the average (compute mean over non-null values only)
- Rationale: imputing with 0 implies "no risk" when the value is simply unknown; imputing with median introduces a fictitious value across too many records. `prior_order_count` already captures that orders existed, regardless of whether a score was recorded
- Report the count and percentage of missing values in the notebook before applying the strategy


| Feature | Description |
|---|---|
| `prior_order_count` | Total number of prior orders |
| `prior_avg_risk_score` | Average `RISKSCORE` across prior orders |


### Step 7 — Join static features
Left join `df_inspection` with cleaned `df_static` on `ElevatingDevicesNumber`.
Retain: `equipment_type`, `device_class`, `location`.

### Step 8 — Encode dummy variables
Apply one-hot encoding to the following three categorical features:
- `inspection_type_cleaned` (mandatory)
- `equipment_type` (mandatory)
- `device_class` (mandatory)
- Drop the first dummy column per feature to avoid multicollinearity (`drop_first=True`)
- Drop the original columns after encoding

### Step 9 — Final validation (see Section 6)
Run all verification checks before saving.

### Step 10 — Output
Save the final feature matrix. Include the `inspection_date` column (required for time-based operations; not a direct model input — do not encode or impute it).

---

## 6. Verification Criteria

### Data Leakage Tests
- For every row, assert: all prior inspection dates used are strictly `< current inspection_date`
- For every row, assert: all order `DateofIssue` values used are strictly `< current inspection_date`
- Sample 20 random rows and manually verify dates satisfy the constraint
- **Passing:** zero violations in the full dataset assertion

### Missing Values Test
- Assert zero nulls across all feature columns in the final matrix (excluding `inspection_date`)
- Exception: `days_since_last_inspection` and `most_recent_prior_outcome` may be null for elevators with no prior history — document and fill with a sentinel value (e.g., `-1` for days, `"NO_HISTORY"` for outcome), then assert zero nulls again
- **Passing:** `df_final.isnull().sum().sum() == 0` after all fills are applied

### Model Performance Target

**Primary metric:** accuracy — simple and interpretable for an operations audience.

**Target:** beat the majority-class baseline by at least 10 percentage points. If the baseline is 65%, the model must reach at least 75% to be considered useful. A model scoring 66% is barely better than always guessing the most common class.


---
