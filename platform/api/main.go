package main

import (
	"encoding/csv"
	"encoding/json"
	"fmt"
	"math"
	"net/http"
	"os"
	"sort"
	"strconv"
	"strings"
	"time"
)

// --- Data types ---

type fleetRow struct {
	elevatorID        int
	location          string
	city              string
	licenseNumber     string
	licenseStatus     string
	licenseExpiryDate time.Time
	expiryISO         string
}

type installedRow struct {
	deviceType   string
	deviceStatus string 
}

type inspectionRow struct {
	inspectionID int
	typ          string
	date         time.Time
	dateISO      string
	outcome      string
	location     string
}

type riskRow struct {
	riskScore   float64
	riskLevel   string
	predictedAt string
}

// --- Response types ---

type listItem struct {
	ElevatorID        int    `json:"elevator_id"`
	Location          string `json:"location"`
	City              string `json:"city"`
	LicenseStatus     string `json:"license_status"`
	LicenseExpiryDate string `json:"license_expiry_date"`
	IsOverdue         bool   `json:"is_overdue"`
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
	ElevatorID  int     `json:"elevator_id"`
	RiskScore   float64 `json:"risk_score"`
	RiskLevel   string  `json:"risk_level"`
	PredictedAt string  `json:"predicted_at"`
}

type errResponse struct {
	Error string `json:"error"`
}

// --- Global state ---

var (
	fleet       []fleetRow
	fleetIndex  map[int]int 
	installed   map[int]installedRow
	alterations map[int]int
	incidents   map[int]int
	inspByID    map[int][]inspectionRow
	overdueIDs  map[int]bool
	riskByID    map[int]riskRow 
)

// --- Path helpers ---

func dataDir() string {
	if d := os.Getenv("DATA_DIR"); d != "" {
		return d
	}
	return "../../data"
}

func fleetCSV() string {
	if p := os.Getenv("FLEET_CSV"); p != "" {
		return p
	}
	return "../elevator_fleet.csv"
}

// --- Data loading ---

func colIdx(headers []string) map[string]int {
	m := make(map[string]int, len(headers))
	for i, h := range headers {
		m[h] = i
	}
	return m
}

func asInt(v any) int {
	switch n := v.(type) {
	case float64:
		return int(n)
	}
	return 0
}

func asStr(v any) string {
	if s, ok := v.(string); ok {
		return s
	}
	return ""
}

func loadFleet() error {
	f, err := os.Open(fleetCSV())
	if err != nil {
		return err
	}
	defer f.Close()

	r := csv.NewReader(f)
	headers, err := r.Read()
	if err != nil {
		return err
	}
	idx := colIdx(headers)

	for {
		rec, err := r.Read()
		if err != nil {
			break
		}
		id, _ := strconv.Atoi(rec[idx["elevator_id"]])
		expiry, _ := time.Parse("02-Jan-06", rec[idx["license_expiry_date"]])
		var expiryISO string
		if !expiry.IsZero() {
			expiryISO = expiry.Format("2006-01-02")
		}
		fleet = append(fleet, fleetRow{
			elevatorID:        id,
			location:          rec[idx["location"]],
			city:              rec[idx["city"]],
			licenseNumber:     rec[idx["license_number"]],
			licenseStatus:     rec[idx["license_status"]],
			licenseExpiryDate: expiry,
			expiryISO:         expiryISO,
		})
	}

	fleetIndex = make(map[int]int, len(fleet))
	for i, row := range fleet {
		fleetIndex[row.elevatorID] = i
	}
	return nil
}

func loadInstalled() error {
	f, err := os.Open(dataDir() + "/installed.json")
	if err != nil {
		return err
	}
	defer f.Close()

	var raw []map[string]any
	if err := json.NewDecoder(f).Decode(&raw); err != nil {
		return err
	}

	installed = make(map[int]installedRow, len(raw))
	for _, item := range raw {
		id := asInt(item["Elevating devices number"])
		installed[id] = installedRow{
			deviceType:   asStr(item["Device Type"]),
			deviceStatus: asStr(item["DeviceStatus"]),
		}
	}
	return nil
}

func loadAlterations() error {
	f, err := os.Open(dataDir() + "/altered.json")
	if err != nil {
		return err
	}
	defer f.Close()

	var raw []map[string]any
	if err := json.NewDecoder(f).Decode(&raw); err != nil {
		return err
	}

	alterations = make(map[int]int)
	for _, item := range raw {
		id := asInt(item["Elevating Devices Number"])
		alterations[id]++
	}
	return nil
}

func loadIncidents() error {
	f, err := os.Open(dataDir() + "/incident.json")
	if err != nil {
		return err
	}
	defer f.Close()

	var raw []map[string]any
	if err := json.NewDecoder(f).Decode(&raw); err != nil {
		return err
	}

	incidents = make(map[int]int)
	for _, item := range raw {
		id := asInt(item["elevating devices number"])
		incidents[id]++
	}
	return nil
}

func loadInspections() error {
	f, err := os.Open(dataDir() + "/inspection.csv")
	if err != nil {
		return err
	}
	defer f.Close()

	r := csv.NewReader(f)
	headers, err := r.Read()
	if err != nil {
		return err
	}
	idx := colIdx(headers)

	inspByID = make(map[int][]inspectionRow)
	for {
		rec, err := r.Read()
		if err != nil {
			break
		}
		elevID, _ := strconv.Atoi(rec[idx["ElevatingDevicesNumber"]])
		inspID, _ := strconv.Atoi(rec[idx["InspectionNumber"]])
		date, _ := time.Parse("1/2/2006", rec[idx["Latest_INSPECTION_Date"]])
		var dateISO string
		if !date.IsZero() {
			dateISO = date.Format("2006-01-02")
		}
		inspByID[elevID] = append(inspByID[elevID], inspectionRow{
			inspectionID: inspID,
			typ:          rec[idx["InspectionType"]],
			date:         date,
			dateISO:      dateISO,
			outcome:      rec[idx["InspectionOutcome"]],
			location:     rec[idx["InspectionLocation"]],
		})
	}

	cutoff := time.Now().AddDate(-1, 0, 0)
	overdueIDs = make(map[int]bool)

	for id, rows := range inspByID {
		sort.Slice(rows, func(i, j int) bool {
			return rows[i].date.After(rows[j].date)
		})
		inspByID[id] = rows
		if rows[0].date.Before(cutoff) {
			overdueIDs[id] = true
		}
	}
	return nil
}

func loadPredictions() {
	f, err := os.Open(dataDir() + "/predictions.csv")
	if err != nil {
		return
	}
	defer f.Close()

	r := csv.NewReader(f)
	headers, err := r.Read()
	if err != nil {
		return
	}
	idx := colIdx(headers)

	riskByID = make(map[int]riskRow)
	for {
		rec, err := r.Read()
		if err != nil {
			break
		}
		id, _ := strconv.Atoi(rec[idx["elevator_id"]])
		score, _ := strconv.ParseFloat(rec[idx["risk_score"]], 64)
		riskByID[id] = riskRow{
			riskScore:   score,
			riskLevel:   computeRiskLevel(score),
			predictedAt: rec[idx["predicted_at"]],
		}
	}
}

func computeRiskLevel(score float64) string {
	if score < 0.33 {
		return "low"
	}
	if score < 0.66 {
		return "medium"
	}
	return "high"
}

func loadData() {
	loaders := []struct {
		name string
		fn   func() error
	}{
		{"fleet", loadFleet},
		{"installed", loadInstalled},
		{"alterations", loadAlterations},
		{"incidents", loadIncidents},
		{"inspections", loadInspections},
	}
	for _, l := range loaders {
		if err := l.fn(); err != nil {
			fmt.Fprintf(os.Stderr, "error loading %s: %v\n", l.name, err)
			os.Exit(1)
		}
	}
	loadPredictions() // non-fatal — forward dependency on Task 6
	fmt.Printf("Loaded %d elevators\n", len(fleet))
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
	searchLoc := strings.ToLower(q.Get("search_location"))

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

	now := time.Now()
	var filtered []fleetRow
	for _, row := range fleet {
		if status != "all" && row.licenseStatus != status {
			continue
		}
		if expired == "yes" && !row.licenseExpiryDate.Before(now) {
			continue
		}
		if expired == "no" && row.licenseExpiryDate.Before(now) {
			continue
		}
		if inspection == "overdue" && !overdueIDs[row.elevatorID] {
			continue
		}
		if inspection == "ok" && overdueIDs[row.elevatorID] {
			continue
		}
		if searchID != "" && !strings.HasPrefix(strconv.Itoa(row.elevatorID), searchID) {
			continue
		}
		if searchLoc != "" && !strings.Contains(strings.ToLower(row.location), searchLoc) {
			continue
		}
		filtered = append(filtered, row)
	}

	sort.SliceStable(filtered, func(i, j int) bool {
		asc := sortDir == "asc"
		if sortBy == "license_expiry_date" {
			if asc {
				return filtered[i].licenseExpiryDate.Before(filtered[j].licenseExpiryDate)
			}
			return filtered[i].licenseExpiryDate.After(filtered[j].licenseExpiryDate)
		}
		if asc {
			return filtered[i].elevatorID < filtered[j].elevatorID
		}
		return filtered[i].elevatorID > filtered[j].elevatorID
	})

	const pageSize = 10
	total := len(filtered)
	totalPages := int(math.Ceil(float64(total) / float64(pageSize)))
	if totalPages < 1 {
		totalPages = 1
	}
	if page > totalPages {
		page = totalPages
	}
	start := (page - 1) * pageSize
	end := min(start+pageSize, total)

	items := make([]listItem, 0, end-start)
	for _, row := range filtered[start:end] {
		items = append(items, listItem{
			ElevatorID:        row.elevatorID,
			Location:          row.location,
			City:              row.city,
			LicenseStatus:     row.licenseStatus,
			LicenseExpiryDate: row.expiryISO,
			IsOverdue:         overdueIDs[row.elevatorID],
		})
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
	i, exists := fleetIndex[id]
	if !exists {
		writeErr(w, http.StatusNotFound, fmt.Sprintf("elevator %d not found", id))
		return
	}
	row := fleet[i]
	inst := installed[id]
	writeJSON(w, http.StatusOK, detailResponse{
		ElevatorID:        row.elevatorID,
		Location:          row.location,
		City:              row.city,
		LicenseNumber:     row.licenseNumber,
		LicenseStatus:     row.licenseStatus,
		LicenseExpiryDate: row.expiryISO,
		DeviceType:        inst.deviceType,
		DeviceStatus:      inst.deviceStatus,
		AlterationCount:   alterations[id],
		IncidentCount:     incidents[id],
		IsOverdue:         overdueIDs[id],
	})
}

func handleGetInspections(w http.ResponseWriter, r *http.Request) {
	id, ok := parseElevatorID(w, r)
	if !ok {
		return
	}
	if _, exists := fleetIndex[id]; !exists {
		writeErr(w, http.StatusNotFound, fmt.Sprintf("elevator %d not found", id))
		return
	}
	rows := inspByID[id]
	result := make([]inspectionResponse, 0, len(rows))
	for _, row := range rows {
		result = append(result, inspectionResponse{
			InspectionID: row.inspectionID,
			Type:         row.typ,
			Date:         row.dateISO,
			Outcome:      row.outcome,
			Location:     row.location,
		})
	}
	writeJSON(w, http.StatusOK, result)
}

func handleGetRisk(w http.ResponseWriter, r *http.Request) {
	id, ok := parseElevatorID(w, r)
	if !ok {
		return
	}
	if _, exists := fleetIndex[id]; !exists {
		writeErr(w, http.StatusNotFound, fmt.Sprintf("elevator %d not found", id))
		return
	}
	if riskByID == nil {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusServiceUnavailable)
		json.NewEncoder(w).Encode(errResponse{Error: "predictions not available"})
		return
	}
	risk, exists := riskByID[id]
	if !exists {
		writeErr(w, http.StatusNotFound, fmt.Sprintf("no risk prediction found for elevator %d", id))
		return
	}
	writeJSON(w, http.StatusOK, riskResponse{
		ElevatorID:  id,
		RiskScore:   risk.riskScore,
		RiskLevel:   risk.riskLevel,
		PredictedAt: risk.predictedAt,
	})
}

// --- Helpers ---

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

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

// --- Main ---

func main() {
	loadData()

	port := os.Getenv("PORT")
	if port == "" {
		port = "8081"
	}

	mux := http.NewServeMux()
	mux.HandleFunc("GET /api/elevators", handleListElevators)
	mux.HandleFunc("GET /api/elevators/{id}", handleGetElevator)
	mux.HandleFunc("GET /api/elevators/{id}/inspections", handleGetInspections)
	mux.HandleFunc("GET /api/elevators/{id}/risk", handleGetRisk)

	fmt.Printf("Rocket Elevators API listening on :%s\n", port)
	if err := http.ListenAndServe(":"+port, mux); err != nil {
		fmt.Fprintf(os.Stderr, "server error: %v\n", err)
		os.Exit(1)
	}
}
