# MP2: Salary evaluation for HCL Technologies

Our DOM207 MP2 project. HCL gave us a file of 526 employees (`ITEmp.xlsx`) and asked
what drives their hourly salaries. The write-up is in
[`report/MP2_Report.pdf`](report/MP2_Report.pdf); this repo holds the code behind it.

## Running it

You need Python 3.14 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

```bash
uv run python src/run_all.py
```

This rebuilds every table and figure from the raw file. To rebuild the PDF as well (needs
pandoc and pdflatex):

```bash
uv run python src/build_report.py
```

## What's where

| Path | What it is |
|---|---|
| `src/01_clean.py` | Cleans the data and logs every change |
| `src/02_eda.py` | Descriptive statistics, correlations and the exploratory figures |
| `src/03_models.py` | Models M1 to M7, effects at typical values, held-out MSE |
| `src/04_diagnostics.py` | Assumption tests, Cook's distance and robustness checks |
| `src/config.py`, `src/helpers.py` | Shared settings, model formulas and table helpers |
| `report/report.md` | The report text, built into the PDF |
| `output/tables/`, `output/figures/` | Everything the scripts produce |

## What we did

- **Cleaning.** We set 31 obviously wrong values to missing, such as a salary of 1111 per
  hour and 1001 years of education. We fixed 24 values that were possible but implausible:
  experience was raised to match tenure, and education under 6 years became 12. The
  originals are kept, and the results barely change without the fixes.
- **Models.** We regressed log hourly salary on education, experience and tenure, then
  added gender, the controls, squared terms and interactions one block at a time. The
  final model, M7, keeps three interactions: female × married, female × tenure and
  married × experience. It explains 58% of the variation and predicts held-out employees
  better than the other models.
- **Checks.** We covered everything from the lecture slides: VIF, Breusch–Pagan and White,
  RESET, Jarque–Bera with a Q–Q plot, Durbin–Watson with Breusch–Godfrey, and Cook's
  distance. We also re-ran M7 without the imputed and the most influential employees.

## What we found

- Women earn about 10% to 34% less than comparable men. The gap is larger for married
  women and grows with each year at HCL.
- Married men get a premium of up to 26%; married women get none.
- Each extra year of education is worth more than the last. Part of that comes from
  educated staff ending up in R&D, which pays about 22% more.
- Architecture and AI roles pay about 27% less than other IT work.
- We found no evidence of a pay difference by province or non-privileged status, or of
  any effect of family background.

The full reasoning, tables and recommendations are in the report.
