"""Stage 4, step 9: write and check the SHA-256 manifest of the code, the rules, and the input files.

Run from this folder: conda run -n py4fi python freeze.py
After a crash of the test, before any outcome: conda run -n py4fi python freeze.py --after-crash "what changed and why"
This folder has no git history. So the manifest gives evidence of a change, but it does not prevent one. The user keeps
the printed hash outside this folder.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from config import ADR_CASH_EVENTS, ALPACA_BARS, OPTION_CBBO, OPTION_DEFINITIONS, OPTIONS_MARKER, OUTCOMES_MARKER, REPORTS, RESULT, ROOT, RUN_RECORD, SOURCE

MANIFEST = REPORTS / "freeze_manifest.json"
RULE_FILES = ["PROTOCOL.md", "STAGE4_PLAN.md"]
INPUT_FILES = [OPTION_CBBO, OPTION_DEFINITIONS, ALPACA_BARS, ADR_CASH_EVENTS, SOURCE / "fred_rates_test.csv"]
STATUS_FINISHING = "finishing"  # The result write has started, so an outcome may exist.
AFTER_CRASH_STATUSES = ("started", "crashed", "floor_failed", "step_a_done", "input_stopped")


class ManifestMismatch(RuntimeError):
    """A frozen file changed, or a manifest is absent."""


class FreezeRefused(RuntimeError):
    """The run rules do not permit a new manifest."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest_hash(path: Path = MANIFEST) -> str:
    return sha256(path)


def frozen_files(root: Path = ROOT, inputs: list[Path] | None = None) -> list[Path]:
    code = sorted(root.glob("*.py")) + sorted((root / "tests").glob("*.py"))
    return code + [root / name for name in RULE_FILES] + list(INPUT_FILES if inputs is None else inputs)


def build_manifest(files: list[Path], root: Path = ROOT) -> dict:
    return {str(path.resolve().relative_to(root.resolve())).replace("\\", "/"): sha256(path) for path in files}


def manifest_text(files: list[Path] | None = None, root: Path = ROOT) -> str:
    return json.dumps(build_manifest(frozen_files() if files is None else files, root), indent=2, sort_keys=True)


def write_manifest(path: Path = MANIFEST, files: list[Path] | None = None, root: Path = ROOT) -> str:
    """Write the manifest and return its own hash."""
    path.parent.mkdir(parents=True, exist_ok=True)
    replace_manifest(path, manifest_text(files, root))
    return sha256(path)


def replace_manifest(path: Path, text: str) -> None:
    """Write through a partial file, so a failed write cannot leave a broken manifest."""
    partial = path.with_suffix(".partial")
    partial.write_text(text, encoding="utf-8", newline="\n")
    partial.replace(path)


def differences(path: Path = MANIFEST, files: list[Path] | None = None, root: Path = ROOT) -> list[str]:
    """The relative paths that were added, removed, or changed since the freeze."""
    if not path.exists():
        raise ManifestMismatch("The freeze manifest is absent")
    frozen = json.loads(path.read_text(encoding="utf-8"))
    current = build_manifest(frozen_files() if files is None else files, root)
    return sorted(name for name in set(frozen) | set(current) if frozen.get(name) != current.get(name))


def verify_manifest(path: Path = MANIFEST, files: list[Path] | None = None, root: Path = ROOT) -> None:
    changed = differences(path, files, root)
    if changed:
        raise ManifestMismatch(f"Changed since the freeze: {changed}")


def refuse_after_unlock() -> None:
    """A normal freeze must come before any approval or run of the test."""
    found = [path.name for path in (OPTIONS_MARKER, OUTCOMES_MARKER, REPORTS / "backward_test_unlocked.json", RUN_RECORD, RESULT, RESULT.with_suffix(".partial"), REPORTS / "stage5_step_a.json") if path.exists()]
    if found:
        raise SystemExit(f"Do not freeze after an unlock or a run. For a crash fix, use --after-crash. Found: {found}")


def after_crash(note: str, path: Path = MANIFEST, record_path: Path = RUN_RECORD, result_path: Path = RESULT, files: list[Path] | None = None, root: Path = ROOT, inputs: list[Path] | None = None, allow_input_change: bool = False) -> str:
    """Write a new manifest after a logged crash fix. Keep the old manifest, and keep both hashes, the changed files, and the note in the run record.

    This is permitted only before any outcome could exist. It keeps the markers and the record, so the audit trail stays whole.
    The record entry goes first, so a failed write cannot lose the old hash.
    """
    if not note or not note.strip():
        raise FreezeRefused("A crash freeze needs a note")
    if not record_path.exists():
        raise FreezeRefused("No run has started, so use a normal freeze")
    record = json.loads(record_path.read_text(encoding="utf-8"))
    if result_path.exists() or result_path.with_suffix(".partial").exists() or record["status"] not in AFTER_CRASH_STATUSES:
        raise FreezeRefused("An outcome may exist, so the frozen files cannot change for this test")
    changed = differences(path, files, root)
    if not changed:
        raise FreezeRefused("No frozen file changed, so a new manifest has nothing to record")
    input_paths = (INPUT_FILES if files is None else []) if inputs is None else inputs
    changed_inputs = sorted(set(changed) & set(build_manifest(input_paths, root)))
    if changed_inputs and not allow_input_change:
        raise FreezeRefused(f"Input files changed: {changed_inputs}. A code fix does not change an input. If this change is intended, pass --allow-input-change")
    old = sha256(path)
    text = manifest_text(files, root)
    new = hashlib.sha256(text.encode("utf-8")).hexdigest()
    shutil.copyfile(path, path.with_name(f"{path.stem}_{old[:12]}{path.suffix}"))
    record.setdefault("refreezes", []).append(dict(at=datetime.now(timezone.utc).isoformat(), old_sha256=old, new_sha256=new, changed=changed, note=note))
    partial = record_path.with_suffix(".partial")
    partial.write_text(json.dumps(record, indent=2), encoding="utf-8")
    partial.replace(record_path)
    replace_manifest(path, text)
    return new


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--after-crash", metavar="NOTE")
    parser.add_argument("--allow-input-change", action="store_true")
    args = parser.parse_args()
    if args.after_crash is not None:
        new = after_crash(args.after_crash, allow_input_change=args.allow_input_change)
    else:
        refuse_after_unlock()
        new = write_manifest()
    print(f"Manifest: {MANIFEST}")
    print(f"Keep this SHA-256 outside this folder: {new}")


if __name__ == "__main__":
    main()
