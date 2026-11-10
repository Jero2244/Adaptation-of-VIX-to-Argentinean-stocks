# GGAL Implied Move Calibration Plan

Nov 5, 2026 · @J

## Question and scope

The question is whether ATM30, read as a 30-day risk-neutral distribution, gives the right probabilities for GGAL ADR moves. The main study asked whether implied volatility carries information. This plan asks whether its level and shape are calibrated.

- **Primary:** the share of 30-day moves inside the ±1σ and ±2σ implied bands, against 68.3% and 95.4%.
- **Secondary:** full calibration through a PIT histogram, separate down-tail and up-tail breaches, and a reliability check of implied move probabilities.
- **Comparison:** the same checks for a band built from HAR. The point is to see which source is better calibrated, not only whether options miss.
- **Out of scope:** a skew-based or model-free distribution as the primary series, because deep out-of-the-money quotes are rare before 2024. Trading rules are also out of scope.

## Status of the evidence

Every result in this plan is exploratory. The only exception would be a frozen test on data from after 2026-10-29.

- **Open data, 2018-05 to 2026-10:** this period shaped the ATM30 method, so any result on it is development evidence.
- **2016-01 to 2018-04:** this period has been used once, by the frozen test, and is development data from now on. Report it as a separate, calmer sub-period, not as confirmation.
- **New data:** only data after 2026-10-29 can confirm a result. See *Optional frozen forward test*.
- **Rules first:** write the primary measures into the repo before running anything. Label any choice made after seeing results as post-result.

## Inputs

No new data is needed. Everything below already exists in the study's panels and code.

| Input | Where it comes from | Use here |
| --- | --- | --- |
| ATM30 and tier flag per session | Stage 1–2 implied volatility panel | Band width |
| Total-return closes | Official daily table (open data), Alpaca bars (2016–18) | 30-day outcome |
| adr\_cash\_events.csv | Cash rows | Dividends inside the total return |
| FRED DGS1MO, DGS3MO | Same interpolation as the study | Risk-neutral drift |
| HAR forecasts of RV30 | Stage 3 expanding-window race code | Benchmark band |
| Event list | Frozen event list | Event subsamples |

Timing gap: ATM30 is measured at 15:45 New York, while the outcome starts at the 16:00 close. The primary run uses the close, and a sensitivity check covers the gap.

## Method

Each origin's 30-day total log return is standardized by the ATM30 band, and the shares of standardized moves are compared with normal probabilities.

1. Horizon T = 30/365, the same window (t, t + 30 calendar days\] as RV30. The outcome ends at the last session inside that window.
2. Band width: s = ATM30 × √T.
3. Centre: m = rT − s²/2, the risk-neutral mean of the total log return. Dividends are inside the total return, so they need no forward adjustment.
4. Outcome: R = log of the total-return close ratio, with cash counted on ex-dates exactly as in RV30.
5. Standardized move: z = (R − m) / s.

```latex
z_t = \frac{R_{t,t+30d} - \left(r_t T - \tfrac{1}{2}\,\mathrm{ATM30}_t^2\,T\right)}{\mathrm{ATM30}_t\sqrt{T}}, \qquad T = \tfrac{30}{365}
```

| Measure | Definition | Value if calibrated |
| --- | --- | --- |
| Inner hit rate | share with \|z\| < 1 | 68.3% |
| Outer hit rate | share with \|z\| < 2 | 95.4% |
| Down-tail breach | share with z < −2 | 2.3% |
| Up-tail breach | share with z > 2 | 2.3% |
| Mean z² | average squared standardized move | 1.00 |
| Mean \|z\| | average absolute standardized move | 0.80 |
| PIT | u = Φ(z), 10 equal bins | 10% per bin |

The reliability check turns implied probabilities into forecasts. For a move of more than 10% or 20% in absolute value, compute the implied normal probability at each origin. Group origins by that probability and compare it with the observed frequency, then score with the Brier score.

Reading guide: mean z² below 1 means the bands are too wide on average. If the tails are breached more often than 2.3% at the same time, the shape is wrong, not only the level.

## Benchmarks

Options are judged against alternatives on the same rows, not only against the nominal 68.3% and 95.4%.

- **HAR band:** s comes from the expanding-window HAR forecast of RV30, with the study's refit rules and with and without the Duan factor. The centre rule is the same as for ATM30.
- **Scaled ATM30:** ATM30 × k, where k is fitted on past rows only. This separates a level bias, the variance risk premium, from a shape error.
- **Fat-tailed ATM30:** the same s with Student-t quantiles, scaled to unit variance, and degrees of freedom fitted on past rows only. This tests whether breaches come from tails rather than level.
- **Scores:** the interval score (Gneiting and Raftery, 2007) at 68% and 95%, and the CRPS of each predictive distribution. Differences use the same block bootstrap.

HAR forecasts start later, so all comparisons use the rows where every method has a value.

## Inference under overlap

Daily origins with 30-day windows overlap by about 21 sessions, so open data holds only about 102 independent months.

- **Bootstrap:** circular blocks of 21 and 63 sessions, 2,000 resamples, on the full session grid. This reuses the study's code.
- **Non-overlapping samples:** fixed steps of 22 and 23 sessions, as in the study. These samples share periods, so they are not independent of each other.
- **Precision:** with about 102 independent months, a hit rate near 68% has a standard error of about 4.6 percentage points.
- **Tails:** each 2σ tail expects only about 2 to 3 cases in 102 months. Tail results are therefore descriptive, with no verdict.
- **One primary number:** the inner and outer hit rates on all open data, with events included. Everything else is labelled secondary.

## Subsamples and robustness

Each cut below repeats the primary measures and is reported beside the main result, never in its place.

| Cut | Why it matters |
| --- | --- |
| Events in vs out | ATM30 prices the election premium at the origin, and election moves sit in the outcome |
| Before vs from 2025-03 | Quote format break |
| Tier 1 vs Tier 2 | Quote quality differs between tiers |
| 2016-01 to 2018-04 | Calmer regime, now development data |
| 0–6 vs more days to near expiry | Coverage and selection change near expiry |
| Centre at zero | Sensitivity to the drift rule |
| Start at the 15:45 stock mid | The 15:45 vs 16:00 timing gap |
| American-exercise adjustment | Black inversion biases IV, if the tree sensitivity is done |

## Stages, checks and outputs

The work runs in six stages. The method is checked on synthetic data before any real result is printed.

1. **C0, rules.** Copy this plan into the repo as CALIBRATION\_PLAN.md and commit it before running anything.
2. **C1, panel.** Join ATM30, tier, event flag, rates and total-return closes, then build the window end, R, m, s and z.
   - Unit tests: window end on non-session days, cash on ex-dates, no value on half days, no imputation.
   - Reconcile row counts with the RV30 panel.
3. **C1b, synthetic check.** Simulate prices with a known vol and run the full pipeline on them. Hit rates must match 68.3% and 95.4% within simulation error. A one-session shift in the outcome must be caught by a test.
4. **C2, primary.** Compute hit rates, tail breaches, mean z², mean |z|, the PIT and bootstrap intervals.
5. **C3, benchmarks and subsamples.** Run HAR, scaled ATM30 and fat-tailed ATM30 on common rows, then each cut.
6. **C4, figures and write-up.** Produce a PIT histogram, a reliability diagram, a rolling 12-month hit rate with the nominal lines, and z over time with ±1 and ±2 lines. Then add a report section and run one adversarial review.

Outputs: reports/calib\_results.json, reports/calib\_descriptive.md and a figures folder. All of them stay local under the Databento license.

## Optional frozen forward test

Only data after 2026-10-29 can confirm a calibration result, and it would take years to be precise.

- **Freeze:** the primary measure, the verdict rule and the bootstrap, all under a SHA-256 manifest as in the main study.
- **Draft verdict rule:** the inner hit rate is miscalibrated if its interval excludes 68.3% under both block sizes. The owner sets the final wording.
- **Power:** data arrives at about one independent month per month. After 24 months the standard error is about 9.5 percentage points, so only large miscalibration would show.
- **Proposal:** freeze the rules now, take a descriptive look at 12 months with no verdict, and run the verdict at a horizon the owner fixes in advance.

## Risks and open decisions

The biggest interpretive risk: a miss under real-world probabilities is not automatically a market error.

- **Risk-neutral vs real-world probabilities:** implied bands include the variance risk premium. Bands that are too wide may simply be the price of insurance, and the write-up should say so.
- **Overlap and power:** with about 102 independent months, tail breaches and most subsample differences stay descriptive.
- **Regime mix:** open data mixes calm years, crises and the 2025-03 break, so one pooled hit rate can hide offsetting errors.
- **Licensed data:** results and figures stay local.

Decisions for the owner before C0:

- [ ] Centre rule: risk-neutral drift (proposed) or zero.
- [ ] Start price: 16:00 close (proposed) or the 15:45 stock mid.
- [ ] Tier 2 days in the primary sample: yes (proposed) or Tier 1 only.
- [ ] Move thresholds for the reliability check: 10% and 20% (proposed) or others.
- [ ] Whether to freeze a forward test, and at what horizon.
