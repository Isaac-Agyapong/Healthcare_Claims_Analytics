"""Create Data/claims.db from SQL/01_schema.sql and load the clean CSVs into it."""
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "Data" / "clean"
DB = ROOT / "Data" / "claims.db"

CLAIM_COLUMNS = ["claim_id", "patient_id", "provider_id", "service_date", "submission_date",
                 "processed_date", "claim_type", "diagnosis_category", "cpt_code", "billed_amount",
                 "allowed_amount", "paid_amount", "claim_status", "denial_reason", "billed_imputed"]


def main():
    patients = pd.read_csv(CLEAN / "patients_clean.csv")
    providers = pd.read_csv(CLEAN / "providers_clean.csv")
    # the clean claims file also carries convenience columns for Excel/Power BI;
    # the database keeps only the fact columns and gets the rest through joins
    claims = pd.read_csv(CLEAN / "claims_clean.csv", dtype={"cpt_code": str})[CLAIM_COLUMNS]
    claims["billed_imputed"] = claims["billed_imputed"].astype(int)

    with sqlite3.connect(DB) as con:
        con.executescript((ROOT / "SQL" / "01_schema.sql").read_text())
        patients.to_sql("patients", con, if_exists="append", index=False)
        providers.to_sql("providers", con, if_exists="append", index=False)
        claims.to_sql("claims", con, if_exists="append", index=False)
        for table in ["patients", "providers", "claims"]:
            print(f"{table:<10} {con.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]:>7,} rows")
    print(f"database: {DB.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
