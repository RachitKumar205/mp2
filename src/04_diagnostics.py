"""Step 4: assumption checks and supplementary analysis for the preferred model.

Covers multicollinearity (VIF, condition number), heteroskedasticity (Breusch-Pagan,
White), functional-form specification (Ramsey RESET), residual normality
(Jarque-Bera), independence (Durbin-Watson, Breusch-Godfrey), influential observations
(Cook's distance) and robustness of the conclusions to alternative samples and estimators.
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from patsy import dmatrices
from scipy import stats
from statsmodels.stats.diagnostic import acorr_breusch_godfrey, het_breuschpagan, het_white, linear_reset
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.stats.stattools import durbin_watson, jarque_bera

from config import (CLEAN_CSV, CONTROLS, FIG_DIR, FORMULAS, MODEL_VARS, PREFERRED, label,
                    save_values, write_table)
from helpers import fit, side_by_side

BLUE, ORANGE = "#2a6f97", "#d1495b"


def vif_table(formula, data) -> pd.Series:
    _, X = dmatrices(formula, data, return_type="dataframe")
    return pd.Series({c: variance_inflation_factor(X.values, i) for i, c in enumerate(X.columns)
                      if c != "Intercept"})


def white_full(m) -> tuple[float, float, int]:
    """Full White test: regress e² on the regressors, their squares and cross-products.

    statsmodels' het_white counts every generated column, but here many are duplicates
    (a 0/1 variable squared is itself) or identically zero (products of categories that
    cannot occur together). Those columns are dropped and the degrees of freedom are the
    rank of what remains, so the chi-squared test is correctly sized.
    """
    X = m.model.exog[:, 1:]  # drop the constant
    k = X.shape[1]
    cols = [X[:, i] for i in range(k)] + [X[:, i] * X[:, j] for i in range(k) for j in range(i, k)]
    Z = np.unique(np.round(np.column_stack(cols), 10), axis=1)
    Z = Z[:, Z.std(axis=0) > 0]
    aux = sm.OLS(m.resid ** 2, sm.add_constant(Z)).fit()
    df = np.linalg.matrix_rank(Z)
    lm = len(m.resid) * aux.rsquared
    return float(lm), float(stats.chi2.sf(lm, df)), int(df)


def diagnostics(name, m) -> dict:
    exog = m.model.exog
    bp = het_breuschpagan(m.resid, exog)
    wf, wfp, wdf = white_full(m)
    # Special form of the White test (Wooldridge): regress e² on ŷ and ŷ².
    wh = het_white(m.resid, sm.add_constant(m.fittedvalues))
    bg = acorr_breusch_godfrey(m, nlags=1, result_object=False)
    r2 = linear_reset(m, power=2, use_f=True)
    r23 = linear_reset(m, power=3, use_f=True)
    jb, jbp, sk, ku = jarque_bera(m.resid)
    return {"Model": name,
            "Breusch-Pagan LM": bp[0], "BP p": bp[1],
            "White (full) LM": wf, "White (full) df": wdf, "White (full) p": wfp,
            "White (special) LM": wh[0], "White p": wh[1],
            "RESET F (ŷ²)": float(r2.fvalue), "RESET p (ŷ²)": float(r2.pvalue),
            "RESET F (ŷ², ŷ³)": float(r23.fvalue), "RESET p (ŷ², ŷ³)": float(r23.pvalue),
            "Jarque-Bera": jb, "JB p": jbp, "Skew": sk, "Kurtosis": ku,
            "Durbin-Watson": durbin_watson(m.resid),
            "Breusch-Godfrey LM (lag 1)": bg[0], "BG p": bg[1],
            "Condition no.": np.linalg.cond(m.model.exog)}


def main() -> None:
    df = pd.read_csv(CLEAN_CSV)
    sample = df.dropna(subset=MODEL_VARS).sort_values("id").reset_index(drop=True)
    f_pref = FORMULAS[PREFERRED]
    ols_pref = smf.ols(f_pref, sample).fit()
    rob_pref = fit(f_pref, sample)

    # 1. Multicollinearity. Squared and interaction terms are mechanically correlated with
    # their components, so the preferred model is also estimated with mean-centred
    # edu/exper/ten. Centring changes no fitted value, only the VIFs of the components.
    c = sample.copy()
    for v in ["edu", "exper", "ten"]:
        c[v] = c[v] - c[v].mean()
    vifs = pd.DataFrame({
        "M3 (linear)": vif_table(FORMULAS["M3"], sample),
        f"{PREFERRED} (raw)": vif_table(f_pref, sample),
        f"{PREFERRED} (centred)": vif_table(f_pref, c),
    })
    vifs.index = [label(i) for i in vifs.index]
    write_table("vif", vifs.rename_axis("Variable"), floatfmt=".2f", index=True)
    ols_c = smf.ols(f_pref, c).fit()
    assert np.allclose(ols_c.fittedvalues, ols_pref.fittedvalues)

    # 2-5. Heteroskedasticity, specification, normality, independence: log vs level salary.
    f_level = f_pref.replace("lsal ~", "sal ~")
    ols_level = smf.ols(f_level, sample).fit()
    diag = pd.DataFrame([
        diagnostics("M3 log(salary), linear", smf.ols(FORMULAS["M3"], sample).fit()),
        diagnostics(f"{PREFERRED} salary in levels", ols_level),
        diagnostics(f"{PREFERRED} log(salary) — preferred", ols_pref),
    ])
    write_table("diagnostics", diag.set_index("Model").T.rename_axis("Statistic"), floatfmt=".4f", index=True)

    # Classical vs robust standard errors for the study variables.
    se = pd.DataFrame({
        "Coef.": ols_pref.params, "Classical SE": ols_pref.bse, "HC3 robust SE": rob_pref.bse,
        "Classical p": ols_pref.pvalues, "Robust p": rob_pref.pvalues,
    }).loc[["edu", "I(edu ** 2)", "exper", "I(exper ** 2)", "ten", "I(ten ** 2)", "female",
            "nonprev", "married", "female:married", "female:ten", "married:exper"]]
    se["SE ratio (robust/classical)"] = se["HC3 robust SE"] / se["Classical SE"]
    se.index = [label(i) for i in se.index]
    write_table("se_comparison", se.rename_axis("Variable"), floatfmt=".4f", index=True)

    # 6. Influential observations.
    infl = ols_pref.get_influence()
    cooks = infl.cooks_distance[0]
    cut = 4 / len(sample)
    influential = cooks > cut

    # 7. Robustness of the preferred model.
    imputed_rows = (sample["ten_gt_exper"] == 1) | (sample["edu_lt6"] == 1)
    original = sample.assign(exper=sample["exper_orig"], edu=sample["edu_orig"])
    w_aux = smf.ols("np.log(resid ** 2) ~ " + f_pref.split("~")[1],
                    sample.assign(resid=ols_pref.resid)).fit()
    weights = 1 / np.exp(w_aux.fittedvalues)
    robust = {
        PREFERRED: rob_pref,
        "M6": fit(FORMULAS["M6"], sample),
        "Original values": fit(f_pref, original),
        "Drop imputed": fit(f_pref, sample[~imputed_rows]),
        "Drop influential": fit(f_pref, sample[~influential]),
        "WLS": smf.wls(f_pref, sample, weights=weights).fit(cov_type="HC3"),
    }
    tab = side_by_side(robust)
    keep = [label(t) for t in ["edu", "I(edu ** 2)", "exper", "I(exper ** 2)", "ten", "I(ten ** 2)", "female",
                               "nonprev", "married", "female:married", "female:ten", "married:exper", "dep",
                               "metro", "itrd", "itarch",
                               "itai", "wrkhm"]] + ["N", "R²", "Adj. R²"]
    mask = tab["Variable"].isin(keep)
    mask = mask | (mask.shift(1, fill_value=False) & (tab["Variable"] == ""))
    write_table("robustness", tab[mask])

    # Figures: residual diagnostics for the preferred model.
    fitted, resid = ols_pref.fittedvalues, ols_pref.resid
    stud = infl.resid_studentized_internal
    fig, ax = plt.subplots(2, 2, figsize=(10, 8))
    ax[0, 0].scatter(fitted, resid, s=8, alpha=.5, color=BLUE)
    lw = sm.nonparametric.lowess(resid, fitted)
    ax[0, 0].plot(lw[:, 0], lw[:, 1], color=ORANGE)
    ax[0, 0].axhline(0, color="black", lw=.8)
    ax[0, 0].set(title="Residuals vs fitted", xlabel="Fitted log(salary)", ylabel="Residual")
    sm.qqplot(stud, line="45", ax=ax[0, 1], markersize=3, alpha=.6)
    ax[0, 1].set(title="Normal Q–Q (studentized residuals)")
    sl = np.sqrt(np.abs(stud))
    ax[1, 0].scatter(fitted, sl, s=8, alpha=.5, color=BLUE)
    lw = sm.nonparametric.lowess(sl, fitted)
    ax[1, 0].plot(lw[:, 0], lw[:, 1], color=ORANGE)
    ax[1, 0].set(title="Scale–location", xlabel="Fitted log(salary)", ylabel="√|studentized residual|")
    # Cook's distance bar plot with the 4/n threshold (the course's ols_plot_cooksd_bar).
    ids = sample["id"].astype(int).to_numpy()
    ax[1, 1].vlines(ids, 0, cooks, colors=np.where(influential, ORANGE, BLUE), lw=1.6)
    ax[1, 1].axhline(cut, color=ORANGE, lw=1)
    ax[1, 1].text(0.98, 0.95, f"Threshold 4/n = {cut:.4f}", transform=ax[1, 1].transAxes,
                  ha="right", va="top", color=ORANGE, fontsize=9)
    for i in np.argsort(cooks)[-3:]:
        ax[1, 1].annotate(str(ids[i]), (ids[i], cooks[i]), fontsize=8, ha="center", va="bottom")
    ax[1, 1].set(title=f"Cook's distance ({int(influential.sum())} above threshold)",
                 xlabel="Employee id", ylabel="Cook's distance")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig6_residual_diagnostics.png", dpi=200)
    plt.close(fig)

    # Level vs log specification: spread of residuals against fitted values.
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.8))
    for a, m, t in [(ax[0], ols_level, "Salary in levels"), (ax[1], ols_pref, "log(salary)")]:
        a.scatter(m.fittedvalues, m.resid, s=8, alpha=.5, color=BLUE)
        a.axhline(0, color="black", lw=.8)
        bp_p = het_breuschpagan(m.resid, m.model.exog)[1]
        a.set(title=f"{t}: Breusch–Pagan p = {bp_p:.3f}", xlabel="Fitted value", ylabel="Residual")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig7_level_vs_log.png", dpi=200)
    plt.close(fig)

    # Predicted salary profiles from the preferred model: experience, by gender and marriage,
    # other variables at their sample means (dummies at sample shares).
    grid = []
    base = sample[["edu", "ten", "dep", "nonprev", *[c for c in CONTROLS if c not in ("married", "dep")]]].mean()
    for female in (0, 1):
        for married in (0, 1):
            for e in range(1, 46):
                grid.append({**base.to_dict(), "exper": e, "female": female, "married": married})
    grid = pd.DataFrame(grid)
    pred = rob_pref.get_prediction(grid).summary_frame()
    grid["sal"] = np.exp(pred["mean"] + ols_pref.mse_resid / 2)
    fig, ax = plt.subplots(figsize=(7, 4.2))
    styles = {(0, 0): (BLUE, "--", "Single men"), (0, 1): (BLUE, "-", "Married men"),
              (1, 0): (ORANGE, "--", "Single women"), (1, 1): (ORANGE, "-", "Married women")}
    for (fe, ma), (col, ls, lab) in styles.items():
        g = grid[(grid.female == fe) & (grid.married == ma)]
        ax.plot(g["exper"], g["sal"], color=col, ls=ls, label=lab, lw=2)
    ax.set(xlabel="Years of professional experience", ylabel="Predicted hourly salary",
           title=f"Predicted salary profiles ({PREFERRED}, other variables at sample means)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig8_predicted_profiles.png", dpi=200)
    plt.close(fig)

    d = diag.set_index("Model")
    lvl, pr, m3 = d.loc[f"{PREFERRED} salary in levels"], d.loc[f"{PREFERRED} log(salary) — preferred"], d.iloc[0]
    save_values({k: (round(float(x), 4) if isinstance(x, (float, np.floating)) else x) for k, x in {
        "vif_max_M3": vifs["M3 (linear)"].max(), "vif_max_raw": vifs[f"{PREFERRED} (raw)"].max(),
        "vif_max_centred_main": vifs[f"{PREFERRED} (centred)"].drop(
            [label(t) for t in ["I(edu ** 2)", "I(exper ** 2)", "I(ten ** 2)", "female:married"]]).max(),
        "vif_max_centred": vifs[f"{PREFERRED} (centred)"].max(),
        "bp_level": lvl["Breusch-Pagan LM"], "bp_level_p": lvl["BP p"],
        "bp_log": pr["Breusch-Pagan LM"], "bp_log_p": pr["BP p"],
        "white_level_p": lvl["White p"], "white_log": pr["White (special) LM"], "white_log_p": pr["White p"],
        "reset_m3_p": m3["RESET p (ŷ², ŷ³)"], "reset_log_p": pr["RESET p (ŷ², ŷ³)"],
        "reset_log_p2": pr["RESET p (ŷ²)"], "reset_level_p": lvl["RESET p (ŷ², ŷ³)"],
        "jb_log": pr["Jarque-Bera"], "jb_log_p": pr["JB p"], "skew_resid": pr["Skew"], "kurt_resid": pr["Kurtosis"],
        "jb_level": lvl["Jarque-Bera"], "skew_resid_level": lvl["Skew"],
        "dw": pr["Durbin-Watson"], "bg": pr["Breusch-Godfrey LM (lag 1)"], "bg_p": pr["BG p"],
        "white_full_log": pr["White (full) LM"], "white_full_log_p": pr["White (full) p"],
        "white_full_log_df": pr["White (full) df"], "white_full_level_p": lvl["White (full) p"],
        "white_full_m3_p": m3["White (full) p"], "cond_raw": pr["Condition no."], "cond_centred": np.linalg.cond(ols_c.model.exog),
        "n_influential": int(influential.sum()), "cooks_cut": cut, "cooks_max": float(cooks.max()),
        "se_ratio_max": se["SE ratio (robust/classical)"].max(), "se_ratio_min": se["SE ratio (robust/classical)"].min(),
        "reset_m6_p": float(linear_reset(smf.ols(FORMULAS["M6"], sample).fit(), power=3, use_f=True).pvalue),
    }.items()})
    print(f"diagnostics: BP p (log) = {pr['BP p']:.3f}, RESET p = {pr['RESET p (ŷ², ŷ³)']:.3f}, "
          f"max VIF centred = {vifs[f'{PREFERRED} (centred)'].max():.2f}")


if __name__ == "__main__":
    main()
