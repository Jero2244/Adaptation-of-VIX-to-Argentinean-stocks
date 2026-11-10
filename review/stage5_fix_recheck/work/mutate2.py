"""Mutation check on copies of the new code. Each mutant: one change, then tests/test_run_once.py and test_inputs.DateGate on the copy. A survivor means that no test protects that part."""
import os, subprocess, sys, queue, threading
from common import make_copy
RTN, FZN, CFN = "run_tests_once.py", "freeze.py", "config.py"
M = [
 # Guard limits and dates
 ("largest .15 -> .25", RTN, "GUARD_LARGEST = 0.15", "GUARD_LARGEST = 0.25"),
 ("median .02 -> .0205", RTN, "GUARD_MEDIAN = 0.02", "GUARD_MEDIAN = 0.0205"),
 ("share .05 -> .055", RTN, "GUARD_SHARE = 0.05", "GUARD_SHARE = 0.055"),
 ("share gap .05 -> .055", RTN, "GUARD_SHARE_GAP = 0.05", "GUARD_SHARE_GAP = 0.055"),
 ("one source 3 -> 5", RTN, "GUARD_ONE_SOURCE_SESSIONS = 3", "GUARD_ONE_SOURCE_SESSIONS = 5"),
 ("guard no abs", RTN, 'np.log(rows["near_forward"] / rows["close"]).abs()', 'np.log(rows["near_forward"] / rows["close"])'),
 ("guard removed", RTN, "    input_guard(panel, only_alpaca, only_options, alpaca_days ^ option_days)\n", ""),
 ("step_b passes no one-source dates", RTN, "input_guard(panel, only_alpaca, only_options, alpaca_days ^ option_days)", "input_guard(panel, only_alpaca, only_options)"),
 ("step_b one-source dates: alpaca only", RTN, "alpaca_days ^ option_days", "alpaca_days - option_days"),
 ("largest dates: wrong filter", RTN, "days[gap > GUARD_LARGEST]", "days[gap > GUARD_MEDIAN]"),
 ("median dates: wrong filter", RTN, "days[gap > GUARD_MEDIAN])", "days)"),
 ("share dates: wrong filter", RTN, "days[gap > GUARD_SHARE_GAP])", "days)"),
 ("one-source dates unsorted dropped", RTN, 'sorted(one_source_dates))', ')'),
 ("stop screen shows dates", RTN, 'f"The input stop fired: {error}. The dates', 'f"The input stop fired: {error} {error.dates}. The dates'),
 ("stop record keeps no dates", RTN, "dates=error.dates)", "dates=[])"),
 ("stop status is crashed", RTN, 'stop_run(record, record_path, STATUS_INPUT_STOPPED,', 'stop_run(record, record_path, "crashed",'),
 # safe error
 ("safe_error shows every message", RTN, 'if isinstance(error, InputGuardFailed) else ""', 'if True else ""'),
 # stop_run
 ("stop_run: no from None", RTN, "raise SystemExit(1) from None", "raise SystemExit(1)"),
 ("stop_run: write error shows message", RTN, 'not updated: {safe_error(write_error)}"', 'not updated: {write_error}"'),
 ("stop_run: OSError only", RTN, "except Exception as write_error:", "except OSError as write_error:"),
 # show_result
 ("show: no line", RTN, '    print(result["line"])\n    print(result["disclosure"], flush=True)', '    print(result["disclosure"], flush=True)'),
 ("show: no disclosure", RTN, '    print(result["disclosure"], flush=True)\n', ""),
 ("show: no full text", RTN, "            print(result_text)\n", ""),
 ("show: truncated partial counts as kept", RTN, 'kept = partial.read_text(encoding="utf-8") == result_text', 'kept = bool(partial.read_text(encoding="utf-8")) or True'),
 ("show: no try around the write", RTN, '    except Exception as error:\n        print(f"The result write did not finish: {safe_error(error)}", file=sys.stderr)\n', '    except ZeroDivisionError as error:\n        pass\n'),
 ("show: read failure not caught", RTN, "        except OSError:\n            kept = False\n", "        except ZeroDivisionError:\n            kept = False\n"),
 ("show: record not marked finished", RTN, '        record["status"] = "finished"\n        write_json(record_path, record)\n    except Exception as error:', '        pass\n    except Exception as error:'),
 # order
 ("JSON text after finishing", RTN, '        result_text = json.dumps(to_json(result), indent=2)  # Here, so a value that JSON cannot write stays an ordinary crash with nothing shown.\n        record["status"] = freeze.STATUS_FINISHING\n        write_json(record_path, record)\n', '        record["status"] = freeze.STATUS_FINISHING\n        write_json(record_path, record)\n        result_text = json.dumps(to_json(result), indent=2)\n'),
 ("accept: JSON text after finishing", RTN, '            result_text = json.dumps(to_json(result), indent=2)\n            record["status"] = freeze.STATUS_FINISHING\n            write_json(record_path, record)\n', '            record["status"] = freeze.STATUS_FINISHING\n            write_json(record_path, record)\n            result_text = json.dumps(to_json(result), indent=2)\n'),
 ("accept: no finishing write", RTN, '            record["status"] = freeze.STATUS_FINISHING\n            write_json(record_path, record)\n        except Exception as error:\n            stop_run(record, record_path, "crashed", f"The run stopped: {safe_error(error)}")\n', '        except Exception as error:\n            stop_run(record, record_path, "crashed", f"The run stopped: {safe_error(error)}")\n'),
 ("accept: failed write not caught", RTN, '        except Exception as error:\n            stop_run(record, record_path, "crashed", f"The run stopped: {safe_error(error)}")\n', '        except ZeroDivisionError as error:\n            pass\n'),
 ("accept: full show replaced by plain write", RTN, '        show_result(result, result_text, record, record_path, result_path)\n        return result\n', '        write_text(result_path, result_text)\n        record["status"] = "finished"\n        write_json(record_path, record)\n        print(result["line"])\n        print(result["disclosure"])\n        return result\n'),
 ("frames before show", RTN, '    show_result(result, result_text, record, record_path, result_path)\n    try:\n        save_frames(panel, terms)\n    except Exception as error:\n        print(f"The result is safe, but the frames were not saved: {safe_error(error)}", file=sys.stderr)\n', '    try:\n        save_frames(panel, terms)\n    except Exception as error:\n        print(f"The result is safe, but the frames were not saved: {safe_error(error)}", file=sys.stderr)\n    show_result(result, result_text, record, record_path, result_path)\n'),
 ("save error shows raw message", RTN, 'not saved: {safe_error(error)}"', 'not saved: {error}"'),
 ("save without try", RTN, '    try:\n        save_frames(panel, terms)\n    except Exception as error:\n        print(f"The result is safe, but the frames were not saved: {safe_error(error)}", file=sys.stderr)\n', "    save_frames(panel, terms)\n"),
 # retry
 ("retry: no sleep", RTN, "            time.sleep(RENAME_WAIT)\n", "            pass\n"),
 ("retry: 1 try", RTN, "RENAME_TRIES = 5", "RENAME_TRIES = 1"),
 ("retry: raises nothing at the end", RTN, "            if attempt == RENAME_TRIES - 1:\n                raise\n", ""),
 # gates
 ("refuse: partial not checked", RTN, 'result_path.with_suffix(".partial").exists() or ', ""),
 ("refuse: result not checked", RTN, 'if result_path.exists() or ', "if "),
 ("refuse: finishing not checked", RTN, 'record["status"] in ("finished", freeze.STATUS_FINISHING)', 'record["status"] == "finished"'),
 ("refuse: finished not checked", RTN, 'record["status"] in ("finished", freeze.STATUS_FINISHING)', 'record["status"] == freeze.STATUS_FINISHING'),
 ("floor accept: status not checked", RTN, '    if accept_floor_failure and record["status"] != "floor_failed":\n        raise RunRefused("Only a run with a failed data floor can accept that failure.")\n', ""),
 ("stop accept: status not checked", RTN, '    if accept_input_stop and record["status"] != STATUS_INPUT_STOPPED:\n        raise RunRefused("Only a run with an input stop can accept that stop.")\n', ""),
 ("note: not needed after started", RTN, '("started", "crashed", "floor_failed", STATUS_INPUT_STOPPED)', '("crashed", "floor_failed", STATUS_INPUT_STOPPED)'),
 ("note: not needed after input stop", RTN, '("started", "crashed", "floor_failed", STATUS_INPUT_STOPPED)', '("started", "crashed", "floor_failed")'),
 ("blank note counts", RTN, "note = crash_fix_note if crash_fix_note and crash_fix_note.strip() else None", "note = crash_fix_note"),
 ("stale accept permitted", RTN, '    if changed and accepting:\n        raise RunRefused("Frozen files changed after the last attempt, so its counts are out of date. Run again with --crash-fix-note before you accept a stop.")\n', ""),
 ("changed hash needs no note", RTN, '    if changed and not note:\n        raise RunRefused("Frozen files changed after the last attempt. Log the fix in PROTOCOL.md, then pass --crash-fix-note.")\n', ""),
 ("stop rerun needs no change", RTN, '    if record["status"] == STATUS_INPUT_STOPPED and not accepting and not changed:\n        raise RunRefused("No frozen file changed after the input stop, so the same stop would repeat. Fix a bug, or accept the stop with --accept-input-stop.")\n', ""),
 ("expected hash: no check", RTN, '    if expected_hash is not None and expected_hash.strip().lower() != frozen_hash.lower():\n        raise RunRefused("The manifest hash differs from the expected hash. Nothing was read.")\n', ""),
 ("expected hash after the record", RTN, 'if expected_hash is not None and expected_hash.strip().lower() != frozen_hash.lower():', 'if False:'),
 ("no hash on screen", RTN, '    print(f"Manifest SHA-256: {frozen_hash}. Compare it with the hash that the user keeps.", flush=True)\n', ""),
 ("accept floor: passed check removed", RTN, '        if step_a_record["floor"]["passed"]:\n            raise RunRefused("The Step A file shows a floor that passed, so there is no failure to accept.")\n', ""),
 ("accept floor: absent check removed", RTN, '        if not step_a_path.exists():\n            raise RunRefused("The Step A file is absent, so nobody can have read the counts.")\n', ""),
 ("accept stop: no step_a in result", RTN, 'floor=last["step_a"]["floor"], step_a=last["step_a"]["counts"], input_stop', 'input_stop'),
 ("accept floor: no counts in result", RTN, 'floor=step_a_record["floor"], step_a=step_a_record["counts"], line', 'line'),
 ("accept: no hash in attempt", RTN, "accepted_input_stop=accept_input_stop, manifest_sha256=frozen_hash)", "accepted_input_stop=accept_input_stop)"),
 ("accept: no flags in attempt", RTN, "accepted_floor_failure=accept_floor_failure, accepted_input_stop=accept_input_stop, ", ""),
 ("accept: no hash in result", RTN, "result.update(disclosure=DISCLOSURE, manifest_sha256=frozen_hash, finished=now())", "result.update(disclosure=DISCLOSURE, finished=now())"),
 ("accept: no disclosure in result", RTN, "result.update(disclosure=DISCLOSURE, manifest_sha256=frozen_hash, finished=now())", "result.update(manifest_sha256=frozen_hash, disclosure='', finished=now())"),
 ("result: no hash", RTN, "result.update(step_a=counts, disclosure=DISCLOSURE, manifest_sha256=frozen_hash, finished=now())", "result.update(step_a=counts, disclosure=DISCLOSURE, finished=now())"),
 ("attempt: no counts", RTN, '        record["attempts"][-1]["step_a"] = dict(counts=counts, floor=floor)  # A later run overwrites the Step A file, so each attempt keeps its own counts.\n', ""),
 ("Step A file dropped", RTN, "        write_json(step_a_path, dict(counts=counts, floor=floor, written=now()))\n", ""),
 ("step_a: blank rate count is 0", RTN, "int(rates.isna().any(axis=1).sum())", "0"),
 ("counts: blank rate dropped", RTN, "blank_rate_sessions=blank_rate_sessions,", ""),
 ("main: drops --accept-input-stop", RTN, "accept_input_stop=args.accept_input_stop, ", ""),
 ("main: drops --accept-floor-failure", RTN, "accept_floor_failure=args.accept_floor_failure, ", ""),
 ("main: drops --expected-hash", RTN, ", expected_hash=args.expected_hash)", ")"),
 ("main: drops the note", RTN, "run_test(args.crash_fix_note, ", "run_test(None, "),
 ("disclosure empty", RTN, 'result.update(step_a=counts, disclosure=DISCLOSURE,', 'result.update(step_a=counts, disclosure="",'),
 # freeze
 ("ac: status check removed", FZN, ' or record["status"] not in AFTER_CRASH_STATUSES', ""),
 ("ac: finishing permitted", FZN, 'AFTER_CRASH_STATUSES = ("started",', 'AFTER_CRASH_STATUSES = ("finishing", "started",'),
 ("ac: input_stopped refused", FZN, ', "step_a_done", "input_stopped")', ', "step_a_done")'),
 ("ac: partial check removed", FZN, 'result_path.with_suffix(".partial").exists() or ', ""),
 ("ac: result check removed", FZN, 'result_path.exists() or ', ""),
 ("ac: note check removed", FZN, '    if not note or not note.strip():\n        raise FreezeRefused("A crash freeze needs a note")\n', ""),
 ("ac: no-run check removed", FZN, '    if not record_path.exists():\n        raise FreezeRefused("No run has started, so use a normal freeze")\n', "    if not record_path.exists():\n        record_path.write_text('{\"status\":\"started\"}')\n"),
 ("ac: no-change allowed", FZN, '    if not changed:\n        raise FreezeRefused("No frozen file changed, so a new manifest has nothing to record")\n', ""),
 ("ac: input refusal removed", FZN, "    if changed_inputs and not allow_input_change:\n", "    if False:\n"),
 ("ac: default wiring ignores real inputs", FZN, "input_paths = (INPUT_FILES if files is None else []) if inputs is None else inputs", "input_paths = [] if inputs is None else inputs"),
 ("ac main: drops --allow-input-change", FZN, "new = after_crash(args.after_crash, allow_input_change=args.allow_input_change)", "new = after_crash(args.after_crash)"),
 ("ac: no backup", FZN, '    shutil.copyfile(path, path.with_name(f"{path.stem}_{old[:12]}{path.suffix}"))\n', ""),
 ("ac: no changed list", FZN, "new_sha256=new, changed=changed, note=note", "new_sha256=new, note=note"),
 ("ac: no note in entry", FZN, "changed=changed, note=note", "changed=changed"),
 ("ac: manifest before record", FZN, '    partial = record_path.with_suffix(".partial")\n    partial.write_text(json.dumps(record, indent=2), encoding="utf-8")\n    partial.replace(record_path)\n    path.write_text(text, encoding="utf-8", newline="\\n")\n', '    path.write_text(text, encoding="utf-8", newline="\\n")\n    partial = record_path.with_suffix(".partial")\n    partial.write_text(json.dumps(record, indent=2), encoding="utf-8")\n    partial.replace(record_path)\n'),
 ("normal: no refusal", FZN, "        refuse_after_unlock()\n", ""),
 ("normal: partial not refused", FZN, 'RESULT.with_suffix(".partial"), ', ""),
 ("normal: Step A file not refused", FZN, ', REPORTS / "stage5_step_a.json")', ')'),
 ("frozen: tests not hashed", FZN, ' + sorted((root / "tests").glob("*.py"))', ""),
 ("frozen: rule files not hashed", FZN, 'code + [root / name for name in RULE_FILES] + ', "code + "),
 ("frozen: inputs not hashed", FZN, " + list(INPUT_FILES if inputs is None else inputs)", " + list(inputs or [])"),
 ("frozen: Alpaca file not an input", FZN, "OPTION_DEFINITIONS, ALPACA_BARS, ADR_CASH_EVENTS", "OPTION_DEFINITIONS, ADR_CASH_EVENTS"),
 ("verify: no-op", FZN, "    if changed:\n        raise ManifestMismatch", "    if False:\n        raise ManifestMismatch"),
 ("marker: ISO date check removed", CFN, '    try:\n        date.fromisoformat(str(content.get("approved_on")))\n    except ValueError:\n        return False\n', ""),
]
env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
copies = [make_copy(f"mut{i}") for i in range(4)]

def tests(d):
    p = subprocess.run([sys.executable, "-m", "unittest", "test_run_once", "test_inputs.DateGate"], cwd=d / "tests", capture_output=True, text=True, env=env)
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
        path.write_text(src.replace(old, new, 1), encoding="utf-8")
        code, tail = tests(d)
        path.write_text(src, encoding="utf-8")
        with lock:
            results.append(name if code == 0 else None)
            print(f"{'caught  ' if code else 'SURVIVED'}  {name}  [{tail}]", flush=True)

threads = [threading.Thread(target=worker, args=(c,)) for c in copies]
[t.start() for t in threads]; [t.join() for t in threads]
print("mutants:", len(results), "survivors:", sum(1 for r in results if r))
