"""F6 (reporting only): b by period for the stored series and the fixed series. DEVELOPMENT work on open data.

OLS with Newey-West(21) t only, no bootstrap. Event windows are not removed here (the study's event list is in events.py; not used). Fragility is a property of the data.
"""
from common import *  # noqa

PERIODS = {"2018-2023": ("2018-05-01", "2023-12-31"), "2024-2025": ("2024-01-01", "2025-12-31"), "2026": ("2026-01-01", "2026-12-31"),
           "before 2025-03": ("2018-05-01", "2025-02-28"), "from 2025-03": ("2025-03-01", "2026-12-31")}

if __name__ == "__main__":
    print(LABEL)
    real = rz.build_realized()
    hf = pd.read_parquet(FDATA / "realized_hf.parquet")
    rows = []
    for label, name, col, R, har in (("stored ATM30, HAR old", "base", "atm30", real, HAR), ("all four fixes, HAR old", "core", "atm30_floor7", real, HAR),
                                     ("all four + tree, HAR old", "core_deam", "atm30_floor7", real, HAR), ("stored ATM30, HAR new (bbo-1m)", "base", "atm30", hf, ["hf_rv1", "hf_rv5", "hf_rv22"]),
                                     ("tree (all dividends), HAR old", "deam", "atm30", real, HAR)):
        panel = make_panel(pd.read_parquet(FDATA / f"series_{name}.parquet"), R, col)
        p = panel[panel.primary]
        for per, (a, b) in PERIODS.items():
            s = p[p.session_date.between(a, b)]
            if len(s) < 40:
                rows.append(dict(series=label, period=per, n=len(s)))
                continue
            f = fit_b(s, names=har + [IV], reps=0)
            rows.append(dict(series=label, period=per, n=len(s), b=f["b"], nw_t=f["nw_t"], r2=f["r2"]))
        f = fit_b(p, names=har + [IV], reps=0)
        rows.append(dict(series=label, period="all", n=len(p), b=f["b"], nw_t=f["nw_t"], r2=f["r2"]))
    t = pd.DataFrame(rows)
    t.to_csv(HERE / "f15_subsamples.csv", index=False)
    pd.set_option("display.float_format", lambda x: f"{x:.3f}")
    print(t.to_string(index=False))
