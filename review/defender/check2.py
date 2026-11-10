import sys
sys.path.insert(0, r"C:\Users\HP Laptop\.spyder-py3\2024-1\vix_ggal_adaptation")
sys.dont_write_bytecode = True
import numpy as np, pandas as pd
import inference as inf, forecasts as fc

ROOT = r"C:\Users\HP Laptop\.spyder-py3\2024-1\vix_ggal_adaptation"
p = pd.read_parquet(ROOT + r"\data\forecast_panel.parquet")
HAR = ["log_rv1", "log_rv5", "log_rv22"]; IV = "log_iv2"
sc = p.dropna(subset=["c_har", "c_har_atm", "m_har", "m_har_atm", "f_har", "f_har_atm", "rv30"]).copy()
print("scored", len(sc), sc.session_date.min())
tgt = sc.rv30.to_numpy(); pos = sc.position.to_numpy()


def report(name, d, blocks=(21, 63), mask=None):
    q = d if mask is None else d[mask]; po = pos if mask is None else pos[mask]
    o = [name, "mean", round(q.mean(), 4)]
    for b in blocks:
        if b * 3 > po[-1] - po[0] + 1:
            continue
        dr = inf.block_bootstrap(lambda i: np.array([q[i].mean()]), po, b, 2000, 3 + b)
        o += [f"b{b} t", round(q.mean() / dr.std(ddof=1), 2), "ci", round(np.percentile(dr, 2.5), 4), round(np.percentile(dr, 97.5), 4)]
    print(*o)


Q = fc.qlike
print("\n== E1 race variants on the same 1460 rows, QLIKE HAR+ATM - HAR")
report("smear, common train (reported)", Q(tgt, sc.c_har_atm) - Q(tgt, sc.c_har))
report("no smear, common train (reported)", Q(tgt, sc.m_har_atm) - Q(tgt, sc.m_har))
report("smear, all-days train (f_)", Q(tgt, sc.f_har_atm) - Q(tgt, sc.f_har))
print("means: c_har", sc.c_har.mean(), "c_har_atm", sc.c_har_atm.mean(), "f_har", sc.f_har.mean(), "f_har_atm", sc.f_har_atm.mean(), "m_har", sc.m_har.mean(), "m_atm", sc.m_har_atm.mean(), "tgt", tgt.mean())

# no-smear on all-days training
valid = p.primary.to_numpy(); mask = p.index.isin(sc.index)
p["nf_har"] = fc.expanding_forecasts(p, HAR, valid, mask, smearing=False)
p["nf_har_atm"] = fc.expanding_forecasts(p, HAR + [IV], valid, mask, smearing=False)
sc = sc.join(p[["nf_har", "nf_har_atm"]])
report("no smear, all-days train", Q(tgt, sc.nf_har_atm) - Q(tgt, sc.nf_har))

print("\n== E2 smear factors")
for n in ("har", "har_atm", "atm", "ewma", "garch_t"):
    r = (sc["c_" + n] / sc["m_" + n])
    print(n, "smear mean", round(r.mean(), 3), "first", round(r.iloc[0], 3), "at 2021-01", round(r[sc.session_date >= "2021-01-01"].iloc[0], 3), "at 2024-01", round(r[sc.session_date >= "2024-01-01"].iloc[0], 3), "last", round(r.iloc[-1], 3))
r = sc.f_har / sc.nf_har; r2 = sc.f_har_atm / sc.nf_har_atm
print("all-days smear har mean", r.mean(), "first", r.iloc[0], "last", r.iloc[-1], "; har_atm", r2.mean(), r2.iloc[0], r2.iloc[-1])

print("\n== E3 common smear: both models use HAR+ATM factor, or both HAR factor")
sm_h = (sc.c_har / sc.m_har); sm_a = (sc.c_har_atm / sc.m_har_atm)
report("both HAR factor", Q(tgt, sc.m_har_atm * sm_h) - Q(tgt, sc.m_har * sm_h))
report("both ATM factor", Q(tgt, sc.m_har_atm * sm_a) - Q(tgt, sc.m_har * sm_a))
sg = (sm_h * sm_a) ** .5
report("both geo-mean", Q(tgt, sc.m_har_atm * sg) - Q(tgt, sc.m_har * sg))


# trailing smear excluding PASO windows or rolling 252 rows
def smear_series(inputs, rule):
    design = np.column_stack([np.ones(len(p))] + [p[c].to_numpy(float) for c in inputs])
    y = p.rv30.to_numpy(float); d = p.session_date.to_numpy(); w = p.window_end.to_numpy()
    common = p.primary.to_numpy() & p.log_garch.notna().to_numpy() & p.log_garch_t.notna().to_numpy() & p.log_ewma.notna().to_numpy()
    paso = (p.session_date < "2019-08-12") & (p.window_end >= "2019-08-12")
    out = np.full(len(p), np.nan)
    for o in sc.index:
        tr = common & (w <= d[o]) & (np.arange(len(p)) < o)
        b = np.linalg.lstsq(design[tr], np.log(y[tr]), rcond=None)[0]
        res = np.log(y[tr]) - design[tr] @ b
        if rule == "exclude_paso":
            res = res[~paso.to_numpy()[tr]]
            f = np.mean(np.exp(res))
        elif rule == "rolling252":
            f = np.mean(np.exp(res[-252:]))
        elif rule == "lognormal":
            f = np.exp(.5 * res.var())
        out[o] = np.exp(design[o] @ b) * f
    return out[sc.index]


print("\n== E4 alternate smearing rules, QLIKE levels and differences")
for rule in ("exclude_paso", "rolling252", "lognormal"):
    a = smear_series(HAR, rule); b = smear_series(HAR + [IV], rule)
    print(rule, "qlike har", round(Q(tgt, a).mean(), 4), "har_atm", round(Q(tgt, b).mean(), 4), "mean f", round(a.mean(), 3), round(b.mean(), 3))
    report(rule, Q(tgt, b) - Q(tgt, a))

print("\n== E5 log-loss race, no conversion to level; HAR+ATM vs HAR")
ly = np.log(tgt); e_h = ly - np.log(sc.m_har.to_numpy()); e_a = ly - np.log(sc.m_har_atm.to_numpy())
report("log MSE diff (common train)", e_a ** 2 - e_h ** 2)
report("log MAE diff", np.abs(e_a) - np.abs(e_h))
cw = e_h ** 2 - (e_a ** 2 - (np.log(sc.m_har.to_numpy()) - np.log(sc.m_har_atm.to_numpy())) ** 2)
report("Clark-West adj (positive favors ATM)", cw)
print("OOS R2 vs expanding? log MSE har", (e_h ** 2).mean(), "har_atm", (e_a ** 2).mean(), "gain share", 1 - (e_a ** 2).mean() / (e_h ** 2).mean())
for lab, lo, hi in (("2018-2023", "2018", "2024"), ("2024-2025", "2024", "2026"), ("2026", "2026", "2027")):
    m = ((sc.session_date >= lo) & (sc.session_date < hi)).to_numpy()
    print(lab, "n", m.sum(), "logMSE har", round((e_h[m] ** 2).mean(), 4), "har+atm", round((e_a[m] ** 2).mean(), 4))
    report(lab + " log MSE diff", e_a ** 2 - e_h ** 2, blocks=(21,), mask=m)
    report(lab + " QLIKE smear diff", (Q(tgt, sc.c_har_atm) - Q(tgt, sc.c_har)), blocks=(21,), mask=m)
    report(lab + " QLIKE nosmear diff", (Q(tgt, sc.m_har_atm) - Q(tgt, sc.m_har)), blocks=(21,), mask=m)
# raw race scored window, log
sr = p.dropna(subset=["f_har", "f_har_atm", "rv30"]).copy()
print("raw race n", len(sr), sr.session_date.min())
p2 = p.copy()

print("\n== E6 smear vs no smear by period, every model (negative: smear better)")
for n in ("atm", "ewma", "garch", "garch_t", "har", "har_atm"):
    row = [n]
    for lab, lo, hi in (("all", "2018", "2027"), ("18-23", "2018", "2024"), ("24-25", "2024", "2026"), ("26", "2026", "2027")):
        m = ((sc.session_date >= lo) & (sc.session_date < hi)).to_numpy()
        row += [lab, round((Q(tgt[m], sc["c_" + n][m]) - Q(tgt[m], sc["m_" + n][m])).mean(), 4)]
    print(*row)
print("share of no-smear gain in first 12 months")
m = (sc.session_date < "2021-01-01").to_numpy()
print("n", m.sum(), "HAR smear-nosmear pre2021", (Q(tgt[m], sc.c_har[m]) - Q(tgt[m], sc.m_har[m])).mean(), "post", (Q(tgt[~m], sc.c_har[~m]) - Q(tgt[~m], sc.m_har[~m])).mean())
print("HAR+ATM diff smear pre2021", (Q(tgt[m], sc.c_har_atm[m]) - Q(tgt[m], sc.c_har[m])).mean(), "post2021", (Q(tgt[~m], sc.c_har_atm[~m]) - Q(tgt[~m], sc.c_har[~m])).mean())
print("HAR+ATM diff nosmear pre2021", (Q(tgt[m], sc.m_har_atm[m]) - Q(tgt[m], sc.m_har[m])).mean(), "post2021", (Q(tgt[~m], sc.m_har_atm[~m]) - Q(tgt[~m], sc.m_har[~m])).mean())

print("\n== F look-ahead perturbation")
rng = np.random.default_rng(1)
for o in (int(sc.index[0]), int(sc.index[500]), int(sc.index[-1])):
    q = p.copy(); dt = q.session_date.iloc[o]
    fut = q.window_end > dt
    q.loc[fut & (q.index != o), "rv30"] = rng.lognormal(size=(fut & (q.index != o)).sum())
    q.loc[q.index > o, HAR + [IV]] = rng.normal(size=((q.index > o).sum(), 4))
    common = p.primary.to_numpy() & p.log_garch.notna().to_numpy() & p.log_garch_t.notna().to_numpy() & p.log_ewma.notna().to_numpy()
    sm = np.zeros(len(q), bool); sm[o] = True
    a = fc.expanding_forecasts(q, HAR + [IV], common, sm)[o]
    print(o, dt.date(), "perturbed", a, "panel", p.c_har_atm.iloc[o], "equal", np.isclose(a, p.c_har_atm.iloc[o]))
ret = p.return_total.to_numpy(); ses = p.window_sessions.to_numpy()
o = 252 + 21 * 40
tr = ret.copy(); tr[o + 1:] = rng.normal(0, .5, len(tr) - o - 1)
g, _ = fc.garch_forecasts(tr[:o + 1], ses[:o + 1], dist="t")
print("GARCH t truncated at", o, g[o], "panel", p.f_garch_t_raw.iloc[o], np.isclose(g[o], p.f_garch_t_raw.iloc[o]))

print("\n== K EWMA lambda and GARCH")
sr = p.dropna(subset=["f_har", "f_har_atm", "f_atm_raw", "f_ewma_raw", "f_garch_raw", "f_garch_t_raw", "rv30"])
for lam in (.90, .94, .97, .98):
    e = fc.CALENDAR_ANNUAL * fc.ewma_variance(ret, lam) * np.where(ses > 0, ses, np.nan)
    pe = pd.Series(e, index=p.index)[sr.index]
    print("lam", lam, "raw qlike all", round(Q(sr.rv30, pe).mean(), 4), "no PASO", round(Q(sr.rv30, pe)[~((sr.session_date < "2019-08-12") & (sr.window_end >= "2019-08-12")).to_numpy()].mean(), 4))
print("ATM30 raw", Q(sr.rv30, sr.f_atm_raw).mean())
fits = pd.read_csv(ROOT + r"\reports\stage3_garch_fits.csv")
print(fits.groupby("dist").agg(n=("origin", "size"), fail=("reason", lambda x: x.notna().sum()), amed=("alpha", "median"), bmed=("beta", "median"), amax=("alpha", "max")))
print("primary comparison affected by t? common mask with and without t identical:", ((p.primary & p.log_garch.notna() & p.log_ewma.notna()) == (p.primary & p.log_garch.notna() & p.log_ewma.notna() & p.log_garch_t.notna())).all())

print("\n== J events")
ev = pd.read_csv(ROOT + r"\reports\stage3_events.csv"); pl = pd.read_csv(ROOT + r"\reports\stage3_placebos.csv")
print(pl.columns.tolist())
for _, r in ev.iterrows():
    g = pl[(pl.event == r.event) & pl.ratio.notna()]
    near = g[(g.near_days - r.near_days).abs() <= 3]
    print(r.event, "ratio", round(r.ratio, 3), "near", round(r.near_days, 1), "plac n", len(g), "share below", round((g.ratio < r.ratio).mean(), 3), "| same near n", len(near), "share", round((near.ratio < r.ratio).mean(), 3) if len(near) else None, "pl near med", round(g.near_days.median(), 1), "uniq", g.placebo_session.nunique())
print("all unique placebo sessions", pl.placebo_session.nunique(), "total rows", len(pl))
