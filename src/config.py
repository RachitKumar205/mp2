"""Shared paths, variable groups, model formulas and small helpers for the MP2 pipeline."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_XLSX = ROOT / "data" / "raw" / "ITEmp.xlsx"
CLEAN_CSV = ROOT / "data" / "processed" / "ITEmp_clean.csv"
FIG_DIR = ROOT / "output" / "figures"
TAB_DIR = ROOT / "output" / "tables"
VALUES_JSON = ROOT / "output" / "values.json"

# Variable groups (column names as they appear after cleaning).
DUMMIES = [
    "nonprev", "female", "married", "metro", "norcen", "south", "west",
    "itreq", "itprog", "itqual", "itarch", "itai", "itclient",
    "itrd", "ittech", "wrkhm",
]
REGION = ["norcen", "south", "west"]  # base: other (eastern) provinces
IT_GROUP = ["itreq", "itprog", "itqual", "itarch", "itai", "itclient"]  # base: other IT work
IT_DIV = ["itrd", "ittech"]  # base: other divisions
BACKGROUND = ["momed", "daded", "sib"]

LABELS = {
    "Intercept": "Intercept",
    "edu": "Education (yrs)", "exper": "Experience (yrs)", "ten": "Tenure (yrs)",
    "female": "Female", "nonprev": "Non-privileged", "married": "Married",
    "dep": "Dependents", "metro": "Metro area", "norcen": "North-central",
    "south": "South", "west": "West", "itreq": "IT requirements",
    "itprog": "IT programming", "itqual": "IT quality assurance",
    "itarch": "IT architecture", "itai": "AI applications",
    "itclient": "Client-only work", "itrd": "R&D division",
    "ittech": "Tech support division", "wrkhm": "Works from home",
    "momed": "Mother's education", "daded": "Father's education",
    "sib": "Siblings",
    "I(exper ** 2)": "Experience²", "I(ten ** 2)": "Tenure²", "I(edu ** 2)": "Education²",
    "female:married": "Female × Married", "female:edu": "Female × Education",
    "female:exper": "Female × Experience", "edu:exper": "Education × Experience",
    "female:nonprev": "Female × Non-privileged", "female:ten": "Female × Tenure",
    "married:exper": "Married × Experience",
}


def label(term: str) -> str:
    return LABELS.get(term, term)


def save_values(new: dict) -> None:
    """Merge key numbers into values.json (the headline figures quoted in README.md)."""
    VALUES_JSON.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(VALUES_JSON.read_text()) if VALUES_JSON.exists() else {}
    data.update(new)
    VALUES_JSON.write_text(json.dumps(data, indent=2, sort_keys=True))


def write_table(name: str, df, floatfmt=".3f", index=False, numparse=True) -> None:
    """Write a table as Markdown and CSV. numparse=False keeps
    pre-formatted strings exactly as given."""
    TAB_DIR.mkdir(parents=True, exist_ok=True)
    md = df.to_markdown(index=index, floatfmt=floatfmt, disable_numparse=not numparse)
    (TAB_DIR / f"{name}.md").write_text(md + "\n")
    df.to_csv(TAB_DIR / f"{name}.csv", index=index)

# Model specifications (shared by 03_models.py and 04_diagnostics.py).
CONTROLS = ["married", "dep", "metro", *REGION, *IT_GROUP, *IT_DIV, "wrkhm"]
HC = "edu + exper + ten"
STUDY = HC + " + female + nonprev"
CTRL = " + ".join(CONTROLS)
QUAD = "I(edu ** 2) + I(exper ** 2) + I(ten ** 2)"
INTER_ALL = ("female:married + female:edu + female:exper + female:ten + edu:exper"
             " + married:exper + female:nonprev")
FORMULAS = {
    "M1": f"lsal ~ {HC}",
    "M2": f"lsal ~ {STUDY}",
    "M3": f"lsal ~ {STUDY} + {CTRL}",
    "M4": f"lsal ~ {STUDY} + {CTRL} + {QUAD}",
    "M5": f"lsal ~ {STUDY} + {CTRL} + {QUAD} + {INTER_ALL}",
    "M6": f"lsal ~ {STUDY} + {CTRL} + {QUAD} + female:married",
    "M7": f"lsal ~ {STUDY} + {CTRL} + {QUAD} + female:married + female:ten + married:exper",
}
PREFERRED = "M7"
MODEL_VARS = ["lsal", "edu", "exper", "ten", "female", "nonprev", *CONTROLS]
