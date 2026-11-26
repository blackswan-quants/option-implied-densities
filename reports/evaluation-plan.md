# Evaluation plan: realised move, density measures, H1/H2 tests

**Project:** P4 Option implied densities around news (BlackSwan Quants 2026/27)
**Author:** Francesco Nicolò (task B)
**Status:** draft for review at the weekly call (by Friday 27 November 2026)
**Scope:** how the pre-event densities produced by the pipeline are evaluated against what happened after the release. It does not cover how the densities are extracted.
**Data:** SPXW pre-event closing snapshots from 2022, about 150 events (as communicated by the lead, 24/11/2026).

Each decision is tagged with its origin:

- **[brief]** BSQ project proposal, Project Brief #4
- **[call]** first call notes (week 1 plan)
- **[lit]** Figlewski (2018), *Risk neutral densities: a review*, a base paper of the brief
- **[B]** proposed here, to be agreed by the team

Decisions marked **[B]** are open to change at the call. Everything else follows from the brief, the first call or the literature.

---

## 1. Notation

| Symbol | Meaning |
|---|---|
| $i = 1,\dots,n$ | event index, $n \approx 150$ |
| $t_i$ (`as_of`) | timestamp of the pre-event snapshot, with time zone |
| $T_i$ | expiry used for event $i$, in years from $t_i$ |
| $F_i$, $D_i$ | forward and discount factor for that expiry; the forward comes from put–call parity [brief] |
| $k = \ln(K/F)$ | log-moneyness, the axis on which densities are passed between modules [call] |
| $q_i(k)$, $F_Q^{(i)}(k)$ | risk-neutral density and CDF of $x = \ln(S_T/F)$ |
| $S_{T,i}$ | settlement value of SPX at expiry $T_i$ |

---

## 2. Realised move

### 2.1 Definition

$$X_i = \ln\frac{S_{T,i}}{F_i}\qquad\text{[call]}$$

- $X_i$ lives on the same axis $k$ as the density, so $F_Q^{(i)}(X_i)$ is defined directly.
- The first call writes this quantity as $R = \ln(S_T/F)$; in this document $R_i$ denotes the simple return defined below.
- The move is measured against the forward, not the spot: $F = \mathbb E^Q[S_T]$, it removes carry and dividends, and it comes from the same quotes as the density.
- **Use in the tests [B]:**
  - H2 uses the signed $X_i$;
  - H1 regressions on the straddle implied move use the absolute simple return $|R_i| = |e^{X_i} - 1|$, because the implied move is defined on simple returns (Section 3.3). Regressions on log-scale measures ($s$, interquantile range) use $|X_i|$. For moves of about 1% the two differ by about 0.005%.
- The choice between $X$ and $R$ does not affect H2: the PIT is invariant under increasing transformations, so $F_R(R_i) = F_X(X_i)$.

### 2.2 Horizon, expiry and snapshot [B]

The move must be measured over **the same horizon as the density**: $S_{T,i}$ is the settlement of the expiry the density comes from. Using a later expiry dilutes the release into ordinary days; measuring the move over a shorter window than the density biases moves downwards by construction.

| Release | Time (ET) | Snapshot $t_i$ | Expiry $T_i$ |
|---|---|---|---|
| CPI | 08:30 | close of the previous trading day | SPXW expiring on the release day |
| Payrolls | 08:30 | close of the previous trading day | SPXW expiring on the release day |
| FOMC | 14:00 | close of the previous trading day (13:45 ET on the release day if available) | SPXW expiring on the release day |

- SPXW are PM-settled, so $S_{T,i}$ is the official SPX close on the expiry date (the early close on half days).
- If no SPXW expires on the release day, use the next expiry; these events are listed in the report.
- Release times are stored with explicit time zones (`America/New_York`) [brief]. US and EU daylight saving changes differ by a few weeks a year.

### 2.3 Overlapping releases [B]

An event is flagged `overlap` if another release of the three types falls in $(t_i, T_i]$. With daily expiries this happens essentially only when two releases share a day (e.g. CPI and FOMC on 12 June 2024).

Overlapping events are merged into one observation, with type `combined`, so that no move is counted twice.

### 2.4 Exclusions [B]

An event is excluded if the pipeline quality checks fail (density mass inside the grid, butterfly condition $g(k) \ge 0$, SVI fit error above a threshold set with C). Every exclusion is listed in the report with its reason.

---

## 3. Measures extracted from the density

**General rule:** every measure is expressed as a return over the option horizon $T_i$, never in index points and never annualised [call].

### 3.1 Standard deviation [call]

$$\mu_i = \int k\, q_i(k)\, dk,\qquad s_i = \sqrt{\int (k-\mu_i)^2\, q_i(k)\, dk}$$

Computed by numerical integration on the pipeline grid. Uses the whole density but depends heavily on the tails, which beyond the quoted strikes come from the SVI extrapolation: for a normal density, the region beyond $\pm 2.5\,s$ holds 1.2% of the probability but about 10% of the variance.

### 3.2 Interquantile range [call]

$$\text{IQR}_{\alpha,i} = k_{1-\alpha,i} - k_{\alpha,i},\qquad k_{\alpha,i} = \big(F_Q^{(i)}\big)^{-1}(\alpha)$$

- $\alpha = 0.10$ (central 80%) by default [B]. If $k_{0.10}$ or $k_{0.90}$ falls outside the quoted strike range for any event, use $\alpha = 0.25$ for all events.
- Does not depend on the tail extrapolation; ignores the tails by construction.
- For a normal density, $\text{IQR}_{0.10} = 2.563\, s$.

### 3.3 Straddle implied move [call]

$$\text{IM}_i = \frac{C_i(F_i) + P_i(F_i)}{D_i\, F_i} = \mathbb E^Q\!\left[\,\left|\frac{S_T}{F} - 1\right|\,\right]$$

- Model-free expected absolute move under $Q$, directly comparable with $|R_i|$. The brief asks to compare it with the realised move [brief].
- Computed from **market mid quotes**, not from SVI [B]: straddle mid prices at the two strikes bracketing $F_i$, linearly interpolated in strike.
- For a normal density, $\text{IM} \approx \sqrt{2/\pi}\, s \approx 0.8\, s$.

### 3.4 Tail mass [brief]

$$\text{TL}_i = F_Q^{(i)}\big(\ln(1-c_i)\big),\qquad \text{TR}_i = 1 - F_Q^{(i)}\big(\ln(1+c_i)\big)$$

- **Relative threshold** $c_i = 2\,\text{IM}_i$ [B]: measures the shape of the tails independently of the overall width. A fixed threshold would be strongly correlated with $s_i$.
- For a lognormal (Black–Scholes) density, $c_i \approx 1.6\, s_i$ and $\text{TL}$, $\text{TR}$ are approximately constant (about 5.5% each, whatever $s_i$), so variation across events is information beyond width.
- $\ln(1 \pm c_i)$ should lie inside the quoted strike range; events where it does not are flagged.

### 3.5 Historical-volatility benchmark [B]

$$\text{HV}_i = \hat\sigma^{(20)}_i\,\sqrt{h_i}$$

with $\hat\sigma^{(20)}_i$ the standard deviation of daily SPX log returns over the 20 trading days before $t_i$, and $h_i$ the horizon in trading days (1 for most events).

Rationale: in volatile periods densities are wider **and** moves are larger. That correlation is a genuine prediction, but an easy one: past volatility alone captures it. HV is the naive benchmark: it is the control in P3 (Section 4.1). The encompassing regression with historical volatility appears in [lit] (Section 5.3); the 20-day window and its use around events are our extension.

### 3.6 Summary

| Measure | Depends on tail extrapolation | Role |
|---|---|---|
| $\text{IM}$ | no | main width, direct comparison with $\lvert R\rvert$ |
| $s$ | yes | width using the whole density |
| $\text{IQR}_{0.10}$ | no (if inside quoted strikes) | robustness |
| $\text{TL}$, $\text{TR}$ | yes, near the quoted edge | tail shape |
| $\text{HV}$ | n/a (not from options) | naive benchmark, control in P3 |

---

## 4. H1: do pre-event width and tail mass predict the size of the move?

### 4.1 Primary analyses

All three regressions predict the same variable, $|R_i|$, and each adds one piece of information to the implied move. For each one, report the coefficients with bootstrap 95% intervals (Section 6) and the out-of-sample $R^2$ computed leave-one-event-out [brief]: for each $i$, fit on the other events, predict event $i$, and compare with the mean of the other events,

$$R^2_{OOS} = 1 - \frac{\sum_i \big(|R_i| - \widehat{|R_i|}_{(-i)}\big)^2}{\sum_i \big(|R_i| - \overline{|R|}_{(-i)}\big)^2}.$$

$R^2_{OOS} > 0$ means the model beats the historical mean. Since $|R_i|$ is a single draw, even a perfectly calibrated density gives a low $R^2$: with normal densities whose width has a 40% coefficient of variation across events, the maximum is about 0.2. A low $R^2$ is not by itself evidence against H1.

**P1. Implied move only** [brief] [lit] [B]

$$|R_i| = \alpha + \beta\, \text{IM}_i + \varepsilon_i$$

- *Question:* does the density predict the size of the move, with everything it contains, regime included?
- *Reference values:* if $Q$ were also the true distribution, $\mathbb E\big[|R_i| \mid \text{IM}_i\big] = \text{IM}_i$, so $\alpha = 0$ and $\beta = 1$.
- Also report the mean ratio $\bar\rho = \frac1n \sum_i |R_i|/\text{IM}_i$ with its interval.

**P2. Implied move and tail mass** [brief] [B]

$$|R_i| = \alpha + \beta\, \text{IM}_i + \gamma_L\, \text{TL}_i + \gamma_R\, \text{TR}_i + \varepsilon_i$$

- *Question:* given the width, does the shape of the tails add information about the size of the move?
- Read $\gamma_L$, $\gamma_R$ and the bootstrap interval of $R^2_{OOS}(\text{P2}) - R^2_{OOS}(\text{P1})$.

**P3. Implied move and historical volatility** [lit] [B]

$$|R_i| = \alpha + \beta\, \text{IM}_i + \delta\, \text{HV}_i + \varepsilon_i$$

- *Question:* do options know something that cannot already be read from past prices?
- *Rationale:* the correlation due to the volatility regime is genuine, not spurious. If densities are wider in turbulent periods and moves are then larger, the density predicted correctly. But that part of the prediction is easy: recent realised volatility alone gives it. Before a release, options can also price a premium specific to that event, which past volatility cannot know. P3 separates the prediction anyone could have made from the part that comes specifically from options.
- *Reading:* if $\beta$ stays positive with $\text{HV}_i$ in the regression, options add information beyond past prices. If $\delta$ is indistinguishable from 0, options already contain the information in past volatility (the "encompassing" result in [lit]).
- $\text{IM}_i$ and $\text{HV}_i$ are correlated, so intervals will be wider than in P1.

At most 3 regressors per model, given $n \approx 150$.

### 4.2 Secondary analyses [B]

1. **Other width measures:** P1 with $s_i$ and $\text{IQR}_{0.10,i}$ in place of $\text{IM}_i$, using $|X_i|$ (reference slope for $s$ under normality: $\sqrt{2/\pi} \approx 0.8$).
2. **Outliers:** Spearman rank correlation between $\text{IM}_i$ and $|R_i|$. The leave-one-out fits of Section 4.1 also give $\hat\beta_{(-i)}$, the P1 slope estimated without event $i$: report its range to identify influential events (no extra computation).
3. **Event type:** P1 estimated separately for FOMC, CPI and payrolls (wide intervals expected).

---

## 5. H2: are realised moves calibrated to the density?

### 5.1 PIT [brief]

$$u_i = F_Q^{(i)}(X_i)$$

If $X_i$ had distribution $F_Q^{(i)}$, then $u_i \sim U(0,1)$, since $P\big(F(X) \le u\big) = P\big(X \le F^{-1}(u)\big) = u$. The PIT puts events with different densities on a common scale.

$$H_0:\ u_1,\dots,u_n \ \text{are independent and uniform on } [0,1].$$

**Numerical edge case [B]:** the pipeline CDF is defined for every $k$, not only on a grid (e.g. analytically from SVI, $F_Q(k) = 1 + e^{-k}c'(k)$ with $c(k) = C/(DF)$), so $u_i$ is strictly in $(0,1)$; a CDF evaluated only on a finite grid would return exactly 0 or 1 for moves outside it, and $\Phi^{-1}(u_i)$ would be infinite. As a safeguard against extreme values dominating the Berkowitz test, $u_i$ is clipped to $[10^{-4},\, 1 - 10^{-4}]$ (i.e. $|z_i| \le 3.72$) and clipped events are flagged. Right-tail values are computed from the survival function to avoid losing precision near 1 (Section 7).

### 5.2 Primary analyses [B]

The brief asks for PIT histograms and a simple uniformity test [brief]. The specific tests below are proposed from the literature. Each answers a different question: KS whether there is any miscalibration, Berkowitz in which direction, the tail counts where.

**Q1. PIT histogram by deciles.** Each decile count is $\text{Bin}(n, 0.1)$ under $H_0$; plot the 95% band $n/10 \pm 1.96\sqrt{n \cdot 0.09}$, i.e. about $15 \pm 7$ for $n = 150$. Reading:

| Shape | Interpretation |
|---|---|
| flat | calibrated |
| hump in the centre | density too wide |
| U-shaped | density too narrow |
| few $u_i$ near 0 | left tail overpriced |
| tilted | centre shifted |

**Q2. Kolmogorov–Smirnov test** (the simple uniformity test asked by the brief). $D_n = \sup_u |\hat G_n(u) - u|$, with $\hat G_n$ the empirical CDF of the $u_i$; 5% critical value $\approx 1.36/\sqrt n \approx 0.11$ for $n = 150$. Detects any departure from uniformity and is not affected by extreme $u_i$, but is mostly sensitive in the centre.

**Q3. Berkowitz test.** $z_i = \Phi^{-1}(u_i)$, $N(0,1)$ under $H_0$. Estimate $\hat\mu_z$, $\hat\sigma_z^2$ and test $(\mu, \sigma^2) = (0, 1)$ with $LR = -2\big[\ell(0,1) - \ell(\hat\mu_z, \hat\sigma_z^2)\big] \sim \chi^2(2)$. Gives the direction: $\hat\sigma_z < 1$ means too wide, $\hat\mu_z \ne 0$ means shifted. The AR(1) part of the original test is dropped (events are not equally spaced).
Caveats: a few extreme events can drive the result, it weights the extrapolated tails most, and it only checks mean and variance.

**Q4. Tail counts** (where the miscalibration sits, as the brief asks). Number of $u_i < 0.05$ and of $u_i > 0.95$, each compared with $\text{Bin}(n, 0.05)$ by an exact binomial test (expected 7.5, central 95% range 3–13 for $n = 150$).

### 5.3 Secondary analyses [B]

1. **Calibration at fixed thresholds (reliability diagram).** The first-call example ("10% of a 2% up movement") made systematic.
   - Two return thresholds fixed in advance: an up move $R_i > +1\%$ and a down move $R_i < -1\%$. With a typical implied move of about 1%, the predicted probabilities are neither tiny nor close to 1.
   - For each event, the predicted probability from its own density, e.g. $p_i = Q(R_i > 1\%) = \texttt{sf}(\ln 1.01)$, and the outcome $y_i = 1$ if the move happened, 0 otherwise.
   - *Main number:* for each threshold, the mean predicted probability $\bar p$ against the observed frequency $\bar y$ over all events, with a binomial 95% interval for $\bar y$. Example of reading: "the density gave on average 9% to a fall below −1%; it happened in 5% of events (interval 2–10%)". The two thresholds say on which side the miscalibration sits.
   - *Figure:* events grouped into 3 bins of predicted probability; for each bin, mean predicted probability (horizontal axis) against observed frequency (vertical axis), with binomial error bars. Points below the diagonal mean the market assigned more probability than realised. Each bin holds only a few dozen events (standard error about $\sqrt{p(1-p)/n}$, e.g. ±5.5 points for $p = 10\%$, $n = 30$), so the figure is descriptive.
   - Complementary to Q4: the tail counts use thresholds relative to each density ($u_i < 0.05$), this uses fixed return thresholds with a direct economic meaning.

2. **Naive $P$ benchmark.** Is $Q$ calibrated better or worse than a density anyone could build from past prices alone?
   - For each event, a normal density centred at 0 with standard deviation $\text{HV}_i$ (Section 3.5, the same quantity used in P3). It knows nothing about the release.
   - Its PIT is $u_i^{HV} = \Phi(X_i / \text{HV}_i)$, and Q1–Q4 are applied to it as to $Q$.
   - Expected: errors in opposite directions. $Q$ too wide (hump, $\hat\sigma_z < 1$) because of the risk premium; the naive density too narrow (U shape, $\hat\sigma_z > 1$) because on release days prices move more than usual. Part of a U shape also comes from the thin tails of the normal, which understates SPX tails on any day, so it is not only due to ignoring the release.
   - Turns "$Q$ is too wide" into a comparison: by how much $Q$ is too wide against how much the naive model is too narrow. Almost no extra cost, since $\text{HV}_i$ is already needed for P3.

3. **By event type.** Q1–Q4 repeated separately for FOMC, CPI and payrolls. With 40–60 events per type the intervals are wide, so this is descriptive.

### 5.4 Interpretation: $Q \ne P$ [lit]

The density is risk-neutral: its weights are normalised state prices, not forecasts. Options carry a variance risk premium and out-of-the-money puts are priced as crash insurance, so relative to realised outcomes we expect $Q$ to be too wide on average and its left tail overpriced [lit, Section 6]. A rejection of $H_0$ in that direction is the expected finding, not a pipeline failure. Options alone cannot separate "the market forecasts badly" from "the market forecasts well and charges a premium".

---

## 6. Inference and reporting

- **Bootstrap** [brief]: resample events with replacement, $B = 10\,000$, percentile 95% intervals. Inside leave-one-out, all copies of the left-out event are removed [B]. Robustness: block bootstrap by calendar quarter, since volatility regimes cluster [B].
- **Effect sizes with intervals, not a hunt for $p < 0.05$** [brief]. Every test performed is listed in the report [brief].
- **Power** [brief]: with $n \approx 150$ only large miscalibrations are detectable, so "not rejected" does not mean "calibrated". Power will be estimated by simulation once the evaluation code exists; details to be defined.

---

## 7. Requirements from the pipeline (to agree with C) [B]

Per snapshot, a result object containing:

- `as_of` (timezone-aware), `expiry`, `T`, `F`, `D`;
- `k_grid` and `q` on the $k = \ln(K/F)$ axis;
- `cdf(k)` and `sf(k)` $= 1 - F_Q(k)$: callables valid at any $k$ (not only on the grid), returning values strictly in $(0,1)$;
- `atm_quotes`: call and put mid (and bid/ask) at the strikes bracketing $F$;
- `k_min_quoted`, `k_max_quoted`: quoted range actually used in the fit;
- quality flags: mass inside the grid, butterfly check $g(k) \ge 0$, SVI fit error.

The pipeline makes no assumption about events: it takes a chain, a date and an expiry; the link to events is made downstream, using the event calendar.

---

## 8. Hypotheses (first draft)

A first, preliminary draft of the expected results, written at this early stage. The brief asks for hypotheses to be written down before looking at results [brief]: this draft will be refined with the team and frozen before any real data is used. Expectations come from [lit] and from $Q \ne P$.

**H1**
- H1a: $\beta > 0$ in P1.
- H1b: $\beta < 1$ and $\bar\rho < 1$ (options price more movement than is realised) [lit: $\beta$ typically 0.7–0.9 for implied against realised volatility over the option's life; our horizon and setting differ].
- H1c: in P3, $\beta$ stays positive and $\delta \approx 0$ (options encompass past volatility) [lit].
- H1d: in P2, no directional expectation on the tail coefficients.

**H2**
- H2a: uniformity of $u_i$ is rejected.
- H2b: $\hat\sigma_z < 1$ (hump-shaped histogram, density too wide).
- H2c: fewer than expected $u_i < 0.05$ (left tail overpriced).
- H2d: no shift in $\hat\mu_z$ from the drift, which is negligible over one day; any shift should come from the tail asymmetry in H2c.
