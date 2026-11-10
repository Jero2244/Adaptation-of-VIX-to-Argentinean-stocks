# Stage 4 plan debate

Exploratory. These files ran on 2026-11-04 and hold the checks behind `STAGE4_PLAN.md`. The study code does not use them.

| Path | Content |
|---|---|
| `stage4_draft_plan.md` | The draft that the agents debated. `STAGE4_PLAN.md` replaces it |
| `advocate/round1.md`, `advocate/round2.md` | Advocate's reports. Scripts and outputs are in the same folder |
| `critic/round1.md`, `critic/round2.md` | Critic's reports. Scripts and outputs are in the same folder |
| `judge/j1_check.py`, `judge/j1.out`, `judge/j1_sim.csv` | My check of the disputed rules |

## Limits

- I did not rerun the scripts from this folder. `judge/j1_check.py` has an absolute path to the session scratchpad, so it needs a path change.
- The agents report that they read no 2016-01 to 2018-04 data, no Alpaca file, and no raw Databento file. I did not audit these reads.
- Outputs come from licensed Databento data. Do not publish or commit them.
