"""Estimation and table helpers shared by the modelling scripts."""

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from config import label


def stars(p):
    return "***" if p < .01 else "**" if p < .05 else "*" if p < .10 else ""


def fit(formula, data):
    return smf.ols(formula, data).fit(cov_type="HC3")


def pct(b):
    """Exact percentage effect of a dummy in a log model: 100 * (exp(b) - 1)."""
    return 100 * (np.exp(b) - 1)


def side_by_side(models: dict) -> pd.DataFrame:
    """Coefficients with stars and robust SEs (in parentheses), one column per model."""
    terms = list(dict.fromkeys(t for m in models.values() for t in m.params.index))
    rows = []
    for t in terms:
        coef, se = {"Variable": label(t)}, {"Variable": ""}
        for k, m in models.items():
            if t in m.params:
                coef[k] = f"{m.params[t]:.4f}{stars(m.pvalues[t])}"
                se[k] = f"({m.bse[t]:.4f})"
            else:
                coef[k] = se[k] = ""
        rows += [coef, se]
    for name, f in [("N", lambda m: f"{int(m.nobs)}"), ("R²", lambda m: f"{m.rsquared:.3f}"),
                    ("Adj. R²", lambda m: f"{m.rsquared_adj:.3f}"), ("AIC", lambda m: f"{m.aic:.1f}"),
                    ("BIC", lambda m: f"{m.bic:.1f}"),
                    ("Robust F", lambda m: f"{m.fvalue:.2f}{stars(m.f_pvalue)}")]:
        rows.append({"Variable": name, **{k: f(m) for k, m in models.items()}})
    return pd.DataFrame(rows)


def sig_table(m) -> pd.DataFrame:
    ci = m.conf_int()
    return pd.DataFrame({
        "Variable": [label(t) for t in m.params.index],
        "Coef.": m.params.values, "Robust SE": m.bse.values, "z": m.tvalues.values,
        "p-value": m.pvalues.values, "95% CI low": ci[0].values, "95% CI high": ci[1].values,
        "Sig.": [stars(p) for p in m.pvalues],
    })
