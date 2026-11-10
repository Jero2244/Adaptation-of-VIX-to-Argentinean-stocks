"""Mutation test of this fix round only, on copies. Each mutant is one change, then the test files of these changes run on the copy."""
import os, subprocess, sys, queue, threading
from common import make_copy
RT, FZ, CF, LD, RZ = "run_tests_once.py", "freeze.py", "config.py", "load_data.py", "realized.py"
M = [
 # no_forward_gaps and branch
 ("nf: no sort", RT, 'ordered = panel.sort_values("session_date")', 'ordered = panel'),
 ("nf: max, not min", RT, 'pd.concat([before, after], axis=1).min(axis=1)', 'pd.concat([before, after], axis=1).max(axis=1)'),
 ("nf: before only", RT, 'pd.concat([before, after], axis=1).min(axis=1)', 'before'),
 ("nf: after only", RT, 'pd.concat([before, after], axis=1).min(axis=1)', 'after'),
 ("nf: after uses ffill", RT, 'forward.bfill().shift(-1)', 'forward.ffill().shift(1)'),
 ("nf: before no abs", RT, 'forward.ffill().shift(1)).abs()', 'forward.ffill().shift(1))'),
 ("nf: after no abs", RT, 'forward.bfill().shift(-1)).abs()', 'forward.bfill().shift(-1))'),
 ("nf: skipna false", RT, '.min(axis=1)[forward', '.min(axis=1, skipna=False)[forward'),
 ("nf: limit .15 -> .16", RT, 'stray = no_forward_gaps(panel) > GUARD_NO_FORWARD', 'stray = no_forward_gaps(panel) > 0.16'),
 ("nf: >= limit", RT, 'stray = no_forward_gaps(panel) > GUARD_NO_FORWARD', 'stray = no_forward_gaps(panel) >= GUARD_NO_FORWARD'),
 ("nf: branch removed", RT, '    if stray.any():\n', '    if False:\n'),
 ("nf: dates all rows", RT, 'panel.loc[stray[stray].index, "session_date"])', 'panel["session_date"])'),
 ("nf: dates positional", RT, 'panel.loc[stray[stray].index, "session_date"]', 'panel["session_date"].iloc[list(stray[stray].index)]'),
 ("nf: dates all no-forward", RT, 'panel.loc[stray[stray].index, "session_date"]', 'panel.loc[stray.index, "session_date"]'),
 ("nf: message holds a value", RT, '"A close on a session with no forward is far from the forwards on both sides"', 'f"A close on a session with no forward is far: {stray.index[0]} {panel[\'close\'].max()}"'),
 ("nf: before the other checks", RT, '    gap = np.log(rows["near_forward"] / rows["close"]).abs()\n', '    gap = np.log(rows["near_forward"] / rows["close"]).abs()\n    if (no_forward_gaps(panel) > GUARD_NO_FORWARD).any():\n        raise InputGuardFailed("A close on a session with no forward is far from the forwards on both sides", [])\n'),
 # DataFault
 ("df: step_b does not convert", RT, '    except DataFault as fault:\n        raise InputGuardFailed(str(fault), fault.dates) from None\n', '    except ZeroDivisionError as fault:\n        raise\n'),
 ("df: drops the dates", RT, 'raise InputGuardFailed(str(fault), fault.dates) from None', 'raise InputGuardFailed(str(fault)) from None'),
 ("df: no from None", RT, 'raise InputGuardFailed(str(fault), fault.dates) from None', 'raise InputGuardFailed(str(fault), fault.dates)'),
 ("df: fixed text", RT, 'raise InputGuardFailed(str(fault), fault.dates) from None', 'raise InputGuardFailed("A data fault", fault.dates) from None'),
 ("df: realized outside the try", RT, '        realized = rz.realized_from_closes(closes, load_cash_events(start, end, marker))\n    except DataFault as fault:\n        raise InputGuardFailed(str(fault), fault.dates) from None\n', '    except DataFault as fault:\n        raise InputGuardFailed(str(fault), fault.dates) from None\n    realized = rz.realized_from_closes(closes, load_cash_events(start, end, marker))\n'),
 ("df: closes outside the try", RT, '        closes = load_alpaca_closes(start, end, marker, bars_path)\n', '        pass\n    except DataFault:\n        pass\n    closes = load_alpaca_closes(start, end, marker, bars_path)\n    try:\n'),
 ("df: not a ValueError", CF, 'class DataFault(ValueError):', 'class DataFault(RuntimeError):'),
 ("df: no bar is plain", LD, 'raise DataFault("The Alpaca file has no bar in the requested dates")', 'raise ValueError("no bar")'),
 ("df: two bars is plain", LD, 'raise DataFault("The Alpaca file has two bars on one New York date", frame.loc[repeated, "session_date"].drop_duplicates())', 'raise ValueError("two bars")'),
 ("df: two bars no drop_duplicates", LD, 'frame.loc[repeated, "session_date"].drop_duplicates()', 'frame.loc[repeated, "session_date"]'),
 ("df: two bars keep default", LD, 'frame["session_date"].duplicated(keep=False)', 'frame["session_date"].duplicated()'),
 ("df: two bars not checked", LD, '    if repeated.any():\n', '    if False:\n'),
 ("df: close is plain", LD, 'raise DataFault("A close is missing or not positive", frame.loc[~usable, "session_date"])', 'raise ValueError("close")'),
 ("df: close dates all", LD, 'frame.loc[~usable, "session_date"]', 'frame["session_date"]'),
 ("df: close zero passes", LD, 'usable = frame["close"] > 0', 'usable = frame["close"] >= 0'),
 ("df: close NaN passes", LD, 'usable = frame["close"] > 0', 'usable = ~(frame["close"] <= 0)'),
 ("df: close message holds a value", LD, '"A close is missing or not positive"', 'f"A close is missing or not positive {frame[\'close\'].min()}"'),
 ("df: layout becomes a stop", LD, 'raise ValueError("The Alpaca file does not have the expected layout") from None', 'raise DataFault("The Alpaca file does not have the expected layout") from None'),
 ("df: ex-date plain", RZ, 'raise DataFault("An ex-date is not a session", missing)', 'raise ValueError("ex")'),
 ("df: ex-date no dates", RZ, 'raise DataFault("An ex-date is not a session", missing)', 'raise DataFault("An ex-date is not a session")'),
 ("df: ex-date not checked", RZ, '    if len(missing):\n', '    if False:\n'),
 ("df: ex-date message holds an amount", RZ, '"An ex-date is not a session"', 'f"An ex-date is not a session {events[\'usd_per_ads\'].iloc[0]}"'),
 # say, hook, stop_run, show_result
 ("say: Exception only", RT, '    except BaseException:\n        pass\n', '    except Exception:\n        pass\n'),
 ("say: no guard", RT, '    try:\n        print(text, file=stream if stream is not None else sys.stdout, flush=True)\n    except BaseException:\n        pass\n', '    print(text, file=stream if stream is not None else sys.stdout, flush=True)\n'),
 ("say: stream ignored", RT, 'file=stream if stream is not None else sys.stdout', 'file=sys.stdout'),
 ("hook: refusal message lost", RT, 'f"{kind.__name__}: {error}" if isinstance(error, (RunRefused, freeze.ManifestMismatch)) else safe_error(error)', 'safe_error(error)'),
 ("hook: mismatch message lost", RT, 'isinstance(error, (RunRefused, freeze.ManifestMismatch))', 'isinstance(error, RunRefused)'),
 ("hook: every message shown", RT, 'isinstance(error, (RunRefused, freeze.ManifestMismatch))', 'True'),
 ("hook: not installed", RT, '    sys.excepthook = safe_excepthook\n', ''),
 ("hook: to stdout", RT, 'else safe_error(error), sys.stderr)', 'else safe_error(error))'),
 ("stop_run: Exception only", RT, '    except BaseException as write_error:', '    except Exception as write_error:'),
 ("stop_run: raw write error", RT, 'lost: {safe_error(write_error)}"', 'lost: {write_error}"'),
 ("stop_run: exit 0", RT, 'raise SystemExit(1) from None', 'raise SystemExit(0) from None'),
 ("stop_run: message not said", RT, '    say(message, sys.stderr)\n', ''),
 ("show: Exception only", RT, '    except BaseException as error:\n        say(f"The result write', '    except Exception as error:\n        say(f"The result write'),
 ("show: read OSError only", RT, 'except (OSError, ValueError):', 'except OSError:'),
 ("show: no full text", RT, '            say(result_text)\n', ''),
 ("show: no line", RT, '    say(result["line"])\n', ''),
 ("show: no disclosure", RT, '    say(result["disclosure"])\n', ''),
 ("show: raw write error", RT, 'did not finish: {safe_error(error)}"', 'did not finish: {error}"'),
 ("frames: raw error", RT, 'not saved: {safe_error(error)}"', 'not saved: {error}"'),
 ("frames: Exception -> OSError", RT, '        save_frames(panel, terms)\n    except Exception as error:', '        save_frames(panel, terms)\n    except OSError as error:'),
 # history
 ("hist: normal counts this attempt", RT, 'past = history(record["attempts"][:-1], record.get("refreezes", []))', 'past = history(record["attempts"], record.get("refreezes", []))'),
 ("hist: accept drops the last", RT, 'past = history(record["attempts"], record.get("refreezes", []))\n        result.update(history=past', 'past = history(record["attempts"][:-1], record.get("refreezes", []))\n        result.update(history=past'),
 ("hist: keeps step_a", RT, 'keys = ("started", "manifest_sha256", "crash_fix_note", "error", "input_stop")', 'keys = ("started", "manifest_sha256", "crash_fix_note", "error", "input_stop", "step_a")'),
 ("hist: no input_stop", RT, '"crash_fix_note", "error", "input_stop")', '"crash_fix_note", "error")'),
 ("hist: no error", RT, '"crash_fix_note", "error", "input_stop")', '"crash_fix_note", "input_stop")'),
 ("hist: no note", RT, '"manifest_sha256", "crash_fix_note", "error"', '"manifest_sha256", "error"'),
 ("hist: no refreezes", RT, 'for key in keys if key in attempt} for attempt in attempts], refreezes=refreezes)', 'for key in keys if key in attempt} for attempt in attempts], refreezes=[])'),
 ("hist: not in accept result", RT, 'result.update(history=past, disclosure=disclosure_for(past), manifest_sha256', 'result.update(disclosure=disclosure_for(past), manifest_sha256'),
 ("hist: not in normal result", RT, 'result.update(step_a=counts, history=past, disclosure', 'result.update(step_a=counts, disclosure'),
 ("disc: normal ignores the stop", RT, 'result.update(step_a=counts, history=past, disclosure=disclosure_for(past)', 'result.update(step_a=counts, history=past, disclosure=DISCLOSURE'),
 ("disc: accept ignores the stop", RT, 'result.update(history=past, disclosure=disclosure_for(past)', 'result.update(history=past, disclosure=DISCLOSURE'),
 ("disc: always says a stop", RT, 'if any("input_stop" in attempt for attempt in past["attempts"]):', 'if True:'),
 # freeze
 ("rm: plain write", FZ, '    partial = path.with_suffix(".partial")\n    partial.write_text(text, encoding="utf-8", newline="\\n")\n    partial.replace(path)\n', '    path.write_text(text, encoding="utf-8", newline="\\n")\n'),
 ("rm: CRLF on Windows", FZ, 'partial.write_text(text, encoding="utf-8", newline="\\n")', 'partial.write_text(text, encoding="utf-8")'),
 ("rm: partial kept and copied", FZ, '    partial.replace(path)\n    \n', '    partial.replace(path)\n'),
 ("rm: write_manifest not through", FZ, '    replace_manifest(path, manifest_text(files, root))\n', '    path.write_text(manifest_text(files, root), encoding="utf-8", newline="\\n")\n'),
 ("rm: after_crash not through", FZ, '    replace_manifest(path, text)\n    return new\n', '    path.write_text(text, encoding="utf-8", newline="\\n")\n    return new\n'),
]
env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
copies = [make_copy(f"mut{i}") for i in range(4)]

def tests(d):
    p = subprocess.run([sys.executable, "-m", "unittest", "test_run_once", "test_alpaca"], cwd=d / "tests", capture_output=True, text=True, env=env)
    tail = p.stderr.strip().splitlines()[-1] if p.stderr.strip() else ""
    return p.returncode, tail

print("baseline:", tests(copies[0]), flush=True)
q = queue.Queue()
for m in M:
    q.put(m)
lock = threading.Lock()
results = []

def worker(d):
    while True:
        try:
            name, file, old, new = q.get_nowait()
        except queue.Empty:
            return
        path = d / file
        src = path.read_text(encoding="utf-8")
        if src.count(old) < 1:
            with lock:
                print(f"NOT APPLIED  {name}", flush=True)
            continue
        path.write_text(src.replace(old, new, 1), encoding="utf-8", newline="")
        code, tail = tests(d)
        path.write_text(src, encoding="utf-8", newline="")
        with lock:
            results.append(name if code == 0 else None)
            print(f"{'caught  ' if code else 'SURVIVED'}  {name}  [{tail}]", flush=True)

threads = [threading.Thread(target=worker, args=(c,)) for c in copies]
[t.start() for t in threads]; [t.join() for t in threads]
print("mutants:", len(results), "survivors:", sum(1 for r in results if r))
