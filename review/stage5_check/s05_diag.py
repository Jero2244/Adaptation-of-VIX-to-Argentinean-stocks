"""Open diagnostics by year, to see trends that approach the locked boundary. Open dates only."""
import _common
from _common import ROOT
import pandas as pd
d = pd.read_parquet(ROOT/"data/session_diagnostics.parquet")
s = pd.read_parquet(ROOT/"data/index_series.parquet")
d["year"] = d.session_date.dt.year
print(d.groupby("year").agg(n=("cbbo_rows","size"), rows=("cbbo_rows","median"), inst=("cbbo_instruments","median"), defs=("definitions","median"), other=("other_roots","sum"), unmatched=("unmatched_quotes","sum"), flag=("flag_mode","median"), null_bid=("null_bid_share","median"), empty=("cbbo_rows", lambda x:(x==0).sum())).round(3).to_string())
print(s.groupby("year").agg(n=("atm30","size"), atm=("atm30","count"), t1=("tier",lambda x:(x==1).sum()), near=("near_days","median"), age=("quote_age","median")).round(2).to_string())
e = d[d.session_date<"2018-09-01"]
print(e.head(5)[["session_date","first_bar","last_bar","cbbo_rows","definitions","flag_mode"]].to_string())
print(s[s.session_date<"2018-08-01"].groupby(s.session_date.dt.to_period("M")).agg(n=("atm30","size"),atm=("atm30","count")).to_string())
print(s[s.atm30.isna()].groupby("status").size().sort_values(ascending=False).head(10).to_string())
print("listed bracket share", s.listed_bracket.mean())
print("last bars on half days", d[d.last_bar<"15:45"][["session_date","last_bar"]].head(8).to_string())
