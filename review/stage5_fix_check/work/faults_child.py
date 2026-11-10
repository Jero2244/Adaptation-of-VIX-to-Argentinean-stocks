"""One fault per process, so the real uncaught traceback shows on stderr. Temporary paths in the copy only. Synthetic values only."""
import json, os, sys
from pathlib import Path
from unittest import mock
project = os.environ["DRIVER_PROJECT"]; fault = os.environ["DRIVER_MODE"]
sys.path.insert(0, project); sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import common, freeze
import run_tests_once as rt

T = Path(project) / "t_" ; T = Path(project) / f"t_{fault}"; T.mkdir(exist_ok=True)
rec, res, opt, out, sa = T/"run.json", T/"result.json", T/"opt.json", T/"out.json", T/"sa.json"
for path, scope in ((opt, "options"), (out, "outcomes")):
    path.write_text(json.dumps(dict(purpose="stage5_one_time_test", scope=scope, approved_by="user", approved_on="2026-11-04")))
series = pd.DataFrame(dict(session_date=pd.bdate_range("2021-01-04", periods=600), atm30=.6, tier=1))
good_a = lambda: (series, pd.DataFrame(), dict(sessions=600, atm30_days=600))
good_b = lambda s: (dict(decision=dict(outcome="Supported"), line="THE VERDICT LINE"), pd.DataFrame())
saved = []
save = lambda p, t: saved.append(1)
def go(run_a=good_a, run_b=good_b, note=None):
    return rt.run_test(note, rec, res, opt, out, lambda: None, run_a, run_b, save, lambda: "hash", sa)

if fault == "double":
    # A real Windows lock on the record (a viewer holds the file), then a crash whose message holds a value.
    go(run_b=lambda s: None) if False else None
    rec.write_text(json.dumps(dict(status="step_a_done", attempts=[])))
    holder = {}
    def a():
        holder["f"] = open(rec, "rb")
        raise ValueError(f"close was {common.SECRET}")
    go(run_a=a)
elif fault == "serialize":
    go(run_b=lambda s: (dict(decision=dict(outcome="Supported"), line="THE VERDICT LINE", bad=pd.NaT), pd.DataFrame()))
elif fault == "disk":
    real = Path.write_text
    def w(self, *a, **k):
        if self.name == "result.partial":
            raise OSError(28, "No space left on device")
        return real(self, *a, **k)
    with mock.patch.object(Path, "write_text", w):
        go()
elif fault == "rename":
    real = Path.replace
    def r(self, target):
        if Path(target).name == "result.json":
            raise PermissionError(13, "locked")
        return real(self, target)
    with mock.patch.object(Path, "replace", r):
        go()
elif fault == "last_record":
    real = Path.replace; n = {"c": 0}
    def r(self, target):
        if Path(target).name == "run.json":
            n["c"] += 1
            if n["c"] == 3:
                raise PermissionError(13, "locked")
        return real(self, target)
    with mock.patch.object(Path, "replace", r):
        go()
elif fault == "interrupt":
    def b(s):
        raise KeyboardInterrupt
    go(run_b=b)
elif fault == "blank_note":
    rec.write_text(json.dumps(dict(status="crashed", attempts=[])))
    print(go(note="   ")["decision"]); print("attempt note:", repr(json.loads(rec.read_text())["attempts"][-1]["crash_fix_note"]))
elif fault == "no_fix_note":
    rec.write_text(json.dumps(dict(status="crashed", attempts=[])))
    go(note="nothing was fixed"); print("status", json.loads(rec.read_text())["status"])
if fault in ("serialize", "disk", "rename", "last_record"):
    pass
print("saved frames:", len(saved))
