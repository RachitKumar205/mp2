"""Step 3: the model ladder, quadratic and interaction effects, and the alternative
models for the subsidiary (indirect) influences of the study variables.

All models are OLS on log(salary) with HC3 heteroskedasticity-robust standard errors.
Models M1-M6 share one estimation sample so that their fit can be compared directly.
"""

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from config import (BACKGROUND, CLEAN_CSV, CTRL, FORMULAS, MODEL_VARS, PREFERRED, STUDY,
                    label, save_values, write_table)
from helpers import fit, pct, side_by_side, sig_table, stars


def wald(m, hypothesis: str):
    w = m.wald_test(hypothesis, scalar=True)
    return float(w.statistic), float(w.pvalue), hypothesis.count("=")


def main() -> None:
    df = pd.read_csv(CLEAN_CSV)
    sample = df.dropna(subset=MODEL_VARS).copy()
    ladder = {k: fit(f, sample) for k, f in FORMULAS.items()}
    pref = ladder[PREFERRED]

    write_table("models_ladder", side_by_side(ladder))
    write_table("sig_preferred", sig_table(pref), floatfmt=".4f")
    write_table("sig_M3", sig_table(ladder["M3"]), floatfmt=".4f")

    # Out-of-sample check: fit each model on 80% of employees and measure the mean squared
    # error (MSE) of log salary on the 20% held out; 10-fold cross-validation confirms it.
    rng = np.random.default_rng(2026)
    order = rng.permutation(len(sample))
    test, train = sample.iloc[order[: len(sample) // 5]], sample.iloc[order[len(sample) // 5:]]
    folds = np.array_split(rng.permutation(len(sample)), 10)
    validation = []
    for k, f in FORMULAS.items():
        m = smf.ols(f, train).fit()
        cv = [np.mean((sample.iloc[fold]["lsal"]
                       - smf.ols(f, sample.drop(sample.index[fold])).fit().predict(sample.iloc[fold])) ** 2)
              for fold in folds]
        validation.append({"Model": k, "Training MSE": np.mean(m.resid ** 2),
                           "Held-out MSE": np.mean((test["lsal"] - m.predict(test)) ** 2),
                           "10-fold CV MSE": np.mean(cv)})
    validation = pd.DataFrame(validation)
    write_table("validation", validation, floatfmt=".4f")

    # Nested comparisons: classical F-test on the same sample (OLS fits) plus fit criteria.
    ols = {k: smf.ols(f, sample).fit() for k, f in FORMULAS.items()}
    nested = []
    for small, big, what in [("M1", "M2", "female, non-privileged"), ("M2", "M3", "control variables"),
                             ("M3", "M4", "quadratic terms"), ("M4", "M5", "all seven candidate interactions"),
                             ("M4", "M6", "female × married"), ("M6", "M7", "female × tenure, married × experience"),
                             ("M7", "M5", "four interactions dropped from M5")]:
        f, p, ddf = ols[big].compare_f_test(ols[small])
        nested.append({"Restricted": small, "Unrestricted": big, "Terms added": what,
                       "F": f, "df": int(ddf), "p-value": p,
                       "ΔAdj. R²": ols[big].rsquared_adj - ols[small].rsquared_adj,
                       "ΔAIC": ols[big].aic - ols[small].aic})
    write_table("nested_tests", pd.DataFrame(nested), floatfmt=".4f")

    # Joint (robust Wald) tests of groups of variables in the preferred model.
    groups = {
        "Region (norcen, south, west)": "norcen = 0, south = 0, west = 0",
        "IT work group (6 dummies)": "itreq = 0, itprog = 0, itqual = 0, itarch = 0, itai = 0, itclient = 0",
        "IT division (itrd, ittech)": "itrd = 0, ittech = 0",
        "Experience + Experience²": "exper = 0, I(exper ** 2) = 0",
        "Tenure + Tenure²": "ten = 0, I(ten ** 2) = 0",
        "Education + Education²": "edu = 0, I(edu ** 2) = 0",
        "All quadratic terms": "I(edu ** 2) = 0, I(exper ** 2) = 0, I(ten ** 2) = 0",
        "All terms involving Female": "female = 0, female:married = 0, female:ten = 0",
        "All terms involving Married": "married = 0, female:married = 0, married:exper = 0",
        "All interaction terms": "female:married = 0, female:ten = 0, married:exper = 0",
        "Family: married, dependents": "married = 0, dep = 0",
    }
    joint = []
    for name, h in groups.items():
        w, p, dfn = wald(pref, h)
        joint.append({"Hypothesis (all = 0)": name, "Wald χ²": w, "df": dfn, "p-value": p, "Sig.": stars(p)})
    write_table("joint_tests", pd.DataFrame(joint), floatfmt=".4f")

    # Quadratics: marginal effects and turning points.
    b = pref.params
    means = sample[["edu", "exper", "ten"]].mean()
    quad = []
    for v in ["edu", "exper", "ten"]:
        b1, b2 = b[v], b[f"I({v} ** 2)"]
        rows = {"Variable": label(v), "Linear": f"{b1:.4f}", "Squared": f"{b2:.5f}",
                "Turning point (yrs)": f"{-b1 / (2 * b2):.1f}",
                "Data range": f"{sample[v].min():.0f}–{sample[v].max():.0f}"}
        for name, q in [("P25", .25), ("Median", .5), ("P75", .75)]:
            at = sample[v].quantile(q)
            rows[f"% per +1 yr at {name}"] = f"{100 * (b1 + 2 * b2 * at):.2f} (at {at:.0f})"
        quad.append(rows)
    quad = pd.DataFrame(quad)
    write_table("quadratic_effects", quad, numparse=False)
    tp_exper = -b["exper"] / (2 * b["I(exper ** 2)"])
    share_past_tp = float((sample["exper"] > tp_exper).mean())

    # Interactions: conditional (marginal) effects with robust SEs. With interactions in the
    # model, the coefficient on e.g. `female` alone is only the gap at married = 0, ten = 0.
    def lincom(weights: dict):
        r = np.array([weights.get(t, 0.0) for t in pref.params.index])
        t = pref.t_test(r)
        return float(t.effect[0]), float(t.sd[0, 0]), float(t.pvalue)

    me = []
    for st, m in [("single", 0), ("married", 1)]:
        for ten in (0, 5, 10):
            me.append(("Gender gap (female − male)", f"{st}, tenure {ten}",
                       {"female": 1, "female:married": m, "female:ten": ten}))
    for g, f in [("men", 0), ("women", 1)]:
        for ex in (5, 15, 25):
            me.append(("Marriage premium (married − single)", f"{g}, experience {ex}",
                       {"married": 1, "female:married": f, "married:exper": ex}))
    me.append(("Extra salary per tenure year (at tenure 0)", "men", {"ten": 1}))
    me.append(("Extra salary per tenure year (at tenure 0)", "women", {"ten": 1, "female:ten": 1}))
    rows = []
    for effect, at, w in me:
        est, se, p = lincom(w)
        rows.append({"Effect": effect, "Evaluated for": at, "Log points": est, "Robust SE": se,
                     "p-value": p, "% effect": pct(est), "Sig.": stars(p)})
    me = pd.DataFrame(rows)
    write_table("interaction_effects", me, floatfmt=".4f")
    eff = {(r["Effect"].split(" (")[0], r["Evaluated for"]): r for _, r in me.iterrows()}

    # Subsidiary influences: how each study coefficient moves as blocks of controls are
    # added. A coefficient that shrinks when a block enters works partly *through* that block.
    path_specs = {
        "Female only": "lsal ~ female",
        "Human capital only (M1)": FORMULAS["M1"],
        "Study IVs (M2)": FORMULAS["M2"],
        "+ family & location": f"lsal ~ {STUDY} + married + dep + metro + norcen + south + west + wrkhm",
        "+ IT work group & division (M3)": FORMULAS["M3"],
    }
    path = []
    for name, f in path_specs.items():
        m = fit(f, sample)
        row = {"Specification": name}
        for v in ["edu", "exper", "ten", "female"]:
            row[label(v).split(" (")[0]] = (f"{m.params[v]:.4f}{stars(m.pvalues[v])}" if v in m.params else "")
        row["Adj. R²"] = f"{m.rsquared_adj:.3f}"
        path.append(row)
    path = pd.DataFrame(path)
    write_table("coef_path", path, numparse=False)
    gap = pd.DataFrame({"Female coef.": [fit("lsal ~ female", sample).params["female"]]})

    # Job sorting: are women allocated to different IT groups / divisions? (linear probability models)
    sort_rows = []
    for v in ["itarch", "itai", "itrd", "itprog", "itclient", "ittech"]:
        m = fit(f"{v} ~ female + edu + exper + ten", sample)
        sort_rows.append({"Outcome (1 if in ...)": label(v),
                          "Female": f"{m.params['female']:.4f}{stars(m.pvalues['female'])}",
                          "Education": f"{m.params['edu']:.4f}{stars(m.pvalues['edu'])}",
                          f"Salary effect of group in {PREFERRED} (%)": f"{pct(pref.params[v]):.1f}"})
    write_table("job_sorting", pd.DataFrame(sort_rows), numparse=False)

    # Family background: indirect effect through education (mediation chain).
    bg = df.dropna(subset=MODEL_VARS + BACKGROUND).copy()
    bgv = " + ".join(BACKGROUND)
    rhs_pref = FORMULAS[PREFERRED].split("~")[1]
    rhs_no_edu = rhs_pref.replace("edu + ", "").replace(" + I(edu ** 2)", "").replace(" + female:edu", "")
    alt = {
        "A1 Education equation": fit(f"edu ~ {bgv} + female + exper + ten + metro + {' + '.join(['norcen','south','west'])}", bg),
        "A2 Reduced form (no edu)": fit(f"lsal ~ {rhs_no_edu} + {bgv}", bg),
        "A3 Preferred + background": fit(f"lsal ~ {rhs_pref} + {bgv}", bg),
        "A4 Preferred (same sample)": fit(FORMULAS[PREFERRED], bg),
    }
    write_table("alt_background", side_by_side(alt))
    bg_tests = []
    for k in ["A1 Education equation", "A2 Reduced form (no edu)", "A3 Preferred + background"]:
        w, p, dfn = wald(alt[k], "momed = 0, daded = 0, sib = 0")
        bg_tests.append({"Model": k, "Joint test momed = daded = sib = 0 (Wald χ², 3 df)": w, "p-value": p,
                         "Sig.": stars(p)})
    write_table("background_tests", pd.DataFrame(bg_tests), floatfmt=".4f")

    # Key numbers quoted in the report text.
    v = {
        "n_model": int(pref.nobs), "n_bg": int(alt["A3 Preferred + background"].nobs),
        "r2_M1": ladder["M1"].rsquared_adj, "r2_M3": ladder["M3"].rsquared_adj,
        "r2_pref": pref.rsquared_adj, "r2_M5": ladder["M5"].rsquared_adj,
        "female_raw_pct": pct(gap.iloc[0]["Female coef."]), "female_M3_pct": pct(ladder["M3"].params["female"]),
        **{f"gap_{st}_t{t}_pct": eff[("Gender gap", f"{st}, tenure {t}")]["% effect"]
           for st in ("single", "married") for t in (0, 5, 10)},
        **{f"gap_{st}_t{t}_p": eff[("Gender gap", f"{st}, tenure {t}")]["p-value"]
           for st in ("single", "married") for t in (0, 5, 10)},
        **{f"mprem_{g}_x{x}_pct": eff[("Marriage premium", f"{g}, experience {x}")]["% effect"]
           for g in ("men", "women") for x in (5, 15, 25)},
        **{f"mprem_{g}_x{x}_p": eff[("Marriage premium", f"{g}, experience {x}")]["p-value"]
           for g in ("men", "women") for x in (5, 15, 25)},
        "ten_ret_men": 100 * b["ten"], "ten_ret_women": 100 * (b["ten"] + b["female:ten"]),
        "ten_ret_women_p": eff[("Extra salary per tenure year", "women")]["p-value"],
        "fxm_coef": b["female:married"], "fxm_p": pref.pvalues["female:married"],
        "fxt_coef": b["female:ten"], "fxt_p": pref.pvalues["female:ten"],
        "mxe_coef": b["married:exper"], "mxe_p": pref.pvalues["married:exper"],
        "r2_M4": ladder["M4"].rsquared_adj, "r2_M6": ladder["M6"].rsquared_adj,
        **{f"mse_test_{r.Model}": r["Held-out MSE"] for _, r in validation.iterrows()},
        **{f"mse_cv_{r.Model}": r["10-fold CV MSE"] for _, r in validation.iterrows()},
        "edu_M3_pct": 100 * ladder["M3"].params["edu"], "ten_M3_pct": 100 * ladder["M3"].params["ten"],
        "exper_M3_pct": 100 * ladder["M3"].params["exper"], "exper_M3_p": ladder["M3"].pvalues["exper"],
        "tp_exper": tp_exper, "tp_exper_married": -(b["exper"] + b["married:exper"]) / (2 * b["I(exper ** 2)"]),
        "edu_rd_pp": 100 * fit("itrd ~ female + edu + exper + ten", sample).params["edu"],
        "edu_M2_coef": ladder["M2"].params["edu"], "edu_M3_coef": ladder["M3"].params["edu"],
        "female_M2_pct": pct(ladder["M2"].params["female"]), "share_past_tp_exper": 100 * share_past_tp,
        "tp_ten": -b["ten"] / (2 * b["I(ten ** 2)"]), "tp_edu": -b["edu"] / (2 * b["I(edu ** 2)"]),
        "edu_me_mean": 100 * (b["edu"] + 2 * b["I(edu ** 2)"] * means["edu"]),
        "edu_me_12": 100 * (b["edu"] + 2 * b["I(edu ** 2)"] * 12),
        "edu_me_16": 100 * (b["edu"] + 2 * b["I(edu ** 2)"] * 16),
        "exper_me_5": 100 * (b["exper"] + 2 * b["I(exper ** 2)"] * 5),
        "exper_me_20": 100 * (b["exper"] + 2 * b["I(exper ** 2)"] * 20),
        "ten_me_0": 100 * b["ten"], "ten_me_10": 100 * (b["ten"] + 2 * b["I(ten ** 2)"] * 10),
        "mean_edu": means["edu"], "mean_exper": means["exper"], "mean_ten": means["ten"],
        "nonprev_pct": pct(b["nonprev"]), "nonprev_p": pref.pvalues["nonprev"],
        "metro_pct": pct(b["metro"]), "itrd_pct": pct(b["itrd"]), "itarch_pct": pct(b["itarch"]),
        "itai_pct": pct(b["itai"]), "wrkhm_pct": pct(b["wrkhm"]), "wrkhm_p": pref.pvalues["wrkhm"],
        "dep_pct": 100 * b["dep"], "dep_p": pref.pvalues["dep"],
        "edu_bg_A3_vs_A4": alt["A3 Preferred + background"].params["edu"] - alt["A4 Preferred (same sample)"].params["edu"],
        "momed_on_edu": alt["A1 Education equation"].params["momed"],
        "daded_on_edu": alt["A1 Education equation"].params["daded"],
        "sib_on_edu": alt["A1 Education equation"].params["sib"],
    }
    for k, (s, bgg, w) in {f"F_{r['Restricted']}_{r['Unrestricted']}": (r["F"], r["p-value"], r["df"]) for r in nested}.items():
        v[k], v[k + "_p"], v[k + "_df"] = s, bgg, w
    for r in joint:
        key = "joint_" + "".join(ch for ch in r["Hypothesis (all = 0)"].split(" (")[0].lower() if ch.isalnum())
        v[key], v[key + "_p"] = r["Wald χ²"], r["p-value"]
    save_values({k: (round(float(x), 4) if isinstance(x, (float, np.floating)) else x) for k, x in v.items()})
    print(f"models: N={int(pref.nobs)}, adj R2 {PREFERRED}={pref.rsquared_adj:.3f}")


if __name__ == "__main__":
    main()
