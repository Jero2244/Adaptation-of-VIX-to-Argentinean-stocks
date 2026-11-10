"""Numbers, claim checks, and charts for the two calibration papers. The papers take their numbers from the result files, and the checks stop the build if a sentence no longer fits them."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

import common as c

ROOT = c.HERE.parent
REPORTS = ROOT / "reports"
R = json.loads((REPORTS / "calib_results.json").read_text(encoding="utf-8"))
SYN = json.loads((REPORTS / "calib_synthetic.json").read_text(encoding="utf-8"))
HORIZON = json.loads((REPORTS / "calib_horizon.json").read_text(encoding="utf-8"))
MANIFEST_TEXT = (REPORTS / "calib_freeze_manifest.json").read_bytes()
C1, C2, C3, POST = R["c1"], R["c2"], R["c3"], R["post_result"]
M, BENCH, CUTS = C2["measures"], C3["benchmarks"], C3["cuts"]
METHODS = BENCH["methods"]
Q = POST["atm30_quintiles"]
QS = Q["groups"]
INNER, OUTER = float(stats.norm.cdf(1) - stats.norm.cdf(-1)), float(stats.norm.cdf(2) - stats.norm.cdf(-2))
FOOTER = "GGAL implied move calibration, draft of 2026-11-05, revised 2026-11-10. Keep local: results from licensed data."
REVISION_NOTE = "Revised 2026-11-10 after an internal audit; see audit/AUDIT_REPORT.md and fixes/ERRATA.md."
PASO = pd.Timestamp("2019-07-31")
BREAK = pd.Timestamp("2025-03-01")


def pct(value: float, digits: int = 1) -> str:
    return f"{100 * value:.{digits}f}%"


def span(row: dict, block: int = 63, digits: int = 1) -> str:
    low, high = row.get(f"low{block}"), row.get(f"high{block}")
    return "blank" if low is None or high is None else f"{100 * low:.{digits}f} to {100 * high:.{digits}f}%"


def nspan(row: dict, block: int = 63, digits: int = 2) -> str:
    low, high = row.get(f"low{block}"), row.get(f"high{block}")
    return "blank" if low is None or high is None else f"{low:.{digits}f} to {high:.{digits}f}"


def includes(row: dict, value: float) -> bool:
    return all(row[f"low{b}"] <= value <= row[f"high{b}"] for b in (21, 63))


def excludes(row: dict, value: float) -> bool:
    return all(not row[f"low{b}"] <= value <= row[f"high{b}"] for b in (21, 63))


def check_claims() -> None:
    """Each line guards a sentence in the papers."""
    assert R["changed_since_freeze"] == [], "Results came from changed files"
    assert includes(M["inner"], INNER) and includes(M["outer"], OUTER) and includes(M["mean_z2"], 1.0)
    assert QS[0]["inner"]["high63"] < INNER and QS[0]["inner"]["high21"] < INNER
    assert Q["lowest_rows_in_2019_paso"] == 0
    assert excludes(Q["lowest_minus_highest_inner"], 0.0)
    assert includes(QS[1]["inner"], INNER) and includes(QS[2]["inner"], INNER) and includes(QS[4]["inner"], INNER)
    assert all(low <= .10 <= high for low, high in zip(C2["pit"]["low63"], C2["pit"]["high63"]))
    assert all(POST["by_event"][name]["inner"] == 1.0 for name in ("2019 general", "2023 PASO", "2023 general"))
    assert selection_bigger()
    assert round(100 * POST["by_event"]["2019 PASO"]["share_of_all_z2"], 1) == 18.3
    assert round(100 * METHODS["HAR, no factor"]["up_tail"]["value"], 1) == 4.2
    assert round(POST["actual_window"]["mean_days"], 2) == 29.35 and round(100 * POST["actual_window"]["inner"], 1) == 68.9
    assert round(100 * CUTS["2016-01 to 2018-04"]["down_tail"]["value"], 1) == .2 and round(100 * CUTS["2016-01 to 2018-04"]["up_tail"]["value"], 1) == 5.9
    base = POST["brier_against_base_rate"]
    assert all(includes(dict(low21=base[x]["low21"], high21=base[x]["high21"], low63=base[x]["low63"], high63=base[x]["high63"]), 0.0) for x in ("0.1", "0.2"))
    assert CUTS["No event in window"]["mean_z2"]["value"] < 1.1 < 4 < CUTS["Event in window"]["mean_z2"]["value"]
    assert POST["by_event"]["2019 PASO"]["outer"] == 0.0
    for name in ("HAR, no factor", "Fat-tailed ATM30"):
        for row in METHODS[name]["scores"].values():
            assert includes(row, 0.0)
    for name in ("HAR, Duan", "Scaled ATM30"):
        assert excludes(METHODS[name]["scores"]["interval_inner"], 0.0) and METHODS[name]["scores"]["interval_inner"]["difference"] > 0
    assert METHODS["Scaled ATM30"]["mean_z2"] < 1 and METHODS["Scaled ATM30"]["inner"]["value"] > METHODS["ATM30"]["inner"]["value"]
    assert METHODS["Fat-tailed ATM30"]["inner"]["value"] < METHODS["ATM30"]["inner"]["value"]
    assert HORIZON["months"] == 36 and HORIZON["verdict_horizon"] == "2029-10-30"
    for line in C2["reliability"].values():
        assert line["groups"][0]["observed"] > line["groups"][0]["mean_probability"] and line["groups"][-1]["observed"] < line["groups"][-1]["mean_probability"]


def selection_bigger() -> bool:
    row = POST["selection"]
    return row["big_move_blank"] > row["big_move_valid"] and row["low63"] > 0


def _axes(ax, grid: str = "y") -> None:
    c._style_axes(ax)
    ax.tick_params(axis="y", colors=c.MUTED)
    ax.grid(axis=grid, color=c.RULE, linewidth=.5, zorder=0)
    ax.set_axisbelow(True)


def bell_chart(path: Path, size=(7.2, 2.5)) -> None:
    x = np.linspace(-3.4, 3.4, 600)
    y = stats.norm.pdf(x)
    fig, ax = plt.subplots(figsize=size)
    ax.fill_between(x, y, where=np.abs(x) <= 2, color=c.BLUE, alpha=.25, linewidth=0)
    ax.fill_between(x, y, where=np.abs(x) <= 1, color=c.BLUE, alpha=.55, linewidth=0)
    ax.plot(x, y, color=c.INK, linewidth=1.2)
    ax.text(0, .17, "Inner band\n68.3% of moves", ha="center", va="center", fontsize=8.5, color="white", fontweight="bold")
    ax.annotate("Outer band\n95.4% of moves\n(inner band included)", xy=(1.5, .06), xytext=(2.25, .27), ha="center", fontsize=8.5, color=c.INK, arrowprops=dict(arrowstyle="-", color=c.MUTED, linewidth=.8))
    ax.annotate("Tail, 2.3%", xy=(-2.35, .012), xytext=(-2.9, .14), ha="center", fontsize=8.5, color=c.INK, arrowprops=dict(arrowstyle="-", color=c.MUTED, linewidth=.8))
    ax.annotate("Tail, 2.3%", xy=(2.35, .012), xytext=(3.05, .12), ha="center", fontsize=8.5, color=c.INK, arrowprops=dict(arrowstyle="-", color=c.MUTED, linewidth=.8))
    ax.set_xticks([-2, -1, 0, 1, 2], ["-2 band widths", "-1", "Centre", "+1", "+2 band widths"])
    ax.set_yticks([])
    ax.set_ylim(0, .43)
    c._style_axes(ax)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def quintile_chart(path: Path, size=(7.2, 2.9)) -> None:
    fig, ax = plt.subplots(figsize=size)
    positions = np.arange(5)
    values = [100 * g["inner"]["value"] for g in QS]
    lows, highs = [100 * g["inner"]["low63"] for g in QS], [100 * g["inner"]["high63"] for g in QS]
    ax.vlines(positions, lows, highs, color=c.BLUE, linewidth=2, zorder=2)
    ax.scatter(positions, values, color=c.BLUE, s=52, edgecolor="white", linewidth=1, zorder=3)
    for x, value, high in zip(positions, values, highs):
        ax.text(x, high + 1.5, f"{value:.1f}%", ha="center", va="bottom", fontsize=8.5, color=c.INK)
    ax.axhline(100 * INNER, color=c.INK, linewidth=1, linestyle=(0, (4, 3)), zorder=1)
    ax.text(.5, 100 * INNER + .8, "Calibrated: 68.3%", ha="center", va="bottom", fontsize=8, color=c.INK)
    ax.set_xticks(positions, [f"{i + 1}{' (lowest)' if i == 0 else ' (highest)' if i == 4 else ''}\n{g['low_atm30']:.2f} to {g['high_atm30']:.2f}" for i, g in enumerate(QS)])
    ax.set_xlabel("ATM30 quintile and range", fontsize=8.5, color=c.MUTED)
    ax.set_xlim(-.5, 4.5)
    ax.set_ylim(30, 100)
    ax.set_ylabel("Inner hit rate (%), 95% interval", fontsize=8.5, color=c.MUTED)
    _axes(ax)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def _panel() -> pd.DataFrame:
    panel = pd.read_parquet(ROOT / "data" / "calibration_panel.parquet")
    return panel[panel["valid"]]


def z_chart(path: Path, size=(7.2, 3.0)) -> None:
    rows = _panel()
    fig, ax = plt.subplots(figsize=size)
    ax.scatter(rows["session_date"], rows["z"], s=4, color=c.BLUE, linewidths=0, alpha=.75, zorder=2)
    for level, style in ((1, (0, (4, 3))), (2, "-")):
        for sign in (1, -1):
            ax.axhline(sign * level, color=c.MUTED, linewidth=.8, linestyle=style, zorder=1)
    ax.annotate("2019 PASO", xy=(PASO, rows["z"].min()), xytext=(pd.Timestamp("2020-06-01"), rows["z"].min() + .25), fontsize=8.2, color=c.INK, va="center", arrowprops=dict(arrowstyle="-", color=c.MUTED, linewidth=.8))
    ax.set_yticks([-6, -4, -2, -1, 0, 1, 2, 4])
    ax.set_ylabel("z: move in band widths", fontsize=8.5, color=c.MUTED)
    c._style_axes(ax)
    ax.tick_params(axis="y", colors=c.MUTED)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def rolling_chart(path: Path, size=(7.2, 3.0)) -> None:
    rows = _panel().set_index("session_date")
    z = rows["z"]
    inner = 100 * (np.abs(z) < 1).astype(float).rolling("365D", min_periods=126).mean()
    outer = 100 * (np.abs(z) < 2).astype(float).rolling("365D", min_periods=126).mean()
    fig, ax = plt.subplots(figsize=size)
    ax.plot(inner.index, inner, color=c.BLUE, linewidth=1.6, label="Inner band")
    ax.plot(outer.index, outer, color=c.ORANGE, linewidth=1.6, label="Outer band")
    ax.axhline(100 * INNER, color=c.BLUE, linewidth=.9, linestyle=(0, (4, 3)), label="Calibrated: 68.3%")
    ax.axhline(100 * OUTER, color=c.ORANGE, linewidth=.9, linestyle=(0, (4, 3)), label="Calibrated: 95.4%")
    ax.axvline(BREAK, color=c.MUTED, linewidth=.9, linestyle=":")
    ax.text(BREAK, 41, " 2025-03 quote format break", fontsize=7.8, color=c.MUTED, va="bottom")
    ax.set_ylim(40, 104)
    ax.set_ylabel("Hit rate over the past 12 months (%)", fontsize=8.5, color=c.MUTED)
    _axes(ax)
    ax.legend(loc="lower center", bbox_to_anchor=(.5, 1.), ncol=4, frameon=False, fontsize=8.2)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def reliability_chart(path: Path, size=(7.2, 3.3), compare: bool = True) -> None:
    fig, axes = plt.subplots(1, 2, figsize=size)
    for ax, x in zip(axes, ("0.1", "0.2")):
        series = [("ATM30", METHODS["ATM30"]["brier"][x]["groups"], c.BLUE, "o"), ("HAR, Duan factor", METHODS["HAR, Duan"]["brier"][x]["groups"], c.ORANGE, "s")] if compare else [("ATM30", C2["reliability"][x]["groups"], c.BLUE, "o")]
        top = 0.0
        for label, groups, color, marker in series:
            p, o = [100 * g["mean_probability"] for g in groups], [100 * g["observed"] for g in groups]
            top = max(top, *p, *o)
            ax.plot(p, o, color=color, marker=marker, markersize=6, linewidth=1.6, markeredgecolor="white", markeredgewidth=1, label=label, zorder=3)
        top *= 1.12
        ax.plot([0, top], [0, top], color=c.INK, linewidth=.9, linestyle=(0, (4, 3)), label="Forecast = observed", zorder=2)
        ax.set_xlim(0, top)
        ax.set_ylim(0, top)
        ax.set_aspect("equal")
        ax.set_title(f"Moves beyond ±{int(float(x) * 100)}%", loc="left", fontsize=9.5, color=c.INK)
        ax.set_xlabel("Forecast probability (%)", fontsize=8.5, color=c.MUTED)
        ax.set_ylabel("Observed share (%)", fontsize=8.5, color=c.MUTED)
        _axes(ax, "both")
        ax.legend(loc="upper left", frameon=False, fontsize=7.8)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def pit_chart(path: Path, size=(7.2, 2.7)) -> None:
    pit = C2["pit"]
    shares, low, high = (100 * np.array(pit[key]) for key in ("shares", "low63", "high63"))
    centers = np.arange(.05, 1, .1)
    fig, ax = plt.subplots(figsize=size)
    ax.bar(centers, shares, width=.086, color=c.BLUE, zorder=2)
    ax.errorbar(centers, shares, yerr=[shares - low, high - shares], fmt="none", ecolor=c.INK, elinewidth=.9, capsize=2, zorder=3)
    ax.axhline(10, color=c.INK, linewidth=1, linestyle=(0, (4, 3)), zorder=2)
    ax.text(.995, 16.2, "Calibrated: 10% per bin (dashed)", ha="right", fontsize=8, color=c.INK)
    ax.set_xlabel("PIT value, u = Φ(z)", fontsize=8.5, color=c.MUTED)
    ax.set_ylabel("Share of origins (%)", fontsize=8.5, color=c.MUTED)
    ax.set_ylim(0, 17.5)
    _axes(ax)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def benchmark_chart(path: Path, size=(7.2, 2.7)) -> None:
    names = list(METHODS)
    fig, axes = plt.subplots(1, 2, figsize=size, sharey=True)
    positions = list(range(len(names)))[::-1]
    for ax, key, nominal, label in ((axes[0], "inner", INNER, "Inner hit rate (%)"), (axes[1], "outer", OUTER, "Outer hit rate (%)")):
        for y, name in zip(positions, names):
            row = METHODS[name][key]
            ax.plot([100 * row["low63"], 100 * row["high63"]], [y, y], color=c.BLUE, linewidth=2, solid_capstyle="round", zorder=2)
            ax.scatter([100 * row["value"]], [y], color=c.BLUE, s=40, edgecolor="white", linewidth=1, zorder=3)
        ax.axvline(100 * nominal, color=c.INK, linewidth=1, linestyle=(0, (4, 3)), zorder=1)
        ax.set_xlabel(f"{label}; dashed: {100 * nominal:.1f}%", fontsize=8.5, color=c.MUTED)
        _axes(ax, "x")
    axes[0].set_yticks(positions, names)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def forward_timeline(path: Path, size=(7.2, 1.75)) -> None:
    fig, ax = plt.subplots(figsize=size)
    for start, end, color, label, ink in ((2016.0, 2018.33, "#c9c8c2", "Development\n(used once)", c.INK), (2018.33, 2026.83, c.BLUE, "Open data: exploratory, no verdict", "white"), (2026.83, 2029.83, c.ORANGE, "Forward test\n36 months", "white")):
        ax.barh(0, end - start - .04, left=start, height=.62, color=color)
        ax.text(2028.85 if color == c.ORANGE else (start + end) / 2, 0, label, ha="center", va="center", fontsize=8.2, color=ink, fontweight="bold")
    ax.plot([2027.83, 2027.83], [-.46, .46], color=c.INK, linewidth=1.2)
    ax.text(2027.83, .5, "12-month look,\nno verdict", ha="center", va="bottom", fontsize=7.6, color=c.INK)
    ax.plot([2029.91, 2029.91], [-.46, .46], color=c.INK, linewidth=1.2)
    ax.text(2029.95, .5, "Verdict", ha="center", va="bottom", fontsize=7.6, color=c.INK)
    ax.set_ylim(-.5, 1.05)
    ax.set_xlim(2015.8, 2030.5)
    ax.set_xticks(range(2016, 2031, 2))
    ax.set_yticks([])
    c._style_axes(ax)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
