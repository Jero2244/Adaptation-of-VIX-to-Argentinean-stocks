"""What flows through when an input is silently wrong. Open window only.
A: definitions matched to the wrong instrument ids each day. B: rate columns blank. C: one bad close.
It shows whether the floor passes, whether the run gives a verdict, and whether a forward-to-close check would catch the fault.
Also prints the forward-to-close distribution by year on the full open panel, to size a limit."""
import _common, json
from _common import HERE, ROOT
import numpy as np, pandas as pd
import run_tests_once as rt, build_snapshot as bs, load_data as ld
from config import SOURCE

START, END = "2018-05-01", "2020-08-31"
OUT = HERE / "run_out"
OUT.mkdir(exist_ok=True)
closes = pd.read_parquet(ROOT / "data/alpaca_open_closes.parquet")
c = closes[closes.session_date.between(START, END)].copy()


def bars(frame, name):
    path = OUT / name
    path.write_text(json.dumps(dict(pages=[dict(bars=dict(GGAL=[dict(t=f"{d.date()}T12:00:00Z", c=float(v)) for d, v in zip(frame.session_date, frame.close)]))])))
    return path


base = bars(c, "bars_open.json")


def check(panel):
    x = panel.dropna(subset=["near_forward"])
    g = np.log(x.near_forward / x.close).abs()
    return dict(n=len(x), median_abs=round(float(g.median()), 4), q95=round(float(g.quantile(.95)), 4), share_above_5pct=round(float((g > .05).mean()), 4), max=round(float(g.max()), 3))


def run(label, path=base, ratefile=SOURCE / "fred_rates.csv"):
    series, terms, counts = rt.step_a(START, END, None, ratefile)
    floor = rt.floor_from_flags(series)
    print(f"--- {label}\n step A {counts} floor {floor}", flush=True)
    if not floor["passed"]:
        print(" status counts", series.status.value_counts().head(3).to_dict())
        print(" the run would stop here with the final result: Inconclusive, data floor")
        return
    res, panel = rt.step_b(series, pd.Timestamp(START), pd.Timestamp(END), None, [], 300, "check", path)
    print(" b", round(res["rule1"]["b"], 3), "n", res["rule1"]["n"], "|", res["decision"]["outcome"])
    print(" median atm30", round(float(panel.atm30.median()), 3), "forward vs close", check(panel), flush=True)


run("clean")
orig = ld.read_member
rng = np.random.default_rng(1)


def shuffled(archive, name, map_symbols=True):
    frame = orig(archive, name, map_symbols)
    if "definition" in name:
        ids = frame.instrument_id.unique()
        frame = frame.assign(instrument_id=frame.instrument_id.map(dict(zip(ids, rng.permutation(ids)))))
    return frame


ld.read_member = shuffled
run("A: definitions matched to the wrong instrument ids")
ld.read_member = orig
blank = OUT / "rates_blank.csv"
rates = pd.read_csv(SOURCE / "fred_rates.csv")
rates["DGS1MO"] = np.nan
rates["DGS3MO"] = np.nan
rates.to_csv(blank, index=False)
try:
    run("B: rate columns all blank", ratefile=blank)
except Exception as error:
    print("B crash", type(error).__name__)
bad = c.copy()
bad.iloc[len(bad) // 2, bad.columns.get_loc("close")] *= 1.5
run("C: one close 50% too high", path=bars(bad, "bars_bad.json"))

print("--- forward to close, full open panel")
series = pd.read_parquet(ROOT / "data/index_series.parquet")
x = series.merge(closes, on="session_date").dropna(subset=["near_forward"])
x["g"] = np.log(x.near_forward / x.close).abs()
print(x.groupby(x.session_date.dt.year).g.describe(percentiles=[.5, .95, .99]).round(4).to_string())
print("rows above 5%:", int((x.g > .05).sum()), "of", len(x))
