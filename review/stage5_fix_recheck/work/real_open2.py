"""Real step_a and step_b on OPEN dates. All writes on scratch paths.
Real data read: option zips (members in the window only, through iter_days; the name list is held in memory), fred_rates.csv, data/alpaca_open_closes.parquet (open dates, asserted), index_series.parquet, load_cash_events on open dates.
day_conditions is replaced, because the real one parses condition.json. load_alpaca_closes reads a scratch JSON built from the open parquet, never the real Alpaca file."""
import io, json, re, sys, shutil
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
sys.dont_write_bytecode = True
REAL = Path(r"C:\Users\HP Laptop\.spyder-py3\2024-1\vix_ggal_adaptation")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(REAL))
import numpy as np, pandas as pd
import run_tests_once as rt
from config import SOURCE, DATA
OUT = HERE / "ro_out"
if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir()
START, END = "2020-01-01", "2022-04-30"
first, last = pd.Timestamp(START), pd.Timestamp(END)
assert first >= pd.Timestamp("2018-05-01")
rt.day_conditions = lambda path: {str(d.date()): "available" for d in pd.bdate_range(START, END)}
rt.TEST_OUTPUT = OUT / "frames"
closes = pd.read_parquet(DATA / "alpaca_open_closes.parquet")
assert closes["session_date"].min() >= pd.Timestamp("2018-05-01")
window = closes[closes["session_date"].between(START, END)].reset_index(drop=True)
def bars(path, frame):
    path.write_text(json.dumps(dict(pages=[dict(bars=dict(GGAL=[dict(t=f"{d.date()}T05:00:00Z", c=float(c)) for d, c in zip(frame["session_date"], frame["close"])]))])))
series, terms, counts = rt.step_a(first, last, None, SOURCE / "fred_rates.csv")
print("Step A counts:", json.dumps(rt.to_json(counts))[:900])
print("floor:", rt.floor_from_flags(series), "blank rate sessions:", counts["blank_rate_sessions"])
evs = [i for i in rt.ev.EVENTS if first <= pd.Timestamp(i[1]) <= last]

def full_run(name, frame, s=series, reps=20):
    root = OUT / name; root.mkdir()
    for f, scope in (("o1.json", "options"), ("o2.json", "outcomes")):
        (root / f).write_text(json.dumps(dict(purpose="stage5_one_time_test", scope=scope, approved_by="user", approved_on="2026-11-04")))
    p = root / "bars.json"; bars(p, frame)
    buf = io.StringIO()
    code = None
    def go(**kw):
        return rt.run_test(kw.pop("note", None), root/"run.json", root/"res.json", root/"o1.json", root/"o2.json", lambda: None, lambda: (s, terms, counts), lambda q: rt.step_b(q, first, last, None, evs, reps, "open check", p), rt.save_test_frames, lambda: "h", root/"a.json", **kw)
    try:
        with redirect_stdout(buf), redirect_stderr(buf):
            r = go()
    except SystemExit as e:
        r, code = None, e.code
    return root, r, buf.getvalue(), code, go

# Clean run at the full 2,000 resamples, to compare with the stored rehearsal.
root, r, text, code, _ = full_run("clean", window, reps=rt.rules.REPS)
print("clean: exit", code, "| status", json.loads((root/"run.json").read_text())["status"], "| outcome", r["decision"]["outcome"], "| frames", sorted(x.name for x in (OUT/"frames").iterdir()))
stored = json.loads((REAL/"review/stage4_rehearsal/rehearsal_2020-01-01_2022-04-30.json").read_text())
new = json.loads((root/"res.json").read_text())
diff = {k: (stored.get(k) == new.get(k)) for k in ("rule1", "no_events", "race", "floor", "tier1", "fixed_steps", "each_event_dropped", "counts", "decision")}
print("same as stored rehearsal (closes from the open parquet, day_conditions replaced):", diff)
print("stored step_a has blank_rate_sessions:", "blank_rate_sessions" in stored["step_a"], stored["step_a"].get("blank_rate_sessions"), "| same other step_a keys:", {k: stored["step_a"].get(k) == new["step_a"].get(k) for k in new["step_a"]})
print("stored guard limit is irrelevant: rehearsal file holds line:", stored["line"] == new["line"] or (stored["line"], new["line"]))
rec = json.loads((root/"run.json").read_text())
print("record holds step_a counts:", "step_a" in rec["attempts"][-1])

def scan(rec_text, frame, s):
    vals = set(np.round(frame["close"], 4)) | set(np.round(s["near_forward"].dropna(), 4)) | set(np.round(s["atm30"].dropna(), 4))
    fl = [float(x) for x in re.findall(r"-?\d+\.\d+", rec_text)]
    return [x for x in fl if round(x, 4) in vals]

def show_stop(name, frame, s=series):
    root, r, text, code, go = full_run(name, frame, s)
    if (root/"run.json").exists():
        rec = json.loads((root/"run.json").read_text())
    last_a = rec["attempts"][-1]
    print(f"{name}: exit {code} | status {rec['status']} | check {last_a.get('input_stop', {}).get('check')} | n dates {len(last_a.get('input_stop', {}).get('dates', []))} | error {str(last_a.get('error'))[:90]}")
    print("    screen has a date:", bool(re.search(r"20\d\d-\d\d-\d\d", text.replace(rt.DISCLOSURE, ""))), "| value match in the record:", scan((root/"run.json").read_text(), frame, s)[:3], "| result written:", (root/"res.json").exists())
    return root, r, text, code, go, last_a

gapframe = window.merge(series[["session_date", "near_forward"]], on="session_date", how="left")
def own_dates(frame, lim):
    j = frame.merge(series[["session_date", "near_forward"]], on="session_date").dropna()
    g = np.log(j["near_forward"]/j["close"]).abs()
    return [str(d.date()) for d in j.loc[g > lim, "session_date"]]

has_fw = window["session_date"].isin(series.loc[series["near_forward"].notna(), "session_date"]).to_numpy()
print("sessions with a near forward:", int(has_fw.sum()), "of", len(window))
ROW = int(np.flatnonzero(has_fw & (np.arange(len(window)) >= 200))[0])
NOF = int(np.flatnonzero(~has_fw & (np.arange(len(window)) >= 200))[0])
clean_b = new["rule1"]["b"]; print("clean b:", round(clean_b, 3), "| clean outcome:", new["decision"]["outcome"], "| low21/low63:", round(new["rule1"]["low21"], 3), round(new["rule1"]["low63"], 3))
for pct in (1.25, 1.5, 2.0, 0.5):
    nb = window.copy(); nb.loc[NOF, "close"] *= pct
    rootx, rx, tx, cx, gx = full_run(f"nofw_{int(pct*100)}", nb, reps=200)
    st = json.loads((rootx/"run.json").read_text())["status"]
    print(f"close x{pct} on a session with no near forward: status {st} | outcome {rx['decision']['outcome'] if rx else None} | b {round(rx['rule1']['b'], 3) if rx else None} | low21 {round(rx['rule1']['low21'], 3) if rx else None} | low63 {round(rx['rule1']['low63'], 3) if rx else None}")
bad = window.copy(); bad.loc[ROW, "close"] *= 1.5
root, r, t, c, go, a = show_stop("one_close_50pct", bad)
print("    dates equal my own calculation:", a["input_stop"]["dates"] == own_dates(bad, .15), "| n", len(a["input_stop"]["dates"]))
buf = io.StringIO()
with redirect_stdout(buf), redirect_stderr(buf):
    res2 = go(accept_input_stop=True)
print("    accept on real data:", res2["decision"], "| json ok:", json.loads((root/"res.json").read_text())["input_stop"]["dates"] == a["input_stop"]["dates"], "| status", json.loads((root/"run.json").read_text())["status"], "| counts in result:", "sessions" in res2["step_a"])
for pct in (1.14, 1.17, 1.20):
    b2 = window.copy(); b2.loc[ROW, "close"] *= pct
    root, r, t, c, go, a = show_stop(f"one_close_{int(round((pct-1)*100))}pct", b2)
    print("    log gap from the bad close alone:", round(abs(np.log(pct)), 4), "| final", r["decision"]["outcome"] if r else None, "| b", round(r["rule1"]["b"], 3) if r and "rule1" in r else None)
half = window.assign(close=window["close"]/2)
root, r, t, c, go, a = show_stop("halved", half)
print("    median dates equal mine:", a["input_stop"]["dates"] == own_dates(half, .02))
rng = np.random.default_rng(0)
idx = rng.choice(len(window), int(len(window)*.08), replace=False)
sh = window.copy(); sh.loc[idx, "close"] *= 1.07
root, r, t, c, go, a = show_stop("share_8pct", sh)
print("    share dates equal mine:", a["input_stop"]["dates"] == own_dates(sh, .05))
miss = window.drop(index=[10, 20, 30, 40]).reset_index(drop=True)
root, r, t, c, go, a = show_stop("four_missing_alpaca", miss)
print("    one-source dates equal mine:", a["input_stop"]["dates"] == [str(window.loc[i, 'session_date'].date()) for i in (10, 20, 30, 40)])
sdrop = series.drop(index=[11, 21, 31, 41]).reset_index(drop=True)
root, r, t, c, go, a = show_stop("four_missing_options", window, sdrop)
print("    one-source dates:", a["input_stop"]["dates"])
miss3 = window.drop(index=[10, 20, 30]).reset_index(drop=True)
root, r, t, c, go, a = show_stop("three_missing", miss3)

# Blank rates.
raw = pd.read_csv(SOURCE / "fred_rates.csv")
cols = [x for x in raw.columns if x != "observation_date"]
print("rate columns:", cols)
b = raw[raw["observation_date"] >= "2019-12-01"].copy(); b[cols] = np.nan
b.to_csv(OUT/"blank_all.csv", index=False)
try:
    s3, _, c3 = rt.step_a(first, last, None, OUT/"blank_all.csv")
    print("all blank: atm30", c3["atm30_days"], "blank sessions", c3["blank_rate_sessions"], "of", c3["sessions"], "floor", rt.floor_from_flags(s3)["passed"])
except Exception as e:
    print("all blank: safe crash:", rt.safe_error(e))
b = raw[raw["observation_date"] >= "2019-12-01"].copy(); b["DGS1MO"] = np.nan
b.to_csv(OUT/"blank_one.csv", index=False)
try:
    s3, _, c3 = rt.step_a(first, last, None, OUT/"blank_one.csv")
    print("one column blank: atm30", c3["atm30_days"], "blank sessions", c3["blank_rate_sessions"], "of", c3["sessions"], "floor", rt.floor_from_flags(s3)["passed"])
except Exception as e:
    print("one column blank: safe crash:", rt.safe_error(e))
b = raw[raw["observation_date"] >= "2021-01-01"].copy()
b.to_csv(OUT/"late_start.csv", index=False)
try:
    s3, _, c3 = rt.step_a(first, last, None, OUT/"late_start.csv")
    print("rates start late: atm30", c3["atm30_days"], "blank sessions", c3["blank_rate_sessions"], "of", c3["sessions"], "floor", rt.floor_from_flags(s3)["passed"])
except Exception as e:
    print("late start: safe crash:", rt.safe_error(e))

# Guard on all open sessions and 73 windows, with the .15 limit.
full = closes.merge(pd.read_parquet(DATA / "index_series.parquet")[["session_date", "near_forward"]], on="session_date", how="left")
g = np.log(full["near_forward"] / full["close"]).abs().dropna()
print("open data: rows", len(g), "median", round(g.median(), 5), "share>5%", round((g > .05).mean(), 5), "max", round(g.max(), 4), "limit", rt.GUARD_LARGEST)
fails = n = 0
worst = 0
for s in pd.period_range("2018-05", "2024-05", freq="M"):
    w = full[full["session_date"].between(s.to_timestamp(), (s + 27).to_timestamp(how="end"))]
    n += 1
    try:
        rt.input_guard(w, 0, 0)
    except rt.InputGuardFailed:
        fails += 1
print("open windows:", n, "stops:", fails)
