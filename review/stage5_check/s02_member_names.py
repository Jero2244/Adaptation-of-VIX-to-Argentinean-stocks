"""ZIP member NAMES only, for 2016-01 to 2018-04. No member is read, no size is read. Compares day sets against the NYSE calendar."""
import _common, re, zipfile
from _common import ROOT
import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar
HOL = pd.to_datetime(["2016-01-01","2016-01-18","2016-02-15","2016-03-25","2016-05-30","2016-07-04","2016-09-05","2016-11-24","2016-12-26",
 "2017-01-02","2017-01-16","2017-02-20","2017-04-14","2017-05-29","2017-07-04","2017-09-04","2017-11-23","2017-12-25",
 "2018-01-01","2018-01-15","2018-02-19","2018-03-30"])
NYSE = pd.bdate_range("2016-01-01","2018-04-30").difference(HOL)
print("NYSE sessions by hand-listed holidays:", len(NYSE))
rx = re.compile(r"-[a-z]+-(\d{8})\.[a-z0-9-]+\.dbn\.zst$")
A = ROOT/"databento_ggal_20261031"
sets = {}
for label, path in [("cbbo", A/"options/OPRA-cbbo_1m.zip"), ("def", A/"options/OPRA-Definition.zip")]:
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
    days = []
    other = []
    for n in names:
        m = rx.search(n)
        if m: days.append(pd.Timestamp(m[1]))
        else: other.append(n)
    days = pd.DatetimeIndex(days)
    print(label, "members", len(names), "non-day members", other, "dup days", int(days.duplicated().sum()), "first", days.min().date(), "last", days.max().date())
    locked = days[(days>="2016-01-01")&(days<="2018-04-30")]
    sets[label] = locked
    print(" locked days", len(locked), "weekend", int((locked.dayofweek>=5).sum()), "not NYSE", [str(d.date()) for d in locked.difference(NYSE)], "NYSE not in zip", [str(d.date()) for d in NYSE.difference(locked)])
    prefixes = {re.sub(r"\d{8}","<d>",n) for n in names if rx.search(n)}
    print(" name patterns", prefixes)
print("cbbo minus def", [str(d.date()) for d in sets["cbbo"].difference(sets["def"])], "def minus cbbo", [str(d.date()) for d in sets["def"].difference(sets["cbbo"])])
for f in ["XNAS-bbo.zip","XNAS-ohlc.zip","XNAS-statistics.zip"]:
    with zipfile.ZipFile(A/"equity"/f) as z:
        names=[n for n in z.namelist() if rx.search(n) or n.endswith("zst")]
    print(f, len(names), sorted(names)[:1], sorted(names)[-1:])
