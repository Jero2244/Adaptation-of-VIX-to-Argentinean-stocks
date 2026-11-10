# Protocol: GGAL ADR 30-day implied volatility study

Status: frozen on 2026-11-05 for the one-time test. The section "Stage 4 frozen rules" holds the verdict rules, and it overrides the earlier sections where they differ. This file changes the original plan where stated. `reports/freeze_manifest.json` holds the hashes of this file, the code, and the inputs.

## User decisions

Date: 2026-11-03.

| Decision | Effect |
|---|---|
| Use the Databento `GGAL` root as given | No search for `GGAL1` or adjusted contracts. The rights-date flag stays. |
| Do not seal or protect 2026 in this study | The date gate does not block 2026. 2026 is open data, not a blind forward test. |

The lockouts of `options-valuation-model` do not apply to this study. This study is a separate project, and its access log covers its own rules only.

## Periods

| Period | Role | Gate |
|---|---|---|
| 2013-04 to 2015-12 | Dropped | Always blocked |
| 2016-01 to 2018-04 | One-time backward test | Blocked until the user approves valid markers: `reports/backward_test_options_unlocked.json` for options, and `reports/backward_test_outcomes_unlocked.json` for closes and cash |
| 2018-05 to 2026-10-29 | Open | Not blocked |

The last 2026 origin with a full 30-day RV window is 2026-09-29. Report 2026 as a separate period. Do not call it a clean test, because the README of the data also lists 2025-2026 as exposed.

## Cash events

`data/adr_cash_events.csv` holds USD per ADS for the total-return calculation.

| Period | Source | Limit |
|---|---|---|
| 2016-05-19, 2017-05-10 | Alpaca corporate actions | Vendor rate and date. The record date is absent, and the tax basis is not confirmed. |
| 2018-05-11 onward | `adr_dividend_ledger.csv` | Quality flags stay in the source file. |
| 2025-01-21 | `rights_valuation.json` | Theoretical value. Alpaca publishes the same ex-date, and the T+1 inference agrees. |

Alpaca also lists USD 0.000413 on 2017-09-26. This study leaves it out, because no local dividend matches it.

## Access log

| Date | Contact |
|---|---|
| 2026-11-03 | Printed the dividend ledger, the local dividend list, and the Alpaca actions, including 2016-2018 and 2026 rows. No prices or returns. |
| 2026-11-03 | Printed bar counts and dates for 2016-01 to 2018-04, with no prices. Printed quote statistics for 2018-06-01, 2024-06-03, and 2025-03-03. |
| 2026-11-03 | Stage 2 read 2018-05-01 to 2026-10-29 only. The 2016-01 to 2018-04 test was not decoded. |
| 2026-11-04 | Stage 3 read official closes, returns, and series for 2018-05-01 to 2026-10-29, including 2026 returns and results. The 2016-01 to 2018-04 test was not read. Its two dividend rows in `adr_cash_events.csv` are filtered out by date. |
| 2026-11-04 | Two review agents and I ran checks on the panel, after the Stage 3 results. Both agents report that they also decoded the Nasdaq bbo-1m equity data through the date gate for 2018-05-01 to 2026-10-29, for a 5-minute measure. They report no read before 2018-05-01, and I did not check this separately. Their scripts and derived files are in `review/`. |
| 2026-11-04 | Two debate agents and I ran checks for the Stage 4 plan on `data/forecast_panel.parquet`, with simulations and dry runs on rows from 2018-05-01 onward. The agents report no read of the locked period, the Alpaca file, or raw Databento files, and I did not audit this. The marker does not exist. Files are in `review/stage4_debate/`. |
| 2026-11-04 | Stage 4 step 4 opened `data/source/alpaca_ggal_sip_raw.json` for the first time in this study. `alpaca_layout.py` printed only key names, value types, and the row count of 2,689 bars. `load_alpaca_closes` then parsed the file for `compare_alpaca.py`. Each parse held the locked rows in memory, and the filter removed them right after the parse. No locked value was shown or written. |
| 2026-11-04 | Stage 4 fetched DGS1MO and DGS3MO for 2015-12-01 to 2018-04-30 into `data/source/fred_rates_test.csv`. These are Treasury rates, not GGAL data. No value was printed. |
| 2026-11-04 | Stage 4 steps 2, 5, and 8 read open dates only: the rerun of `run_development.py`, the Alpaca comparison to 2026-09-14, and the rehearsal on 2020-01-01 to 2022-04-30. The rehearsal output is in `review/stage4_rehearsal/`. |
| 2026-11-04 | An independent agent checked the Stage 5 plan. Its report is `review/stage5_check/report.md`. It reports that one of its scripts parsed the full `data/adr_cash_events.csv`, so the two locked dividend rows were in memory for a moment. It reports that it read 2016-2018 zip member names only, and printed that both zips have 585 days that match the NYSE calendar. It read the header line of `data/source/fred_rates_test.csv`. It reports no read of the Alpaca files, no marker, and no locked value shown or written. I did not audit these reads. I checked that no marker, run record, or result exists. |
| 2026-11-04 | After the check, the fixes reran the tests, `run_development.py`, and the rehearsal on open dates. `review/stage5_check/guard_open_windows.py` ran the input stop on 73 open 28-month windows, and all passed. These runs load the cash file through `load_cash_events`, which parses the full file before its filter. No locked value was shown or written. **Correction after the second check:** until 2026-11-04, `tests/test_inputs.py` also read the full cash file by `pd.read_csv`, with no gate, in each full test run. The test now goes through the gate on open dates, but it still parses the local dividend file before a date filter. Each rehearsal also parsed the full Alpaca file through `load_alpaca_closes`, in `step_b`. Each rehearsal and each `step_a` parse `condition.json`, which holds locked dates and no prices, with no gate. |
| 2026-11-04 | A second independent agent checked the fixes. Its report is `review/stage5_fix_check/report.md`. It reports these contacts: `freeze.verify_manifest()` hashed the inputs, `load_cash_events` held the two locked rows in memory, and `iter_days` held 2016-2018 zip member names in memory. It read `data/source/fred_rates.csv` in full, which holds Treasury rates from 2018-01 and no GGAL data. It read on screen, partly by accident, the 2016-05-19, 2017-05-10, and 2017-09-26 dates and the USD 0.000413 amount, in `build_inputs.py` and this file. It reports no read of the Alpaca bars, the corporate actions, `fred_rates_test.csv`, or `condition.json`. It wrote no marker. I did not audit these reads. I checked that no marker, run record, or result exists. |
| 2026-11-04 | A separate agent searched public sources for a rights date in the test period. Its report is `review/stage5_rights_check/report.md`. It read no project file. **It saw 2017 prices:** search summaries and filing excerpts showed the 2017 offering price per share and per ADS, and the last reported ADS sale price before the offering. It removed them from its report, so they did not reach the study session or any study file. The report holds dates, share counts, ratios, peso dividend totals, and offering sizes, and no price. The study session read this report. |
| 2026-11-04 | The fix round after the second check reran the tests and the rehearsal on 2020-01-01 to 2022-04-30, on open dates. It also ran the input stop on 73 open 28-month windows at the limit .15, and it measured the gaps of closes on open sessions with no forward. These runs load the cash file through `load_cash_events`, and the rehearsal parses the full Alpaca file and `condition.json`. The rehearsal also ran with the old runner, to a scratch folder. No locked value was shown or written. |
| 2026-11-04 | A third independent agent rechecked the failure paths. Its report is `review/stage5_fix_recheck/report.md`. It reports these contacts: `load_cash_events` held the two locked rows in memory, `iter_days` held 2016-2018 zip member names in memory, and one script loaded `data/source/fred_rates.csv` in full, with only its column names printed. On screen, it read the 2016-05-19, 2017-05-10, and 2017-09-26 dates and the USD 0.000413 amount in this file and an earlier report, the rights report with no price, and the two test event dates. It reports no read of the Alpaca bars, the corporate actions, `fred_rates_test.csv`, or `condition.json`. It wrote no marker. I did not audit these reads. I checked that no marker, run record, or result exists. **Addition from the fourth check:** this entry omitted two minor items from its report: the cut-off input hashes that its searches printed, and its open-data reads. Neither holds locked content. |
| 2026-11-04 | The fix round after the third agent reran all 226 tests, the rehearsal on 2020-01-01 to 2022-04-30, and the input stop on 73 open 28-month windows. These runs load the cash file through `load_cash_events`, and the rehearsal parses the full Alpaca file and `condition.json`. The test suite also parses the local dividend file before a date filter. No locked value was shown or written. |
| 2026-11-04 | A fourth independent agent rechecked the latest fixes. Its report is `review/stage5_narrow_recheck/report.md`. It reports these contacts: `load_cash_events` held the two locked rows in memory, `iter_days` may have held 2016-2018 zip member names in memory, and tests may have loaded `data/source/fred_rates.csv`, with nothing printed from it. On screen, it read the 2016-05-19, 2017-05-10, and 2017-09-26 dates, the USD 0.000413 amount, the two test event dates, and the disclosure text. It skipped one test that parses locked rows, and an audit hook recorded no open of the Alpaca file or `fred_rates_test.csv`. It read open closes and the open series. Dates from 2016-2018 in its outputs carry invented values. It wrote no marker. I did not audit these reads. |
| 2026-11-04 | The main session wrote and ran `review/stage5_narrow_recheck/bad_close_detection.py`. It reads open closes and the open series, with an assertion that all dates are from 2018-05-01 onward, and it prints counts and rates. |
| 2026-11-05 | The main session applied the user's choice for the no-forward check, notes N1 to N3, and the S2 tests. It read this file, the fourth report, and `run_tests_once.py` on screen, so it saw the same dates, amount, and disclosure text as the fourth agent. It reran all tests, the rehearsal on 2020-01-01 to 2022-04-30 with the new runner and with the runner in `review/pre_fix2_backup/`, and the 73 open windows. `review/stage5_fix3/check_new_rule.py` read open closes and the open series, with the same date assertion. `review/stage5_fix3/mutate_fix3.py` ran tests on a copy with synthetic data. The tests and rehearsals parsed the files named in the 2026-11-04 fix round entry. No locked value was shown or written. No marker, run record, or result exists. |

## Stage 4 frozen rules

The user approved these rules on 2026-11-04. The code is in `stage4_rules.py` and `run_tests_once.py`. All rules apply to 2016-01 to 2018-04 only. The period 2018-05 to 2026-10 gets the descriptive report `reports/stage4_descriptive.md` and no verdict.

**User decisions:** Stage 5 stays in the plan, and the user accepts its low power and limits. Clark-West is a label. The negative outcome is "Smaller than .37". The user states no contact with 2016-2018 prices. The user accepts the method rules.

| Rule | Text |
|---|---|
| Rule 1, decides the verdict | `b` on `log_iv2` in HAR+IV has a lower bound above zero in both percentile bootstrap intervals: 21-session and 63-session blocks, 2,000 resamples, 2.5th and 97.5th percentiles |
| Rule 2, label | Clark-West on log loss without a level factor, HAR nested in HAR+ATM30, 21-session blocks, t above 1.65 on at least 180 scored rows. It adds "also out-of-sample" |
| Rule 3, label | The QLIKE difference of HAR+ATM30 minus HAR with the Duan factor has a 97.5th percentile below zero. It adds "with usable gain". The no-factor result and mean forecast over mean target are reported beside it |
| Training and scoring | Both models train on the same `primary` rows, and each target window ends on or before the origin. No row needs a GARCH or EWMA value. Scoring starts at position 252, with at least 126 training rows |
| Data floor | At least 300 valid origins. Divide the sessions from the first valid origin into consecutive 21-session spans. At least 20 spans hold 10 or more valid origins. These 20 spans do not need to be adjacent. A short last span counts if it holds 10. Step A checks the floor from option days, and Step B checks it again |
| Input stop | After the closes load and before any result, compare the near forward with the close, as an absolute log gap. The run stops if the median is above .02, if more than 5% of rows are above 5%, if the largest gap is above .15, or if more than 3 sessions are in one source only. A close on a session with no near forward is compared with the nearest forward on each side and with the adjacent close on each side. The run stops only if the smaller forward gap and the smaller close gap are both above .15. A session at the edge uses its one side. The largest forward gap on the 287 open sessions is .098, and 1 of 2,104 open closes is above .15 from both adjacent closes. The user chose the close condition on 2026-11-05, because blank days placed at random gave false stops in 16.7% of 585-session windows, and 0.0% with the condition. **Known limit:** this check is weaker on small errors, and two adjacent bad closes that agree do not stop it. These data faults also stop the run: no bar, two bars on one date, a close that is missing or not positive, and an ex-date that is not a session. The screen names the failed check, with no date and no value. See "Input stop end path" |
| Input stop end path | The run sets the status `input_stopped`, calculates no result, and keeps only the dates of the failing rows in the run record. A person reads these dates, with no values, and looks for a bug. If a bug caused the stop, the crash fix applies, and a rerun needs a changed frozen file. A fix cannot change the stop limits. If no bug caused it, `--accept-input-stop` writes the final result "Inconclusive, inputs failed". The result records the check and the dates. If a later attempt gives a verdict, its result lists the earlier stops and refreezes, and its disclosure states that a person read the failing dates |
| Outcomes, first match wins | 0. "Inconclusive, inputs failed", only through the input stop end path. 1. "Inconclusive, data floor". 2. "Supported", if Rule 1 passes. 3. "Smaller than .37", if both upper bounds are below .37. 4. "Inconclusive", with the sign of `b` |
| Verdict line | It states the period, the real interval coverage of about 80% to 91%, and "With events only; the ordinary-day question stays open" if "Supported" holds and either no-event interval includes zero. It also states opposite QLIKE signs |
| Disclosure | The result states the user's statement on contact, the printed dividend rows, bar counts, and dates, the code parses that held locked rows in memory, including the local dividend file, the parse of the condition file, the unaudited agent reads, the agent's contact with 2017 prices, the 2017 rights offering and its open gap, the limit of the Alpaca check, and that the test falls before the format break |
| 2017 rights offering | The user decided on 2026-11-04: no cash row. A rights offering ended on 2017-09-26, and its final prospectus supplement says that the rights were not made available to ADS holders. Nobody could read the Nasdaq or depositary records, so a depositary sale of those rights is not excluded. The USD 0.000413 Alpaca item on the same date stays out |
| Events | Events stay in for the verdict. The no-event result has equal rank in the report. The test events are the 2017 PASO (2017-08-13) and the 2017 midterm (2017-10-22) |
| Reported, no effect | Fixed-step samples (22 and 23 sessions), upper bounds against .37 and .525, no-factor QLIKE, Tier 1 only, each event dropped |
| Returns | Alpaca closes and the two dividend rows of `adr_cash_events.csv`. Alpaca passed limits B1 to B6 on open dates, in `reports/stage4_alpaca_comparison.md` |
| Run rules | One result only. A logged fix is allowed until an outcome is displayed or written. After that, a method change makes the period development data. Each attempt and the result record the manifest SHA-256, and each attempt keeps its own Step A counts. The run prints the hash for comparison with the hash that the user keeps, and `--expected-hash` refuses a mismatch before any read |
| Result write | The run writes the result in memory as text before the write starts, so a value that JSON cannot write stays an ordinary crash. From the status `finishing`, no rerun is possible, and the run always prints the line and the disclosure. If the status is `finishing` and `reports/stage5_result.partial` holds valid JSON, that file is the result, and a person can rename it with no change. If no file holds the result, the text that the run prints is the result. **Accepted risk:** the user accepted on 2026-11-04 that a power loss or a hard kill can lose the result in a window of about one millisecond, while the partial file is written. The same holds for an interrupt right after the record says `finishing` |
| Fix before any run | If a marker exists and no run has started, `--after-crash` does not apply. The user can remove the marker, make the fix, run a normal freeze, keep the new hash, and write the marker again. Log this in this file |
| Crash fix | Log the fix in this file. If a frozen file changed, run `freeze.py --after-crash "<note>"`. It keeps a copy of the old manifest, and it keeps the old hash, the new hash, the changed files, and the note in the run record. It refuses if no frozen file changed. It refuses a changed input file unless `--allow-input-change` is passed. Then run with `--crash-fix-note`, which cannot be blank. The first run after a refreeze needs a note. The user keeps the new hash. `freeze.py` refuses this if a result or a partial result exists, or if the result write has started |
| Floor failure in Step A | The run writes option counts to `reports/stage5_step_a.json` and stops with no result, and the outcomes stay unread. A person reads the counts, including the count of sessions with a blank rate. If a bug caused the failure, the crash fix applies. If not, `--accept-floor-failure` writes the final result "Inconclusive, data floor". After a refreeze, the run must repeat Step A before this flag works |
| Floor failure in Step B | This is unlikely, because the two floors matched on open data. The outcome is final. The result file still holds `b` and the intervals, and the verdict line stays correct |

**Details that the plan did not state.** I set these to make the rules run. The user can change them before the unlock, and the freeze must then run again.

| Item | Choice | Reason |
|---|---|---|
| Bootstrap seed | 20261104 plus the block length | The study code and the review checks use this |
| Rule 3 blocks and rows | 21-session blocks, at least 180 scored rows | The simulation used 21-session blocks. Rule 2 and Rule 3 score the same rows |
| Fixed-step minimum | A sample with fewer than 7 rows has no estimate | The regression has 5 coefficients. The simulation used this limit. It does not affect a verdict |
| First return | The first session in 2016 has no return | 2015 is dropped, so no 2015 close enters |
| Cash flags | The test series has no dividend or rights flags | They need outcome data in Step A, and they do not enter a verdict |
| Sessions in one source only | The run stops if more than 3 sessions are in one source only. The count is in the result | The user changed this detail on 2026-11-04, after the independent check. The limit equals limit B1 |
| Stock mid | The test series has none. The input stop compares the near forward with the Alpaca close | Nasdaq equity data starts in 2018-05. The user accepted this stop on 2026-11-04 |
| Quote snapshot | `last_quotes` takes the last non-null value of each column, not the last row. So a last row with a null bid keeps an older bid, with the new age | A strict last row changes no `ATM30` value from 2018 to 2023, removes one 2023 day, and changes `b` from .622 to .627 on all rows. Step A counts these rows in `reports/stage5_step_a.json`, because the count for the test period is unknown |

## Stage 2 rules

These rules fill gaps in `PLAN.md`. They are development choices until the freeze.

| Item | Rule |
|---|---|
| Snapshot | Last quote per contract from 09:30 to 15:45 New York. The primary series needs a quote age of at most 30 minutes. |
| Half days | The market closes before 15:45, so `ATM30` is missing on these days. |
| Valid pair | The call and the put at one strike both have 0 < bid <= ask. |
| Forward | Parity at the two-sided strike with the smallest absolute C - P. |
| Term IV | Black on the discount-adjusted call-put average. Linear interpolation of IV in log strike between the two strikes nearest the forward. |
| Strike limit | Each strike is at most 25% (absolute log distance) from the forward. |
| Tier | Tier 1 has a bracketed forward, or a strike at the forward, on each term. Tier 2 has one strike on at least one term. |
| Terms | The two listed expiries that bracket 30 days. A failed expiry makes the day missing. Expiry time is 16:00 New York. |
| Rates | `DGS1MO` and `DGS3MO`, continuous, linear in days, flat outside 30 and 91 days. Each session uses the last observation before that session. |
| `MF30` | Black total vol at OTM mids, PCHIP in log-moneyness, flat wings, 4,001 grid points. At least 2 quotes per wing on both terms. |

Sensitivity variants: `atm30_floor7`, `atm30_usable`, and `atm30_session_last`.

## Stage 3 rules

These rules fill gaps in `PLAN.md`. They are development choices until the freeze. Items marked "after results" came after contact with the results, so they are not clean tests.

| Item | Rule |
|---|---|
| RV30 | Squared total returns on sessions in (origin, origin + 30 calendar days], times 365/30. A window with no full data stays blank. |
| RV21 | The next 21 sessions, times 252/21. Sensitivity only. |
| Cash | On the ex-date, in the total return and in the overnight part. |
| HAR inputs | Log annualized RV over 1, 5, and 22 sessions through the origin close. The mean daily variance has a floor of 1e-6, because 17 sessions have a zero return. The floor binds on more than these sessions: 40 primary rows, and 2.2% of all sessions. Floors of 1e-8 and 1e-5 are sensitivity runs, and they have almost no effect. |
| Bootstrap | Circular blocks of 21 and 63 sessions on the full session grid, 2,000 resamples, pairs of rows. A block length is not used if fewer than three blocks fit. |
| Newey-West | 21 lags. Comparison only. |
| Non-overlapping samples | 21 offsets from the first valid session. The next origin is the first valid session on or after the end of the current window. Offsets can merge, so the report counts distinct samples. The offset start came after results, as a bug fix. The review found a design flaw: paths merge. `reports/stage3_findings.md` has fixed-step checks. The code does not have them yet. |
| Instruments | IV lagged 1 and 5 sessions on the session grid, compared on identical days. The identical-day rule came after results, as a bug fix. The review found that lag 5 is probably not valid for this purpose. |
| Training rows | A row needs a target window that ends on or before the origin date. Common training days in each race. This choice drives results: it drops 2018-06 to 2019-04 from HAR in the calibrated race, and it moves the QLIKE gain from -.043 to -.077 on the same rows. The training start is open for Stage 4. |
| Forecast start | Position 252. Calibrated models also need 126 training rows. |
| Calibration | OLS in logs, refit at each origin, with a Duan smearing factor. |
| No smearing | The same race without the factor. After results. |
| EWMA | Lambda .94, times the sessions in the target window. |
| GARCH | Zero-mean GARCH(1,1), normal errors, refit every 21 sessions. A failed fit keeps the prior parameters. |
| GARCH with t errors | The same, with Student-t errors. After results. |
| Drop PASO in the race | Scored origins with 2019-08-12 in the target window. After results. |
| Events | The two expiries with IV that straddle the first session after the election. The observation is the last session where the near expiry is at least 7 days away, within 60 days of the event. |
| Placebos | Multiples of 28 days up to 12 steps each way, with an expiry gap within 7 days of the event, and no listed event from the observation to the far expiry. No p-values. |
