"""Inspection plots for Stage 2: ATM30 history, and the windows around 2019-08-12 and the rights date."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from config import DATA, REPORTS

INK, MUTED, GRID, LINE = "#1f2328", "#5f6670", "#e4e7eb", "#2f6db5"
WINDOWS = [("2019-07-15", "2019-09-30", "2019-08-12", "2019 PASO: first session after the vote"),
           ("2024-12-16", "2025-02-28", "2025-01-21", "Rights ex-date 2025-01-21")]


def style(axis) -> None:
    axis.spines[["top", "right"]].set_visible(False)
    axis.spines[["left", "bottom"]].set_color(GRID)
    axis.grid(axis="y", color=GRID, linewidth=0.8)
    axis.set_axisbelow(True)
    axis.tick_params(colors=MUTED, labelsize=9, length=0)
    axis.set_ylabel("Annualized vol (%)", color=MUTED, fontsize=9)


def main() -> None:
    series = pd.read_parquet(DATA / "index_series.parquet")
    figure, axes = plt.subplot_mosaic([["all", "all"], ["a", "b"]], figsize=(11, 7), constrained_layout=True)
    # Gaps stay visible: a missing session breaks the line.
    axes["all"].plot(series["session_date"], series["atm30"] * 100, color=LINE, linewidth=1.1)
    axes["all"].set_title("ATM30, 2018-05 to 2026-10 (gaps are missing sessions)", loc="left", color=INK, fontsize=11)
    style(axes["all"])
    for key, (start, end, marker, title) in zip("ab", WINDOWS):
        part = series[series["session_date"].between(start, end)]
        axes[key].plot(part["session_date"], part["atm30"] * 100, color=LINE, linewidth=2, marker="o", markersize=4)
        axes[key].axvline(pd.Timestamp(marker), color=MUTED, linewidth=1, linestyle="--")
        axes[key].set_title(title, loc="left", color=INK, fontsize=11)
        axes[key].tick_params(axis="x", rotation=30)
        style(axes[key])
    figure.savefig(REPORTS / "atm30_inspection.png", dpi=130)


if __name__ == "__main__":
    main()
