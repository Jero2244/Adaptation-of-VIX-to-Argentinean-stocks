"""Audit step 6: small read-only checks. Frozen-file state, post-break detail, quote width, MF30 inputs, PDF text."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
pd.set_option("display.width", 250, "display.max_columns", 60, "display.max_rows", 300)
HERE = Path(__file__).resolve().parent

import freeze  # noqa: E402

print("=== frozen files changed since the manifest:", freeze.differences())

pb = pd.read_csv(HERE / "a03_postbreak.csv")
print("\n=== post-break days where the strict last-row rule changes ATM30 by more than 1%, or loses the day")
print(pb[(pb.rel_strict.abs() > 0.01) | (pb.stored.notna() & pb.mine_strict_rule.isna())][["day", "stored", "mine_strict_rule", "rel_strict", "revived_bids", "why_strict"]].to_string())
print("largest |mine - stored| under the study rule:\n", pb.assign(a=pb.diff_study.abs()).nlargest(3, "a")[["day", "stored", "mine_study_rule", "diff_study"]].to_string())

s = pd.read_parquet(ROOT / "data" / "index_series.parquet")
p = pd.read_parquet(ROOT / "data" / "forecast_panel.parquet")
ok = s[s.atm30.notna()]
print("\n=== quote width at the strikes that set ATM30 (worst of the two terms): share of valid days above each level")
for cut in (0.25, 0.5, 0.75, 1.0):
    print(f"  relative spread > {cut}: {(ok.relative_spread > cut).mean():.3f}")
print("  by period: median relative spread before 2025-03 %.3f, from 2025-04 %.3f" % (ok[ok.session_date < "2025-03-01"].relative_spread.median(), ok[ok.session_date >= "2025-04-01"].relative_spread.median()))
print("  monthly median 2024-10..2025-09:\n", ok[(ok.session_date >= "2024-10-01") & (ok.session_date < "2025-10-01")].groupby(ok.session_date.dt.strftime("%Y-%m"))["relative_spread"].median().round(3).to_string())

snap = pd.read_parquet(ROOT / "data" / "option_snapshot_1545.parquet")
snap["session_date"] = snap["session_date"].astype("datetime64[ns]")
snap["post"] = snap.session_date >= "2025-03-01"
print("\n=== snapshot table: bid status by period")
print(snap.groupby("post").apply(lambda f: pd.Series(dict(rows=len(f), bid_zero=(f.bid == 0).mean(), bid_nan=f.bid.isna().mean(), ask_nan=f.ask.isna().mean(), crossed=(f.bid > f.ask).mean(), locked=((f.bid == f.ask) & (f.bid > 0)).mean(), age_gt30=(f.age > 30).mean())), include_groups=False).round(4).to_string())
two = snap[(snap.bid > 0) & (snap.ask >= snap.bid)]
print("two-sided quotes: median (ask-bid)/mid by year:\n", two.assign(rs=(two.ask - two.bid) / ((two.ask + two.bid) / 2)).groupby(two.session_date.dt.year)["rs"].median().round(3).to_string())

print("\n=== MF30: wing quotes that fed it, and extrapolated share")
m = s[s.mf30.notna()]
print(m.groupby("year").agg(n=("mf30", "size"), extrap_med=("mf_extrapolated_share", "median"), extrap_p90=("mf_extrapolated_share", lambda x: x.quantile(.9))).round(3).to_string())

print("\n=== primary rows by flag")
pr = p[p.primary]
for f in ("flag_front_under_7d", "flag_ex_in_front", "flag_rights_in_bracket", "flag_option_degraded"):
    print(f"  {f}: {int(pr[f].sum())} of {len(pr)}")
print("  tier 2:", int((pr.tier == 2).sum()), " far_days>65:", int((pr.far_days > 65).sum()))

print("\n=== PDF text spot check")
try:
    from pypdf import PdfReader
    for name in ("GGAL_study_technical_final.pdf", "GGAL_study_plain_final.pdf", "GGAL_calibration_technical.pdf", "GGAL_calibration_plain.pdf"):
        reader = PdfReader(str(ROOT / "writeup" / name))
        text = " ".join(page.extract_text() or "" for page in reader.pages)
        print(f"  {name}: {len(reader.pages)} pages, {len(text)} chars; has 'VIX': {'VIX' in text}; has '.622': {'.622' in text}; has '69.6': {'69.6' in text}; has 'Inconclusive': {'Inconclusive' in text}")
except Exception as error:  # pypdf may be absent
    print("  could not read the PDFs:", type(error).__name__, error)
