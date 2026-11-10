# Adversarial review of the implied move calibration (C4)

Date: 2026-11-05. One independent agent, read-only. The session saved this summary, because a subagent cannot write here. The scripts `rev1.py` to `rev4.py` are in this folder. All these checks are post-result. Keep them local, because they derive from licensed data.

**Verdict of the review:** the computation is sound, but the write-up had to change before the user relies on it. The review found no formula error, no look-ahead, and no row mismatch. The saved numbers reproduce exactly.

## Must-fix findings and their status

| # | Finding | Status |
|---|---|---|
| 1 | The lead sentence "no clear error" fits only pooled coverage. The inner rate is about 50% in the lowest ATM30 quintile, with a large lowest-minus-highest gap | Fixed. Reproduced in `calib_post.py` |
| 2 | "Scaled ATM30 fixes mean z squared" is wrong: it overshoots to .81. The 2019 PASO inflates k, and the worse scores depend largely on this | Fixed. Reproduced in `calib_post.py`. Interval widths from the review's sensitivity were not reproduced |
| 3 | The fat-tail outer result is mechanical, because a unit-variance t has almost the same 2-sigma quantile as a normal | Fixed |
| 4 | "Tie" is too strong, and coverage differs | Fixed |
| 5 | Only the inner rate had a coverage check. The review's simulation gives weaker cover for outer and mean z squared, about 60% for outer at 252 rows | Disclosed. These numbers come from `rev3.py` only, with one assumed jump model |
| 6 | "Move probabilities add little" overreaches, and the Limits text contradicted the main reading | Fixed |
| 7 | The selection limit had no direction: blank ATM30 rows have larger moves | Fixed. Reproduced in `calib_post.py` |

## Minor findings and their status

- **Fixed T against shorter real windows:** disclosed, and reproduced in `calib_post.py`.
- **Constant-case truth is about 68.8%, not 68.3%:** disclosed. The frozen code is unchanged. The C1b tolerance cannot see this gap.
- **The wandering case is near nominal, so its "Fires" column shows false alarms:** disclosed.
- **The forward table uses consecutive rows:** the column is renamed, and the report has a note.
- **Forward code checks only that a horizon argument exists, and does not filter rows:** open. It is logged in `CALIBRATION_PLAN.md`, and it must be fixed before any forward run.
- **Report wording is fixed text:** the docstring now says so.
- **Omissions from report tables:** noted in the report, and the numbers are in the JSON.
- **The plan's 4.6 and 9.5 point standard errors are high:** noted in the report.
- **Rolling figure:** early points hold about six months of rows under a "12-month" title. This is not changed.

## Checked and fine, according to the review

- z, centre, window, and alignment. R rebuilt from raw closes and the cash file on 400 rows differs by 0.0.
- CRPS, interval score, move probabilities, PIT, and strict hit rules, by reading.
- No look-ahead in k, nu, HAR, or the past base rate.
- One common-row mask for all methods.
- Bootstrap positions and non-contiguous cuts.
- Event mask counts.
- Ordering by file times: the manifest came before the results, and all manifest hashes matched at the review.

## Not checked by the review

- Whether a real-data run happened before the manifest. File times and the code guard fit the claim, but they cannot prove it.
- The construction of ATM30, the accuracy of the cash file and the event dates, and the test-period R against raw Alpaca closes.
- The saved `by_event` table as a whole, and the 300-run simulation in `reports/calib_synthetic.json`.
