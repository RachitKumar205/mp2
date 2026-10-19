"""Step 1: clean ITEmp.xlsx.

Invalid cells (R1-R5) are set to missing and logged. Two groups of implausible but
non-missing values are then imputed (R6, R7); their original values are kept in
`exper_orig` / `edu_orig` so the imputation can be audited and reversed in the
robustness check.
"""

import numpy as np
import pandas as pd

from config import CLEAN_CSV, DUMMIES, IT_DIV, IT_GROUP, REGION, save_values, write_table

# Plausible ranges for count variables (inclusive).
RANGES = {
    "edu": (0, 20), "momed": (0, 20), "daded": (0, 20),
    "exper": (0, 60), "ten": (0, 60), "dep": (0, 15), "sib": (0, 15),
}


def main() -> None:
    from config import RAW_XLSX

    raw = pd.read_excel(RAW_XLSX, sheet_name="Salary")
    raw.columns = [c.strip() for c in raw.columns]
    df = raw.copy()
    log = []

    def drop(col, mask, rule):
        for i in df.index[mask]:
            log.append({"id": int(df.at[i, "id"]), "variable": col,
                        "raw value": str(raw.at[i, col]), "rule": rule})
        df.loc[mask, col] = np.nan

    blanks = raw.isna().sum()

    # R1: text where a number is expected.
    for col in df.columns:
        num = pd.to_numeric(df[col], errors="coerce")
        drop(col, num.isna() & df[col].notna(), "R1 non-numeric entry")
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # R2: dummy variables must be 0 or 1.
    for col in DUMMIES:
        drop(col, df[col].notna() & ~df[col].isin([0, 1]), "R2 dummy not in {0,1}")

    # R3: implausible counts of years / people.
    for col, (lo, hi) in RANGES.items():
        drop(col, df[col].notna() & ~df[col].between(lo, hi), f"R3 outside [{lo}, {hi}]")

    # R4: an hourly salary must be positive.
    drop("sal", df["sal"].notna() & (df["sal"] <= 0), "R4 non-positive salary")

    # R5: gross salary errors. Tukey fence on log(sal) (salary is log-normal, so the
    # fence is applied on the log scale rather than on the raw, skewed scale).
    lsal = np.log(df["sal"].dropna())
    q1, q3 = lsal.quantile([0.25, 0.75])
    fence = float(np.exp(q3 + 1.5 * (q3 - q1)))
    below = df.loc[df["sal"] <= fence, "sal"].max()
    drop("sal", df["sal"] > fence, f"R5 salary above log-scale fence ({fence:.2f})")

    df["lsal"] = np.log(df["sal"])

    # Imputation. Original values are kept for the robustness check in 04_diagnostics.py.
    df["exper_orig"], df["edu_orig"] = df["exper"], df["edu"]
    imputed = []

    # R6: years at HCL count as professional experience, so experience can never be
    # below tenure. Raise experience to tenure (the smallest consistent correction).
    m6 = df["ten"] > df["exper"]
    for i in df.index[m6]:
        imputed.append({"id": int(df.at[i, "id"]), "variable": "exper", "original": df.at[i, "exper"],
                        "imputed": df.at[i, "ten"], "rule": "R6 experience raised to tenure"})
    df.loc[m6, "exper"] = df.loc[m6, "ten"]
    df["ten_gt_exper"] = m6.astype(int)

    # R7: education below 6 years is implausible for an IT employee. Replace it with the
    # median education of employees in the same experience band (education >= 6).
    bands = pd.cut(df["exper"], [0, 10, 20, 30, 40, 60])
    band_median = df.loc[df["edu"] >= 6].groupby(bands, observed=True)["edu"].median()
    m7 = df["edu"] < 6
    for i in df.index[m7]:
        new = float(band_median[bands[i]])
        imputed.append({"id": int(df.at[i, "id"]), "variable": "edu", "original": df.at[i, "edu"],
                        "imputed": new, "rule": f"R7 median education, experience band {bands[i]}"})
        df.at[i, "edu"] = new
    df["edu_lt6"] = m7.astype(int)
    imputed = pd.DataFrame(imputed)

    # Mutually exclusive dummy sets: verify before choosing reference categories.
    sets = {"Region": REGION, "IT work group": IT_GROUP, "IT division": IT_DIV}
    excl = []
    for name, cols in sets.items():
        s = df[cols].sum(axis=1, min_count=1)
        excl.append({"Dummy set": name, "Variables": ", ".join(cols),
                     "Rows with >1 category": int((s > 1).sum()),
                     "Reference (all zero)": int((s == 0).sum())})
    excl = pd.DataFrame(excl)
    assert (excl["Rows with >1 category"] == 0).all(), "dummy sets overlap"

    log = pd.DataFrame(log).sort_values(["variable", "id"])
    df.to_csv(CLEAN_CSV, index=False)

    # Tables for the report.
    write_table("cleaning_log", log[["variable", "id", "raw value", "rule"]])
    by_rule = log.groupby("rule").size().rename("cells").reset_index()
    write_table("cleaning_by_rule", by_rule)
    miss = pd.DataFrame({
        "blank in raw file": blanks.drop(["id"]),
        "set to missing": log.groupby("variable").size().reindex(blanks.index.drop("id")).fillna(0).astype(int),
    })
    miss["missing after cleaning"] = df[miss.index].isna().sum()
    miss = miss[(miss.sum(axis=1)) > 0].rename_axis("variable")
    write_table("missingness", miss, index=True)
    write_table("dummy_sets", excl)
    write_table("imputation_log", imputed[["variable", "id", "original", "imputed", "rule"]], floatfmt=".0f")

    flagged = df.loc[df["ten_gt_exper"] == 1, "id"].astype(int).tolist()
    save_values({
        "n_raw": len(raw), "n_vars": raw.shape[1],
        "cells_fixed": len(log), "rows_fixed": log["id"].nunique(),
        "sal_fence": round(fence, 2), "sal_max_kept": float(below),
        "n_sal_valid": int(df["sal"].notna().sum()),
        "n_complete": int(df[list(raw.columns) + ["lsal"]].dropna().shape[0]),
        "n_imputed_exper": int(m6.sum()), "n_imputed_edu": int(m7.sum()),
        "n_ten_gt_exper": len(flagged), "ids_ten_gt_exper": ", ".join(map(str, flagged)),
        "sal_removed": ", ".join(log.loc[log.variable == "sal", "raw value"]),
    })
    print(f"cleaned: {len(log)} cells set to missing in {log['id'].nunique()} rows; fence={fence:.2f}; "
          f"imputed {int(m6.sum())} exper and {int(m7.sum())} edu values")


if __name__ == "__main__":
    main()
