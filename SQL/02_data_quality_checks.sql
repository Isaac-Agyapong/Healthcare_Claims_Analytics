-- =====================================================================
-- Data quality checks: run after loading. Every check should return 0
-- problem rows (or the expected counts) before analysis starts.
-- =====================================================================

-- Q1: Row counts per table
SELECT 'patients' AS table_name, COUNT(*) AS row_count FROM patients
UNION ALL SELECT 'providers', COUNT(*) FROM providers
UNION ALL SELECT 'claims',    COUNT(*) FROM claims;

-- Q2: Orphan keys (claims pointing at a patient or provider that does not exist)
SELECT
    SUM(CASE WHEN p.patient_id  IS NULL THEN 1 ELSE 0 END) AS orphan_patient_rows,
    SUM(CASE WHEN pr.provider_id IS NULL THEN 1 ELSE 0 END) AS orphan_provider_rows
FROM claims c
LEFT JOIN patients  p  ON p.patient_id   = c.patient_id
LEFT JOIN providers pr ON pr.provider_id = c.provider_id;

-- Q3: Financial logic violations (paid must not exceed allowed; allowed must not exceed billed)
SELECT
    SUM(CASE WHEN paid_amount    > allowed_amount + 0.01 THEN 1 ELSE 0 END) AS paid_gt_allowed,
    SUM(CASE WHEN allowed_amount > billed_amount  + 0.01 THEN 1 ELSE 0 END) AS allowed_gt_billed,
    SUM(CASE WHEN claim_status = 'Denied' AND paid_amount > 0 THEN 1 ELSE 0 END) AS denied_but_paid
FROM claims;

-- Q4: Date logic violations
SELECT
    SUM(CASE WHEN submission_date < service_date THEN 1 ELSE 0 END)                   AS submitted_before_service,
    SUM(CASE WHEN processed_date  < submission_date THEN 1 ELSE 0 END)                AS processed_before_submitted,
    SUM(CASE WHEN claim_status = 'Pending' AND processed_date IS NOT NULL THEN 1 ELSE 0 END) AS pending_with_decision,
    SUM(CASE WHEN claim_status <> 'Pending' AND processed_date IS NULL THEN 1 ELSE 0 END)    AS decided_without_date
FROM claims;

-- Q5: Denied claims missing a denial reason
SELECT COUNT(*) AS denied_without_reason
FROM claims
WHERE claim_status = 'Denied' AND denial_reason = 'Not Applicable';

-- Q6: Share of billed amounts that were imputed during cleaning
SELECT
    SUM(billed_imputed)                                AS imputed_rows,
    ROUND(100.0 * SUM(billed_imputed) / COUNT(*), 2)   AS imputed_pct
FROM claims;
