## AND-105 Task 5: Writer/Reviewer Code Review

**Scope:** Go database layer — `platform/api/main.go`, `platform/api/db.go`  
**Review methods:** Reviewer session (worktree), fan-out (`claude -p`), `/code-review`, `/security-review`  
**Sessions:** Writer session: `db-writer` · Reviewer session: `db-reviewer` (worktree, isolated)

---

## CRITICAL

None. No SQL injection vulnerabilities found. The only string interpolation in SQL (`orderCol` / `sortDir` in `handleListElevators:182`) is safe — both values are derived from a Go-side whitelist map, not from raw user input.

---

## WARNINGS

### W1 — `context.Background()` in all handlers (pool exhaustion risk)
**File:** `main.go:185, 234, 279, 325, 360, 420`  
**Found by:** Reviewer session, fan-out (`main.go`), fan-out (`db.go` — health check)  
**Severity:** High  

Every handler passes `context.Background()` to every `db.Query` and `db.QueryRow` call. This means if a client disconnects mid-request, the in-flight query continues running and holds a pool connection until the DB responds. With `MaxConns = 10`, sustained traffic with slow queries can exhaust the pool.

**Fix:** Replace `ctx := context.Background()` with `ctx := r.Context()` inside every handler. The `handleHealth` function in `db.go:45` is fine using `context.Background()`.

**Status: Fixed in this commit.**

---

### W2 — Scan errors silently dropped in `handleFleetStats`
**File:** `main.go:369, 378, 384, 406`  
**Found by:** Reviewer session, /code-review, fan-out (`main.go`)  
**Severity:** Medium  

Four `QueryRow().Scan()` calls discard their errors. On DB failure: `totalElevators` returns 0, risk level counts accumulate garbage, and `passRate` defaults to 0.0 — all without any error response to the client.

---

### W3 — Scan error ignored in `handleGetRisk` prediction count check
**File:** `main.go:344`  
**Found by:** Reviewer session, /code-review, fan-out (`main.go`)  
**Severity:** Medium  

`db.QueryRow(ctx, "SELECT COUNT(*) FROM predictions").Scan(&count)` error is dropped. A failed query leaves `count == 0` and returns a misleading 503 "predictions not available" instead of a database error.

---

### W4 — Hardcoded fallback credentials in `db.go`
**File:** `db.go:20-21`  
**Found by:** fan-out (`db.go`), fan-out (`main.go`), /security-review, /code-review  
**Severity:** Medium (security)  

`getenv("POSTGRES_PASSWORD", "rocket_pass")` silently falls back to a hardcoded password with no log warning, no startup error. An operator deploying to staging without env vars would never know.

---

### W5 — `sslmode=disable` on database connection
**File:** `db.go:16`  
**Found by:** fan-out (`db.go`), fan-out (`main.go`), /security-review  
**Severity:** Medium (security)  

All traffic between the API and PostgreSQL is plaintext. Acceptable inside a single Docker network; a credential-exposure risk if the DB is on a different host or network segment.

---

### W6 — Missing `rows.Err()` check after `rows.Next()` loops
**File:** `main.go:206, 315, 467`  
**Found by:** fan-out (`main.go`), /code-review  
**Severity:** Medium  

If iteration ends due to a network error (not EOF), `rows.Err()` returns non-nil but is never checked. Partial result sets are silently returned as if complete in `handleListElevators`, `handleGetInspections`, and `handleFleetAlerts`.

---

## SUGGESTIONS

### S1 — No server-side error logging
**File:** `main.go` (all handlers)  
**Found by:** Reviewer session  

When `writeErr(w, http.StatusInternalServerError, ...)` is called, the actual `err` value is discarded. A `log.Printf("handler error: %v", err)` before each `writeErr` would make production debugging possible.

### S2 — TOCTOU race in `handleGetInspections` / `handleGetRisk`
**File:** `main.go:280-290, 326-337`  
**Found by:** Reviewer session  

Both handlers call `elevatorExists()` then issue the main query in two separate round-trips. If an elevator is deleted between the two calls, `handleGetInspections` returns HTTP 200 with `[]` instead of 404, and `handleGetRisk` returns a confusing 503. `handleGetElevator` handles this correctly with a single query — the same pattern should apply here.

### S3 — No `MaxConnLifetime` / `MaxConnIdleTime` on pool
**File:** `db.go:28`  
**Found by:** fan-out (`main.go`)  

Pool only sets `MaxConns = 10`. Stale connections after a DB restart or network blip are never proactively evicted.

### S4 — Fragile `sortDir` interpolation pattern
**File:** `main.go:182`  
**Found by:** fan-out (`db.go`)  

`sortDir` is a user-supplied string that is interpolated into SQL after whitelist validation. The whitelist and the interpolation are coupled by convention only. Using a code-defined map (`map[string]string{"asc": "ASC", "desc": "DESC"}`) would make the pattern injection-proof by construction, not by discipline.

### S5 — Two open rowsets held simultaneously in `handleFleetStats`
**File:** `main.go:374, 401`  
**Found by:** Reviewer session  

`riskRows` and `typeRows` are both deferred — both pool connections are held open together for the tail of the function. Closing `riskRows` explicitly before opening `typeRows` would reduce pool pressure.

---

## VERDICT

The database integration is **solid for a first implementation**. No SQL injection vulnerabilities exist. Connection pooling is configured, parameterized queries are used correctly throughout, and the health endpoint verifies live connectivity.

The main reliability risk is **W1** (context propagation) — the only issue that could cause resource exhaustion under real load. The correctness issues (W2, W3, W6) would surface as misleading error responses on DB failure, not data corruption. The security issues (W4, W5) are deployment-configuration concerns that matter before any non-local environment.

**Fixed in this commit:** W1 — `context.Background()` replaced with `r.Context()` in all six handlers.
