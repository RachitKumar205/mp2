# MP2: Evaluating Employee Salaries at HCL Technologies

Course project MP2 (DOM207 / DOM3007 / DOM6401). We act as the consulting firm
**DOM207-DOM3007-DOM6401 Inc.**, hired by **HCL Technologies** to evaluate employee
salary packages. The data are in `ITEmp.xlsx`: 526 employees and 25 variables, with
average hourly salary as the dependent variable (DV).

This README documents the whole project: what the brief asks for, how the data
were cleaned, the hypotheses, the models, the assumption checks, and the findings.
Every number below comes from the scripts in `src/`. Run `src/run_all.py` to
regenerate them (see [How to run](#how-to-run)).

---

## Contents

1. [What the brief requires](#1-what-the-brief-requires)
2. [How to run](#how-to-run)
3. [Project layout](#3-project-layout)
4. [Data processing](#4-data-processing)
5. [Data visualization](#5-data-visualization)
6. [Variables: theory and roles](#6-variables-theory-and-roles)
7. [Hypotheses](#7-hypotheses)
8. [Analysis: models and estimation](#8-analysis-models-and-estimation)
9. [Analysis: model assumptions and supplementary checks](#9-analysis-model-assumptions-and-supplementary-checks)
10. [Results](#10-results)
11. [Recommendations](#11-recommendations)
12. [Limitations](#12-limitations)
13. [References](#13-references)
14. [Output file index](#14-output-file-index)

---

## 1. What the brief requires

The spec (`MP2Specs.pdf`) asks for the following.

**Deliverables:** a report (Word or PDF) plus the complete R/Python analysis files.

**Mandatory report sections:** Introduction, Data processing, Data visualization,
Hypotheses, Analysis, Results (with tables of significance), Recommendations and
References. The title page must carry the names, roll numbers, course and instructor.

**Technical must-haves, and where each is covered here:**

| Requirement in the brief | Where it is covered |
|---|---|
| Formulate hypotheses on how the primary study IVs relate to the DV | §7 |
| Give a theoretical justification for each variable as a salary determinant | §6 |
| Cover subsidiary influences: which variables to include or exclude, and why | §6, §10.6 |
| Include control variables and show their coefficients | §8, §10.5 |
| Justify the assumptions underlying the model | §9 |
| Test quadratic and interaction effects (*critically important*) | §8, §10.2–10.3 |
| Supplementary analysis: specification, heteroskedasticity, multicollinearity (*critically important*) | §9 |
| Examine several alternative models for subsidiary influences | §8 (M1–M7, A1–A4), §10.6 |
| Give an elaborate Results section with significance tables, interpreted | §10 |
| Base recommendations on findings, not speculation | §11 |
| Add no new data to the file; fixing obvious errors is allowed | §4 (invalid cells set to missing; two groups of implausible values imputed, with originals kept) |

---

## How to run

The project needs Python 3.14 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

```bash
uv run python src/run_all.py
```

`run_all.py` runs four steps in order. Each step can also be run on its own from
the project root.

| Step | Script | Produces |
|---|---|---|
| 1 | `src/01_clean.py` | `data/processed/ITEmp_clean.csv`, cleaning-log tables |
| 2 | `src/02_eda.py` | descriptive table, figures 1–5 |
| 3 | `src/03_models.py` | model ladder, significance tables, quadratic, interaction and subsidiary tables |
| 4 | `src/04_diagnostics.py` | VIF, BP/White, RESET, JB, DW, influence and robustness tables, figures 6–8 |

Each table is written twice to `output/tables/`: as Markdown (`.md`) and as CSV.
Headline numbers go to `output/values.json`.

---

## 3. Project layout

```
mp2/
├── data/
│   ├── raw/ITEmp.xlsx              # untouched copy of the client file
│   └── processed/ITEmp_clean.csv   # cleaned data (+ lsal, imputation flags, original exper/edu)
├── src/
│   ├── config.py                   # paths, variable groups, model formulas, labels
│   ├── helpers.py                  # OLS-with-HC3 fit, coefficient tables, stars
│   ├── 01_clean.py
│   ├── 02_eda.py
│   ├── 03_models.py
│   ├── 04_diagnostics.py
│   └── run_all.py
├── output/
│   ├── figures/                    # fig1–fig8 (.png, 200 dpi)
│   ├── tables/                     # every table as .md and .csv
│   └── values.json                 # headline numbers
├── pyproject.toml / uv.lock
└── README.md
```

Libraries used: pandas, numpy, statsmodels, scipy, matplotlib, seaborn, openpyxl
and tabulate.

---

## 4. Data processing

**Source.** The source is the `Salary` sheet of `ITEmp.xlsx`: 526 rows and 25 columns, with
a unique employee `id` and no duplicate rows. The `Data Description` sheet is the
data dictionary.

**Principle.** The brief forbids adding data but allows fixing obvious errors. Cleaning
has two parts:

- **Invalid cells (R1–R5)** are set to **missing**. Their true value cannot be recovered,
  so nothing is guessed. Models use listwise deletion. Each change is logged with the
  employee id and raw value (`output/tables/cleaning_log.md`).
- **Implausible but present values (R6–R7)** are **imputed**: 16 experience values and
  8 education values. The original values are kept in the columns `exper_orig` and
  `edu_orig`, every change is logged (`output/tables/imputation_log.md`), and a robustness
  model re-runs the analysis on the original values (§9.6).

### 4.1 Cleaning rules

| Rule | What it catches | Cells |
|---|---|---:|
| R1 | Text where a number is expected (`acb`, `SS0`, `b`, `aaa`, `a`, `s`, `ab`) | 8 |
| R2 | Dummy variable not equal to 0 or 1 (e.g. `norcen` = 100, `itprog` = 44, `south` = 1111) | 6 |
| R3 | Counts outside a plausible range: education, mom's and dad's education in [0, 20] years; siblings in [0, 15] | 9 |
| R4 | Non-positive hourly salary (−2.45) | 1 |
| R5 | Salary above the Tukey fence on the **log** scale: Q3 + 1.5·IQR of log(sal), which gives **25.00/hour** | 7 |
| | **Total set to missing** | **31 cells in 29 employees** |
| R6 | Tenure greater than experience → experience **imputed** as equal to tenure | 16 |
| R7 | Education below 6 years → **imputed** as the median education of employees in the same experience band | 8 |

**Why the salary fence uses the log scale.** Salary is log-normally distributed,
so a fence on the raw scale would flag many genuine high earners. The values removed by R5
are 46.67, 55.67, 55.78, 60, 333.334, 435.67 and 1111. The largest salary kept is 24.98. The
smallest removed value is almost twice that, and the three largest are 70–240 times the median
of 4.65. These are data-entry errors, not real salaries.

**Full cleaning log** (variable, id, raw value, rule):

| variable | id | raw value | rule |
|:--|--:|:--|:--|
| daded | 88 | 435 | R3 |
| edu | 53 | 122 | R3 |
| edu | 103 | 1001 | R3 |
| edu | 104 | SS0 | R1 |
| edu | 481 | 120 | R3 |
| itprog | 232 | 44 | R2 |
| itqual | 278 | s | R1 |
| itreq | 219 | 111 | R2 |
| metro | 32 | b | R1 |
| momed | 226 | 111 | R3 |
| momed | 274 | ab | R1 |
| norcen | 174 | 100 | R2 |
| sal | 44 | 1111 | R5 |
| sal | 103 | 435.67 | R5 |
| sal | 222 | acb | R1 |
| sal | 291 | 55.78 | R5 |
| sal | 360 | 333.334 | R5 |
| sal | 410 | 55.67 | R5 |
| sal | 443 | 60 | R5 |
| sal | 498 | 46.67 | R5 |
| sal | 503 | −2.45 | R4 |
| sib | 33, 127, 247, 382 | 33, 101, 333, 222 | R3 |
| south | 247 | aaa | R1 |
| south | 250, 258 | 231, 1111 | R2 |
| west | 120, 419 | a, a | R1 |
| west | 519 | 101 | R2 |

### 4.2 Missingness after cleaning

| variable | blank in raw file | set to missing | missing after cleaning |
|:--|--:|--:|--:|
| sal | 2 | 9 | 11 |
| edu | 1 | 4 | 5 |
| exper | 2 | 0 | 2 |
| metro | 1 | 1 | 2 |
| norcen | 1 | 1 | 2 |
| south | 5 | 3 | 8 |
| west | 0 | 3 | 3 |
| itreq | 4 | 1 | 5 |
| itprog | 0 | 1 | 1 |
| itqual | 0 | 1 | 1 |
| momed | 3 | 2 | 5 |
| daded | 2 | 1 | 3 |
| sib | 1 | 4 | 5 |

- 515 employees have a valid salary.
- The main estimation sample, complete on all model variables, is **N = 490**. The imputation (R6, R7) changes values only, never the number of rows.
- The family-background models also need `momed`, `daded` and `sib`, so they use N = 479.

### 4.3 Structural checks

**Mutually exclusive dummy sets** (verified, not altered). The code confirms that no
employee belongs to more than one category within a set. All three sets can therefore
enter a model together, and the all-zero group is the reference category.

| Dummy set | Variables | Rows in >1 category | Reference group (all zero) |
|:--|:--|--:|--:|
| Region | norcen, south, west | 0 | 125 (other / eastern provinces) |
| IT work group | itreq, itprog, itqual, itarch, itai, itclient | 0 | 79 (other IT work) |
| IT division | itrd, ittech | 0 | 245 (other divisions) |

### 4.4 Imputed values (R6, R7)

All 24 changes, with original and imputed values, are in `output/tables/imputation_log.md`.

**R6: tenure longer than experience (16 employees).** Ids: 32, 74, 166, 174, 202, 211,
216, 218, 276, 334, 342, 360, 381, 466, 478, 524.
- **Problem:** years worked at HCL are themselves professional experience, so experience
  cannot logically be lower than tenure.
- **Imputation:** experience is raised to equal tenure. This is the smallest change that
  makes each record internally consistent.
- **Size of the changes:** 1–6 years for 15 employees. The exception is id 74, raised
  from 20 to 34 years.
- **Audit:** the rows are flagged in `ten_gt_exper`.

**R7: education below 6 years (8 employees).** Ids: 38, 139, 306, 379, 465, 470, 503, 504.
- **Problem:** values of 0–5 years of schooling are implausible for IT-company employees.
- **Imputation:** each value is replaced by the median education of employees in the same
  experience band (0–10, 10–20, 20–30, 30–40 and 40+ years), using only employees with
  6 or more years of education.
- **Result:** all 8 employees have 22–51 years of experience, and every band's median is
  **12 years**.
- **Audit:** the rows are flagged in `edu_lt6`.

**Why this is defensible, and its cost.**
- The brief allows modifying obvious errors, and the original values are preserved.
- The analysis is re-run on the original values as a robustness check (§9.6). Every
  headline conclusion is unchanged.
- The cost: the 8 low-education employees earn little (2.90–4.17/hr). Giving them
  12 years of education makes the education profile slightly steeper above 12 years
  (§10.2).

**Naming.** The data column is `nonprev`, but the dictionary says `noprev`. The
dictionary entries `ittech` and `wrkhm` have trailing spaces. Column names are
stripped, and the data's own `nonprev` is kept.

### 4.5 Transformation of the DV

The models use **lsal = log(sal)**:

- Raw salary is strongly right-skewed (skewness 1.98); log(salary) is close to symmetric (0.38).
- Coefficients then read as approximate percentage effects. For a dummy, the exact effect is 100·(e^b − 1)%.
- The log removes the heteroskedasticity present in the level model (§9.3).

---

## 5. Data visualization

Each figure answers a specific modelling question; none is decorative.

| Figure | File | What it shows | Modelling decision it drives |
|---|---|---|---|
| 1 | `fig1_salary_distribution.png` | Histograms of salary and log(salary) | Use log(salary) as the DV |
| 2 | `fig2_functional_form.png` | log(salary) against education, experience and tenure, with LOWESS curves | Education rises at an increasing rate (convex), experience rises then falls (concave), tenure rises then flattens → **quadratic terms** |
| 3 | `fig3_gender_marriage.png` | Mean salary by gender × marital status, with 95% CIs | Married men earn 7.99/hr against 5.19 for single men; women earn about 4.6 whether married or not → **female × married interaction** |
| 4 | `fig4_correlations.png` | Correlation heatmap of the numeric variables | exper–ten r = 0.51, edu–exper r = −0.25, momed–daded r = 0.39 → **check multicollinearity (VIF)**. Background variables are almost uncorrelated with salary |
| 5 | `fig5_it_group.png` | Salary boxplots by IT work group | Pay differs clearly by group → include the IT group and division as **controls** |
| 6 | `fig6_residual_diagnostics.png` | Residuals vs fitted, Q–Q, scale–location, leverage | Checks the model assumptions (§9) |
| 7 | `fig7_level_vs_log.png` | Residual spread for the level vs log models | Visual evidence that the log model removes heteroskedasticity |
| 8 | `fig8_predicted_profiles.png` | Predicted salary vs experience for the four gender × marriage groups (M7) | Shows the quadratic and interaction findings together |

**Descriptive statistics** (`output/tables/descriptives.md`):

| Variable | N | Mean | SD | Min | Median | Max |
|:--|--:|--:|--:|--:|--:|--:|
| Hourly salary | 515 | 5.93 | 3.72 | 0.53 | 4.65 | 24.98 |
| log(salary) | 515 | 1.63 | 0.54 | −0.63 | 1.54 | 3.22 |
| Education (yrs), after R7 | 521 | 12.71 | 2.49 | 6 | 12 | 18 |
| Experience (yrs), after R6 | 524 | 17.12 | 13.56 | 1 | 13.5 | 51 |
| Tenure (yrs) | 526 | 5.10 | 7.22 | 0 | 2 | 44 |
| Dependents | 526 | 1.04 | 1.26 | 0 | 1 | 6 |
| Mother's education | 521 | 9.93 | 3.22 | 4 | 10 | 15 |
| Father's education | 523 | 14.47 | 3.65 | 8 | 15 | 19 |
| Siblings | 521 | 1.57 | 1.18 | 0 | 2 | 5 |
| Female | 526 | 0.48 | | | | |
| Married | 526 | 0.61 | | | | |
| Non-privileged | 526 | 0.10 | | | | |
| Metro area | 524 | 0.72 | | | | |
| Works from home | 526 | 0.14 | | | | |

---

## 6. Variables: theory and roles

The framework is the **Mincer (1974) human-capital earnings function**: log earnings
are a function of schooling and of experience and its square. The model then adds
demographic, job and location characteristics.

| Variable | Role | Theoretical justification | Expected sign |
|---|---|---|---|
| `edu` | **Study IV** | Human capital: schooling raises productivity and signals ability (Becker 1964; Spence 1973) | + (possibly convex) |
| `exper` | **Study IV** | General on-the-job human capital accumulates, but investment declines over the career | + with diminishing returns (concave) |
| `ten` | **Study IV** | Firm-specific capital and internal promotion ladders | + with diminishing returns |
| `female` | **Study IV** | Pay-equity question for the client: discrimination, occupational sorting, career interruptions | − |
| `nonprev` | **Study IV** | Non-privileged employees may face weaker networks and less access to high-pay roles | − |
| `married` | Control (moderator) | Marriage premium for men (productivity/specialization or employer favouritism); none or a penalty for women | + for men |
| `dep` | Control | Dependants can reduce hours or mobility (especially for carers) | − |
| `metro` | Control | Metro areas have higher productivity and cost of living | + |
| `norcen`, `south`, `west` | Control (set) | Regional labour-market differences across Indian provinces | ? |
| `itreq` … `itclient` | Control (set) | Compensating differentials and the market value of each IT function | ? |
| `itrd`, `ittech` | Control (set) | Division-level pay structures (R&D usually pays a premium) | R&D + |
| `wrkhm` | Control | Remote work trades pay against flexibility (compensating differential) | − |
| `momed`, `daded`, `sib` | **Excluded from the main model; used in alternative models** | Family background should affect pay only **through** the employee's own education (an indirect, subsidiary path) | 0 direct |

**Why include the controls?** They are plausible determinants of pay that are
correlated with the study IVs. For example, women are more often in tech-support and
client-only roles, and educated employees are more often in R&D. Leaving them out would
bias the study-IV coefficients (omitted-variable bias). Their coefficients are reported
in full (§10.5).

**Why exclude family background from the main model?**

1. Theory treats it as a cause of education, not of pay directly.
2. In a pay regression it is a "bad control" that would absorb part of the education effect.
3. We test it rather than assume it: alternative models A1–A4 (§10.6) show it has
   **no** direct and **no** indirect effect. Adding it changes the education
   coefficient by less than 0.001 and makes no measurable difference, so dropping it costs nothing.

---

## 7. Hypotheses

The DV is log hourly salary. The hypotheses (H) were set **before** estimation; the
candidate interactions were fixed in advance as the set in model M5.

| # | Hypothesis | Test |
|---|---|---|
| H1 | Education raises salary (β_edu > 0), at an increasing rate (convex: β_edu² > 0) | Joint test of edu and edu²; sign of edu² |
| H2 | Experience raises salary with diminishing returns (β_exper > 0, β_exper² < 0) | t-tests and joint test |
| H3 | Tenure raises salary with diminishing returns (β_ten > 0, β_ten² < 0) | t-tests and joint test |
| H4 | Women earn less than comparable men (β_female < 0) | t-test and joint test of all female terms |
| H5 | Non-privileged employees earn less (β_nonprev < 0) | t-test |
| H6 | The gender gap is larger for married employees: a marriage premium for men only (β_female×married < 0) | t-test and conditional effects |
| H7 | Returns to human capital differ by gender (female × edu, female × exper, female × ten ≠ 0) | t-tests within M5/M7 |
| H8 | The marriage premium changes over the career (married × exper ≠ 0) | t-test |
| H9 | Education and experience are complements (edu × exper > 0) | t-test in M5 |
| H10 | Family background (momed, daded, sib) affects salary only indirectly, through education | Alternative models A1–A4 |
| H11 | Part of the effect of education and gender works through job allocation (IT group and division) | Coefficient path across models + job-sorting regressions |

---

## 8. Analysis: models and estimation

**Estimator.** OLS on log(salary) with **HC3 heteroskedasticity-robust standard
errors** (MacKinnon & White 1985) in every model. Significance stars: `*` p < 0.10,
`**` p < 0.05, `***` p < 0.01. Models M1–M7 share **one estimation sample (N = 490)**, so
their fit statistics compare directly.

**Model ladder** (formulas in `src/config.py`, `FORMULAS`):

| Model | Specification | Purpose |
|---|---|---|
| M1 | edu + exper + ten | Pure human capital |
| M2 | M1 + female + nonprev | Adds the remaining study IVs |
| M3 | M2 + all controls (family, location, region, IT group, IT division, wrkhm) | Linear main model |
| M4 | M3 + edu² + exper² + ten² | **Quadratic effects** |
| M5 | M4 + 7 candidate interactions: female×married, female×edu, female×exper, female×ten, edu×exper, married×exper, female×nonprev | **General interaction model** |
| M6 | M4 + female×married | Theory-first parsimonious model |
| **M7** | **M6 + female×ten + married×exper** | **Preferred model**: general-to-specific reduction of M5 |

**Alternative models for subsidiary influences:**

| Model | Specification | Question |
|---|---|---|
| A1 | edu ~ momed + daded + sib + female + exper + ten + metro + region | Does family background predict education? (first link of the indirect path) |
| A2 | M7 without the education terms, + background | Total (reduced-form) effect of background on salary |
| A3 | M7 + background | Direct effect of background, holding education fixed |
| A4 | M7 on the same N = 479 sample | Baseline for A3 |
| Coefficient path | Female only → M1 → M2 → + family & location → M3 | How study-IV coefficients change as controls enter |
| Job sorting | Linear probability models: in group or division g ~ female + edu + exper + ten | Do women or the more educated land in better- or worse-paid groups? |

**How M7 was selected.**

1. Over M4, the 7 candidate interactions are jointly significant (F = 3.57, df = 7, p < 0.001).
2. Within M5 only three are individually significant: female×married, female×ten and married×exper.
3. Dropping the other four is not rejected (F = 0.88, df = 4, p = 0.475).
4. M7 has the lowest AIC of all the models (405.5).
5. M7 is the only model that passes the RESET specification test at 5% (§9.2).

---

## 9. Analysis: model assumptions and supplementary checks

All tests are on the preferred model M7 unless stated (`output/tables/diagnostics.md`).

| Statistic | M3 (log, linear) | M7 salary in **levels** | **M7 log(salary)** |
|:--|--:|--:|--:|
| Breusch–Pagan LM (p) | 31.98 (0.044) | 70.04 (<0.001) | **34.10 (0.132)** |
| White, special form LM (p) | 0.55 (0.759) | 60.94 (<0.001) | **2.31 (0.316)** |
| RESET F, ŷ² + ŷ³ (p) | 5.45 (0.005) | 20.91 (<0.001) | **2.47 (0.086)** |
| Jarque–Bera (p) | 33.2 (<0.001) | 682.2 (<0.001) | 73.2 (<0.001) |
| Residual skewness | 0.14 | 1.47 | **−0.02** |
| Residual kurtosis | 4.24 | 7.98 | 4.89 |
| Durbin–Watson | 1.88 | 1.90 | **1.89** |

### 9.1 Linearity in parameters

The model is linear in its coefficients. Non-linear effects of education, experience and
tenure enter through quadratic terms, and the curvature in Figure 2 justifies them. All
three quadratic terms are jointly significant (χ² = 30.87, df = 3, p < 0.001).

### 9.2 Correct specification (Ramsey RESET)

| Model | What RESET says |
|---|---|
| M3 (linear) | Strongly rejected (p = 0.005): curvature and interactions are missing |
| M6 | Still rejected (p = 0.043) |
| **M7** | **Not rejected at 5%** (p = 0.086 with ŷ² and ŷ³; p = 0.072 with ŷ² alone) |
| Level-salary model | Rejected (p < 0.001), which supports the log transformation |

### 9.3 Homoskedasticity

| Model | Breusch–Pagan | White (special form) |
|---|---|---|
| Level-salary model | p < 0.001 | p < 0.001 |
| **M7 (log)** | **p = 0.132** | **p = 0.316** |

- The level model is clearly heteroskedastic, and Figure 7 shows the fan shape.
- The log transformation removes it.
- The White test uses the special form (regress e² on ŷ and ŷ²; Wooldridge). The full
  White test is not identified here, because the squares of the many dummy variables
  duplicate the dummies themselves.
- As a safeguard, **all inference uses HC3 robust SEs**. Robust SEs differ from classical
  SEs by only −2% to +18% (`se_comparison.md`), and no conclusion changes.

### 9.4 No perfect multicollinearity (VIF)

| Specification | Max VIF |
|---|--:|
| M3 (linear) | 2.63 |
| M7, raw variables | 59.2 (education and its square) |
| **M7, mean-centred edu / exper / ten** | **5.84** (all below 10) |

- In the linear model M3 the largest VIF is 2.63, so there is no collinearity problem.
- In M7 the raw VIFs of education and its square reach about 59. This is **structural**
  collinearity between a variable and its own square or interaction, not a data problem.
- **How it is handled:** education, experience and tenure are re-estimated mean-centred.
  Centring leaves every fitted value and every test unchanged (asserted in code). It only
  changes the parameterisation, and it brings every VIF below 10.
- Joint tests of each variable with its square are used for inference on the study IVs.
- The condition number falls from 16,001 to 2,384. The dummy-variable sets cause no
  trap, because each set has a reference group.

### 9.5 Normality of errors

- Jarque–Bera rejects normality (p < 0.001). The cause is excess kurtosis (4.9), not
  skew: the residual skewness is −0.02, and the Q–Q plot (Figure 6) departs only in the tails.
- With N = 490, the central limit theorem makes the OLS coefficients approximately normal,
  so t- and z-tests remain valid. HC3 SEs add further protection.
- The level model is far worse (JB = 682, skewness 1.47).

### 9.6 Independence, exogeneity, influence and robustness

- **Independence.** The data are a cross-section of employees. The Durbin–Watson
  statistic of 1.89, with rows ordered by id, shows no serial dependence.
- **Zero conditional mean.** We control for every observed determinant of pay. Unobserved
  ability and performance are not in the data, so the coefficients describe conditional
  associations and should not be read as strict causal effects (§12).
- **Influential observations.** 31 employees have Cook's D > 4/n = 0.008; the largest
  is 0.062, far below 1.
- **Robustness of M7** (`output/tables/robustness.md`). Every headline result keeps its
  sign and significance in all five alternatives below:

  | Variant | Female×Married | Female×Tenure | Married×Exper | Exper / Exper² | Female | R&D | Architecture / AI |
  |---|--:|--:|--:|---|--:|--:|---|
  | M7 baseline (N = 490) | −0.196** | −0.013** | −0.0066** | +*** / −*** | −0.101* | +0.201*** | −0.31*** / −0.31*** |
  | **Original values, no imputation** (N = 490) | −0.192** | −0.014** | −0.0064** | same | −0.101* | +0.187*** | same |
  | Drop the 24 imputed rows (N = 471) | −0.185** | −0.014** | −0.0071** | same | −0.116* | +0.200*** | same |
  | Drop Cook's D > 4/n (N = 459) | −0.212*** | −0.018*** | −0.0084*** | same | −0.077* | +0.220*** | same |
  | FGLS / WLS on estimated variance | −0.160** | −0.016*** | −0.0084*** | same | −0.114** | +0.192*** | same |
  | M6 (fewer interactions) | −0.232*** | n/a | n/a | same | −0.125** | +0.198*** | same |

  The only visible difference from the imputation: Tenure² is significant at 10% on the
  original values (p = 0.068) and not after imputation (p = 0.105).

---

## 10. Results

### 10.1 Model ladder

Coefficients are shown with HC3 robust significance stars; the full table with SEs is
`output/tables/models_ladder.md`.

| Variable | M1 | M2 | M3 | M4 | M5 | M6 | **M7** |
|:--|:--|:--|:--|:--|:--|:--|:--|
| Education | 0.1006*** | 0.0940*** | 0.0577*** | −0.0854 | … | −0.0832 | **−0.0738** |
| Education² | | | | 0.0054** | … | 0.0053** | **0.0049\*\*** |
| Experience | 0.0029* | 0.0033* | 0.0011 | 0.0275*** | … | 0.0283*** | **0.0292\*\*\*** |
| Experience² | | | | −0.0006*** | … | −0.0006*** | **−0.0006\*\*\*** |
| Tenure | 0.0223*** | 0.0172*** | 0.0130*** | 0.0220*** | … | 0.0209*** | **0.0274\*\*\*** |
| Tenure² | | | | −0.0004 | … | −0.0003 | **−0.0004** |
| Female | | −0.2996*** | −0.2623*** | −0.2596*** | … | −0.1249** | **−0.1006\*** |
| Non-privileged | | −0.0012 | 0.0154 | 0.0055 | … | −0.0019 | **−0.0086** |
| Married | | | 0.1023** | 0.0577 | … | 0.1826*** | **0.2655\*\*\*** |
| Female × Married | | | | | … | −0.2319*** | **−0.1961\*\*** |
| Female × Tenure | | | | | … | | **−0.0125\*\*** |
| Married × Experience | | | | | … | | **−0.0066\*\*** |
| Controls | no | no | yes | yes | yes | yes | yes |
| N | 490 | 490 | 490 | 490 | 490 | 490 | 490 |
| Adj. R² | 0.307 | 0.378 | 0.501 | 0.539 | 0.556 | 0.548 | **0.556** |
| AIC | 601.9 | 550.9 | 457.5 | 421.7 | 409.8 | 412.4 | **405.5** |

**Nested F-tests** (`nested_tests.md`): every step of the ladder adds significant
explanatory power.

| Restricted → Unrestricted | Terms added | F | df | p |
|---|---|--:|--:|--:|
| M1 → M2 | female, non-privileged | 28.78 | 2 | <0.001 |
| M2 → M3 | 15 controls | 8.95 | 15 | <0.001 |
| M3 → M4 | quadratic terms | 13.81 | 3 | <0.001 |
| M4 → M5 | all 7 interactions | 3.57 | 7 | <0.001 |
| M4 → M6 | female × married | 10.90 | 1 | 0.001 |
| M6 → M7 | female × tenure, married × experience | 5.19 | 2 | 0.006 |
| M7 → M5 | the 4 interactions dropped | 0.88 | 4 | 0.475 (dropping is justified) |

**Joint robust Wald tests in M7** (`joint_tests.md`):

| Hypothesis (all = 0) | χ² | df | p |
|---|--:|--:|--:|
| Region (norcen, south, west) | 3.78 | 3 | 0.287 |
| IT work group (6 dummies) | 46.77 | 6 | <0.001 |
| IT division (itrd, ittech) | 15.42 | 2 | <0.001 |
| Education + Education² | 27.71 | 2 | <0.001 |
| Experience + Experience² | 28.38 | 2 | <0.001 |
| Tenure + Tenure² | 16.80 | 2 | <0.001 |
| All quadratic terms | 30.87 | 3 | <0.001 |
| All terms involving Female | 64.13 | 3 | <0.001 |
| All terms involving Married | 17.18 | 3 | <0.001 |
| All interaction terms | 23.43 | 3 | <0.001 |
| Married + Dependents | 21.22 | 2 | <0.001 |

### 10.2 Quadratic effects

Marginal effects, in % per extra year (`quadratic_effects.md`):

| Variable | Turning point | P25 | Median | P75 | Reading |
|---|--:|--|--|--|---|
| Education | 7.5 yrs (a minimum) | 4.36% at 12 yrs | 4.36% at 12 yrs | 6.32% at 14 yrs | Convex. Returns **rise** with each year of schooling: 4.4% at 12 years, 8.3% at 16. The minimum at 7.5 years sits at the bottom of the (imputed) 6–18 range, where few employees are |
| Experience (single) | 26.2 yrs | 2.36% at 5 | 1.47% at 13 | 0.02% at 26 | Concave. Steep early, flat by about 26 years (about 20 years for married employees, because married × exper < 0) |
| Tenure (men) | 31.0 yrs | 2.74% at 0 | 2.57% at 2 | 2.12% at 7 | Essentially linear: Tenure² is not significant (p = 0.105), so each year adds roughly 2.7% for men |

**Key insight.** In the linear model M3, experience looks insignificant
(β = 0.0011, p = 0.489). The quadratic shows a strong concave profile instead
(joint p < 0.001). The linear specification hid the effect of experience; this is why the
quadratic terms matter.

### 10.3 Interaction effects

Conditional effects in M7, with robust SEs (`interaction_effects.md`). With
interactions in the model, the `female` coefficient alone is only the gap for a single
woman at tenure 0, so the effects must be evaluated at chosen values:

| Effect | Evaluated for | % effect | p |
|---|---|--:|--:|
| Gender gap (female − male) | single, tenure 0 | −9.6% | 0.093 |
| | single, tenure 5 | −15.0% | 0.009 |
| | single, tenure 10 | −20.2% | 0.003 |
| | married, tenure 0 | −25.7% | <0.001 |
| | married, tenure 5 | −30.2% | <0.001 |
| | married, tenure 10 | −34.4% | <0.001 |
| Marriage premium (married − single) | men, experience 5 | +26.2% | <0.001 |
| | men, experience 15 | +18.1% | 0.006 |
| | men, experience 25 | +10.5% | 0.163 |
| | women, experience 5 | +3.7% | 0.558 |
| | women, experience 15 | −2.9% | 0.566 |
| | women, experience 25 | −9.1% | 0.087 |
| Return to one extra year of tenure (at tenure 0) | men | +2.8% | <0.001 |
| | women | +1.5% | 0.052 |

What the conditional effects show:

1. **The gender gap depends on marriage.** Single women earn about 10% less than
   comparable single men at hire. Married women earn about 25% less than married men,
   because married men receive a premium that married women do not.
2. **The gender gap widens with tenure.** Women gain about 1.5% per year of tenure
   against 2.8% for men. The gap therefore roughly doubles over ten years with the company.
3. **The male marriage premium is largest early in the career** (+26% at 5 years of
   experience) and fades to insignificance by about 25 years.
4. **No support for the other candidate interactions.** In M5, female×edu
   (p = 0.23), female×exper (p = 0.72), edu×exper (p = 0.21) and female×nonprev
   (p = 0.39) are all insignificant, and dropping them is not rejected (p = 0.475). Women's returns to education and to
   general experience are therefore the same as men's. The gap arises through tenure,
   marriage and the level of pay.

Figure 8 plots these effects as predicted salary profiles.

### 10.4 Significance table for the preferred model (M7)

N = 490, R² = 0.580, adjusted R² = 0.556, robust F = 30.22 (p < 0.001). Full table with
95% CIs: `sig_preferred.md`.

| Variable | Coef. | Robust SE | z | p | Sig. |
|:--|--:|--:|--:|--:|:--|
| Intercept | 1.5023 | 0.3768 | 3.99 | <0.001 | *** |
| Education | −0.0738 | 0.0584 | −1.26 | 0.206 |  |
| Education² | 0.0049 | 0.0023 | 2.16 | 0.031 | ** |
| Experience | 0.0292 | 0.0055 | 5.32 | <0.001 | *** |
| Experience² | −0.0006 | 0.0001 | −4.70 | <0.001 | *** |
| Tenure | 0.0274 | 0.0083 | 3.32 | <0.001 | *** |
| Tenure² | −0.0004 | 0.0003 | −1.62 | 0.105 |  |
| Female | −0.1006 | 0.0599 | −1.68 | 0.093 | * |
| Non-privileged | −0.0086 | 0.0605 | −0.14 | 0.887 |  |
| Married | 0.2655 | 0.0677 | 3.92 | <0.001 | *** |
| Female × Married | −0.1961 | 0.0766 | −2.56 | 0.011 | ** |
| Female × Tenure | −0.0125 | 0.0056 | −2.21 | 0.027 | ** |
| Married × Experience | −0.0066 | 0.0029 | −2.32 | 0.021 | ** |
| Dependents | −0.0353 | 0.0140 | −2.52 | 0.012 | ** |
| Metro area | 0.1353 | 0.0431 | 3.14 | 0.002 | *** |
| North-central | −0.0347 | 0.0457 | −0.76 | 0.448 |  |
| South | −0.0535 | 0.0458 | −1.17 | 0.242 |  |
| West | 0.0445 | 0.0604 | 0.74 | 0.462 |  |
| IT requirements | −0.0924 | 0.1029 | −0.90 | 0.369 |  |
| IT programming | −0.0958 | 0.0577 | −1.66 | 0.097 | * |
| IT quality assurance | −0.1563 | 0.0761 | −2.05 | 0.040 | ** |
| IT architecture | −0.3116 | 0.0557 | −5.60 | <0.001 | *** |
| AI applications | −0.3118 | 0.0769 | −4.05 | <0.001 | *** |
| Client-only work | −0.1005 | 0.0615 | −1.63 | 0.102 |  |
| R&D division | 0.2007 | 0.0521 | 3.85 | <0.001 | *** |
| Tech support division | 0.0698 | 0.0562 | 1.24 | 0.214 |  |
| Works from home | −0.1102 | 0.0595 | −1.85 | 0.064 | * |

On its own, the education coefficient is insignificant because it is the slope at
education = 0. Inference for education comes from the joint test (p < 0.001) and the
marginal effects in §10.2.

### 10.5 Control variables

Effects are exact percentages, 100·(e^b − 1):

| Control | Effect | Reading |
|---|--:|---|
| Metro area | **+14.5%** *** | A metro premium consistent with labour-market and cost-of-living theory |
| R&D division | **+22.2%** *** | The highest-paying division |
| IT architecture | **−26.8%** *** | Paid well below the reference "other IT work" group |
| AI applications | **−26.8%** *** | As above; a surprising result for a strategic skill set |
| IT quality assurance | −14.5% ** | |
| IT programming | −9.1% * (p = 0.097) | Weak evidence |
| Works from home | −10.4% * (p = 0.064) | Weak evidence of a remote-work pay penalty |
| Dependents | −3.5% per dependent ** | |
| Region (set) | jointly 0 (p = 0.287) | No provincial pay differences once metro status is held fixed |
| Client-only work, tech support, IT requirements | n.s. | |

### 10.6 Subsidiary (indirect) influences

**(a) Coefficient path** (`coef_path.md`): how each study IV changes as blocks of
controls enter.

| Specification | Education | Experience | Tenure | Female | Adj. R² |
|---|--|--|--|--|--:|
| Female only | | | | −0.4127*** | 0.147 |
| Human capital only (M1) | 0.1006*** | 0.0029* | 0.0223*** | | 0.307 |
| Study IVs (M2) | 0.0940*** | 0.0033* | 0.0172*** | −0.2996*** | 0.378 |
| + family & location | 0.0782*** | 0.0020 | 0.0153*** | −0.2741*** | 0.432 |
| + IT group & division (M3) | 0.0577*** | 0.0011 | 0.0130*** | −0.2623*** | 0.501 |

- **Education.** The coefficient falls from 0.094 to 0.058 once the location and job
  controls enter, so about **39% of the return to education works indirectly**, through
  where educated employees are placed. The job-sorting regressions confirm this: each
  extra year of education raises the probability of working in the R&D division by
  **10.2 percentage points** (p < 0.01), and R&D pays 22.2% more.
- **Gender.** The raw gap is **−33.8%**. Human capital (education, experience,
  tenure) explains part of it, bringing it to −25.9%. Location, family and job
  allocation explain little more (−23.1% in M3). In log points, about **two-thirds of the
  raw gap (−0.26 of −0.41) remains unexplained** by any observed characteristic.

**(b) Job sorting by gender** (`job_sorting.md`; linear probability models
controlling for edu, exper and ten):

| In group / division | Female (pp) | Education (pp per yr) | Pay effect of group in M7 |
|---|--:|--:|--:|
| R&D division | −10.3*** | +10.2*** | +22.2% |
| Tech support division | +26.3*** | n.s. | +7.2% (n.s.) |
| Client-only work | +20.4*** | +4.4*** | −9.6% (n.s.) |
| AI applications | +6.3** | n.s. | −26.8% |
| IT architecture | −8.4** | −2.2*** | −26.8% |
| IT programming | n.s. | n.s. | −9.1% |

Women are under-represented in the best-paid division (R&D) and over-represented in
client-only (n.s. pay effect) and AI work. These channels partly offset each other: women are also less
often in the low-paid architecture group. As a result, job allocation explains only a
small part of the gender gap.

**(c) Family background** (`alt_background.md`, `background_tests.md`; N = 479):

| Model | Joint test momed = daded = sib = 0 | Conclusion |
|---|---|---|
| A1: education equation | χ² = 1.06, p = 0.787 | Background does not predict education |
| A2: reduced form (no edu) | χ² = 0.24, p = 0.971 | No total effect on salary |
| A3: M7 + background | χ² = 0.63, p = 0.889 | No direct effect on salary |
| A3 vs A4: change in the education coefficient | −0.0003 | No omitted-variable bias from excluding background |

Family background has neither a direct nor an indirect effect, so it is correctly
excluded from the main model.

### 10.7 Hypothesis verdicts

| # | Hypothesis | Verdict | Evidence |
|---|---|---|---|
| H1 | Education +, convex | **Supported** | Joint p < 0.001; edu² > 0 (p = 0.031); return 4.4% at 12 yrs → 8.3% at 16 yrs |
| H2 | Experience +, diminishing | **Supported** | exper > 0, exper² < 0 (both p < 0.001); peak at about 26 yrs |
| H3 | Tenure +, diminishing | **Partly supported** | ten > 0 (p < 0.001), joint p < 0.001; ten² not significant (p = 0.105), so no clear diminishing returns |
| H4 | Women earn less | **Supported** | All female terms jointly p < 0.001; gap 10–35% depending on marriage and tenure |
| H5 | Non-privileged earn less | **Not supported** | β ≈ 0, p = 0.887 in M7; insignificant in every model |
| H6 | Gap larger for married (marriage premium for men only) | **Supported** | female × married = −0.196 (p = 0.011); men +26% → +11%; women ≈ 0 |
| H7 | Returns to human capital differ by gender | **Partly supported** | Tenure: yes (female × ten = −0.0125, p = 0.027). Education and experience: no |
| H8 | Marriage premium changes with experience | **Supported** | married × exper = −0.0066 (p = 0.021); premium fades over the career |
| H9 | Education × experience complementarity | **Not supported** | Insignificant in M5 |
| H10 | Background acts only through education | **Not supported in either direction** | No direct and no indirect effect (A1–A3: all p > 0.5) |
| H11 | Education and gender work partly through job allocation | **Supported for education; weak for gender** | Education coefficient −39% once job controls enter; gender coefficient moves only −0.30 → −0.26 |

---

## 11. Recommendations

Each recommendation rests on a specific finding above.

1. **Run a formal pay-equity review for women.** After controlling for education,
   experience, tenure, location, job group and division, women earn 10–35% less than
   comparable men (§10.3). Job allocation and human capital explain only about a third
   of the raw gap (§10.6). The model in `src/03_models.py` can serve as an annual audit
   tool: flag employees whose pay falls well below the model's prediction.

2. **Audit tenure-based raises and promotions by gender.** Each year with HCL adds
   about 2.8% to men's pay but only about 1.5% to women's (§10.3), so the gap widens
   with service. Increment and promotion criteria should be standardized and reviewed.

3. **Separate pay from marital status.** Married men earn a premium of up to 26% that
   married women do not receive (H6, H8). Any allowances or discretionary components
   that track family status should be reviewed, because they produce a gender gap among
   married staff of about 26–34%.

4. **Invest in education and keep R&D open to all.** Returns to education rise with
   each year (4% to 8% per year, H1), and about 39% of that return comes from placement,
   mainly in the R&D division (+22.2%). Tuition support and transparent R&D entry criteria would
   raise productivity and pay. Women's lower R&D placement (−10 pp) deserves specific
   attention.

5. **Benchmark the architecture and AI groups against the market.** These groups are
   paid about 27% less than comparable staff elsewhere (§10.5). For strategic functions
   this creates a retention risk. A market comparison is recommended before any change;
   the data cannot say why the gap exists.

6. **Manage the late-career pay plateau.** Pay growth from experience flattens after
   about 26 years (about 20 for married staff, §10.2). Senior career tracks and
   performance-linked pay can keep late-career employees motivated.

7. **No action needed on regional pay or non-privileged status.** Regions show no pay
   differences beyond the metro premium (p = 0.29), and non-privileged status has no
   effect (p = 0.89). The metro premium (+14.5%) is consistent with cost-of-living
   differences.

8. **Monitor remote work.** Working from home carries a −10% effect, but the evidence
   is weak (p = 0.064). Track it rather than act on it now.

9. **Validate data at entry.** 31 cells had obvious errors (§4), including salaries of
   1111/hr and text in numeric fields. Another 24 records were internally inconsistent
   (tenure above experience) or implausible (under 6 years of schooling) and had to be
   imputed. Range and type checks in the HR system would stop
   these at source.

---

## 12. Limitations

- **Causality.** The data are cross-sectional and observational. Unobserved ability,
  performance ratings and hours are not available, so coefficients are conditional
  associations, not proven causal effects.
- **Unexplained gap.** The unexplained gender gap is consistent with discrimination,
  but it may also reflect unmeasured factors such as performance or negotiation.
- **Specification.** RESET passes at 5% but not at 10% (p = 0.086). Some non-linearity
  may remain.
- **Residual tails.** Residuals have fat tails (kurtosis 4.9). Inference relies on the
  large sample and HC3 SEs.
- **Selection of M7.** M7 keeps the significant interactions from the pre-specified
  candidate set in M5, which carries a multiple-testing risk. The kept interactions are
  theory-based, survive every robustness check (§9.6), and the reduction from M5 is
  formally supported (p = 0.475).
- **Imputation.** 24 values (16 experience, 8 education) are imputed rather than
  observed. The rules are simple and logged, and the results on the original values
  are almost identical (§9.6). The main sensitivity: Tenure² is significant at 10% only
  without imputation.
- **Sample size.** Missing data reduce the model sample from 526 to 490 (listwise deletion).
- **Data vintage.** The data date from 2014 and come from one firm, so external validity
  is limited.

---

## 13. References

- Becker, G. S. (1964). *Human Capital*. University of Chicago Press.
- Blau, F. D., & Kahn, L. M. (2017). The gender wage gap: Extent, trends, and explanations. *Journal of Economic Literature*, 55(3), 789–865.
- Breusch, T. S., & Pagan, A. R. (1979). A simple test for heteroscedasticity and random coefficient variation. *Econometrica*, 47(5), 1287–1294.
- Jarque, C. M., & Bera, A. K. (1980). Efficient tests for normality, homoscedasticity and serial independence of regression residuals. *Economics Letters*, 6(3), 255–259.
- Korenman, S., & Neumark, D. (1991). Does marriage really make men more productive? *Journal of Human Resources*, 26(2), 282–307.
- MacKinnon, J. G., & White, H. (1985). Some heteroskedasticity-consistent covariance matrix estimators with improved finite sample properties. *Journal of Econometrics*, 29(3), 305–325.
- Mincer, J. (1974). *Schooling, Experience, and Earnings*. NBER / Columbia University Press.
- Ramsey, J. B. (1969). Tests for specification errors in classical linear least-squares regression analysis. *Journal of the Royal Statistical Society B*, 31(2), 350–371.
- Seabold, S., & Perktold, J. (2010). statsmodels: Econometric and statistical modeling with Python. *Proc. 9th Python in Science Conference*.
- Spence, M. (1973). Job market signaling. *Quarterly Journal of Economics*, 87(3), 355–374.
- Topel, R. (1991). Specific capital, mobility, and wages: Wages rise with job seniority. *Journal of Political Economy*, 99(1), 145–176.
- White, H. (1980). A heteroskedasticity-consistent covariance matrix estimator and a direct test for heteroskedasticity. *Econometrica*, 48(4), 817–838.
- Wooldridge, J. M. (2020). *Introductory Econometrics: A Modern Approach* (7th ed.). Cengage.

---

## 14. Output file index

| File (`output/tables/`) | Contents | README section |
|---|---|---|
| `cleaning_log`, `cleaning_by_rule`, `missingness`, `dummy_sets`, `imputation_log` | Data processing | §4 |
| `descriptives` | Summary statistics | §5 |
| `models_ladder`, `sig_M3`, `sig_preferred` | Coefficient and significance tables | §10.1, §10.4 |
| `nested_tests`, `joint_tests` | F-tests and robust Wald tests | §10.1 |
| `quadratic_effects`, `interaction_effects` | Marginal and conditional effects | §10.2–10.3 |
| `coef_path`, `job_sorting`, `alt_background`, `background_tests` | Subsidiary influences | §10.6 |
| `vif`, `diagnostics`, `se_comparison`, `robustness` | Assumption checks | §9 |
| `output/values.json` | Headline numbers quoted in this README | — |
