"""Sanity check of the bbo-1m realized variance (F5). DEVELOPMENT work on open data. Stdout only."""
from common import *  # noqa

if __name__ == "__main__":
    print(LABEL)
    r = pd.read_parquet(FDATA / "realized_hf.parquet")
    r = r.dropna(subset=["rv_hf_day", "return_total"])
    r["sq"] = r.return_total ** 2
    r["year"] = r.session_date.dt.year
    print("sessions", len(r), " total RVhf / total squared close-to-close return = %.3f" % (r.rv_hf_day.sum() / r.sq.sum()))
    g = r.groupby("year").apply(lambda f: pd.Series(dict(sum_ratio=f.rv_hf_day.sum() / f.sq.sum(), median_rvhf_vol=np.sqrt(252 * f.rv_hf_day.median()), median_sq_vol=np.sqrt(252 * f.sq.median()))), include_groups=False)
    print(g.round(3).to_string())
    ov = (r.return_overnight ** 2).sum() / r.rv_hf_day.sum()
    print("share of RVhf from the overnight piece: %.3f" % ov)
    print("corr(log RVhf, log squared return, floor 1e-8) = %.3f ; lag-1 autocorrelation of log RVhf %.3f vs of log squared return %.3f" % (
        np.corrcoef(np.log(r.rv_hf_day), np.log(r.sq.clip(lower=1e-8)))[0, 1], r.rv_hf_day.pipe(np.log).autocorr(), r.sq.clip(lower=1e-8).pipe(np.log).autocorr()))
