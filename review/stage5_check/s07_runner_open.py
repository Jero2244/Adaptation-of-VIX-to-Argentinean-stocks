"""Run step_a and step_b on the first open 28 months, then recompute key items by independent code. Bars come from
data/alpaca_open_closes.parquet, written to a synthetic JSON file here. The real Alpaca file stays closed. Output goes under review/stage5_check/."""
import _common, json
from _common import HERE, ROOT
import numpy as np, pandas as pd
import run_tests_once as rt, stage4_rules as rules, inference as inf, forecasts as fc, events as ev
from config import SOURCE

START, END = "2018-05-01", "2020-08-31"
OUT = HERE / "run_out"
OUT.mkdir(exist_ok=True)
closes = pd.read_parquet(ROOT / "data/alpaca_open_closes.parquet")
print("open closes", closes.session_date.min().date(), closes.session_date.max().date(), len(closes))
official = pd.read_parquet(ROOT / "data/equity_official_daily.parquet")
official["session_date"] = pd.to_datetime(official["session_date"])
j = closes.merge(official[["session_date", "official_close_price"]], on="session_date")
gap = 1e4 * np.log(j.close / j.official_close_price).abs()
print("HANDOFF check: sessions", len(j), "with a difference", int((gap > 1e-6).sum()), "largest bp", round(gap.max(), 2))
c = closes[closes.session_date.between(START, END)]
path = OUT / "bars_open.json"
path.write_text(json.dumps(dict(pages=[dict(bars=dict(GGAL=[dict(t=f"{d.date()}T12:00:00Z", c=float(v)) for d, v in zip(c.session_date, c.close)]))])))
series, terms, counts = rt.step_a(START, END, None, SOURCE / "fred_rates.csv")
floor = rt.floor_from_flags(series)
print("step A", counts, floor)
events = [e for e in ev.EVENTS if pd.Timestamp(START) <= pd.Timestamp(e[1]) <= pd.Timestamp(END)]
result, panel = rt.step_b(series, pd.Timestamp(START), pd.Timestamp(END), None, events, 2000, "open check", path)
panel.to_parquet(OUT / "panel.parquet", index=False)
terms.to_parquet(OUT / "terms.parquet", index=False)
print("panel and terms write to parquet without error")
rt.write_json(OUT / "result.json", result)
print({k: result[k] for k in ("floor", "line", "decision", "counts")})
print("rule1", result["rule1"])
print("no_events", result["no_events"])
print("race scored", result["race"]["scored"], result["race"]["first_scored"])
print("step A floor = step B floor:", floor == result["floor"])

# Independent recomputation
d = c.reset_index(drop=True)
dates = d.session_date.to_numpy()
r = np.log(d.close / d.close.shift(1)).to_numpy()
cash = pd.read_csv(ROOT / "data/adr_cash_events.csv", parse_dates=["ex_date"])
cash = cash[cash.ex_date.between(START, END)]
for _, row in cash.iterrows():
    k = np.flatnonzero(dates == np.datetime64(row.ex_date))[0]
    r[k] = np.log((d.close[k] + row.usd_per_ads) / d.close[k - 1])
rv = []
for i in range(len(d)):
    e = dates[i] + np.timedelta64(30, "D")
    if e > dates[-1]:
        rv.append(np.nan)
        continue
    m = (dates > dates[i]) & (dates <= e)
    rv.append((r[m] ** 2).sum() * 365 / 30)
rv = np.array(rv)
print("rv30 max abs diff", np.nanmax(np.abs(rv - panel.rv30.to_numpy())), "same blanks", (np.isnan(rv) == panel.rv30.isna().to_numpy()).all())
print("first origin with HAR", int(panel.log_rv22.notna().idxmax()), "last origin with rv30", panel.session_date[panel.rv30.notna()].max().date(), "its window end", panel.window_end[panel.rv30.notna()].max().date(), "last session", panel.session_date.max().date())
for L in (1, 5, 22):
    h = np.array([np.nan if i < L else np.log(252 * max(np.mean(r[i - L + 1:i + 1] ** 2), 1e-6)) for i in range(len(d))])
    print("log_rv", L, "max abs diff", np.nanmax(np.abs(h - panel[f"log_rv{L}"].to_numpy())), "same blanks", (np.isnan(h) == panel[f"log_rv{L}"].isna().to_numpy()).all())
p = panel[panel.primary]
X = np.column_stack([np.ones(len(p)), p.log_rv1, p.log_rv5, p.log_rv22, np.log(p.atm30 ** 2)])
y = np.log(p.rv30.to_numpy())
print("b own lstsq", np.linalg.lstsq(X, y, rcond=None)[0][4], "vs", result["rule1"]["b"])
pos = p.position.to_numpy()
for block in (21, 63):
    g = np.random.default_rng(rules.SEED + block)
    dr = []
    for _ in range(2000):
        ix = inf.block_sample(pos, block, g)
        dr.append(np.linalg.lstsq(X[ix], y[ix], rcond=None)[0][4])
    print(block, "own percentile", np.percentile(dr, [2.5, 97.5]), "vs", result["rule1"][f"low{block}"], result["rule1"][f"high{block}"])
primary = panel.primary.to_numpy()
wend = panel.window_end.to_numpy()
da = panel.session_date.to_numpy()
fs = fc.expanding_forecasts(panel, rules.HAR, primary, primary & (panel.position.to_numpy() >= 252), smearing=False)
sc = np.flatnonzero(np.isfinite(fs))[0]
tr = primary & (wend <= da[sc]) & (np.arange(len(panel)) < sc)
print("first scored", panel.session_date[sc].date(), "pos", sc, "train rows", int(tr.sum()), "latest training window end", pd.Timestamp(wend[tr].max()).date())
Xt = np.column_stack([np.ones(tr.sum())] + [panel.loc[tr, n] for n in rules.HAR])
be = np.linalg.lstsq(Xt, np.log(panel.rv30[tr].to_numpy()), rcond=None)[0]
print("own forecast", float(np.exp(np.r_[1, panel.loc[sc, rules.HAR].to_numpy(float)] @ be)), "vs", fs[sc])
evs = [ev.first_session(e[1], panel.session_date.to_numpy()) for e in events]
print("events", [str(x.date()) for x in evs])
keep = np.ones(len(p), bool)
for e in evs:
    keep &= ~((p.session_date < e) & (p.session_date + pd.Timedelta(days=30) >= e)).to_numpy()
print("no-event rows own", int(keep.sum()), "vs", result["no_events"]["n"])
