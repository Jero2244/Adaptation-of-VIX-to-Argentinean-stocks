"""Stage 3 figures. All results are exploratory. Run after run_development.py.

Output: reports/stage3_figures.png
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import forecasts as fc
from config import DATA, REPORTS
from events import EVENTS

BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
SURFACE, INK, SECONDARY, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"


def style(axis, title: str) -> None:
    axis.set_facecolor(SURFACE)
    axis.set_title(title, loc="left", fontsize=11, color=INK)
    axis.grid(axis="y", color=GRID, linewidth=0.6)
    axis.set_axisbelow(True)
    axis.tick_params(colors=MUTED, labelsize=8, length=0)
    for side in ("top", "right", "left"):
        axis.spines[side].set_visible(False)
    axis.spines["bottom"].set_color(AXIS)


def vol_timeline(axis, panel: pd.DataFrame) -> None:
    style(axis, "ATM30 and the realized vol of the next 30 days (annualized)")
    axis.plot(panel["session_date"], np.sqrt(panel["rv30"]), color=ORANGE, linewidth=1.3, label="Realized vol, next 30 days")
    axis.plot(panel["session_date"], panel["atm30"], color=BLUE, linewidth=1.3, label="ATM30")
    axis.legend(frameon=False, fontsize=8, loc="upper right", labelcolor=SECONDARY, ncols=2)
    axis.set_ylim(0, None)


def yearly_coefficients(axis, yearly: pd.DataFrame) -> None:
    style(axis, "Coefficient on log ATM30 squared, by year")
    rows = yearly[yearly["coefficient"] == "log_iv2"]
    for spec, color, marker, shift, label in (("MZ", BLUE, "o", -0.1, "MZ, IV alone"), ("HAR+IV", ORANGE, "s", 0.1, "HAR+IV")):
        chosen = rows[rows["spec"] == spec]
        axis.scatter(chosen["year"] + shift, chosen["estimate"], color=color, marker=marker, s=46, edgecolors=SURFACE, linewidths=1.5, zorder=3, label=label)
    axis.axhline(0, color=AXIS, linewidth=1)
    axis.set_xticks(sorted(rows["year"].unique()))
    axis.legend(frameon=False, fontsize=8, labelcolor=SECONDARY, loc="best")


def offset_spread(axis, offsets: pd.DataFrame) -> None:
    style(axis, "Coefficient across 21 non-overlapping samples")
    for place, (spec, color, label) in enumerate((("MZ", BLUE, "MZ, IV alone"), ("HAR+IV", ORANGE, "HAR+IV"))):
        chosen = offsets[offsets["spec"] == spec].sort_values("offset")
        axis.scatter(chosen["offset"], chosen["coefficient"], color=color, s=40, edgecolors=SURFACE, linewidths=1.5, label=label, marker="os"[place], zorder=3)
    axis.axhline(0, color=AXIS, linewidth=1)
    axis.set_xticks(range(0, 21, 5))
    axis.set_xlabel("Offset, in sessions", fontsize=8, color=MUTED)
    axis.legend(frameon=False, fontsize=8, labelcolor=SECONDARY, loc="best")


def cumulative_gain(axis, panel: pd.DataFrame) -> None:
    style(axis, "Cumulative QLIKE of HAR+ATM30 minus HAR (below zero means ATM30 helps)")
    scored = panel.dropna(subset=["c_atm", "c_ewma", "c_garch", "c_garch_t", "c_har", "c_har_atm", "rv30"])
    for prefix, color, label in (("c", BLUE, "With smearing"), ("m", ORANGE, "No smearing")):
        difference = fc.qlike(scored["rv30"], scored[f"{prefix}_har_atm"]) - fc.qlike(scored["rv30"], scored[f"{prefix}_har"])
        axis.plot(scored["session_date"], np.cumsum(difference), color=color, linewidth=1.3, label=label)
    axis.legend(frameon=False, fontsize=8, labelcolor=SECONDARY, loc="lower left")
    axis.axhline(0, color=AXIS, linewidth=1)
    for name, date in EVENTS:
        day = pd.Timestamp(date)
        if day >= scored["session_date"].iloc[0]:
            axis.axvline(day, color=GRID, linewidth=0.8, zorder=0)
    axis.set_xlabel("Vertical lines mark the listed events", fontsize=8, color=MUTED)


def event_ratios(axis, event_rows: pd.DataFrame, placebos: pd.DataFrame) -> None:
    style(axis, "Forward vol over near vol: events and placebo dates")
    names = event_rows["event"].tolist()
    for place, name in enumerate(names):
        chosen = placebos[placebos["event"] == name]["ratio"].dropna()
        axis.scatter(np.full(len(chosen), place), chosen, color=MUTED, s=16, alpha=0.6, linewidths=0, zorder=2, label="Placebo dates" if place == 0 else None)
    axis.scatter(range(len(names)), event_rows["ratio"], color=ORANGE, s=56, edgecolors=SURFACE, linewidths=1.5, zorder=3, label="Event")
    axis.axhline(1, color=AXIS, linewidth=1)
    axis.set_xticks(range(len(names)), [n.replace(" ", "\n") for n in names], fontsize=8)
    axis.legend(frameon=False, fontsize=8, labelcolor=SECONDARY, loc="best")


def main() -> None:
    panel = pd.read_parquet(DATA / "forecast_panel.parquet")
    yearly = pd.read_csv(REPORTS / "stage3_yearly.csv")
    offsets = pd.read_csv(REPORTS / "stage3_offsets.csv")
    event_rows = pd.read_csv(REPORTS / "stage3_events.csv")
    placebos = pd.read_csv(REPORTS / "stage3_placebos.csv")
    figure, axes = plt.subplot_mosaic([["vol", "vol"], ["year", "offset"], ["gain", "event"]], figsize=(13, 11), constrained_layout=True, facecolor=SURFACE)
    vol_timeline(axes["vol"], panel)
    yearly_coefficients(axes["year"], yearly)
    offset_spread(axes["offset"], offsets)
    cumulative_gain(axes["gain"], panel)
    event_ratios(axes["event"], event_rows, placebos)
    figure.suptitle("GGAL ADR, Stage 3. Exploratory results.", x=0.01, ha="left", fontsize=12, color=INK)
    figure.savefig(REPORTS / "stage3_figures.png", dpi=130)


if __name__ == "__main__":
    main()
