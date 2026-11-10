import sys
import numpy as np
import pandas as pd
ROOT = r"C:\Users\HP Laptop\.spyder-py3\2024-1\vix_ggal_adaptation"
sys.path.insert(0, ROOT)
import forecasts as fc
import inference as inf
import events as ev

pd.set_option("display.width", 200, "display.max_columns", 30, "display.max_rows", 100)
p = pd.read_parquet(ROOT + r"\data\forecast_panel.parquet")
HAR = ["log_rv1", "log_rv5", "log_rv22"]
IV = "log_iv2"
FULL = HAR + [IV]


def ols_b(frame, names=FULL, key=IV):
    X = np.column_stack([np.ones(len(frame))] + [frame[n].to_numpy(float) for n in names])
    r = inf.ols(frame.log_rv30.to_numpy(float), X)
    i = 1 + names.index(key)
    return r["beta"][i], r["beta"][i] / r["classical_se"][i]


def boot(d, positions, block, reps=2000, seed=20261104):
    draws = inf.block_bootstrap(lambda idx: np.array([d[idx].mean()]), positions, block, reps, seed + block)
    s = inf.bootstrap_summary(np.array([d.mean()]), draws)
    return round(float(d.mean()), 4), round(float(s["t"][0]), 2), round(float(s["low"][0]), 4), round(float(s["high"][0]), 4)


# 1. Smearing by model in 2024-2025.
l = pd.read_csv(ROOT + r"\reports\stage3_race_levels.csv")
v = l[(l.period == "2024-2025") & l.race.isin(["calibrated", "calibrated, no smearing"])].pivot(index="model", columns="race", values="qlike")
v["no_smear_worse"] = v["calibrated, no smearing"] > v["calibrated"]
print(v.round(4)); print("worse without smearing:", int(v.no_smear_worse.sum()), "of", len(v))
print(l[(l.period == "2024-2025") & (l.race == "calibrated, no smearing")][["model", "mean_forecast", "mean_target"]].round(3))

# 2. Offsets: distinct samples.
o = pd.read_csv(ROOT + r"\reports\stage3_offsets.csv")
h = o[o.spec == "HAR+IV"].drop_duplicates("sample_id")
print("distinct", len(h), "t above 2", int((h.classical_t > 2).sum()), "b", round(h.coefficient.median(), 3))

# 3. Fixed-step samples.
valid = p.primary.to_numpy()
first = int(np.flatnonzero(valid)[0])
dates = p.session_date.to_numpy()
for step in (22, 23):
    rows = []
    for offset in range(step):
        pos = np.arange(first + offset, len(p), step)
        pos = pos[valid[pos]]
        gap = (dates[pos[1:]] - dates[pos[:-1]]).min() / np.timedelta64(1, "D")
        c = p.iloc[pos]
        calm = c[~((c.session_date < "2019-08-12") & (c.window_end >= "2019-08-12"))]
        rows.append((offset, len(c), gap, *ols_b(c), *ols_b(calm)))
    t = pd.DataFrame(rows, columns=["offset", "n", "min_gap", "b", "t", "b_no_paso", "t_no_paso"])
    print("step", step, "n", t.n.median(), "min gap days", t.min_gap.min(), "mean b", round(t.b.mean(), 3), "range", round(t.b.min(), 3), round(t.b.max(), 3), "median t", round(t.t.median(), 2), "| no PASO mean", round(t.b_no_paso.mean(), 3), "range", round(t.b_no_paso.min(), 3), round(t.b_no_paso.max(), 3), "median t", round(t.t_no_paso.median(), 2))

# 4. Calibrated rows, training start, and Clark-West.
cols = ["c_atm", "c_ewma", "c_garch", "c_garch_t", "c_har", "c_har_atm", "rv30"]
scored_mask = p[cols].notna().all(axis=1).to_numpy()
s = p[scored_mask]
y, pos = s.rv30.to_numpy(), s.position.to_numpy()
print("scored", len(s), s.session_date.min().date())
print("QLIKE common, smearing", boot(fc.qlike(y, s.c_har_atm) - fc.qlike(y, s.c_har), pos, 21))
print("QLIKE common, no smearing", boot(fc.qlike(y, s.m_har_atm) - fc.qlike(y, s.m_har), pos, 21))
train = p.primary.to_numpy()
long = {}
for name, inputs, smear in (("h_s", HAR, True), ("f_s", FULL, True), ("h_m", HAR, False), ("f_m", FULL, False)):
    long[name] = fc.expanding_forecasts(p, inputs, train, scored_mask, smearing=smear)[scored_mask]
print("QLIKE long training, smearing", boot(fc.qlike(y, long["f_s"]) - fc.qlike(y, long["h_s"]), pos, 21))
print("QLIKE long training, no smearing", boot(fc.qlike(y, long["f_m"]) - fc.qlike(y, long["h_m"]), pos, 21))
ly = np.log(y)


def clark_west(f_small, f_big, positions, target):
    d = (target - f_small) ** 2 - ((target - f_big) ** 2 - (f_small - f_big) ** 2)
    return boot(d, positions, 21), boot(d, positions, 63)


print("CW common", clark_west(np.log(s.m_har.to_numpy()), np.log(s.m_har_atm.to_numpy()), pos, ly))
print("CW long training", clark_west(np.log(long["h_m"]), np.log(long["f_m"]), pos, ly))
print("log MSE diff common", boot((ly - np.log(s.m_har_atm.to_numpy())) ** 2 - (ly - np.log(s.m_har.to_numpy())) ** 2, pos, 21))
raw = p.dropna(subset=["f_har", "f_har_atm", "rv30"])
# Raw dates, no smearing, from the study's raw-race training.
raw_mask = p.index.isin(raw.index)
h = fc.expanding_forecasts(p, HAR, train, raw_mask, smearing=False)[raw_mask]
f = fc.expanding_forecasts(p, FULL, train, raw_mask, smearing=False)[raw_mask]
ry, rpos = raw.rv30.to_numpy(), raw.position.to_numpy()
print("raw dates rows", len(raw), "QLIKE no smearing", boot(fc.qlike(ry, f) - fc.qlike(ry, h), rpos, 21))
print("CW raw", clark_west(np.log(h), np.log(f), rpos, np.log(ry)))
parts = raw.assign(d=fc.qlike(ry, f) - fc.qlike(ry, h))
paso = (parts.session_date < "2019-08-12") & (parts.window_end >= "2019-08-12")
early = (parts.session_date < "2019-12-11") & ~paso
print("sum PASO", paso.sum(), round(parts.d[paso].sum(), 1), "sum early", early.sum(), round(parts.d[early].sum(), 1), "sum later", (~paso & ~early).sum(), round(parts.d[~paso & ~early].sum(), 1))

# 5. Where b sits.
a = p[p.primary]
sessions = p.session_date.to_numpy()
inside = np.zeros(len(a), bool)
for _, date in ev.EVENTS:
    day = ev.first_session(date, sessions)
    inside |= ((a.session_date < day) & (a.window_end >= day)).to_numpy()
print("no events b", round(ols_b(a[~inside])[0], 3), "n", int((~inside).sum()))
print("no events before 2025-03 b", round(ols_b(a[~inside & (a.session_date < "2025-03-01").to_numpy()])[0], 3), "n", int((~inside & (a.session_date < "2025-03-01").to_numpy()).sum()))
print("from 2025-03 b", round(ols_b(a[a.session_date >= "2025-03-01"])[0], 3), "n", int((a.session_date >= "2025-03-01").sum()))
print("from 2025-03, no events b", round(ols_b(a[~inside & (a.session_date >= "2025-03-01").to_numpy()])[0], 3))
rng = np.random.default_rng(1)
span = ev.first_session
draws = []
for _ in range(1000):
    pick = rng.choice(len(sessions) - 1, size=len(ev.EVENTS), replace=False)
    mask = np.zeros(len(a), bool)
    for q in pick:
        mask |= ((a.session_date < sessions[q]) & (a.window_end >= sessions[q])).to_numpy()
    draws.append(ols_b(a[~mask])[0])
print("random drops", np.round(np.percentile(draws, [2.5, 50, 97.5]), 3), "share below .459", float(np.mean(np.array(draws) < ols_b(a[~inside])[0])))
# 6. Within-year spread terciles.
g = a.copy()
g["t"] = g.groupby("year").relative_spread.transform(lambda v: pd.qcut(v, 3, labels=False))
d = pd.get_dummies(g.year, prefix="y", drop_first=True, dtype=float)
g = pd.concat([g, d], axis=1)
print("within-year spread terciles", [round(ols_b(g[g.t == k], FULL + list(d.columns))[0], 3) for k in range(3)])
# 7. Floor binds.
print("floor rows", int((p.primary & (p.return_total ** 2 < 1e-6)).sum()), "of all sessions share", round(float((p.return_total ** 2 < 1e-6).mean()), 4))
