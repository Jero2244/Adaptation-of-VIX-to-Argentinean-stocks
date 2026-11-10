# Recheck of the Stage 5 failure-path fixes

Written 2026-11-04. An independent agent wrote this text. The harness does not let the agent write report files, so the main session saved its returned report here without a change to the findings. Scripts and outputs are in `work/`, copied from the session scratchpad. Line numbers refer to the unfrozen code of this date.

## Verdict: Ready after listed fixes

Do not freeze yet. All 11 items work in the ordinary fault cases. Two gaps remain in Blockers 1 and 3, and both need a rare event such as Ctrl-C at the wrong moment. A small patch closes most of both, and I tested it on a copy. One finding (S1) needs a user decision before the freeze.

**Final state of the real folder:**
- `reports/` holds no marker, run record, Step A file, result, `.partial` file, or manifest backup.
- `data/test` does not exist.
- The SHA-256 of `reports/freeze_manifest.json` is still `696fb7f0b5597ac0b4615151a22160b8db703d8344dd9a40c4483157eb8cca27`.
- No project file changed after 22:30, so I edited nothing.

Outputs: `walk.out`, `fmatrix.out`, `edge.py` (output on screen only), `mutate2.out`, `real_open2.out`, `fixtry.out`, `real_suite2.out`.

## BLOCKER

Both blockers meet the stated definition, but their likelihood is very low. The user can downgrade them. The fix is small, so I recommend that you apply it.

**B1. A crash message can still reach the screen. CONFIRMED with a real child process and real stderr.**
- **Where:** `run_tests_once.py:196-201` (`stop_run`) and `:312-313`.
- **Cause:** `stop_run` catches only `Exception`, and its prints are not protected. A new error inside the `except` block still carries the original error as context.
- **Evidence:** the synthetic secret `987.654` appeared under "During handling", with crashes in both Step A and Step B:

| Case | Secret on screen |
|---|---|
| Ctrl-C during the `crashed` record write | Yes |
| Ctrl-C during the rename | Yes |
| The print of "The run stopped" fails once, then stderr works | Yes |
| The print of "The run record was not updated" fails once | Yes |
| Record write fails, patched or with a real Windows lock | No |

- **Likelihood:** very low. It needs a crash whose message holds a value, plus Ctrl-C or a brief stderr failure. The rename retries lengthen the window, by up to 4 seconds if the file is locked. A leak cannot be undone.
- **Fix:**
  1. Catch `BaseException` in `stop_run`.
  2. Add a `say()` helper that cannot raise.
  3. Set a `sys.excepthook` in `main()` that prints only `safe_error`. It must also show `RunRefused` and `ManifestMismatch` messages.
- **Patch trial:** the secret appeared in none of the 8 cases (4 types, Step A and Step B). The 99 tests that I ran on the copy pass, and a refusal still shows its message.

**B2. Ctrl-C can lose the outcome after the status `finishing`, and a failed print skips the later steps. CONFIRMED.**
- **Where:** `run_tests_once.py:206-224`. The `except` catches only `Exception`, line 216 catches only `OSError`, and the prints at 222-224 are not protected.
- **Evidence on the normal path and both accept paths:**

| Case | Line shown | File holds result | Legal next move |
|---|---|---|---|
| Ctrl-C during the partial write | No | No | None. This loses the test. |
| Ctrl-C during the rename | No | Yes, `.partial` | Rule applies |
| Print of the line fails | No | Yes | Closed, but the disclosure and frames are skipped |
| `.partial` holds bytes that are not UTF-8 (`edge.py` case 8) | No | No | `UnicodeDecodeError` escapes |

- **Likelihood:** very low. The partial write takes about a millisecond.
- **Fix:**
  1. Use `except BaseException` around the write.
  2. Use `except (OSError, ValueError)` around the read.
  3. Use `say()` for the prints.
- **Patch trial:** Ctrl-C now gives the line, the disclosure, and the frames, plus the full text if no file holds the result. A failed line print no longer stops the disclosure or the frames.
- **Limit of the patch:** a power loss or hard kill in that window still loses the test. To close it, write the partial file before the status `finishing`, and delete it if the status write fails. The user can instead accept this risk in `PROTOCOL.md`.

## SHOULD FIX

**S1. The input stop does not check a close on a session with no near forward. CONFIRMED on open dates through the real code. The user decides.**
- **Where:** `run_tests_once.py:111` (`dropna`).
- **Evidence:** on 2020-01 to 2022-04, 117 of 587 sessions have no forward. A bad close on one of them never stops the run:

| Close on a no-forward session | Status | `b` (clean 1.103) | Lower bounds, 21 and 63 blocks |
|---|---|---|---|
| x1.25 | finished | 1.260 | .817, .775 |
| x1.5 | finished | 1.301 | .894, .796 |
| x2.0 | finished | 1.336 | .918, .798 |
| x0.5 | finished | 1.333 | .918, .797 |

- **Reading the table:** the clean bounds are .645 and .726 at 2,000 resamples, and these rows use 200. So compare the bounds with care. `b` does not depend on the resamples.
- **Why it matters:** the error moves `b` and the bounds up, toward "Supported". The verdict did not flip here, because this window is already "Supported". This is why I rate it below BLOCKER.
- **Likelihood:** low. Alpaca differed by at most 17 bp on open dates, but 2016-2017 is unchecked. The test period may also have more no-forward days.
- **Fix:** compare such a close with the nearest forward on each side, using a wider limit. Or stop on a large return that reverses on the next session. Either one is a rule change and needs the user's decision before the freeze.

**S2. A repeating data crash in Step B has no final outcome. CONFIRMED (`walk.out`, H1).**
- **Where:** `run_tests_once.py:126-130`, `load_data.py` (not positive, two bars on one date, no bars), and `realized.py:33` (ex-date not a session).
- **Scenario:** these checks run before the guard, so they give `crashed`, not `input_stopped`. With a cash row on a non-session day, both accept flags are refused and a rerun repeats the crash. This is the same gap as old Blocker 2, on a smaller path.
- **Likelihood:** low. It is most likely if Alpaca omits an ex-date session.
- **Fix:** convert these faults to `InputGuardFailed`, which keeps them date-only. Or state in `PROTOCOL.md` what happens if no fix exists.

**S3. The result does not say that an input stop came first. CONFIRMED (`walk.out`, F7).**
- **Where:** `run_tests_once.py:303`.
- **Scenario:** a person reads the failing dates, fixes a bug, and gets a verdict. The result file and the disclosure do not mention the stop. Only the run record holds it, as it does for crashes and refreezes.
- **Why it matters:** those dates are a weak look at the outcome data, because a large gap can follow a large move.
- **Fix:** add to the result a short list of attempts and refreezes, with notes, stop checks, and dates.

**S4. Tests leave parts of the fixes unprotected. CONFIRMED (`mutate2.out`).** The baseline passes. Of 95 mutants, 64 were caught and 31 survived. These survivors matter:

| Area | Surviving change |
|---|---|
| Accept-path failures (Blocker 1) | Failed write not caught, no `finishing` write, `show_result` replaced by a plain write |
| Result text | A truncated partial counts as kept, so the text is not printed |
| Command line | `main()` drops the note, `--accept-input-stop`, `--accept-floor-failure`, or `--expected-hash`. `freeze.main` drops `--allow-input-change` |
| Refreeze | Default input list ignored, so a changed input passes. Blank-note and no-run refusals are masked by the no-change refusal |
| Stale accept | Removable, because the tests pass no note. Accept plus a note would then pass |
| Other refusals | A result file alone is unchecked. The `floor_failed` check on accept is masked |
| Manifest list | Tests, rule files, inputs, or the Alpaca file can drop out of the hash list with no test failure |
| Step A and Step B wiring | `step_a` can pass 0 for blank rates. `step_b` can pass no one-source dates, or the wrong set |
| Stop dates | The largest-gap and median filters can use another limit |
| `stop_run` | A raw write error can be shown, or it can catch `OSError` only |
| Retry | The wait can be removed |

- **Equivalent, safe to ignore:** "JSON text after finishing" is still a crash inside the same `try` in the normal path. "Note not needed after input stop" is hidden by later checks.
- **Do the tests mock away the claim?** Partly. The state-machine tests inject `run_a`, `run_b`, and `save`, and nothing tests `main()`. The double-fault test checks the suppress flag correctly, but in-process tests cannot see top-level printing.
- **Fix:** add tests for these, plus a child-process test that reads stderr.
- **Current behavior:** my walks passed all of these paths except the items in B1 and B2.

**S5. The access log needs entries before the freeze. CONFIRMED by reading.**
- `PROTOCOL.md` has no entry for this fix round: the test runs, the rehearsal, and the rerun of the 73 windows at .15. Line 52 describes the earlier run.
- This recheck also needs an entry, with the contacts below.
- Line 53 omits that the second agent read `fred_rates.csv` in full, from 2018-01. These are Treasury rates, not GGAL data.
- Line 54 says that the rights report "holds dates, share counts, and ratios". It also holds peso dividend totals and offering sizes. It holds no price.
- `DISCLOSURE` names the Alpaca and cash file parses, but not the test parse of the local dividend file (`tests/test_inputs.py:118`).

**S6. The manifest write in `--after-crash` is not atomic. CONFIRMED (`edge.py` case 2).**
- **Where:** `freeze.py:116`.
- **Scenario:** a partial write leaves bad JSON. Then `after_crash` and `verify_manifest` both raise `JSONDecodeError`, and no rule covers this. A manual restore from the kept backup works.
- **Likelihood:** low.
- **Fix:** write through a partial file and rename it.

**S7. No route is defined for a fix when a marker exists but no run record does. CONFIRMED (`edge.py` case 4, `walk.out` A2).**
- **Where:** `freeze.py:96-97` and `:83`.
- **Scenario:** the marker is written, and then a hash mismatch or a needed fix appears. `--after-crash` says "use a normal freeze", and the normal freeze refuses because of the marker.
- **Fix:** state in `PROTOCOL.md` that if no run has started, the user can remove the marker and freeze normally.

## NOTE

All are CONFIRMED by test or reading.
- **Bad close near the limit:** with forwards present, a close 17% too high passes (`b` 1.203), and 20% stops. The user chose this limit.
- **What the dates reveal:** they hold no price, and I found no value in any stop field. But a date with a large gap can suggest a large move, and the list length gives a count of such days. The user accepted this.
- **"A rerun needs a changed file":** a log line in `PROTOCOL.md` satisfies it (`walk.out`, F2 to F5). The same stop repeats, so no harm follows.
- **"A fix cannot change the stop limits":** this is a written rule only. A limit change would be visible in the `changed` list.
- **Misleading messages:**
  - If the stop's record write fails, the screen still says that the dates are in the record, and the status stays `started`. A rerun with a note is permitted.
  - "The result is safe" prints after a failed frame save even if no file holds the result (`edge.py` case 7).
- **Failed accept write:** the status becomes `crashed`, so accept is refused and a rerun with a note is needed. A rerun reaches the same stop, so this is not stranded.
- **Hand-edited records:** a missing key or empty `attempts` gives `IndexError` or `KeyError`. No state changes.
- **Retry after a failed manifest write:** this adds a second, identical refreeze entry. No harm follows.
- **`--allow-input-change` alone:** it is ignored, and the normal freeze still refuses after a run.
- **Rights disclosure:**
  - It does not say that the local ex-date is unknown (`review/stage5_rights_check/report.md:134`). The ADS close may show an ex-rights step on that date, with no flag.
  - The rights report warns that its quotes came through a summarizer. The disclosure does not.
- **`HANDOFF.md`:** step 1 of the approval is still wrong, `--expected-hash` is absent, and "If the run stops" omits the input stop path and the `.partial` rule. It is outside the manifest, and the main session already plans to correct it.
- **Tool artifact:** `guard_ctrlc` in `fmatrix.out` shows `date=1`. The date came from the source line of my test script, not from the code.

## Fixes that I found correct

- **Blocker 1:** I injected faults at each write on all three paths (`fmatrix.out`):
  - A JSON failure or a failed `finishing` write is an ordinary crash with nothing shown, and a rerun is permitted.
  - After `finishing`, a partial write failure, a truncated partial, a rename failure, or a read failure each kept the outcome.
  - The line and the disclosure always printed in these cases, and the frames were saved on the normal path.
  - No case showed an outcome and still permitted a rerun or a refreeze.
- **Blocker 2:** checked through the real code on open dates and through the real command lines:
  - The stored dates match my own calculation for all four checks, including both one-source directions.
  - No stop field or screen line holds a value or a date.
  - Accept gives "Inconclusive, inputs failed", is final, and holds the dates.
  - An unchanged rerun, the wrong flag, and a stale accept are all refused. `--after-crash` accepts the status.
- **Blocker 3, the stated scenario:** a failed record write shows no message, both patched and with a real Windows lock at the real 1-second wait. See B1 for what remains.
- **Items 5 to 9:**
  - The record entry, changed files, and backup are correct.
  - No-change refreezes and input changes are refused, and the flag works through the command line.
  - The record goes first. A retry after a failed record or manifest write works.
  - A changed hash needs a note, and a stale accept and a passed floor are refused.
  - Each attempt keeps its counts.
  - `blank_rate_sessions` gave 0 on clean data, 587 of 587 with blank rates, and 254 with a late rate start.
  - `--expected-hash` refuses a wrong or blank hash, and it accepts upper case. Blank notes are refused.
- **Item 10:** `PROTOCOL.md` and the code agree on all three user decisions: the stop end path, the .15 limit, and no cash row with disclosure. `DISCLOSURE` matches the rights report on its facts. See S5 and the rights note for the gaps.
- **Item 7:**
  - Retry delays and the kept manifest break nothing.
  - `step_a_counts` and the record writes work on real open data.
  - First-attempt logic works with empty `attempts`.
- **Item 8:** all walks gave the expected result: Step A pass, crash and fix, floor failure and accept, Step B, input stop and accept, input stop and fix, and repeat runs.
- **Main-session claims:**
  - **Tests:** 194 discovered. I ran 193 and all pass.
  - **Input stop:** 73 of 73 open windows pass, with maximum gap .0874 on 1,817 rows.
  - **Rehearsal:** my rerun matches the stored rehearsal on all 9 result fields I compared and on all `step_a` keys. I used closes from the open parquet and replaced `day_conditions`.

## What I did not check

- Any 2016-2018 option, rate, cash, or Alpaca content. So the real floor and guard results stay unknown.
- A full run with real markers, the real Alpaca file, or real zips on locked dates. In the command-line walks, `step_a` was replaced.
- `test_one_dividend_for_each_local_dividend_by_year`, because it parses locked rows before its filter.
- The old-code rehearsal diff, because I have no old output. I compared with the stored new file only.
- A rehearsal through the real Alpaca file. This is forbidden here.
- A real antivirus lock, a real full disk, or a real power loss. I used patches and one real file handle.
- A real `conda run` Ctrl-C. I raised `KeyboardInterrupt` inside the write calls, in real child processes.
- `freeze.verify_manifest()` on the real folder, because it now reports changes by design and would hash the inputs.

## Contact with locked data or names

No locked price or return was shown or written. I opened none of the forbidden files, and I had no accidental read of locked file contents.
- **Memory-only parse:** `load_cash_events` on open dates held the two locked cash rows for a moment, in the test suite and in `real_open2.py`. Nothing from them was printed.
- **Memory-only names:** `iter_days` held 2016-2018 zip member names in `real_open2.py`. It read only members in the 2020-2022 window and printed no names.
- **Memory-only rates:** `real_open2.py` loaded `data/source/fred_rates.csv` in full, which includes 2018-01 to 2018-04 Treasury rates. I printed only its column names. It is not GGAL data.
- **Text read on screen:**
  - `PROTOCOL.md` and the earlier report show the 2016-05-19, 2017-05-10, and 2017-09-26 dates and the USD 0.000413 amount.
  - The rights report shows 2017 dates, share counts, and peso dividend totals, with no price.
  - `events.py:20` shows the two test event dates, printed by a search. They are also in `PROTOCOL.md`.
  - Searches also printed cut-off manifest hashes of the input files, but no content.
- **Open data read:** `alpaca_open_closes.parquet` (with a date assertion), `index_series.parquet`, the option zips in the window, the stored rehearsal, and the open equity tables through the tests.
- **Not parsed:** `condition.json`. My open-date runs replaced `day_conditions`, and the tests mock `step_a`.
- **Synthetic only:** the 2016-2018 dates in my copies carry invented closes and forwards.

## Proposed order

1. The user decides S1, S2, and the power-loss option in B2.
2. Apply the B1 and B2 patch, S3, and S6, and add the S4 tests.
3. Add the log entries in S5 and the rule in S7.
4. Rerun the tests and the rehearsal.
5. Run `freeze.py` once, with the user's approval, then correct `HANDOFF.md`.

The user decides what changes. I changed nothing.
