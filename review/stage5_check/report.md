# Stage 5 check: independent review before the one-time test

Written 2026-11-04. An independent agent wrote this text. The harness did not let the agent write files of this kind, so the main session saved its returned report here without a change to the findings. Scripts and outputs are in this folder. `run_out/` and `s04_atm30_frozen_vs_strict.parquet` hold files derived from licensed data, so keep them local.

## Verdict: Ready after listed fixes

The rules and the calculations are correct in the code. I recomputed them with separate code on open data, and they match. The gate held in every attack that I tried.

The problems are in the failure paths:
- A wrong input can give a clean, wrong verdict with no warning.
- A plain bug can end the test with a final "data floor" result.
- The crash rule cannot run as written.
- One floor rule in `PROTOCOL.md` has a second reading that the code does not follow.

All frozen-file fixes can go in one new freeze. No marker exists now, so `freeze.py` permits this. After my work, I confirmed that there is no marker, no run record, no result file, and no `data/test`. All 29 code and rule files still match the manifest.

## Contact with locked data

No locked value was shown or written. These reads did touch locked rows or names:

- **Accidental, in memory only:** `s07_runner_open.py` calls `pd.read_csv` on the full `data/adr_cash_events.csv`, and then filters to open dates. So the two locked dividend rows were in memory for a moment. The script prints nothing from them. I should have used `load_cash_events` only. I did not stop when I saw this, because it happened in an earlier script and I noticed it when I wrote this report.
- **Same parse through study code:** `load_cash_events` on open dates, `test_cash_events_are_gated_and_filtered`, and `test_event_counts` parse the full file. The tests print no rows.
- **Permitted names:** `s02_member_names.py` read zip member names for 2016-01 to 2018-04. It read no member and no file size. It printed one result: the day sets match the NYSE calendar, with 585 days in each zip.
- **Header only:** I read the first line of `data/source/fred_rates_test.csv`: `observation_date,DGS1MO,DGS3MO`.

I did not open the Alpaca file or the corporate actions file. I did not call `load_alpaca_closes` on the real file. I wrote no marker. Log these reads in the access log at the next freeze (see S4).

## BLOCKER

**B1. A wrong option map or a bad close gives a clean, wrong verdict. CONFIRMED by injected faults.**
- Where: `run_tests_once.py:70-80`. `PROTOCOL.md:83` removes the forward-to-stock check.
- Scenario: The 2016-2018 archive maps some instrument ids to wrong symbols, or Alpaca has one bad close. Nothing stops the run. `HANDOFF.md:33` states that the archive layout is untested.
- Evidence (`s08_silent_faults.out`, window 2018-05 to 2020-08):

| Run | Floor | b | Outcome | Median abs. log(forward / close) | Largest |
|---|---|---|---|---|---|
| Clean | Pass | .685 | Supported | .0031 | .079 |
| Definitions on wrong ids | Pass | -.012 | Smaller than .37 | .389 | 1.68 |
| One close 50% too high | Pass | -.083 | Inconclusive | .0031 | .406 |

- These are injected faults. They are not evidence that the archive has such a fault. They show that the run cannot detect one.
- Fix: In `step_b`, after the closes load and before `evaluate`, compare `near_forward` with `close`. Raise an error with no values if any of these holds: the median is above .02, the share above 5% is more than 5%, or the largest gap is above .25.
- Basis: The open panel has yearly medians of at most .0046, 6 of 1,817 rows above 5%, and a largest gap of .087. The check returns only pass or fail, so no outcome appears. A false stop is safe, because the crash rule then applies. The limits are a proposal, and the user must accept them.
- Freeze: Yes. `run_tests_once.py`, `PROTOCOL.md`, and a new unit test change.

**B2. A bug can become the final result "Inconclusive, data floor", and no evidence stays. CONFIRMED.**
- Where: `run_tests_once.py:140-146`, `:59`, `:126`. Also `build_snapshot.py:69-70`, which drops unmatched quotes in silence.
- Scenario: Blank rates or unmatched definitions give no `ATM30` and no crash. The floor fails, the result file is written, and every later run is refused. No outcome was read, so the test is lost for no reason. Step A keeps no reason counts, because `step_a` discards `diagnostics` and the status column stays in memory.
- Evidence: `s08_silent_faults.out` case B (0 `ATM30` days, status "no pair within the strike distance" on 531 days, no crash). `s11_edges.out` (all quotes unmatched gives no crash). `s06_run_procedure.out` part D (a rerun with a fix note is refused, and only the result and the run record exist).
- Fix:
  1. Write `reports/stage5_step_a.json` before the floor decision. It holds options data only: status counts by year, tier counts, unmatched quotes, other roots, rows per session, null-bid share, and first and last bars.
  2. On a floor failure, stop with the status `floor_failed`, and do not write the result file.
  3. Add a flag `--accept-floor-failure` that writes the final result after a person reads the counts.
- This agrees with the crash rule in spirit, because no outcome data was read. `PROTOCOL.md` must state it.
- Freeze: Yes.

**B3. The crash rule cannot run as written. CONFIRMED.**
- Where: `run_tests_once.py:129`, `:132`, `freeze.py:58-68`.
- Scenario: Step A crashes on the archive layout. The refusal text says "Log the fix in PROTOCOL.md". This edit, or any code fix, changes a frozen file, so the manifest check refuses the run. `freeze.py` also refuses, because the markers and the run record exist. The only ways through are to delete the markers and the run record, or to edit the manifest by hand. Each one destroys part of the audit trail.
- `test_crash_shows_no_value_and_needs_a_logged_fix` does not find this, because it injects a manifest check that always passes.
- Evidence: `s06_run_procedure.out` part A.
- Fix:
  1. Add `freeze.py --after-crash "<note>"`. It refuses if a result file or a `.partial` file exists, or if the record status is `finished`.
  2. It writes a new manifest, and it appends the old hash, the new hash, and the note to the run record.
  3. It prints the new hash for the user to keep.
  4. `run_test` then needs the note, as it does now.
- Freeze: Yes. `freeze.py`, `run_tests_once.py`, and tests change.

**B4. The overriding text of the floor differs from the code, and the difference changes outcomes. CONFIRMED.**
- Where: `PROTOCOL.md:64` says "at least 20 consecutive 21-session spans hold 10 or more". `STAGE4_PLAN.md:40` divides the sessions into consecutive spans and needs any 20 filled spans. `stage4_rules.py:57-59` follows the plan. `PROTOCOL.md` overrides the plan.
- Evidence: `s12_floor_readings.out`. On 55 open 28-month windows, all 55 pass in the code, and 38 pass if the 20 filled spans must be adjacent. So the two readings differ on 17 windows. The test has about 26 spans.
- Fix: Change the `PROTOCOL.md` text to "Divide the sessions from the first valid origin into consecutive 21-session spans. At least 20 spans hold 10 or more valid origins". This matches the plan and the code. The user confirms the reading.
- Freeze: Yes. `PROTOCOL.md` changes.

## SHOULD FIX

**S1. A failed rename leaves the outcome in `.partial` and permits a second run. CONFIRMED by a patched rename.**
- Where: `run_tests_once.py:99-103`, `:126`, `:161`.
- Scenario: `partial.replace(path)` fails, for example because another program locks the file. The write is outside the `try`. `stage5_result.partial` holds the full outcome, the record stays `started`, and `result_path.exists()` is false. A rerun with a note runs Step B again.
- Evidence: `s06_run_procedure.out` part B.
- Fix: Refuse a run if the `.partial` file exists. Treat the write failure as "an outcome may exist".
- Freeze: Yes.

**S2. A failure while saving frames hides the verdict line and can print values. CONFIRMED by an injected failure.**
- Where: `run_tests_once.py:164-166`.
- Scenario: `save_frames` runs before the prints and outside the `try`. If it fails, the line is not printed, the frames are lost, and the raw error message reaches the screen. The result file is safe, and the record is `finished`.
- Likelihood: Low. The frames write without error on open data (`s07_runner_open.out`).
- Fix: Print the line and the disclosure first. Put the save in its own `try`, and print `safe_error` only.
- Freeze: Yes.

**S3. A date mismatch between Alpaca and the options does not stop the run. CONFIRMED by a mistake in the check itself.**
- Where: `run_tests_once.py:79`, `PROTOCOL.md:82`.
- Evidence: The first `s07` run stamped synthetic bars at 04:00 UTC, so winter bars fell on the prior New York date (`s07_accidental_date_shift.out`). The run reported 43 sessions in each source only, and went on. b moved from .685 to .644, and the outcome moved from Supported to Inconclusive.
- Likelihood: Low on the real file. The real reader handles time zones, and limit B1 passed on open dates. The counts also agree: 2,689 bars minus 2,104 open sessions is 585, which is the session count of the period.
- Fix: Stop before the outcome if sessions in one source exceed 3, which is limit B1. This changes a detail that the user accepted, so the user decides. It belongs with the B1 guard.
- Freeze: Yes.

**S4. The disclosure and the access log are incomplete. CONFIRMED by reading.**
- Where: `run_tests_once.py:43-44`, `PROTOCOL.md:38-50`.
- The disclosure names only the debate agents. The access log also lists two review agents with unaudited reads, and this check is not logged yet. The disclosure omits the Stage 4 parse that held locked rows in memory.
- Fix: Say "The agents report...", and name the memory parse. Add this check to the access log.
- Freeze: Yes.

**S5. Nothing ties the run to the hash that the user keeps. CONFIRMED by reading.**
- Where: `run_tests_once.py:132-135`, `:153`.
- The run trusts the manifest in the folder. Neither the record nor the result holds the manifest hash, so the hash outside the folder is never compared.
- Fix: Write the manifest SHA-256 in each attempt and in the result, and print it at the start. The user compares it with the kept hash.
- Freeze: Yes.

**S6. The approval instruction is incomplete. CONFIRMED.**
- Where: `HANDOFF.md:150-153`.
- The file names of the markers are only in `PROTOCOL.md:21`.
- It does not say to write the options marker first. With both markers present, Step B follows Step A with no pause, so the user cannot read the Step A counts.
- A template value `"approved_on": "YYYY-MM-DD"` opens the gate (`s06_run_procedure.out` part E).
- A marker with a BOM or in UTF-16 is refused, and Windows PowerShell 5 can write these. This is safe, but the refusal message does not say why.
- Fix: In `HANDOFF.md`, state the two names, the order (options marker, read Step A, then outcomes marker), an exact command that writes plain UTF-8, and the hash comparison. Optionally require an ISO date in `marker_opens`.
- Freeze: `HANDOFF.md` is outside the manifest, so no. The `config.py` option needs a freeze.

## NOTE

**N1. `last_quotes` takes the last non-null value of each column, not the last quote. CONFIRMED, with no effect on values before 2024.**
- Where: `build_snapshot.py:38`, `PROTOCOL.md:91`. No unit test covers this function.
- A row with a null bid keeps an older bid, with the new age (`s04_last_nonnull.out`, part 1).
- A strict last row changes no `ATM30` value from 2018 to 2023, and it removes one 2023 day. It changes 2 days in 2024, 26 in 2025, and 7 in 2026. It removes 9 primary rows. b moves from .622 to .627 on all rows, and from .5252 to .5244 before 2025-03.
- Null bids in the last row are 0 from 2018 to 2022. The test period is unknown, so count them in the B2 file.
- Do not change the rule unless the user wants a full rerun of Stage 3. Record the difference in `PROTOCOL.md`. A change to this record needs a freeze.

**N2. The coverage statement holds, but its lower end is generous.** `stage4_rules.py:165` says about 85% to 91%. `a2_sim` gives 85.0% to 91.2%, and the judge run gives 84% to 92%. `a7` gives 80% to 90%, with 80% at b = .37 on 240 replications. "About 80% to 91%" is more careful. Freeze if changed.

**N3. If the floor fails in Step B only, the result file still holds b and all intervals.** The verdict line stays correct. This is unlikely, because the Step A and Step B floors matched on open data.

**N4. Corporate events in 2017 are not checked. PLAUSIBLE.** `build_inputs.py:56` requires that Alpaca lists only the 2025 rights event. The agent recalls a 2017 GGAL share offering, but it did not check for a rights ex-date, because that needs locked-period information. If one exists, its effect is one return. The user can check this outside the study.

**N5. `load_data.py:78` says no other code opens the Alpaca file.** `alpaca_layout.py` parses it with no gate, `freeze.py` hashes it, and `build_inputs.py` copies it. None shows a value. The text is wrong, but there is no leak.

## Areas with no problem

- **Rule 1, Rule 2, Rule 3, outcome order, verdict line:** They match `PROTOCOL.md`. Seeds, 2,000 resamples, and percentiles reproduce exactly with separate code (`s07_runner_open.out`).
- **Targets and inputs:** Separate loops match `rv30` and `log_rv1/5/22` to about 1e-14, including blanks. The first HAR row is position 22. The first return is blank.
- **Training and scoring:** The first scored row is position 252. The latest training window ends on or before the origin, and a separate forecast is equal.
- **Default wiring:** `run_test` passes the locked dates, the right markers, the test rates, and `TEST_EVENTS` (`s06` part F).
- **Gate:** No marker, a wrong scope, a directory as a marker, and a 2018-04-30 start are all blocked (`s11_edges.out`). `--rehearse` always passes no marker. No code reads a marker by default.
- **Leakage to the screen:** Step A prints counts only. A crash inside the `try` prints the type and the code locations only.
- **Later data:** Closes, cash, and rates end at the test end, by filter or by the fetch limit. In `data/`, `reports/`, and `review/`, parquet and CSV files with a named date column hold no rows before 2018-05. The one exception is `fred_rates.csv`, which holds Treasury rates from 2018-01 and does not enter the test.
- **Archive names:** There are 585 days in both option zips, with no weekend, no holiday, and no gap. The regex and the strict zip are safe. Nasdaq zips start on 2018-05-01.
- **Empty days and bad symbols:** An empty day gives a missing `ATM30`. A non-OSI symbol gives a safe crash.

## False alarms ruled out

- **Simulation rows.** `a2_sim` keeps rows whose window ends after the frame end, so it has 2% to 4% more rows than the frozen code. With frozen rows and functions (`s10_sim_frozen.out`, 399 draws, 600 replications per true b):

| True b | "Supported", frozen | "Supported", plan | "Smaller than .37", frozen | "Smaller than .37", plan |
|---|---|---|---|---|
| 0 | 3.5% | 4.0% | 42.2% | 39.8% |
| .37 | 32.3% | 34.8% | 4.8% | 4.8% |
| .62 | 65.3% | 65.5% | 0% | .2% |

  The differences are within simulation error.
- **Adjusted Alpaca prices.** The loader does not read the `adjustment` parameter. But closes equal the official closes on all but 7 of 2,104 open sessions, across the open dividends. So the file is not dividend-adjusted on open dates.
- **Saturday expiries in January 2016.** The first valid origin is about 2016-02-04, after that expiry.
- **`MF30` failure on old chains.** A failure there gives a safe crash, and `MF30` does not enter a verdict.

## HANDOFF.md claims

All checked claims hold: 123 tests pass. The manifest SHA-256 matches `63deb90f...`. All 29 code and rule files match the manifest, and there is no extra `.py` file. 20 of 20 Stage 3 outputs are unchanged. `index_series.parquet` and `atm_terms.parquet` are byte-identical to the backup. The 13 reconciliation values match after rounding. Closes differ on 7 of 2,104 sessions, with a largest gap of 16.96 bp. The rehearsal covers 587 sessions, with a matching series.

## Order of the fixes

1. Get the user's decision on the B1 limits, S3, and the reading in B4.
2. Apply B1 to B4 and S1 to S5, with unit tests. Add a crash-path test that uses the real `verify_manifest`.
3. Run the tests and the rehearsal again.
4. Log the changes and this check in `PROTOCOL.md`, and run `freeze.py`.
5. Update `HANDOFF.md` with the new hash and S6. The user keeps the new hash.

None of these fixes reads locked data. They change no verdict rule, except for the text correction in B4 and the new stops in B1 and S3.

## What was not checked

- Any content of the 2016-2018 option files, rates, cash rows, or Alpaca bars. So chain quality, coverage, the floor result, and null-bid counts in the test period stay unknown.
- SHA-256 of the five input files in the manifest, because hashing opens them. Only their modification times were checked against the manifest.
- `condition.json` in the option zip, because it has rows for locked dates. Degraded days do not affect the rules.
- `to_df` on an empty DBN member. Only empty frames after the decode step were tested.
- A run of `run_test` with real markers and real zips. The parts ran separately: markers on temporary paths, and steps on open dates.
- Whether the agents' reads in earlier stages stayed in the open period.
- The proposed fixes themselves. The agent edited no project file and did not test the B1 limits inside the code.
