```{=latex}
\begin{titlepage}
\centering
\vspace*{6cm}
{\LARGE\bfseries HCL Technologies\par}
\vspace{0.8cm}
{\Large DOM207 MP2 Report\par}
\vspace{2.5cm}
\begin{tabular}{ll}
\toprule
\textbf{Team member} & \textbf{Roll number} \\
\midrule
Lalit Maurya & 2310110164 \\
Jia Swapnil Khot & 2310110491 \\
Rachit Kumar & 2310110234 \\
\bottomrule
\end{tabular}
\vfill
{\large \today\par}
\end{titlepage}
```

# Introduction

HCL Technologies asked us to look at how its employees are paid and what drives the differences. We were given a file of 526 employees. Besides the average hourly salary, it records each employee's education, professional experience, years with HCL (tenure), gender, marital status and number of dependents, whether they are non-privileged, where they live, their IT work group and division, whether they work from home, and their parents' education and number of siblings.

We had four questions in mind. How much do education, experience and tenure add to pay, and does that change over a career? Are women and non-privileged employees paid less than colleagues with the same profile? Do these effects interact, for instance is the gender gap different for married and single staff? And through which channels do they work, for instance does education raise pay directly, or by getting people into better-paid divisions?

One caveat up front: the file is a single snapshot, with no performance ratings, hours or job grades. What we can show is how pay differs with each characteristic once the others are held constant. We cannot show that any of them causes the difference.

**Our recommendations in brief:**

1. Review the pay of women. Women earn 10% to 34% less than men with the same education, experience, job and location, and about two-thirds of the raw gap is not explained by anything in the data.
2. Audit raises and promotions by gender. Each year with HCL adds about 2.8% to a man's pay but only 1.5% to a woman's.
3. Remove marital status from pay decisions. Married men earn up to 26% more than comparable single men; married women show no such premium.
4. Support further education and make entry to R&D transparent. Each extra year of education is worth more than the last, and part of its return comes through placement in R&D, which pays 22% more.
5. Compare the pay of the architecture and AI groups with the market. Both are paid about 27% less than comparable employees in other IT work.

# Data processing

The raw file had 526 employees and 25 columns, with a unique id for each employee and no duplicate rows. We cleaned it in Python with pandas [2]. Since the brief does not let us add data, we handled two kinds of problem differently. Values that were plainly wrong and could not be recovered were set to missing. Values that were present but impossible or implausible were replaced using the rest of the data, and we kept the originals. Table 1 lists the rules.

**Invalid values.** Eight cells had text where a number should be, such as `acb` in salary and `SS0` in education. Six yes/no variables held something other than 0 or 1, for example 100 in north-central and 1111 in south. Nine counts could not be real, like 1001 years of education or 333 siblings. On salary, one value was negative ($-2.45$) and seven were far too high: 1111, 435.67, 333.33, 60, 55.78, 55.67 and 46.67 per hour, when the median is 4.65. Salaries are skewed, so we applied Tukey's rule [6] to log salary rather than to the raw values, which gives a cut-off of 25.00 per hour. The highest salary we kept is 24.98 and the lowest we removed is 46.67, so the cut-off sits in an obvious gap. All 31 values were set to missing.

**Tenure longer than experience.** Sixteen employees had been with HCL longer than their professional experience, one of them for 34 years against 20 years of experience. Time at HCL counts as professional experience, so this cannot be right. We set experience equal to tenure, which is the smallest change that makes each record add up.

**Very low education.** Eight employees were recorded with 0 to 5 years of education, which is hard to believe for an IT company. All eight had 22 to 51 years of experience. We replaced each value with the median education of colleagues in the same experience band who had at least 6 years of schooling. That median was 12 years in every band.

```{=latex}
\begin{table}[htbp]
\centering
\caption{Rules used to clean the data}
\small
\begin{tabular}{@{}lllr@{}}
\toprule
Rule & Problem & Action & \multicolumn{1}{r}{Cells} \\
\midrule
R1 & Text in a numeric column & Set to missing & 8 \\
R2 & Yes/no variable not 0 or 1 & Set to missing & 6 \\
R3 & Education outside 0–20 years, siblings outside 0–15 & Set to missing & 9 \\
R4 & Negative salary & Set to missing & 1 \\
R5 & Salary above 25.00 per hour (Tukey limit on log salary) & Set to missing & 7 \\
R6 & Tenure longer than experience & Experience set equal to tenure & 16 \\
R7 & Education below 6 years & Median of the same experience band (12 years) & 8 \\
\bottomrule
\end{tabular}
\end{table}
```

**Groups of categories and sample.** Province, IT work group and division are each stored as a set of yes/no columns. We checked that nobody falls into two categories of the same set. Employees in none of them form the reference group: 125 in other provinces, 79 in other IT work and 245 in other divisions. After cleaning, 490 employees have every variable the main models need, and we use the same 490 throughout so that the models can be compared like for like.

# Data visualization

**Salaries are skewed, so we work with their logarithm.** The median is 4.65 per hour and the mean 5.93, with a long tail reaching 24.98 (Figure 1). Taking logs brings the skewness down from 1.98 to 0.38. It also means the coefficients can be read as percentage differences in pay, which is how pay is usually discussed.

![Salary (left) and log salary (right) for the 515 employees with a valid salary.](output/figures/fig1_salary_distribution.png){width=78%}

**Education, experience and tenure do not act in a straight line.** Pay barely moves until about 11 years of education and then climbs quickly (Figure 2). With experience it rises for about 20 years and then drifts down. With tenure it jumps in the first few years at HCL and then flattens out. Each of these shapes needs a squared term in the model.

![Log salary against education, experience and tenure. The red line is a smoothed average.](output/figures/fig2_functional_form.png){width=95%}

**The gender gap depends on marital status, and pay varies a lot by job.** Among single staff, women earn 11% less than men (4.61 against 5.19 per hour). Among married staff the gap is 43% (4.59 against 7.99). The difference comes from married men, who earn far more than single men, while married and single women earn about the same (Figure 3a). That is why we test a gender × marriage interaction. The median salary is 3.42 per hour in AI applications and 3.86 in architecture, compared with 6.00 in other IT work (Figure 3b), and 6.63 in R&D compared with 4.00 elsewhere, so work group and division go into every full model.

```{=latex}
\begin{figure}[H]
\centering
\begin{subfigure}[b]{0.42\textwidth}\centering
\includegraphics[width=\textwidth]{output/figures/fig3_gender_marriage.png}
\caption{Mean salary by gender and marital status}
\end{subfigure}\hfill
\begin{subfigure}[b]{0.55\textwidth}\centering
\includegraphics[width=\textwidth]{output/figures/fig5_it_group.png}
\caption{Salary by IT work group}
\end{subfigure}
\caption{Salary by gender, marital status and work group.}
\end{figure}
```

These patterns overlap. Women make up 64% of AI applications and 66% of client-only work but 48% of all staff, educated employees are more often in R&D, and experience and tenure move together (correlation 0.51). The models pull these effects apart before we draw any conclusions.

# Hypotheses

We start from Mincer's earnings function [3], in which log pay depends on schooling, experience and experience squared. The idea is that schooling and learning on the job build skills that employers pay for, and that this learning slows down later in a career. Table 2 shows the role each variable plays and why it is there.

| Variable | Role | Why it should affect salary | Expected |
|:------------------|:----------|:--------------------------------------------------|:-------------------|
| Education | Study | Raises productivity and signals ability | Positive, rising |
| Experience | Study | Skills learned on the job, at a slowing rate | Positive, slowing |
| Tenure | Study | Skills specific to HCL; internal promotion | Positive, slowing |
| Female | Study | Discrimination, job sorting, career breaks | Negative |
| Non-privileged | Study | Weaker networks and access to well-paid roles | Negative |
| Married, dependents | Control | Marriage premium for men; caring duties | + for men; $-$ |
| Metro, province | Control | Productivity, cost of living, regional markets | +; unknown |
| Work group, division, home working | Control | Market value of each function; flexibility | Unknown |
| Parents' education, siblings | Excluded | Should act only through the employee's education | None directly |

Table: Variables, their roles and the reasons for including them

**Controls and exclusions.** Every control affects pay and is linked to at least one study variable. If we left it out, its effect would be wrongly credited to that study variable, which is known as omitted-variable bias [8]. Family background is a different case. Parents' education and siblings should matter only through how much schooling the employee got, so putting them next to education would take away part of education's effect. Rather than assume this, we test it with the alternative models described below.

Table 3 lists the hypotheses. We picked the interactions in H6 to H9 before fitting any model.

| | Hypothesis |
|:-----|:---------------------------------------------------------------------------------|
| H1 | Education raises salary, and each extra year is worth more than the last |
| H2 | Experience raises salary, at a slowing rate |
| H3 | Tenure raises salary, at a slowing rate |
| H4 | Women earn less than comparable men |
| H5 | Non-privileged employees earn less than comparable colleagues |
| H6 | The gender gap is larger among married employees, because only men receive a marriage premium |
| H7 | Returns to education, experience or tenure differ between men and women |
| H8 | The marriage premium changes over a career |
| H9 | Education and experience reinforce each other |
| H10 | Family background affects salary only through education |
| H11 | Part of the effect of education and gender comes through the work group and division |

Table: Hypotheses

# Analysis

**Method.** We used ordinary least squares (OLS) regression, which estimates the effect of each variable with the others held constant. Because the outcome is log hourly salary, a coefficient $b$ on a yes/no variable means pay differs by $100(e^{b}-1)$ percent. The preferred model looks like this:
$$\ln(\text{salary}) = \beta_0 + \beta_1\,\text{edu} + \beta_2\,\text{edu}^2 + \beta_3\,\text{exper} + \beta_4\,\text{exper}^2 + \beta_5\,\text{ten} + \beta_6\,\text{ten}^2 + \dots + \varepsilon .$$
All standard errors are HC3 robust [8], so they stay valid if the spread of salaries differs between employees. We call a result significant at $p < 0.05$ and weak evidence between 0.05 and 0.10. Everything was run in Python with pandas [2] and statsmodels [5], and the full output and the logs of every data change are in the submitted files.

**Model building.** We added one group of variables at a time (Table 4), and each step improved the model on an F-test ($p \le 0.006$ every time). M6 adds just the interaction that theory and Figure 3a point to, but it failed the specification test described below ($p = 0.043$), so something was still missing. M5 adds all seven interactions we had chosen in advance. Only three were significant, and M7 keeps those three. Dropping the other four makes no real difference ($F = 0.88$, $p = 0.475$), and M7 has the lowest AIC of all the models and passes the specification test.

**Performance on unseen data.** A good model should also work on employees it has not seen. We held back a random 20% of employees, fitted each model on the other 80%, and measured the mean squared error (MSE) of its log-salary predictions on the group held back. We then repeated the check with 10-fold cross-validation, where every employee is held out once. The error drops at nearly every step, and M7 does best on both measures (held-out MSE 0.118, cross-validated MSE 0.137). Its extra terms help it predict, not just fit the sample.

| Model | Adds | Adj. R² | AIC | Held-out MSE | CV MSE | What changed |
|:------|:------------------------------------|------:|------:|------:|------:|:----------------------------------------|
| M1 | Education, experience, tenure | 0.307 | 601.9 | 0.203 | 0.201 | Education worth about 10% a year |
| M2 | Female, non-privileged | 0.378 | 550.9 | 0.188 | 0.181 | Women about 26% lower |
| M3 | All controls | 0.501 | 457.5 | 0.147 | 0.151 | Experience not significant |
| M4 | Squares of education, experience, tenure | 0.539 | 421.7 | 0.128 | 0.142 | Experience significant again |
| M5 | Seven candidate interactions | 0.556 | 409.8 | 0.122 | 0.138 | Three of seven significant |
| M6 | Female × married | 0.548 | 412.4 | 0.126 | 0.139 | Theory only; fails RESET |
| M7 | Female × married, female × tenure, married × experience | 0.556 | 405.5 | 0.118 | 0.137 | Preferred model |

Table: Models estimated (AIC: Akaike information criterion; MSE of log salary on the 20% held out and in 10-fold cross-validation; lower is better)

**Alternative models.** To trace indirect effects we did three things. We followed how the coefficients of the study variables changed as controls were added. We regressed membership of each work group and division on gender and education, to see who ends up where (job sorting). And we fitted four family-background models: education on background (A1), salary on background without education (A2), M7 with background added (A3), and M7 on the same 479 employees (A4).

**Checking the model assumptions.** Table 5 goes through the six classical OLS assumptions, plus independence and influential cases, with what we tested and what we did about it.

![Checks of M7: residuals against predicted values, normal Q–Q plot, scale–location, and Cook's distance for each employee with the 4/n threshold (outliers in red).](output/figures/fig6_residual_diagnostics.png){width=72%}

```{=latex}
\begin{table}[htbp]
\centering
\caption{Checks of the model assumptions for M7}
\small
\begin{tabular}{@{}>{\raggedright\arraybackslash}p{2.7cm}>{\raggedright\arraybackslash}p{2.9cm}>{\raggedright\arraybackslash}p{5.6cm}>{\raggedright\arraybackslash}p{4.3cm}@{}}
\toprule
Assumption & Test & Result & Action \\
\midrule
Parameter linearity & Ramsey RESET [4] & M3 fails ($p = 0.005$), M6 fails ($p = 0.043$), M7 passes ($p = 0.086$) & Squared terms and interactions \\[2pt]
Random sampling & Study design & Single cross-section of 526 employees with unique ids & Results describe HCL staff, not a wider population \\[2pt]
No perfect collinearity & Variance inflation factor & Largest 2.63 in M3; 59.2 in M7 from education and its square, 5.84 after centring & Centred education, experience and tenure \\[2pt]
Zero conditional mean & RESET; theory & Form passes RESET; performance and ability are not recorded & Rich controls; results read as associations \\[2pt]
Homoskedasticity & Breusch–Pagan [1], White [7] & Salary in levels fails BP ($p < 0.001$); log salary passes BP ($p = 0.132$) and White ($p = 0.316$; full $p = 0.415$) & Log salary; robust standard errors; weighted least squares \\[2pt]
Normality & Jarque–Bera, Q–Q plot & Rejected; symmetric (skewness $-0.02$) with heavy tails & Large sample; robust standard errors \\[2pt]
Independence & Durbin–Watson; Breusch–Godfrey & DW 1.89; no autocorrelation ($p = 0.216$) & None needed \\[2pt]
Influential cases & Cook's distance & Largest 0.062, far below 1; 31 above $4/n$ & Re-estimated without them \\[2pt]
\bottomrule
\end{tabular}
\end{table}
```

The RESET test checks whether squares and cubes of the model's own predictions explain anything extra. The linear model fails it, and adding the squared terms and interactions fixes the problem.

For equal spread, the contrast between salary in levels and log salary is clear. In levels, the residuals fan out as predicted salary rises and the Breusch–Pagan test rejects equal spread. In logs there is no visible pattern (Figure 4, top left) and the test passes. We ran the White test both ways. The full version, with every regressor, square and cross-product, has 319 auxiliary terms, and with that many it has very little power. It does not even reject for salary in levels ($p = 0.897$). The special form [8], which uses only the predictions and their squares, behaves as expected: it rejects for levels ($p < 0.001$) and passes for logs ($p = 0.316$). In any case, robust and ordinary standard errors differ by only $-2\%$ to $+18\%$.

All VIFs are below 3 in the linear model. In M7 the large values come only from a variable sitting next to its own square or interaction. Centring education, experience and tenure before squaring them changes no prediction or test and brings every VIF under 10. Tenure stays at 5.84, a little over the stricter cut-off of 5, because it also appears in its square and in female × tenure, so we always test it together with those terms.

The residuals are symmetric and stray from normal only in the tails (Figure 4, top right), which is not a concern with 490 employees. The Durbin–Watson statistic is close to 2, and the Breusch–Godfrey test finds no first-order autocorrelation. Finally, the Cook's distance plot (Figure 4, bottom right) shows that no single employee dominates the fit.


**Robustness.** We re-ran M7 four more ways: on the original, unimputed values, without the 24 imputed employees, without the 31 most influential employees, and with weighted least squares (Table 6). The interactions and the gender effect keep their sign and significance every time. The imputation changes only one thing: the square of tenure is significant at 10% on the original values ($p = 0.068$) but not after imputation ($p = 0.105$).

| Version | N | Female | Female × married | Female × tenure | Married × experience |
|:----------------------------------|----:|--------:|--------:|--------:|--------:|
| M7 | 490 | $-0.101$\* | $-0.196$\*\* | $-0.013$\*\* | $-0.0066$\*\* |
| Original values, no imputation | 490 | $-0.101$\* | $-0.192$\*\* | $-0.014$\*\* | $-0.0064$\*\* |
| Without the 24 imputed employees | 471 | $-0.116$\* | $-0.185$\*\* | $-0.014$\*\* | $-0.0071$\*\* |
| Without the 31 most influential | 459 | $-0.077$\* | $-0.212$\*\*\* | $-0.018$\*\*\* | $-0.0084$\*\*\* |
| Weighted least squares | 490 | $-0.114$\*\* | $-0.160$\*\* | $-0.016$\*\*\* | $-0.0084$\*\*\* |

Table: Robustness of the main results (\* $p<0.10$, \*\* $p<0.05$, \*\*\* $p<0.01$)

# Results

**Descriptive statistics.** Table 7 summarises every variable and Table 8 shows how the independent variables correlate. The strongest correlations, experience with tenure and education with the R&D division, are both 0.51. That is nowhere near high enough to make two variables hard to tell apart, which fits with the low VIFs. Parents' education and siblings hardly correlate with anything.

{{float:descriptives|Descriptive statistics after cleaning (kurtosis is excess kurtosis; Q1 and Q3 are the first and third quartiles)}}

{{float:iv_correlations|Correlations between the independent variables (the full matrix of all IVs is in the submitted files)}}

**Model estimates.** Table 9 gives the M7 estimates. The model explains 58% of the variation in log salary (adjusted R² 0.556; robust $F = 30.2$, $p < 0.001$). That is below the 0.85 often expected of business models, but normal for salary data on individual employees, where a lot depends on things the file does not record, such as performance and negotiation. Because of the squared terms and interactions, some coefficients mean little on their own. The education coefficient, for example, is the effect at zero years of schooling, and the female coefficient is the gap for a single woman in her first year. So we test each variable together with its square or interactions and quote effects at typical values. We also read a non-significant result as a lack of evidence, not as proof that there is no effect.

```{=latex}
\begin{table}[htbp]
\centering
\caption{Estimates of the preferred model M7 (N = 490; * $p<0.10$, ** $p<0.05$, *** $p<0.01$)}
\small
\begin{tabular}{@{}lrrrl@{\hspace{2em}}lrrrl@{}}
\toprule
Variable & Coef. & SE & p &  & Variable & Coef. & SE & p &  \\
\midrule
Intercept & 1.5023 & 0.3768 & $<$0.001 & *** & Dependents & $-0.0353$ & 0.0140 & 0.012 & ** \\
Education & $-0.0738$ & 0.0584 & 0.206 &  & Metro area & 0.1353 & 0.0431 & 0.002 & *** \\
Education² & 0.0049 & 0.0023 & 0.031 & ** & North-central & $-0.0347$ & 0.0457 & 0.448 &  \\
Experience & 0.0292 & 0.0055 & $<$0.001 & *** & South & $-0.0535$ & 0.0458 & 0.242 &  \\
Experience² & $-0.0006$ & 0.0001 & $<$0.001 & *** & West & 0.0445 & 0.0604 & 0.462 &  \\
Tenure & 0.0274 & 0.0083 & $<$0.001 & *** & IT requirements & $-0.0924$ & 0.1029 & 0.369 &  \\
Tenure² & $-0.0004$ & 0.0003 & 0.105 &  & IT programming & $-0.0958$ & 0.0577 & 0.097 & * \\
Female & $-0.1006$ & 0.0599 & 0.093 & * & IT quality assurance & $-0.1563$ & 0.0761 & 0.040 & ** \\
Non-privileged & $-0.0086$ & 0.0605 & 0.887 &  & IT architecture & $-0.3116$ & 0.0557 & $<$0.001 & *** \\
Married & 0.2655 & 0.0677 & $<$0.001 & *** & AI applications & $-0.3118$ & 0.0769 & $<$0.001 & *** \\
Female × married & $-0.1961$ & 0.0766 & 0.011 & ** & Client-only work & $-0.1005$ & 0.0615 & 0.102 &  \\
Female × tenure & $-0.0125$ & 0.0056 & 0.027 & ** & R\&D division & 0.2007 & 0.0521 & $<$0.001 & *** \\
Married × experience & $-0.0066$ & 0.0029 & 0.021 & ** & Tech support division & 0.0698 & 0.0562 & 0.214 &  \\
 &  &  &  &  & Works from home & $-0.1102$ & 0.0595 & 0.064 & * \\
\bottomrule
\end{tabular}
\end{table}
```

**Education pays more with each additional year.** Education and its square are jointly significant ($\chi^2 = 27.7$, $p < 0.001$), and the square is positive ($p = 0.031$). One more year of schooling adds 4.4% to pay at 12 years, 6.3% at 14 and 8.3% at 16, which supports H1.

**Experience raises pay early in a career, then levels off.** For a single employee, one more year of experience adds 2.4% at 5 years and 1.5% at 13 years, and the curve peaks at 26 years ($\chi^2 = 28.4$, $p < 0.001$). For married employees the peak comes earlier, at about 20 years. In the linear model M3 experience seemed to have no effect at all ($p = 0.489$), because a straight line through a curve that goes up and then down is almost flat. H2 is supported.

**Each year with HCL adds about 2.8% to a man's pay, with no clear slowdown.** Tenure and its square are jointly significant ($\chi^2 = 16.8$, $p < 0.001$), but the square alone is not ($p = 0.105$). So the first half of H3 holds, but not the slowdown.

**Women earn less than comparable men, and the gap widens with marriage and with years at HCL.** The gender terms are jointly significant ($\chi^2 = 64.1$, $p < 0.001$). In her first year, a single woman earns 9.6% less than a comparable single man, though this is only weak evidence ($p = 0.093$). After ten years the gap is 20.2% (Table 10). For married women it starts at 25.7% and reaches 34.4% after ten years. It widens because a year at HCL adds only 1.5% to a woman's pay, compared with 2.8% for a man. This supports H4 and H6, and H7 as far as tenure is concerned.

| Comparison | Evaluated for | Difference | p | Evaluated for | Difference | p |
|:----------------------|:----------------------|-------:|------:|:----------------------|-------:|------:|
| Women vs men | Single, first year | $-9.6\%$ | 0.093 | Married, first year | $-25.7\%$ | <0.001 |
| | Single, 5 years | $-15.0\%$ | 0.009 | Married, 5 years | $-30.2\%$ | <0.001 |
| | Single, 10 years | $-20.2\%$ | 0.003 | Married, 10 years | $-34.4\%$ | <0.001 |
| Married vs single | Men, 5 years' exp. | $+26.2\%$ | <0.001 | Women, 5 years' exp. | $+3.7\%$ | 0.558 |
| | Men, 15 years' exp. | $+18.1\%$ | 0.006 | Women, 15 years' exp. | $-2.9\%$ | 0.566 |
| | Men, 25 years' exp. | $+10.5\%$ | 0.163 | Women, 25 years' exp. | $-9.1\%$ | 0.087 |
| Extra year at HCL | Men | $+2.8\%$ | <0.001 | Women | $+1.5\%$ | 0.052 |

Table: Effects of gender, marriage and tenure in M7 (years refer to years at HCL unless stated)

**Married men earn a premium that fades over time, but married women do not.** A married man with 5 years of experience earns 26.2% more than a comparable single man. By 15 years the premium is 18.1%, and by 25 years it is no longer significant (Figure 5). For married women we find no significant premium at any point, so H8 is supported. None of the other interactions in M5 is significant: gender with education ($p = 0.23$) or with experience ($p = 0.72$), education with experience ($p = 0.21$), and gender with non-privileged status ($p = 0.39$). H9 is therefore not supported, and we see no evidence that women get a different return to education or general experience than men do.

![Predicted hourly salary against experience for the four groups, other variables at their means (M7).](output/figures/fig8_predicted_profiles.png){width=58%}

**We find no evidence of a pay difference by non-privileged status or province, but location, dependents and job matter.** The difference for non-privileged employees is small and not significant ($-0.9\%$, $p = 0.887$), so H5 is not supported, and the provinces are not jointly significant either ($\chi^2 = 3.8$, $p = 0.287$). Neither result proves that pay is equal; both are simply inconclusive. Employees in metro areas earn 14.5% more, and each dependent goes with 3.5% lower pay. R&D pays 22.2% more than other divisions. Compared with other IT work, architecture and AI applications both pay 26.8% less and quality assurance 14.5% less. The penalty for working from home ($-10.4\%$, $p = 0.064$) is weak evidence only.

**Part of the return to education comes through placement in R&D, but most of the gender gap is unexplained.** When the job and location controls go in, the education coefficient drops from 0.094 to 0.058 (Table 11). Roughly 39% of the return to education therefore comes from where educated employees end up working. R&D is one clear channel: each extra year of education raises the chance of being in R&D by 10.2 percentage points. The gender gap behaves differently. It falls from 33.8% with no controls to 25.9% with education, experience and tenure, and only to 23.1% with everything, leaving about two-thirds of it unexplained. Job sorting does little here because its effects cancel out. Women are 10.3 points less likely to be in R&D, which pays well, but also 8.4 points less likely to be in architecture, which pays badly. H11 holds for education and only weakly for gender.

```{=latex}
\begin{table}[htbp]
\centering
\caption{Coefficients of the study variables as the controls enter (* $p<0.10$, ** $p<0.05$, *** $p<0.01$)}
\small
\begin{tabular}{@{}lrrrrr@{}}
\toprule
Model & Education & Experience & Tenure & Female & Adjusted R² \\
\midrule
Female only & & & & $-0.413$*** & 0.147 \\
Human capital only (M1) & 0.101*** & 0.003* & 0.022*** & & 0.307 \\
Study variables (M2) & 0.094*** & 0.003* & 0.017*** & $-0.300$*** & 0.378 \\
+\ family and location & 0.078*** & 0.002 & 0.015*** & $-0.274$*** & 0.432 \\
+\ work group and division (M3) & 0.058*** & 0.001 & 0.013*** & $-0.262$*** & 0.501 \\
\bottomrule
\end{tabular}
\end{table}
```

**We find no evidence that family background affects pay, directly or through education.** Parents' education and siblings do not explain the employee's own education (A1: $p = 0.787$), do not explain salary when education is left out (A2: $p = 0.971$), and add nothing once education is in (A3: $p = 0.889$). Including them moves the education coefficient by less than 0.001. H10 is not supported, and leaving family background out of the main model is justified. Table 12 brings all the tests together.

| | Test | Result | Finding |
|:----|:------------------------------------|:------------------------------------|:-------------------|
| H1 | Education and its square | $p < 0.001$; square positive ($p = 0.031$) | Supported |
| H2 | Experience and its square | $p < 0.001$; peak at 26 years | Supported |
| H3 | Tenure and its square | $p < 0.001$; square $p = 0.105$ | Rise only |
| H4 | All gender terms | $p < 0.001$; gap 10% to 34% | Supported |
| H5 | Non-privileged | $p = 0.887$ | No evidence |
| H6 | Female × married | $-0.196$, $p = 0.011$ | Supported |
| H7 | Gender interactions | Tenure $p = 0.027$; others $p > 0.2$ | Tenure only |
| H8 | Married × experience | $-0.0066$, $p = 0.021$ | Supported |
| H9 | Education × experience | $p = 0.21$ | Not supported |
| H10 | Models A1 to A3 | All $p > 0.78$ | No evidence |
| H11 | Coefficient path; job sorting | Education $-39\%$; gender $-0.30$ to $-0.26$ | Education only |

Table: Summary of the hypothesis tests

# Recommendations

**1. Review the pay of women.** Women earn 9.6% to 34.4% less than men with the same education, experience, tenure, job and location, and about two-thirds of the raw gap is not explained by anything in the data. We recommend a formal pay-equity review. The model in this report could be rerun each year to flag employees who are paid well below what their profile predicts. Since we had no performance ratings, the review should first check whether performance accounts for part of the gap.

**2. Audit raises and promotions by gender.** A year at HCL adds about 2.8% to a man's pay and 1.5% to a woman's, so the gap between single men and women doubles from 9.6% to 20.2% over ten years. HCL should standardise how increases and promotions are decided, and compare what men and women with the same rating actually receive.

**3. Remove marital status from pay decisions.** Married men earn up to 26.2% more than comparable single men, while married women show no significant premium. This premium explains most of why the gender gap is so much larger among married staff. Any allowance or discretionary payment linked to family status should be reviewed.

**4. Support further education and make entry to R&D transparent.** Each extra year of education is worth more than the last (4.4% at 12 years, 8.3% at 16), and about 39% of that return comes through placement, mostly in R&D, which pays 22.2% more. Tuition support should raise both productivity and pay. Women are 10.3 points less likely to be in R&D, so its entry criteria should be published and applied the same way to everyone.

**5. Compare the pay of the architecture and AI groups with the market.** Both earn about 26.8% less than comparable employees in other IT work. These are strategic skills, and the data cannot tell us why they are paid less, so HCL should check market rates before changing anything.

**6. Plan for the late-career plateau, and do not adjust pay by province or privilege.** The return to experience falls to almost nothing after about 26 years (20 for married staff), so senior career tracks and performance-linked pay would help keep experienced people. We found no evidence of a pay difference by province ($p = 0.287$) or non-privileged status ($p = 0.887$), so there is no basis for adjusting pay on either, and the 14.5% metro premium is in line with the cost of living. Working from home ($-10.4\%$, $p = 0.064$) is worth monitoring but not acting on yet. Finally, simple range checks in the HR system would have caught the 55 errors and implausible values we had to deal with.

**Limitations.** The data is a single snapshot with no performance, hours or job grades, so it shows differences in pay rather than their causes, and part of the unexplained gender gap may come from things that are not recorded. The 24 imputed values only affect whether the return to tenure slows down. M7 passes the specification test at 5% but not at 10% ($p = 0.086$). Its three interactions were picked from a larger set, which raises the risk of a false positive, although we chose that set in advance and all three survive every robustness check. Lastly, the data covers one company in 2014.

# References

```{=latex}
\begingroup\small\setlength{\parskip}{0.25em}
```

[1] Breusch, T. S. and Pagan, A. R. (1979). A simple test for heteroscedasticity and random coefficient variation. *Econometrica*, 47(5), 1287–1294.

[2] McKinney, W. (2010). Data structures for statistical computing in Python. *Proceedings of the 9th Python in Science Conference*, 56–61.

[3] Mincer, J. (1974). *Schooling, Experience, and Earnings*. New York: National Bureau of Economic Research.

[4] Ramsey, J. B. (1969). Tests for specification errors in classical linear least-squares regression analysis. *Journal of the Royal Statistical Society, Series B*, 31(2), 350–371.

[5] Seabold, S. and Perktold, J. (2010). Statsmodels: Econometric and statistical modeling with Python. *Proceedings of the 9th Python in Science Conference*, 92–96.

[6] Tukey, J. W. (1977). *Exploratory Data Analysis*. Reading, MA: Addison-Wesley.

[7] White, H. (1980). A heteroskedasticity-consistent covariance matrix estimator and a direct test for heteroskedasticity. *Econometrica*, 48(4), 817–838.

[8] Wooldridge, J. M. (2020). *Introductory Econometrics: A Modern Approach* (7th ed.). Boston: Cengage.

```{=latex}
\endgroup
```
