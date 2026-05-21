# AND-103 Task 5
import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Fixture: load the feature matrix produced by feature_engineering.ipynb
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def feature_matrix() -> pd.DataFrame:
    """Load the final feature matrix. Assumes the notebook has been run and
    the output saved to intelligence/feature_matrix.csv."""
    return pd.read_csv("data/feature_matrix.csv", parse_dates=["inspection_date"])


# ---------------------------------------------------------------------------
# Test 1: Prior-inspection count is correct for a known elevator
#
# Elevator 17489, inspection 5102083 (2014-12-04).
# Manual count from inspection.csv: 12 prior inspections with date < 2014-12-04.
# ---------------------------------------------------------------------------

KNOWN_ELEVATOR = 17489
KNOWN_INSPECTION = 5102083
KNOWN_DATE = pd.Timestamp("2014-12-04")
EXPECTED_PRIOR_COUNT = 12


def test_prior_inspection_count_known_elevator(feature_matrix: pd.DataFrame) -> None:
    row = feature_matrix[feature_matrix["InspectionNumber"] == KNOWN_INSPECTION]
    assert len(row) == 1, f"Inspection {KNOWN_INSPECTION} not found in feature matrix"
    actual = row.iloc[0]["prior_inspection_count"]
    assert actual == EXPECTED_PRIOR_COUNT, (
        f"Elevator {KNOWN_ELEVATOR} on {KNOWN_DATE.date()}: "
        f"expected {EXPECTED_PRIOR_COUNT} prior inspections, got {actual}"
    )


# ---------------------------------------------------------------------------
# Test 2: First-ever inspection has zero or NaN for all prior-inspection features
#
# Elevator 36600, inspection 2289392 (2011-01-04).
# No inspections exist before this date — all prior-inspection aggregate
# features must be 0 or NaN.
# ---------------------------------------------------------------------------

FIRST_ELEVATOR = 36600
FIRST_INSPECTION = 2289392

PRIOR_AGGREGATE_FEATURES = [
    "prior_inspection_count",
    "prior_outcome_counts_passed",
    "prior_outcome_counts_needs_action",
    "days_since_last_inspection",
    "rolling_pass_rate",
    "most_recent_prior_outcome",
    "prior_order_count",
    "prior_avg_risk_score",
]

# Sentinel values used by the pipeline for "no prior history"
NO_HISTORY_SENTINELS = {0, 0.0, -1, -1.0, "NO_HISTORY"}


def test_first_inspection_has_no_prior_features(feature_matrix: pd.DataFrame) -> None:
    row = feature_matrix[feature_matrix["InspectionNumber"] == FIRST_INSPECTION]
    assert len(row) == 1, f"Inspection {FIRST_INSPECTION} not found in feature matrix"
    r = row.iloc[0]

    failures = []
    for col in PRIOR_AGGREGATE_FEATURES:
        if col not in feature_matrix.columns:
            continue
        val = r[col]
        is_zero_or_null = pd.isna(val) or val in NO_HISTORY_SENTINELS
        if not is_zero_or_null:
            failures.append(f"  {col} = {val!r} (expected 0, -1, NaN, or NO_HISTORY)")

    assert not failures, (
        f"Elevator {FIRST_ELEVATOR} first inspection {FIRST_INSPECTION} "
        f"has non-zero prior features:\n" + "\n".join(failures)
    )


# ---------------------------------------------------------------------------
# Test 3: No future information — order features use only data before inspection_date
#
# Elevator 17489, inspection 5102083 (2014-12-04).
# Manual count from order.csv: 17 prior orders with DateofIssue < 2014-12-04.
# Avg RISKSCORE (non-null) of those orders: 14.5625
# 18 future orders exist on or after 2014-12-04 — none should appear in features.
# ---------------------------------------------------------------------------

EXPECTED_PRIOR_ORDER_COUNT = 13   # 13 orders with valid DateofIssue < 2014-12-04; rest are NaT
EXPECTED_PRIOR_AVG_RISK = 17.923  # mean of 13 non-null RISKSCORE values


def test_prior_order_count_no_future_data(feature_matrix: pd.DataFrame) -> None:
    row = feature_matrix[feature_matrix["InspectionNumber"] == KNOWN_INSPECTION]
    assert len(row) == 1, f"Inspection {KNOWN_INSPECTION} not found in feature matrix"
    actual_count = row.iloc[0]["prior_order_count"]
    assert actual_count == EXPECTED_PRIOR_ORDER_COUNT, (
        f"Elevator {KNOWN_ELEVATOR} on {KNOWN_DATE.date()}: "
        f"expected {EXPECTED_PRIOR_ORDER_COUNT} prior orders, got {actual_count}"
    )


def test_prior_avg_risk_score_no_future_data(feature_matrix: pd.DataFrame) -> None:
    row = feature_matrix[feature_matrix["InspectionNumber"] == KNOWN_INSPECTION]
    assert len(row) == 1, f"Inspection {KNOWN_INSPECTION} not found in feature matrix"
    actual_avg = row.iloc[0]["prior_avg_risk_score"]
    assert abs(actual_avg - EXPECTED_PRIOR_AVG_RISK) < 0.01, (
        f"Elevator {KNOWN_ELEVATOR} on {KNOWN_DATE.date()}: "
        f"expected avg risk score {EXPECTED_PRIOR_AVG_RISK}, got {actual_avg}"
    )


def test_no_future_orders_in_sample(feature_matrix: pd.DataFrame) -> None:
    """For a random sample of rows, assert prior_order_count never exceeds
    the true count of orders with DateofIssue strictly before inspection_date."""
    orders = pd.read_csv("data/order.csv")
    orders["DateofIssue"] = pd.to_datetime(orders["DateofIssue"], format="mixed")

    sample = feature_matrix.dropna(subset=["prior_order_count"]).sample(
        min(200, len(feature_matrix)), random_state=42
    )

    violations = []
    for _, row in sample.iterrows():
        device = row["ElevatingDevicesNumber"]
        date = row["inspection_date"]
        true_prior = orders[
            (orders["ElevatingDevicesNumber"] == device)
            & (orders["DateofIssue"] < date)
        ]
        if row["prior_order_count"] > len(true_prior):
            violations.append(
                f"  InspectionNumber={row['InspectionNumber']}: "
                f"feature says {row['prior_order_count']} prior orders, "
                f"true count is {len(true_prior)}"
            )

    assert not violations, "Future orders leaked into prior_order_count:\n" + "\n".join(violations)


def test_no_future_data_in_prior_count(feature_matrix: pd.DataFrame) -> None:
    """For every row, prior_inspection_count must not exceed the number of
    inspections that actually existed before that row's inspection_date."""
    inspection = pd.read_csv(
        "data/inspection.csv",
        parse_dates=["Earliest_INSPECTION_Date"],
    )

    violations = []
    sample = feature_matrix.dropna(subset=["prior_inspection_count"]).sample(
        min(200, len(feature_matrix)), random_state=42
    )

    for _, row in sample.iterrows():
        device = row["ElevatingDevicesNumber"]
        date = row["inspection_date"]
        true_prior = inspection[
            (inspection["ElevatingDevicesNumber"] == device)
            & (inspection["Earliest_INSPECTION_Date"] < date)
        ]
        if row["prior_inspection_count"] > len(true_prior):
            violations.append(
                f"InspectionNumber={row['InspectionNumber']}: "
                f"feature says {row['prior_inspection_count']} priors, "
                f"true count is {len(true_prior)}"
            )

    assert not violations, "Future data leaked into prior_inspection_count:\n" + "\n".join(violations)
