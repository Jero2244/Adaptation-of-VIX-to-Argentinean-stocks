import pandas as pd, numpy as np
ROOT = r"C:\Users\HP Laptop\.spyder-py3\2024-1\vix_ggal_adaptation"
p = pd.read_parquet(ROOT + r"\data\forecast_panel.parquet")
print(list(p.columns))
print(len(p), p.session_date.min().date(), p.session_date.max().date())
print((p.position.diff().dropna()==1).all())
print("first primary pos", p.position[p.primary].min(), p.session_date[p.primary].min().date())
print("non-null rows", p[["log_rv1","log_rv5","log_rv22","log_iv2","rv30","window_end"]].notna().sum().to_dict())
har = p[["log_rv1","log_rv5","log_rv22","rv30"]].notna().all(axis=1)
print("har valid", har.sum(), "primary", p.primary.sum())
g = p[p.session_date<"2025-03-01"].assign(y=lambda d:d.session_date.dt.year, iv=lambda d:d.log_iv2.notna(), full=lambda d:d.primary)
print(g.groupby("y")[["iv","full"]].mean().round(3))
print(g[g.y.isin([2018,2019])].groupby(g.session_date.dt.to_period("Q"))[["iv","full"]].mean().round(3))
print(p[p.primary].session_date.iloc[:3].dt.date.tolist(), p[p.primary][['session_date','window_end']].tail(2))
