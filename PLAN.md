# GGAL ADR 30-day implied volatility index and forecast test

> **Changes after this plan (user, 2026-11-03).** `PROTOCOL.md` holds the current rules and overrides this page where they differ.
> - The study uses the Databento `GGAL` root as given. The `GGAL1` item is closed.
> - The lockouts of `options-valuation-model` do not apply to this study. 2026 is open data here, not a blind test.
> - The inputs stay in `databento_ggal_20261031/` and `data/`.

## Context

The goal is a VIX-style index for GGAL ADR options, and a test of how well it predicts realized volatility (RV). Two independent agents debated your plan over two rounds, with checks on the real data. This plan is the judge's result.

**Main result: your plan survives, but its headline changes.** A true model-free index cannot be measured before 2024, because the wing quotes do not exist. The main forecast series becomes a 30-day near-ATM implied volatility (IV). The model-free index stays as a descriptive series for 2024 onward.

The checks are exploratory. They used placeholder or approximate rates and simple prototypes. The study must recompute all of them.

## Judge's rulings

| Issue | Ruling | Deciding evidence |
|---|---|---|
| Model-free index as main series | **Critic wins.** Near-ATM IV is primary. | At least 5 OTM bids per wing on both expiries: 0-1% of days in 2018-2023, 13% in 2024. At least 2 per wing: 0-1% in 2021-2022. |
| Model-free index adds forecast information | **Critic wins.** Keep it out of regressions. | Block-bootstrap t at most 1.57 with ATM in the regression. About 1.0 without PASO 2019. |
| Smoothing recovers skew from thin chains | **Critic wins.** Drop skew prediction before 2024. | Full vs thinned gap correlation .77/.62, and .40/.09 on deep days. |
| "Gap is inside bid-ask noise" | **Advocate partly wins.** The yardstick was wrong, but the conclusion stays. | Gap width .008-.048, against .12-.27 for the level. It is still close to the gap in several years. |
| One jump breaks the results | **Split.** It breaks level regressions, not log regressions. | Level b .79 to .22 without 2019-08-12. Log b .58 to .57. |
| MZ a=0, b=1 as main test | **Critic wins.** Report it, but do not lead with it. | Implied variance exceeds RV in 79% of observations, so rejection says little. |
| Dividends in IV | **Critic wins.** Primary uses the parity forward, with no dividend input. | Ledger forwards sit 1.3-2.3% below parity. Only 13% of ex-window days had all dividends strictly declared. |
| American bias is small | **Split.** Small for index levels, but it needs a flag. | Index level about -1.3 to -1.9% of vol. Front-term IV -8 to -9% near ex-dates under foresight dividends. |
| Thin strikes break ATM IV | **Advocate wins.** Acceptable with a flag. | 25% gap: median error 1.6% of vol, p95 11.7%, mean +2.1%. |
| Cycle-phase pattern, 21-session vs 30-day horizon | **Advocate wins.** Neither threatens the design. | Phase effect +1.5 to +2.5%. Correlation between horizons .986. |
| Coverage: 95% or 83% | **Critic wins until proved otherwise.** Publish exact rules. | Two-sided pair on both terms: 83%. Both terms bracket the forward on 729 days only. |
| Stable forecast relation | **Critic wins.** Report by regime. | b is .55 pooled, .97 in 2024. Yearly b runs -.36 to .97. About 10 windows in 2024 cannot show stability. |

**Judge's additions, which neither agent proposed:**
- The ATM series needs no wings, and its forward comes from parity. It can therefore go back before the XNAS equity data starts. Use 2016-01 to 2018-04 as a second one-time test, with Alpaca closes for RV.
- Measure RV on the exact 30-calendar-day window of the IV, and annualize with 365/30. This meets your "no mix" rule. The 21-session version becomes a sensitivity run.

## Final design

### Series
- **`ATM30` (primary):**
  1. Take the 15:45 New York snapshot, with the last quote in the prior 30 minutes.
  2. Get the forward from put-call parity at the near-money strike.
  3. Solve Black IV on the call-put mid average at the near-forward strike. Interpolate between two strikes when they bracket the forward.
  4. Interpolate total variance to 30 days between the two bracketing expiries. Do not extrapolate.
- **Tiers and flags:** Tier 1 has a forward bracketed by two strikes. Tier 2 has one strike only. Also flag ex-date in front term, front term under 7 days, degraded days, and quote age.
- **`MF30` (descriptive, 2024 onward):** PCHIP in log-moneyness, flat wings, dense grid. Require at least 2 OTM quotes per wing. Report the share of extrapolated variance. SVI is dropped.
- **Rates:** real USD Treasury series from FRED, not a placeholder.
- **Sensitivity only:** American tree inversion with dividends known at that date, and the 7-day front-term floor.

### Realized variance
- Use total-return close-to-close log returns from `equity_official_daily`. Include dividends and the January 2025 rights.
- Sum squared returns in the 30 calendar days after the origin close.
- Parkinson and Garman-Klass are dropped, because high/low include extended hours and miss overnight jumps. Report an overnight and open-to-close split instead.

### Tests
1. **Primary question:** does log `ATM30` add information beyond log RV over 1, 5 and 22 sessions (HAR), on identical dates?
2. **Inference:** block bootstrap with 21 and 63-day blocks, and non-overlapping samples across all 21 offsets. Newey-West is reported for comparison only.
3. **Stability:** report 2018-2023 and 2024-2025 separately. Add leave-one-year-out, year-demeaned, and leave-one-event-out estimates.
4. **Forecast race:** QLIKE is primary and MSE is secondary. Compare `ATM30`, HAR, GARCH and EWMA, with expanding-window calibration and a 252-session start.
5. **Reported but not headline:** MZ a and b in logs. The level form goes in an appendix. VRP reports both mean and median, because they differ in sign.
6. **Measurement error:** instrument `ATM30` with lagged IV, as a sensitivity run.

### Argentina events
- Fix the list in advance: 2019 PASO and general; 2021 PASO and midterm; 2023 PASO, general and runoff; 2025 PBA and midterm. The 2016-2018 test adds 2017 PASO and midterm.
- Measure **forward variance between expiries that straddle the event**, against non-event cycles at the same term. A rise in 30-day IV alone is mechanical.
- Report case studies with placebo dates and no p-values. Remove event variance from both IV and RV in any exclusion run.

### Dropped or deferred
- **Dropped:** the 2013-2015 period, the intraday jump split, and skew prediction before 2024.
- **Deferred:** the 60-day horizon and the ADR basket.

### Clean tests

You decided to bring your own copy of the data, including 2026, into this repository. So 2026 becomes this study's forward test.

| Period | Role | Note |
|---|---|---|
| 2018-05 to 2025-12 | Development | Already examined in the debate, so results are exploratory |
| 2016-01 to 2018-04 | One-time backward test | Thinner chains, about 28 windows, Alpaca closes |
| 2026-01 to the last origin with a full 30-day RV window | One-time forward test | About 9 windows, so "inconclusive" is a likely verdict |

**Caution:** Results here will expose 2026 returns to you. After that, the 2026 test of the `options-valuation-model` ADR project is no longer blind, even with separate files.

## Implementation

**Before you start, put this data in `data/`:**
- Options: cbbo-1m, definitions, and statistics.
- Equity: official daily, ohlcv-1d, and bbo-1m.
- Dividend ledger, with its 2016-2018 rows if they exist.
- Alpaca raw daily bars.

Tell me the format, raw or decoded, because the loader depends on it.

**New files in `vix_ggal_adaptation/`, using flat modules as in `options/`:**
- `PROTOCOL.md`: all rules, thresholds, event dates, verdict rules, and the access log.
- `config.py`: paths and one date gate. The gate blocks the two test periods until the freeze.
- `load_data.py`, `atm_index.py`, `model_free_index.py`, `realized.py`, `forecasts.py`, `inference.py`, `events.py`.
- `run_development.py`, `run_tests_once.py`, `tests/`, `reports/`.

**Copy these with a source note, and do not edit the originals:**
- `options/volatility_index.py`: `expiry_minutes` (use 16:00 New York), `constant_maturity`, parity logic from `single_term`.
- `options/option_analytics.py`: `solve_iv`, `binomial_price`.
- `options-valuation-model/adr/estimators_v2.py`: `ewma_variance`, `fit_garch`. `fit_har` uses non-negative weights, so the HAR regression gets its own OLS.
- `options-valuation-model/adr/databento_store.py`: `parse_occ`, `iter_zip`.
- `options-valuation-model/adr/returns_v1.py`: `session_returns`.

**Stages:**
1. **Data check.** Reconcile your copy with the inventory counts, up to the gate. Resolve the `GGAL1` root around the 2025 rights.
2. **Build series.** Publish coverage counts by year and by days to expiry. Explain the 95% vs 83% gap. Do not impute missing days. Test across the February-March 2025 quote format break.
3. **Development analysis.** Write all tests and figures. Label them exploratory.
4. **Freeze.** Record the method and verdict rules in `PROTOCOL.md`.
5. **One-time tests.** I ask you first, then run each test once. Any later method change makes that period development data.
6. **Write-up.** Include an honest paragraph on American exercise and dividends, missing-day selection, and the low power.

**Tools:** Python in Conda `py4fi` does the build and the inference. `reports/` gets a CSV export so that you can repeat the MZ and Newey-West regressions in EViews.

**Open item for you:** ask Databento how the cbbo-1m bars are built for early years. Flags and null `ts_event` suggest reconstruction (inference, not confirmed).

## Verification

Run `conda run -n py4fi python -m unittest discover -s tests -v`. The tests must show:
- A synthetic flat-vol chain returns the input vol, for both `ATM30` and `MF30`.
- The date gate raises an error for a blocked period.
- No forecast input uses a return after the origin date.
- Total-return calculation is correct across an ex-date and the rights date.

Then compare the development results with the debate checks. Differences must have an explanation:
- ATM coverage near .91, .90, .85, .72, .78, .85, .91 for 2018-2024, under the advocate's rule.
- Pooled log b near .55, and near .97 in 2024.
- `ATM30`/`MF30` median vol ratio near 1.07.

Inspect plots of `ATM30` around 2019-08-12 and the rights date, and confirm one test-run marker per period.

## Rule slips in the debate

The agents reported these contacts with data that `options-valuation-model/research/adr/HANDOFF.md` seals:
- The advocate printed the whole dividend ledger, including 2026 ex-date rows (amounts only). It also loaded the official-close file before it filtered, but printed nothing from 2026. Nothing from 2026 entered its results.
- The advocate read 2025 in its first-round regressions. 2025 is that project's completed holdout.
- The critic printed whole-file row counts, which include sealed sessions.
- The inventory loaded whole equity files, then dropped 2026 rows. It read 2026 row and day counts from `report.md`.
- I saw the Alpaca request parameters, which show the 2026 end date, and no 2026 prices.

These contacts do not affect the checks above. They do matter to that project's record, so consider adding a note there. I have not edited that project.
