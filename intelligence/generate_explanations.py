"""
## AND-105 Task 7: Batch Generation and Storage

Generate risk explanations for high-risk elevators and store them in the predictions table.
Incremental: only processes high-risk elevators whose risk_explanation is still NULL, so
re-running picks up where it left off instead of regenerating everything.
Model: llama3.1:8b-instruct-q8_0 via Ollama.
System prompt: SYSTEM_FINAL from risk_explanations.ipynb (Task 6).
"""
from __future__ import annotations

import os
import sys
import time
import requests
import psycopg2
import psycopg2.extras
from datetime import timedelta

DB = dict(
    host=os.getenv("POSTGRES_HOST", "localhost"),
    port=int(os.getenv("POSTGRES_PORT", "5432")),
    dbname=os.getenv("POSTGRES_DB", "rocket_elevators"),
    user=os.getenv("POSTGRES_USER", "rocket_user"),
    password=os.getenv("POSTGRES_PASSWORD", "rocket_pass"),
)
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.1:8b-instruct-q8_0"

# SYSTEM_FINAL — post-Reviewer version from Task 6 (risk_explanations.ipynb)
# Uses {score} placeholder replaced per elevator before calling the model.
SYSTEM_FINAL = """You are a data analyst summarizing elevator risk indicators for compliance review.
Risk scores range from 0.0 (no risk) to 1.0 (critical). Scores above 0.85 indicate imminent compliance action.

Write 1-3 sentences summarizing the key risk indicators for this elevator based on its score of {score}.
Use only as many sentences as the data supports. Do not repeat or rephrase facts to meet a length requirement.

Rules:
- Begin with the actual score value: "With a risk score of {score}..."
- Cite specific counts, pass rates, and dates where present. Omit any category for which no value is available.
- Do not write any number, date, or count that does not appear verbatim in the data. Do not round, estimate, or approximate.
- Do not reference regulatory sections, clauses, or legal obligations not present in the data.
- Output only the explanation. No headers, no bullet points."""


def build_prompt(score: float) -> str:
    score_str = f"{score:.4f}"
    return SYSTEM_FINAL.replace("{score}", score_str)


def elevator_to_text(e: dict) -> str:
    pct = f"{e['pass_rate_pct']}%" if e["pass_rate_pct"] is not None else "unknown"
    lines = [
        f"Elevator ID: {e['elevator_id']}",
        f"Location: {e['location']}, {e['city']}",
        f"Equipment type: {e['equipment_type']}",
        f"License status: {e['license_status']}",
        f"Risk score: {e['risk_score']:.4f} ({e['risk_level']} risk)",
        "",
        "Inspection outcome summary (all time):",
        f"  Total: {e['total_inspections']}  |  Passed: {e['passed_count']}  |  Needs Action: {e['needs_action_count']}  |  Pass rate: {pct}",
        "",
        "Last 5 inspections (most recent first):",
    ]
    if e["inspections"]:
        for insp in e["inspections"]:
            lines.append(f"  - {insp['date']} | {insp['inspection_type']} | outcome: {insp['outcome']}")
    else:
        lines.append("  - No inspection records")

    lines.append("")
    lines.append("Incidents (most recent 2 years of dataset):")
    if e["incidents"]:
        for inc in e["incidents"]:
            lines.append(f"  - {inc['date']} | {inc['category']} | {inc['root_cause']}")
    else:
        lines.append("  - None")

    lines.append("")
    lines.append("Recent alterations:")
    if e["alterations"]:
        for alt in e["alterations"][:3]:
            lines.append(f"  - {alt['alteration_type']} | status: {alt['status']}")
    else:
        lines.append("  - None")

    return "\n".join(lines)


def call_ollama(system_prompt: str, user_message: str, timeout: int = 120) -> str:
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "stream": False,
            "options": {"temperature": 0.2},
        },
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()["message"]["content"].strip()


def generate_with_retry(system_prompt: str, user_message: str) -> str | None:
    for attempt in range(2):
        try:
            return call_ollama(system_prompt, user_message)
        except requests.exceptions.Timeout:
            if attempt == 0:
                print("    Timeout — retrying once...")
            else:
                print("    Timeout on retry — skipping.")
                return None
        except Exception as exc:
            print(f"    API error: {exc} — skipping.")
            return None
    return None


def load_context(
    cur: psycopg2.extras.RealDictCursor,
    ids: list[int],
    two_years_ago: str,
) -> tuple[dict, dict, dict, dict]:
    cur.execute(
        """
        SELECT
            elevator_id,
            COUNT(*)                                           AS total_inspections,
            COUNT(*) FILTER (WHERE outcome = 'Passed')        AS passed_count,
            COUNT(*) FILTER (WHERE outcome != 'Passed')       AS needs_action_count,
            ROUND(
                COUNT(*) FILTER (WHERE outcome = 'Passed')::numeric
                / NULLIF(COUNT(*), 0) * 100, 1
            )                                                  AS pass_rate_pct
        FROM inspections
        WHERE elevator_id = ANY(%s)
        GROUP BY elevator_id
        """,
        (ids,),
    )
    outcome_stats = {r["elevator_id"]: dict(r) for r in cur.fetchall()}

    cur.execute(
        """
        SELECT elevator_id,
               COALESCE(inspection_type, 'Unknown') AS inspection_type,
               latest_inspection_date::text         AS date,
               outcome,
               ROW_NUMBER() OVER (
                   PARTITION BY elevator_id ORDER BY latest_inspection_date DESC
               ) AS rn
        FROM inspections
        WHERE elevator_id = ANY(%s)
        """,
        (ids,),
    )
    inspections_by_id: dict[int, list] = {i: [] for i in ids}
    for row in cur.fetchall():
        if row["rn"] <= 5:
            inspections_by_id[row["elevator_id"]].append(dict(row))

    cur.execute(
        """
        SELECT elevator_id,
               COALESCE(category, 'Unknown') AS category,
               date_of_occurrence::text      AS date,
               COALESCE(root_cause, '')      AS root_cause
        FROM incidents
        WHERE elevator_id = ANY(%s)
          AND date_of_occurrence >= %s
        """,
        (ids, two_years_ago),
    )
    incidents_by_id: dict[int, list] = {i: [] for i in ids}
    for row in cur.fetchall():
        incidents_by_id[row["elevator_id"]].append(dict(row))

    cur.execute(
        """
        SELECT elevator_id,
               COALESCE(alteration_type, 'Unknown') AS alteration_type,
               COALESCE(status, '')                 AS status
        FROM alterations
        WHERE elevator_id = ANY(%s)
        """,
        (ids,),
    )
    alterations_by_id: dict[int, list] = {i: [] for i in ids}
    for row in cur.fetchall():
        alterations_by_id[row["elevator_id"]].append(dict(row))

    return outcome_stats, inspections_by_id, incidents_by_id, alterations_by_id


def main() -> None:
    conn = psycopg2.connect(**DB)
    print("Connected to database")

    with conn.cursor() as cur:
        cur.execute("SELECT MAX(date_of_occurrence) FROM incidents")
        max_date = cur.fetchone()[0]
    two_years_ago = (max_date - timedelta(days=730)).strftime("%Y-%m-%d")
    print(f"Incident window: {two_years_ago} → {max_date}")

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT
                e.elevator_id,
                COALESCE(e.location, 'Unknown')    AS location,
                COALESCE(e.city, 'Unknown')        AS city,
                e.license_status,
                COALESCE(e.device_type, 'Unknown') AS equipment_type,
                p.risk_score,
                p.risk_level
            FROM predictions p
            JOIN elevators e ON e.elevator_id = p.elevator_id
            WHERE p.risk_level = 'high'
              AND p.risk_explanation IS NULL
            ORDER BY p.risk_score DESC
            """
        )
        base_rows = [dict(r) for r in cur.fetchall()]

    total = len(base_rows)
    print(f"Found {total} high-risk elevators without an explanation")

    if total == 0:
        print("Nothing to process — all high-risk elevators already explained.")
        conn.close()
        return

    ids = [e["elevator_id"] for e in base_rows]

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        outcome_stats, inspections_by_id, incidents_by_id, alterations_by_id = load_context(
            cur, ids, two_years_ago
        )

    elevators = []
    for e in base_rows:
        eid = e["elevator_id"]
        stats = outcome_stats.get(eid, {})
        elevators.append(
            {
                **e,
                "total_inspections": stats.get("total_inspections", 0),
                "passed_count": stats.get("passed_count", 0),
                "needs_action_count": stats.get("needs_action_count", 0),
                "pass_rate_pct": stats.get("pass_rate_pct", None),
                "inspections": inspections_by_id[eid],
                "incidents": incidents_by_id[eid],
                "alterations": alterations_by_id[eid],
            }
        )

    generated = 0
    failures: list[int] = []
    explanation_lengths: list[int] = []
    total_start = time.monotonic()

    for idx, e in enumerate(elevators, start=1):
        eid = e["elevator_id"]
        print(f"Processing elevator {idx}/{total} (ID {eid})...")

        system_prompt = build_prompt(e["risk_score"])
        user_message = elevator_to_text(e)

        t0 = time.monotonic()
        explanation = generate_with_retry(system_prompt, user_message)
        elapsed = time.monotonic() - t0

        if explanation is None:
            print(f"    Failed — skipping elevator {eid}")
            failures.append(eid)
            continue

        with conn.cursor() as cur:
            cur.execute(
                "UPDATE predictions SET risk_explanation = %s WHERE elevator_id = %s",
                (explanation, eid),
            )
        conn.commit()

        generated += 1
        explanation_lengths.append(len(explanation))
        print(f"    Done in {elapsed:.1f}s — {len(explanation)} chars")

    total_elapsed = time.monotonic() - total_start

    print("\n--- Summary ---")
    print(f"Total high-risk elevators:  {total}")
    print(f"Explanations generated:     {generated}")
    print(f"Failures:                   {len(failures)}")
    if failures:
        print(f"Failed elevator IDs:        {failures}")
    if explanation_lengths:
        avg_len = sum(explanation_lengths) / len(explanation_lengths)
        print(f"Avg explanation length:     {avg_len:.0f} chars")
    print(f"Total elapsed time:         {total_elapsed:.1f}s")

    conn.close()


if __name__ == "__main__":
    main()
