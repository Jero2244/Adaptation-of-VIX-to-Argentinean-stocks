"""Race grid: training start x smearing, nested-model tests, log loss. Read-only on the project."""
import sys
PROJECT = r"C:\Users\HP Laptop\.spyder-py3\2024-1\vix_ggal_adaptation"
sys.path.insert(0, PROJECT)
import numpy as np, pandas as pd
import forecasts as fc, inference as inf

p = pd.read_parquet(PROJECT + r"\data\forecast_panel.parquet")
print(len(p), p.session_date.min(), p.session_date.max())
HAR = ["log_rv1", "log_rv5", "log_rv22"]; IV = "log_iv2"
primary = p["primary"].to_numpy()
common = primary & p["log_garch"].notna().to_numpy() & p["log_garch_t"].notna().to_numpy() & p["log_ewma"].notna().to_numpy()
print("primary rows", primary.sum(), "common rows", common.sum(), "first common", p.session_date[common].min())


def boot(d, pos, block=21, reps=2000, seed=1):
    d = np.asarray(d)
    draws = inf.block_bootstrap(lambda i: np.array([d[i].mean()]), pos, block, reps, seed)
    return d.mean(), d.mean() / draws.std(ddof=1), np.percentile(draws, 2.5), np.percentile(draws, 97.5)


def gridrow(label, score_mask):
    pos = p["position"].to_numpy()[score_mask]
    y = p["rv30"].to_numpy()[score_mask]
    rows = []
    for tname, train in (("train=primary(2018-06 on)", primary), ("train=common(2019-05 on)", common)):
        for smear in (True, False):
            h = fc.expanding_forecasts(p, HAR, train, score_mask, smearing=smear)[score_mask]
            hi = fc.expanding_forecasts(p, HAR + [IV], train, score_mask, smearing=smear)[score_mask]
            a = fc.expanding_forecasts(p, [IV], train, score_mask, smearing=smear)[score_mask]
            ok = np.isfinite(h) & np.isfinite(hi) & np.isfinite(a)
            d = fc.qlike(y[ok], hi[ok]) - fc.qlike(y[ok], h[ok])
            m, t, lo, hi_ = boot(d, pos[ok], 21)
            _, t63, lo63, hi63 = boot(d, pos[ok], 63)
            # log loss
            dl = (np.log(y[ok]) - np.log(hi[ok])) ** 2 - (np.log(y[ok]) - np.log(h[ok])) ** 2
            ml, tl, lol, hil = boot(dl, pos[ok], 21)
            _, tl63, _, _ = boot(dl, pos[ok], 63)
            # Clark-West adjustment, log loss, nested HAR vs HAR+IV
            cw = dl + (np.log(hi[ok]) - np.log(h[ok])) ** 2
            mc, tc, loc, hic = boot(cw, pos[ok], 21)
            _, tc63, _, _ = boot(cw, pos[ok], 63)
            # Clark-West adjustment on QLIKE by the same logic is not standard. Report level bias too.
            rows.append(dict(score=label, train=tname, smear=smear, n=int(ok.sum()), first=p.session_date[score_mask][ok].min().date(),
                             q_har=fc.qlike(y[ok], h[ok]).mean(), q_hi=fc.qlike(y[ok], hi[ok]).mean(), q_atm=fc.qlike(y[ok], a[ok]).mean(),
                             dq=m, dq_t21=t, dq_lo=lo, dq_hi=hi_, dq_t63=t63, mean_f_har=h[ok].mean(), mean_f_hi=hi[ok].mean(), mean_y=y[ok].mean(),
                             dlog=ml, dlog_t21=tl, dlog_t63=tl63, cw=mc, cw_t21=tc, cw_t63=tc63))
    return rows


rows = []
rawmask = primary & (p["position"].to_numpy() >= 252)
rows += gridrow("raw dates (2019-05 on, PASO scored)", rawmask)
rows += gridrow("calibrated dates (2019-12 on)", common & (p.session_date >= "2019-12-11").to_numpy())
g = pd.DataFrame(rows)
pd.set_option("display.width", 250, "display.max_columns", 50)
print(g.round(4).to_string())
g.to_csv(sys.argv[0].replace(".py", ".csv"), index=False)

# ATM30 raw against no-smearing HAR, on raw dates and calibrated dates.
for label, mask in (("raw dates", rawmask), ("cal dates", common & (p.session_date >= "2019-12-11").to_numpy())):
    y = p["rv30"].to_numpy()[mask]; pos = p["position"].to_numpy()[mask]
    atm = p["f_atm_raw"].to_numpy()[mask]
    for smear in (True, False):
        h = fc.expanding_forecasts(p, HAR, primary, mask, smearing=smear)[mask]
        ok = np.isfinite(h)
        print(label, "ATM raw - HAR smear", smear, boot(fc.qlike(y[ok], atm[ok]) - fc.qlike(y[ok], h[ok]), pos[ok]))

# Smearing factor path in the calibrated race and in the primary training set.
dates = p.session_date.to_numpy(); we = p.window_end.to_numpy(); tgt = np.log(p.rv30.to_numpy())
for names, lab in ((HAR, "HAR"), (HAR + [IV], "HAR+IV")):
    X = np.column_stack([np.ones(len(p))] + [p[n].to_numpy(dtype=float) for n in names])
    for train, tl in ((common, "common"), (primary, "primary")):
        for d in ("2019-12-11", "2020-06-01", "2021-01-04", "2022-01-03", "2024-01-02", "2026-01-02"):
            o = np.searchsorted(dates, np.datetime64(d))
            t = train & (we <= dates[o]) & (np.arange(len(p)) < o)
            b, s = fc.fit_log_ols(X[t], tgt[t])
            # smear without PASO target windows in the factor only
            nop = t & ~((dates < np.datetime64("2019-08-12")) & (we >= np.datetime64("2019-08-12")))
            s2 = float(np.mean(np.exp(tgt[nop] - X[nop] @ b)))
            print(lab, tl, d, "rows", int(t.sum()), "smear", round(s, 3), "smear no PASO rows", round(s2, 3))

# Share of the smear from PASO windows and median of residual. Gaussian alternative.
# QLIKE race with a smear that omits nothing: Gaussian exp(s2/2) as alternative rule, known before results?
