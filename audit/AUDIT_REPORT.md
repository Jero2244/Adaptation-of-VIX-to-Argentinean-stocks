# Audit report: GGAL ADR implied volatility study

Date: 2026-11-10. Scope: the whole project folder. I changed no original file. All audit scripts and outputs are in `audit/`. `freeze.differences()` returns an empty list after the audit, so the frozen files are unchanged. I did not rerun Stage 5, and I read raw quotes on open dates only (2018-05-01 onward).

## 1. Verdict

**The code is sound. The study is not a VIX replication. The written conclusions are mostly as weak as the evidence, and that is correct.** I rebuilt `ATM30` from the raw Databento quotes with independent code, and it matches the stored series to 1e-10 on 16 sample days and to 2e-5 on all 393 valid days after 2025-03. I rebuilt returns, RV30, the HAR inputs, the primary coefficient (.622), the Stage 5 coefficient (.281), and the calibration hit rates (69.6% and 93.8%), and all match. I found no look-ahead and no critical calculation error. The main problems are in the method and the framing, not in the arithmetic. First, the primary index is a Black at-the-money implied volatility, so no part of the CBOE variance-swap formula is in it, and the project name and your own description say "VIX methodology". Second, the options are American and GGAL pays dividends of 2% to 3.7%, and the recipe overstates term IV by about 2% to 13% when a dividend falls inside the term. Third, the quotes are very wide: the bid-ask band puts a median uncertainty of about ±14% on the IV, and no spread filter exists. Fourth, the HAR baseline is weak (R² .097 with a negative 22-day coefficient), so "information beyond HAR" is a low bar. Fifth, the positive result (b = .622) depends on election windows and on the period after the 2025-03 quote format change, and the one frozen test is inconclusive. You can trust the statement "inconclusive, with weak in-sample evidence". You cannot present this as a tested VIX-style index for GGAL.

## 2. Findings

Type: **E** = definite error or omission. **C** = method choice that is debatable. **U** = I am unsure.

| ID | Severity | Type | Location | What is wrong | Why it matters | Fix |
|---|---|---|---|---|---|---|
| F1 | Major | C + E (framing) | `atm_index.py`, `model_free_index.py`, folder name, `writeup/build_*_final.py` | The primary series `ATM30` is a Black (1976) ATM implied volatility. The CBOE formula is absent: no strip sum of ΔK/K² · e^{RT} · Q(K), no K0, no ΔK, no (F/K0 − 1)² term, no zero-bid stop. `MF30` is also not CBOE: it integrates a PCHIP smile with flat wings. | The choice is correct for this chain (see evidence A). But the project name, and the description "translates the VIX methodology", are wrong. A referee will reject a "VIX-style" claim at once. | Rename the series and the paper ("ATM implied volatility index"). Say in the abstract that a CBOE index cannot be built before 2024. Add a literal CBOE-style series for 2024 onward as a descriptive series, with a gate of 3 or more strikes on each wing. `audit/a02_series_and_cboe.py` has working code. |
| F2 | Major | E | `atm_index.py:86-136` (`parity_forward`, `term_iv`); write-up section 9 | American exercise and dividends are not handled. Parity and Black assume European options. The study never measured the effect. The write-up quotes "-1.3% to -1.9%" from an unrecorded debate check, with no sign convention. | My simulation runs your `term_iv` on American tree prices (evidence B). With no dividend, the error is below 0.4%. With a 2% dividend inside the term, term IV is too high by 1.7% (30 days), 2.6% (20 days), and 5.1% (10 days). With 3.5%, it is 4.6%, 6.7%, and 12.6%. 238 valid days have an ex-date in the front term. | Invert with an American tree and known dividends, or use only the out-of-the-money option at each strike. As a minimum, report the measured bias and keep the "drop `flag_ex_in_front`" result (b = .665) beside the headline. |
| F3 | Major | E | `atm_index.py:70-83` (`two_sided_pairs`); `build_series.py` | No spread filter exists. The index uses the mid of very wide quotes. | Near the money, the relative IV error is about the relative price error. The half-width of the bid-ask IV band is ±13.7% (median), ±25.6% (75th percentile), and ±39.8% (90th percentile). The daily SD of log `ATM30` changes is 7.3%. Examples: 2023-05-30, 12.5 put quoted 0.05 / 3.30; 2024-06-18, 33 call quoted 0.60 / 2.95. Median relative spread is .24 before 2025-03 and .55 from 2025-04. | Add a maximum-spread rule. Store IV at the bid and at the ask as an uncertainty band. Repeat the primary regression with the filter. Treat this as development work. |
| F4 | Major | C | `atm_index.py:108-136`; `PROTOCOL.md` "Tier" | Strike discreteness. 561 of 1,846 valid days (30%) are Tier 2: one strike, up to 25% from the forward (median 11.8%), is used as "at the money". In 2021 and 2022 the median near term has one two-sided strike. 34% of primary rows have a forward below USD 12 with strikes USD 2.50 apart. | The IV at a strike 12% away is a skew point, not an ATM value. Tier 2 is 50% to 87% of days in 2020-2022. b is .703 on Tier 1 and .435 on Tier 2. | Report Tier 1 as the primary series, or model the skew. State the strike gap per day as a quality flag. |
| F5 | Major | C | `realized.py:97-104`, `stage4_rules.py:13` | The baseline is weak. The HAR inputs are squared daily returns. In the primary regression the HAR coefficients are .008, .100, and -.025, and R² is .097. The folder holds 1-minute Nasdaq quotes, but the study code does not use them. | "Adds information beyond HAR" is a low bar against this baseline. Your own review found b near .53 with 5-minute inputs, and .28 to .30 without events, with an interval that includes zero. Those checks are not in the study code. | Build RV from `bbo-1m` mids (5-minute, plus the overnight return). Use it for the HAR inputs and as a second target. |
| F6 | Major | C | Abstract and section 4 of the technical paper; `reports/stage4_descriptive.md` | The positive result is fragile. b = .622 falls to .459 without elections and to .366 before 2025-03 without elections (interval includes zero). The period from 2025-03 gives 1.19, and that period has a different quote format and much wider spreads. Stage 5 is inconclusive. | The data cannot separate "IV became informative" from "the data changed in 2025-03". The 2019 PASO return of -82.4% (log) drives the level results: level R² is .031 with it and .146 without it. | Keep the present wording. Lead the abstract with the three numbers together (.622, .366, and .281 inconclusive), not with .622 alone. |
| F7 | Minor | E | `build_snapshot.py:33-40` (`last_quotes`) | `groupby().last()` takes the last non-null value per column. After 2025-03 a null bid means "no bid". So the code joins an old bid with a new ask and a new age. | Measured on all 393 valid days from 2025-03: 1.7% of instruments get a revived bid per day. With a strict last row, 8 days lose their value, 6 days change by more than 1%, and the largest change is +14.2% (2025-07-11). The effect on `MF30` wings is not measured. `PROTOCOL.md` discloses the rule but tested its effect on values only for 2018-2023. | Use `drop_duplicates(keep="last")`. Treat a null bid as no bid. |
| F8 | Minor | E | `build_series.py:19,82`; write-up section 3.1 | The 30-minute age rule does nothing before 2025-03. Each instrument has exactly 390 rows per day, one per minute, so the quote age is 0 on 99.5% of valid days. After 2025-03 rows appear only on updates, and the rule then removes 7.0% of snapshot rows. | The write-up describes a staleness control. For 2016 to 2025-02 it does not exist, and the rule changes meaning at the format change. | Say this in the method text. A real staleness rule needs the time of the last quote change. |
| F9 | Minor | C | `bracket_terms` in `atm_index.py:139-146` | The near term is used down to 15 minutes before expiry. Near IV is 24% above far IV at 1 to 3 days and 17% above at 3 to 7 days. The largest near IV is 7.0. 249 valid days have a near term under 7 days. | The effect on the index is small (below 1%), because total-variance weights shrink the near term. But on these days the index is in effect the far-term IV at 31 to 37 days. CBOE rolls away from such terms. | Make `atm30_floor7` primary, or say that the index horizon drifts to about 35 days near expiry. |
| F10 | Minor | C | `combine` in `build_series.py:50-64` | No extrapolation. 101 sessions have no listed bracket, mostly just after a monthly expiry. On 21 valid days the far term is more than 65 days away, and on 20 it is more than 90 days away (the longest is 121). | Missing days follow the expiry cycle, so the sample is not random in time. Long interpolation spans assume a flat forward variance over 3 to 4 months. | Flag days with a far term above 65 days. Report coverage by cycle phase (already partly done). |
| F11 | Minor | C | `realized.py:67-94` | RV30 uses sessions in (t, t + 30 days] and the factor 365/30. The last session is on average 29.37 days after the origin, and 42% of windows end before day 30. | RV is understated by about 2% against a 30-day IV. The constant absorbs this in the log regression. The VRP level and the calibration hit rate do not (the calibration report states 68.9% with the real length). | Annualize with the real window length, or state the 2% offset beside each VRP number. |
| F12 | Minor | E (terms) | `run_development.py:280-289`; paper section 4 | "Variance risk premium" is `ATM30`² minus RV. ATM variance is not model-free implied variance. Where both exist, `MF30`² / `ATM30`² has a median of 1.15. | The premium is understated by about 13%, so "implied variance exceeds RV on 72% of origins" is a lower bound. The mean is negative only because of the 2019 PASO. | Call it "ATM variance minus RV", or use `MF30` for 2024 onward. |
| F13 | Minor | C | All interval tables | The "95%" bootstrap intervals cover 80% to 91% in your own simulations. Every table prints the nominal label. | Borderline results are weaker than they look, for example "All, no events": .152 to .715, and .060 to .761 with 63-session blocks. | Print calibrated intervals, or widen by the simulated factor (SD of b over median SE is 1.3 to 1.5). |
| F14 | Minor | C | `reports/stage3_results.md`; final papers | The Mincer-Zarnowitz test is run but not reported in the final paper. My rerun, with HAC and 21 lags: in logs a = -.54, b = .70, joint p < .0001. In variance levels b = .69, p = .064. In volatility levels b = .68, p = .027. | A paper on implied against realized volatility needs the unbiasedness test in the text, with the caveat about the premium. | Add one table. |
| F15 | Minor | E (process) | `HANDOFF.md` "Process facts"; `reports/backward_test_*_unlocked.json` | The session wrote both unlock markers, and the protocol says that only the user approves a marker. Your saved hash was never compared. The two runs are not in the access log. The test is backward in time. | The "one-time test" rests on self-report. All of this is disclosed, and the outcome is inconclusive, so no claim depends on it. | Compare your saved hash now, and record the result outside the frozen files. |
| F16 | Minor | E | `load_data.py` definitions; `config.py:29` | `contract_multiplier` is undefined in the OPRA definitions (the value is INT_MAX), and `unit_of_measure_qty` is blank. So the code cannot detect a non-standard deliverable. | 17 primary rows have the 2025-01-21 rights date inside the bracket. You closed the `GGAL1` question, and I did not reopen it. | State this limit in the data section. The "drop `flag_rights_in_bracket`" result (b = .624) already shows a small effect. |
| F17 | Minor | E (docs) | Project root; your task description | No `README.md` exists at the root. Your description names MBP-1, MBP-10, and BBO-1s, and options from 2013. The folder holds `cbbo-1m`, `bbo-1m`, `ohlcv-1d`, `statistics`, `definition`, and `tcbbo`. 2013-2015 is dropped. OPRA statistics and TCBBO are never used. | A reader cannot tell which data produced which result. Trades (TCBBO, from 2023-03) could check the quote mids, and nobody did this. | Write a short README with the data inventory and the pipeline map. |
| F18 | Cosmetic | C | `build_series.py:25-35` | The rate is log(1 + yield) on a bond-equivalent Treasury yield, linear between 1 and 3 months. CBOE converts BEY to APY first and uses a spline. | The difference is about 6 bp at a 5% yield. The whole discount factor is 0.4% of price at 30 days. No material effect. | State the convention. |
| F19 | Cosmetic | C | `build_snapshot.py:84-86` | The stock mid comes from the Nasdaq book only, not the consolidated quote. | It feeds only diagnostics and one calibration cut. | State it. |
| F20 | Cosmetic | C | `PROTOCOL.md` "Half days" | 17 half days have no value, because the snapshot time stays at 15:45. | Small loss of days. | Sample 15 minutes before the early close. |
| F21 | Cosmetic | E (terms) | Paper section 3.2 | The regression is called "a HAR specification (Corsi, 2009)". Corsi's model uses intraday realized variance. Here "RV1" is one squared daily return, with a floor that binds on 47 sessions. | Terminology. | Write "HAR-type regression on squared daily returns". |
| F22 | Cosmetic | E | `writeup/build_technical_final.py`, `build_plain_final.py` | Open-data numbers are typed into the builders. Only the Stage 5 numbers are checked against a result file. | I compared every typed number with the CSV reports, and all match today. A later edit can break this silently. | Add asserts against `reports/stage4_coefficients.csv` and `stage3_*.csv`. |
| F23 | Cosmetic | E | Reference lists | Core sources are missing: the Cboe VIX white paper, Carr and Madan (1998), Britten-Jones and Neuberger (2000), Jiang and Tian (2005), Mincer and Zarnowitz (1969), Newey and West (1987), and Politis and Romano (1992). | The paper starts from the VIX and uses these methods. | Add them. Verify all references against the sources. |
| F24 | Cosmetic | U | `audit/a03_postbreak.csv` | On 3 of 393 days my rebuild differs from the stored value by 3e-6 to 1.8e-5 (2025-11-11, 2025-10-13, 2026-10-12). | No effect. The probable cause is the order of rows with equal timestamps. I did not find it. | None needed. |

### Evidence A: a literal CBOE calculation on this chain (F1)

Script: `audit/a02_series_and_cboe.py`. Output: `audit/a02_series_and_cboe.out` and `audit/a02_cboe_by_session.csv`. I applied the white-paper formula per term to the stored 15:45 snapshot, then interpolated total variance to 30 days.

| Year | Sessions | Share with 2+ OTM bids on each wing, both terms | Median strikes used, near term | CBOE-style / `ATM30` (vol, median) | Variance recovered under a flat smile (1 = no error) |
|---|---|---|---|---|---|
| 2018 | 169 | 27% | 4 | 1.10 | 1.07 |
| 2019 | 252 | 12% | 3 | 1.12 | 1.12 |
| 2020 | 253 | 0% | 2 | 1.16 | 1.21 |
| 2021 | 252 | 0% | 2 | 1.30 | 1.48 |
| 2022 | 251 | 0% | 2 | 1.83 | 1.63 |
| 2023 | 250 | 15% | 3 | 1.11 | 1.10 |
| 2024 | 252 | 52% | 7 | 1.00 | 0.94 |
| 2025 | 250 | 38% | 6 | 1.02 | 0.97 |
| 2026 | 208 | 71% | 11 | 1.01 | 0.94 |

- The last column prices the same strikes with Black at the ATM vol, then applies the CBOE sum. A value of 1.63 means that the strike grid alone overstates variance by 63%, before any skew.
- With 3 or more strikes per wing on both terms (245 sessions, almost all from 2024), the ratio to `ATM30` is .98 to 1.09 and the flat-smile recovery is .91 to 1.01. So a CBOE-style series is usable only there.
- The daily SD of log changes is 12.4% for the CBOE-style series and 7.3% for `ATM30`. The CBOE-style series is far noisier.
- **Reading:** your move to an ATM series is right. The error is the name, not the choice.

### Evidence B: American exercise and dividends (F2)

Script: `audit/a05_american_bias.py`. It prices American calls and puts on a CRR tree (600 steps, one cash dividend at mid-term, known flat vol), and it runs your own `atm_index.term_iv` on those prices. With European prices the same recipe returns the true vol within 0.04%.

| Dividend inside the term | 10 days | 20 days | 30 days | 45 days |
|---|---|---|---|---|
| None | +0.04% | +0.08% | +0.11% | +0.16% |
| 2.0% of the price | +5.1% | +2.6% | +1.7% | +1.2% |
| 3.5% of the price | +12.6% | +6.7% | +4.6% | +3.1% |

- Cells are the mean relative error of term IV. The worst single case is +26.7%.
- The parity forward is too high by 0.1% to 0.8% in the same cases.
- Real dividends per event, against the prior close: 3.75% (2023-05-31), 3.29% (2022-05-13), 2.32%, 2.12%, and 2.06% (2024).
- **Limit:** this is a model result with a known dividend. The index error is smaller than the term error, because both terms enter with weights.

### Evidence C: quote width (F3, F4)

Scripts: `audit/a06_misc.py`, `audit/a07_level_bias.py`, `audit/a03_reproduce_raw.py samples`.

- Share of valid days with a relative spread (call plus put spread over call plus put mid, worst term) above .25: 55%. Above .50: 25%. Above 1.0: 5%.
- Monthly median relative spread: .13 to .21 from 2024-10 to 2025-03, then .30, .45, .33, .69, and .63 from 2025-04 to 2025-08.
- Open item "2022-07-08" is now explained. The near term had one pair, at strike 7.5, with the stock near 6.68: call 0.05 / 0.10 and put 0.80 / 1.70. The forward of 6.32 is quote noise, not a data fault.
- **Unsure:** `ATM30` over realized vol has a median of 1.28 to 1.37 in 2021-2023 (thin quotes) and 1.06 to 1.12 in 2024-2025. This suggests an upward bias from wide quotes. But inside years, neither the spread nor the tier explains the ratio (coefficients .019 and -.009, both far from significant). So I cannot show a level bias.

## 3. What I verified and found correct

**Index construction**
- **Raw rebuild:** independent code (own zip reader, snapshot, pairing, parity forward, `brentq` inversion on the discounted price, interpolation, rate rule) matches the stored `ATM30`. The largest difference is 7e-11 on 16 sample days from 2018 to 2026, and 1.8e-5 on 393 valid days from 2025-03. The stored snapshot table matches the raw files on every sample day, with 0 mismatched rows.
- **Forward:** put-call parity at the strike with the smallest |C − P|, with F = K + e^{rT}(C − P). This is the CBOE rule. No dividend input is needed.
- **Price for inversion:** e^{rT}(C + P)/2 equals the Black call plus (K − F)/2. I checked the identity.
- **Quote rules:** bid above zero and ask at or above bid, on both sides. Crossed quotes are excluded. The snapshot has 0.0% crossed quotes before 2025-03 and 0.01% after.
- **Term interpolation:** linear in total variance to 43,200 minutes, with a 525,600-minute year. This equals the CBOE weighting. Weights stay inside 0 to 1.
- **Roll:** the mean absolute daily log change is 6.4% on roll days and 4.7% on other days. I found no large discontinuity.
- **Time:** all conversions use `America/New_York` with DST. The snapshot is the bar stamped 15:45:00. Expiry is 16:00 New York on the date in the OSI symbol, so holiday-shifted expiries such as 2022-04-14 are right. Buenos Aires time plays no role, because the ADR and its options trade in the US.
- **Rates:** each session uses the last FRED observation before that session. No look-ahead.
- **Flat-vol tests:** `tests/test_index.py` covers both series. I did not rerun the suite (see section 4).

**Realized volatility**
- **Returns and RV30:** rebuilt from the official closes and the cash file. The largest difference is 0 for returns and 2e-14 for RV30. Row presence matches on all 2,115 rows.
- **HAR inputs:** rebuilt, with a difference of 0. They use returns through the origin only.
- **Alignment:** IV at t is compared with returns after the close of t. No training row has a window that ends after the origin. Annualization is consistent: 365 days on both sides.
- **Closes:** the Nasdaq official close against Alpaca: 7 of 2,104 sessions differ, and the largest gap is 17 bp. So the Alpaca bars are unadjusted, which is what the test needs.
- **Corporate actions:** every ex-date is a session. Cash enters the return on the ex-date. The closes show no split-like step: the eight largest daily moves are all market events (2019-08-12, March 2020, and the 2025 elections).

**Statistics**
- **Primary regression:** statsmodels gives b = .622, R² .097 and .177, and a HAC t of 4.13 (21 lags), 3.85 (42), and 3.82 (63). The naive OLS t is 13.3, so the overlap correction matters and is applied.
- **Bootstrap:** my own circular block bootstrap gives .341 to .934 (21 sessions) and .319 to .974 (63). The study has .337 to .916 and .309 to .946.
- **Residuals:** autocorrelation is .94 at lag 1 and .03 at lag 21. Blocks of 21 and 63 sessions fit this.
- **Unit roots:** ADF rejects a unit root for log IV (p = .0001) and log RV30 (p < .0001). The spurious-regression risk is low.
- **Stage 5:** from the saved test panel, n = 455 and b = .2810. The verdict "Inconclusive" follows from the frozen rules.
- **Formulas:** QLIKE, Clark-West, the Duan factor, the GARCH recursion, and EWMA are correct as coded.
- **Seeds:** every bootstrap has a fixed seed.
- **Events:** all 11 election dates agree with my knowledge of the Argentine election calendar. I did not check them against an official source.

**Implied move calibration**
- **Formula:** z = (R − (rT − s²/2)) / s, with s = `ATM30` · √(30/365), is correct for a risk-neutral lognormal band on the total return.
- **Rebuild:** 1,828 rows, with a z difference of 0. Inner 69.58% against 68.27%. Outer 93.76% against 95.45%. Mean z² is 1.334.
- **Benchmark and interval:** the nominal rates are the right reference under normality. A rough binomial check with 87 independent windows gives 60% to 79% for the inner rate, wider than your bootstrap interval of 63.9% to 75.4%.
- **Reading:** the report states the risk-neutral against real-world caveat, the horizon mismatch, and the selection effect. I found no overclaim there.

**Write-up**
- Every number typed in `build_technical_final.py` and `build_plain_final.py` matches `reports/stage4_descriptive.md`, `reports/stage3_*.csv`, `reports/stage2_coverage.md`, and `reports/stage5_result.json`.
- Figure 1 and the forest figure match the data, with correct labels and units.
- The method section describes what the code does.
- The references in the two technical papers agree with my memory of the sources. Nobody checked them against the sources.

## 4. Could not verify

| Item | Reason | What I need |
|---|---|---|
| The four PDF files, page by page | No PDF renderer is installed (no poppler, no pypdf). I checked the builder sources, their asserts, the file times, and two figures | `pypdf` or poppler in an environment |
| The 247 unit tests | I did not run the suite, to avoid any write in the project. The manifest check shows that the tested code is unchanged | Your approval to run it |
| Raw 2016-2018 option quotes and Alpaca closes | I kept the audit on open dates. The Stage 5 number is rebuilt only from the saved panel | Your decision that the audit can read them |
| Power simulations, the "80% to 91%" coverage claim, and the review numbers (5-minute HAR, the 57% event share) | Not rerun | Time. The scripts are in `review/` |
| Dividend amounts, the rights value, and the tax basis | No external source checked. 19 of the 32 open dividend rows have the basis "unconfirmed" | Depositary notices |
| Adjusted contracts around 2025-01-21 | The definitions carry no multiplier. You closed this item | OCC memos |
| How Databento built `cbbo-1m` before 2025-03 | Unknown. Bars are complete every minute, and `ts_event` is the last trade time or null | Databento's answer |
| Effect of the last-non-null rule on `MF30` | Measured for `ATM30` only | One more run |
| Files that I did not read line by line | `tests/`, `report_stage4.py`, `compare_alpaca.py`, `plot_*.py`, `calibration/calib_post.py`, `calib_synthetic.py`, `calib_report.py`, `calib_figures.py`, `writeup/calib_common.py`, and the scripts in `review/` | Time |
| A cause for the higher b after 2025-03 | The format change, the wider spreads, and the 2025 elections occur together | New data, or trade-based checks with TCBBO |

## 5. Prioritized fix list

**Warning:** every `.py` file in the root is frozen. An edit breaks the manifest check. Stage 5 is finished and must not run again. So put each fix in a new file or a new version folder, and label every new result as development work.

1. **Fix the framing (F1, F17, F23).** Rename the index and the paper. State that the series is an ATM implied volatility, and show evidence A as the reason. Add a README and the missing references.
2. **Control quote quality (F3, F4, F7, F8).** Add a spread limit, a strict last-row snapshot, and an IV band from bid and ask. Make Tier 1 with the spread limit the primary development series. Report how b changes.
3. **Handle American exercise and dividends (F2).** Run the planned tree inversion, or use out-of-the-money options only. Replace the "-1.3% to -1.9%" text with a measured number.
4. **Strengthen the baseline (F5).** Build 5-minute RV from the `bbo-1m` file that is already in the folder. Use it for the HAR inputs and as a second target.
5. **Tighten the inference text (F6, F13, F14).** Lead with .622, .366, and .281 together. Print calibrated intervals. Add the Mincer-Zarnowitz table.
6. **Correct the smaller measures (F9 to F12).** Use the 7-day floor, flag long far terms, use the real window length, and rename the premium.
7. **Close the process items (F15, F22).** Compare your saved hash. Add asserts for the typed numbers.
8. **Plan the only clean confirmation.** A forward test on data after 2026-10-29, with rules frozen after fixes 2 to 4.

## Audit files

| File | Content |
|---|---|
| `rawio.py` | Independent reader for one day of a Databento zip |
| `a00_inspect.py`, `.out` | Schemas and basic statistics of the stored tables |
| `a01_raw_look.py`, `.out` | Raw record layout on five days: rows per instrument, flags, null bids, definitions |
| `a02_series_and_cboe.py`, `.out`, `a02_cboe_by_session.csv` | Series quality, roll effect, forward against stock, and the CBOE-style calculation |
| `a03_reproduce_raw.py`, `a03_samples.*`, `a03_postbreak.*` | Rebuild of `ATM30` from raw quotes, under the study rule and the strict rule |
| `a04_stats.py`, `.out` | Rebuild of returns, RV30, the regressions, Stage 5 b, and calibration |
| `a05_american_bias.py`, `.out`, `.csv` | American exercise and dividend simulation |
| `a06_misc.py`, `.out` | Manifest check, post-break detail, quote width |
| `a07_level_bias.py`, `.out` | Level of `ATM30` against quote quality |

Run each script from `audit/` with the `py4fi` Python and `PYTHONDONTWRITEBYTECODE=1`. They write only in `audit/`.
