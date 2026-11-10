"""Exact draft section C and D rules on a 28-month frame. Exploratory. Reads no locked data."""
import sys
import numpy as np
import pandas as pd
ROOT = r"C:\Users\HP Laptop\.spyder-py3\2024-1\vix_ggal_adaptation"
sys.path.insert(0, ROOT)
import forecasts as fc
import inference as inf
HAR = ["log_rv1", "log_rv5", "log_rv22"]
IV = "log_iv2"
FULL = HAR + [IV]
CALC = ["position", "session_date", "window_end", "rv30", "log_rv30", "log_iv2"] + HAR


def design(f, names):
    return np.column_stack([np.ones(len(f))] + [f[n].to_numpy(float) for n in names])


def apply_rules(w, reps=2000, seed=20261104, strict_end=None, har_train_all=True, block63=False):
    """w is a session-grid frame. Position resets to 0. HAR inputs are blank before position 22 (warm-up)."""
    w = w.reset_index(drop=True).copy()
    w["position"] = np.arange(len(w))
    w.loc[w.position < 22, HAR] = np.nan
    if strict_end is not None:
        late = w.window_end > strict_end
        w.loc[late, ["rv30", "log_rv30"]] = np.nan
    prim = w[[IV, "log_rv30"] + HAR].notna().all(axis=1).to_numpy()
    harv = w[["log_rv30"] + HAR].notna().all(axis=1).to_numpy()
    out = dict(sessions=len(w), origins=int(prim.sum()))
    s = w[prim]
    X = design(s, FULL)
    y = s.log_rv30.to_numpy(float)
    pos = s.position.to_numpy()
    b = np.linalg.lstsq(X, y, rcond=None)[0][4]

    def boot(idx):
        return np.array([np.linalg.lstsq(X[idx], y[idx], rcond=None)[0][4]])

    d = inf.block_bootstrap(boot, pos, 21, reps, seed)[:, 0]
    lo, hi = np.percentile(d, [2.5, 97.5])
    out.update(b=b, lo=lo, hi=hi, se=d.std(ddof=1))
    if block63:
        d63 = inf.block_bootstrap(boot, pos, 63, reps, seed + 63)[:, 0]
        out.update(lo63=np.percentile(d63, 2.5), hi63=np.percentile(d63, 97.5))
    # Fixed-step samples. Draft text: pooled over steps 22 and 23.
    first = int(np.flatnonzero(prim)[0])
    rows = []
    for step in (22, 23):
        for off in range(step):
            q = np.arange(first + off, len(w), step)
            q = q[prim[q]]
            c = w.iloc[q]
            if len(c) < 7:
                rows.append((step, len(c), np.nan, np.nan))
                continue
            r = inf.ols(c.log_rv30.to_numpy(float), design(c, FULL))
            rows.append((step, len(c), r["beta"][4], r["beta"][4] / r["classical_se"][4]))
    fs = pd.DataFrame(rows, columns=["step", "n", "b", "t"])
    out.update(fs_mean=fs.b.mean(), fs_medt=fs.t.median(), fs_n=fs.n.median(), fs_nmin=fs.n.min(),
               fs_mean22=fs.b[fs.step == 22].mean(), fs_medt22=fs.t[fs.step == 22].median(),
               fs_mean23=fs.b[fs.step == 23].mean(), fs_medt23=fs.t[fs.step == 23].median())
    # Rules 2 and 3. Rows: primary, position >= 252. Training: longest available for each model.
    score = prim & (w.position.to_numpy() >= 252)
    tr_h = harv if har_train_all else prim
    fh = fc.expanding_forecasts(w, HAR, tr_h, score, smearing=False)
    ff = fc.expanding_forecasts(w, FULL, prim, score, smearing=False)
    gh = fc.expanding_forecasts(w, HAR, tr_h, score, smearing=True)
    gf = fc.expanding_forecasts(w, FULL, prim, score, smearing=True)
    m = np.isfinite(fh) & np.isfinite(ff) & np.isfinite(gh) & np.isfinite(gf)
    out["scored"] = int(m.sum())
    if m.sum() < 42:
        out.update(cw=np.nan, cw_t=np.nan, q_duan=np.nan, q_duan_hi=np.nan, q_none=np.nan, q_none_hi=np.nan)
    else:
        sp = w.position.to_numpy()[m]
        yt = w.rv30.to_numpy(float)[m]
        ly = np.log(yt)
        a, c = np.log(fh[m]), np.log(ff[m])
        cw = (ly - a) ** 2 - ((ly - c) ** 2 - (a - c) ** 2)

        def mean_boot(v, sd):
            dr = inf.block_bootstrap(lambda i: np.array([v[i].mean()]), sp, 21, reps, sd)[:, 0]
            return v.mean(), v.mean() / dr.std(ddof=1), np.percentile(dr, 97.5)

        mc, tc, _ = mean_boot(cw, seed + 1)
        qd = fc.qlike(yt, gf[m]) - fc.qlike(yt, gh[m])
        qn = fc.qlike(yt, ff[m]) - fc.qlike(yt, fh[m])
        md, _, hd = mean_boot(qd, seed + 2)
        mn, _, hn = mean_boot(qn, seed + 3)
        out.update(cw=mc, cw_t=tc, q_duan=md, q_duan_hi=hd, q_none=mn, q_none_hi=hn, logmse=np.mean((ly - c) ** 2 - (ly - a) ** 2))
    return verdict(out)


def verdict(o):
    o["r1a"] = bool(o["b"] > 0 and o["lo"] > 0)
    o["r1b"] = bool(o["fs_mean"] > 0 and o["fs_medt"] > 1.65)
    o["r1b_strict"] = bool(o["fs_mean22"] > 0 and o["fs_mean23"] > 0 and o["fs_medt22"] > 1.65 and o["fs_medt23"] > 1.65)
    o["r1"] = o["r1a"] and o["r1b"]
    ok = np.isfinite(o["cw_t"])
    o["r2"] = bool(o["cw_t"] > 1.65) if ok else False
    o["r3"] = bool(o["q_duan"] < 0 and o["q_duan_hi"] < 0 and o["q_none"] < 0 and o["q_none_hi"] < 0) if ok else False
    o["floor"] = bool(o["origins"] >= 300 and o["fs_n"] >= 20)
    o["sup"] = o["r1"] and o["r2"]
    o["notsup"] = bool(o["b"] <= 0 or o["hi"] < .25)
    o["both"] = o["sup"] and o["notsup"]
    if not o["floor"]:
        o["outcome"] = "Inconclusive (floor)"
    elif o["sup"] and o["r3"]:
        o["outcome"] = "Supported, usable gain"
    elif o["sup"]:
        o["outcome"] = "Supported"
    elif o["notsup"]:
        o["outcome"] = "Not supported"
    else:
        o["outcome"] = "Inconclusive"
    return o
