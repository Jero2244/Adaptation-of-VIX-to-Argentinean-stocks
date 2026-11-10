"""The real test suite on the real folder, without one test: test_one_dividend_for_each_local_dividend_by_year parses the local dividend file, which holds locked rows, before its filter."""
import os, sys, unittest
from pathlib import Path
sys.dont_write_bytecode = True
REAL = Path(r"C:\Users\HP Laptop\.spyder-py3\2024-1\vix_ggal_adaptation")
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
print("ran", result.testsRun, "failures", len(result.failures), "errors", len(result.errors))
for t, tb in result.failures + result.errors:
    print(t.id(), tb[-300:])
