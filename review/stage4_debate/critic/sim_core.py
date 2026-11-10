"""Critic round 1: shared simulation of the draft Stage 4 rules. Reads data/forecast_panel.parquet only. Exploratory."""
import sys, time
import numpy as np, pandas as pd
ROOT = r"C:\Users\HP Laptop\.spyder-py3\2024-1\vix_ggal_adaptation"
sys.path.insert(0, ROOT)
import inference as inf

HAR = ["log_rv1", "log_rv5", "log_rv22"]; IV = "log_iv2"
L_GRID = 542      # 585 sessions, less 21 with no full window at the end, less 22 for HAR inputs.
SCORE_START = 230 # Position 252 on the study grid = 230 on this grid (22 burn-in).
GAP = 21          # Training row needs window end <= origin: about 21 sessions.
MIN_TRAIN = 126
TARGETS = (0.0, 0.25, 0.37, 0.62)


def load_pool(kind):
    p = pd.read_parquet(ROOT + r"\data\forecast_panel.parquet", columns=["position", "session_date", "window_end", "primary", "log_rv30", "rv30", "tier", "year"] + HAR + [IV])
    g = p[p.session_date < "2025-03-01"].iloc[22:].reset_index(drop=True)
    if kind == "no2019paso":
        cut = (g.session_date >= "2019-07-10") & (g.session_date <= "2019-09-15")
        g = g[~cut].reset_index(drop=True)
    elif kind != "all":
        raise ValueError(kind)
    return g


def arrays(g):
    v = g.primary.to_numpy()
    X = np.column_stack([np.ones(len(g))] + [g[n].to_numpy(float) for n in HAR] + [g[IV].to_numpy(float)])
    y = g.log_rv30.to_numpy(float)
    return v, X, y


def ols_t(X, y):
    inv = np.linalg.pinv(X.T @ X)
    b = inv @ (X.T @ y)
    r = y - X @ b
    s2 = r @ r / max(len(y) - X.shape[1], 1)
    return b[-1], np.sqrt(s2 * inv[-1, -1])


def expanding(gr, X, y, x_iv, start, min_train=MIN_TRAIN):
    """One fit per scored row. Results move linearly with the target b, so one fit serves every target."""
    k_col = X.shape[1] - 1
    Xh = X[:, :k_col]
    out = []
    for r in np.flatnonzero(gr >= start):
        k = np.searchsorted(gr, gr[r] - GAP, side="right")
        if k < min_train:
            continue
        Xt, yt, xt, Xht = X[:k], y[:k], x_iv[:k], Xh[:k]
        bf = np.linalg.lstsq(Xt, yt, rcond=None)[0]
        sol = np.linalg.lstsq(Xht, np.column_stack([yt, xt]), rcond=None)[0]
        bh, gam = sol[:, 0], sol[:, 1]
        out.append((r, X[r] @ bf, Xh[r] @ bh, Xh[r] @ gam, np.mean(np.exp(yt - Xt @ bf)), yt - Xht @ bh, xt - Xht @ gam))
    return out


def boot_index(pos, block, reps, rng):
    return [inf.block_sample(pos, block, rng) for _ in range(reps)]


def mean_boot(d, idx):
    return np.array([d[i].mean() for i in idx])


def race(fits_, idx_, y, x, c):
    if not len(fits_) or idx_ is None:
        return dict(cw_t=np.nan, qd=np.nan, qd_u=np.nan, qn=np.nan, qn_u=np.nan, bias_n=np.nan, bias_d=np.nan)
    r = np.array([f[0] for f in fits_])
    yt = y[r] + c * x[r]
    # Full model: beta(c) = beta(0) + c e_iv, so its forecast moves by c * x, and its residuals do not move.
    ff = np.array([f[1] for f in fits_]) + c * x[r]
    fh = np.array([f[2] + c * f[3] for f in fits_])
    cw = (yt - fh) ** 2 - ((yt - ff) ** 2 - (fh - ff) ** 2)
    cw_t = cw.mean() / mean_boot(cw, idx_).std(ddof=1)
    sf = np.array([f[4] for f in fits_])
    sh = np.array([np.mean(np.exp(f[5] + c * f[6])) for f in fits_])
    rv = np.exp(yt)

    def q(fc):
        ratio = rv / fc
        return ratio - np.log(ratio) - 1
    qd = q(np.exp(ff) * sf) - q(np.exp(fh) * sh)
    qn = q(np.exp(ff)) - q(np.exp(fh))
    return dict(cw_t=cw_t, qd=qd.mean(), qd_u=np.percentile(mean_boot(qd, idx_), 97.5), qn=qn.mean(), qn_u=np.percentile(mean_boot(qn, idx_), 97.5),
                bias_n=np.exp(ff).mean() / rv.mean(), bias_d=(np.exp(ff) * sf).mean() / rv.mean())


def evaluate_rules(X, y, v, gr, reps, rng, base_b, targets, frozen=None):
    """Apply every rule to one sample. X, y hold valid rows. v and gr describe the session grid."""
    x = X[:, -1]
    L = len(v)
    rec = dict(n=len(y))
    b_hat = np.linalg.lstsq(X, y, rcond=None)[0][-1]
    idx = boot_index(gr, 21, reps, rng)
    draws = np.array([np.linalg.lstsq(X[i], y[i], rcond=None)[0][-1] for i in idx])
    rec.update(b0=b_hat, se=draws.std(ddof=1))
    pct = np.percentile(draws, [2.5, 5, 95, 97.5])
    fs_b, fs_se, fs_n = [], [], []
    for step in (22, 23):
        for off in range(step):
            p = np.arange(off, L, step)
            p = p[v[p]]
            if len(p) < 7:
                continue
            rows = np.searchsorted(gr, p)
            b1, s1 = ols_t(X[rows], y[rows])
            fs_b.append(b1); fs_se.append(s1); fs_n.append(len(p))
    fs_b, fs_se, fs_n = map(np.array, (fs_b, fs_se, fs_n))
    rec.update(fs_n_med=np.median(fs_n), fs_n_min=fs_n.min(), fs_n_max=fs_n.max())
    fits = expanding(gr, X, y, x, L - 312 if L >= 312 else 0)
    fits_early = expanding(gr, X, y, x, 0)
    rows = np.array([f[0] for f in fits]) if fits else np.array([], int)
    rows_e = np.array([f[0] for f in fits_early]) if fits_early else np.array([], int)
    rec.update(scored=len(rows), scored_early=len(rows_e), scored_span=(gr[rows[-1]] - gr[rows[0]] + 1) / 21 if len(rows) else 0, scored_span_early=(gr[rows_e[-1]] - gr[rows_e[0]] + 1) / 21 if len(rows_e) else 0)
    idxS = boot_index(gr[rows], 21, reps, rng) if len(rows) > 21 else None
    idxE = boot_index(gr[rows_e], 21, reps, rng) if len(rows_e) > 21 else None
    for bt in targets:
        c = 0.0 if bt is None else bt - base_b
        s = {}
        bh = b_hat + c
        low, l90, u90, high = pct + c
        ts = (fs_b + c) / fs_se
        s.update(b=bh, low=low, high=high, l90=l90, u90=u90, fs_mean=(fs_b + c).mean(), fs_medt=np.median(ts))
        s["r1a"] = bh > 0 and low > 0
        s["r1b"] = s["fs_mean"] > 0 and s["fs_medt"] > 1.65
        m = race(fits, idxS, y, x, c)
        e = race(fits_early, idxE, y, x, c)
        s.update(m)
        s["cw_early"] = e["cw_t"]
        s["r2"] = m["cw_t"] > 1.65
        s["r2_early"] = e["cw_t"] > 1.65
        s["r3d"] = m["qd"] < 0 and m["qd_u"] < 0
        s["r3n"] = m["qn"] < 0 and m["qn_u"] < 0
        s["r3"] = s["r3d"] and s["r3n"]
        s["R1"] = s["r1a"] and s["r1b"]
        s["S"] = s["R1"] and s["r2"]
        s["G"] = s["S"] and s["r3"]
        s["NS_b"] = bh <= 0
        s["NS_u"] = high < 0.25
        s["NS"] = s["NS_b"] or s["NS_u"]
        s["S_and_NS"] = s["S"] and s["NS"]
        s["R1_and_NS"] = s["R1"] and s["NS"]
        if frozen is not None:
            bfz, bhz = frozen
            yt = y + c * x
            f2 = X @ bfz
            f1 = X[:, :-1] @ bhz
            d = (yt - f1) ** 2 - ((yt - f2) ** 2 - (f1 - f2) ** 2)
            s["cw_frozen"] = d.mean() / mean_boot(d, idx).std(ddof=1)
            f2m = f2 + (yt - f2).mean()
            f1m = f1 + (yt - f1).mean()
            dm = (yt - f1m) ** 2 - ((yt - f2m) ** 2 - (f1m - f2m) ** 2)
            s["cw_frozen_dm"] = dm.mean() / mean_boot(dm, idx).std(ddof=1)
        for k, val in s.items():
            rec[f"{bt}|{k}"] = val
    return rec


def one_sim(pool, base_b, block_outer, reps, rng, frozen):
    v0, X0, y0 = pool
    G = len(v0)
    starts = rng.integers(0, G, size=L_GRID // block_outer + 2)
    grid = np.concatenate([(s + np.arange(block_outer)) % G for s in starts])[:L_GRID]
    v = v0[grid]
    gr = np.flatnonzero(v)
    return evaluate_rules(X0[grid][v], y0[grid][v], v, gr, reps, rng, base_b, TARGETS, frozen)


def run(kind, sims, reps, block_outer, seed):
    g = load_pool(kind)
    v, X, y = arrays(g)
    Xv, yv = X[v], y[v]
    base = np.linalg.lstsq(Xv, yv, rcond=None)[0]
    bhz = np.linalg.lstsq(Xv[:, :-1], yv, rcond=None)[0]
    pool = (v, np.nan_to_num(X), np.nan_to_num(y))
    rng = np.random.default_rng(seed)
    t0 = time.time()
    recs = []
    for i in range(sims):
        recs.append(one_sim(pool, base[-1], block_outer, reps, rng, (base, bhz)))
        if (i + 1) % 100 == 0:
            print(kind, block_outer, i + 1, round(time.time() - t0), flush=True)
    return pd.DataFrame(recs), dict(kind=kind, rows=int(v.sum()), grid=len(v), coverage=float(v.mean()), base_b=float(base[-1]))
