# Methodology Report — Inspection Outcome Prediction Pipeline

---

## 1. Feature Engineering Summary

### Datasets and join key

Three datasets were used, joined on `ElevatingDevicesNumber`:

| Dataset | Rows | Role |
|---|---|---|
| `inspection.csv` | 143,181 | Base table — source of target variable and inspection history |
| `order.csv` | 187,416 | Compliance orders — risk scores and order counts |
| `merged_elevator_data.csv` | 52,339 | Static device attributes — equipment type, device class |

### Features created

**From prior inspection history** :

| Feature | Description |
|---|---|
| `prior_inspection_count` | Total prior inspections for this device |
| `prior_outcome_counts_passed/needs_action` | Count of each binary outcome in prior history |
| `prior_type_counts_*` (7 columns) | Count per cleaned inspection type |
| `days_since_last_inspection` | Days elapsed since the most recent prior inspection |
| `rolling_pass_rate` | Pass rate over the last 5 prior inspections |
| `most_recent_prior_outcome` | Outcome of the immediately preceding inspection |

**From prior compliance orders** (orders with `DateofIssue < inspection_date` only):

| Feature | Description |
|---|---|
| `prior_order_count` | Number of prior compliance orders |
| `prior_avg_risk_score` | Mean RISKSCORE of prior orders (nulls excluded, not imputed) |

**From static device attributes**:
`equipment_type`, `device_class`, `inspection_type_cleaned`

**Derived ratio features**:
`pass_rate`, `needs_action_rate`, `orders_per_inspection`

**Total: 33 features** after encoding and derivation.

### Data leakage prevention

The central constraint throughout the pipeline: for each inspection row with date `t`, only data where `inspection_date < t` (inspections) or `DateofIssue < t` (orders) was used. No current-inspection data, no future data. First inspections for a device receive count features of 0 and sentinel values for date/outcome features (`-1` and `"NO_HISTORY"`). The train/test split is time-based (80/20): the model trains on inspections up to December 2015 and is tested on inspections from December 2015 to January 2017.

---

## 2. TDD Experience

### Tests written

Six tests were written in `test_features.py` before the feature matrix existed:

| Test | What it verifies |
|---|---|
| `test_prior_inspection_count_known_elevator` | Elevator 17489 on 2014-12-04 has exactly 12 prior inspections |
| `test_first_inspection_has_no_prior_features` | Elevator 36600's first inspection has zeros or sentinels for all prior features |
| `test_prior_order_count_no_future_data` | Elevator 17489 on 2014-12-04 has exactly 13 prior orders |
| `test_prior_avg_risk_score_no_future_data` | Average risk score for those 13 orders is 17.923 |
| `test_no_future_orders_in_sample` | For 200 random rows, `prior_order_count` never exceeds true prior count |
| `test_no_future_data_in_prior_count` | For 200 random rows, `prior_inspection_count` never exceeds true prior count |

### Did the tests catch real issues?

Yes. The sampling tests (tests 5 and 6) would have caught any leakage bug in the feature engineering loop. The known-elevator tests provided a fixed regression anchor: if the implementation changes and counts shift, the tests fail immediately.

### How writing tests first affected the workflow

In practice, writing the tests first did not change the way the pipeline was built. The implementation followed its own logic — reading the data, constructing the joins, iterating over inspection rows — without the tests actively guiding each decision. The process felt more like building first and verifying second than the strict red-green cycle that TDD describes in theory.

What the tests did provide was confidence at the end. Once the feature matrix was complete, running the test suite gave a clear answer to a question that would otherwise have required manual spot-checking: did the leakage constraints actually hold across the whole dataset, not just in the cases that were easy to reason about? The sampling tests (tests 5 and 6) in particular covered 200 random rows each, which would have been impractical to verify by hand.

So the honest answer is that TDD here was less about driving design and more about having a documented, automated way to confirm the work was correct when it was done. That is still useful — it just does not match the textbook description of the methodology.

---

## 3. Model Results

**Baseline:** 62.0% — accuracy achieved by always predicting the majority class ("Needs Action").

**Train/test split:** 113,431 rows (2011–2015) for training, 28,358 rows (2015–2017) for testing.

| Model | No feature selection | With SelectKBest (k=25) | vs Baseline |
|---|---|---|---|
| LogisticRegression | 60.2% | 60.1% | −1.8% |
| RandomForest | 58.0% | 58.0% | −3.9% |
| HistGradientBoosting | 60.4% | **60.7%** | −1.2% |

Feature selection (SelectKBest with `mutual_info_classif`, k=25) produced a marginal improvement for HGB (+0.3%) and no meaningful change for LR and RF.

**Best model:** HistGradientBoosting with SelectKBest (k=25), achieving 60.7% at the standard 0.5 threshold. With threshold calibration (predicting "Passed" only when `P(Passed) ≥ 0.70`), accuracy rises to **63.0%**, exceeding the baseline by +1.0%.

HGB outperforms LR and RF because it handles non-linear interactions between features naturally and is robust to the mix of continuous and binary features in this dataset.

**Why no model clearly beats the baseline at the default threshold:** The temporal split creates a distribution shift — devices in the 2015–2017 test period have 4–5 years of inspection history, while the training data includes many devices with shorter histories. Features based on raw cumulative counts (e.g., `prior_inspection_count`) scale with history length and do not transfer perfectly across the two periods. The derived ratio features (`pass_rate`, `needs_action_rate`) reduced this effect but did not eliminate it.

---

## 4. Lessons Learned

**About the spec:** The feature engineering spec did not document that `merged_elevator_data.csv` contains one row per alteration record rather than one row per device. This was discovered mid-implementation when a direct left join multiplied inspection rows by the number of alteration records per device, inflating the dataset. The fix (deduplication before joining) was straightforward, but it caused a bug that had to be diagnosed and corrected. The spec should always document the row granularity of every dataset and any required deduplication before join operations.

**About the pipeline:** Features should be designed for the evaluation period, not just the training period. All features in this pipeline are cumulative counts or averages over prior history — values that grow as a device accumulates inspections over time. A device inspected in 2015 has 4 years of history; a device inspected in 2012 might have 1. When the model trains on 2011–2015 data and is tested on 2015–2017 data, the test set has uniformly longer histories than what the model saw during training, and the learned relationships between count magnitude and outcome do not transfer. The fix is to design ratio features from the start — `pass_rate`, `orders_per_inspection` — rather than adding them later as a correction. If the evaluation will be temporal, features should be normalized by history length before any model is trained.
