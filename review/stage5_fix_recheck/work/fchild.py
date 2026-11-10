"""One fault per process, so the real uncaught traceback shows on real stderr. Temporary paths in a copy, synthetic values only."""
import json, os, sys, io
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
project, case, path_kind, folder = os.environ["P"], os.environ["CASE"], os.environ["PATHK"], Path(os.environ["F"])
sys.path.insert(0, project)
import numpy as np, pandas as pd
import freeze, run_tests_once as rt
SECRET = "987.654"
folder.mkdir(parents=True, exist_ok=True)
rec, res, opt, out, sa = folder/"run.json", folder/"result.json", folder/"opt.json", folder/"out.json", folder/"sa.json"
for p, scope in ((opt, "options"), (out, "outcomes")):
    p.write_text(json.dumps(dict(purpose="stage5_one_time_test", scope=scope, approved_by="user", approved_on="2026-11-04")))
good = pd.DataFrame(dict(session_date=pd.bdate_range("2021-01-04", periods=600), atm30=.6, tier=1))
thin = good.assign(atm30=np.nan)
A = lambda s: (lambda: (s, pd.DataFrame(), dict(sessions=len(s), atm30_days=int(s["atm30"].notna().sum()))))
LINE = "THE VERDICT LINE"
def good_b(s):
    return dict(decision=dict(outcome="Supported"), line=LINE), pd.DataFrame()
def stop_b(s):
    raise rt.InputGuardFailed("The largest gap of forward and close is above the limit", ["2017-03-01"])
def secret_b(s):
    raise ValueError(f"close was {SECRET}")
def secret_a():
    raise ValueError(f"forward was {SECRET}")
def save(p, t):
    (folder/"frames_saved").write_text("1")
def go(run_a, run_b, note=None, **kw):
    return rt.run_test(note, rec, res, opt, out, lambda: None, run_a, run_b, save, lambda: "h", sa, **kw)
rt.RENAME_WAIT = 0
# Setup without faults.
kw = {}
run_a, run_b = A(good), good_b
if path_kind == "floor":
    with redirect_stdout(io.StringIO()):
        go(A(thin), good_b)
    kw = dict(accept_floor_failure=True)
elif path_kind == "stop":
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        try:
            go(A(good), stop_b)
        except SystemExit:
            pass
    kw = dict(accept_input_stop=True)
elif path_kind == "secret_a":
    run_a = secret_a
elif path_kind == "secret_b":
    run_b = secret_b
elif path_kind == "guard":
    run_b = stop_b
elif path_kind == "badjson":
    run_b = lambda s: (dict(decision=dict(outcome="Supported"), line=LINE, bad=object()), pd.DataFrame())

real_write, real_replace, real_read = Path.write_text, Path.replace, Path.read_text
spec = json.loads(os.environ.get("SPEC", "[]"))  # list of [kind, target, status]
def status_of(text):
    try:
        return json.loads(text).get("status")
    except Exception:
        return None
counts = {}
def match(s, name, status_text):
    out_ = []
    for kind, target, status in spec:
        if kind in s and target == name and (status is None or status == status_of(status_text)):
            out_.append(kind)
    return out_
def W(self, data, *a, **k):
    m = match(("W", "T", "KW"), self.name, data)
    if "T" in m:
        real_write(self, data[:len(data)//2], *a, **k)
        raise OSError(28, "No space left on device")
    if "W" in m:
        raise OSError(28, "No space left on device")
    if "KW" in m:
        raise KeyboardInterrupt
    return real_write(self, data, *a, **k)
def N(self, target):
    try:
        text = real_read(self, encoding="utf-8")
    except OSError:
        text = ""
    m = match(("N", "KN"), Path(target).name, text)
    if "N" in m:
        raise PermissionError(13, "locked")
    if "KN" in m:
        raise KeyboardInterrupt
    return real_replace(self, target)
def Rd(self, *a, **k):
    for kind, target, status in spec:
        if kind == "RD" and target == self.name:
            raise PermissionError(13, "cannot read")
    return real_read(self, *a, **k)
Path.write_text, Path.replace, Path.read_text = W, N, Rd

class Flaky:
    """A stream that fails on a chosen text, then works."""
    def __init__(self, base, text, once=True):
        self.base, self.text, self.once, self.fired = base, text, once, False
    def write(self, s):
        if self.text in s and not (self.once and self.fired):
            self.fired = True
            raise OSError(22, "Invalid argument")
        return self.base.write(s)
    def flush(self):
        return self.base.flush()
    def __getattr__(self, name):
        return getattr(self.base, name)

for kind, target, status in spec:
    if kind == "EP":
        sys.stderr = Flaky(sys.stderr, target)
    if kind == "OP":
        sys.stdout = Flaky(sys.stdout, target, once=False)
    if kind == "LOCK":
        rt.RENAME_WAIT = 1.0
        holder = None
        real_b = run_b
        def run_b(s, real_b=real_b):
            globals()["holder"] = open(folder/target, "rb")  # A real Windows handle that blocks the rename.
            return real_b(s)
if os.environ.get("HOOK"):
    sys.excepthook = rt.safe_hook
go(run_a, run_b, **kw)
print("child finished normally")
