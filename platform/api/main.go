// AND-105 Task 4: Go Database Integration

package main

import (
	"context"
	"encoding/json"
	"fmt"
	"math"
	"net/http"
	"os"
	"strconv"

	"github.com/jackc/pgx/v5"
)

// --- Response types ---

type listItem struct {
	ElevatorID        int    `json:"elevator_id"`
	Location          string `json:"location"`
	City              string `json:"city"`
	LicenseStatus     string `json:"license_status"`
	LicenseExpiryDate string `json:"license_expiry_date"`
	IsOverdue         bool   `json:"is_overdue"`
	RiskLevel         string `json:"risk_level"`
}

type listResponse struct {
	Data       []listItem `json:"data"`
	Total      int        `json:"total"`
	Page       int        `json:"page"`
	TotalPages int        `json:"total_pages"`
}

type detailResponse struct {
	ElevatorID        int    `json:"elevator_id"`
	Location          string `json:"location"`
	City              string `json:"city"`
	LicenseNumber     string `json:"license_number"`
	LicenseStatus     string `json:"license_status"`
	LicenseExpiryDate string `json:"license_expiry_date"`
	DeviceType        string `json:"device_type"`
	DeviceStatus      string `json:"device_status"`
	AlterationCount   int    `json:"alteration_count"`
	IncidentCount     int    `json:"incident_count"`
	IsOverdue         bool   `json:"is_overdue"`
}

type inspectionResponse struct {
	InspectionID int    `json:"inspection_id"`
	Type         string `json:"type"`
	Date         string `json:"date"`
	Outcome      string `json:"outcome"`
	Location     string `json:"location"`
}

type riskResponse struct {
	ElevatorID      int     `json:"elevator_id"`
	RiskScore       float64 `json:"risk_score"`
	RiskLevel       string  `json:"risk_level"`
	PredictedAt     string  `json:"predicted_at"`
	RiskExplanation *string `json:"risk_explanation"`
}

type errResponse struct {
	Error string `json:"error"`
}

type fleetStatsResponse struct {
	TotalElevators     int            `json:"total_elevators"`
	ByRiskLevel        map[string]int `json:"by_risk_level"`
	InspectionPassRate float64        `json:"inspection_pass_rate"`
	ByEquipmentType    map[string]int `json:"by_equipment_type"`
}

type fleetAlertItem struct {
	ElevatorID            int     `json:"elevator_id"`
	RiskScore             float64 `json:"risk_score"`
	RiskLevel             string  `json:"risk_level"`
	LastInspectionDate    string  `json:"last_inspection_date"`
	LastInspectionOutcome string  `json:"last_inspection_outcome"`
	EquipmentType         string  `json:"equipment_type"`
}

// --- Handlers ---

func handleListElevators(w http.ResponseWriter, r *http.Request) {
	q := r.URL.Query()

	page := 1
	if v := q.Get("page"); v != "" {
		p, err := strconv.Atoi(v)
		if err != nil || p < 1 {
			writeErr(w, http.StatusBadRequest, "invalid value for parameter 'page'")
			return
		}
		page = p
	}

	status := q.Get("status")
	if status == "" {
		status = "all"
	}
	if !oneOf(status, "all", "ACTIVE", "PENDING_RENEWAL", "BY_REQUEST") {
		writeErr(w, http.StatusBadRequest, fmt.Sprintf("invalid value for parameter 'status': '%s'", status))
		return
	}

	expired := q.Get("expired")
	if expired == "" {
		expired = "all"
	}
	if !oneOf(expired, "all", "yes", "no") {
		writeErr(w, http.StatusBadRequest, fmt.Sprintf("invalid value for parameter 'expired': '%s'", expired))
		return
	}

	inspection := q.Get("inspection")
	if inspection == "" {
		inspection = "all"
	}
	if !oneOf(inspection, "all", "overdue", "ok") {
		writeErr(w, http.StatusBadRequest, fmt.Sprintf("invalid value for parameter 'inspection': '%s'", inspection))
		return
	}

	searchID := q.Get("search_id")
	searchLoc := q.Get("search_location")

	sortBy := q.Get("sort_by")
	if sortBy == "" {
		sortBy = "elevator_id"
	}
	if !oneOf(sortBy, "elevator_id", "license_expiry_date") {
		writeErr(w, http.StatusBadRequest, fmt.Sprintf("invalid value for parameter 'sort_by': '%s'", sortBy))
		return
	}

	sortDir := q.Get("sort_dir")
	if sortDir == "" {
		sortDir = "asc"
	}
	if !oneOf(sortDir, "asc", "desc") {
		writeErr(w, http.StatusBadRequest, fmt.Sprintf("invalid value for parameter 'sort_dir': '%s'", sortDir))
		return
	}

	// sortBy and sortDir are validated against a whitelist — safe to interpolate
	orderCol := "e.elevator_id"
	if sortBy == "license_expiry_date" {
		orderCol = "e.license_expiry_date"
	}

	query := `
		WITH latest_insp AS (
			SELECT elevator_id, MAX(latest_inspection_date) AS last_date
			FROM inspections
			GROUP BY elevator_id
		)
		SELECT
			e.elevator_id,
			COALESCE(e.location, '')                                    AS location,
			COALESCE(e.city, '')                                        AS city,
			e.license_status,
			COALESCE(e.license_expiry_date::text, '')                   AS license_expiry_date,
			COALESCE(p.risk_level, '')                                  AS risk_level,
			COALESCE(li.last_date < NOW() - INTERVAL '1 year', false)   AS is_overdue,
			COUNT(*) OVER()                                             AS total_count
		FROM elevators e
		LEFT JOIN predictions p  ON p.elevator_id  = e.elevator_id
		LEFT JOIN latest_insp li ON li.elevator_id = e.elevator_id
		WHERE
			($1 = 'all' OR e.license_status = $1)
			AND ($2 = 'all'
				OR ($2 = 'yes' AND e.license_expiry_date < NOW())
				OR ($2 = 'no'  AND (e.license_expiry_date IS NULL OR e.license_expiry_date >= NOW())))
			AND ($3 = 'all'
				OR ($3 = 'overdue' AND     COALESCE(li.last_date < NOW() - INTERVAL '1 year', false))
				OR ($3 = 'ok'      AND NOT COALESCE(li.last_date < NOW() - INTERVAL '1 year', false)))
			AND ($4 = '' OR e.elevator_id::text LIKE $4 || '%')
			AND ($5 = '' OR LOWER(COALESCE(e.location, '')) LIKE '%' || LOWER($5) || '%')
		ORDER BY ` + orderCol + ` ` + sortDir + `
		LIMIT 10 OFFSET $6`

	ctx := r.Context()
	dbRows, err := db.Query(ctx, query, status, expired, inspection, searchID, searchLoc, (page-1)*10)
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "database error")
		return
	}
	defer dbRows.Close()

	var items []listItem
	var total int
	for dbRows.Next() {
		var item listItem
		if err := dbRows.Scan(
			&item.ElevatorID, &item.Location, &item.City,
			&item.LicenseStatus, &item.LicenseExpiryDate,
			&item.RiskLevel, &item.IsOverdue, &total,
		); err != nil {
			writeErr(w, http.StatusInternalServerError, "database error")
			return
		}
		items = append(items, item)
	}
	if items == nil {
		items = []listItem{}
	}

	const pageSize = 10
	totalPages := int(math.Ceil(float64(total) / float64(pageSize)))
	if totalPages < 1 {
		totalPages = 1
	}
	if page > totalPages {
		page = totalPages
	}

	writeJSON(w, http.StatusOK, listResponse{
		Data:       items,
		Total:      total,
		Page:       page,
		TotalPages: totalPages,
	})
}

func handleGetElevator(w http.ResponseWriter, r *http.Request) {
	id, ok := parseElevatorID(w, r)
	if !ok {
		return
	}

	ctx := r.Context()
	var resp detailResponse
	err := db.QueryRow(ctx, `
		SELECT
			e.elevator_id,
			COALESCE(e.location, '')                                    AS location,
			COALESCE(e.city, '')                                        AS city,
			COALESCE(e.license_number, '')                              AS license_number,
			e.license_status,
			COALESCE(e.license_expiry_date::text, '')                   AS license_expiry_date,
			COALESCE(e.device_type, '')                                 AS device_type,
			COALESCE(e.device_status, '')                               AS device_status,
			COUNT(a.service_request_number)                             AS alteration_count,
			COUNT(i.incident_number)                                    AS incident_count,
			COALESCE(MAX(insp.latest_inspection_date) < NOW() - INTERVAL '1 year', false) AS is_overdue
		FROM elevators e
		LEFT JOIN alterations  a    ON a.elevator_id    = e.elevator_id
		LEFT JOIN incidents    i    ON i.elevator_id    = e.elevator_id
		LEFT JOIN inspections  insp ON insp.elevator_id = e.elevator_id
		WHERE e.elevator_id = $1
		GROUP BY e.elevator_id, e.location, e.city, e.license_number, e.license_status,
		         e.license_expiry_date, e.device_type, e.device_status
	`, id).Scan(
		&resp.ElevatorID, &resp.Location, &resp.City,
		&resp.LicenseNumber, &resp.LicenseStatus, &resp.LicenseExpiryDate,
		&resp.DeviceType, &resp.DeviceStatus,
		&resp.AlterationCount, &resp.IncidentCount, &resp.IsOverdue,
	)
	if err == pgx.ErrNoRows {
		writeErr(w, http.StatusNotFound, fmt.Sprintf("elevator %d not found", id))
		return
	}
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "database error")
		return
	}
	writeJSON(w, http.StatusOK, resp)
}

func handleGetInspections(w http.ResponseWriter, r *http.Request) {
	id, ok := parseElevatorID(w, r)
	if !ok {
		return
	}

	ctx := r.Context()
	exists, err := elevatorExists(ctx, id)
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "database error")
		return
	}
	if !exists {
		writeErr(w, http.StatusNotFound, fmt.Sprintf("elevator %d not found", id))
		return
	}

	rows, err := db.Query(ctx, `
		SELECT
			inspection_number,
			COALESCE(inspection_type, '') AS type,
			latest_inspection_date::text  AS date,
			outcome,
			COALESCE(location, '')        AS location
		FROM inspections
		WHERE elevator_id = $1
		ORDER BY latest_inspection_date DESC
	`, id)
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "database error")
		return
	}
	defer rows.Close()

	result := []inspectionResponse{}
	for rows.Next() {
		var insp inspectionResponse
		if err := rows.Scan(&insp.InspectionID, &insp.Type, &insp.Date, &insp.Outcome, &insp.Location); err != nil {
			writeErr(w, http.StatusInternalServerError, "database error")
			return
		}
		result = append(result, insp)
	}
	writeJSON(w, http.StatusOK, result)
}

func handleGetRisk(w http.ResponseWriter, r *http.Request) {
	id, ok := parseElevatorID(w, r)
	if !ok {
		return
	}

	ctx := r.Context()
	exists, err := elevatorExists(ctx, id)
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "database error")
		return
	}
	if !exists {
		writeErr(w, http.StatusNotFound, fmt.Sprintf("elevator %d not found", id))
		return
	}

	var resp riskResponse
	err = db.QueryRow(ctx, `
		SELECT elevator_id, risk_score, risk_level, prediction_date::text, risk_explanation
		FROM predictions
		WHERE elevator_id = $1
	`, id).Scan(&resp.ElevatorID, &resp.RiskScore, &resp.RiskLevel, &resp.PredictedAt, &resp.RiskExplanation)
	if err == pgx.ErrNoRows {
		var count int
		db.QueryRow(ctx, "SELECT COUNT(*) FROM predictions").Scan(&count)
		if count == 0 {
			writeErr(w, http.StatusServiceUnavailable, "predictions not available")
		} else {
			writeErr(w, http.StatusNotFound, fmt.Sprintf("no risk prediction found for elevator %d", id))
		}
		return
	}
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "database error")
		return
	}
	writeJSON(w, http.StatusOK, resp)
}

func handleFleetStats(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()

	var predCount int
	if err := db.QueryRow(ctx, "SELECT COUNT(*) FROM predictions").Scan(&predCount); err != nil || predCount == 0 {
		writeErr(w, http.StatusServiceUnavailable, "predictions not available")
		return
	}

	var totalElevators int
	db.QueryRow(ctx, "SELECT COUNT(*) FROM elevators").Scan(&totalElevators)

	byRiskLevel := map[string]int{"high": 0, "medium": 0, "low": 0}
	riskRows, err := db.Query(ctx, "SELECT risk_level, COUNT(*) FROM predictions GROUP BY risk_level")
	if err == nil {
		defer riskRows.Close()
		for riskRows.Next() {
			var level string
			var count int
			riskRows.Scan(&level, &count)
			byRiskLevel[level] = count
		}
	}

	var passed, inspTotal int
	db.QueryRow(ctx, `
		SELECT
			COUNT(*) FILTER (WHERE outcome = 'Passed'),
			COUNT(*)
		FROM inspections
	`).Scan(&passed, &inspTotal)
	var passRate float64
	if inspTotal > 0 {
		passRate = math.Round(float64(passed)/float64(inspTotal)*10000) / 10000
	}

	byEquipmentType := make(map[string]int)
	typeRows, err := db.Query(ctx, `
		SELECT COALESCE(NULLIF(TRIM(device_type), ''), 'Unknown'), COUNT(*)
		FROM elevators
		GROUP BY 1
	`)
	if err == nil {
		defer typeRows.Close()
		for typeRows.Next() {
			var dtype string
			var count int
			typeRows.Scan(&dtype, &count)
			byEquipmentType[dtype] = count
		}
	}

	writeJSON(w, http.StatusOK, fleetStatsResponse{
		TotalElevators:     totalElevators,
		ByRiskLevel:        byRiskLevel,
		InspectionPassRate: passRate,
		ByEquipmentType:    byEquipmentType,
	})
}

func handleFleetAlerts(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()

	var predCount int
	if err := db.QueryRow(ctx, "SELECT COUNT(*) FROM predictions").Scan(&predCount); err != nil || predCount == 0 {
		writeErr(w, http.StatusServiceUnavailable, "predictions not available")
		return
	}

	rows, err := db.Query(ctx, `
		WITH latest_insp AS (
			SELECT DISTINCT ON (elevator_id)
				elevator_id,
				latest_inspection_date,
				outcome
			FROM inspections
			ORDER BY elevator_id, latest_inspection_date DESC
		)
		SELECT
			e.elevator_id,
			p.risk_score,
			p.risk_level,
			li.latest_inspection_date::text  AS last_inspection_date,
			li.outcome                        AS last_inspection_outcome,
			COALESCE(NULLIF(TRIM(e.device_type), ''), '') AS equipment_type
		FROM elevators e
		JOIN predictions p  ON p.elevator_id  = e.elevator_id
		JOIN latest_insp li ON li.elevator_id = e.elevator_id
		WHERE p.risk_level = 'high' AND li.outcome != 'Passed'
		ORDER BY p.risk_score DESC
	`)
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "database error")
		return
	}
	defer rows.Close()

	alerts := []fleetAlertItem{}
	for rows.Next() {
		var a fleetAlertItem
		if err := rows.Scan(
			&a.ElevatorID, &a.RiskScore, &a.RiskLevel,
			&a.LastInspectionDate, &a.LastInspectionOutcome, &a.EquipmentType,
		); err != nil {
			writeErr(w, http.StatusInternalServerError, "database error")
			return
		}
		alerts = append(alerts, a)
	}
	writeJSON(w, http.StatusOK, alerts)
}

// --- Helpers ---

func elevatorExists(ctx context.Context, id int) (bool, error) {
	var exists bool
	err := db.QueryRow(ctx, "SELECT EXISTS(SELECT 1 FROM elevators WHERE elevator_id = $1)", id).Scan(&exists)
	return exists, err
}

func parseElevatorID(w http.ResponseWriter, r *http.Request) (int, bool) {
	id, err := strconv.Atoi(r.PathValue("id"))
	if err != nil {
		writeErr(w, http.StatusBadRequest, "elevator id must be an integer")
		return 0, false
	}
	return id, true
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}

func writeErr(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, errResponse{Error: msg})
}

func oneOf(v string, options ...string) bool {
	for _, o := range options {
		if v == o {
			return true
		}
	}
	return false
}

// --- Main ---

func main() {
	if err := initDB(); err != nil {
		fmt.Fprintf(os.Stderr, "database init failed: %v\n", err)
		os.Exit(1)
	}

	port := os.Getenv("PORT")
	if port == "" {
		port = "8081"
	}

	mux := http.NewServeMux()
	mux.HandleFunc("GET /api/health", handleHealth)
	mux.HandleFunc("GET /api/elevators", handleListElevators)
	mux.HandleFunc("GET /api/elevators/{id}", handleGetElevator)
	mux.HandleFunc("GET /api/elevators/{id}/inspections", handleGetInspections)
	mux.HandleFunc("GET /api/elevators/{id}/risk", handleGetRisk)
	mux.HandleFunc("GET /api/fleet/stats", handleFleetStats)
	mux.HandleFunc("GET /api/fleet/alerts", handleFleetAlerts)

	fmt.Printf("Rocket Elevators API listening on :%s\n", port)
	if err := http.ListenAndServe(":"+port, mux); err != nil {
		fmt.Fprintf(os.Stderr, "server error: %v\n", err)
		os.Exit(1)
	}
}
