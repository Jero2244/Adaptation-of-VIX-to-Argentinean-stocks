"""Make each listed fault in a temporary copy of the code, and check that the tests catch it. The real folder does not change. Runs test_run_once and test_alpaca only, which use synthetic data."""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
R, F, L = "run_tests_once.py", "freeze.py", "load_data.py"
MUTANTS = [
    ("before no abs", R, 'before = np.log(ordered["close"] / forward.ffill().shift(1)).abs()', 'before = np.log(ordered["close"] / forward.ffill().shift(1))'),
    ("after no abs", R, 'after = np.log(ordered["close"] / forward.bfill().shift(-1)).abs()', 'after = np.log(ordered["close"] / forward.bfill().shift(-1))'),
    ("after only", R, 'return pd.concat([before, after], axis=1).min(axis=1)[forward.isna()', 'return after[forward.isna()'),
    ("before only", R, 'return pd.concat([before, after], axis=1).min(axis=1)[forward.isna()', 'return before[forward.isna()'),
    ("dates all no-forward", R, 'panel.loc[stray[stray].index, "session_date"])', 'panel.loc[stray.index, "session_date"])'),
    ("condition removed", R, 'stray = far & (adjacent_close_gaps(panel).reindex(far.index) > GUARD_NO_FORWARD)', 'stray = far'),
    ("condition replaces the forward rule", R, 'stray = far & (adjacent_close_gaps(panel).reindex(far.index) > GUARD_NO_FORWARD)', 'stray = adjacent_close_gaps(panel).reindex(far.index) > GUARD_NO_FORWARD'),
    ("adjacent: left only", R, 'return pd.concat([np.log(close / close.shift(1)).abs(), np.log(close / close.shift(-1)).abs()], axis=1).min(axis=1)', 'return np.log(close / close.shift(1)).abs()'),
    ("adjacent: right only", R, 'return pd.concat([np.log(close / close.shift(1)).abs(), np.log(close / close.shift(-1)).abs()], axis=1).min(axis=1)', 'return np.log(close / close.shift(-1)).abs()'),
    ("adjacent: max", R, 'np.log(close / close.shift(-1)).abs()], axis=1).min(axis=1)', 'np.log(close / close.shift(-1)).abs()], axis=1).max(axis=1)'),
    ("fault: fixed text", R, 'raise InputGuardFailed(str(fault), fault.dates) from None', 'raise InputGuardFailed("A data fault", fault.dates) from None'),
    ("close zero passes", L, 'usable = frame["close"] > 0', 'usable = (frame["close"] >= 0) | frame["close"].isna()'),
    ("close null passes", L, 'usable = frame["close"] > 0', 'usable = ~(frame["close"] <= 0)'),
    ("say: Exception only", R, '    except BaseException:\n        pass\n\n\ndef safe_excepthook', '    except Exception:\n        pass\n\n\ndef safe_excepthook'),
    ("hook: no guard", R, '    except BaseException:\n        pass  # If the hook raises', '    except ZeroDivisionError:\n        pass  # If the hook raises'),
    ("partial read: narrow catch", R, 'except BaseException:  # The text below', 'except (OSError, ValueError):  # The text below'),
    ("raw write error", R, 'say(f"The result write did not finish: {safe_error(error)}", sys.stderr)', 'say(f"The result write did not finish: {type(error).__name__} {error}", sys.stderr)'),
    ("history keeps step_a", R, 'keys = ("started", "manifest_sha256", "crash_fix_note", "error", "input_stop")', 'keys = ("started", "manifest_sha256", "crash_fix_note", "error", "input_stop", "step_a")'),
    ("history no error", R, 'keys = ("started", "manifest_sha256", "crash_fix_note", "error", "input_stop")', 'keys = ("started", "manifest_sha256", "crash_fix_note", "input_stop")'),
    ("history no note", R, 'keys = ("started", "manifest_sha256", "crash_fix_note", "error", "input_stop")', 'keys = ("started", "manifest_sha256", "error", "input_stop")'),
    ("history no refreezes", R, 'for key in keys if key in attempt} for attempt in attempts], refreezes=refreezes)', 'for key in keys if key in attempt} for attempt in attempts], refreezes=[])'),
    ("no history in the accept result", R, 'result.update(history=past, crash_fix_note=note, disclosure', 'result.update(crash_fix_note=note, disclosure'),
    ("no note in the accept result", R, 'result.update(history=past, crash_fix_note=note, disclosure', 'result.update(history=past, disclosure'),
    ("no note in the result", R, 'result.update(step_a=counts, history=past, crash_fix_note=note, disclosure', 'result.update(step_a=counts, history=past, disclosure'),
    ("write_manifest writes directly", F, 'replace_manifest(path, manifest_text(files, root))', 'path.write_text(manifest_text(files, root), encoding="utf-8")'),
]


def run_tests(folder: Path) -> set:
    done = subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-p", "test_[ra]*.py"], cwd=folder, capture_output=True, text=True, timeout=600)
    lines = (done.stdout + done.stderr).splitlines()
    failures = {line for line in lines if line.startswith(("FAIL:", "ERROR:"))}
    if not any(line.startswith("Ran ") for line in lines):
        failures.add("ABORTED: an uncaught interrupt ended the test run")
    return failures


with tempfile.TemporaryDirectory() as base:
    copy = Path(base) / "code"
    (copy / "tests").mkdir(parents=True)
    for path in ROOT.glob("*.py"):
        shutil.copy(path, copy)
    for path in (ROOT / "tests").glob("*.py"):
        shutil.copy(path, copy / "tests")
    baseline = run_tests(copy)
    print("baseline failures, which need the data folder that the copy does not have:", sorted(baseline), flush=True)
    survived = 0
    for name, file, old, new in MUTANTS:
        target = copy / file
        original = target.read_bytes()
        text = original.decode("utf-8").replace("\r\n", "\n")
        if text.count(old) != 1:
            print("NOT APPLIED", name, flush=True)
            survived += 1
            continue
        target.write_bytes(text.replace(old, new).encode("utf-8"))
        passed = not (run_tests(copy) - baseline)
        target.write_bytes(original)
        survived += passed
        print("SURVIVED" if passed else "caught  ", name, flush=True)
    print(f"mutants {len(MUTANTS)}, survived or not applied {survived}")
