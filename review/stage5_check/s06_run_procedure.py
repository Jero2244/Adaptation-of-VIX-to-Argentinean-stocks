"""Run-procedure experiments, on temporary paths and synthetic frames. No real marker, no locked date."""
import _common, json, tempfile, shutil, os
from pathlib import Path
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr
import numpy as np, pandas as pd
import run_tests_once as rt, freeze, config
from config import MARKER_PURPOSE, SCOPE_OPTIONS, SCOPE_OUTCOMES, marker_opens

def mark(path, scope, **kw):
    path.write_text(json.dumps(dict(dict(purpose=MARKER_PURPOSE, scope=scope, approved_by="user", approved_on="2026-11-04"), **kw)))
def good(n=620):
    d = pd.bdate_range("2021-01-04", periods=n)
    return pd.DataFrame(dict(session_date=d, atm30=.6, tier=1))
SECRET = {"decision": {"outcome": "Supported"}, "line": "line", "rule1": {"b": 0.777}}

def setup():
    r = Path(tempfile.mkdtemp())
    mark(r/"o.json", SCOPE_OPTIONS); mark(r/"c.json", SCOPE_OUTCOMES)
    return r
def call(r, note=None, check=lambda: None, run_b=None, save=lambda p,t: None, series=None):
    series = good() if series is None else series
    return rt.run_test(note, r/"run.json", r/"result.json", r/"o.json", r/"c.json", check, lambda:(series,pd.DataFrame(),dict(sessions=len(series))), run_b or (lambda s:(dict(SECRET),pd.DataFrame())), save)

print("== A. Crash, then log the fix in PROTOCOL.md as the refusal text says")
r = setup()
(r/"PROTOCOL.md").write_text("rules\n"); man = r/"manifest.json"
freeze.write_manifest(man,[r/"PROTOCOL.md"],r)
check = lambda: freeze.verify_manifest(man,[r/"PROTOCOL.md"],r)
def boom(s): raise ValueError("x")
buf = StringIO()
try:
    with redirect_stdout(buf), redirect_stderr(buf): call(r, check=check, run_b=boom)
except SystemExit: pass
print("status after crash:", json.loads((r/"run.json").read_text())["status"])
(r/"PROTOCOL.md").write_text("rules\nlogged fix\n")
try:
    with redirect_stdout(buf), redirect_stderr(buf): call(r, note="fix", check=check)
    print("rerun passed")
except Exception as e: print("rerun with note after the log edit:", type(e).__name__, e)
print("freeze.py refuses with real paths? It looks for the two markers and the run record:")
saved = (freeze.OPTIONS_MARKER, freeze.OUTCOMES_MARKER, freeze.REPORTS)
freeze.OPTIONS_MARKER, freeze.OUTCOMES_MARKER, freeze.REPORTS = r/"o.json", r/"c.json", r
try:
    freeze.refuse_after_unlock(); print("freeze allowed")
except SystemExit as e: print("freeze refused:", e)
os.rename(r/"run.json", r/"backward_test_run.json")
try:
    freeze.refuse_after_unlock(); print("freeze allowed")
except SystemExit as e: print("freeze refused:", e)
freeze.OPTIONS_MARKER, freeze.OUTCOMES_MARKER, freeze.REPORTS = saved

print("\n== B. The result file write fails at the replace step")
r = setup()
orig = Path.replace
def bad(self, target):
    if str(target).endswith("result.json"): raise PermissionError("locked by another process")
    return orig(self, target)
Path.replace = bad
try:
    with redirect_stdout(buf), redirect_stderr(buf): call(r)
except PermissionError as e: print("uncaught:", e)
Path.replace = orig
print("files:", sorted(p.name for p in r.iterdir()))
print("status:", json.loads((r/"run.json").read_text())["status"], "| partial holds outcome:", "0.777" in (r/"result.partial").read_text())
b_calls=[]
def second(s): b_calls.append(1); return dict(SECRET),pd.DataFrame()
with redirect_stdout(buf), redirect_stderr(buf): call(r, note="retry", run_b=second)
print("second run with a note was accepted, and Step B ran again:", b_calls)

print("\n== C. save_frames fails after the result write")
r = setup()
def badsave(p,t): raise ValueError("Conversion failed for column x, value 12.34")
out = StringIO()
try:
    with redirect_stdout(out), redirect_stderr(out): call(r, save=badsave)
except ValueError as e: print("uncaught, message reaches the traceback:", e)
print("line printed to screen:", "line" in out.getvalue(), "| status:", json.loads((r/"run.json").read_text())["status"], "| result exists:", (r/"result.json").exists())

print("\n== D. Floor failure from a bug: terminal, and no diagnostics stay")
r = setup()
thin = good().assign(atm30=np.nan)
out = StringIO()
with redirect_stdout(out): res = call(r, series=thin)
print("printed:", out.getvalue().strip())
print("files:", sorted(p.name for p in r.iterdir()), "| keys:", list(res))
try:
    with redirect_stdout(out): call(r, note="the fault was a bug in the rates path", series=good())
except rt.RunRefused as e: print("after the fix, with a note:", e)

print("\n== E. Marker forms")
r = Path(tempfile.mkdtemp()); m = r/"m.json"
base = dict(purpose=MARKER_PURPOSE, scope="options", approved_by="user", approved_on="2026-11-04")
m.write_text(json.dumps(base), encoding="utf-8-sig"); print("UTF-8 BOM (Windows PowerShell 5 Set-Content -Encoding utf8):", marker_opens(m,"options"))
m.write_text(json.dumps(base), encoding="utf-16"); print("UTF-16 (Windows PowerShell 5 > redirect):", marker_opens(m,"options"))
m.write_text(json.dumps(dict(base, approved_on="YYYY-MM-DD"))); print("Template text left in approved_on:", marker_opens(m,"options"))
m.write_text(json.dumps(dict(base, approved_by="user", scope="outcomes"))); print("Outcomes marker for options:", marker_opens(m,"options"))

print("\n== F. Default wiring of run_test, with step functions and the manifest patched, and no file read")
calls = {}
sa, sb = rt.step_a, rt.step_b
rt.step_a = lambda *a: (calls.__setitem__("a",a), (good(),pd.DataFrame(),dict(sessions=620)))[1]
rt.step_b = lambda *a, **k: (calls.__setitem__("b",(a,k)), (dict(SECRET),pd.DataFrame()))[1]
r = setup()
with redirect_stdout(buf): rt.run_test(None, r/"run.json", r/"result.json", r/"o.json", r/"c.json", lambda:None, save_frames=lambda p,t:None)
rt.step_a, rt.step_b = sa, sb
print("step_a args:", [str(x)[:60] for x in calls["a"]])
print("step_b args:", [str(x)[:60] for x in calls["b"][0][1:]], calls["b"][1])

print("\n== G. Floor reading: 20 filled spans that are not adjacent")
import stage4_rules as rules
v = np.zeros(21*30,bool)
for s in list(range(0,10))+list(range(12,22)): v[s*21:s*21+15]=True
print(rules.data_floor(v), "| longest run of adjacent filled spans = 10")
