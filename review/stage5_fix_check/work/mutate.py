"""Mutation check on a code copy: apply one change to a fix, run tests/test_run_once.py in the copy, and see if a test fails. A survivor means that no test protects that part of the fix."""
import os, subprocess, sys
from common import *
d = make_copy("mutants")
RT, FZ, CF = d / "run_tests_once.py", d / "freeze.py", d / "config.py"
rt0, fz0, cf0 = RT.read_text(encoding="utf-8"), FZ.read_text(encoding="utf-8"), CF.read_text(encoding="utf-8")
M = [
 ("guard removed from step_b", RT, "    input_guard(panel, only_alpaca, only_options)\n", ""),
 ("guard moved after evaluate", RT, "    input_guard(panel, only_alpaca, only_options)\n    days = panel", "    days = panel"),
 ("guard limit largest .25 -> .40", RT, "GUARD_LARGEST = 0.25", "GUARD_LARGEST = 0.40"),
 ("guard limit median .02 -> .0205", RT, "GUARD_MEDIAN = 0.02", "GUARD_MEDIAN = 0.0205"),
 ("guard limit share .05 -> .055", RT, "GUARD_SHARE = 0.05", "GUARD_SHARE = 0.055"),
 ("guard share gap .05 -> .055", RT, "GUARD_SHARE_GAP = 0.05", "GUARD_SHARE_GAP = 0.055"),
 ("one-source limit 3 -> 5", RT, "GUARD_ONE_SOURCE_SESSIONS = 3", "GUARD_ONE_SOURCE_SESSIONS = 5"),
 ("one source: only_options ignored", RT, "only_alpaca + only_options > GUARD", "only_alpaca > GUARD"),
 ("one source: only_alpaca ignored", RT, "only_alpaca + only_options > GUARD", "only_options > GUARD"),
 ("guard: no abs", RT, 'np.log(rows["near_forward"] / rows["close"]).abs()', 'np.log(rows["near_forward"] / rows["close"])'),
 ("Step A file written after the floor branch (dropped)", RT, "        write_json(step_a_path, dict(counts=counts, floor=floor, written=now()))\n", ""),
 ("floor failure no longer stops", RT, '        if not floor["passed"]:\n', '        if False:\n'),
 ("floor_failed status replaced by crashed", RT, 'record["status"] = "floor_failed"', 'record["status"] = "crashed"'),
 ("accept: needs no failed floor", RT, '    if accept_floor_failure and record["status"] != "floor_failed":\n        raise RunRefused("Only a run with a failed data floor can accept that failure.")\n', ""),
 ("accept: no manifest hash in attempt", RT, "accepted_floor_failure=True, manifest_sha256=frozen_hash", "accepted_floor_failure=True"),
 ("accept: no manifest hash in result", RT, "disclosure=DISCLOSURE, manifest_sha256=frozen_hash, finished=now())\n        record[", "disclosure=DISCLOSURE, finished=now())\n        record["),
 ("accept: no disclosure in result", RT, 'The outcomes stayed unread.", disclosure=DISCLOSURE,', 'The outcomes stayed unread.",'),
 ("accept: file floor ignored", RT, 'floor=step_a_record["floor"], ', ""),
 ("partial check removed from run_test", RT, 'result_path.with_suffix(".partial").exists() or ', ""),
 ("no finishing status", RT, "    record[\"status\"] = freeze.STATUS_FINISHING\n    write_json(record_path, record)\n", ""),
 ("finishing not refused in run_test", RT, 'record["status"] in ("finished", freeze.STATUS_FINISHING)', 'record["status"] == "finished"'),
 ("finished not refused in run_test", RT, 'record["status"] in ("finished", freeze.STATUS_FINISHING)', 'record["status"] == freeze.STATUS_FINISHING'),
 ("disclosure not printed", RT, '    print(result["disclosure"])\n', ""),
 ("line not printed", RT, '    print(result["line"])\n    print(result["disclosure"])', '    print(result["disclosure"])'),
 ("frames saved before the line", RT, '    print(result["line"])\n    print(result["disclosure"])\n    try:\n        save_frames(panel, terms)\n    except Exception as error:\n        print(f"The result is safe, but the frames were not saved: {safe_error(error)}", file=sys.stderr)\n',
  '    try:\n        save_frames(panel, terms)\n    except Exception as error:\n        print(f"The result is safe, but the frames were not saved: {safe_error(error)}", file=sys.stderr)\n    print(result["line"])\n    print(result["disclosure"])\n'),
 ("save without try", RT, '    try:\n        save_frames(panel, terms)\n    except Exception as error:\n        print(f"The result is safe, but the frames were not saved: {safe_error(error)}", file=sys.stderr)\n', "    save_frames(panel, terms)\n"),
 ("save error shows raw message", RT, 'not saved: {safe_error(error)}"', 'not saved: {error}"'),
 ("safe_error shows every message", RT, 'if isinstance(error, InputGuardFailed) else ""', 'if True else ""'),
 ("no hash on screen", RT, '    print(f"Manifest SHA-256: {frozen_hash}. Compare it with the hash that the user keeps.", flush=True)\n', ""),
 ("no hash in attempt", RT, "crash_fix_note=crash_fix_note, manifest_sha256=frozen_hash)", "crash_fix_note=crash_fix_note)"),
 ("no hash in result", RT, 'result.update(step_a=counts, disclosure=DISCLOSURE, manifest_sha256=frozen_hash, finished=now())', 'result.update(step_a=counts, disclosure=DISCLOSURE, finished=now())'),
 ("no disclosure in result", RT, 'result.update(step_a=counts, disclosure=DISCLOSURE,', 'result.update(step_a=counts, disclosure="",'),
 ("note not required", RT, 'if record["status"] in ("started", "crashed", "floor_failed") and not (crash_fix_note or accept_floor_failure):', 'if False:'),
 ("note not required after started", RT, 'in ("started", "crashed", "floor_failed") and not', 'in ("crashed", "floor_failed") and not'),
 ("after_crash: step_a_done refused", FZ, 'AFTER_CRASH_STATUSES = ("started", "crashed", "floor_failed", "step_a_done")', 'AFTER_CRASH_STATUSES = ("started", "crashed", "floor_failed")'),
 ("after_crash: floor_failed refused", FZ, '"crashed", "floor_failed", "step_a_done")', '"crashed", "step_a_done")'),
 ("after_crash: started refused", FZ, '("started", "crashed", "floor', '("crashed", "floor'),
 ("after_crash: status check removed", FZ, ' or record["status"] not in AFTER_CRASH_STATUSES', ""),
 ("after_crash: finishing permitted", FZ, 'AFTER_CRASH_STATUSES = ("started",', 'AFTER_CRASH_STATUSES = ("finishing", "started",'),
 ("after_crash: partial check removed", FZ, 'result_path.with_suffix(".partial").exists() or ', ""),
 ("after_crash: result check removed", FZ, 'result_path.exists() or ', ""),
 ("after_crash: note check removed", FZ, '    if not note or not note.strip():\n        raise FreezeRefused("A crash freeze needs a note")\n', ""),
 ("after_crash: nothing kept in record", FZ, '    record.setdefault("refreezes", []).append(dict(at=datetime.now(timezone.utc).isoformat(), old_sha256=old, new_sha256=new, note=note))\n', ""),
 ("normal freeze: no refusal", FZ, "        refuse_after_unlock()\n", ""),
 ("marker: ISO date check removed", CF, '    try:\n        date.fromisoformat(str(content.get("approved_on")))\n    except ValueError:\n        return False\n', ""),
]
env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")


def tests():
    p = subprocess.run([sys.executable, "-m", "unittest", "test_run_once", "test_inputs.DateGate"], cwd=d / "tests", capture_output=True, text=True, env=env)
    tail = p.stderr.strip().splitlines()[-1] if p.stderr.strip() else ""
    return p.returncode, tail


print("baseline:", tests())
for name, path, old, new in M:
    src = path.read_text(encoding="utf-8")
    if src.count(old) < 1:
        print(f"NOT APPLIED  {name}")
        continue
    path.write_text(src.replace(old, new, 1), encoding="utf-8")
    code, tail = tests()
    print(f"{'caught  ' if code else 'SURVIVED'}  {name}  [{tail}]", flush=True)
    RT.write_text(rt0, encoding="utf-8"); FZ.write_text(fz0, encoding="utf-8"); CF.write_text(cf0, encoding="utf-8")
