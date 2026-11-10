# Fixes report: audit findings F1 to F24

**Label for every number in this report: DEVELOPMENT work on open data (2018-05-01 to 2026-10-29).** No number here replaces the pre-registered Stage 5 result ("Inconclusive", `b` = .281). I did not read raw quotes before 2018-05-01. I did not run `run_tests_once.py`. I did not edit any existing file. All new files are in `fixes/`, plus the new root `README.md`.

Note on IDs: the task text calls `contract_multiplier` "F15" and the saved hash "the process item". In the audit, `contract_multiplier` is F16 and the hash item is F15. This report uses the audit IDs.

## 0. Baseline reproduction (gate for every later step)

- **Series.** The frozen `build_series.series_tables` ran unchanged on the stored snapshot (`f01_baseline.py`, `f01_baseline.out`). It gives 1,846 valid `ATM30` days. The maximum difference to `data/index_series.parquet` is 0.0. Presence mismatches: 0.
- **Engine check.** The variant engine with no option equals the stored series for `atm30`, `atm30_floor7`, `atm30_usable`, `tier`, `near_iv`, and `far_iv` (`f13_checks.out`, part 1).
- **Regression.** `b` = .622 on 1,806 origins. Newey-West(21) t = 4.13. The bootstrap intervals are .337 to .916 (21-session blocks) and .309 to .946 (63-session blocks). All match the stored values.
- **Result.** The baseline reproduces. Every later item started from this engine.

How to rerun: `python f01_baseline.py` (about 2.5 minutes).

## 1. Framing

| ID | Status | Files |
|---|---|---|
| F1 | Fixed in new text (README) and listed in `ERRATA.md`. The papers are not edited | `../README.md`, `ERRATA.md` |
| F17 | Fixed in new text | `../README.md` |
| F23 | Fixed in the README list. The references are from memory and are unverified | `../README.md`, `ERRATA.md` |
| F21 | Documented only | `ERRATA.md` |

- **F1.** The README says that `ATM30` is a Black at-the-money implied volatility interpolated to 30 days. It is not the CBOE strip formula. It includes the audit table that shows why the literal CBOE calculation fails before 2024. The audit script `audit/a02_series_and_cboe.py` produced these numbers. I did not rerun it. I did not add a literal CBOE-style series for 2024 onward. That part of the F1 fix is **not done**.
- **F17.** The README lists the data in `databento_ggal_20261031/`, which files the study uses, and the pipeline order.
- **F23.** The README lists the missing references. Nobody has checked them against the sources.
- **F21.** The corrected wording is in `ERRATA.md`.

## 2. Quote-quality controls and strict snapshot (F3, F4, F7, F8, F9)

Files: `f02_strict_snapshot.py`, `f03_variants.py`, `f04_fit_variants.py`, `f13_checks.py`, outputs `f02_*`, `f04_variants.out`, `f04_variants.csv`, `f04_days_by_year.csv`, `f04_days_removed_by_year.csv`, `f13_checks.out`. Series are in `data/series_*.parquet`.

**Rules (each chosen once, before any `b` was computed for the variant):**
- **Strict snapshot (F7).** The last row at or before 15:45 sets both bid and ask. A null bid stays null. I re-read the raw quotes on the 432 sessions where any row has a null bid. On every other session no row has a null bid, so the strict rule equals the stored rule there. On the 432 sessions, no last row has a null ask, and no ask differs.
- **Spread filter (F3).** Keep a strike only if the relative spread of the call-put pair is at most .50. This is the study's own pair measure, (call width + put width) / (call mid + put mid). Rationale: a pair at .50 has a bid-ask band of about plus or minus 25% of the price, and the audit shows that 25% of days are above that level. Sensitivity: .25 and 1.00.
- **Tier 1 only (F4).** A term with one strike (Tier 2) gets no IV.
- **7-day floor (F9).** The near term must have 7 days or more. This is the frozen `atm30_floor7` rule.
- **Not done: a real staleness rule (F8).** It needs the time of the last quote change, which the data does not give before 2025-03. F8 is documented only.

**Results (primary regression, the study's own estimator and bootstrap):**

| Variant | Valid days | Origins | `b` | NW t | 95% bootstrap, 21 / 63 blocks | `b` of the stored series on the same origins |
|---|---|---|---|---|---|---|
| Stored baseline | 1,846 | 1,806 | .622 | 4.13 | .337 to .916 / .309 to .946 | .622 |
| F9, near term at least 7 days | 1,597 | 1,564 | .650 | 4.22 | .368 to .965 / .334 to 1.000 | .650 |
| F7, strict last row | 1,837 | 1,797 | .627 | 4.14 | .340 to .924 / .313 to .968 | .627 |
| F3, spread at most .50 | 1,688 | 1,650 | .668 | 4.10 | .355 to 1.017 / .331 to 1.034 | .643 |
| F4, Tier 1 only | 1,285 | 1,245 | .703 | 3.67 | .361 to 1.080 / .361 to 1.106 | .703 |
| **Combined: strict + spread .50 + Tier 1** | 1,037 | 1,003 | .835 | 3.71 | .432 to 1.296 / .414 to 1.316 | .829 |
| **Combined + 7-day floor (all four)** | 966 | 936 | .846 | 3.66 | .440 to 1.324 / .437 to 1.346 | .840 |
| Sensitivity: spread .25 | 1,119 | 1,090 | .774 | 3.41 | .366 to 1.252 / .362 to 1.297 | .757 |
| Sensitivity: spread 1.00 | 1,828 | 1,789 | .630 | 4.13 | .346 to .931 / .309 to .966 | .629 |
| Sensitivity: all four with spread .25 | 728 | 707 | .808 | 2.73 | .312 to 1.478 / .307 to 1.533 | .811 |
| Sensitivity: all four with spread 1.00 | 1,137 | 1,104 | .720 | 3.62 | .385 to 1.139 / .367 to 1.154 | .717 |

**How to read this (the result weakens the claim "cleaning improves the estimate"):**
- **The level of `ATM30` barely moves.** On the days that stay valid, the mean log change against the stored series is .000 to .002. The mean absolute change is .000 (strict, Tier 1, floor), .007 (spread .50), and .002 (all four).
- **The filters remove days, not bias.** The last column shows that the stored series gives almost the same higher `b` (.84) on the surviving origins. So the rise of `b` from .622 to .846 is a sample-selection effect, not a measurement improvement. I do not claim that the fixes make `b` larger.
- **The surviving sample is thin in the middle of the period.** The all-four series has 11 valid days in 2022, 51 in 2021, and 106 in 2020. It has 124 to 184 days in each of 2018, 2019, 2024, 2025, and about 98 in 2026.
- **Precision falls.** The intervals widen from about .58 to about .90 in width. The tightest filter (spread .25) leaves 707 origins and a NW t of 2.7.
- **No variant reverses the sign.** Every variant has a lower bootstrap bound above zero.
- **Days removed per year** (against 1,846 stored valid days; full tables in `f04_days_removed_by_year.csv`):

| Filter | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | Total |
|---|---|---|---|---|---|---|---|---|---|---|
| Strict last row | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 4 | 4 | 9 |
| Spread at most .50 | 2 | 1 | 17 | 9 | 36 | 42 | 22 | 9 | 20 | 158 |
| Tier 1 only | 17 | 34 | 108 | 130 | 171 | 61 | 18 | 14 | 8 | 561 |
| 7-day floor | 27 | 34 | 20 | 13 | 19 | 25 | 37 | 40 | 34 | 249 |
| All four | 30 | 43 | 110 | 130 | 185 | 122 | 78 | 85 | 97 | 880 |

- **Strict rule detail (F7).** 9 days lose their value (2023-05-30, 2025-05-16, 2025-06-18, 2025-06-27, 2025-08-13, 2026-01-14, 2026-03-18, 2026-06-17, 2026-07-17). 35 days change. 6 change by more than 1%. The largest is +14.25% (2025-07-11). The audit counted 8 lost days after 2025-03. The extra day is 2023-05-30, which has null bids before the format break. My strict values agree with the audit's independent rebuild to 1.8e-5 on 385 post-break days.
- **Not measured:** the effect of the strict rule on `MF30`.

How to rerun: `f02_strict_snapshot.py` (about 10 minutes), then `f03_variants.py base strict spread25 spread50 spread100 tier1 core core25 core100` (each name takes 2 to 5 minutes), then `f04_fit_variants.py` (about 5 minutes). Use the `py4fi` Python from this folder.

## 3. American exercise and dividends (F2)

Files: `deam.py`, `f05_deam_synthetic.py`, `f05b_deam_spot_noise.py`, `f03_variants.py` (variants `deam`, `deamC`, `core_deam`), `f12_deam_summary.py`, outputs `f05*.out`, `f05_deam_synthetic.csv`, `f12_deam_summary.out`, `f03_deam_terms_*.csv`.

**Method.** When a cash dividend has an ex-date inside the term, the code inverts the out-of-the-money option at each of the two strikes next to the forward with a CRR American tree (400 steps, escrowed dividend). It takes the spot from the Nasdaq 15:45 mid (`stock_mid`). It builds the forward from the spot and the dividend, because put-call parity fails for American options with a dividend. It then uses the same strike interpolation as the frozen code. Terms with no dividend use the frozen recipe.

**Synthetic validation (passed).** The generator is a 1,000-step tree. The inversion uses 400 steps. The frozen recipe is off by 2% to 13% in 84 of 216 cases (mean 5.2%, maximum 11.7%). In those 84 cases the new recipe has a mean absolute error of 0.02% and a maximum of 0.11%. Across all 216 cases the maximum is 0.12%, and 100% are within 1%. The old-recipe table reproduces the audit (for a 2% dividend: +5.1%, +2.6%, +1.7%, +1.2% at 10, 20, 30, 45 days).
- **Limits of the validation.** The vol is flat. The spot and the dividend are known. The "wide quote" test in `f05` is symmetric around the price, so it does not test anything. Ignore its line.
- **Spot sensitivity (`f05b`).** A spot error of 0.3% moves the term IV by 0.1% to 0.8%. A spot error of 0.5% moves it by 0.1% to 1.9%.

**Real data.**
- The tree ran on 9,329 term evaluations (all dividends) on 2,072 sessions, and 2,968 (confirmed dividends only). The Nasdaq mid was available in every case.
- **Term IV, tree against frozen:** the mean is +0.5% and the median is -0.55%. The spread is wide (10th to 90th percentile: -5.8% to +7.1%). For terms of 14 to 30 days the median is -0.8%. For terms under 14 days it is -3.3% (n = 38).
- **Forward, spot-based against parity:** the median log ratio is -0.3%, with a 10th to 90th percentile range of -7.0% to +1.9%. This noise is larger than the 0.1% to 0.8% American bias in the audit. So the spot-based forward adds noise of the same size as the effect.
- **Why the average effect is small.** Most open-period dividends are small. The 2025-2026 monthly dividends are about 0.3% of the price. Only a few exceed 2%.
- **`ATM30` level.** 656 of 1,846 days change (285 with confirmed rows only). The mean log change over all days is -0.13% (-0.07% with confirmed rows). On the changed days the mean is -0.36%, with a range of -23% to +26%. By year, the largest mean change on changed days is -2.2% in 2022 (the 3.3% dividend of 2022-05-13).
- **Effect on `b`:** all dividends .621 (NW t 4.18, bootstrap .342 to .912 and .313 to .941). Confirmed dividends only: .623 (t 4.16). The stored value is .622. On the all-four series plus tree, `b` is .848 against .846 without the tree. There is no effect on `b`.
- **Confirmed against unconfirmed.** I separate the rows by the `basis` column. A row is "confirmed" if its basis is not "nasdaq_basis_unconfirmed". For the confirmed-only run, a term that holds any unconfirmed dividend keeps the frozen recipe. The results are the same within .002.
- **Not verified:** whether the ledger dividend (USD per ADS, net of withholding) is the amount that moves the option underlying. I treated the ex-date open (09:30) as the time of the drop. I used one dividend model (escrowed).

How to rerun: `f05_deam_synthetic.py` (about 5 minutes), `f05b_deam_spot_noise.py` (under 1 minute). `f03_variants.py deam deamC core_deam` takes 50 to 90 minutes each, because the tree runs on every listed expiry. Then run `f12_deam_summary.py deam deamC core_deam` and `f04_fit_variants.py`.

## 4. Better baseline (F5)

Files: `f06_bbo_grid.py`, `f07_bbo_quality.py`, `f08_rv_har.py`, `f14_rv_sanity.py`, outputs `f06_*`, `f07_bbo_quality.out`, `f08_rv_har.out`, `f08_rv_har.csv`, `f14_rv_sanity.out`. Data: `data/bbo_grid.parquet`, `data/realized_hf.parquet`.

**Data quality of the `bbo-1m` mids (checked first).**
- **Layout.** The file is update-only. A day has a median of 408 rows, 383 of them in the regular session. It also holds pre-market and after-hours rows. Pre-market quotes can be absurd (for example 0.01 / 199,999.99 on 2018-06-01).
- **Bad rows.** There are 1,825 rows with a null price and 7 crossed rows in 2,137 days. There are no zero bids.
- **Regular session.** Every grid minute from 09:30 to 16:00 has a valid quote. The median quote age is 0 minutes, and 0.3% of grid points are older than 5 minutes. The median relative spread is .16% to .22% by year. 0.1% to 1.0% of grid points have a spread above 5%.
- **Against official prices.** The 16:00 mid is within a median of 5 bp of the official close (99th percentile 38 bp). The 09:30 mid differs from the official open by a median of 90 bp, because the open is an auction. So I use the official open and close for the day ends.
- **Jumps.** 5-minute returns above 5% (61 cases) mostly sit at the open (85% in the first 10 minutes) and often touch a wide quote (66%).
- **Noise.** The lag-1 autocorrelation of 5-minute returns is +.010. Bid-ask bounce is not visible. The signature plot is flat: the mean daily variance at the 5-minute step is 1.005 times the 30-minute value.
- **Venue.** The quote is Nasdaq-only (F19). In the regular session it fits the official close well. It is not the consolidated quote.

**Construction.** Daily RV is the sum of squared pieces that partition the close-to-close total return: (1) previous close to official open, with cash (the study's own overnight return); (2) official open to the 09:35 mid; (3) 5-minute mid returns from 09:35 to 15:55; (4) the 15:55 mid to the official close. On the 17 early-close days the grid ends at 13:00. The HAR inputs use the study's formulas (252 times the mean over 1, 5, and 22 sessions, floor 1e-6). The total RV is 0.97 times the total squared close-to-close return. The overnight piece is 33% of it. Log RV is far more persistent than the squared return (lag-1 autocorrelation .54 against .08).

**Results (stored `ATM30`, 1,806 origins, same rows in every line):**

| Target | Baseline | R² baseline | R² with `ATM30` | `b` | NW t | Bootstrap 21 / 63 blocks |
|---|---|---|---|---|---|---|
| log `RV30` (study target) | HAR old (squared daily returns) | .097 | .177 | .622 | 4.13 | .337 to .916 / .309 to .946 |
| log `RV30` (study target) | HAR new (`bbo-1m`) | .108 | .178 | .608 | 3.35 | .283 to .970 / .253 to .996 |
| log `RV30`, high-frequency version | HAR old | .160 | .302 | .696 | 5.78 | .482 to .939 / .439 to .978 |
| log `RV30`, high-frequency version | HAR new | .193 | .305 | .653 | 4.41 | .385 to .958 / .343 to .988 |

- **Reading.** The new baseline raises R² from .097 to .108 on the study target, and from .160 to .193 on the high-frequency target. The gain is small. `b` falls by 2% to 6% and stays clearly positive. The t-statistic falls from 4.13 to 3.35. The intervals widen. So the result survives a stronger baseline, with less strength. It does not vanish. The old HAR coefficients (.010, .127, .181) shift toward the daily term in the new HAR (.124, .208, .079).
- **Sensitivity.** Carrying over wide-quote mids (spread above 5%) changes `b` by .002. It drops 20 origins (the cause was not checked).
- **Not done:** the improved baseline in the out-of-sample race (QLIKE, Clark-West), and the Mincer-Zarnowitz test on the high-frequency target.

How to rerun: `f06_bbo_grid.py` (about 5 minutes), `f07_bbo_quality.py`, `f08_rv_har.py` (about 3 minutes; needs `series_base` and `series_core`), `f14_rv_sanity.py`.

## 5. Inference (F13, F14)

Files: `f09_mz_coverage.py`, outputs `f09_mz_coverage.out`, `f09_mincer_zarnowitz.csv`, `f09_coverage.csv`.

**Mincer-Zarnowitz (HAC, 21 lags; joint Wald test of a = 0 and b = 1), stored series, 1,806 origins:**

| Scale | a | b | R² | Joint p |
|---|---|---|---|---|
| Logs | -.541 | .698 | .163 | < .0001 |
| Variance levels | .181 | .686 | .031 | .064 |
| Volatility levels | .163 | .683 | .100 | .027 |

These match the audit rerun. The all-four series (936 origins) gives joint p of .10 (logs), .31 (variance), and .48 (volatility), but with a much smaller sample. A rejection is expected in part because of the variance risk premium. The test does not support the claim of information beyond HAR.

**Measured coverage of the nominal 95% intervals.** A Monte Carlo with 400 draws and fixed regressors. The errors are Gaussian with the empirical autocovariance of the residuals (Bartlett taper, lag 90). The simulation error of each rate is about 1.6 points.

| Series | Interval | Measured coverage |
|---|---|---|
| Stored | Bootstrap, 21-session blocks | 87.0% |
| Stored | Bootstrap, 63-session blocks | 89.3% |
| Stored | b +- 1.96 Newey-West(21) | 87.8% |
| All four | Bootstrap, 21-session blocks | 89.3% |
| All four | Bootstrap, 63-session blocks | 91.3% |
| All four | b +- 1.96 Newey-West(21) | 89.8% |

The SD of `b` across draws is 1.1 to 1.3 times the width-implied standard error. This agrees with the study's own simulation (80% to 91%). **Limit:** the regressors are fixed in my simulation. Real regressors are random and persistent, so real coverage can differ. I did not rerun the study's simulation.

## 6. Smaller items

| ID | Status | Note |
|---|---|---|
| F6 | Reported only | `f15_subsamples.py`, `f15_subsamples.csv`. The stored series gives `b` of .526 (2018-2023), 1.185 (2024-2025), and .423 (2026, NW t 1.0). The all-four series gives .530 (t 2.0), 1.362, and 1.405 (t 2.6). The 2025-03 split is .525 and 1.190 (stored) against .646 and 1.619 (all four). So the fixes do not remove the pattern. The late period still carries the large `b`, and the early period is weaker. Fragility is a property of the data |
| F9 | Fixed in new code | The 7-day series is in section 2. It lifts `b` to .650. 249 days drop |
| F10 | Documented only | 21 valid days have a far term above 65 days, and 20 are above 90 (`f13_checks.out`). I did not add a flag column |
| F11 | Documented only | `ERRATA.md` |
| F12 | Documented only | `ERRATA.md` (audit numbers; not recomputed) |
| F15 (hash) | Fixed in new code | `f10_check_manifest.py`, `f10_check_manifest.out`. The manifest hash is 9214a220...abc and matches `HANDOFF.md`. `freeze.differences()` is empty. **Open:** I cannot see your saved copy. Run `python f10_check_manifest.py --saved <your hash>` |
| F16 (multiplier) | Check script written | `f11_check_multiplier.py`, `f11_check_multiplier.out`. The script asserts that any defined multiplier equals 100. On 12 sample days the field is undefined (INT_MAX) and `unit_of_measure_qty` is blank. The result: the 100-share deliverable is assumed, not verified. No other root exists in any session (`other_roots` is 0 on 2,137 sessions). I did not reopen `GGAL1` |
| F18, F19, F20 | Documented only | `ERRATA.md` |
| F22 | Documented only | The fix needs an edit to the frozen builders |
| F24 | Documented only | `ERRATA.md` |
| F8 | Documented only | `ERRATA.md`. See section 2 |

## 7. Not done

- A literal CBOE-style series for 2024 onward (part of F1).
- A real staleness rule (F8) and a half-day snapshot fix (F20).
- Calibrated intervals in the papers (F13). The measured coverage is reported, but no widening factor is applied.
- Asserts in the paper builders (F22), and any edit to the papers or PDFs.
- The Clark-West and QLIKE races with the new baseline and series.
- The forward test (fix 8 of the audit). A description follows.

**Forward test, description only.** Freeze the rules after the choices for the spread filter, Tier 1, the strict snapshot, the American tree, and the `bbo-1m` HAR. Write the thresholds and the primary regression in a new protocol file. Hash it. Collect Databento data after 2026-10-29. Run the regression once on a pre-stated number of origins, and use the study's bootstrap with a stated block length. Power will be low for the first year. This is the only clean confirmation, because the 2018-2026 rules came after contact with the data.

## 8. What is unverified

- The strict snapshot was re-read only on the 432 sessions with a null bid in some row. On the other sessions I rely on the argument that no row has a null bid. A session with a null ask and no null bid would not be caught.
- The dividend amounts and their basis (19 of 32 open rows are unconfirmed).
- The real-data behavior of the tree beyond the synthetic validation. The spot-based forward is noisy.
- The coverage simulation covers fixed regressors only.
- The references in `README.md`. They are from memory.
- The 247 unit tests. I did not run them.
- The four PDFs. I did not read them.

## 9. Final check

`freeze.differences()` must return `[]`. The result of the last run is in `f10_check_manifest.out` and in the final reply.
