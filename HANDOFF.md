# Handoff: GGAL ADR 30-day implied volatility study

Last updated 2026-11-05. Read this page first, then `PROTOCOL.md`, then `review/stage5_check/report.md`. `STAGE4_PLAN.md` and `PLAN.md` hold the background. `PROTOCOL.md` overrides both where they differ.

## Start here

**Current position (2026-11-05): Stage 5 is finished. The one result is "Inconclusive", with a positive sign of `b`.** Do not rerun the test. The run refuses a second run. After this result, any method change makes 2016-01 to 2018-04 development data.

**Result (`reports/stage5_result.json`):**

| Measure | Result |
|---|---|
| Verdict line | Inconclusive. 2016-01 to 2018-04 only. The "95%" intervals really cover about 80% to 91% in simulation. The sign of b is positive |
| `b`, with events, 455 origins | .281. Interval -.209 to .845 (21-session blocks), -.232 to .937 (63-session blocks) |
| `b`, no events, 418 origins | .351. Interval -.121 to .916, and -.168 to .925 |
| `b`, Tier 1 only, 245 origins | .411. Interval -.110 to 1.162, and -.026 to 1.367 |
| Fixed-step mean `b` (22 and 23 sessions) | .396 and .384. Median t .69 and .64 |
| Clark-West, 271 scored rows | Mean -.0041, t -.30 and -.27. No "also out-of-sample" label |
| QLIKE, HAR+ATM30 minus HAR | Duan .0066 (-.0082 to .0249). No factor .0113 (-.0065 to .0332). No "usable gain" label |

**Reading:** Rule 1 fails, because both lower bounds are below zero. "Smaller than .37" fails, because the upper bounds are .845 and .937. So the test does not show information, and it does not rule out the development sizes (.37, .525, or .622). Do not write "no effect". The out-of-sample results show no gain in this period, and their intervals also include zero.

**How the run went:** The input stop did not fire, and the run has 2 attempts: Step A only, then Steps A and B. `reports/stage5_console.txt` holds the screen output.

**Process facts for the write-up:**
- The user said "Lets continue to Step B". The session read this as approval, and it wrote the outcomes marker.
- The session compared the manifest with the hash that it printed at the freeze. The user has not confirmed a match with their saved copy.
- The Step A and Step B runs are not in the access log in `PROTOCOL.md`, because an edit would change a frozen file.
- The session added the backward-test limit to `writeup/` and this page before the run.

**Stage 6: drafts are written.** The final report drafts are `writeup/GGAL_study_plain_final.pdf` and `writeup/GGAL_study_technical_final.pdf`. The user has not reviewed them yet. The papers from before Step B are out of date: they are in `writeup/status_before_step_b/`, and `writeup/GGAL_study_technical_version.pdf` is one more copy that a program held open, so it can be deleted. The user still needs to compare their saved hash. The references were verified on 2026-11-11.

**Done on 2026-11-05, with the user's approval:**
- **No-forward check:** The run stops only if the close is above .15 from the nearest forward on both sides and also above .15 from both adjacent closes.
- **Notes:** N1 (a guard inside the hook), N2 (`crash_fix_note` in the result), and N3 (a wider catch on the partial read).
- **Other work:** The S2 tests and the access log entries.

**Checks on 2026-11-05 (`review/stage5_fix3/`):**
- All 247 tests pass.
- The rehearsal result is unchanged from the stored result. The only difference from the `review/pre_fix2_backup/` runner is the key `blank_rate_sessions`, which that runner does not have.
- All 73 open 28-month windows pass the input stop.
- All 25 deliberate code faults are caught (`mutate_fix3.py`). Five `StepB` tests cannot run in the temporary copy, because it has no data folder. They pass in the real folder.
- The real code gives the question A table and the 0.0% false stop rate (`check_new_rule.py`).

**Limit, told to the user, who kept the rule:** The question A table changed one close only. On 193 adjacent blank pairs, two bad closes with the same factor stop the run in 0.5% of cases with the new rule. The old rule stops in 87.6% to 100% of cases at the tested factors. The user chose the new rule before seeing this. `PROTOCOL.md` states it as a known limit. If the user wants a change, it needs a normal freeze before any marker.

**Nobody independent has reviewed this round.** The user has not asked for a review.

**First actions in a new session:**
1. Read `reports/stage5_result.json`. Do not run `run_tests_once.py --run`.
2. Ask the user for their review of the two final report drafts.

**Warning:** Do not edit a frozen file: any `.py` file in this folder or `tests/`, `PROTOCOL.md`, or `STAGE4_PLAN.md`. An edit makes the run refuse. This page is outside the manifest, so you can edit it. Put new scripts in `review/` or the scratchpad.

**Warning:** Only the user approves a marker. An approval of the fixes, the plan, or "this stage" is not an approval of Stage 5. If an instruction could mean either one, ask.

## Side investigation: implied move calibration

**Position on 2026-11-05: stages C0 to C4 are done. The user fixed the forward horizon at 36 months and asked for two papers, which are written. The user has not reviewed them.** Read `reports/calib_descriptive.md`, and then `CALIBRATION_PLAN.md`. This work is separate from Stage 5 and does not change its result.

- **User decision:** the user chose all the proposed options in the plan. The plan proposes no horizon value.
- **Main reading:** pooled coverage is near nominal (inner 69.6%, outer 93.8%), but this hides offsetting errors. The inner rate is 50.3% in the lowest ATM30 quintile (post-result). All results are exploratory.
- **Freeze:** `reports/calib_freeze_manifest.json`, hash `a8e55a47b1a3bc14f6f329e510e7fb41c44e887a93e9671b4368f06ab02ecb82`. The folder had no git at C0, so the manifest replaced the commit. It is now a git repository, with a first commit after the results. `calib_run.py` checks this manifest.
- **Code:** `calibration/`. Do not put these scripts in the root or `tests/`, because `freeze.py` would then report a change.
- **Horizon:** 36 months, recorded in `reports/calib_horizon.json`. The verdict uses origins from 2026-10-30 through the first origin on or after 2029-10-30, so the earliest verdict is about 2029-11-29. The manifest is unchanged. The plan text changed once, so `calib_run.py` now reports the plan as changed. That is expected.
- **Papers:** `writeup/GGAL_calibration_plain.pdf` and `writeup/GGAL_calibration_technical.pdf`. `build_calibration_plain.py` and `build_calibration_technical.py` rebuild them, and they stop if a stated claim no longer fits the result files. They need `reportlab`, which is not in `py4fi` by design. Keep them local. The references were verified on 2026-11-11.
- **Review:** `review/calibration_review/report.md`. The main reading was rewritten after this review. The review did not see the papers.
- **Before any forward run:** fix `forward_verdict`, and write a loader for dates after 2026-10-29. See the post-result log in `CALIBRATION_PLAN.md`.
- **Not run:** the American-exercise cut, because the tree sensitivity is not done.
- **Stage 6 drafts:** the calibration results are not in them. The drafts still wait for the user's review.

## Status

| Stage | Status |
|---|---|
| 1. Data check | Done, except the full row-count reconciliation |
| 2. Build series | Done |
| 3. Development analysis | **Done. The user has read the results** |
| 4. Freeze | **Done. Latest freeze on 2026-11-05. Steps 2 to 9 of `STAGE4_PLAN.md` are complete** |
| 5. One-time test, 2016-01 to 2018-04 | **Done on 2026-11-05. Result: Inconclusive, positive sign** |
| 6. Write-up | **Drafts written on 2026-11-05. The user has not reviewed them** |

All 247 unit tests pass on the frozen code. All results are exploratory.

## Where we left off

**This section describes the freeze of 2026-11-04, before the later fix rounds.** The rules are in `PROTOCOL.md`, and `reports/freeze_manifest.json` holds the hashes. The current manifest hash is `9214a2205f7a6078af41c3d8650b77a1d53bfa772bf14228be6d9d21ae883abc`. The hash `696fb7f0...cca27` is out of date.

No unlock marker exists, the test has not run, and no 2016-2018 value was shown. See the access log in `PROTOCOL.md`.

**Checks on 2026-11-04:**
- The rerun of `run_development.py` left all 20 compared Stage 3 outputs unchanged. `review/compare_rerun.py` runs this comparison.
- The rebuild of `build_series.py` gave byte-identical series and term files.
- The new study code matches all 13 values from `review/verify_debate.txt`, after rounding. See `reports/stage4_descriptive.md`.
- Alpaca passed limits B1 to B6 on open dates. Closes differ on 7 of 2,104 sessions, and the largest gap is 17 bp. See `reports/stage4_alpaca_comparison.md`.
- The rehearsal on 2020-01-01 to 2022-04-30 ran from start to end. Its series matches the open series on all 587 sessions. It is not evidence for the claim.

**New descriptive result:** On the same-row race, the Duan QLIKE difference is -.0187, with an interval of -.0444 to .0115. The no-factor difference is .0002. Clark-West t is 2.70 with 21-session blocks and 2.07 with 63-session blocks. So the race shows information, but no dependable usable gain.

**Limit:** The code for the test has run only on open and synthetic data. The 2016-2018 archive can have a layout that the code does not handle. Then the crash rule in `PROTOCOL.md` applies.

**Main result:** In-sample, pooled, `ATM30` adds information beyond past RV. The size is not stable: event windows, mainly the 2019 PASO, supply about a quarter of the coefficient. Evidence on ordinary days before 2025-03 is weak. Out-of-sample, the sign favors `ATM30` on later dates, but the size depends on training and level choices, and no dependable forecast gain is shown.

| Measure | Result |
|---|---|
| In-sample b on IV, HAR+IV | .622, 95% interval .337 to .916, on 1,806 origins |
| All listed events dropped | .459 |
| No events, before 2025-03 | .366 |
| From 2025-03, with and without events | 1.190 and .781 |
| Fixed-step non-overlapping samples (review check) | Mean b .61 and .60, without the PASO row .50 and .49 |
| By period | .526 in 2018-2023, 1.185 in 2024-2025, .423 in 2026 (interval includes zero) |
| Clark-West on log loss (review check) | t 5.2, 4.2, and 2.7 across training and row sets |
| QLIKE, HAR+ATM30 minus HAR | -.077 to .000 across smearing, training, and row choices. No value is clean |

**Limit:** `reports/stage3_results.md` still holds the original tables, and `reports/stage3_findings.md` corrects how to read them. `reports/stage3_findings.md` still recommends Clark-West as the information rule. The user chose a label, so `PROTOCOL.md` overrides that text.

## Independent check of the Stage 5 plan

An independent agent returned "Ready after listed fixes" on 2026-11-04. The report is `review/stage5_check/report.md`. On the same day, the user accepted the input stops and the floor reading, and approved all the fixes. They are done, and the hash above is the new freeze.

- **Blockers:** B1 (input stop), B2 (a floor failure is not final until a person accepts it), B3 (`freeze.py --after-crash`), and B4 (floor text).
- **Other fixes:** S1 to S6, the coverage wording, the `last_quotes` record, and the Alpaca reader text.
- **Checks:** All 151 tests pass, including a crash test with the real manifest check. All 20 compared Stage 3 outputs are unchanged. The rehearsal result is unchanged, and the input stop passed on all 73 open 28-month windows.
- **Not tested:** Nobody independent reviewed the fixes. No full run has used real markers and real zips.
- **Rights, now checked:** A rights offering ended on 2017-09-26. The final prospectus supplement says that the rights were not made available to ADS holders, and an agent found no ADS ex-date. It could not read the Nasdaq or BNY Mellon records. That agent saw 2017 prices in filings and search summaries, and it removed them from its report. This contact is not yet in the access log or the disclosure, and the same is true of the contacts in the fix check.
- **Superseded:** "Not tested" above is now out of date. The fix check tested the fixes, and it did not run real markers with real zips.

## Earlier questions for the user

The user answered questions 1 to 3 and chose to hold on question 4. See "User decisions". Question 3 is now settled by the rights check. The next question is the Step A question in "Start here".

1. Do you want to read `reports/stage3_findings.md` before the test? You chose to start the work without a review, and the test cannot be repeated.
2. Did you save the hash in "Where we left off" outside this folder? The session cannot confirm this.
3. Does a rights ex-date exist in 2016-01 to 2018-04? You can check this outside the study. Report only yes or no and the date, with no prices. If one exists, decide how to treat it before any marker. The change would need a new freeze.
4. Do you approve Step A of Stage 5? Only the user can approve it. Step A reads the options and shows counts and the data floor result. The closes and returns stay unread, so no verdict can appear. Step B reads the closes and cash, and it needs a separate approval after the Step A counts.

The session offered two ways to write the options marker: the session writes it with the user's stated approval, or the user writes it with the command under "Commands". The second way keeps the approval record fully in the user's hands.

The 2016-01 to 2018-04 test stays locked until the user decides.

**Note:** Any later method change on the open data is still development. After the one-time test runs, a method change makes that period development data too.

## User decisions

**Project scope:**
- Use the Databento `GGAL` root as given. Do not look for `GGAL1` or adjusted contracts. Do not reopen this item.
- The lockouts of `options-valuation-model` do not apply here. This is a separate project.
- 2026 is open data, not a blind forward test. Report it as a separate period.
- The inputs stay in `databento_ggal_20261031/` and `data/`.

**Stage 4 questions, 2026-11-04:**
1. Power: The user accepts the low power and the limits, and wants Stage 5 in the plan. At a true `b` of .37, the test ends "Inconclusive" about 60% of the time.
2. Clark-West is a label, not a requirement. The verdict "Supported" depends only on the two bootstrap intervals.
3. Contact: The user states "no contact" with 2016-2018 prices. The files cannot prove this, and nobody audited the agents' reads. The access log also shows that the study printed 2016-2018 dividend rows, bar counts, and dates on 2026-11-03, with no prices or returns. The disclosure states this.
4. The negative outcome is "Smaller than .37", not a sign rule.
5. The user accepts the method rules, and approved work steps 2 to 9 of `STAGE4_PLAN.md`. The user chose to start without a review of `reports/stage3_findings.md`.

**Later decisions, 2026-11-04:**
- The user accepted the seven details in `PROTOCOL.md`, then asked for an independent check of the Stage 5 plan.
- After the check, the user accepted the input stop limits (B1), the stop at more than 3 sessions in one source only (S3), and the floor reading of any 20 filled spans (B4). The user approved all the fixes and a new freeze.
- The user has **not** approved Stage 5. No marker may exist before that approval.

**Decisions on 2026-11-05:**
- Question A: The user chose the adjacent-close condition, and answered "yes to your recommendations". The session read this as approval of N1 to N3 and the new freeze as well.
- The user confirmed that they have read the Stage 3 results.
- The user kept the new check after hearing its limit, and approved Step A. Step A ran, and the floor passed.
- The user has **not** approved Step B.

**Answers in the session after the freeze (dated 2026-11-04 by the system clock):**
- Question 1: The user has read the Stage 3 results.
- Question 2: The user has saved the manifest hash outside this folder.
- Question 3: The user leaves the rights ex-date unchecked. The rules stay as frozen, and the item stays open. The write-up must disclose it.
- Question 4: **Hold, no marker.** The user first wrote "you can continue to the test" and selected "Not yet". When asked, the user chose "Hold, no marker". Do not read the first phrase as approval.
- Checks in that session: No marker, run record, or result exists. `freeze.verify_manifest()` passed, and the manifest hash matches.

## Stage 2 summary

`ATM30` has a value on 1,846 of 2,137 sessions (86.4%), from 2018-05-01 to 2026-10-29. `MF30` has 512 sessions from 2024 onward. It is descriptive only. Details are in `reports/stage2_findings.md`.

**Correction from Stage 2:** An earlier statement said that spreads and daily changes roughly doubled after the format break. That was wrong, because a six-month comparison window caused the result. The monthly median spread is .133 in February 2025 and .154 in March 2025, and it rises only from April.

## Files

| Path | Content |
|---|---|
| `STAGE4_PLAN.md` | The approved Stage 4 plan: verdict rules, expected results, and work steps |
| `PLAN.md` | The original design, with a note on later changes |
| `PROTOCOL.md` | **Frozen rules,** decisions, periods, cash events, Stage 2 and Stage 3 rules, access log |
| `stage4_rules.py` | Verdict rules, data floor, intervals, and the same-row race, as pure functions |
| `run_tests_once.py` | The one-time test and its rehearsal |
| `freeze.py` | Writes and checks `reports/freeze_manifest.json` |
| `report_stage4.py` | Writes the descriptive report of the seen data |
| `compare_alpaca.py`, `alpaca_layout.py`, `fetch_test_rates.py` | Alpaca limits B1 to B6, layout helper, and test rates |
| `config.py` | Paths, the markers, and the date gate (`require_open`) |
| `load_data.py` | Databento readers that use the gate |
| `build_inputs.py` | Copies source files, builds cash events and the official daily table |
| `build_snapshot.py` | Decodes the 15:45 snapshot (about 2.5 minutes) and fetches FRED rates |
| `atm_index.py`, `model_free_index.py` | Index calculations |
| `build_series.py` | Builds both series and the coverage report |
| `plot_series.py` | Stage 2 inspection plots |
| `realized.py` | Total returns, RV30, RV21, HAR inputs, overnight split |
| `forecasts.py` | EWMA, GARCH, expanding log regressions, losses |
| `inference.py` | OLS, Newey-West, 2SLS, block bootstrap, non-overlapping samples |
| `events.py` | Event list, forward variance, placebo dates |
| `run_development.py` | Runs all of Stage 3 (several minutes) and writes the reports |
| `plot_development.py` | Stage 3 figures |
| `tests/` | Unit tests |
| `review/` | Scripts and outputs of the Stage 3 review. Start with `review/README.md` |
| `review/stage4_debate/` | Reports, scripts, and outputs of the Stage 4 plan debate. Start with its `README.md` |
| `data/index_series.parquet` | Series, variants, and flags |
| `data/atm_terms.parquet` | IV per session and expiry |
| `data/forecast_panel.parquet` | All inputs, targets, and forecasts by session |
| `data/adr_cash_events.csv` | 33 dividends and the rights value, in USD per ADS |
| `data/equity_official_daily.parquet` | Official closes, 2,137 sessions |
| `data/source/alpaca_ggal_sip_raw.json` | Alpaca bars. Only `load_alpaca_closes` reads the values. Read 2016-01 to 2018-04 only after the unlock |
| `data/alpaca_open_closes.parquet` | Filtered Alpaca closes, open dates only |
| `data/source/fred_rates_test.csv` | Treasury rates of the test, 2015-12-01 to 2018-04-30 |
| `reports/stage4_descriptive.md`, `reports/stage4_*.csv` | Descriptive report of the seen data, with no verdict, and its tables |
| `reports/stage4_alpaca_comparison.md` | Alpaca against official closes, open dates only |
| `reports/freeze_manifest.json` | SHA-256 of the code, the rules, and the inputs |
| `review/stage4_rehearsal/` | Rehearsal output on seen data |
| `review/stage5_fix_check/`, `review/stage5_fix_recheck/`, `review/stage5_narrow_recheck/` | The second, third, and fourth independent checks, each with `report.md` and scripts in `work/`. Keep them local, because some outputs derive from licensed data |
| `review/stage5_rights_check/` | The rights offering check, from public filings. It holds no price |
| `writeup/GGAL_study_plain_final.pdf`, `writeup/GGAL_study_technical_final.pdf` | Final report drafts, with the result. They hold results from licensed data, so keep them local. `build_plain_final.py` and `build_technical_final.py` rebuild them and check the quoted result numbers against the result file. They need `reportlab`, which is not in `py4fi` by design. The session installed it only in its scratch folder. This folder is outside the manifest |
| `writeup/status_before_step_b/` | The status papers from before Step B. Out of date |
| `review/stage5_fix3/` | Scripts and outputs of the 2026-11-05 checks. Keep them local |
| `review/pre_fix3_backup/` | Code, rules, the stored rehearsal, and the manifest from before the 2026-11-05 changes |
| `review/pre_fix2_backup/` | Code and rules from the freeze `696fb7f0...cca27` |
| `review/stage5_check/` | **Independent check of Stage 5:** `report.md`, its scripts and outputs, and `guard_open_windows.py`. Some files derive from licensed data, so keep them local |
| `reports/stage5_step_a.json` | The option counts of Step A |
| `reports/backward_test_run.json`, `reports/stage5_result.json`, `reports/stage5_console.txt` | The run record, the one result, and the screen output. Do not edit them |
| `review/pre_stage4_backup/` | Code and outputs from before Stage 4 |
| `reports/stage3_findings.md` | **Read this first:** findings, limits, and decisions |
| `reports/stage3_results.md` | All Stage 3 tables |
| `reports/stage3_figures.png` | Stage 3 figures |
| `reports/stage3_*.csv` | The same tables as CSV |
| `reports/eviews_regressions.csv` | Export for the EViews regressions |
| `reports/stage2_findings.md`, `reports/stage2_coverage.md` | Stage 2 findings and coverage |

The Databento data is licensed. Do not publish it or commit it. Files derived from it, such as `reports/eviews_regressions.csv`, stay local unless the license permits otherwise.

## Commands

Run these from this folder:

```
conda run -n py4fi python -m unittest discover -s tests -v
conda run -n py4fi python build_inputs.py
conda run --no-capture-output -n py4fi python build_snapshot.py
conda run --no-capture-output -n py4fi python build_series.py
conda run --no-capture-output -n py4fi python plot_series.py
conda run --no-capture-output -n py4fi python run_development.py
conda run --no-capture-output -n py4fi python plot_development.py
conda run --no-capture-output -n py4fi python compare_alpaca.py
conda run --no-capture-output -n py4fi python run_tests_once.py --rehearse 2020-01-01 2022-04-30
```

**Warning:** Run these commands only after the user approves Stage 5. Do not change a frozen file first. A change makes the manifest check refuse the run.

```
conda run --no-capture-output -n py4fi python run_tests_once.py --run
```

**How the user approves:**

1. Compare the manifest hash with the hash that you keep, in PowerShell 7. If they differ, stop.

   ```
   (Get-FileHash reports/freeze_manifest.json -Algorithm SHA256).Hash
   ```

2. Write the options marker, with a real date, in PowerShell 7. This writes plain UTF-8. Windows PowerShell 5 can write a BOM, and the gate then refuses the marker.

   ```
   '{"purpose": "stage5_one_time_test", "scope": "options", "approved_by": "user", "approved_on": "2026-11-05"}' | Set-Content -NoNewline -Encoding utf8NoBOM reports/backward_test_options_unlocked.json
   ```

3. Run the test command, and add `--expected-hash <the hash that you keep>`. A mismatch refuses the run before any read. Step A runs and stops, because the outcomes marker is absent.
4. Read `reports/stage5_step_a.json`. It holds option counts only.
5. To continue, write `reports/backward_test_outcomes_unlocked.json` in the same way, with the scope `outcomes`. Run the test command again, with `--expected-hash`. With both markers present, Step B follows Step A with no pause, so write this marker only after step 4.

The manifest check does not cover the markers.

**If the run stops:**
- **Input stop:** The screen names the check, and the run record holds the failing dates with no values. Read the dates and look for a bug. If a bug caused the stop, use the crash fix. If not, `--accept-input-stop` writes the final result "Inconclusive, inputs failed".
- **Partial result:** If the status is `finishing` and `reports/stage5_result.partial` holds valid JSON, that file is the result. Rename it with no change. If no file holds the result, the text that the run prints is the result.
- **Other stops:** See "Crash fix" and "Floor failure in Step A" in `PROTOCOL.md`.

**EViews:** Load `reports/eviews_regressions.csv` and keep rows with `primary` = 1. Then run `ls log_rv30 c log_iv2` for the MZ regression, and `ls log_rv30 c log_rv1 log_rv5 log_rv22 log_iv2` for the primary regression. Choose HAC (Newey-West) errors with 21 lags. EViews does not count the missing days, so these results match the study only if the rows are treated as consecutive.

**Caution:** Do not pass a multi-line `python -c` string to `conda run`. It crashes conda, and the command then waits at a prompt. Put the code in a script file.

**Caution:** A subagent cannot write a report file here. The harness refuses it, so ask the subagent to return its report as text, and save the text yourself.

**Caution:** Use the default client for FRED. Do not set a browser user agent. The system blocks that, and the plain request works without a key.

## Next step: Stage 6

The drafts in `writeup/` wait for the user's review. The final paper must include American exercise and dividends, missing-day selection, low power, the disclosure text in the result, the backward-test limit, and the process facts in "Start here".

## Open items

- The test is backward. No later price enters it, but the method, the rules, and the .37 limit came after contact with 2018-2026. So it measures fit on unseen older data, and it is not a real-time simulation. The write-up must state this. The user discussed this on 2026-11-05 and continued.
- A forward test on data from after 2026-10-29 would avoid this limit. It is not in the plan, and early results would have low power.
- 2022-07-08 is explained (`audit/AUDIT_REPORT.md`): the near term had one pair at strike 7.5, with wide quotes. The low forward is quote noise. `reports/stage2_findings.md` still lists it as open, and it is outdated.
- The spread gradient has no proved cause, and persistent quote error is untested. See `reports/stage3_findings.md`.
- Nobody can yet separate the 2025 quote format break from a real market change.
- Fixed-step samples, Clark-West, and same-row training are now in the study code. The other review checks (other level rules, 5-minute measures) are not. Their scripts are in `review/`.
- These debate numbers are not reproduced: level b .79 and .22, implied variance above RV in 79%, 729 Tier 1 days (the study has 878 to 2024), and about 1.5 points of the 83% coverage. The plan does not record the debate rules.
- The explanation for pooled log b (a sample that ends in 2024) is not confirmed, and `PLAN.md` has evidence against it. The .97 in 2024 is not explained.
- The plan's `ATM30`/`MF30` ratio of 1.07 is probably inverted. The study has 0.946, and the inverse is 1.057. This is not confirmed.
- The American tree inversion in the plan is not done. It is a sensitivity run for exercise style and dividends.
- The 2016 and 2017 dividends use Alpaca's rate and date, with no record date or tax basis.
- The plan's question to Databento on how early cbbo-1m bars are built has no answer yet.
- Stage 1 did not reconcile the row counts with the decoded inventory.
- This folder is now a git repository, but its first commit (`22368c5`) came after all results. So git does not show that the rules came before the results. `reports/freeze_manifest.json` shows later changes to frozen files, but it does not prevent them.
