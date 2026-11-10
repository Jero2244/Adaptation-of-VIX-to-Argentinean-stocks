"""Stage 4, step 6: fetch the Treasury rates of the one-time test into a separate file.

Run from this folder: conda run -n py4fi python fetch_test_rates.py
The file starts before 2016-01-04, so the first session has a prior observation. It ends at 2018-04-30, so the test never
joins later rates. data/source/fred_rates.csv does not change. Use the default client, as HANDOFF.md says.
"""
from __future__ import annotations

import io
import urllib.request

import pandas as pd

from build_snapshot import FRED_SERIES
from config import SOURCE

TEST_RATES = SOURCE / "fred_rates_test.csv"
URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}&cosd=2015-12-01&coed=2018-04-30"


def main() -> None:
    if TEST_RATES.exists():
        raise SystemExit(f"{TEST_RATES.name} exists, and this script does not overwrite it")
    frames = []
    for series in FRED_SERIES:
        with urllib.request.urlopen(URL.format(series=series), timeout=60) as response:
            frame = pd.read_csv(io.BytesIO(response.read()))
        frames.append(frame.set_index("observation_date")[series])
    table = pd.concat(frames, axis=1)
    if str(table.index.max()) > "2018-04-30" or str(table.index.min()) > "2016-01-01":
        raise SystemExit("The rate file does not fit the test dates")
    table.to_csv(TEST_RATES)
    print(f"{TEST_RATES.name}: {len(table)} rows, {table.index.min()} to {table.index.max()}")


if __name__ == "__main__":
    main()
