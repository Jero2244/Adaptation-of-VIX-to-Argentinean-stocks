# Review of Stage 3

Exploratory. These scripts ran on 2026-11-04, after the Stage 3 results. They hold the checks behind the "review check" numbers in `reports/stage3_findings.md`. The study code does not use them.

A defender and an attacker wrote the scripts in `defender/` and `attacker/`. I wrote `verify_debate.py` to reproduce their main numbers.

## Files

| Path | Content |
|---|---|
| `verify_debate.py`, `verify_debate.txt` | My reproduction of the main review numbers. **Start here** |
| `defender/build5m.py`, `defender/rv5m.csv` | 5-minute RV from Nasdaq bbo-1m mids, and its output |
| `defender/check1.py`, `check2.py`, `check3.py` | Defender checks. Output is in the `.txt` file with the same name |
| `attacker/a1_race.py`, `a1_race.csv`, `a1.out` | First race checks. **Caution: the attacker reports that this script has the Clark-West sign reversed. Use `a5_race2.py`** |
| `attacker/a2_insample.py`, `a2.out` | In-sample checks |
| `attacker/a3_intraday.py`, `a3_intraday.parquet`, `a3.out` | Intraday RV from Nasdaq bbo-1m mids, and its output |
| `attacker/a4_har_intraday.py`, `a4.out` | HAR with intraday inputs |
| `attacker/a5_race2.py`, `a5.out` | Corrected race checks and Clark-West |
| `attacker/a6_rows.py` | Row checks. No output file was saved |
| `attacker/a7_round2.py`, `a7.out` | Round 2 checks |

## How to run

Run from the project folder. Run the data builders first only if their outputs are absent, because they decode the Nasdaq zip.

```
conda run --no-capture-output -n py4fi python review/verify_debate.py
conda run --no-capture-output -n py4fi python review/defender/check3.py
```

## Limits

- All paths to the project are absolute, so the scripts need this folder at its present location.
- These scripts read `data/forecast_panel.parquet`, or the Nasdaq data through the date gate from 2018-05-01. They do not read the locked period.
- `defender/rv5m.csv` and `attacker/a3_intraday.parquet` come from licensed Databento data. Do not publish them or commit them.
- The two agents use different overnight rules for their 5-minute measures, so their results differ slightly.
- In the copies, only two path lines changed: `OUT` in `defender/build5m.py` and `D` in `defender/check3.py`. Each now points to the folder of its script.
