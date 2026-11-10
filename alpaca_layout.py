"""Print the layout of the Alpaca bar file: key names, value types, and row counts. It prints no dates or prices.

Run from this folder: conda run -n py4fi python alpaca_layout.py
A key that holds a digit is masked, because it could be a date. Only strings of known metadata keys could show a value,
and this helper prints no string values.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from config import ALPACA_BARS

MAX_KEYS = 40


def safe_key(key: str) -> str:
    return "<masked key>" if re.search(r"\d", str(key)) else str(key)


def describe(value, depth: int = 0, max_depth: int = 14) -> list[str]:
    """One line per level. A list reports its length and the union of the layout of its items, with no item values."""
    pad = "  " * depth
    if isinstance(value, dict):
        keys = list(value)
        masked = sum(safe_key(k) != str(k) for k in keys)
        lines = [f"{pad}dict with {len(keys)} keys, {masked} masked"]
        if depth < max_depth:
            shown = 0
            for key in keys:
                if safe_key(key) != str(key):
                    continue
                if shown == MAX_KEYS:
                    lines.append(f"{pad}  more keys not shown")
                    break
                lines.append(f"{pad}  {safe_key(key)}:")
                lines += describe(value[key], depth + 2, max_depth)
                shown += 1
            if masked:
                lines.append(f"{pad}  layout of the first masked key:")
                lines += describe(value[next(k for k in keys if safe_key(k) != str(k))], depth + 2, max_depth)
        return lines
    if isinstance(value, list):
        lines = [f"{pad}list with {len(value)} items, types {sorted({type(item).__name__ for item in value})}"]
        if value and depth < max_depth and isinstance(value[0], (dict, list)):
            lines.append(f"{pad}  layout of the first item:")
            lines += describe(value[0], depth + 2, max_depth)
        return lines
    return [f"{pad}{type(value).__name__}"]


def layout(path: Path = ALPACA_BARS) -> str:
    return "\n".join(describe(json.loads(Path(path).read_text(encoding="utf-8"))))


if __name__ == "__main__":
    print(layout())
