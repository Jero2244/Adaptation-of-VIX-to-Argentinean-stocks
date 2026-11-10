# GGAL implied move calibration: descriptive results

**Status:** Exploratory. Open data and 2016-01 to 2018-04 are development data. No verdict. Results stay local under the Databento license. The rules are in `CALIBRATION_PLAN.md`. `reports/calib_results.json` holds all numbers. The manifest was written at 2026-11-05T15:03:51.363726+00:00, before any calibration result. Changed since the freeze, at the last run: none. After that run, the plan text changed once, to record the owner's horizon (`reports/calib_horizon.json`).

## Main reading

On open data, pooled coverage of the ATM30 band is near nominal, but this average hides offsetting errors. The inner hit rate is 69.6% against 68.3%, and the outer hit rate is 93.8% against 95.4%. Both intervals include the nominal value under both block sizes. So the pooled result does not show that the move probabilities are right at each origin.

- **The error depends on the level of ATM30 (post-result).** The inner rate is 50.3% in the lowest ATM30 quintile (39.3 to 62.0%), and 79.7% and 74.2% in the top two. The lowest minus the highest is -24.0 points (-40.9 to -6.4). The lowest quintile has 0 rows in the 2019 PASO windows, so that event does not explain this result. The cut points use hindsight.
- **The error also changes with time.** The yearly inner rate runs from 55.7% to 80.1% (post-result).
- **This does not prove calibration, even when pooled.** The inner interval is about 11 points wide, and the method was developed on this same period.
- **The "95%" intervals are too narrow.** In the frozen simulation, they hold the true inner rate in about 86% to 92% of runs at this sample size. The review's own simulation gives about 89% to 92% for the outer rate and 84% to 91% for mean z squared. It rests on one assumed jump model.
- **Large moves carry the excess.** Mean z squared is 1.33, with an interval of 0.92 to 1.89. It is 1.04 on 1665 origins with no event in the window, and 4.31 on 163 origins with an event. These 163 origins cover only 9 events.
- **The centre shows no level error (post-result).** Median absolute z is 0.986 times its normal value. So the excess in mean z squared comes from the tails, and not from a band that is too narrow everywhere.
- **One event has a large effect (post-result).** Without the 2019 PASO windows, mean z squared is 1.10 and the outer hit rate is 94.8%.
- **No score difference is shown for two benchmarks.** On 1599 common rows, intervals include zero for HAR with no factor and fat-tailed ATM30. This does not show that they are equal, and their coverage differs from ATM30. HAR with the Duan factor and scaled ATM30 have wider bands and worse inner interval scores.
- **No gain over a past base rate is shown (post-result).** At the 10% threshold, ATM30 has a Brier score of 0.2517, and a past base rate has 0.2511. At the 20% threshold, the scores are 0.1826 and 0.1853. Both differences have intervals that include zero, so a modest gain is not excluded.

**Caution:** A miss under real-world probabilities is not automatically a market error. Implied bands are risk-neutral and include the variance risk premium. This study cannot separate that premium from a forecast error.

## Primary measures

All open data, events included, Tier 1 and Tier 2, 1828 origins from 2018-05-01 to 2026-09-29. Intervals are 95% block bootstrap percentile intervals.

| Measure | Value | If calibrated | 21-session blocks | 63-session blocks |
|---|---|---|---|---|
| Inner hit rate | 69.6% | 68.3% | 63.8 to 75.1% | 63.9 to 75.4% |
| Outer hit rate | 93.8% | 95.4% | 90.6 to 96.8% | 90.1 to 96.8% |
| Down-tail breach | 4.0% | 2.3% | 1.4 to 7.1% | 1.1 to 7.4% |
| Up-tail breach | 2.2% | 2.3% | 0.8 to 4.0% | 0.8 to 4.0% |
| Mean z squared | 1.33 | 1.00 | 0.93 to 1.83 | 0.92 to 1.89 |
| Mean absolute z | 0.84 | 0.80 | 0.73 to 0.96 | 0.73 to 0.97 |

Mean z is 0.023, and the standard deviation of z is 1.155. Tail results are descriptive, because each 2-sigma tail expects only about 2 to 3 cases in about 102 independent months.

**Fixed-step samples.** These samples share periods, so they are not independent of each other.

| Step | Samples | Median rows | Inner: mean (range) | Outer: mean (range) | Mean z squared: mean (range) |
|---|---|---|---|---|---|
| 22 | 22 | 83.5 | 69.6% (63.1% to 74.4%) | 93.8% (89.3% to 96.5%) | 1.33 (1.08 to 1.65) |
| 23 | 23 | 79.0 | 69.6% (60.8% to 77.5%) | 93.8% (91.1% to 96.2%) | 1.33 (1.15 to 1.65) |

**PIT.** Shares per bin, from low to high: 9.7%, 8.3%, 8.4%, 8.4%, 9.7%, 11.7%, 10.7%, 11.9%, 10.6%, 10.7%. Every bin interval includes 10% under 63-session blocks. See `reports/calib_figures/pit_histogram.png`.

## Coverage by ATM30 level and by year (post-result)

The quintile cut points use the whole sample, so this is hindsight. The intervals use 63-session blocks.

| ATM30 quintile | ATM30 range | Rows | Inner | Interval | Outer | Interval | Mean z squared |
|---|---|---|---|---|---|---|---|
| 1 | 0.38 to 0.52 | 366 | 50.3% | 39.3 to 62.0% | 88.3% | 79.2 to 95.4% | 1.91 |
| 2 | 0.52 to 0.58 | 366 | 72.4% | 61.7 to 81.1% | 95.9% | 92.1 to 98.9% | 1.06 |
| 3 | 0.58 to 0.64 | 366 | 71.3% | 60.4 to 82.0% | 92.3% | 85.0 to 98.1% | 1.44 |
| 4 | 0.64 to 0.73 | 365 | 79.7% | 70.4 to 88.2% | 97.0% | 92.9 to 99.7% | 1.00 |
| 5 | 0.73 to 1.60 | 365 | 74.2% | 61.1 to 85.8% | 95.3% | 89.0 to 99.7% | 1.26 |

| Year | Rows | Inner | Outer | Mean z squared |
|---|---|---|---|---|
| 2018 | 154 | 67.5% | 87.0% | 1.72 |
| 2019 | 227 | 62.6% | 87.2% | 2.88 |
| 2020 | 216 | 68.5% | 91.7% | 1.49 |
| 2021 | 181 | 78.5% | 98.9% | 0.66 |
| 2022 | 196 | 80.1% | 95.4% | 0.94 |
| 2023 | 213 | 69.5% | 95.3% | 0.94 |
| 2024 | 230 | 55.7% | 96.1% | 1.23 |
| 2025 | 234 | 72.6% | 92.7% | 1.24 |
| 2026 | 177 | 75.1% | 100.0% | 0.68 |

## Reliability of implied move probabilities

The groups are 5 equal-count groups by implied probability, on all 1828 origins. Inside each group, the rows overlap in time.

**Moves beyond 10%.** Brier score 0.2518.

| Rows | Mean forecast | Observed |
|---|---|---|
| 366 | 47.4% | 62.8% |
| 366 | 52.5% | 50.5% |
| 366 | 56.5% | 54.4% |
| 365 | 60.5% | 51.5% |
| 365 | 69.6% | 62.7% |

**Moves beyond 20%.** Brier score 0.1902.

| Rows | Mean forecast | Observed |
|---|---|---|
| 366 | 15.0% | 27.6% |
| 366 | 20.0% | 18.9% |
| 366 | 24.6% | 23.2% |
| 365 | 29.5% | 18.4% |
| 365 | 43.0% | 35.9% |

The observed share does not rise steadily with the forecast. The lowest group has more moves than it forecasts, and the highest group has fewer. This shape stays without the 2019 PASO windows (post-result).

**Base-rate reference (post-result).** On 1599 rows. A negative difference favours ATM30. The hindsight rate uses the whole sample, so no forecaster could have it.

| Threshold | ATM30 | Past base rate | Hindsight base rate | ATM30 minus past | 63-session blocks |
|---|---|---|---|---|---|
| 10% | 0.2517 | 0.2511 | 0.2473 | +0.0006 | -0.0080 to +0.0100 |
| 20% | 0.1826 | 0.1853 | 0.1822 | -0.0028 | -0.0129 to +0.0081 |

## Benchmarks on common rows

1599 rows, from 2019-05-02 to 2026-09-29. Past-only k has a median of 1.24, and past-only degrees of freedom have a median of 5.

| Method | Inner | 63-session blocks | Outer | 63-session blocks | Down | Up | Mean z squared |
|---|---|---|---|---|---|---|---|
| ATM30 | 70.4% | 63.9 to 76.5% | 94.5% | 90.7 to 97.5% | 2.9% | 2.6% | 1.30 |
| HAR, Duan | 78.7% | 72.4 to 84.3% | 95.9% | 92.6 to 98.5% | 2.3% | 1.8% | 1.02 |
| HAR, no factor | 67.5% | 60.8 to 74.0% | 92.7% | 88.4 to 96.3% | 3.1% | 4.2% | 1.60 |
| Scaled ATM30 | 80.5% | 74.4 to 86.1% | 96.7% | 93.7 to 98.9% | 2.1% | 1.2% | 0.81 |
| Fat-tailed ATM30 | 63.2% | 56.3 to 69.6% | 94.6% | 90.8 to 97.6% | 2.9% | 2.4% | 1.30 |

**Score differences.** Each cell is the benchmark minus ATM30, with the 63-session interval. A negative value favours the benchmark.

| Method | CRPS | Interval score, 68% | Interval score, 95% | Brier, 10% | Brier, 20% |
|---|---|---|---|---|---|
| HAR, Duan | +0.0021 (-0.0005 to +0.0041) | +0.0262 (+0.0025 to +0.0468) | +0.0560 (-0.1144 to +0.1834) | +0.0086 (-0.0042 to +0.0206) | +0.0182 (+0.0021 to +0.0330) |
| HAR, no factor | -0.0009 (-0.0025 to +0.0005) | -0.0048 (-0.0206 to +0.0098) | +0.0687 (-0.0426 to +0.2277) | -0.0016 (-0.0110 to +0.0063) | +0.0001 (-0.0112 to +0.0118) |
| Scaled ATM30 | +0.0055 (+0.0023 to +0.0094) | +0.0482 (+0.0223 to +0.0790) | +0.0294 (-0.1544 to +0.1768) | +0.0119 (-0.0007 to +0.0243) | +0.0258 (+0.0093 to +0.0431) |
| Fat-tailed ATM30 | -0.0001 (-0.0009 to +0.0006) | -0.0006 (-0.0099 to +0.0094) | -0.0012 (-0.0163 to +0.0104) | +0.0010 (-0.0074 to +0.0100) | -0.0027 (-0.0084 to +0.0034) |

**Reading.**
- **Scaled ATM30:** the scale overshoots, and mean z squared falls to 0.81. The inner rate rises to 80.5%. The 2019 PASO inflates k. With those windows out of the k fit, median k is 1.07, the inner rate is 74.3%, and mean z squared is 1.03. This sensitivity uses hindsight, so it is not a benchmark. The worse scores of scaled ATM30 depend largely on this event.
- **Fat-tailed ATM30:** a unit-variance t has almost the same 2-sigma quantile as a normal: 2.05 at 5 degrees of freedom, against 2.00. So its outer hit rate is close to ATM30 by construction, and this benchmark has almost no power to test tails at 2 sigma. Its inner rate falls because a unit-variance t is narrower in the centre.
- **Fitted tails:** past-only degrees of freedom are 6 or fewer on 1528 of 1599 rows. This points to fat tails, but the fit fixes the variance at one and the rows overlap.
- **Mean z squared:** fat-tailed ATM30 uses the same s, so this value equals the ATM30 value.

## Subsamples and robustness

These cuts are secondary and sit beside the primary result. Intervals use 63-session blocks. A blank interval means that the block is more than a third of the span.

| Cut | Rows | Inner | Interval | Outer | Interval | Down | Up | Mean z squared |
|---|---|---|---|---|---|---|---|---|
| Event in window | 163 | 55.2% | 24.5 to 84.7% | 78.5% | 53.4 to 98.8% | 16.0% | 5.5% | 4.31 |
| No event in window | 1665 | 71.0% | 65.2 to 76.8% | 95.3% | 92.3 to 97.9% | 2.8% | 1.9% | 1.04 |
| Before 2025-03 | 1453 | 68.5% | 62.0 to 75.3% | 93.3% | 88.9 to 96.8% | 4.4% | 2.3% | 1.41 |
| From 2025-03 | 375 | 73.6% | 61.9 to 82.9% | 95.5% | 88.5 to 100.0% | 2.4% | 2.1% | 1.04 |
| Tier 1 | 1267 | 68.7% | 62.6 to 75.5% | 93.6% | 89.5 to 97.2% | 4.7% | 1.7% | 1.44 |
| Tier 2 | 561 | 71.5% | 62.0 to 80.2% | 94.1% | 89.7 to 97.9% | 2.5% | 3.4% | 1.10 |
| Near expiry under 7 days | 245 | 66.1% | 55.9 to 75.1% | 93.9% | 88.6 to 98.0% | 4.9% | 1.2% | 1.43 |
| Near expiry 7 days or more | 1583 | 70.1% | 64.5 to 75.8% | 93.7% | 90.0 to 96.8% | 3.9% | 2.4% | 1.32 |
| Centre at zero | 1828 | 69.7% | 64.1 to 75.3% | 93.7% | 89.8 to 96.8% | 4.2% | 2.1% | 1.33 |
| Start at the 15:45 stock mid | 1828 | 69.1% | 63.2 to 75.1% | 93.7% | 90.0 to 96.8% | 4.0% | 2.3% | 1.34 |
| Same rows as the 15:45 start, at the close | 1828 | 69.6% | 63.9 to 75.4% | 93.8% | 90.1 to 96.8% | 4.0% | 2.2% | 1.33 |
| 2016-01 to 2018-04 | 471 | 66.0% | 48.8 to 83.2% | 93.8% | 87.7 to 98.7% | 0.2% | 5.9% | 1.14 |
| 2016-01 to 2018-04, event in window | 37 | 43.2% | blank | 70.3% | blank | 0.0% | 29.7% | 2.51 |
| 2016-01 to 2018-04, no event in window | 434 | 68.0% | 50.9 to 84.1% | 95.9% | 91.0 to 99.5% | 0.2% | 3.9% | 1.02 |

- **Not run:** the American-exercise cut, because the tree sensitivity is not done.
- **2016-01 to 2018-04:** this period is development data now, and it is calmer. It has 471 origins with Alpaca closes, and it does not confirm the open-data result.
- **Timing gap:** the 15:45 start changes the inner rate from 69.6% to 69.1%.
- **Centre:** a zero centre changes the inner rate from 69.6% to 69.7%.

**By event (post-result).** Rows inside one event overlap heavily, so each event is about one independent case.

| Event | Origins | Inner | Outer | Mean z | Mean z squared | Share of all z squared |
|---|---|---|---|---|---|---|
| 2019 PASO | 20 | 0.0% | 0.0% | -4.69 | 22.28 | 18.3% |
| 2019 general | 20 | 100.0% | 100.0% | -0.12 | 0.06 | 0.1% |
| 2021 PASO | 16 | 87.5% | 100.0% | 0.08 | 0.37 | 0.2% |
| 2021 midterm | 17 | 82.4% | 100.0% | -0.90 | 0.85 | 0.6% |
| 2023 PASO | 18 | 100.0% | 100.0% | 0.09 | 0.10 | 0.1% |
| 2023 general | 20 | 100.0% | 100.0% | -0.13 | 0.15 | 0.1% |
| 2023 runoff | 20 | 10.0% | 95.0% | 1.55 | 2.54 | 2.1% |
| 2025 PBA | 15 | 0.0% | 60.0% | -2.48 | 7.26 | 4.5% |
| 2025 midterm | 17 | 11.8% | 52.9% | 1.94 | 4.11 | 2.9% |

## Method checks

- **Synthetic run:** with a known vol, all six measures match their nominal values within simulation error. See `reports/calib_synthetic_pipeline.json`.
- **Alignment:** a planted jump catches a one-session shift of the outcome, in both directions.
- **Row counts:** 1828 open rows are the 1806 primary rows plus 22 rows with no HAR inputs. The largest gap between the rebuilt RV30 window and the study's RV30 is 0.0e+00. No half day has an ATM30 value.

**How far to trust the intervals.** This simulation uses the frozen rules on simulated prices, with 300 runs and 500 resamples per block. Constant vol is the kindest case. The wandering case adds a slow error to the implied vol. Real data can differ from both. The review found that the true inner rate in the constant case is about 68.8% on this grid, not the 68.3% in the table. The effect on the coverage is small.

| Case, about 2,100 sessions | True inner rate | Cover, 21-session blocks | Cover, 63-session blocks |
|---|---|---|---|
| Constant vol | 68.3% | 90% | 92% |
| Wandering implied-vol error | 68.6% | 86% | 89% |

## Forward test

The rules are frozen, and no forward data has been read. The owner fixed the horizon at 36 months: origins from 2026-10-30 through the first origin on or after 2029-10-30. So the earliest verdict is about 2029-11-29, when the last window closes. With about 86% of sessions usable, this gives about 650 rows, so the simulated power against bands 25% too wide lies between the 504-row and the 756-row lines below.

The table shows how the verdict rule behaves in simulation at each horizon. With no error, a higher share means more false alarms. "Fires" is the share of runs in which the rule says "Miscalibrated".

**Read this table with care.**
- "Rows" means consecutive rows. Real data has a value on about 86% of sessions, so each row count takes longer on the calendar.
- The wandering case has a true inner rate near nominal, so its "Fires" column shows mostly false alarms and not power.
- The review simulated the outer rate at 252 rows, and its intervals cover only about 60%. So the 12-month look gives very unreliable outer intervals.
- The plan's standard errors of 4.6 and 9.5 points are too high against the simulated widths. Do not reuse them.

| Rows | About months | Fires, no error | Cover 21, no error | Cover 63, no error | Fires, bands 25% too wide | Fires, wandering error | Cover 63, wandering error |
|---|---|---|---|---|---|---|---|
| 252 | 12 | 13% | 85% | 81% | 35% | 20% | 74% |
| 504 | 24 | 11% | 86% | 86% | 51% | 16% | 83% |
| 756 | 36 | 12% | 86% | 87% | 63% | 15% | 85% |
| 1260 | 60 | 9% | 88% | 91% | 85% | 10% | 90% |

## Limits

- All results here are exploratory. Open data shaped the ATM30 method, and only data after 2026-10-29 can confirm a result.
- ATM30 is a single near-the-money volatility, so a normal band ignores skew by design.
- Open data mixes calm years, crises, and the 2025-03 format break. One pooled hit rate can hide offsetting errors, as the rolling figure shows.
- Selection: an origin has no z when ATM30 is blank. On 270 such rows with a complete window, moves above 20% occur in 34.8%, against 24.8% on valid rows (0.8 to 19.8 points of difference). So the pooled coverage may be overstated.
- Fixed T: the plan uses T = 30/365, but real windows average 29.35 days to the last session. With the real length, the inner rate is 68.9% and mean z squared is 1.36 (post-result).
- Black inversion on American options with dividends can bias IV. This is not measured here.
- Post-result checks came after the results. They can suggest ideas for a later test, but they confirm nothing. Several lines in the main reading rest on them, and each one carries the label.
- The rolling and reliability figures were drawn after the results.
- `reports/calib_results.json` also holds what the tables leave out: 21-session intervals of the cuts, mean absolute z of the cuts, and fixed steps of 2016-2018.

## Figures

- `reports/calib_figures/pit_histogram.png`
- `reports/calib_figures/reliability.png` (common rows)
- `reports/calib_figures/rolling_hit_rate.png`
- `reports/calib_figures/z_over_time.png`
