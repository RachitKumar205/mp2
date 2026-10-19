"""Run the full MP2 analysis from the raw Excel file to every table and figure."""

import runpy
from pathlib import Path

HERE = Path(__file__).resolve().parent

for step in ["01_clean.py", "02_eda.py", "03_models.py", "04_diagnostics.py"]:
    print(f"== {step}")
    runpy.run_path(str(HERE / step), run_name="__main__")
