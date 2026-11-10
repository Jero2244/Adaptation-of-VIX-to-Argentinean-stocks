# Recheck of the latest fix round

Written 2026-11-04. An independent agent wrote this text. The harness does not let the agent write report files, so the main session saved its returned report here without a change to the findings. Scripts and outputs are in `work/`, copied from the session scratchpad.

## Verdict: Ready after listed fixes

Do not freeze yet. I found no code bug that can lose the test, show a locked value, or give a wrong verdict outside a triple fault. One item needs the user's attention before the freeze: S1, the false stop risk of the new no-forward branch. The code matches the user's decision, and I do not reopen that decision. The evidence is new, and the user should see it. The other fixes are small.

**Final state of the real folder:**
- `reports/` holds no marker, run record, Step A file, result, `.partial` file, or manifest backup.
- `data/test` does not exist.
- The SHA-256 of `reports/freeze_manifest.json` is still `696fb7f0b5597ac0b4615151a22160b8db703d8344dd9a40c4483157eb8cca27`.
- No project file is newer than my first script, so I changed nothing.

## BLOCKER

None.

## SHOULD FIX

**S1. On clean closes, the no-forward branch can stop the run if the test period has more or longer blank runs. CONFIRMED by simulation on open dates. For the test period it is PLAUSIBLE, because its blank pattern is locked.**
- **Where:** `run_tests_once.py:123-125` and `:128-134`, and the PROTOCOL.md "Input stop" row.
- **Status of the code:** it does what the user decided. An up-and-down drift during a blank run triggers the branch, and no bug is needed.
- **Why I raise it:** the consequence fits the BLOCKER text. A false stop has only two ends: "Inconclusive, inputs failed", or a verdict after a person reads the dates. A fix cannot change the limit. I rate it SHOULD FIX only because I was told not to reopen the decision and the likelihood in the locked period is unknown. The supporting figure ".098 on 287 sessions" is correct, but it reflects one alignment of blanks with closes:
  - The blanks are 13.6% of 2,104 sessions, in 94 runs, and the longest run is 15.
  - No session is above .10, and 3 are above .08.
- **Evidence:** all runs use clean closes on open dates. The forward equals the close, so only the blank pattern changes (`stress2.py`, `stress3.py`).

| Test on 585-session windows | False stop |
|---|---|
| Real blank pattern, moved along the closes at random | 16.7% of 600 windows |
| Same, with the extra condition below | 0.0% |
| Full sample (2,104 sessions), real pattern shifted | 50 of 85 shifts |

Random blank runs, 150 windows for each cell. The first number in each cell uses open-period volatility, and the second uses 0.7 times that volatility:

| Blank share | Mean run 3 | Mean run 8 | Mean run 15 |
|---|---|---|---|
| 14% | 18.7% / 2.7% | 36.0% / 15.3% | 60.7% / 20.7% |
| 25% | 29.3% / 10.0% | 65.3% / 22.0% | 87.3% / 40.0% |
| 49% | 60.0% / 18.0% | 92.0% / 65.3% | 97.3% / 82.7% |

- **Limits of this evidence:**
  - Moving the pattern breaks any link between blank days and quiet periods. The real alignment passed, so such a link may exist, and these rates can be too high.
  - The daily standard deviation of the open closes is .0436. I do not know the value for 2016-2018.
  - The data floor permits about 49% blank sessions.
- **Likelihood:** unknown. It is low if 2016-2018 looks like the open data, and high if the option data is much thinner there.
- **Proposed action:**
  1. Show the user this table before the freeze. Keeping the rule needs no code change.
  2. If the user wants a change, one option is to stop only if the close is also above .15 from both adjacent closes. Only 1 of 2,104 real closes meets that condition alone, and the false stop rate fell to 0.0% in the test above. An isolated bad close should still stop, but I did not test this.
  3. A count-only option is to add the longest blank run to the Step A counts. The person then sees the risk before the outcomes marker. This does not reduce the risk.

**S2. The tests leave parts of this round unprotected. CONFIRMED (`mutate3.out`).** The baseline passes. Of 74 applied mutants, 53 were caught and 21 survived. One more mutant was a no-op of mine and did not apply. The walks show that the current code is correct on each item below. Only the protection is missing.

| Surviving change | Missing test |
|---|---|
| `before` or `after` without `.abs()` (`:132-133`) | A bad close that is too low. With either change, a low close can stop no run |
| `after` only, no `min` | A stray on the last row, and a real jump that stays near the left side only |
| Dates list all no-forward sessions (`:125`) | A panel with several blank rows and one stray. The list length would reveal more |
| Fixed text in place of `str(fault)` (`:146`) | The data fault name reaches the stop check |
| Close of zero or NaN passes (`load_data.py:105`) | Only a negative close is tested. Add 0 and null |
| `say` catches `Exception` only (`:213`) | Ctrl-C inside a print |
| Raw error in "The result write did not finish" (`:252`) | A write error that holds the synthetic secret |
| `history` drops `error`, note, or refreezes, or keeps `step_a` (`:235-236`) | Exact keys of the history, including a refreeze |
| No `history` in the accept result (`:314`) | The disclosure says "See the history in the result file", and no test checks that it is there |
| `write_manifest` writes directly (`freeze.py:62`) | Only the `after_crash` route is tested |

Safe to ignore on the real path:
- No `from None`, because the error is caught and never reaches the top.
- `duplicated()` default, because `drop_duplicates` gives the same dates.
- Positional dates and no sort, because the panel has a sorted default index.
- `>=` at the limit.
- `except OSError` around the frame save, because the hook still hides the message.

**S3. The access log has no entry for this round, and this recheck also needs one. CONFIRMED.**
- **Where:** PROTOCOL.md line 55 is the last log entry, for the third agent.
- **Evidence:** PROTOCOL.md was last saved at 23:13:52. The stored rehearsal was written at 23:17:20, so the log cannot describe that run.
- **Fix:** before the freeze, add the 226 tests, the rehearsal, the 73 windows, and the contacts listed at the end of this report. PROTOCOL.md is in the manifest, so this must come first.

## NOTE

All are CONFIRMED.

- **N1. A failure inside the hook can show the message (`run_tests_once.py:219`).**
  - `safe_error(error)` runs outside `say`'s guard. If it raises, Python prints "Error in sys.excepthook" and then the original chain.
  - In a real child process, the synthetic secret 987.654 reached the screen, in both Step A and Step B (`fmatrix.out`, `*_ctrlc_handler_and_hook`).
  - This needs a crash whose message holds a value, a Ctrl-C inside the short `except` block, and a second Ctrl-C inside the hook. This is a rare triple fault, so it is not a blocker.
  - **Fix:** wrap the hook body in `try/except BaseException: pass`.
- **N2. The note of the final attempt is not in the result.** `history` takes `attempts[:-1]`, so the note stays only in the run record. A refreeze note does reach the result, but a rerun with no refreeze leaves none. **Fix:** add `crash_fix_note=note` to the result.
- **N3. A second Ctrl-C can skip the line (`:256-258`).** The read of the partial file catches `OSError` and `ValueError` only. This needs one Ctrl-C in the partial write window and a second during the read.
- **N4. A forward that is not positive passes silently.** A negative forward gives a NaN gap, so that row passes, and a stray between two negative forwards also passes. This is older behavior. The smallest forward on open data is 5.85, so it is unlikely. A zero or infinite forward does stop the run.
- **N5. `replace_manifest` has no retry, unlike `write_text`.** A lock on the rename raises an error. The old manifest stays whole, and a retry works, but it adds a second identical refreeze entry.
- **N6. A log detail.** The third-agent log entry omits two minor items from its report: the cut-off input hashes printed by searches, and its open-data reads. Neither is locked content.
- **N7. A note on the walks.** With an infinite close, a pandas `RuntimeWarning` reaches stderr. It shows a source line and no value.

## What I found correct, and how I tested it

**1. `no_forward_gaps` and the branch** (`edge_guard.py`):
- A brute-force check agreed on 1,500 random panels, with no disagreement. The panels had several blank runs, shuffled rows, and non-default indexes.
- These cases give the right dates and no value: leading and trailing runs, several strays, all blank but one, and an infinite close.
- A gap of exactly .15 passes, as "above" requires.
- All-blank panels stop earlier, at "No session has both".
- A panel with duplicate index labels lists too many dates, but the real path cannot produce one.
- On open data: 287 sessions and a largest gap of .0981 match PROTOCOL.md. My own 75 windows of 28 months gave 0 stops.

**2. `DataFault`** (`cli_walk.py`, through the real `main()`, the real `step_b`, the real gate, and the real manifest check, on copies with synthetic bars; only `step_a` is replaced):
- These faults all give `input_stopped`: no bar, bars only outside the dates, two bars, a negative, zero, null, or NaN close, and one or two ex-dates that are not sessions.
- The secret was absent from the screen, the record, and the result. No date appeared on the screen.
- An unchanged rerun and the wrong accept flag are refused. `--accept-input-stop` gives the final "Inconclusive, inputs failed".
- A layout fault (missing key, missing page, text close) stays an ordinary crash.
- A missing `c` key would be a crash, not a stop. The real file cannot trigger this, because every rehearsal already parses all its bars through that code.
- By reading: `DataFault` is a `ValueError`, so `compare_alpaca.py`, `load_sessions`, and the tests behave as before. I found no code that depends on the old message text.
- Good data: a diff of `realized.py`, `load_data.py`, and `config.py` against `review/pre_fix2_backup` shows only error branches and the new class. So the reasoning about `run_development.py` holds for these three files. That backup is older than this round, so I cannot show by diff that nothing else changed this round.

**3. `say`, the hook, `stop_run`, and `show_result`** (`fmatrix.py`, real child processes, hook installed, about 85 cases):
- No secret appeared in any Step A or Step B case with a failed write, a failed rename, a Ctrl-C in the write, rename, or print, a failed print, a Ctrl-C in the handler, or a real Windows lock. The only exception is N1.
- All three end paths (normal and both accept paths) showed the same thing. After `finishing`, each fault keeps the outcome and permits no rerun or refreeze.
- A Ctrl-C during the partial write now prints the full text.
- A Ctrl-C during the line print leaves the result file, or a pointer to the partial file, and still prints the disclosure.
- A Ctrl-C before `finishing` is on disk leaves a legal next move.
- I found no stranded state. Swallowing a Ctrl-C in `stop_run` still exits with code 1.
- An uncaught Ctrl-C exits with code 3221225786, which is not zero.
- Plain command line on a copy: each refusal shows its message and exits with code 1. I tested no marker, the wrong accept flags, an absent manifest, a changed file, a wrong hash, and an existing result. A real `BadZipFile` in `step_a` gives type and locations only.

**4. `history` and `disclosure_for`:**
- The result holds only time, hash, note, error, stop check, and dates, plus the refreeze fields.
- By code path, `error` comes from `safe_error`. A guard message is fixed text, and the other messages are hidden.
- The note is typed by a person, so no outcome value can enter it through code.
- Counts are right. After an accept, the record holds 2 attempts and the history holds 1. After a fix, the same. The current attempt is left out on both paths.
- The stop sentence appears only after a stop.

**5. `replace_manifest`** (`rm_test.py`, and the fix walk):
- The file has no CR bytes, and its hash equals the text hash and the record's new hash.
- A failed rename leaves the old manifest whole, and verify still refuses the changed file.
- A garbage leftover `.partial` is overwritten by a retry.
- The frozen file list holds no `.partial`.

**6. PROTOCOL.md:**
- The texts for the input stop, the end path, the result write, the accepted risk, and the disclosure match the code.
- "Fix before any run" works as written on a copy. The normal freeze refuses with markers, and it works after they are removed.
- The log entry for the prior recheck agrees with its report, apart from N6.

**7. Main-session claims:**
- 226 tests are discovered. I ran 225, and all pass. I skipped `test_one_dividend_for_each_local_dividend_by_year` because it parses locked rows. An audit hook blocked any open of the Alpaca file and `fred_rates_test.csv`, and it recorded no attempt.
- All `.py` files that I checked in `run_tests_once.py`, `stage4_rules.py`, `freeze.py`, `config.py`, `load_data.py`, and `realized.py` are ASCII. So a console encoding error cannot silently remove the verdict line through `say`.

## What I did not check

- Any 2016-2018 option, rate, cash, or Alpaca content. So the real blank pattern, floor, and stop result stay unknown.
- A run with real markers or real locked files. `step_a` was replaced in the walks, except for the `BadZipFile` case.
- The rehearsal rerun or the old-versus-new rehearsal diff. I also did not rerun the 73 windows of `guard_open_windows.py`. I ran my own 75 windows from stored open files.
- `run_development.py` itself. I checked it by reading only.
- A real Ctrl-C signal, a real full disk, a real antivirus lock, or a real power loss. I raised `KeyboardInterrupt` inside calls, in real child processes, and used one real file handle.
- Whether any test in the real suite parses `condition.json`. An earlier report says the tests mock `step_a`, and I did not audit it again.
- `HANDOFF.md`, which is outside this scope.

## Contact with locked data or names

No locked price or return was shown or written. I opened none of the forbidden files, and I had no accidental read of locked file contents.

- **Memory-only parse:** the real test suite called `load_cash_events` on open dates, which held the two locked cash rows for a moment. Nothing from them was printed. The suite may also have held 2016-2018 zip member names through `iter_days`. I printed none.
- **Rates:** tests may have loaded `data/source/fred_rates.csv`, which holds Treasury rates from 2018-01. I printed nothing from it.
- **Text read on screen:**
  - PROTOCOL.md and the prior report show the 2016-05-19, 2017-05-10, and 2017-09-26 dates, the USD 0.000413 amount, and the two test event dates.
  - `run_tests_once.py` shows the disclosure text.
  - The harness script `common.py` shows 2017-05-10 with an invented amount.
- **Copies not opened:** my scratch copies of the code include `build_inputs.py` and `tests/test_inputs.py`. I did not read them. They only ran where the test files import them.
- **Open data read:** `data/alpaca_open_closes.parquet` and `data/index_series.parquet`, with an assertion that all dates are from 2018-05-01 onward.
- **Synthetic only:** dates from 2016-2018 in my outputs, such as 2016-05-23, carry invented closes, forwards, and cash.
- **Conda note:** two `conda run` calls that started together collided on a temp file and did nothing. I reran them. No state changed.

Main files: `edge_guard.py`, `cli_walk.out`, `fmatrix.out`, `mutate3.out`, `open_gaps.py`, `stress2.py`, `stress3.py`, `rm_test.py`, `real_suite3.py`.

## Proposed order

1. Show the user S1, and record the user's choice.
2. Add the S2 tests. Apply N1 and, if wanted, N2 and N3.
3. Add the S3 log entries.
4. Rerun the tests and the rehearsal, then freeze with the user's approval.
