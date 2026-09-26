"""
Rebuild the whole project from scratch:

    python run_all.py

1. generate raw data        -> Data/raw/
2. clean it (notebook 01)   -> Data/clean/
3. explore it (notebook 02) -> Image/*.png
4. load SQLite + run SQL    -> Data/claims.db, SQL/query_results.md
5. build the Excel workbook -> Excel/Healthcare_Claims_Analysis.xlsx
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = ROOT / "Python"

STEPS = [
    [sys.executable, PY / "generate_data.py"],
    [sys.executable, "-m", "jupyter", "nbconvert", "--to", "notebook", "--execute", "--inplace",
     PY / "01_data_cleaning.ipynb", PY / "02_exploratory_analysis.ipynb"],
    [sys.executable, PY / "load_to_sqlite.py"],
    [sys.executable, PY / "run_sql_queries.py"],
    [sys.executable, PY / "build_excel.py"],
]

for step in STEPS:
    print(f"\n>>> {' '.join(Path(str(s)).name for s in step[1:])}")
    subprocess.run([str(s) for s in step], check=True, cwd=ROOT)
print("\nDone.")
