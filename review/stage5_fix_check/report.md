# Independent check of the Stage 5 fixes

Written 2026-11-04. An independent agent wrote this text. The harness does not let the agent write report files, so the main session saved its returned report here without a change to the findings. Scripts and outputs are in `work/`, copied from the session scratchpad. Line numbers refer to the freeze with manifest SHA-256 `696fb7f0...cca27`.

## Verdict: Ready after listed fixes

Do not write a marker yet. The rule logic, the gate, and the input stop are correct. The problems are in the failure paths again. Three blockers remain, and all code fixes fit in one new freeze. No marker exists, so a normal `freeze.py` run is still permitted.

Final state of the real folder:
- `reports/` holds no marker, run record, Step A file, result, or `.partial` file.
- `data/test` does not exist.
- The SHA-256 of `reports/freeze_manifest.json` is still `696fb7f0b5597ac0b4615151a22160b8db703d8344dd9a40c4483157eb8cca27`.
- `freeze.verify_manifest()` passed.
- I edited no project file.

The output files are `walk_main.out`, `walk_floor.out`, `faults.out`, `mutate.out`, `real_open.out`, and `real_suite.out`.

## BLOCKER

**1. A failed result write can lose the one test, with no legal way forward. CONFIRMED by injected faults (`faults.out`).**
- **Where:** `run_tests_once.py:166-172` and `:225-229`. `finish` runs outside the `try`, before the prints and the frame save.
- **Evidence:**

| Fault after Step B | Verdict printed | Frames saved | Result text exists | Rerun | `--after-crash` |
|---|---|---|---|---|---|
| Value that JSON cannot write (`pd.NaT`) | No | No | No | Refused | Refused |
| Disk full on the partial file | No | No | No | Refused | Refused |
| Rename fails | No | No | In `.partial` only | Refused | Refused |
| Last record write fails | No | No | Yes | Refused | Refused |

- **Serialization case:** nothing was displayed or written, so the crash rule permits a fix, but the code refuses it.
- **Rename case:** no rule says that a person may read or rename the `.partial` file. A write-then-rename is also a known place for antivirus locks on Windows (PLAUSIBLE).
- **Accept path:** `--accept-floor-failure` also uses `finish`, so it has the same failure path. I read this code and did not inject the fault there.
- **Likelihood:** low. The rehearsal shape writes without error. The cost is the full test.
- **Fix:**
  1. Serialize the result to text before the status changes to `finishing`, so a JSON error stays an ordinary crash.
  2. Retry the rename a few times.
  3. Wrap `finish` in a `try`. Always print the line and the disclosure, and always try the frame save.
  4. Add a rule to `PROTOCOL.md` that a `.partial` file with the status `finishing` is the result.
- **New freeze:** Yes.

**2. An input stop has no end state and no permitted way to diagnose it. CONFIRMED by test for the path. The chance of a stop is PLAUSIBLE.**
- **Where:** `run_tests_once.py:96-109`, `:183-186`, `PROTOCOL.md:67`, `:75`. The earlier report also said that a false stop is safe because the crash rule applies.
- **Scenario:** Step B stops on the largest gap. The stop names the check, with no date and no value. To find the row, a person must see closes, and closes are outcomes.
- **Evidence (`walk_main.out`, steps 10 to 13):**
  - `--accept-floor-failure` is refused after an input stop.
  - A rerun with a note is permitted, with no required change.
  - A real data fault therefore repeats the same stop. The status stays `crashed` with no final result.
- **Other route:** a change to the limits is a rule change after a weak look at the outcome data.
- **Risk:** the limits passed on open data only, and old chains are untested.
- **Fix (the user decides):**
  - Define a final outcome, such as "Inconclusive, inputs failed", or
  - Permit a diagnostic that shows only the dates of the failing rows, with no values. State this in `PROTOCOL.md` before any marker.
- **New freeze:** Yes.

**3. A double fault prints the crash message, which can hold a locked value. CONFIRMED with a real Windows file lock (`faults.out`, case `double`).**
- **Where:** `run_tests_once.py:219-224`.
- **Scenario:** A crash occurs, and the write of the `crashed` record then fails because another program holds the record file. The new exception escapes the `except` block, and Python prints the original exception as its context.
- **Evidence, with a synthetic secret:** `ValueError: close was 987.654` appeared on the screen under "During handling of the above exception". The status stayed `started`.
- **Likelihood:** low. It needs two faults and a message that holds a value. It is still the only path I found that shows a value, and it cannot be undone.
- **Fix:** Put the record write in its own `try`. Print `safe_error` in all cases, and exit with `raise SystemExit(1) from None`. Do the same for the record writes in the Step A stop branches, and add a test.
- **New freeze:** Yes.

## SHOULD FIX

**4. The hash comparison in HANDOFF cannot run before the read. CONFIRMED by test (`walk_main.out`, steps 1 and 2).**
- **Where:** `HANDOFF.md:199`, `run_tests_once.py:187-191`.
- **Scenario:** Step 1 says to compare the hash that the run prints, then write the marker.
  - With no marker, the run refuses and prints no hash.
  - With a marker, the run prints the hash and goes straight into the read.
  - With both markers, the verdict can print before the person compares.
- **Fix:** Before each run, use `(Get-FileHash reports/freeze_manifest.json -Algorithm SHA256).Hash`. Compare it with the kept hash, in any letter case. I ran this command and it gives the correct hash. An optional code fix is an `--expected-hash` argument that refuses a mismatch.
- **New freeze:** No for HANDOFF. Yes for the argument.

**5. `--after-crash` does not record what changed, and it accepts a changed input file. CONFIRMED by test (`walk_floor.out`, steps 8 and 9).**
- **Where:** `freeze.py:96-98`.
- **Evidence:**
  - At status `step_a_done`, with no crash, I changed the frozen Alpaca file in a copy with synthetic data.
  - The freeze passed with the note "no crash at all". The entry holds only two hashes and the note.
  - The old manifest is overwritten, so nobody can tell which file changed.
  - The next run passed with no `--crash-fix-note`, although `PROTOCOL.md:75` requires one.
- **Fix:**
  - Store the output of `differences()` in the entry.
  - Keep a copy of the old manifest.
  - Refuse changes to input files unless a separate flag permits them.
  - Require a note on the first run after a refreeze.
- **New freeze:** Yes.

**6. A failed record write in `--after-crash` loses the old hash. CONFIRMED with a real lock (`faults.out`).**
- **Where:** `freeze.py:97-101`. The manifest is written first, then the record.
- **Evidence:** The manifest moved and the record has no entry. On a retry, old and new hash are equal, and the first hash is not kept anywhere.
- **Fix:** Write the record entry before the manifest, or write a pending entry first.
- **New freeze:** Yes.

**7. `--accept-floor-failure` can finalize stale counts after a code fix. CONFIRMED by test (`walk_floor.out`, steps 5 and 6).**
- **Where:** `run_tests_once.py:192-198`.
- **Scenario:** The floor fails, a fix goes in, and `--after-crash` runs. The person then accepts without a new Step A. The final result holds the old counts and the new manifest hash.
- **Fix:** Refuse if the last attempt's hash differs from the current hash. Also check that the floor in the Step A file has `passed` false.
- **New freeze:** Yes.

**8. A repeat run overwrites the earlier Step A counts. CONFIRMED by test (`walk_floor.out`, step 7).**
- **Where:** `run_tests_once.py:205`.
- **Scenario:** The counts that justified a fix disappear after the fix. The run record does not hold them.
- **Fix:** Also store the counts and the floor in each attempt.
- **New freeze:** Yes.

**9. The Step A counts do not show blank rates. CONFIRMED on open dates (`real_open.out`).**
- **Where:** `run_tests_once.py:61-68`.
- **Evidence:** With blank rates on 2020-05 to 2022-08, the floor fails. The status reads "near: no pair within the strike distance". Nothing names the rates.
- **Risk:** A person can read this as thin data and accept a final floor failure.
- **Fix:** Add a count of sessions with a blank rate.
- **New freeze:** Yes.

**10. The access log has factual gaps. CONFIRMED by reading.**
- `PROTOCOL.md:52` says that these runs load the cash file through `load_cash_events`. But `tests/test_inputs.py:101` calls `pd.read_csv` on the full file, with no gate. So each full test run parses the two locked rows by a direct route.
- `PROTOCOL.md:50` and `:52` omit the Alpaca parse of the rehearsal, through `step_b` and `load_alpaca_closes`.
- The rehearsal and the study code also parse `condition.json`, which holds locked dates (`load_data.py:59-62`, `run_tests_once.py:77`). No gate protects this, and neither the log nor the disclosure names it. It holds conditions, not prices.
- **Fix:** Correct the log, name `condition.json`, and change the test to filter or to avoid the direct read.
- **New freeze:** Yes.

**11. The tests leave parts of the fixes unprotected. CONFIRMED by mutation test (`mutate.out`).** The baseline passes on a copy. Of 45 single changes, 24 were caught and 21 survived.

| Fix | Changes that no test catches |
|---|---|
| B1 | Largest limit .25 to .40, median .02 to .0205, share .05 to .055, gap .05 to .055 |
| B2 | Accept path: no hash in the attempt, no hash in the result, no disclosure, no floor |
| S1 | Status check for `finished` or `finishing` removed in `run_test`. Another check hides each one in the tests |
| S2 | Disclosure not printed, frames saved before the line |
| S4 | Empty disclosure in the result |
| B3 | Status check removed in `after_crash`, `finishing` permitted, `started`, `floor_failed`, or `step_a_done` refused, result check removed |
| B3 | `refuse_after_unlock` removed from the normal freeze |
| Crash rule | Note not required after the status `started` |

- The behavior is correct today, because my walks exercised most of it. The tests would not catch a later regression in these parts.
- The state-machine tests also inject `run_a`, `run_b`, and `save`, and the default wiring has no unit test. The real `step_b`, gate, and manifest paths do have separate tests, so these are not empty tests.
- **Fix:** Add tests for the survivors and pin the guard constants.
- **New freeze:** Yes.

## NOTE

All items below are CONFIRMED unless stated.

- **Bad close below the limit.** On 2020-05 to 2022-08, the clean `b` is .944. One close 20% too high gives 1.227, and one close 25% too high gives 1.246. The run does not stop in either case. Three missing sessions give .892 with no stop. The open maximum gap is .087, so the limit of .25 leaves a wide band. The user accepted this limit, and only the user can change it. A change needs a freeze.
- **A note is not tied to a fix.** `run_test` accepts a whitespace note, and it reruns with no change to any file (`faults.out`). `after_crash` refuses a whitespace note, so the two checks differ.
- **`conda run` changes the note.** `100%` became `100` in `"Fixed reader & bars, 100% (see log)"`. Spaces, `&`, and quotes survive. Tell users to avoid `%`.
- **Accept path output.** It prints the line but not the disclosure (`run_tests_once.py:197`). The disclosure is in the result file. A note passed with the accept flag is dropped.
- **Guard message.** The stop names which check failed. `PROTOCOL.md:67` says "pass or fail only". No value is shown, so I consider this acceptable. Repeated refreezes with new limits could bisect a gap, but each one leaves a record.
- **Stale text in frozen files.** `stage4_rules.py:48` still says "20 consecutive 21-session spans", which is the reading that B4 rejected. `build_snapshot.py:34` says "Last row". `STAGE4_PLAN.md:149` still says that a Step A floor failure is the verdict. `PROTOCOL.md` overrides the plan. `PROTOCOL.md` also does not state that a short last span can count. Fix these in the same freeze if one runs.
- **Normal freeze.** `refuse_after_unlock` does not list the Step A file or the `.partial` file (`freeze.py:79`), by reading. This matters only if a person deletes the markers and the record. It is part of the known limit that the manifest shows a change but does not prevent one.
- **False alarm ruled out.** All-negative forwards pass the guard as NaN gaps. This cannot occur in the real path, because `near_forward` exists only on status `ok` days, and `atm_index.py:107` rejects a non-positive forward.
- **Open item from HANDOFF.** The possible 2017 rights ex-date stays unchecked. I did not look at it.

## Fixes that I found correct

- **B1:** The guard runs before `evaluate`. It stopped on these faults through the real code on open dates:
  - One close 50% too high.
  - Closes halved.
  - A wrong map on 100%, 10%, and 3% of days. The check that fired was median, share, and largest, in that order.

  It made 0 stops on 73 open windows. My separate calculation matches: 1,817 rows, median .0036, largest .0874. Messages hold no value.
- **S3:** Three missing sessions pass, and four stop, through the real `step_b`. A shifted date gives a safe crash from the cash check.
- **B2:** The Step A file is written before the floor decision, and it holds only counts, status strings, and bar times. I scanned the file on real open data, and no float in it matches a close, a forward, or an IV. A floor failure gives `floor_failed` with no result and no Step B. The accept path works, is final, and needs that status. See items 1 and 7 for the limits.
- **B3:** The full cycle ran through the real command lines on a copy with the real manifest check: crash, refusal, mismatch, `--after-crash`, and rerun. All refusals fired: no note, no run, a result, and a partial file. The normal freeze also refused. The audit fields are present. See items 5 and 6 for the limits.
- **B4:** `PROTOCOL.md:66`, `STAGE4_PLAN.md:40`, and `stage4_rules.py:57-59` agree, except for the docstring in the notes above.
- **S1:** A `.partial` file or a failed rename refuses a rerun and refuses `--after-crash`. See item 1 for the stranded state.
- **S2:** In a clean run, the line and the disclosure print first. The save has its own `try` and prints the safe error only. Real `save_test_frames` wrote both files on open data, on a scratch path.
- **S4:** The disclosure holds every item that `PROTOCOL.md:70` requires. See item 10 for the log.
- **S5:** The hash is printed before Step A, in each attempt, and in the result, including after a refreeze. It matches the manifest. See item 4 for when the comparison can happen.
- **S6:** The exact PowerShell 7 command writes plain UTF-8, with no BOM. The file names and marker order are correct. In Windows PowerShell 5, the same command fails and writes no file, which is safe. A BOM marker and the template date are refused. See item 4 for step 1.
- **Coverage wording:** "about 80% to 91%" is in `stage4_rules.py:165`, `PROTOCOL.md:69`, `STAGE4_PLAN.md:51`, `report_stage4.py:111`, and a test.
- **`last_quotes` record:** The text matches the code, and tests cover it. `last_row_null_bids` is 0 on 2020-05 to 2022-08, which agrees with the earlier report.
- **Alpaca reader text:** A search of the project and `review/` code shows no other reader of the closes.
- **Repeat run after a result:** Runs with no note, with a note, and with the accept flag were all refused. `--after-crash` and the normal freeze were also refused.
- **Unit tests:** 146 of 151 pass. I skipped the 5 tests in `BuiltInputs`, because their `setUpClass` reads the cash file directly.

## What I did not check

- Any content of the 2016-2018 option files, rates, cash rows, or Alpaca bars. So the real floor result, the real guard result, and any layout problem stay unknown.
- A full run with real markers and real zips. In the full-path walks, `step_a` was replaced, because the copies have no zips. The real `step_a` ran separately, on open dates.
- The real `load_alpaca_closes` on the real file, a rehearsal run, and `condition.json`. I replaced `day_conditions` in my open-date runs.
- The 5 `BuiltInputs` tests.
- The 2,000-resample run. My runs used 10 to 60 resamples.
- A real antivirus lock. I used a real file handle lock and patched failures.

## Contact with locked data or names

No locked price, return, or rate was shown or written. These contacts occurred:

- **Hash only:** `freeze.verify_manifest()` read all five input files to hash them. It showed no value.
- **Memory-only parse:** `load_cash_events` on open dates parsed the full cash file, so the two locked rows were in memory for a moment. This happened in `test_cash_events_are_gated_and_filtered` and in each `step_b` call in `real_open.py`. Nothing from those rows was printed.
- **Memory-only names:** `iter_days` read the zip name lists, which include 2016-2018 member names, in my `real_open.py` runs. It filtered them and printed nothing. It read no locked member.
- **Text that I read on screen:**
  - `build_inputs.py:29-31` shows the dates 2016-05-19, 2017-05-10, and 2017-09-26, and the amount USD 0.000413. I printed these lines by accident in a wider `sed` read, and I then did not reopen that part. `PROTOCOL.md:32` and `:36` hold the same text, and the task required me to read that file.
  - `PROTOCOL.md` also gives the 2017 event dates, and `review/stage5_check/report.md` gives the header of the test rates file.
- **Treasury rates:** I read `data/source/fred_rates.csv` in full. It holds Treasury rates from 2018-01 and is not GGAL data.
- **Open files only:** I read `data/alpaca_open_closes.parquet`, with a date assertion, and `data/index_series.parquet`.
- **Synthetic data only:** The 2016-2018 dates in my copies carry invented closes and forwards.
- **Not opened:** The Alpaca bars, the corporate actions, `fred_rates_test.csv`, and `condition.json`, except for the hashes above.

## Proposed order

1. The user decides item 2 and the note on the close limit.
2. Apply blockers 1 and 3 and items 5 to 11, then log them in `PROTOCOL.md`, including this check and the contacts above.
3. Run the tests and the rehearsal, then run `freeze.py` once, with the user's approval.
4. Correct `HANDOFF.md` step 1 and the hash.
5. Ask an independent reviewer to recheck the failure paths in `finish` and the `except` block.

The user decides what changes.
