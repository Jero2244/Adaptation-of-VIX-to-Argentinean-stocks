"""C4: four local figures of the calibration results. They derive from licensed data, so keep them local.

Run from the project folder: conda run --no-capture-output -n py4fi python calibration/calib_figures.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calib_core as cc  # noqa: E402

OUT = cc.ROOT / "reports" / "calib_figures"
SURFACE, INK, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
BLUE, ORANGE = "#2a78d6", "#eb6834"
BREAK = pd.Timestamp("2025-03-01")
SOURCE = "Exploratory. Open data, 2018-05 to 2026-10, daily origins with overlapping 30-day windows."


def style(ax, title, xlabel, ylabel):
    ax.set_facecolor(SURFACE)
    ax.set_title(title, loc="left", color=INK, fontsize=11)
    ax.set_xlabel(xlabel, color=MUTED, fontsize=9)
    ax.set_ylabel(ylabel, color=MUTED, fontsize=9)
    ax.tick_params(colors=MUTED, labelsize=8, length=0)
    ax.grid(True, axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)


def finish(fig, name):
    fig.patch.set_facecolor(SURFACE)
    fig.text(0.01, 0.005, SOURCE, color=MUTED, fontsize=7.5)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(OUT / name, dpi=160)
    plt.close(fig)


def pit(results):
    data = results["c2"]["pit"]
    shares, low, high = (100 * np.array(data[key]) for key in ("shares", "low63", "high63"))
    centers = np.arange(0.05, 1, 0.1)
    fig, ax = plt.subplots(figsize=(7.5, 4))
    ax.bar(centers, shares, width=0.09, color=BLUE, label="Share of origins")
    ax.errorbar(centers, shares, yerr=[shares - low, high - shares], fmt="none", ecolor=INK, elinewidth=1, capsize=2, label="95% interval, 63-session blocks")
    ax.axhline(10, color=MUTED, linestyle="--", linewidth=1.2, label="Calibrated: 10% per bin")
    style(ax, "PIT of the ATM30 band: all intervals include 10%", "PIT value, u = Φ(z)", "Share of origins (%)")
    ax.legend(frameon=False, fontsize=8, labelcolor=MUTED, loc="upper left", ncol=1)
    ax.set_ylim(0, 19)
    finish(fig, "pit_histogram.png")


def reliability(results):
    methods = results["c3"]["benchmarks"]["methods"]
    fig, axes = plt.subplots(1, 2, figsize=(9, 4.4))
    for ax, x in zip(axes, cc.THRESHOLDS):
        top = 0
        for name, color, marker in (("ATM30", BLUE, "o"), ("HAR, Duan", ORANGE, "s")):
            groups = methods[name]["brier"][str(x)]["groups"]
            p, o = 100 * np.array([g["mean_probability"] for g in groups]), 100 * np.array([g["observed"] for g in groups])
            top = max(top, p.max(), o.max())
            ax.plot(p, o, color=color, marker=marker, markersize=7, linewidth=2, markeredgecolor=SURFACE, markeredgewidth=1.5, label=name)
        top = top * 1.1
        ax.plot([0, top], [0, top], color=MUTED, linestyle="--", linewidth=1.2, label="Forecast = observed")
        ax.set_xlim(0, top)
        ax.set_ylim(0, top)
        ax.set_aspect("equal")
        style(ax, f"Moves beyond ±{int(x * 100)}%, common rows from 2019-05", "Forecast probability (%)", "Observed share (%)")
        ax.legend(frameon=False, fontsize=8, labelcolor=MUTED, loc="upper left")
    finish(fig, "reliability.png")


def rolling(panel):
    rows = panel[panel["valid"]].set_index("session_date")
    z = rows["z"]
    frames = (np.abs(z) < 1).astype(float).rolling("365D", min_periods=126).mean(), (np.abs(z) < 2).astype(float).rolling("365D", min_periods=126).mean()
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.plot(frames[0].index, 100 * frames[0], color=BLUE, linewidth=2, label="Inner: |z| < 1")
    ax.plot(frames[1].index, 100 * frames[1], color=ORANGE, linewidth=2, label="Outer: |z| < 2")
    ax.axhline(100 * cc.INNER, color=BLUE, linestyle="--", linewidth=1, label="Nominal 68.3%")
    ax.axhline(100 * cc.OUTER, color=ORANGE, linestyle="--", linewidth=1, label="Nominal 95.4%")
    ax.axvline(BREAK, color=MUTED, linewidth=1, linestyle=":")
    ax.text(BREAK, 102, " 2025-03 format break", color=MUTED, fontsize=8)
    style(ax, "Rolling 12-month hit rates", "Origin date", "Share of origins (%)")
    ax.set_ylim(0, 108)
    ax.legend(frameon=False, fontsize=8, labelcolor=MUTED, loc="lower left", ncol=2)
    finish(fig, "rolling_hit_rate.png")


def z_over_time(panel):
    rows = panel[panel["valid"]]
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.scatter(rows["session_date"], rows["z"], s=7, color=BLUE, linewidths=0, alpha=0.7, label="z per origin")
    for level, style_name in ((1, "--"), (2, "-")):
        ax.axhline(level, color=MUTED, linewidth=1, linestyle=style_name)
        ax.axhline(-level, color=MUTED, linewidth=1, linestyle=style_name)
    ax.annotate("2019 PASO", xy=(pd.Timestamp("2019-07-31"), rows["z"].min()), xytext=(pd.Timestamp("2020-03-01"), rows["z"].min() + 0.3), color=MUTED, fontsize=8, arrowprops=dict(arrowstyle="-", color=MUTED, linewidth=0.8))
    style(ax, "Standardized 30-day moves, with ±1 and ±2 lines", "Origin date", "z")
    ax.grid(False)
    finish(fig, "z_over_time.png")


def main():
    OUT.mkdir(exist_ok=True)
    results = json.loads((cc.ROOT / "reports" / "calib_results.json").read_text(encoding="utf-8"))
    panel = pd.read_parquet(cc.ROOT / "data" / "calibration_panel.parquet")
    pit(results)
    reliability(results)
    rolling(panel)
    z_over_time(panel)
    print(f"Wrote figures to {OUT}")


if __name__ == "__main__":
    main()
