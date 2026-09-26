-- =====================================================================
-- Healthcare Claims Analytics: database schema (SQLite)
-- Star schema: one fact table (claims) and two dimensions (patients, providers)
-- Loaded by Python/load_to_sqlite.py from Data/clean/*.csv
-- =====================================================================

DROP TABLE IF EXISTS claims;
DROP TABLE IF EXISTS patients;
DROP TABLE IF EXISTS providers;

CREATE TABLE patients (
    patient_id       TEXT PRIMARY KEY,
    gender           TEXT NOT NULL CHECK (gender IN ('Female', 'Male')),
    date_of_birth    DATE NOT NULL,
    state            TEXT NOT NULL,
    plan_type        TEXT NOT NULL CHECK (plan_type IN ('Commercial', 'Medicare', 'Medicaid')),
    enrollment_date  DATE NOT NULL
);

CREATE TABLE providers (
    provider_id      TEXT PRIMARY KEY,
    provider_name    TEXT NOT NULL,
    specialty        TEXT NOT NULL,
    state            TEXT NOT NULL,
    network_status   TEXT NOT NULL CHECK (network_status IN ('In-Network', 'Out-of-Network'))
);

CREATE TABLE claims (
    claim_id            TEXT PRIMARY KEY,
    patient_id          TEXT NOT NULL REFERENCES patients (patient_id),
    provider_id         TEXT NOT NULL REFERENCES providers (provider_id),
    service_date        DATE NOT NULL,
    submission_date     DATE NOT NULL,
    processed_date      DATE,                          -- NULL while a claim is pending
    claim_type          TEXT NOT NULL,
    diagnosis_category  TEXT NOT NULL,
    cpt_code            TEXT NOT NULL,
    billed_amount       REAL NOT NULL CHECK (billed_amount >= 0),
    allowed_amount      REAL NOT NULL CHECK (allowed_amount >= 0),
    paid_amount         REAL NOT NULL CHECK (paid_amount >= 0),
    claim_status        TEXT NOT NULL CHECK (claim_status IN ('Paid', 'Denied', 'Pending')),
    denial_reason       TEXT NOT NULL,
    billed_imputed      INTEGER NOT NULL DEFAULT 0     -- 1 = billed amount was imputed during cleaning
);

CREATE INDEX idx_claims_patient  ON claims (patient_id);
CREATE INDEX idx_claims_provider ON claims (provider_id);
CREATE INDEX idx_claims_service  ON claims (service_date);
CREATE INDEX idx_claims_status   ON claims (claim_status);
