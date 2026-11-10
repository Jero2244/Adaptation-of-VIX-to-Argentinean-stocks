"""Audit step 7: does the level of ATM30 depend on quote quality? Read-only, from data/forecast_panel.parquet."""
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parent.parent
pd.set_option("display.width", 250, "display.max_columns", 60, "display.max_rows", 300)
p = pd.read_parquet(ROOT / "data" / "forecast_panel.parquet")
s = p[p.primary].copy()
s["ratio"] = s.atm30 / np.sqrt(s.rv30)
s["lr"] = np.log(s.ratio)
s["iv_band_half"] = s.relative_spread / 2  # near the money, d(IV)/IV is about d(price)/price, so half the relative spread is the half-width of the bid-ask IV band
print("By year: n, median ATM30, median realized vol, median ATM30/RV vol, share tier 2, median half-width of the bid-ask IV band (worst term)")
print(s.groupby("year").agg(n=("atm30", "size"), atm=("atm30", "median"), rv=("rv30", lambda x: np.sqrt(x).median()), ratio=("ratio", "median"), tier2=("tier", lambda x: (x == 2).mean()), band=("iv_band_half", "median")).round(3).to_string())
print("\nBy tier: median ATM30/RV vol:", s.groupby("tier")["ratio"].median().round(3).to_dict())
print("By spread tercile (pooled): median ATM30/RV vol:", s.groupby(pd.qcut(s.relative_spread, 3, labels=["low", "mid", "high"]), observed=True)["ratio"].median().round(3).to_dict())
s["sp_t"] = s.groupby("year")["relative_spread"].transform(lambda x: pd.qcut(x, 3, labels=False, duplicates="drop"))
print("By spread tercile within year: median ATM30/RV vol:", s.groupby("sp_t")["ratio"].median().round(3).to_dict())
X = sm.add_constant(pd.concat([s[["relative_spread"]], (s.tier == 2).astype(float).rename("tier2"), pd.get_dummies(s.year, prefix="y", drop_first=True, dtype=float)], axis=1))
m = sm.OLS(s.lr, X).fit(cov_type="HAC", cov_kwds=dict(maxlags=21))
print("\nlog(ATM30 / realized vol) on relative_spread and tier2, year dummies, HAC(21):")
print(m.summary2().tables[1].loc[["relative_spread", "tier2"]].round(3).to_string())
X2 = sm.add_constant(pd.concat([s[["relative_spread"]], (s.tier == 2).astype(float).rename("tier2"), pd.get_dummies(s.year, prefix="y", drop_first=True, dtype=float)], axis=1))
m2 = sm.OLS(s.log_iv2, X2).fit(cov_type="HAC", cov_kwds=dict(maxlags=21))
print("log(ATM30^2) on the same:")
print(m2.summary2().tables[1].loc[["relative_spread", "tier2"]].round(3).to_string())
print("\nhalf-width of the bid-ask IV band, all primary rows: median %.3f, p75 %.3f, p90 %.3f ; daily sd of log ATM30 change is about 0.073" % (s.iv_band_half.median(), s.iv_band_half.quantile(.75), s.iv_band_half.quantile(.9)))
print("near strike price level: share of primary rows with near_forward < 12 (strikes 2.5 apart => gaps above 20%%): %.3f" % (s.near_forward < 12).mean())
