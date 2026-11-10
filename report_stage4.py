"""Stage 4: the descriptive report of the seen data, 2018-05 to 2026-10. It has no verdict.

Each headline states the period, and the result with and without events. The reconciliation compares this code with
review/verify_debate.txt, which held the checks before they entered the study code.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import events as ev
import forecasts as fc
import stage4_rules as rules
from config import REPORTS

BREAK = "2025-03-01"
# Values from review/verify_debate.txt.
EXPECTED = {
    "fixed step 22, mean b": 0.611, "fixed step 23, mean b": 0.602,
    "fixed step 22, no PASO, mean b": 0.5, "fixed step 23, no PASO, mean b": 0.493,
    "no events, b": 0.459, "no events before 2025-03, b": 0.366, "from 2025-03, b": 1.19, "from 2025-03, no events, b": 0.781,
    "scored rows": 1599, "Clark-West mean": 0.0624, "Clark-West t, 21 blocks": 2.7, "Clark-West t, 63 blocks": 2.07, "QLIKE no factor mean": 0.0002,
}


def table(frame: pd.DataFrame, digits: int = 3) -> str:
    view = frame.copy()
    for column in view.columns:
        if pd.api.types.is_float_dtype(view[column]):
            view[column] = view[column].map(lambda v: "" if pd.isna(v) else f"{v:.{digits}f}")
    lines = ["| " + " | ".join(map(str, view.columns)) + " |", "|" + "---|" * len(view.columns)]
    return "\n".join(lines + ["| " + " | ".join(map(str, row)) + " |" for row in view.itertuples(index=False)])


def coefficient_rows(panel: pd.DataFrame, event_sessions: list[pd.Timestamp], reps: int) -> pd.DataFrame:
    rows = panel[panel["primary"]]
    before, after = rows[rows["session_date"] < BREAK], rows[rows["session_date"] >= BREAK]
    groups = [("All", "with events", rows), ("All", "no events", rules.without_events(rows, event_sessions)),
              ("Before 2025-03", "with events", before), ("Before 2025-03", "no events", rules.without_events(before, event_sessions)),
              ("From 2025-03", "with events", after), ("From 2025-03", "no events", rules.without_events(after, event_sessions))]
    for period, (first, last) in {"2018-2023": ("2018-05-01", "2023-12-31"), "2024-2025": ("2024-01-01", "2025-12-31"), "2026": ("2026-01-01", "2026-12-31")}.items():
        chosen = rows[rows["session_date"].between(first, last)]
        groups += [(period, "with events", chosen), (period, "no events", rules.without_events(chosen, event_sessions))]
    output = []
    for period, events_label, chosen in groups:
        result = rules.intervals(chosen, reps)
        output.append(dict(period=period, events=events_label, n=result["n"], b=result["b"], low21=result["low21"], high21=result["high21"], low63=result["low63"], high63=result["high63"]))
    return pd.DataFrame(output)


def fixed_steps(panel: pd.DataFrame, paso: pd.Timestamp) -> pd.DataFrame:
    with_events = rules.fixed_step_summary(panel).assign(events="with events")
    calm = panel.assign(primary=panel["primary"] & ~((panel["session_date"] < paso) & (panel["window_end"] >= paso)))
    return pd.concat([with_events, rules.fixed_step_summary(calm).assign(events="no 2019 PASO windows")], ignore_index=True)


def race_table(race: dict) -> pd.DataFrame:
    rows = []
    for label, key, small, big in (("Duan factor", "qlike_duan", "duan_har", "duan_har_atm"), ("No factor", "qlike_no_factor", "no_factor_har", "no_factor_har_atm")):
        rows.append(dict(level_rule=label, qlike_difference=race[key]["mean"], low=race[key]["low"], high=race[key]["high"], mean_forecast_har=race["mean_forecast"][small], mean_forecast_har_atm=race["mean_forecast"][big], mean_target=race["mean_target"]))
    return pd.DataFrame(rows)


def ewma_sensitivity(panel: pd.DataFrame) -> pd.DataFrame:
    """Calibrated EWMA QLIKE on the common rows of the calibrated race, with lambda .94 and .98."""
    frame = panel.copy()
    frame["log_ewma98"] = np.log(fc.ewma_forecasts(frame["return_total"].to_numpy(), frame["window_sessions"].to_numpy(), 0.98))
    common = (frame["primary"] & frame["log_garch"].notna() & frame["log_garch_t"].notna() & frame["log_ewma"].notna()).to_numpy()
    forecast98 = fc.expanding_forecasts(frame, ["log_ewma98"], common & frame["log_ewma98"].notna().to_numpy(), common)
    scored = np.isfinite(forecast98) & frame["c_ewma"].notna().to_numpy()
    target = frame["rv30"].to_numpy()[scored]
    return pd.DataFrame([dict(lam=0.94, n=int(scored.sum()), qlike=float(fc.qlike(target, frame["c_ewma"].to_numpy()[scored]).mean())), dict(lam=0.98, n=int(scored.sum()), qlike=float(fc.qlike(target, forecast98[scored]).mean()))])


def reconciliation(coefficients: pd.DataFrame, steps: pd.DataFrame, race: dict) -> pd.DataFrame:
    def coefficient(period: str, events_label: str) -> float:
        return float(coefficients.loc[(coefficients["period"] == period) & (coefficients["events"] == events_label), "b"].iloc[0])

    def step_b(step: int, events_label: str) -> float:
        return float(steps.loc[(steps["step"] == step) & (steps["events"] == events_label), "mean_b"].iloc[0])

    found = {
        "fixed step 22, mean b": step_b(22, "with events"), "fixed step 23, mean b": step_b(23, "with events"),
        "fixed step 22, no PASO, mean b": step_b(22, "no 2019 PASO windows"), "fixed step 23, no PASO, mean b": step_b(23, "no 2019 PASO windows"),
        "no events, b": coefficient("All", "no events"), "no events before 2025-03, b": coefficient("Before 2025-03", "no events"),
        "from 2025-03, b": coefficient("From 2025-03", "with events"), "from 2025-03, no events, b": coefficient("From 2025-03", "no events"),
        "scored rows": float(race["scored"]), "Clark-West mean": race["clark_west"]["mean"], "Clark-West t, 21 blocks": race["clark_west"]["t"], "Clark-West t, 63 blocks": race["clark_west_block63"]["t"], "QLIKE no factor mean": race["qlike_no_factor"]["mean"],
    }
    frame = pd.DataFrame([dict(item=name, review=EXPECTED[name], study_code=found[name]) for name in EXPECTED])
    frame["difference"] = frame["study_code"] - frame["review"]
    return frame


def write(panel: pd.DataFrame, reps: int = rules.REPS) -> str:
    """Write reports/stage4_descriptive.md and its CSV tables. panel is the output of add_forecasts."""
    sessions = panel["session_date"].to_numpy()
    event_sessions = [ev.first_session(date, sessions) for _, date in ev.EVENTS]
    coefficients = coefficient_rows(panel, event_sessions, reps)
    steps = fixed_steps(panel, ev.first_session("2019-08-11", sessions))
    race = rules.same_row_race(panel, reps)
    races = race_table(race)
    ewma = ewma_sensitivity(panel)
    checks = reconciliation(coefficients, steps, race)
    for name, frame in dict(coefficients=coefficients, fixed_steps=steps, same_row_race=races, ewma=ewma, reconciliation=checks).items():
        frame.to_csv(REPORTS / f"stage4_{name}.csv", index=False)
    clark = pd.DataFrame([dict(blocks=21, **race["clark_west"]), dict(blocks=63, **race["clark_west_block63"])])
    text = f"""# Stage 4: descriptive report of the seen data

Period: {panel["session_date"].min().date()} to {panel["session_date"].max().date()}. **This period has no verdict.** All results are exploratory, because the method came after contact with these data. Only the 2016-01 to 2018-04 test gets a verdict. That period stays locked, and this report did not read it.

The "95%" intervals really cover about 80% to 91% in simulation, so they are too narrow.

## Coefficient on `log_iv2` in HAR+IV

"No events" drops each origin with a listed election in its target window.

{table(coefficients)}

## Fixed-step non-overlapping samples

Steps of 22 and 23 sessions. Reported only. These samples share periods, so they are not independent evidence. "No 2019 PASO windows" drops only that event.

{table(steps)}

## Same-row race: HAR+ATM30 against HAR

Both models train on all `primary` rows with a target window that ends on or before the origin. {race["scored"]} rows are scored, from {pd.Timestamp(race["first_scored"]).date()}. A negative difference favors HAR+ATM30. The Duan factor decides the level rule, and the no-factor result is beside it.

{table(races, 4)}

## Clark-West on log loss, without a level factor

HAR is nested in HAR+ATM30. A positive mean favors HAR+ATM30.

{table(clark, 4)}

## Other frozen sensitivity results

GARCH with t errors is primary, and normal errors are also reported. Both are in `reports/stage3_results.md`. Neither affects a verdict. EWMA with the lambda of .94 is primary, and .98 is a sensitivity run, on the common rows of the calibrated race:

{table(ewma, 4)}

## Reconciliation with the review scripts

`review` holds the values in `review/verify_debate.txt`. `study_code` holds the values of this run.

{table(checks, 4)}
"""
    (REPORTS / "stage4_descriptive.md").write_text(text, encoding="utf-8")
    return text
