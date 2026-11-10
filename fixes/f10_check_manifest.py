"""Process check (F15): compare the freeze manifest with a saved hash, and list changed frozen files. No file is written.

Usage:
  python f10_check_manifest.py                      compares with the hash printed in HANDOFF.md and with freeze.differences()
  python f10_check_manifest.py --saved <sha256>     also compares with the copy that the user keeps outside this folder
Exit code 0 only if every comparison that was asked for matches and freeze.differences() is empty.
Limit: this script cannot see the user's saved copy. Only the user can supply it.
"""
import argparse
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import freeze  # noqa: E402


def handoff_hashes() -> list[str]:
    text = (ROOT / "HANDOFF.md").read_text(encoding="utf-8")
    return re.findall(r"current manifest hash is `([0-9a-f]{64})`", text)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--saved", help="SHA-256 of reports/freeze_manifest.json from the user's own copy")
    args = ap.parse_args()
    actual = freeze.manifest_hash()
    print("SHA-256 of reports/freeze_manifest.json:", actual)
    ok = True
    for h in handoff_hashes():
        match = h == actual
        ok &= match
        print("HANDOFF.md 'current manifest hash':", h, "->", "MATCH" if match else "DIFFERENT")
    if not handoff_hashes():
        print("HANDOFF.md: no hash found in the expected sentence (cannot compare)")
    if args.saved:
        match = args.saved.strip().lower() == actual
        ok &= match
        print("User's saved hash:", args.saved.strip().lower(), "->", "MATCH" if match else "DIFFERENT")
    else:
        print("User's saved hash: NOT SUPPLIED. This comparison is still open (audit finding F15).")
    diffs = freeze.differences()
    print("freeze.differences():", diffs)
    ok &= not diffs
    print("RESULT:", "ALL MATCH" if ok else "MISMATCH")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
