"""Real step_a and step_b code on OPEN dates, with all writes on scratch paths. Real data read here: option zips (members 2020-05 onward only, by iter_days), fred_rates.csv, data/alpaca_open_closes.parquet (open dates, asserted), and load_cash_events on open dates.
day_conditions is replaced, because the real function parses condition.json, which has rows for locked dates. load_alpaca_closes reads a scratch JSON built from the open parquet, never the real Alpaca file."""
import json, os, sys, tempfile
from pathlib import Path
sys.dont_write_bytecode = True
REAL = Path(r"C:\Users\HP Laptop\.spyder-py3\2024-1\vix_ggal_adaptation")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(REAL))
import numpy as np, pandas as pd
import build_snapshot as bs, freeze, run_tests_once as rt
from config import SOURCE, DATA

OUT = HERE / "real_open_out"; OUT.mkdir(exist_ok=True)
START, END = "2020-05-01", "2022-08-31"
rt.day_conditions = lambda path: {str(d.date()): "available" for d in pd.bdate_range(START, END)}
rt.TEST_OUTPUT = OUT / "frames"

closes = pd.read_parquet(DATA / "alpaca_open_closes.parquet")
assert closes["session_date"].min() >= pd.Timestamp("2018-05-01")
window = closes[closes["session_date"].between(START, END)]


def bars(path, frame):
    path.write_text(json.dumps(dict(pages=[dict(bars=dict(GGAL=[dict(t=f"{d.date()}T05:00:00Z", c=float(c)) for d, c in zip(frame["session_date"], frame["close"])]))])))


def a(rates=SOURCE / "fred_rates.csv"):
    return rt.step_a(pd.Timestamp(START), pd.Timestamp(END), None, rates)


series, terms, counts = a()
print("Step A counts:", json.dumps(rt.to_json(counts))[:1500])
print("floor from flags:", rt.floor_from_flags(series))
print("near_forward present:", "near_forward" in series, "| near_forward only on ok days:", bool((series.loc[series["status"] != "ok", "near_forward"].isna()).all()))
print("series columns dropped:", [c for c in rt.UNUSED_FLAGS if c in series])
nums = [k for k in json.dumps(rt.to_json(counts))]
# Every string inside the counts, to see if a price or an IV can enter one.
def strings(v):
    if isinstance(v, dict):
        for k, x in v.items():
            yield str(k); yield from strings(x)
    elif isinstance(v, str):
        yield v
print("strings in counts:", sorted(set(strings(rt.to_json(counts)))))

# Clean full run through run_test, with real save_test_frames on scratch.
root = OUT / "clean"; root.mkdir(exist_ok=True)
for f in root.glob("*"):
    f.unlink()
p = root / "bars.json"; bars(p, window)
marker = root / "m.json"
for name, scope in (("o1.json", "options"), ("o2.json", "outcomes")):
    (root / name).write_text(json.dumps(dict(purpose="stage5_one_time_test", scope=scope, approved_by="user", approved_on="2026-11-04")))
evs = [i for i in rt.ev.EVENTS if pd.Timestamp(START) <= pd.Timestamp(i[1]) <= pd.Timestamp(END)]
run_b = lambda s: rt.step_b(s, pd.Timestamp(START), pd.Timestamp(END), None, evs, 60, "open-window check", p)
result = rt.run_test(None, root / "run.json", root / "res.json", root / "o1.json", root / "o2.json", lambda: None, lambda: (series, terms, counts), run_b, rt.save_test_frames, lambda: "h", root / "a.json")
print("result keys:", list(result)); print("frames:", sorted(x.name for x in (OUT / "frames").iterdir())); print("JSON round trip ok:", isinstance(json.loads((root / "res.json").read_text()), dict))
sa = json.loads((root / "a.json").read_text()); print("Step A file keys:", list(sa), "| counts keys:", list(sa["counts"]))
# Scan the Step A file for any float that matches a close, a forward, or an IV.
vals = set(np.round(window["close"], 6)) | set(np.round(series["near_forward"].dropna(), 6)) | set(np.round(series["atm30"].dropna(), 6))
def nums(v):
    if isinstance(v, dict):
        for x in v.values():
            yield from nums(x)
    elif isinstance(v, float):
        yield v
print("Step A floats:", list(nums(sa)), "| match a price or IV:", any(round(x, 6) in vals for x in nums(sa)))

# Faults through the real step_b.
def attempt(name, s, frame):
    q = OUT / f"{name}.json"; bars(q, frame)
    try:
        r, _ = rt.step_b(s, pd.Timestamp(START), pd.Timestamp(END), None, evs, 10, "x", q)
        print(f"{name}: NOT stopped, outcome {r['decision']['outcome']}, b {r['rule1']['b']:.3f}")
    except rt.InputGuardFailed as e:
        print(f"{name}: stopped: {e}")
    except Exception as e:
        print(f"{name}: crash, not the guard: {type(e).__name__}")


bad = window.copy(); bad.iloc[200, bad.columns.get_loc("close")] *= 1.5
attempt("one close 50% high", series, bad)
attempt("one close 25% high", series, window.assign(close=np.where(np.arange(len(window)) == 200, window["close"] * 1.25, window["close"])))
attempt("one close 20% high (under .25)", series, window.assign(close=np.where(np.arange(len(window)) == 200, window["close"] * 1.20, window["close"])))
attempt("four sessions missing", series, window.drop(window.index[[10, 20, 30, 40]]))
attempt("three sessions missing", series, window.drop(window.index[[10, 20, 30]]))
attempt("dates shifted one day", series, window.assign(session_date=window["session_date"] - pd.Timedelta(days=1)))
attempt("all closes split-adjusted by half", series, window.assign(close=window["close"] / 2))

# Wrong definitions on a share of days, through the real snapshot code.
real_iter = bs.iter_days
for share in (1.0, 0.10, 0.03):
    rng = np.random.default_rng(1)
    def fake_iter(path, *args, **kw):
        for day, frame in real_iter(path, *args, **kw):
            if path == bs.OPTION_DEFINITIONS and rng.random() < share:
                frame = frame.copy(); frame["instrument_id"] = rng.permutation(frame["instrument_id"].to_numpy())
            yield day, frame
    bs.iter_days = fake_iter
    s2, _, c2 = a()
    bs.iter_days = real_iter
    print(f"wrong map on {share:.0%} of days: atm30 days {c2['atm30_days']}, floor {rt.floor_from_flags(s2)}")
    attempt(f"wrong map {share:.0%}", s2, window)

# Blank rates: can a person see the cause in the Step A counts?
rates = pd.read_csv(SOURCE / "fred_rates.csv", nrows=0).columns.tolist()
blank = OUT / "blank_rates.csv"
frame = pd.read_csv(SOURCE / "fred_rates.csv")
frame = frame[frame["observation_date"] >= "2020-01-01"]
frame[["DGS1MO", "DGS3MO"]] = np.nan
frame.to_csv(blank, index=False)
try:
    s3, _, c3 = a(blank)
    print("blank rates: atm30 days", c3["atm30_days"], "floor", rt.floor_from_flags(s3), "status:", c3["status_by_year"])
except Exception as e:
    print("blank rates: safe crash:", rt.safe_error(e))

# Guard on all open sessions, with separate code, and all rolling 28-month windows to the data end.
full = closes.merge(pd.read_parquet(DATA / "index_series.parquet")[["session_date", "near_forward"]], on="session_date", how="left")
g = np.log(full["near_forward"] / full["close"]).abs().dropna()
print("open data: rows", len(g), "median", round(g.median(), 5), "share>5%", round((g > .05).mean(), 5), "max", round(g.max(), 4))
fails = 0; n = 0
for start in pd.period_range("2018-05", "2024-05", freq="M"):
    w = full[full["session_date"].between(start.to_timestamp(), (start + 27).to_timestamp(how="end"))]
    n += 1
    try:
        rt.input_guard(w, 0, 0)
    except rt.InputGuardFailed:
        fails += 1
print("open windows:", n, "stops:", fails)
print("real manifest untouched by this script: hash", freeze.manifest_hash())
