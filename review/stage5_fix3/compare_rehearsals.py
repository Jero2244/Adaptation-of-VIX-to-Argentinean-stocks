"""Open dates only. Compare three rehearsal results: the stored one from before this round, the new one, and one from the runner in review/pre_fix2_backup. Prints only whether keys differ."""
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
NAME = "rehearsal_2020-01-01_2022-04-30.json"
new = json.loads((ROOT / "review" / "stage4_rehearsal" / NAME).read_text(encoding="utf-8"))
stored = json.loads((ROOT / "review" / "pre_fix3_backup" / "stage4_rehearsal" / NAME).read_text(encoding="utf-8"))


def differing(first, second, path=""):
    if isinstance(first, dict) and isinstance(second, dict):
        return [item for key in sorted(set(first) | set(second)) for item in differing(first.get(key, "<absent>"), second.get(key, "<absent>"), f"{path}/{key}")]
    return [] if first == second else [path]


print("new against stored, differing keys:", differing(new, stored))
spec = importlib.util.spec_from_file_location("old_runner", ROOT / "review" / "pre_fix2_backup" / "run_tests_once.py")
old_runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old_runner)
with tempfile.TemporaryDirectory() as folder:
    old_runner.rehearse("2020-01-01", "2022-04-30", output=Path(folder))
    old = json.loads((Path(folder) / NAME).read_text(encoding="utf-8"))
print("new against old runner, differing keys:", differing(new, old))
