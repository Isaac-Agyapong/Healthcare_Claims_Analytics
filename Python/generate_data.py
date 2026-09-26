"""
Generate a synthetic (but realistic) health-insurance claims dataset.

Outputs three raw CSVs to Data/raw/:
    patients.csv, providers.csv, claims.csv

The raw files intentionally contain data-quality problems (duplicates, mixed
date formats, inconsistent casing, missing and negative values) so the
cleaning step has real work to do. The random seed is fixed, so the output is
reproducible.
"""
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
N_PATIENTS = 8_000
N_PROVIDERS = 250
N_CLAIMS = 50_000
START, END = pd.Timestamp("2024-01-01"), pd.Timestamp("2025-12-31")

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "Data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

rng = np.random.default_rng(SEED)

STATES = ["FL", "GA", "TX", "NY", "CA", "NC", "OH", "PA", "IL", "AZ"]
STATE_P = [0.20, 0.10, 0.14, 0.10, 0.12, 0.08, 0.07, 0.07, 0.07, 0.05]

# specialty -> (share of providers, base billed $, claim type, diagnosis categories)
SPECIALTIES = {
    "Primary Care":       (0.22, 180,   "Professional", ["Preventive Care", "Diabetes", "Hypertension", "Respiratory"]),
    "Pediatrics":         (0.10, 160,   "Professional", ["Preventive Care", "Respiratory", "Infectious Disease"]),
    "Cardiology":         (0.09, 950,   "Professional", ["Heart Disease", "Hypertension"]),
    "Orthopedics":        (0.09, 1400,  "Professional", ["Musculoskeletal", "Injury"]),
    "Oncology":           (0.05, 3200,  "Professional", ["Cancer"]),
    "Behavioral Health":  (0.10, 220,   "Professional", ["Mental Health", "Substance Use"]),
    "Radiology":          (0.10, 650,   "Outpatient",   ["Musculoskeletal", "Cancer", "Injury", "Heart Disease"]),
    "Emergency Medicine": (0.10, 1900,  "Outpatient",   ["Injury", "Heart Disease", "Respiratory", "Infectious Disease"]),
    "Hospital":           (0.15, 14000, "Inpatient",    ["Heart Disease", "Respiratory", "Cancer", "Injury", "Musculoskeletal"]),
}

CPT_BY_TYPE = {
    "Professional": ["99213", "99214", "99215", "99203", "99204", "90837", "99395"],
    "Outpatient":   ["99284", "99285", "71046", "72148", "74177", "70450"],
    "Inpatient":    ["99221", "99222", "99223", "99231", "99232"],
}

PREFIXES = ["Sunrise", "Bayview", "Summit", "Riverside", "Oakwood", "Lakeshore", "Pinecrest",
            "Harbor", "Meadow", "Northgate", "Cypress", "Golden", "Evergreen", "Cedar", "Coastal",
            "Valley", "Unity", "Heritage", "Crescent", "Magnolia", "Liberty", "Horizon", "Willow",
            "Prairie", "Highland", "Palm", "Brookside", "Silver", "Keystone", "Maple"]
SUFFIXES = ["Group", "Associates", "Clinic", "Partners", "Center", "Medical", "Health", "Care", "Specialists"]


def make_patients() -> pd.DataFrame:
    plan = rng.choice(["Commercial", "Medicare", "Medicaid"], N_PATIENTS, p=[0.50, 0.30, 0.20])
    age = np.where(plan == "Medicare", rng.integers(65, 91, N_PATIENTS), rng.integers(0, 65, N_PATIENTS))
    dob = pd.Timestamp("2024-01-01") - pd.to_timedelta(age * 365.25 + rng.integers(0, 365, N_PATIENTS), unit="D")
    enroll = START - pd.to_timedelta(rng.integers(0, 365 * 5, N_PATIENTS), unit="D")
    return pd.DataFrame({
        "patient_id": [f"P{i:05d}" for i in range(1, N_PATIENTS + 1)],
        "gender": rng.choice(["F", "M"], N_PATIENTS, p=[0.52, 0.48]),
        "date_of_birth": dob.normalize(),
        "state": rng.choice(STATES, N_PATIENTS, p=STATE_P),
        "plan_type": plan,
        "enrollment_date": enroll.normalize(),
    })


def make_providers() -> pd.DataFrame:
    names = [f"{p} {s}" for p in PREFIXES for s in SUFFIXES]
    names = rng.choice(names, N_PROVIDERS, replace=False)
    spec_names = list(SPECIALTIES)
    spec_p = np.array([v[0] for v in SPECIALTIES.values()])
    specialty = rng.choice(spec_names, N_PROVIDERS, p=spec_p / spec_p.sum())
    hospital_kinds = ["Regional", "Memorial", "General", "Community"]
    final, seen = [], set()
    for n, s in zip(names, specialty):
        if s == "Hospital":
            prefix = n.split()[0]
            n = next((f"{prefix} {k} Hospital" for k in hospital_kinds
                      if f"{prefix} {k} Hospital" not in seen), f"{prefix} Hospital {len(seen)}")
        seen.add(n)
        final.append(n)
    names = final
    return pd.DataFrame({
        "provider_id": [f"PR{i:04d}" for i in range(1, N_PROVIDERS + 1)],
        "provider_name": names,
        "specialty": specialty,
        "state": rng.choice(STATES, N_PROVIDERS, p=STATE_P),
        "network_status": rng.choice(["In-Network", "Out-of-Network"], N_PROVIDERS, p=[0.82, 0.18]),
    })


def make_claims(patients: pd.DataFrame, providers: pd.DataFrame) -> pd.DataFrame:
    n = N_CLAIMS

    # --- service dates with winter seasonality and mild growth into 2025
    days = pd.date_range(START, END, freq="D")
    month = days.month.to_numpy()
    weight = np.where(np.isin(month, [12, 1, 2]), 1.25, 1.0) * np.where(days.year == 2025, 1.10, 1.0)
    service = rng.choice(days, n, p=weight / weight.sum())
    service = pd.to_datetime(service)

    # --- who and where (Medicare members use more care)
    util = patients["plan_type"].map({"Commercial": 1.0, "Medicare": 2.2, "Medicaid": 1.3}).to_numpy()
    pat_idx = rng.choice(len(patients), n, p=util / util.sum())
    prov_idx = rng.integers(0, len(providers), n)
    pat = patients.iloc[pat_idx].reset_index(drop=True)
    prov = providers.iloc[prov_idx].reset_index(drop=True)

    spec = prov["specialty"].to_numpy()
    claim_type = np.array([SPECIALTIES[s][2] for s in spec])
    diagnosis = np.array([rng.choice(SPECIALTIES[s][3]) for s in spec])
    cpt = np.array([rng.choice(CPT_BY_TYPE[t]) for t in claim_type])
    oon = (prov["network_status"] == "Out-of-Network").to_numpy()
    plan = pat["plan_type"].to_numpy()

    # --- money
    base = np.array([SPECIALTIES[s][1] for s in spec], dtype=float)
    billed = base * rng.lognormal(0, 0.45, n) * np.where(oon, 1.30, 1.0)
    allowed_ratio = pd.Series(plan).map({"Commercial": 0.66, "Medicare": 0.46, "Medicaid": 0.38}).to_numpy()
    allowed_ratio = np.where(oon, 0.50, allowed_ratio) * rng.normal(1, 0.05, n)
    allowed = billed * np.clip(allowed_ratio, 0.25, 0.95)
    member_share = pd.Series(plan).map({"Commercial": 0.20, "Medicare": 0.20, "Medicaid": 0.02}).to_numpy()

    # --- submission lag (a few very late submissions -> timely-filing denials)
    lag = rng.gamma(2.0, 4.0, n).round().astype(int) + 1
    late = rng.random(n) < 0.012
    lag[late] = rng.integers(95, 180, late.sum())
    submitted = service + pd.to_timedelta(lag, unit="D")

    # --- denial probability: the "story" in the data
    #   * out-of-network and inpatient claims are denied more often
    #   * missing prior-auth denials climb through 2025 (a policy change)
    #   * three providers have chronic billing problems
    problem_providers = rng.choice(providers["provider_id"], 3, replace=False)
    is_problem = prov["provider_id"].isin(problem_providers).to_numpy()
    in_2025 = service.year == 2025
    months_into_2025 = np.where(in_2025, service.month, 0)
    p_deny = (0.065
              + 0.13 * oon
              + 0.05 * (claim_type == "Inpatient")
              + 0.03 * (plan == "Medicaid")
              + 0.22 * is_problem
              + 0.006 * months_into_2025 * (claim_type != "Professional"))
    denied = (rng.random(n) < p_deny) | late

    reasons = np.full(n, "", dtype=object)
    for i in np.flatnonzero(denied):
        if late[i]:
            reasons[i] = "Timely filing"
        elif oon[i] and rng.random() < 0.55:
            reasons[i] = "Out-of-network"
        elif is_problem[i] and rng.random() < 0.6:
            reasons[i] = rng.choice(["Coding error", "Duplicate claim"], p=[0.7, 0.3])
        elif claim_type[i] != "Professional" and in_2025[i] and rng.random() < 0.5:
            reasons[i] = "Missing prior authorization"
        else:
            reasons[i] = rng.choice(
                ["Missing prior authorization", "Not medically necessary", "Coding error",
                 "Eligibility", "Duplicate claim"],
                p=[0.25, 0.22, 0.25, 0.16, 0.12])

    # claims received near the end of the data window may still be pending. Pending is drawn
    # independently of the eventual decision so recent months' denial rates are not biased.
    days_to_end = (END - submitted).days.to_numpy()
    pending = (days_to_end < 45) & (rng.random(n) < 0.6)
    status = np.where(pending, "Pending", np.where(denied, "Denied", "Paid"))
    reasons[pending] = ""

    denied = status == "Denied"
    proc_days = np.where(denied,rng.gamma(3.0, 8.0, n), rng.gamma(2.5, 5.0, n)).round().astype(int) + 2
    processed = pd.Series(submitted + pd.to_timedelta(proc_days, unit="D"))
    processed[status == "Pending"] = pd.NaT

    paid = np.where(status == "Paid", allowed * (1 - member_share), 0.0)
    allowed = np.where(status == "Denied", 0.0, allowed)

    claims = pd.DataFrame({
        "claim_id": [f"C{i:06d}" for i in range(1, n + 1)],
        "patient_id": pat["patient_id"],
        "provider_id": prov["provider_id"],
        "service_date": service,
        "submission_date": submitted,
        "processed_date": processed,
        "claim_type": claim_type,
        "diagnosis_category": diagnosis,
        "cpt_code": cpt,
        "billed_amount": billed.round(2),
        "allowed_amount": allowed.round(2),
        "paid_amount": paid.round(2),
        "claim_status": status,
        "denial_reason": reasons,
    })
    return claims.sort_values("service_date").reset_index(drop=True)


def add_mess(patients, providers, claims):
    """Inject the kinds of problems real exports have."""
    p, pr, c = patients.copy(), providers.copy(), claims.copy()

    # patients: inconsistent gender coding, a few missing states
    idx = rng.choice(len(p), 600, replace=False)
    p.loc[idx, "gender"] = p.loc[idx, "gender"].map(
        lambda g: rng.choice(["Female", "female", " f"]) if g == "F" else rng.choice(["Male", "male", "M "]))
    p.loc[rng.choice(len(p), 80, replace=False), "state"] = np.nan

    # providers: stray whitespace and casing in specialty
    idx = rng.choice(len(pr), 30, replace=False)
    pr.loc[idx, "specialty"] = pr.loc[idx, "specialty"].map(lambda s: f" {s.upper()} ")

    # claims: dates as text, some in US format
    for col in ["service_date", "submission_date", "processed_date"]:
        c[col] = c[col].dt.strftime("%Y-%m-%d")
    idx = rng.choice(len(c), int(len(c) * 0.05), replace=False)
    c.loc[idx, "service_date"] = pd.to_datetime(c.loc[idx, "service_date"]).dt.strftime("%m/%d/%Y")

    # claims: status casing, missing/negative billed amounts, blank reasons as NaN
    idx = rng.choice(len(c), 700, replace=False)
    c.loc[idx, "claim_status"] = c.loc[idx, "claim_status"].map(lambda s: rng.choice([s.lower(), s.upper()]))
    c.loc[rng.choice(len(c), 120, replace=False), "billed_amount"] = np.nan
    idx = rng.choice(len(c), 45, replace=False)
    c.loc[idx, "billed_amount"] = -c.loc[idx, "billed_amount"].abs()
    c["denial_reason"] = c["denial_reason"].replace("", np.nan)

    # claims: ~1.5% exact duplicate rows (double-submitted from the clearinghouse)
    dupes = c.sample(frac=0.015, random_state=SEED)
    c = pd.concat([c, dupes]).sample(frac=1, random_state=SEED).reset_index(drop=True)
    return p, pr, c


def main():
    patients = make_patients()
    providers = make_providers()
    claims = make_claims(patients, providers)
    patients, providers, claims = add_mess(patients, providers, claims)

    patients.to_csv(RAW / "patients.csv", index=False, date_format="%Y-%m-%d")
    providers.to_csv(RAW / "providers.csv", index=False)
    claims.to_csv(RAW / "claims.csv", index=False)
    print(f"patients: {len(patients):,}  providers: {len(providers):,}  claims: {len(claims):,}")
    print(f"written to {RAW}")


if __name__ == "__main__":
    main()
