 ## AND-104 Task 2: API Specification

# REST API Specification — Rocket Elevators Go Backend

---

## 1. Outcomes

This API enables external clients to consume elevator fleet data as structured JSON. A developer building a mobile app, a third-party integration, or a future frontend replacement must be able to:

- List the full elevator fleet with filtering and pagination
- Retrieve complete details for a single elevator
- Retrieve the inspection history for a specific elevator
- Retrieve the predicted risk score for a specific elevator

The Go service is a pure data API. It does not render HTML and has no dependency on the Python dashboard server.

---

## 2. Scope Boundaries

**In scope:**
- Four read-only JSON endpoints defined in this document
- Pagination and filtering on the list endpoint
- Structured error responses for all failure cases

**Out of scope:**
- HTML rendering of any kind
- Authentication or authorization
- Write operations (POST, PUT, DELETE)
- The Python dashboard server (`platform/server.py`) — it remains unchanged
- Serving static assets

---

## 3. Constraints and Assumptions

- The Go server reads data files directly from `data/` at startup and holds them in memory
- Elevator IDs are integers (`ElevatingDevicesNumber` in the source files)
- All dates in responses are ISO 8601 strings (`YYYY-MM-DD`)
- `data/predictions.csv` does not exist at the time this spec is written — the risk endpoint has a forward dependency on Task 6, which generates this file
- A request for a valid elevator ID that has no inspections returns an empty array, not a 404
- The overdue rule mirrors the Python server: an elevator is overdue if its most recent inspection date is more than 365 days before today

---

## 4. Prior Decisions

- Field names in API responses follow the normalized names already in `platform/elevator_fleet.csv` (e.g., `elevator_id`, `location`, `city`, `license_status`), not the raw CSV column names from `data/license.csv`
- `installed.json` is the source for `device_type` and `device_status`; these fields may be absent if an elevator has no installed record
- `alteration_count` and `incident_count` are integer counts derived from `altered.json` and `incident.json` respectively — raw alteration and incident records are not exposed by this API
- The inspection overdue calculation is already established in `platform/server.py:46-48` and must produce the same result

### Data Source Mapping

| Response field | Source file | Source column |
|---|---|---|
| elevator_id | platform/elevator_fleet.csv | elevator_id |
| location | platform/elevator_fleet.csv | location |
| city | platform/elevator_fleet.csv | city |
| license_number | platform/elevator_fleet.csv | license_number |
| license_status | platform/elevator_fleet.csv | license_status |
| license_expiry_date | platform/elevator_fleet.csv | license_expiry_date |
| device_type | data/installed.json | Device Type |
| device_status | data/installed.json | DeviceStatus |
| alteration_count | data/altered.json | count where Elevating Devices Number = id |
| incident_count | data/incident.json | count where elevating devices number = id |
| inspection_id | data/inspection.csv | InspectionNumber |
| type | data/inspection.csv | InspectionType |
| date | data/inspection.csv | Latest_INSPECTION_Date |
| outcome | data/inspection.csv | InspectionOutcome |
| inspection location | data/inspection.csv | InspectionLocation |
| risk_score | data/predictions.csv | risk_score (forward dependency — Task 6) |
| risk_level | derived | computed from risk_score thresholds |
| predicted_at | data/predictions.csv | prediction_date (forward dependency — Task 6) |

---

## 5. Task Breakdown

### GET /api/elevators

Returns a paginated list of elevators with optional filters.

**Query parameters:**

| Parameter | Type | Default | Valid values |
|---|---|---|---|
| page | integer | 1 | ≥ 1 |
| status | string | all | all, ACTIVE, PENDING_RENEWAL, BY_REQUEST |
| expired | string | all | all, yes, no |
| inspection | string | all | all, overdue, ok |
| search_id | string | "" | partial match prefix on elevator_id |
| search_location | string | "" | case-insensitive substring match on location |
| sort_by | string | elevator_id | elevator_id, license_expiry_date |
| sort_dir | string | asc | asc, desc |

**Success response — 200 OK:**

| Field | Type |
|---|---|
| data | array of objects |
| data[].elevator_id | integer |
| data[].location | string |
| data[].city | string |
| data[].license_status | string |
| data[].license_expiry_date | string (YYYY-MM-DD) |
| data[].is_overdue | boolean |
| total | integer |
| page | integer |
| total_pages | integer |

#### Example Response

```json
{
  "data": [
    {
      "elevator_id": 10,
      "location": "111 Wellesley St W, Toronto",
      "city": "Toronto",
      "license_status": "ACTIVE",
      "license_expiry_date": "2017-04-28",
      "is_overdue": false
    }
  ],
  "total": 38284,
  "page": 1,
  "total_pages": 1915
}
```

**Error responses:**

- `400 Bad Request` — `status` or `expired` value is not in the allowed set, or `page`/`per_page` is not a positive integer

```json
{ "error": "invalid value for parameter 'status': 'UNKNOWN'" }
```

**Data sources:** `platform/elevator_fleet.csv`, `data/inspection.csv`

---

### GET /api/elevators/{id}

Returns full details for a single elevator, combining license, device, and summary count data.

**Path parameter:** `id` — integer elevator ID

**Success response — 200 OK:**

| Field | Type |
|---|---|
| elevator_id | integer |
| location | string |
| city | string |
| license_number | string |
| license_status | string |
| license_expiry_date | string (YYYY-MM-DD) |
| device_type | string |
| device_status | string |
| alteration_count | integer |
| incident_count | integer |
| is_overdue | boolean |

#### Example Response

```json
{
  "elevator_id": 10,
  "location": "111 Wellesley St W, Toronto",
  "city": "Toronto",
  "license_number": "EDLIC-000010",
  "license_status": "ACTIVE",
  "license_expiry_date": "2017-04-28",
  "device_type": "Passenger Elevator",
  "device_status": "Active",
  "alteration_count": 2,
  "incident_count": 0,
  "is_overdue": false
}
```

**Error responses:**

- `400 Bad Request` — `id` is not a valid integer

```json
{ "error": "elevator id must be an integer" }
```

- `404 Not Found` — no elevator exists with that ID

```json
{ "error": "elevator 99999 not found" }
```

**Data sources:** `platform/elevator_fleet.csv`, `data/installed.json`, `data/altered.json`, `data/incident.json`, `data/inspection.csv`

---

### GET /api/elevators/{id}/inspections

Returns the full inspection history for a specific elevator, sorted by date descending.

**Path parameter:** `id` — integer elevator ID

**Success response — 200 OK:**

| Field | Type |
|---|---|
| [].inspection_id | integer |
| [].type | string |
| [].date | string (YYYY-MM-DD) |
| [].outcome | string |
| [].location | string |

#### Example Response

```json
[
  {
    "inspection_id": 5312245,
    "type": "ED-Major Alteration Inspection",
    "date": "2015-01-22",
    "outcome": "Follow up Major",
    "location": "111 Wellesley St W, Toronto"
  },
  {
    "inspection_id": 5248292,
    "type": "ED-Periodic Inspection",
    "date": "2015-01-22",
    "outcome": "Complete",
    "location": "111 Wellesley St W, Toronto"
  },
  {
    "inspection_id": 4184747,
    "type": "ED-Followup Inspection",
    "date": "2013-01-10",
    "outcome": "Passed",
    "location": "111 Wellesley St W, Toronto"
  }
]
```

An elevator with no inspections returns an empty array `[]`, not a 404.

**Error responses:**

- `400 Bad Request` — `id` is not a valid integer

```json
{ "error": "elevator id must be an integer" }
```

- `404 Not Found` — no elevator exists with that ID

```json
{ "error": "elevator 99999 not found" }
```

**Data sources:** `data/inspection.csv`

---

### GET /api/elevators/{id}/risk

Returns the predicted risk score for a specific elevator.

**Forward dependency:** This endpoint depends on `data/predictions.csv`, which is generated in Task 6. Until that file exists, the endpoint returns 503.

**Path parameter:** `id` — integer elevator ID

**Success response — 200 OK:**

| Field | Type |
|---|---|
| elevator_id | integer |
| risk_score | float |
| risk_level | string (low, medium, high) |
| predicted_at | string (YYYY-MM-DD) |

#### Example Response

```json
{
  "elevator_id": 10,
  "risk_score": 0.73,
  "risk_level": "high",
  "predicted_at": "2026-05-26"
}
```

`risk_level` is derived from `risk_score` using these thresholds:
- `low`: score < 0.4
- `medium`: 0.4 ≤ score < 0.7
- `high`: score ≥ 0.7

**Error responses:**

- `400 Bad Request` — `id` is not a valid integer

```json
{ "error": "elevator id must be an integer" }
```

- `404 Not Found` — elevator ID exists in the fleet but has no prediction record, or the elevator itself does not exist

```json
{ "error": "no risk prediction found for elevator 10" }
```

- `503 Service Unavailable` — `data/predictions.csv` does not exist (Task 6 has not run yet)

```json
{ "error": "predictions not available" }
```

**Data sources:** `data/predictions.csv` (forward dependency — Task 6)

---

## 6. Verification Criteria

- `GET /api/elevators` returns `Content-Type: application/json` and a valid paginated envelope
- `GET /api/elevators?status=ACTIVE` returns only rows where `license_status` is `ACTIVE`
- `GET /api/elevators?expired=yes` returns only elevators whose `license_expiry_date` is in the past
- `GET /api/elevators?status=INVALID` returns 400 with an error message
- `GET /api/elevators/10` returns the correct fields for elevator 10 and matches data in `elevator_fleet.csv` and `installed.json`
- `GET /api/elevators/99999` returns 404
- `GET /api/elevators/abc` returns 400
- `GET /api/elevators/10/inspections` returns results sorted by date descending
- `GET /api/elevators/10/inspections` for an elevator with no inspections returns `[]`
- `GET /api/elevators/10/risk` returns 503 when `data/predictions.csv` does not exist
- `GET /api/elevators/10/risk` returns a valid risk object after Task 6 generates `predictions.csv`

