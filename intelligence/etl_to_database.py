## AND-105 Task 3: Data Migration — ETL from flat files to PostgreSQL

import json
import logging
import os
import re
import time
from pathlib import Path

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"
MIGRATIONS = ROOT / "platform" / "api" / "migrations" / "001_initial_schema.sql"


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

def get_connection() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "rocket_elevators"),
        user=os.getenv("POSTGRES_USER", "rocket_user"),
        password=os.getenv("POSTGRES_PASSWORD", "rocket_pass"),
    )


# ---------------------------------------------------------------------------
# Schema bootstrap
# ---------------------------------------------------------------------------

def run_migrations(conn: psycopg2.extensions.connection) -> None:
    sql = MIGRATIONS.read_text()
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
    log.info("Schema ready (migrations applied)")


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def parse_date(value: str | None) -> str | None:
    """Return ISO date string or None for any empty / unparseable value."""
    if not value or not isinstance(value, str) or value.strip() == "":
        return None
    value = value.strip()
    for fmt in ("%d-%b-%y", "%m/%d/%Y", "%Y-%m-%d"):
        try:
            return pd.to_datetime(value, format=fmt).date().isoformat()
        except (ValueError, TypeError):
            pass
    try:
        return pd.to_datetime(value).date().isoformat()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Location helpers (same logic as prepare_data.py)
# ---------------------------------------------------------------------------

def fmt_location(s: str | None) -> str | None:
    if not s or not isinstance(s, str):
        return None
    match = re.search(r"[A-Z]\d[A-Z]", s)
    trimmed = s[: match.start()].strip() if match else s.strip()
    parts = re.split(r"  +", trimmed)
    result = ", ".join(p.title() for p in parts)
    return result or None


def extract_city(s: str | None) -> str | None:
    if not s or not isinstance(s, str):
        return None
    match = re.search(r"[A-Z]\d[A-Z]", s)
    trimmed = s[: match.start()].strip() if match else s.strip()
    parts = re.split(r"  +", trimmed)
    raw = parts[-1] if len(parts) > 1 else (trimmed.split()[-1] if trimmed else "")
    return raw.title() or None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fetch_valid_elevator_ids(conn: psycopg2.extensions.connection) -> set[int]:
    with conn.cursor() as cur:
        cur.execute("SELECT elevator_id FROM elevators")
        return {row[0] for row in cur.fetchall()}


# ---------------------------------------------------------------------------
# Table loaders
# ---------------------------------------------------------------------------

def load_elevators(conn: psycopg2.extensions.connection) -> tuple[int, int]:
    log.info("Loading elevators …")

    license_df = pd.read_csv(DATA / "license.csv", dtype=str)

    with open(DATA / "installed.json") as f:
        installed_raw = json.load(f)
    installed = {
        int(r["Elevating devices number"]): {
            "device_type": r.get("Device Type"),
            "device_status": r.get("DeviceStatus"),
        }
        for r in installed_raw
        if str(r.get("Elevating devices number", "")).strip().isdigit()
    }

    rows = []
    skipped = 0
    for _, row in license_df.iterrows():
        raw_id = str(row.get("ElevatingDevicesNumber", "")).strip()
        if not raw_id.isdigit():
            log.warning("elevators: skipping row — invalid elevator_id %r", raw_id)
            skipped += 1
            continue

        elevator_id = int(raw_id)
        raw_loc = row.get("LocationoftheElevatingDevice")
        device = installed.get(elevator_id, {})

        rows.append((
            elevator_id,
            fmt_location(raw_loc),
            extract_city(raw_loc),
            row.get("ElevatingDevicesLicenseNumber") or None,
            row.get("LICENSESTATUS") or None,
            parse_date(row.get("LICENSEEXPIRYDATE")),
            row.get("LICENSEHOLDER") or None,
            device.get("device_type"),
            device.get("device_status"),
        ))

    sql = """
        INSERT INTO elevators
            (elevator_id, location, city, license_number, license_status,
             license_expiry_date, license_holder, device_type, device_status)
        VALUES %s
        ON CONFLICT (elevator_id) DO NOTHING
    """
    with conn.cursor() as cur:
        execute_values(cur, sql, rows)
    conn.commit()

    inserted = len(rows) - skipped
    log.info("elevators: %d inserted, %d skipped", inserted, skipped)
    return inserted, skipped


def load_inspections(conn: psycopg2.extensions.connection) -> tuple[int, int]:
    log.info("Loading inspections …")

    valid_ids = fetch_valid_elevator_ids(conn)
    df = pd.read_csv(DATA / "inspection.csv", dtype=str)

    rows = []
    skipped = 0
    for _, row in df.iterrows():
        raw_num = str(row.get("InspectionNumber", "")).strip()
        if not raw_num.isdigit():
            log.warning("inspections: skipping row — invalid InspectionNumber %r", raw_num)
            skipped += 1
            continue

        raw_date = row.get("Latest_INSPECTION_Date")
        parsed_date = parse_date(raw_date)
        if not parsed_date:
            log.warning("inspections: skipping %s — unparseable date %r", raw_num, raw_date)
            skipped += 1
            continue

        raw_elevator = str(row.get("ElevatingDevicesNumber", "")).strip()
        elevator_id = int(raw_elevator) if raw_elevator.isdigit() and int(raw_elevator) in valid_ids else None

        outcome = row.get("InspectionOutcome") or None
        if not outcome:
            log.warning("inspections: skipping %s — missing outcome", raw_num)
            skipped += 1
            continue

        rows.append((
            int(raw_num),
            elevator_id,
            row.get("InspectionType") or None,
            parsed_date,
            outcome,
            fmt_location(row.get("InspectionLocation")),
        ))

    sql = """
        INSERT INTO inspections
            (inspection_number, elevator_id, inspection_type,
             latest_inspection_date, outcome, location)
        VALUES %s
        ON CONFLICT (inspection_number) DO NOTHING
    """
    with conn.cursor() as cur:
        execute_values(cur, sql, rows)
    conn.commit()

    log.info("inspections: %d inserted, %d skipped", len(rows), skipped)
    return len(rows), skipped


def load_incidents(conn: psycopg2.extensions.connection) -> tuple[int, int]:
    log.info("Loading incidents …")

    valid_ids = fetch_valid_elevator_ids(conn)
    with open(DATA / "incident.json") as f:
        raw = json.load(f)

    rows = []
    skipped = 0
    for record in raw:
        incident_number = str(record.get("Incident Number", "")).strip()
        if not incident_number:
            log.warning("incidents: skipping row — missing Incident Number")
            skipped += 1
            continue

        raw_elevator = str(record.get("elevating devices number", "")).strip()
        elevator_id = int(raw_elevator) if raw_elevator.isdigit() and int(raw_elevator) in valid_ids else None

        rows.append((
            incident_number,
            elevator_id,
            parse_date(record.get("Date Of Occurrence")),
            record.get("catagory of incident") or None,
            record.get("Specific Root Cause") or None,
            record.get("Reported occurrence narrative") or None,
        ))

    sql = """
        INSERT INTO incidents
            (incident_number, elevator_id, date_of_occurrence,
             category, root_cause, narrative)
        VALUES %s
        ON CONFLICT (incident_number) DO NOTHING
    """
    with conn.cursor() as cur:
        execute_values(cur, sql, rows)
    conn.commit()

    log.info("incidents: %d inserted, %d skipped", len(rows), skipped)
    return len(rows), skipped


def load_alterations(conn: psycopg2.extensions.connection) -> tuple[int, int]:
    log.info("Loading alterations …")

    valid_ids = fetch_valid_elevator_ids(conn)
    with open(DATA / "altered.json") as f:
        raw = json.load(f)

    rows = []
    skipped = 0
    for record in raw:
        raw_num = str(record.get("originating service request number", "")).strip()
        if not raw_num.isdigit():
            log.warning("alterations: skipping row — invalid service_request_number %r", raw_num)
            skipped += 1
            continue

        raw_elevator = str(record.get("Elevating Devices Number", "")).strip()
        elevator_id = int(raw_elevator) if raw_elevator.isdigit() and int(raw_elevator) in valid_ids else None

        rows.append((
            int(raw_num),
            elevator_id,
            record.get("Alteration Type") or None,
            record.get("Status of Alteration Request") or None,
            record.get("Summary") or None,
        ))

    sql = """
        INSERT INTO alterations
            (service_request_number, elevator_id, alteration_type, status, summary)
        VALUES %s
        ON CONFLICT (service_request_number) DO NOTHING
    """
    with conn.cursor() as cur:
        execute_values(cur, sql, rows)
    conn.commit()

    log.info("alterations: %d inserted, %d skipped", len(rows), skipped)
    return len(rows), skipped


def load_predictions(conn: psycopg2.extensions.connection) -> tuple[int, int]:
    log.info("Loading predictions …")

    valid_ids = fetch_valid_elevator_ids(conn)
    df = pd.read_csv(DATA / "predictions.csv", dtype=str)

    rows = []
    skipped = 0
    for _, row in df.iterrows():
        raw_id = str(row.get("elevator_id", "")).strip()
        if not raw_id.isdigit() or int(raw_id) not in valid_ids:
            log.warning("predictions: skipping row — elevator_id %r not in elevators", raw_id)
            skipped += 1
            continue

        try:
            risk_score = float(row.get("risk_score", ""))
        except (ValueError, TypeError):
            log.warning("predictions: skipping %s — invalid risk_score", raw_id)
            skipped += 1
            continue

        parsed_date = parse_date(row.get("prediction_date"))
        if not parsed_date:
            log.warning("predictions: skipping %s — unparseable prediction_date", raw_id)
            skipped += 1
            continue

        rows.append((
            int(raw_id),
            round(risk_score, 4),
            row.get("risk_level") or None,
            row.get("model_version") or None,
            parsed_date,
            None,  # risk_explanation — populated in Task 6
        ))

    sql = """
        INSERT INTO predictions
            (elevator_id, risk_score, risk_level, model_version,
             prediction_date, risk_explanation)
        VALUES %s
        ON CONFLICT (elevator_id) DO NOTHING
    """
    with conn.cursor() as cur:
        execute_values(cur, sql, rows)
    conn.commit()

    log.info("predictions: %d inserted, %d skipped", len(rows), skipped)
    return len(rows), skipped


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def verify(conn: psycopg2.extensions.connection) -> None:
    checks = [
        ("elevators",   "SELECT COUNT(*) FROM elevators"),
        ("elevators with device_type",  "SELECT COUNT(*) FROM elevators WHERE device_type IS NOT NULL"),
        ("elevators with city",         "SELECT COUNT(*) FROM elevators WHERE city IS NOT NULL"),
        ("inspections", "SELECT COUNT(*) FROM inspections"),
        ("inspections with DATE type",  "SELECT COUNT(*) FROM inspections WHERE latest_inspection_date IS NOT NULL"),
        ("incidents",   "SELECT COUNT(*) FROM incidents"),
        ("alterations", "SELECT COUNT(*) FROM alterations"),
        ("predictions", "SELECT COUNT(*) FROM predictions"),
        ("predictions risk levels",     "SELECT risk_level, COUNT(*) FROM predictions GROUP BY risk_level ORDER BY risk_level"),
    ]

    print("\n── Verification ───────────────────────────────")
    with conn.cursor() as cur:
        for label, query in checks:
            cur.execute(query)
            rows = cur.fetchall()
            if len(rows) == 1:
                print(f"  {label:<35} {rows[0][0]:>10,}")
            else:
                print(f"  {label}:")
                for row in rows:
                    print(f"    {row[0]:<12} {row[1]:>10,}")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    start = time.time()
    log.info("Connecting to PostgreSQL …")
    conn = get_connection()

    run_migrations(conn)

    results: dict[str, tuple[int, int]] = {}
    results["elevators"]   = load_elevators(conn)
    results["inspections"] = load_inspections(conn)
    results["incidents"]   = load_incidents(conn)
    results["alterations"] = load_alterations(conn)
    results["predictions"] = load_predictions(conn)

    elapsed = time.time() - start

    print("\n── Migration Summary ──────────────────────────")
    print(f"{'Table':<16} {'Inserted':>10} {'Skipped':>10}")
    print("─" * 40)
    total_inserted = total_skipped = 0
    for table, (inserted, skipped) in results.items():
        print(f"{table:<16} {inserted:>10,} {skipped:>10,}")
        total_inserted += inserted
        total_skipped += skipped
    print("─" * 40)
    print(f"{'TOTAL':<16} {total_inserted:>10,} {total_skipped:>10,}")
    print(f"\nCompleted in {elapsed:.1f}s")

    verify(conn)
    conn.close()


if __name__ == "__main__":
    main()
