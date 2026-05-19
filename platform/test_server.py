# AND-103 Task 2 Part A & B — Automated tests for the operations dashboard server
import re

import pytest
from fastapi.testclient import TestClient

from server import app, load_data

# ---------------------------------------------------------------------------
# Fixture: one TestClient per test session, data loaded once.
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def _load() -> None:
    """Load elevator_fleet.csv into the module-level DataFrame before any test."""
    load_data()


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

# Elevator ID 8 exists in the fleet and has inspection records in inspection.csv.
# 999999 is guaranteed not to exist in the dataset.
KNOWN_ID = 8
UNKNOWN_ID = 999999


def _elevator_ids(html: str) -> list[int]:
    """Extract elevator IDs from font-mono table cells in the HTML fragment."""
    return [int(v) for v in re.findall(r'class="px-5 py-3 font-mono text-slate-500">(\d+)', html)]


# ---------------------------------------------------------------------------
# Test 1 — Main page loads successfully
# ---------------------------------------------------------------------------

def test_dashboard_returns_200(client: TestClient) -> None:
    """GET / must return HTTP 200 and include aggregate summary stats."""
    response = client.get("/")

    assert response.status_code == 200

    html = response.text
    # The dashboard renders three stat cards; each embeds a formatted integer.
    # Verify that at least one large number (≥ 5 digits) appears — proof the DataFrame was loaded and the template rendered correctly.
    assert re.search(r"\d{2,3},\d{3}", html), (
        "Expected a formatted total count (e.g. '43,297') in the dashboard HTML"
    )


# ---------------------------------------------------------------------------
# Test 2 — Status filter returns only rows matching the filter value
# ---------------------------------------------------------------------------

def test_filter_by_pending_renewal_returns_only_pending_rows(client: TestClient) -> None:
    """Filtering by PENDING_RENEWAL must exclude every ACTIVE badge from the table body."""
    response = client.get("/fragments/table", params={"status": "PENDING_RENEWAL"})

    assert response.status_code == 200

    html = response.text

    # The PENDING_RENEWAL badge renders the text "Pending Renewal" inside an amber span.
    # The ACTIVE badge renders the text "Active" inside an emerald span with class text-emerald-700.
    # The dropdown option also contains ">Active<" so we match the full closing tag ">Active</span>"
    # to target only the status badge, not the <option> element.
    assert "Pending Renewal" in html, "Expected 'Pending Renewal' badges in filtered results"
    assert ">Active</span>" not in html, (
        "Found an 'Active' status badge in a PENDING_RENEWAL-filtered response — "
        "the filter is not being applied correctly"
    )

    # Also verify the result count matches the known PENDING_RENEWAL total (632).
    assert "632" in html, (
        "Expected the result count '632' to appear in the fragment when filtering "
        "by PENDING_RENEWAL"
    )


# ---------------------------------------------------------------------------
# Test 3 — Sorting by elevator_id descending returns rows in correct order
# ---------------------------------------------------------------------------

def test_sort_elevator_id_descending(client: TestClient) -> None:
    """Sorting by elevator_id desc must return the first page with IDs in descending order."""
    response = client.get(
        "/fragments/table",
        params={"sort_by": "elevator_id", "sort_dir": "desc"},
    )

    assert response.status_code == 200

    ids = _elevator_ids(response.text)
    assert len(ids) > 0, "No elevator ID cells found in the sorted fragment"
    assert ids == sorted(ids, reverse=True), (
        f"Elevator IDs are not in descending order: {ids}"
    )


# ---------------------------------------------------------------------------
# AND-103 Task 2 Part B — TDD for GET /elevator/{id} (detail endpoint)
# These tests are written BEFORE the endpoint exists; they drive the implementation.
# ---------------------------------------------------------------------------

def test_detail_known_id_returns_200_with_elevator_data(client: TestClient) -> None:
    """GET /elevator/{id} for a known ID must return HTTP 200 and show that elevator's data."""
    response = client.get(f"/elevator/{KNOWN_ID}")

    assert response.status_code == 200

    html = response.text
    # The elevator ID itself must appear somewhere in the rendered page.
    assert str(KNOWN_ID) in html, (
        f"Expected elevator ID '{KNOWN_ID}' to appear in the detail page HTML"
    )
    # The page must also show the license status for this elevator.
    assert "ACTIVE" in html or "PENDING_RENEWAL" in html, (
        "Expected a license status value in the detail page HTML"
    )


def test_detail_unknown_id_returns_404(client: TestClient) -> None:
    """GET /elevator/{id} for a non-existent ID must return HTTP 404."""
    response = client.get(f"/elevator/{UNKNOWN_ID}")

    assert response.status_code == 404


def test_detail_includes_inspection_history(client: TestClient) -> None:
    """GET /elevator/{id} must include at least one inspection record with date, type, and outcome."""
    response = client.get(f"/elevator/{KNOWN_ID}")

    assert response.status_code == 200

    html = response.text
    # Verify the three required fields are present in the inspection history section.
    # Elevator 8 has inspections with types like "ED-Followup Inspection" and
    # outcomes like "Passed" and "Follow up".
    assert "Inspection" in html, (
        "Expected inspection type to appear in the detail page HTML"
    )
    assert "Passed" in html or "Follow up" in html, (
        "Expected an inspection outcome ('Passed' or 'Follow up') in the detail page HTML"
    )
    # Dates are stored as MM/DD/YYYY — verify at least one year appears.
    assert re.search(r"\d{4}", html), (
        "Expected an inspection date (containing a 4-digit year) in the detail page HTML"
    )
