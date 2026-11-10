"""The real test suite on the real folder, without the class BuiltInputs, because its setUpClass parses the full cash file with pd.read_csv (a forbidden route).
test_cash_events_are_gated_and_filtered stays: it uses load_cash_events on open dates."""
import os, sys, unittest
from pathlib import Path
sys.dont_write_bytecode = True
REAL = Path(r"C:\Users\HP Laptop\.spyder-py3\2024-1\vix_ggal_adaptation")
os.chdir(REAL); sys.path.insert(0, str(REAL))


def flat(suite):
    for t in suite:
        if isinstance(t, unittest.TestSuite):
            yield from flat(t)
        else:
            yield t


loaded = list(flat(unittest.defaultTestLoader.discover(str(REAL / "tests"), top_level_dir=str(REAL / "tests"))))
keep = [t for t in loaded if type(t).__name__ != "BuiltInputs"]
print("discovered", len(loaded), "kept", len(keep), "skipped", sorted(t.id() for t in loaded if type(t).__name__ == "BuiltInputs"))
result = unittest.TextTestRunner(verbosity=0).run(unittest.TestSuite(keep))
print("ran", result.testsRun, "failures", len(result.failures), "errors", len(result.errors))
for t, tb in result.failures + result.errors:
    print(t.id(), tb[-300:])
