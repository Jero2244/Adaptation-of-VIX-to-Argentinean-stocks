# Errata: wording corrections for the papers

Scope: `writeup/GGAL_study_plain_final.pdf`, `writeup/GGAL_study_technical_final.pdf`, and their builders. I did not edit any builder or PDF. This list says what each text needs. Each item cites its audit finding (`audit/AUDIT_REPORT.md`).

All numbers marked "development" come from open data (2018-05-01 to 2026-10-29). They do not replace the pre-registered Stage 5 result ("Inconclusive", `b` = .281).

## Wording that must change

| ID | Where | Current wording | Correct wording |
|---|---|---|---|
| F1 | Title, abstract, section 1, folder name | "VIX-style index", "translates the VIX methodology", "VIX adaptation" | "ATM implied volatility index (`ATM30`)". Add one sentence: `ATM30` is a Black at-the-money implied volatility interpolated to 30 days. It has no part of the CBOE strip formula. A literal CBOE calculation needs 3 or more out-of-the-money strikes on each wing in both terms. The chain has that on 245 sessions, almost all from 2024. See `README.md` |
| F1 | Description of `MF30` | "model-free" or "CBOE-style" | "Descriptive integral of a fitted smile with flat wings. Not the CBOE formula." |
| F21 | Technical paper, section 3.2 | "a HAR specification (Corsi, 2009)" | "a HAR-type regression on squared daily returns". Corsi (2009) uses intraday realized variance. Here `RV1` is one squared daily return, and the floor binds on 47 sessions |
| F12 | Technical paper, section 4; plain paper | "variance risk premium" for `ATM30`² minus `RV30` | "ATM variance minus realized variance". `MF30`² / `ATM30`² has a median of 1.15, so ATM variance understates model-free variance. "Implied variance exceeds `RV` on 72% of origins" is a lower bound for the premium |
| F13 | Every interval table and the abstract | "95% interval" | "nominal 95% interval". Measured coverage is 87% to 91% (development, `fixes/f09_coverage.csv`), and the study's own earlier simulation gave 80% to 91%. State this under each table |
| F14 | Technical paper | The Mincer-Zarnowitz regression is run in Stage 3 but is not in the paper | Add the table in `fixes/f09_mincer_zarnowitz.csv`. In logs: a = -.54, b = .70, joint p < .0001. In variance levels: b = .69, p = .064. In volatility levels: b = .68, p = .027. State that `a` not 0 and `b` not 1 is expected in part from the variance risk premium |
| F6 | Abstract | Leads with `b` = .622 | Lead with three numbers together: .622 (all origins, in-sample), .366 (before 2025-03, no events, interval includes zero), and .281 (one-time test, Inconclusive). The positive result is fragile |
| F2 | Section 9 (limits) | "-1.3% to -1.9%" with no source | Replace with the measured simulation: with a 2% dividend inside the term, term IV is too high by 1.7% (30 days), 2.6% (20 days), and 5.1% (10 days). With 3.5%, by 4.6%, 6.7%, and 12.6%. See `audit/a05_american_bias.out`. On real data, the tree correction does not move `b` much and adds noise. See `fixes/FIXES_REPORT.md` |

## Method text that must change

| ID | Text | Correction |
|---|---|---|
| F8 | Section 3.1, "30-minute age rule" | Before 2025-03 each instrument has exactly 390 rows per day, one per minute. So the quote age is 0 on 99.5% of valid days, and the rule removes nothing. From 2025-03 rows appear on updates only, and the rule removes 7.0% of snapshot rows. The rule changes meaning at the format break. It is not a staleness control before 2025-03 |
| F7 | Section 3.1, snapshot rule | The code takes the last non-null value of each column. After 2025-03 a null bid means "no bid", so an old bid can join a new ask. Write this down. Under the strict last-row rule 9 days lose their value, and the largest change is +14.2% (2025-07-11). See `fixes/f04_variants.csv` |
| F9 | Section 3 | The near term is used down to 15 minutes before expiry. On 249 valid days the near term is under 7 days, and the index horizon drifts toward about 35 days. The `atm30_floor7` series is the 7-day alternative |
| F10 | Section 3 | There is no extrapolation. 101 sessions have no listed bracket. On 21 valid days the far term is more than 65 days away. Missing days follow the expiry cycle |
| F11 | Section 4 | `RV30` uses sessions in (t, t + 30 days] and the factor 365/30. The last session is on average 29.37 days after the origin. `RV` is about 2% low against a 30-day IV. The constant in the log regression absorbs this. The premium level and the calibration hit rate do not |
| F16 | Section 2 (data) | `contract_multiplier` is undefined in the OPRA definitions (the value is INT_MAX) and `unit_of_measure_qty` is blank. The 100-share deliverable is assumed, not verified. `fixes/f11_check_multiplier.out` shows this on 12 sample days. The `GGAL1` question stays closed |
| F17 | Section 2 (data) | The folder holds `cbbo-1m`, `bbo-1m`, `ohlcv-1d`, `statistics`, `definition`, and `tcbbo`. It does not hold MBP-1, MBP-10, or BBO-1s. 2013-2015 is dropped. OPRA statistics and TCBBO are not used |
| F18 | Section 3 | The rate is log(1 + yield) on a bond-equivalent Treasury yield, with linear interpolation between 1 and 3 months. CBOE converts to an annual percentage yield and uses a spline. The effect is about 6 bp at a 5% yield |
| F19 | Section 3 | The stock mid comes from the Nasdaq book only (`XNAS.ITCH`), not the consolidated quote. It feeds diagnostics and one calibration cut. `fixes/f07_bbo_quality.out` shows that the Nasdaq mid is close to the official close (median gap 5 bp) during the regular session |
| F20 | Section 3 | 17 half days have no value, because the snapshot time stays at 15:45. A fix would sample 15 minutes before the early close |
| F24 | Appendix | On 3 of 393 post-break days the independent rebuild differs by 3e-6 to 1.8e-5. The probable cause is the order of rows with equal timestamps. No effect |

## Process text that must change

| ID | Item |
|---|---|
| F15 | The session wrote both unlock markers. The protocol says only the user approves a marker. The user's saved hash has not been compared with `reports/freeze_manifest.json`. The two Stage 5 runs are not in the access log. Run `fixes/f10_check_manifest.py --saved <your hash>` and record the result outside the frozen files. Today the manifest hash matches the hash in `HANDOFF.md`. Only the user can compare the saved copy |
| F22 | The builders type the open-data numbers by hand. Only the Stage 5 numbers are checked against a result file. A later edit can break this silently. The fix is an assert against `reports/stage4_coefficients.csv` and `reports/stage3_*.csv`. This needs an edit to the builders, which I did not make |
| F23 | The reference lists lack: the Cboe VIX white paper, Carr and Madan (1998), Britten-Jones and Neuberger (2000), Jiang and Tian (2005), Mincer and Zarnowitz (1969), Newey and West (1987), and Politis and Romano (1992). `README.md` lists them. Verify each one against the source |

## Findings with no wording change

- F3, F4, F5: method limits, tested in `fixes/`. They need a short note in the limits section with the numbers in `fixes/FIXES_REPORT.md`.
- F6: fragility is a property of the data. See the F6 row above.
