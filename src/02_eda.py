"""Step 2: descriptive statistics and the figures used in the Data visualization section.

Each figure answers a modelling question (functional form, interaction, collinearity),
so no chart is decorative.
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from config import CLEAN_CSV, DUMMIES, FIG_DIR, IT_GROUP, label, save_values, write_table

sns.set_theme(style="whitegrid", context="paper", font_scale=1.15)
BLUE, ORANGE = "#2a6f97", "#d1495b"


def save(fig, name):
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(FIG_DIR / f"{name}.png", dpi=200)
    plt.close(fig)


def main() -> None:
    df = pd.read_csv(CLEAN_CSV)

    # Descriptive statistics, with every statistic the course requires for a formal report.
    names = {"sal": "Hourly salary", "lsal": "log(salary)"}
    cols = ["sal", "lsal", "edu", "exper", "ten", "dep", "momed", "daded", "sib", *DUMMIES]
    rows = []
    for c in cols:
        x = df[c].dropna()
        rows.append({"Variable": names.get(c, label(c)), "N": len(x), "Mean": x.mean(), "Median": x.median(),
                     "Mode": x.mode().iloc[0], "Variance": x.var(), "SD": x.std(), "Min": x.min(),
                     "Max": x.max(), "Range": x.max() - x.min(), "Skewness": x.skew(),
                     "Kurtosis": x.kurt(), "Q1": x.quantile(.25), "Q3": x.quantile(.75)})
    write_table("descriptives", pd.DataFrame(rows), floatfmt=".2f")

    # Correlations of the independent variables (lower triangle for the report; full matrix as CSV).
    ivs = ["edu", "exper", "ten", "female", "nonprev", "married", "dep", "metro", "wrkhm",
           "itrd", "momed", "daded", "sib"]
    corr_iv = df[ivs].corr()
    tri = corr_iv.where(np.tril(np.ones(corr_iv.shape, dtype=bool), k=-1)).iloc[1:, :-1]
    tri.index = [f"{i + 2}. {label(v).split(' (')[0]}" for i, v in enumerate(ivs[1:])]
    tri.columns = [str(i + 1) for i in range(len(ivs) - 1)]
    write_table("iv_correlations", tri.map(lambda v: "" if pd.isna(v) else f"{v:.2f}".replace("-0.00", "0.00")), index=True,
                numparse=False)
    all_ivs = ["edu", "exper", "ten", "female", "nonprev", *[c for c in DUMMIES if c not in ("female", "nonprev")],
               "dep", "momed", "daded", "sib"]
    df[all_ivs].corr().round(3).to_csv(FIG_DIR.parent / "tables" / "iv_correlations_full.csv")

    # Fig 1: salary is right-skewed; log(salary) is close to symmetric.
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.8))
    sns.histplot(df["sal"].dropna(), bins=30, ax=ax[0], color=BLUE)
    ax[0].set(title=f"Hourly salary (skewness {df.sal.skew():.2f})", xlabel="Salary per hour", ylabel="Employees")
    sns.histplot(df["lsal"].dropna(), bins=30, ax=ax[1], color=BLUE)
    ax[1].set(title=f"log(salary) (skewness {df.lsal.skew():.2f})", xlabel="log(salary)", ylabel="Employees")
    save(fig, "fig1_salary_distribution")

    # Fig 2: functional form of the human-capital variables (LOWESS shows curvature).
    fig, ax = plt.subplots(1, 3, figsize=(12, 3.8), sharey=True)
    for a, v in zip(ax, ["edu", "exper", "ten"]):
        sns.regplot(data=df, x=v, y="lsal", ax=a, lowess=True, scatter_kws={"s": 8, "alpha": .35, "color": "grey"},
                    line_kws={"color": ORANGE})
        a.set(xlabel=label(v), ylabel="log(salary)" if v == "edu" else "", title=f"log(salary) vs {label(v).split(' (')[0].lower()}")
    save(fig, "fig2_functional_form")

    # Fig 3: the gender gap depends on marital status (motivates female x married).
    g = df.groupby(["married", "female"])["sal"].agg(["mean", "sem", "count"]).reset_index()
    g["Group"] = g["female"].map({0: "Men", 1: "Women"})
    g["Status"] = g["married"].map({0: "Single", 1: "Married"})
    fig, ax = plt.subplots(figsize=(6, 4))
    for i, (grp, c) in enumerate([("Men", BLUE), ("Women", ORANGE)]):
        s = g[g.Group == grp]
        x = np.arange(2) + (i - .5) * .38
        ax.bar(x, s["mean"], width=.38, yerr=1.96 * s["sem"], color=c, label=grp, capsize=4)
        for xi, m, n in zip(x, s["mean"], s["count"]):
            ax.text(xi, 0.3, f"n={n}", ha="center", color="white", fontsize=9)
    ax.set_xticks(range(2), ["Single", "Married"])
    ax.set(ylabel="Mean hourly salary (95% CI)", title="Mean salary by gender and marital status")
    ax.legend()
    save(fig, "fig3_gender_marriage")

    # Fig 4: correlations among the numeric regressors (motivates the VIF check).
    num = ["lsal", "edu", "exper", "ten", "dep", "momed", "daded", "sib"]
    corr = df[num].corr()
    fig, ax = plt.subplots(figsize=(7, 5.5))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="RdBu_r", vmin=-1, vmax=1, ax=ax,
                xticklabels=["log(sal)"] + [label(c).split(" (")[0] for c in num[1:]],
                yticklabels=["log(sal)"] + [label(c).split(" (")[0] for c in num[1:]])
    ax.set_title("Correlation matrix of numeric variables")
    save(fig, "fig4_correlations")

    # Fig 5: salary by IT work group.
    grp = np.select([df[c] == 1 for c in IT_GROUP], [label(c) for c in IT_GROUP], "Other IT work")
    d5 = df.assign(group=grp).dropna(subset=["sal"])
    order = d5.groupby("group")["sal"].median().sort_values().index
    fig, ax = plt.subplots(figsize=(8, 4))
    sns.boxplot(data=d5, y="group", x="sal", order=order, ax=ax, color="#bcd4e6", fliersize=2)
    ax.set(xlabel="Hourly salary", ylabel="", title="Salary by IT work group")
    save(fig, "fig5_it_group")

    save_values({
        "skew_sal": round(float(df.sal.skew()), 2), "skew_lsal": round(float(df.lsal.skew()), 2),
        "mean_sal": round(float(df.sal.mean()), 2), "median_sal": round(float(df.sal.median()), 2),
        "corr_exper_ten": round(float(corr.loc["exper", "ten"]), 2),
        "corr_edu_exper": round(float(corr.loc["edu", "exper"]), 2),
        "corr_momed_daded": round(float(corr.loc["momed", "daded"]), 2),
        **{f"mean_sal_{r.Group.lower()}_{r.Status.lower()}": round(float(r["mean"]), 2) for _, r in g.iterrows()},
    })
    print("eda: tables and 5 figures written")


if __name__ == "__main__":
    main()
