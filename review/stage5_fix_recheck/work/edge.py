import io, json, shutil, sys, tempfile
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest import mock
from common import make_copy, HERE
d = make_copy("edge")
sys.path.insert(0, str(d))
import numpy as np, pandas as pd
import freeze, run_tests_once as rt
T = HERE / "edge_t"
if T.exists():
    shutil.rmtree(T)
T.mkdir()
def setup(name):
    t = T / name; t.mkdir()
    c = t / "c.py"; c.write_text("x=1"); m = t / "m.json"; h = freeze.write_manifest(m, [c], t)
    (t / "run.json").write_text(json.dumps(dict(status="crashed", attempts=[dict(manifest_sha256=h)])))
    c.write_text("x=2")
    return t, c, m, h
print("1. manifest write fails after the record write, then a retry")
t, c, m, h = setup("a")
real = Path.write_text
def fail_m(self, *a, **k):
    if self.name == "m.json":
        raise PermissionError(13, "locked")
    return real(self, *a, **k)
with mock.patch.object(Path, "write_text", fail_m):
    try:
        freeze.after_crash("n", m, t/"run.json", t/"r.json", [c], t)
    except Exception as e:
        print("   first:", type(e).__name__)
rec = json.loads((t/"run.json").read_text()); print("   entries:", len(rec["refreezes"]), "| manifest still old:", freeze.sha256(m) == h)
new = freeze.after_crash("n", m, t/"run.json", t/"r.json", [c], t)
rec = json.loads((t/"run.json").read_text()); print("   after retry entries:", len(rec["refreezes"]), "| both old:", [e["old_sha256"] == h for e in rec["refreezes"]], "| new matches file:", rec["refreezes"][-1]["new_sha256"] == freeze.sha256(m), "| backups:", sorted(p.name for p in t.glob("m_*")))
print("2. manifest write is cut off part way (killed or disk full): non-atomic write")
t, c, m, h = setup("b")
def trunc(self, data, *a, **k):
    if self.name == "m.json":
        real(self, data[:20], *a, **k)
        raise OSError(28, "No space left on device")
    return real(self, data, *a, **k)
with mock.patch.object(Path, "write_text", trunc):
    try:
        freeze.after_crash("n", m, t/"run.json", t/"r.json", [c], t)
    except Exception as e:
        print("   first:", type(e).__name__)
for label, f in (("after_crash retry", lambda: freeze.after_crash("n", m, t/"run.json", t/"r.json", [c], t)), ("verify", lambda: freeze.verify_manifest(m, [c], t))):
    try:
        f(); print("  ", label, "ok")
    except Exception as e:
        print("  ", label, "->", type(e).__name__)
b = t / f"m_{h[:12]}.json"; print("   backup exists:", b.exists())
shutil.copyfile(b, m); print("   after a manual restore, retry:", freeze.after_crash("n", m, t/"run.json", t/"r.json", [c], t)[:8])
print("3. record replace fails in after_crash: manifest stays, partial left over")
t, c, m, h = setup("c")
with mock.patch.object(Path, "replace", side_effect=PermissionError(13, "locked")):
    try:
        freeze.after_crash("n", m, t/"run.json", t/"r.json", [c], t)
    except Exception as e:
        print("   first:", type(e).__name__, "| manifest old:", freeze.sha256(m) == h, "| leftover:", sorted(p.name for p in t.iterdir()))
print("   retry:", freeze.after_crash("n", m, t/"run.json", t/"r.json", [c], t)[:8])
print("4. markers present, no run record, code changed (a fix before the first run)")
t = T / "d"; t.mkdir()
c = t / "c.py"; c.write_text("x=1"); m = t / "m.json"; freeze.write_manifest(m, [c], t); c.write_text("x=2")
try:
    freeze.after_crash("n", m, t/"run.json", t/"r.json", [c], t)
except freeze.FreezeRefused as e:
    print("   after_crash:", e)
print("5. accept paths with odd records")
def rec_case(name, record, **kw):
    t = T / name; t.mkdir()
    for f, s in (("o.json", "options"), ("p.json", "outcomes")):
        (t/f).write_text(json.dumps(dict(purpose="stage5_one_time_test", scope=s, approved_by="user", approved_on="2026-11-04")))
    (t/"run.json").write_text(json.dumps(record))
    before = (t/"run.json").read_text()
    try:
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            rt.run_test(None, t/"run.json", t/"res.json", t/"o.json", t/"p.json", lambda: None, lambda: 1/0, lambda s: 1/0, lambda a, b: None, lambda: "h", t/"sa.json", **kw)
        print("  ", name, "ran")
    except BaseException as e:
        print("  ", name, "->", type(e).__name__, "| record unchanged:", (t/"run.json").read_text() == before, "| result:", (t/"res.json").exists())
rec_case("stop_empty_attempts", dict(status="input_stopped", attempts=[]), accept_input_stop=True)
rec_case("stop_no_stepa", dict(status="input_stopped", attempts=[dict(manifest_sha256="h")]), accept_input_stop=True)
rec_case("stop_no_stop_key", dict(status="input_stopped", attempts=[dict(manifest_sha256="h", step_a=dict(counts={}, floor={}))]), accept_input_stop=True)
rec_case("floor_empty_attempts_no_file", dict(status="floor_failed", attempts=[]), accept_floor_failure=True)
rec_case("no_status_key", dict(attempts=[]))
rec_case("no_attempts_key", dict(status="step_a_done"))
print("6. stale floor file: floor_failed with an attempt hash that is current, Step A file corrupt")
t = T / "e"; t.mkdir()
for f, s in (("o.json", "options"), ("p.json", "outcomes")):
    (t/f).write_text(json.dumps(dict(purpose="stage5_one_time_test", scope=s, approved_by="user", approved_on="2026-11-04")))
(t/"run.json").write_text(json.dumps(dict(status="floor_failed", attempts=[dict(manifest_sha256="h")])))
(t/"sa.json").write_text("{not json")
try:
    rt.run_test(None, t/"run.json", t/"res.json", t/"o.json", t/"p.json", lambda: None, lambda: 1/0, lambda s: 1/0, lambda a, b: None, lambda: "h", t/"sa.json", accept_floor_failure=True)
except Exception as e:
    print("   ->", type(e).__name__, "status:", json.loads((t/"run.json").read_text())["status"])
print("7. no file holds the result, and the frame save also fails")
t = T / "f"; t.mkdir()
for f, s in (("o.json", "options"), ("p.json", "outcomes")):
    (t/f).write_text(json.dumps(dict(purpose="stage5_one_time_test", scope=s, approved_by="user", approved_on="2026-11-04")))
good = pd.DataFrame(dict(session_date=pd.bdate_range("2021-01-04", periods=600), atm30=.6, tier=1))
def badw(path, text):
    if path.name == "res.json":
        raise OSError(28, "No space left")
    realwt(path, text)
realwt = rt.write_text
def bad_save(a, b):
    raise OSError("no space")
buf = io.StringIO()
with mock.patch.object(rt, "write_text", badw), redirect_stdout(buf), redirect_stderr(buf):
    rt.run_test(None, t/"run.json", t/"res.json", t/"o.json", t/"p.json", lambda: None, lambda: (good, pd.DataFrame(), dict(sessions=600, atm30_days=600)), lambda s: (dict(decision=dict(outcome="X"), line="LINE"), pd.DataFrame()), bad_save, lambda: "h", t/"sa.json")
print("   screen says:", [x for x in buf.getvalue().splitlines() if "safe" in x or "No file" in x])
print("8. partial with bytes that are not UTF-8: read in show_result")
t = T / "g"; t.mkdir()
for f, s in (("o.json", "options"), ("p.json", "outcomes")):
    (t/f).write_text(json.dumps(dict(purpose="stage5_one_time_test", scope=s, approved_by="user", approved_on="2026-11-04")))
def garb(path, text):
    if path.name == "res.json":
        path.with_suffix(".partial").write_bytes(b"\xff\xfe{")
        raise OSError(28, "No space left")
    realwt(path, text)
buf = io.StringIO()
try:
    with mock.patch.object(rt, "write_text", garb), redirect_stdout(buf), redirect_stderr(buf):
        rt.run_test(None, t/"run.json", t/"res.json", t/"o.json", t/"p.json", lambda: None, lambda: (good, pd.DataFrame(), dict(sessions=600, atm30_days=600)), lambda s: (dict(decision=dict(outcome="X"), line="LINE"), pd.DataFrame()), lambda a, b: None, lambda: "h", t/"sa.json")
    print("   no exception")
except Exception as e:
    print("   exception:", type(e).__name__, "| line shown:", "LINE" in buf.getvalue())
print("9. ascii checks: disclosure ascii:", rt.DISCLOSURE.isascii())
src = Path(rt.__file__).read_text(encoding="utf-8")
print("   run_tests_once ascii:", src.isascii(), "| stage4_rules ascii:", (d/"stage4_rules.py").read_text(encoding="utf-8").isascii())
