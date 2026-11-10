"""Fix steps 2 and 3 (F2-F4, F7-F9): fit the primary regression on each variant series. DEVELOPMENT work on open data.

Reads fixes/data/series_NAME.parquet written by f03_variants.py. The regression is the study's own: log RV30 on HAR (log RV1, RV5, RV22) and log ATM30^2,
Newey-West(21) t, circular block bootstrap with 2000 resamples and seed SEED + block (blocks 21 and 63), the same code (inference.py) and the same
session-grid positions. Writes f04_variants.csv, f04_days_by_year.csv, f04_variants.out.
Also reports b of the STORED series on the same origins (columns b_stored_same_rows), to separate the method effect from the sample effect.
"""
import sys
from multiprocessing import Pool

from common import *  # noqa

# (label, series name, column)
JOBS = [
    ("stored baseline", "base", "atm30"),
    ("F9 min near term 7d", "base", "atm30_floor7"),
    ("F7 strict last row", "strict", "atm30"),
    ("F3 spread <= .50", "spread50", "atm30"),
    ("F3 spread <= .25 (sens.)", "spread25", "atm30"),
    ("F3 spread <= 1.00 (sens.)", "spread100", "atm30"),
    ("F4 Tier 1 only", "tier1", "atm30"),
    ("COMBINED strict+spread.50+Tier1", "core", "atm30"),
    ("COMBINED + 7d floor (all four)", "core", "atm30_floor7"),
    ("all four, spread .25 (sens.)", "core25", "atm30_floor7"),
    ("all four, spread 1.00 (sens.)", "core100", "atm30_floor7"),
    ("F2 American tree, all dividends", "deam", "atm30"),
    ("F2 American tree, confirmed only", "deamC", "atm30"),
    ("all four + American tree", "core_deam", "atm30_floor7"),
]
REAL = None
BASE = None


def init():
    global REAL, BASE
    REAL = rz.build_realized()
    BASE = pd.read_parquet(FDATA / "series_base.parquet")


def job(args):
    label, name, col = args
    ser = pd.read_parquet(FDATA / f"series_{name}.parquet")
    panel = make_panel(ser, REAL, col)
    p = panel[panel.primary]
    res = fit_b(p)
    # stored series on the same origins
    pb = make_panel(BASE, REAL, "atm30")
    pb = pb[pb.session_date.isin(p.session_date)]
    same = fit_b(pb, reps=0)
    both = pd.DataFrame(dict(a=ser.set_index("session_date")[col], b=BASE.set_index("session_date")["atm30"])).dropna()
    lr = np.log(both.a / both.b)
    row = dict(variant=label, series=name, column=col, valid_days=int(ser[col].notna().sum()), primary_origins=res["n"], b=res["b"], nw_t=res["nw_t"], r2=res["r2"],
               boot21_t=res.get("boot21_t"), boot21_low=res.get("boot21_low"), boot21_high=res.get("boot21_high"),
               boot63_t=res.get("boot63_t"), boot63_low=res.get("boot63_low"), boot63_high=res.get("boot63_high"),
               b_stored_same_rows=same["b"], nw_t_stored_same_rows=same["nw_t"], common_days=len(both),
               level_mean_log_change=float(lr.mean()), level_median_log_change=float(lr.median()), level_mean_abs_log_change=float(lr.abs().mean()))
    return row, ser.assign(variant=label)[["session_date", col, "variant"]].rename(columns={col: "v"})


if __name__ == "__main__":
    print(LABEL)
    jobs = [j for j in JOBS if (FDATA / f"series_{j[1]}.parquet").exists()]
    skipped = [j[0] for j in JOBS if j not in jobs]
    if skipped:
        print("SKIPPED (series file missing):", skipped)
    with Pool(4, initializer=init) as pool:
        results = pool.map(job, jobs)
    table = pd.DataFrame([r for r, _ in results])
    table.to_csv(HERE / "f04_variants.csv", index=False)
    pd.set_option("display.float_format", lambda x: f"{x:.3f}")
    print(table[["variant", "valid_days", "primary_origins", "b", "nw_t", "boot21_low", "boot21_high", "boot63_low", "boot63_high", "r2"]].to_string(index=False))
    print("\nSample effect: b of the STORED series on the same origins, and the level change of the variant against the stored series (common days)")
    print(table[["variant", "primary_origins", "b", "b_stored_same_rows", "nw_t_stored_same_rows", "common_days", "level_mean_log_change", "level_median_log_change", "level_mean_abs_log_change"]].to_string(index=False))
    # days by year
    long = pd.concat([d for _, d in results])
    long["year"] = long.session_date.dt.year
    cnt = long.groupby(["variant", "year"]).v.count().unstack("year")
    base = cnt.loc["stored baseline"]
    removed = (base - cnt).drop(index="stored baseline")
    cnt.to_csv(HERE / "f04_days_by_year.csv")
    removed.to_csv(HERE / "f04_days_removed_by_year.csv")
    print("\nValid ATM30 days by year")
    print(cnt.to_string())
    print("\nDays removed against the stored baseline, by year (negative = gained)")
    print(removed.to_string())
