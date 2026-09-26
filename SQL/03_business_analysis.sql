-- =====================================================================
-- Business analysis: where is claim revenue being lost?
-- Techniques: JOINs, CTEs, CASE, conditional aggregation, window functions
-- (LAG, SUM OVER, AVG OVER PARTITION, DENSE_RANK, ROW_NUMBER, NTILE)
-- Denial rate is always measured on decided claims only (Pending excluded).
-- =====================================================================

-- Q1: Headline KPIs
SELECT
    COUNT(*)                                                            AS total_claims,
    COUNT(DISTINCT patient_id)                                          AS unique_patients,
    ROUND(SUM(billed_amount), 0)                                        AS total_billed,
    ROUND(SUM(paid_amount), 0)                                          AS total_paid,
    ROUND(100.0 * SUM(paid_amount) / SUM(billed_amount), 1)             AS paid_to_billed_pct,
    ROUND(100.0 * SUM(claim_status = 'Denied')
               / SUM(claim_status <> 'Pending'), 1)                     AS denial_rate_pct,
    ROUND(SUM(CASE WHEN claim_status = 'Denied' THEN billed_amount END), 0) AS denied_billed
FROM claims;

-- Q2: Monthly trend with month-over-month change and running total paid
WITH monthly AS (
    SELECT
        strftime('%Y-%m', service_date)                                 AS month,
        COUNT(*)                                                        AS claims,
        SUM(paid_amount)                                                AS paid,
        1.0 * SUM(claim_status = 'Denied') / SUM(claim_status <> 'Pending') AS denial_rate
    FROM claims
    GROUP BY month
)
SELECT
    month,
    claims,
    ROUND(100.0 * (claims - LAG(claims) OVER (ORDER BY month)) / LAG(claims) OVER (ORDER BY month), 1) AS claims_mom_pct,
    ROUND(paid, 0)                                                      AS paid,
    ROUND(SUM(paid) OVER (PARTITION BY substr(month, 1, 4) ORDER BY month), 0) AS paid_ytd,
    ROUND(100 * denial_rate, 1)                                         AS denial_rate_pct
FROM monthly
ORDER BY month;

-- Q3: Denial reasons ranked by dollars at risk, with share of total
SELECT
    denial_reason,
    COUNT(*)                                                            AS denied_claims,
    ROUND(SUM(billed_amount), 0)                                        AS denied_billed,
    ROUND(100.0 * SUM(billed_amount) / SUM(SUM(billed_amount)) OVER (), 1) AS share_of_denied_pct
FROM claims
WHERE claim_status = 'Denied'
GROUP BY denial_reason
ORDER BY denied_billed DESC;

-- Q4: Year-over-year change in denials by reason (conditional aggregation)
SELECT
    denial_reason,
    SUM(strftime('%Y', service_date) = '2024')                          AS denials_2024,
    SUM(strftime('%Y', service_date) = '2025')                          AS denials_2025,
    ROUND(100.0 * (SUM(strftime('%Y', service_date) = '2025') - SUM(strftime('%Y', service_date) = '2024'))
                / SUM(strftime('%Y', service_date) = '2024'), 1)        AS yoy_change_pct
FROM claims
WHERE claim_status = 'Denied'
GROUP BY denial_reason
ORDER BY yoy_change_pct DESC;

-- Q5: Denial rate by plan type and network status (joins across all three tables)
SELECT
    p.plan_type,
    pr.network_status,
    COUNT(*)                                                            AS decided_claims,
    ROUND(100.0 * AVG(c.claim_status = 'Denied'), 1)                    AS denial_rate_pct
FROM claims c
JOIN patients  p  ON p.patient_id   = c.patient_id
JOIN providers pr ON pr.provider_id = c.provider_id
WHERE c.claim_status <> 'Pending'
GROUP BY p.plan_type, pr.network_status
ORDER BY p.plan_type, pr.network_status;

-- Q6: Provider outliers: denial rate vs. peers with the same claim type and network status
WITH provider_stats AS (
    SELECT
        pr.provider_id,
        pr.provider_name,
        pr.specialty,
        pr.network_status,
        c.claim_type,
        COUNT(*)                                                        AS decided_claims,
        AVG(c.claim_status = 'Denied')                                  AS denial_rate,
        SUM(CASE WHEN c.claim_status = 'Denied' THEN 1 ELSE 0 END)      AS denials
    FROM claims c
    JOIN providers pr ON pr.provider_id = c.provider_id
    WHERE c.claim_status <> 'Pending'
    GROUP BY pr.provider_id
),
with_peers AS (
    SELECT *,
        1.0 * SUM(denials) OVER (PARTITION BY claim_type, network_status)
            / SUM(decided_claims) OVER (PARTITION BY claim_type, network_status) AS peer_rate
    FROM provider_stats
)
SELECT
    provider_name,
    specialty,
    network_status,
    decided_claims,
    ROUND(100 * denial_rate, 1)                                         AS denial_rate_pct,
    ROUND(100 * peer_rate, 1)                                           AS peer_rate_pct,
    ROUND(100 * (denial_rate - peer_rate), 1)                           AS excess_pts
FROM with_peers
WHERE decided_claims >= 100
ORDER BY excess_pts DESC
LIMIT 10;

-- Q7: Most common denial reason at the three flagged providers
WITH reason_counts AS (
    SELECT
        pr.provider_name,
        c.denial_reason,
        COUNT(*)                                                        AS denials,
        ROW_NUMBER() OVER (PARTITION BY pr.provider_name ORDER BY COUNT(*) DESC) AS rn
    FROM claims c
    JOIN providers pr ON pr.provider_id = c.provider_id
    WHERE c.claim_status = 'Denied'
      AND pr.provider_name IN ('Silver Partners', 'Unity Clinic', 'Pinecrest Group')
    GROUP BY pr.provider_name, c.denial_reason
)
SELECT provider_name, denial_reason, denials
FROM reason_counts
WHERE rn <= 2
ORDER BY provider_name, denials DESC;

-- Q8: Top 3 providers per specialty by denied dollars (DENSE_RANK)
WITH ranked AS (
    SELECT
        pr.specialty,
        pr.provider_name,
        ROUND(SUM(c.billed_amount), 0)                                  AS denied_billed,
        DENSE_RANK() OVER (PARTITION BY pr.specialty ORDER BY SUM(c.billed_amount) DESC) AS rnk
    FROM claims c
    JOIN providers pr ON pr.provider_id = c.provider_id
    WHERE c.claim_status = 'Denied'
    GROUP BY pr.specialty, pr.provider_name
)
SELECT specialty, rnk, provider_name, denied_billed
FROM ranked
WHERE rnk <= 3
ORDER BY specialty, rnk;

-- Q9: Cost by specialty: share of claims vs. share of paid dollars
SELECT
    pr.specialty,
    COUNT(*)                                                            AS claims,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)                  AS share_of_claims_pct,
    ROUND(SUM(c.paid_amount), 0)                                        AS paid,
    ROUND(100.0 * SUM(c.paid_amount) / SUM(SUM(c.paid_amount)) OVER (), 1) AS share_of_paid_pct,
    ROUND(AVG(CASE WHEN c.claim_status = 'Paid' THEN c.paid_amount END), 0) AS avg_paid_per_paid_claim
FROM claims c
JOIN providers pr ON pr.provider_id = c.provider_id
GROUP BY pr.specialty
ORDER BY paid DESC;

-- Q10: High-cost members: how concentrated is spend? (NTILE)
WITH member_spend AS (
    SELECT patient_id, SUM(paid_amount) AS paid
    FROM claims
    GROUP BY patient_id
),
bucketed AS (
    SELECT *, NTILE(100) OVER (ORDER BY paid DESC) AS pct_bucket
    FROM member_spend
)
SELECT
    CASE WHEN pct_bucket = 1  THEN 'Top 1%'
         WHEN pct_bucket <= 5  THEN 'Top 2-5%'
         WHEN pct_bucket <= 20 THEN 'Top 6-20%'
         ELSE 'Bottom 80%' END                                          AS member_group,
    COUNT(*)                                                            AS members,
    ROUND(SUM(paid), 0)                                                 AS paid,
    ROUND(100.0 * SUM(paid) / (SELECT SUM(paid) FROM member_spend), 1)  AS share_of_paid_pct
FROM bucketed
GROUP BY member_group
ORDER BY MIN(pct_bucket);

-- Q11: Submission lag vs. denial rate (timely filing risk)
SELECT
    CASE WHEN julianday(submission_date) - julianday(service_date) <= 7  THEN '1) 0-7 days'
         WHEN julianday(submission_date) - julianday(service_date) <= 30 THEN '2) 8-30 days'
         WHEN julianday(submission_date) - julianday(service_date) <= 90 THEN '3) 31-90 days'
         ELSE '4) 90+ days' END                                         AS submission_lag,
    COUNT(*)                                                            AS decided_claims,
    ROUND(100.0 * AVG(claim_status = 'Denied'), 1)                      AS denial_rate_pct
FROM claims
WHERE claim_status <> 'Pending'
GROUP BY submission_lag
ORDER BY submission_lag;

-- Q12: Median and average processing time by status (median via ROW_NUMBER, since SQLite has no MEDIAN)
WITH durations AS (
    SELECT
        claim_status,
        julianday(processed_date) - julianday(submission_date)          AS days,
        ROW_NUMBER() OVER (PARTITION BY claim_status
                           ORDER BY julianday(processed_date) - julianday(submission_date)) AS rn,
        COUNT(*) OVER (PARTITION BY claim_status)                       AS n
    FROM claims
    WHERE claim_status <> 'Pending'
)
SELECT
    claim_status,
    MAX(n)                                                              AS claims,
    ROUND(AVG(days), 1)                                                 AS avg_days,
    AVG(CASE WHEN rn IN ((n + 1) / 2, (n + 2) / 2) THEN days END)       AS median_days,
    MAX(days)                                                           AS max_days
FROM durations
GROUP BY claim_status;

-- Q13: Denial rate and average paid by member age group
SELECT
    CASE WHEN age < 18 THEN '0-17'
         WHEN age < 35 THEN '18-34'
         WHEN age < 50 THEN '35-49'
         WHEN age < 65 THEN '50-64'
         ELSE '65+' END                                                 AS age_group,
    COUNT(*)                                                            AS claims,
    ROUND(100.0 * SUM(claim_status = 'Denied') / SUM(claim_status <> 'Pending'), 1) AS denial_rate_pct,
    ROUND(AVG(CASE WHEN claim_status = 'Paid' THEN paid_amount END), 0) AS avg_paid
FROM (
    SELECT c.*, CAST((julianday(c.service_date) - julianday(p.date_of_birth)) / 365.25 AS INTEGER) AS age
    FROM claims c
    JOIN patients p ON p.patient_id = c.patient_id
)
GROUP BY age_group
ORDER BY age_group;
