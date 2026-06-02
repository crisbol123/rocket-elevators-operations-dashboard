CREATE TABLE elevators (
    elevator_id          INTEGER     PRIMARY KEY,
    location             TEXT,
    city                 TEXT,
    license_number       TEXT        NOT NULL,
    license_status       TEXT        NOT NULL,
    license_expiry_date  DATE,
    license_holder       TEXT,
    device_type          TEXT,
    device_status        TEXT
);

CREATE INDEX idx_elevators_license_status    ON elevators (license_status);
CREATE INDEX idx_elevators_license_expiry    ON elevators (license_expiry_date);


CREATE TABLE inspections (
    inspection_number       INTEGER     PRIMARY KEY,
    elevator_id             INTEGER     REFERENCES elevators (elevator_id) ON DELETE SET NULL,
    inspection_type         TEXT        NOT NULL,
    latest_inspection_date  DATE        NOT NULL,
    outcome                 TEXT        NOT NULL,
    location                TEXT
);

CREATE INDEX idx_inspections_elevator_id            ON inspections (elevator_id);
CREATE INDEX idx_inspections_latest_inspection_date ON inspections (latest_inspection_date);
CREATE INDEX idx_inspections_outcome                ON inspections (outcome);


CREATE TABLE incidents (
    incident_number    TEXT    PRIMARY KEY,
    elevator_id        INTEGER REFERENCES elevators (elevator_id) ON DELETE SET NULL,
    date_of_occurrence DATE,
    category           TEXT,
    root_cause         TEXT,
    narrative          TEXT
);

CREATE INDEX idx_incidents_elevator_id ON incidents (elevator_id);


CREATE TABLE alterations (
    service_request_number  INTEGER PRIMARY KEY,
    elevator_id             INTEGER REFERENCES elevators (elevator_id) ON DELETE SET NULL,
    alteration_type         TEXT,
    status                  TEXT,
    summary                 TEXT
);

CREATE INDEX idx_alterations_elevator_id ON alterations (elevator_id);


CREATE TABLE predictions (
    elevator_id       INTEGER         PRIMARY KEY REFERENCES elevators (elevator_id) ON DELETE CASCADE,
    risk_score        NUMERIC(5,4)    NOT NULL,
    risk_level        TEXT            NOT NULL,
    model_version     TEXT            NOT NULL,
    prediction_date   DATE            NOT NULL,
    risk_explanation  TEXT
);

CREATE INDEX idx_predictions_risk_level ON predictions (risk_level);
CREATE INDEX idx_predictions_risk_score ON predictions (risk_score);
