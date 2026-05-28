---
name: new-endpoint
description: Adds a new Go API endpoint through a repeatable spec → code → route → build → sample → validate workflow. Pass the endpoint slug and a quoted description as arguments.
user-invocable: true
argument-hint: fleet-stats "Returns aggregate fleet statistics"
---

## AND-104 Task 7: New Endpoint Workflow

Parse `$ARGUMENTS` as two tokens: the first is the **endpoint slug** (e.g., `fleet-stats`), the rest of the string is the **description** (e.g., `"Returns aggregate fleet statistics"`).

Execute the following six steps in order. Do not skip any step.

---

### Step 1 — Write the spec skeleton

**File:** `docs/api_spec.md`

Add the new endpoint inside the `## 5. Task Breakdown` section — that is where all existing endpoints are documented. Append it after the last endpoint subsection already in that section (e.g., after `### GET /api/elevators/{id}/risk`), and before `## 6. Verification Criteria`. Do not add it anywhere else in the file.

The section must include:

- HTTP method and full path (e.g., `### GET /api/fleet/fleet-stats`)
- One-line description from `$ARGUMENTS`
- **Query parameters table** (if any): name, type, default, valid values
- **Success response — 200 OK**: a Markdown table listing every field, its type, and a short note; leave a `<!-- EXAMPLE -->` placeholder where the JSON example will go in Step 5
- **Error responses**: list every possible non-200 status code with its trigger condition and a fenced JSON example
- **Data sources**: list every file in `data/` or `platform/` that the handler will read

Do not summarize or omit fields. The spec is the contract.

---

### Step 2 — Write the Go response struct(s)

**File:** `platform/api/main.go`

Add any new response struct(s) in the `// --- Response types ---` block (around line 49). Follow the existing naming convention: one struct per response shape, field names in PascalCase with `json:"snake_case"` tags. Example:

```go
type fleetStatsResponse struct {
    TotalElevators int            `json:"total_elevators"`
    ByRiskLevel    map[string]int `json:"by_risk_level"`
}
```

Do not add structs anywhere else in the file.

---

### Step 3 — Write the Go handler function

**File:** `platform/api/main.go`

Add the handler function in the `// --- Handlers ---` block (after the last existing handler, before `// --- Helpers ---`). The function signature must be:

```go
func handleXxx(w http.ResponseWriter, r *http.Request) { ... }
```

where `Xxx` is the PascalCase form of the endpoint slug (e.g., `fleet-stats` → `FleetStats`).

Rules:
- Read only from the global variables already loaded at startup: `fleet`, `fleetIndex`, `installed`, `alterations`, `incidents`, `inspByID`, `overdueIDs`, `riskByID`. Do not open any file inside a handler.
- Use `writeJSON(w, http.StatusOK, ...)` for success responses and `writeErr(w, status, msg)` for errors.
- If the handler depends on `riskByID` (predictions), guard with `if riskByID == nil { writeErr(w, http.StatusServiceUnavailable, "predictions not available"); return }`.
- Sort slices explicitly when the spec requires ordering.

---

### Step 4 — Register the route

**File:** `platform/api/main.go`, inside `func main()`, in the `// --- Main ---` block.

Add the new route immediately after the last existing `mux.HandleFunc` line. Use the exact HTTP method and path from Step 1:

```go
mux.HandleFunc("GET /api/fleet/fleet-stats", handleFleetStats)
```

---

### Step 5 — Build, restart, and fill the spec example

Run these commands from `platform/api/`:

```bash
go build -o rocket-elevators-api . && echo "build ok"
```

If the build fails, fix the compile errors before proceeding.

Then restart the server (kill any process on port 8081 first):

```bash
pkill -f rocket-elevators-api 2>/dev/null; sleep 1
DATA_DIR=../../data FLEET_CSV=../elevator_fleet.csv ./rocket-elevators-api &
sleep 2
```

Then run `/sample-endpoint /api/<path>` to get the real JSON example from the live API and replace the `<!-- EXAMPLE -->` placeholder in the spec with the output.

---

### Step 6 — Validate

Run the validation skill for the new endpoint:

```
/validate-api /api/fleet/<slug>
```

If validation fails, fix the discrepancy between the handler output and the spec, then re-build and re-validate until it passes.
