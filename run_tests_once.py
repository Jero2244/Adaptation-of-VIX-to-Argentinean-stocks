"""Stage 5: the one-time test of 2016-01 to 2018-04, and its rehearsal on open dates. Rules are in PROTOCOL.md.

The test needs the user's approval, in the markers of config.py. This file never creates a marker.
    conda run --no-capture-output -n py4fi python run_tests_once.py --run
Rehearsal on open dates, which needs no marker and writes only to review/stage4_rehearsal/:
    conda run --no-capture-output -n py4fi python run_tests_once.py --rehearse 2020-01-01 2022-04-30

Step A reads options, writes option counts to reports/stage5_step_a.json, and prints counts only. If the data floor fails,
the run stops, and the Alpaca outcomes stay unread. Step B reads the outcomes, checks the inputs, rechecks the floor,
calculates all results in memory, and writes one result file at the end. An error prints only its type and code
locations, so a traceback cannot show a value. An input stop keeps only the failing dates, in the run record.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

import events as ev
import freeze
import realized as rz
import stage4_rules as rules
from build_series import session_rates, series_tables
from build_snapshot import snapshot_tables
from config import (ALPACA_BARS, DATA, DataFault, OPTION_CBBO, OPTIONS_MARKER, OUTCOMES_MARKER, REPORTS, RESULT, ROOT, RUN_RECORD, SCOPE_OPTIONS, SCOPE_OUTCOMES, SOURCE, TEST_END, load_cash_events, marker_opens)
from load_data import day_conditions, load_alpaca_closes

TEST_START = pd.Timestamp("2016-01-01")
PERIOD = "2016-01 to 2018-04 only"
STEP_A_FILE = REPORTS / "stage5_step_a.json"
TEST_OUTPUT = DATA / "test"
TEST_RATES = SOURCE / "fred_rates_test.csv"
REHEARSAL = ROOT / "review" / "stage4_rehearsal"
HAR_START = 22  # log_rv22 needs 22 returns, and the first session has none.
UNUSED_FLAGS = ["flag_ex_in_front", "flag_rights_in_front", "flag_rights_in_bracket", "flag_equity_degraded", "log_forward_to_stock"]
GUARD_MEDIAN = 0.02
GUARD_SHARE_GAP = 0.05
GUARD_SHARE = 0.05
GUARD_LARGEST = 0.15
GUARD_NO_FORWARD = 0.15
GUARD_ONE_SOURCE_SESSIONS = 3
INPUTS_FAILED = "Inconclusive, inputs failed"
STATUS_INPUT_STOPPED = "input_stopped"
RENAME_TRIES = 5  # A virus scanner can hold a new file for a moment on Windows.
RENAME_WAIT = 1.0
DISCLOSURE = ("The user states no contact with 2016-2018 prices. The access log shows that the study printed dividend rows, bar counts, and dates for the period, with no prices or returns. "
              "Code parses of the Alpaca file, the cash file, and the local dividend file held locked rows in memory before a filter removed them, and code also parsed the option condition file, which holds locked dates and no prices. No locked value was shown or written. "
              "The agents report no read of locked values, and nobody audited this. An agent that looked for a rights date read public filings and search summaries. It saw the 2017 offering price and one ADS sale price, and it passed neither to the study. "
              "A rights offering ended on 2017-09-26. Its final prospectus supplement, read through a summarizing tool, says that the rights were not made available to ADS holders, so the cash rows hold no entry for it. Nobody could read the Nasdaq or depositary records, so a depositary sale of those rights is not excluded. The local ex-date is unknown, so the ADS close can show a step on that date with no flag. "
              "Alpaca passed its limits on open dates, which does not prove the same fit in 2016-2017. The test falls entirely before the 2025-03 format break.")


class RunRefused(RuntimeError):
    """The run rules do not permit this run."""


class InputGuardFailed(RuntimeError):
    """An input check failed before any outcome. The message names the check, and it holds no value. The dates of the failing rows stay in an attribute, and they hold no value either."""

    def __init__(self, message: str, dates=()):
        super().__init__(message)
        self.dates = [str(pd.Timestamp(day).date()) for day in dates]


def step_a_counts(series: pd.DataFrame, diagnostics: pd.DataFrame, duplicates: int, blank_rate_sessions: int = 0) -> dict:
    """Option counts only, for a person to read before any outcome. This holds no IV, price, or return."""
    return dict(sessions=len(series), atm30_days=int(series["atm30"].notna().sum()), duplicate_quotes=duplicates, blank_rate_sessions=blank_rate_sessions,
                status_by_year={str(year): {str(k): int(v) for k, v in group["status"].value_counts().items()} for year, group in series.groupby("year")},
                tier_counts={str(k): int(v) for k, v in series["tier"].value_counts().items()} if "tier" in series else {},
                unmatched_quotes=int(diagnostics["unmatched_quotes"].sum()), other_roots=int(diagnostics["other_roots"].sum()), last_row_null_bids=int(diagnostics["last_row_null_bids"].sum()),
                median_rows_per_session=float(diagnostics["cbbo_rows"].median()), median_null_bid_share=float(diagnostics["null_bid_share"].median()),
                first_bars={str(k): int(v) for k, v in diagnostics["first_bar"].value_counts().head(5).items()}, last_bars={str(k): int(v) for k, v in diagnostics["last_bar"].value_counts().head(5).items()})


def step_a(start, end, marker: Path | None, rates_path: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Options only. The cash flags need outcome data, so this step leaves them out. They do not enter a verdict."""
    snapshot, listed, diagnostics = snapshot_tables(start, end, marker, use_equity=False, progress=False)
    diagnostics = diagnostics.set_index("session_date")
    rates = session_rates(diagnostics.index.sort_values(), rates_path)
    empty = np.array([], dtype="datetime64[ns]")
    series, terms, duplicates = series_tables(snapshot, listed, diagnostics, rates, empty, empty, day_conditions(OPTION_CBBO), {})
    series = series.drop(columns=[name for name in UNUSED_FLAGS if name in series.columns])
    return series, terms, step_a_counts(series, diagnostics, duplicates, int(rates.isna().any(axis=1).sum()))


def floor_from_flags(series: pd.DataFrame) -> dict:
    """The data floor from the option days only, before any return is read. Each target window must end on or before the last session."""
    dates = series["session_date"].to_numpy()
    ends = dates + np.timedelta64(rz.WINDOW_DAYS, "D")
    positions = np.arange(len(dates))
    return rules.data_floor(series["atm30"].notna().to_numpy() & (positions >= HAR_START) & (ends <= dates[-1]))


def input_guard(panel: pd.DataFrame, only_alpaca: int, only_options: int, one_source_dates=()) -> None:
    """Stop before any outcome if the options and the closes do not fit. It returns nothing, and a stop carries dates only, so it shows no value.

    A wrong option map or a bad close moves the near forward away from the close. The limits compare with the open
    data: yearly medians of at most .0046, 6 of 1,817 rows above 5%, and a largest gap of .087.
    """
    if only_alpaca + only_options > GUARD_ONE_SOURCE_SESSIONS:
        raise InputGuardFailed("More than 3 sessions are in one source only", sorted(one_source_dates))
    if "near_forward" not in panel.columns:
        raise InputGuardFailed("The series has no near forward")
    rows = panel.dropna(subset=["near_forward", "close"])
    if rows.empty:
        raise InputGuardFailed("No session has both a near forward and a close")
    gap = np.log(rows["near_forward"] / rows["close"]).abs()
    days = rows["session_date"]
    if gap.median() > GUARD_MEDIAN:
        raise InputGuardFailed("The median gap of forward and close is above the limit", days[gap > GUARD_MEDIAN])
    if (gap > GUARD_SHARE_GAP).mean() > GUARD_SHARE:
        raise InputGuardFailed("The share of large gaps of forward and close is above the limit", days[gap > GUARD_SHARE_GAP])
    if gap.max() > GUARD_LARGEST:
        raise InputGuardFailed("The largest gap of forward and close is above the limit", days[gap > GUARD_LARGEST])
    far = no_forward_gaps(panel) > GUARD_NO_FORWARD
    stray = far & (adjacent_close_gaps(panel).reindex(far.index) > GUARD_NO_FORWARD)
    if stray.any():
        raise InputGuardFailed("A close on a session with no forward is far from the forwards on both sides and from the adjacent closes", panel.loc[stray[stray].index, "session_date"])


def no_forward_gaps(panel: pd.DataFrame) -> pd.Series:
    """On sessions with a close and no near forward: the smaller absolute log gap to the nearest forward on each side. A real jump stays near one side, and a bad close is far from both."""
    ordered = panel.sort_values("session_date")
    forward = ordered["near_forward"]
    before = np.log(ordered["close"] / forward.ffill().shift(1)).abs()
    after = np.log(ordered["close"] / forward.bfill().shift(-1)).abs()
    return pd.concat([before, after], axis=1).min(axis=1)[forward.isna() & ordered["close"].notna()]


def adjacent_close_gaps(panel: pd.DataFrame) -> pd.Series:
    """On each session: the smaller absolute log gap to the close before and the close after. A drift during a blank run stays near an adjacent close, and an isolated bad close is far from both."""
    close = panel.sort_values("session_date")["close"]
    return pd.concat([np.log(close / close.shift(1)).abs(), np.log(close / close.shift(-1)).abs()], axis=1).min(axis=1)


def step_b(series: pd.DataFrame, start, end, marker: Path | None, event_list, reps: int = rules.REPS, period: str = PERIOD, bars_path: Path = ALPACA_BARS) -> tuple[dict, pd.DataFrame]:
    """Read the outcomes, check the inputs, and calculate every result in memory. The frame ends at end, so it never joins later data."""
    try:
        closes = load_alpaca_closes(start, end, marker, bars_path)
        alpaca_days, option_days = set(closes["session_date"]), set(series["session_date"])
        only_alpaca = len(alpaca_days - option_days)
        only_options = len(option_days - alpaca_days)
        realized = rz.realized_from_closes(closes, load_cash_events(start, end, marker))
    except DataFault as fault:
        raise InputGuardFailed(str(fault), fault.dates) from None
    panel = rules.add_inputs(realized.merge(series, on="session_date", how="left", validate="one_to_one"))
    input_guard(panel, only_alpaca, only_options, alpaca_days ^ option_days)
    days = panel["session_date"].to_numpy()
    event_sessions = [ev.first_session(date, days) for _, date in event_list]
    result = rules.evaluate(panel, event_sessions, reps, period)
    gaps = np.diff(days) / np.timedelta64(1, "D")
    result["counts"] = dict(alpaca_sessions=len(closes), option_sessions=len(series), only_alpaca=only_alpaca, only_options=only_options, largest_calendar_gap=float(gaps.max()), first_session=str(pd.Timestamp(days[0]).date()), last_session=str(pd.Timestamp(days[-1]).date()), last_window_end=str(panel.loc[panel["rv30"].notna(), "window_end"].max().date()))
    return result, panel


def to_json(value):
    if value is pd.NaT:
        return None
    if isinstance(value, dict):
        return {str(k): to_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_json(v) for v in value]
    if isinstance(value, (np.floating, float)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (pd.Timestamp, np.datetime64)):
        return str(pd.Timestamp(value).date())
    return value


def write_text(path: Path, text: str) -> None:
    """Write through a .partial file. A failed rename gets a few more tries, and then it raises."""
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(".partial")
    partial.write_text(text, encoding="utf-8")
    for attempt in range(RENAME_TRIES):
        try:
            partial.replace(path)
            return
        except OSError:
            if attempt == RENAME_TRIES - 1:
                raise
            time.sleep(RENAME_WAIT)


def write_json(path: Path, value: dict) -> None:
    write_text(path, json.dumps(to_json(value), indent=2))


def read_record(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else dict(status="none", attempts=[])


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_error(error: BaseException) -> str:
    """The error type and code locations only. The message and the variables can hold values, so they stay out. A guard message holds no value."""
    frames = [f"{Path(frame.filename).name}:{frame.lineno} {frame.name}" for frame in traceback.extract_tb(error.__traceback__)]
    detail = f" ({error})" if isinstance(error, InputGuardFailed) else ""
    return f"{type(error).__name__}{detail} at " + " > ".join(frames)


def say(text: str, stream=None) -> None:
    """Print, and never raise. A new error inside an except block would carry the original error, and its message can hold a value."""
    try:
        print(text, file=stream if stream is not None else sys.stdout, flush=True)
    except BaseException:
        pass


def safe_excepthook(kind, error, trace) -> None:
    """The last guard: an uncaught error shows its type and code locations only. A refusal holds no value, so it keeps its message."""
    try:
        say(f"{kind.__name__}: {error}" if isinstance(error, (RunRefused, freeze.ManifestMismatch)) else safe_error(error), sys.stderr)
    except BaseException:
        pass  # If the hook raises, Python prints the original error, and its message can hold a value.


def stop_run(record: dict, record_path: Path, status: str, message: str) -> None:
    """Stop with one safe message. A failed record write must not let Python print the original error, because that message can hold a value."""
    record["status"] = status
    try:
        write_json(record_path, record)
    except BaseException as write_error:
        say(f"The run record was not updated, so what it should hold is lost: {safe_error(write_error)}", sys.stderr)
    say(message, sys.stderr)
    raise SystemExit(1) from None


def history(attempts: list[dict], refreezes: list[dict]) -> dict:
    """What came before this result: notes, errors, input stops, and refreezes. These hold no outcome value."""
    keys = ("started", "manifest_sha256", "crash_fix_note", "error", "input_stop")
    return dict(attempts=[{key: attempt[key] for key in keys if key in attempt} for attempt in attempts], refreezes=refreezes)


def disclosure_for(past: dict) -> str:
    if any("input_stop" in attempt for attempt in past["attempts"]):
        return f"{DISCLOSURE} An earlier attempt stopped at the input check, and a person read the failing dates before this result. See the history in the result file."
    return DISCLOSURE


def show_result(result: dict, result_text: str, record: dict, record_path: Path, result_path: Path) -> None:
    """The record says finishing, so no rerun can happen. Whatever fails now, the person still gets the outcome: this is the one result."""
    try:
        write_text(result_path, result_text)
        record["status"] = "finished"
        write_json(record_path, record)
    except BaseException as error:
        say(f"The result write did not finish: {safe_error(error)}", sys.stderr)
    if not result_path.exists():
        partial = result_path.with_suffix(".partial")
        try:
            kept = partial.read_text(encoding="utf-8") == result_text
        except BaseException:  # The text below must still print after a failed read or a second Ctrl-C.
            kept = False
        if kept:
            say(f"The full result is in {partial.name}. Under PROTOCOL.md, this file is the result.", sys.stderr)
        else:
            say("No file holds the result. Save the text below. Under PROTOCOL.md, it is the result.", sys.stderr)
            say(result_text)
    say(result["line"])
    say(result["disclosure"])


def accepted_stop(record: dict, step_a_path: Path, accept_floor_failure: bool) -> dict:
    """The final result after a person reads the counts or the dates. No outcome value enters it."""
    if accept_floor_failure:
        if not step_a_path.exists():
            raise RunRefused("The Step A file is absent, so nobody can have read the counts.")
        step_a_record = json.loads(step_a_path.read_text(encoding="utf-8"))
        if step_a_record["floor"]["passed"]:
            raise RunRefused("The Step A file shows a floor that passed, so there is no failure to accept.")
        return dict(decision=dict(outcome=rules.NO_FLOOR), floor=step_a_record["floor"], step_a=step_a_record["counts"], line=f"{rules.NO_FLOOR}. {PERIOD}. The outcomes stayed unread.")
    last = record["attempts"][-1]
    return dict(decision=dict(outcome=INPUTS_FAILED), floor=last["step_a"]["floor"], step_a=last["step_a"]["counts"], input_stop=last["input_stop"], line=f"{INPUTS_FAILED}. {PERIOD}. The run read the closes for the input check and calculated no result.")


def run_test(crash_fix_note: str | None = None, record_path: Path = RUN_RECORD, result_path: Path = RESULT, options_marker: Path = OPTIONS_MARKER, outcomes_marker: Path = OUTCOMES_MARKER, check_manifest: Callable[[], None] = freeze.verify_manifest, run_a: Callable | None = None, run_b: Callable | None = None, save_frames: Callable | None = None, manifest_hash: Callable[[], str] = freeze.manifest_hash, step_a_path: Path = STEP_A_FILE, accept_floor_failure: bool = False, accept_input_stop: bool = False, expected_hash: str | None = None) -> dict:
    """Run the test once. Crash rule: a logged fix is allowed until an outcome is displayed or written. After that, no rerun."""
    run_a = run_a or (lambda: step_a(TEST_START, TEST_END, options_marker, TEST_RATES))
    run_b = run_b or (lambda series: step_b(series, TEST_START, TEST_END, outcomes_marker, ev.TEST_EVENTS))
    save_frames = save_frames or save_test_frames
    note = crash_fix_note if crash_fix_note and crash_fix_note.strip() else None
    accepting = accept_floor_failure or accept_input_stop
    record = read_record(record_path)
    if result_path.exists() or result_path.with_suffix(".partial").exists() or record["status"] in ("finished", freeze.STATUS_FINISHING):
        raise RunRefused("The one-time test has already produced a result, or an outcome may exist. A second run is not permitted.")
    if accept_floor_failure and record["status"] != "floor_failed":
        raise RunRefused("Only a run with a failed data floor can accept that failure.")
    if accept_input_stop and record["status"] != STATUS_INPUT_STOPPED:
        raise RunRefused("Only a run with an input stop can accept that stop.")
    if record["status"] in ("started", "crashed", "floor_failed", STATUS_INPUT_STOPPED) and not (note or accepting):
        raise RunRefused("An earlier attempt did not finish. Log the fix in PROTOCOL.md, run freeze.py --after-crash if a frozen file changed, then pass --crash-fix-note.")
    if not marker_opens(options_marker, SCOPE_OPTIONS):
        raise RunRefused("The options marker is absent or not valid. Only the user can approve the test. A marker must be plain UTF-8 JSON with an ISO date.")
    check_manifest()
    frozen_hash = manifest_hash()
    print(f"Manifest SHA-256: {frozen_hash}. Compare it with the hash that the user keeps.", flush=True)
    if expected_hash is not None and expected_hash.strip().lower() != frozen_hash.lower():
        raise RunRefused("The manifest hash differs from the expected hash. Nothing was read.")
    changed = bool(record["attempts"]) and record["attempts"][-1].get("manifest_sha256") != frozen_hash
    if changed and accepting:
        raise RunRefused("Frozen files changed after the last attempt, so its counts are out of date. Run again with --crash-fix-note before you accept a stop.")
    if changed and not note:
        raise RunRefused("Frozen files changed after the last attempt. Log the fix in PROTOCOL.md, then pass --crash-fix-note.")
    if record["status"] == STATUS_INPUT_STOPPED and not accepting and not changed:
        raise RunRefused("No frozen file changed after the input stop, so the same stop would repeat. Fix a bug, or accept the stop with --accept-input-stop.")
    if accepting:
        result = accepted_stop(record, step_a_path, accept_floor_failure)
        past = history(record["attempts"], record.get("refreezes", []))
        result.update(history=past, crash_fix_note=note, disclosure=disclosure_for(past), manifest_sha256=frozen_hash, finished=now())
        record["attempts"].append(dict(started=now(), crash_fix_note=note, accepted_floor_failure=accept_floor_failure, accepted_input_stop=accept_input_stop, manifest_sha256=frozen_hash))
        try:
            result_text = json.dumps(to_json(result), indent=2)
            record["status"] = freeze.STATUS_FINISHING
            write_json(record_path, record)
        except Exception as error:
            stop_run(record, record_path, "crashed", f"The run stopped: {safe_error(error)}")
        show_result(result, result_text, record, record_path, result_path)
        return result
    record["attempts"].append(dict(started=now(), crash_fix_note=note, manifest_sha256=frozen_hash))
    record["status"] = "started"
    write_json(record_path, record)
    try:
        series, terms, counts = run_a()
        floor = floor_from_flags(series)
        write_json(step_a_path, dict(counts=counts, floor=floor, written=now()))
        record["attempts"][-1]["step_a"] = dict(counts=counts, floor=floor)  # A later run overwrites the Step A file, so each attempt keeps its own counts.
        write_json(record_path, record)
        print(f"Step A: {counts['sessions']} sessions, {counts['atm30_days']} ATM30 days. Floor: {floor}. Details: {step_a_path.name}", flush=True)
        if not floor["passed"]:
            record["status"] = "floor_failed"
            write_json(record_path, record)
            print("The data floor failed, and the outcomes stay unread. Read the counts. If a bug caused this, fix it with the crash rule. If not, pass --accept-floor-failure.")
            return dict(decision=None, floor=floor, step_a=counts)
        if not marker_opens(outcomes_marker, SCOPE_OUTCOMES):
            record["status"] = "step_a_done"
            write_json(record_path, record)
            print("Step A passed. The outcomes marker is absent, so the run stops before any outcome.")
            return dict(decision=None, floor=floor, step_a=counts)
        result, panel = run_b(series)
        past = history(record["attempts"][:-1], record.get("refreezes", []))
        result.update(step_a=counts, history=past, crash_fix_note=note, disclosure=disclosure_for(past), manifest_sha256=frozen_hash, finished=now())
        result_text = json.dumps(to_json(result), indent=2)  # Here, so a value that JSON cannot write stays an ordinary crash with nothing shown.
        record["status"] = freeze.STATUS_FINISHING
        write_json(record_path, record)
    except InputGuardFailed as error:
        record["attempts"][-1]["error"] = safe_error(error)
        record["attempts"][-1]["input_stop"] = dict(check=str(error), dates=error.dates)
        stop_run(record, record_path, STATUS_INPUT_STOPPED, f"The input stop fired: {error}. The dates of the failing rows are in {record_path.name}, with no values. Fix a bug under the crash rule, or accept the stop with --accept-input-stop.")
    except Exception as error:
        record["attempts"][-1]["error"] = safe_error(error)
        stop_run(record, record_path, "crashed", f"The run stopped: {record['attempts'][-1]['error']}")
    show_result(result, result_text, record, record_path, result_path)
    try:
        save_frames(panel, terms)
    except Exception as error:
        say(f"The frames were not saved: {safe_error(error)}", sys.stderr)
    return result


def save_test_frames(panel: pd.DataFrame, terms: pd.DataFrame) -> None:
    TEST_OUTPUT.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(TEST_OUTPUT / "test_panel.parquet", index=False)
    terms.to_parquet(TEST_OUTPUT / "test_terms.parquet", index=False)


def rehearse(start: str, end: str, reps: int = rules.REPS, output: Path = REHEARSAL) -> dict:
    """The same code on one open window. It reads no locked date, and it gives no evidence for the claim."""
    first, last = pd.Timestamp(start), pd.Timestamp(end)
    series, _, counts = step_a(first, last, None, SOURCE / "fred_rates.csv")
    floor = floor_from_flags(series)
    events_in_window = [item for item in ev.EVENTS if first <= pd.Timestamp(item[1]) <= last]
    result, panel = step_b(series, first, last, None, events_in_window, reps, f"{start} to {end}, rehearsal on seen data")
    open_series = pd.read_parquet(DATA / "index_series.parquet")
    joined = series[["session_date", "atm30"]].merge(open_series[["session_date", "atm30"]], on="session_date", suffixes=("", "_open"), validate="one_to_one")
    result.update(step_a=counts, floor_from_flags=floor, rehearsal=dict(sessions_joined=len(joined), series_matches_open=bool(np.allclose(joined["atm30"], joined["atm30_open"], rtol=1e-12, atol=0, equal_nan=True))))
    write_json(output / f"rehearsal_{start}_{end}.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--run", action="store_true")
    group.add_argument("--rehearse", nargs=2, metavar=("START", "END"))
    parser.add_argument("--crash-fix-note")
    parser.add_argument("--accept-floor-failure", action="store_true")
    parser.add_argument("--accept-input-stop", action="store_true")
    parser.add_argument("--expected-hash", help="The hash that the user keeps. A mismatch refuses the run before any read.")
    args = parser.parse_args()
    sys.excepthook = safe_excepthook
    if args.rehearse:
        result = rehearse(*args.rehearse)
        print(json.dumps(to_json(dict(line=result["line"], floor=result["floor"], floor_from_flags=result["floor_from_flags"], counts=result["counts"], step_a=result["step_a"], rehearsal=result["rehearsal"], rule1=result["rule1"], race_scored=result["race"]["scored"])), indent=2))
    else:
        run_test(args.crash_fix_note, accept_floor_failure=args.accept_floor_failure, accept_input_stop=args.accept_input_stop, expected_hash=args.expected_hash)


if __name__ == "__main__":
    main()
