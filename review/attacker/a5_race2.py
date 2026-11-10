"""Correct Clark-West sign (a1 had it reversed). Scale-free QLIKE. Smearing variants. Period split."""
import sys
PROJECT = r"C:\Users\HP Laptop\.spyder-py3\2024-1\vix_ggal_adaptation"
sys.path.insert(0, PROJECT)
import numpy as np, pandas as pd
import forecasts as fc, inference as inf

p = pd.read_parquet(PROJECT + r"\data\forecast_panel.parquet")
HAR = ["log_rv1", "log_rv5", "log_rv22"]; IV = "log_iv2"
primary = p.primary.to_numpy()
common = primary & p.log_garch.notna().to_numpy() & p.log_garch_t.notna().to_numpy() & p.log_ewma.notna().to_numpy()
dates = p.session_date.to_numpy(); we = p.window_end.to_numpy(); tgt = np.log(p.rv30.to_numpy()); pos_all = p.position.to_numpy()
PASO = np.datetime64("2019-08-12")
is_paso = (dates < PASO) & (we >= PASO)


def forecasts(names, train, mask):
    """Log forecast and smear variants at each scored origin."""
    X = np.column_stack([np.ones(len(p))] + [p[n].to_numpy(float) for n in names])
    out = {k: np.full(len(p), np.nan) for k in ("logf", "duan", "win99", "win975", "gauss", "nopaso")}
    for o in np.flatnonzero(mask):
        if o < 252:
            continue
        t = train & (we <= dates[o]) & (np.arange(len(p)) < o)
        if t.sum() < 126:
            continue
        b = np.linalg.lstsq(X[t], tgt[t], rcond=None)[0]
        e = tgt[t] - X[t] @ b
        out["logf"][o] = X[o] @ b
        out["duan"][o] = np.exp(e).mean()
        out["win99"][o] = np.exp(np.minimum(e, np.quantile(e, .99))).mean()
        out["win975"][o] = np.exp(np.minimum(e, np.quantile(e, .975))).mean()
        out["gauss"][o] = np.exp(e.var() / 2)
        out["nopaso"][o] = np.exp(e[~is_paso[t]]).mean()
    return out


def boot(dv, pos, block=21, reps=2000):
    dr = inf.block_bootstrap(lambda i: np.array([dv[i].mean()]), pos, block, reps, 11)
    return dv.mean(), dv.mean() / dr.std(ddof=1), np.percentile(dr, 2.5), np.percentile(dr, 97.5)


rawmask = primary & (pos_all >= 252)
calmask = common & (p.session_date >= "2019-12-11").to_numpy()
y_all = p.rv30.to_numpy()
rows = []
for scorelab, mask, train_opts in (("cal dates", calmask, (("common", common), ("primary", primary))), ("raw dates", rawmask, (("primary", primary),))):
    for tname, train in train_opts:
        h = forecasts(HAR, train, mask); hi = forecasts(HAR + [IV], train, mask)
        ok = mask & np.isfinite(h["logf"]) & np.isfinite(hi["logf"])
        y = y_all[ok]; pos = pos_all[ok]; lh = h["logf"][ok]; lhi = hi["logf"][ok]
        ly = np.log(y)
        dl = (ly - lhi) ** 2 - (ly - lh) ** 2
        cw = -dl + (lhi - lh) ** 2
        m, t, lo, hi_ = boot(cw, pos); _, t63, lo63, _ = boot(cw, pos, 63)
        ml, tl, lol, hil = boot(dl, pos); _, tl63, lol63, hil63 = boot(dl, pos, 63)
        print(f"{scorelab} train={tname} n={ok.sum()} logloss HAR {((ly-lh)**2).mean():.4f} HAR+IV {((ly-lhi)**2).mean():.4f} d {ml:.4f} t21 {tl:.2f} [{lol:.3f},{hil:.3f}] t63 {tl63:.2f} [{lol63:.3f},{hil63:.3f}] OOS R2 gain {-ml/((ly-ly.mean())**2).mean():.3f} | CW {m:.4f} t21 {t:.2f} t63 {t63:.2f}")
        # QLIKE under own-scale optimum (hindsight scale, ranks the shape only).
        for lab, fh, fhi in (("no smear", np.exp(lh), np.exp(lhi)),):
            ch, chi = (y / fh).mean(), (y / fhi).mean()
            q = fc.qlike(y, chi * fhi) - fc.qlike(y, ch * fh)
            print(f"   hindsight scale c_har {ch:.3f} c_hi {chi:.3f} q_har {fc.qlike(y, ch*fh).mean():.4f} q_hi {fc.qlike(y, chi*fhi).mean():.4f} d,t,lo,hi {np.round(boot(q, pos), 4)}")
        for sm in ("duan", "win99", "win975", "gauss", "nopaso"):
            fh = np.exp(lh) * h[sm][ok]; fhi = np.exp(lhi) * hi[sm][ok]
            d = fc.qlike(y, fhi) - fc.qlike(y, fh)
            print(f"   smear={sm:7s} median factor HAR {np.median(h[sm][ok]):.3f} HAR+IV {np.median(hi[sm][ok]):.3f} mean f {fh.mean():.3f}/{fhi.mean():.3f} y {y.mean():.3f} q_har {fc.qlike(y, fh).mean():.4f} q_hi {fc.qlike(y, fhi).mean():.4f} d,t,lo,hi {np.round(boot(d, pos), 4)}")
        fh = np.exp(lh); fhi = np.exp(lhi)
        d = fc.qlike(y, fhi) - fc.qlike(y, fh)
        print(f"   smear=none    mean f {fh.mean():.3f}/{fhi.mean():.3f} q_har {fc.qlike(y, fh).mean():.4f} q_hi {fc.qlike(y, fhi).mean():.4f} d,t,lo,hi {np.round(boot(d, pos), 4)}")
        yrs = p.session_date.dt.year.to_numpy()[ok]
        for lab, sel in (("2019-2023", yrs <= 2023), ("2024-2025", (yrs >= 2024) & (yrs <= 2025)), ("2026", yrs == 2026)):
            dd = dl[sel]; po = pos[sel]
            print(f"   period {lab} n={sel.sum()} dlog {np.round(boot(dd, po), 4)} CW t {boot(cw[sel], po)[1]:.2f} dq none {np.round(boot(d[sel], po), 4)} mean f none {fh[sel].mean():.3f}/{fhi[sel].mean():.3f} y {y[sel].mean():.3f}")
print("done5")
