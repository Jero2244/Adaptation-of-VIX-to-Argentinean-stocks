"""The real test suite on the real folder, without the one test that parses the local dividend file before its filter. An audit hook refuses any open of a locked file, so no locked file can be read by accident."""
import os, sys, unittest
from pathlib import Path
sys.dont_write_bytecode = True
REAL = Path(r"C:\Users\HP Laptop\.spyder-py3\2024-1\vix_ggal_adaptation")
BLOCK = ("alpaca_ggal_sip_raw.json", "fred_rates_test.csv")
hits = []
def hook(event, args):
    if event == "open" and isinstance(args[0], (str, os.PathLike)):
        name = os.path.basename(str(args[0]))
        if name in BLOCK and str(REAL).lower() in os.path.abspath(str(args[0])).lower():
            hits.append(name)
            raise PermissionError("blocked by the review audit hook")
sys.addaudithook(hook)
os.chdir(REAL); sys.path.insert(0, str(REAL))
SKIP = "test_one_dividend_for_each_local_dividend_by_year"
def flat(suite):
    for t in suite:
        if isinstance(t, unittest.TestSuite):
            yield from flat(t)
        else:
            yield t
loaded = list(flat(unittest.defaultTestLoader.discover(str(REAL / "tests"), top_level_dir=str(REAL / "tests"))))
keep = [t for t in loaded if t.id().split(".")[-1] != SKIP]
print("discovered", len(loaded), "kept", len(keep))
result = unittest.TextTestRunner(verbosity=0).run(unittest.TestSuite(keep))
print("ran", result.testsRun, "failures", len(result.failures), "errors", len(result.errors), "blocked opens", hits)
for t, tb in result.failures + result.errors:
    print(t.id(), tb[-300:])
