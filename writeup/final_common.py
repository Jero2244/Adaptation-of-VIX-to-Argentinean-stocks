"""Charts and checks for the two final reports. It reads the stored panels for one descriptive chart, and it checks the quoted result numbers against the result file."""
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import common as c

ROOT = c.HERE.parent
RESULT = json.loads((ROOT / "reports" / "stage5_result.json").read_text(encoding="utf-8"))
FOOTER = "GGAL study, final report draft, 2026-11-05, revised 2026-11-10. Keep local: results from licensed data."
REVISION_NOTE = "Revised 2026-11-10 after an internal audit; see audit/AUDIT_REPORT.md and fixes/ERRATA.md."
FIXES = ROOT / "fixes"


def check_numbers() -> None:
    """A transcription check: the text quotes these values, so stop the build if they differ from the result file."""
    r, n, t, race = RESULT["rule1"], RESULT["no_events"], RESULT["tier1"], RESULT["race"]
    quoted = {(r["n"], 455), (n["n"], 418), (t["n"], 245), (race["scored"], 271)}
    assert all(a == b for a, b in quoted)
    pairs = [(r["b"], .281), (r["low21"], -.209), (r["high21"], .845), (r["low63"], -.232), (r["high63"], .937), (n["b"], .351), (n["low21"], -.121), (n["high21"], .916), (n["low63"], -.168), (n["high63"], .925), (t["b"], .411), (t["low21"], -.110), (t["high21"], 1.162), (t["low63"], -.026), (t["high63"], 1.367), (race["clark_west"]["t"], -.300), (race["clark_west_block63"]["t"], -.270), (race["qlike_duan"]["low"], -.008), (race["qlike_duan"]["high"], .025), (race["qlike_no_factor"]["low"], -.007), (race["qlike_no_factor"]["high"], .033), (race["mean_target"], .113), (RESULT["each_event_dropped"]["2017-08-14"]["b"], .362), (RESULT["each_event_dropped"]["2017-10-23"]["b"], .262), (RESULT["fixed_steps"][0]["mean_b"], .396), (RESULT["fixed_steps"][1]["mean_b"], .384)]
    for value, text in pairs:
        assert abs(value - text) < .001, (value, text)
    assert RESULT["decision"] == dict(outcome="Inconclusive", rule1=False, also_out_of_sample=False, usable_gain=False)


def check_open_data() -> None:
    """Audit finding F22. The open-data coefficients that the text types by hand must equal reports/stage4_coefficients.csv (read only)."""
    table = pd.read_csv(ROOT / "reports" / "stage4_coefficients.csv").set_index(["period", "events"])
    typed = {
        ("All", "with events"): (1806, .622, .337, .916, .309, .946),
        ("All", "no events"): (1643, .459, .152, .715, .060, .761),
        ("Before 2025-03", "with events"): (1431, .525, .208, .862, .152, .922),
        ("Before 2025-03", "no events"): (1300, .366, -.018, .682, -.131, .717),
        ("From 2025-03", "with events"): (375, 1.190, .488, 1.516, .330, 1.516),
        ("From 2025-03", "no events"): (343, .781, .227, 1.244, .149, 1.415),
        ("2018-2023", "with events"): (1165, .526, .192, .875, None, None),
        ("2018-2023", "no events"): (1034, .364, -.030, .721, None, None),
        ("2024-2025", "with events"): (464, 1.185, .588, 1.469, None, None),
        ("2024-2025", "no events"): (432, .891, .429, 1.223, None, None),
        ("2026", "with events"): (177, .423, -.387, 1.569, None, None),
    }
    for key, values in typed.items():
        row = table.loc[key]
        assert int(row["n"]) == values[0], key
        for name, text in zip(("b", "low21", "high21", "low63", "high63"), values[1:]):
            if text is not None:
                assert abs(row[name] - text) < .0006, (key, name, row[name], text)


def check_fixes() -> None:
    """The post-audit numbers that the text types by hand must equal the files in fixes/ (read only). Development work, not Stage 5."""
    v = pd.read_csv(FIXES / "f04_variants.csv").set_index("variant")
    wanted = {
        "stored baseline": (1846, 1806, .622, .622, 4.13),
        "F9 min near term 7d": (1597, 1564, .650, .650, 4.21),
        "F7 strict last row": (1837, 1797, .627, .627, 4.14),
        "F3 spread <= .50": (1688, 1650, .668, .643, 4.10),
        "F4 Tier 1 only": (1285, 1245, .703, .703, 3.67),
        "COMBINED strict+spread.50+Tier1": (1037, 1003, .835, .829, 3.71),
        "COMBINED + 7d floor (all four)": (966, 936, .846, .840, 3.66),
        "all four, spread .25 (sens.)": (728, 707, .808, .811, 2.73),
        "F2 American tree, all dividends": (1846, 1806, .621, .622, 4.17),
        "F2 American tree, confirmed only": (1846, 1806, .623, .622, 4.16),
        "all four + American tree": (961, 931, .848, .843, 3.71),
    }
    for name, (days, origins, b, b_same, t) in wanted.items():
        row = v.loc[name]
        assert (int(row["valid_days"]), int(row["primary_origins"])) == (days, origins), name
        assert abs(row["b"] - b) < .0006 and abs(row["b_stored_same_rows"] - b_same) < .0006 and abs(row["nw_t"] - t) < .006, name
    four = v.loc["COMBINED + 7d floor (all four)"]
    assert (round(four["boot21_low"], 3), round(four["boot21_high"], 3), round(four["boot63_low"], 3), round(four["boot63_high"], 3)) == (.440, 1.324, .437, 1.346)
    har = pd.read_csv(FIXES / "f08_rv_har.csv")
    old, new = (har[(har["iv_series"] == "stored ATM30") & (har["rv_version"] == "RVhf (no filter)") & (har["target"] == "log_rv30") & (har["baseline"].str.startswith(kind))].iloc[0] for kind in ("HAR old", "HAR new"))
    assert (round(old["r2_har"], 3), round(new["r2_har"], 3), round(old["b"], 3), round(new["b"], 3)) == (.097, .108, .622, .608)
    assert (round(old["nw_t"], 2), round(new["nw_t"], 2)) == (4.13, 3.35)
    assert (round(new["boot21_low"], 3), round(new["boot21_high"], 3), round(new["boot63_low"], 3), round(new["boot63_high"], 3)) == (.283, .970, .253, .996)
    mz = pd.read_csv(FIXES / "f09_mincer_zarnowitz.csv").set_index(["iv_series", "scale"])
    typed_mz = {("stored ATM30", "logs"): (-.541, .698, .163), ("stored ATM30", "variance levels"): (.181, .686, .031), ("stored ATM30", "volatility levels"): (.163, .683, .100)}
    for key, (a, b, r2) in typed_mz.items():
        assert abs(mz.loc[key, "a"] - a) < .0006 and abs(mz.loc[key, "b"] - b) < .0006 and abs(mz.loc[key, "r2"] - r2) < .0006, key
    assert mz.loc[("stored ATM30", "logs"), "p_joint"] < .0001
    assert (round(mz.loc[("stored ATM30", "variance levels"), "p_joint"], 3), round(mz.loc[("stored ATM30", "volatility levels"), "p_joint"], 3)) == (.064, .027)
    assert tuple(round(mz.loc[("all four fixes", s), "p_joint"], 2) for s in ("logs", "variance levels", "volatility levels")) == (.10, .31, .48)
    cov = pd.read_csv(FIXES / "f09_coverage.csv")
    assert all(abs(x - y) < .0006 for x, y in zip(cov["measured_coverage"], (.870, .893, .878, .893, .913, .898))), "coverage as in fixes/FIXES_REPORT.md"
    assert (cov["draws"] == 400).all() and (cov["nominal"] == .95).all()
    sub = pd.read_csv(FIXES / "f15_subsamples.csv").set_index(["series", "period"])
    typed_sub = {("stored ATM30, HAR old", "2018-2023"): (.526, 2.98), ("stored ATM30, HAR old", "2024-2025"): (1.185, 6.57), ("stored ATM30, HAR old", "2026"): (.423, 1.01), ("stored ATM30, HAR old", "before 2025-03"): (.525, 3.25), ("stored ATM30, HAR old", "from 2025-03"): (1.190, 5.83),
                 ("all four fixes, HAR old", "2018-2023"): (.530, 1.99), ("all four fixes, HAR old", "2024-2025"): (1.362, 7.76), ("all four fixes, HAR old", "2026"): (1.405, 2.63), ("all four fixes, HAR old", "before 2025-03"): (.646, 2.58), ("all four fixes, HAR old", "from 2025-03"): (1.619, 9.84)}
    for key, (b, t) in typed_sub.items():
        assert abs(sub.loc[key, "b"] - b) < .0006 and abs(sub.loc[key, "nw_t"] - t) < .006, key


def panels() -> tuple[pd.DataFrame, pd.DataFrame]:
    columns = ["session_date", "atm30", "rv30"]
    return pd.read_parquet(ROOT / "data" / "forecast_panel.parquet", columns=columns), pd.read_parquet(ROOT / "data" / "test" / "test_panel.parquet", columns=columns)


def series_chart(path: Path, size: tuple[float, float]) -> dict:
    """Implied volatility and the realized volatility of the next 30 days, on one log axis. Returns the medians that the text quotes."""
    open_panel, test_panel = panels()
    fig, ax = plt.subplots(figsize=size)
    ax.axvspan(pd.Timestamp("2016-01-04"), pd.Timestamp("2018-04-30"), color=c.TINT, zorder=0)
    ax.text(pd.Timestamp("2017-03-01"), 3.15, "One-time test", ha="center", va="top", fontsize=8, color=c.INK, fontweight="bold")
    for frame in (test_panel, open_panel):
        realized = frame.dropna(subset=["rv30"])
        implied = frame.dropna(subset=["atm30"])
        ax.plot(realized["session_date"], np.sqrt(realized["rv30"]), color=c.ORANGE, linewidth=.9, zorder=2)
        ax.plot(implied["session_date"], implied["atm30"], color=c.BLUE, linewidth=.9, zorder=3)
    ax.plot([], [], color=c.BLUE, linewidth=2, label="Implied volatility, ATM30")
    ax.plot([], [], color=c.ORANGE, linewidth=2, label="Realized volatility of the next 30 days")
    ax.set_yscale("log")
    ax.set_yticks([.2, .5, 1, 2, 3], [".2", ".5", "1", "2", "3"])
    ax.minorticks_off()
    ax.set_ylim(.15, 3.4)
    ax.set_xlim(pd.Timestamp("2015-10-01"), pd.Timestamp("2026-12-31"))
    ax.grid(axis="y", color=c.RULE, linewidth=.5, zorder=1)
    c._style_axes(ax)
    ax.tick_params(axis="y", colors=c.MUTED)
    ax.set_ylabel("Annualized volatility, log scale", fontsize=8.5, color=c.MUTED)
    ax.legend(loc="lower center", bbox_to_anchor=(.5, 1.0), ncol=2, frameon=False, fontsize=8.5)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return dict(test_atm=test_panel["atm30"].median(), open_atm=open_panel["atm30"].median(), test_rv=np.sqrt(test_panel["rv30"]).median(), open_rv=np.sqrt(open_panel["rv30"]).median())


def comparison_chart(path: Path, rows: list[tuple[str, float, float, float, str]], size: tuple[float, float]) -> None:
    """Each row: label, b, low, high, and "dev" or "test". Intervals use 21-session blocks."""
    fig, ax = plt.subplots(figsize=size)
    positions = list(range(len(rows)))[::-1]
    look = dict(dev=(c.BLUE, "o"), test=(c.ORANGE, "s"))
    for y, (_, b, low, high, kind) in zip(positions, rows):
        color, marker = look[kind]
        ax.plot([low, high], [y, y], color=color, linewidth=2, solid_capstyle="round", zorder=2)
        ax.scatter([b], [y], color=color, marker=marker, s=44, edgecolor="white", linewidth=1, zorder=3)
        ax.text(high + .04, y, f"{b:.2f}", va="center", fontsize=8, color=c.INK)
    ax.axvline(0, color=c.INK, linewidth=1)
    ax.text(-.02, len(rows) - .42, "0: no added information", ha="right", va="bottom", fontsize=7.8, color=c.INK)
    ax.set_yticks(positions, [row[0] for row in rows])
    ax.set_ylim(-.6, len(rows) - .05)
    ax.set_xlim(-.6, 1.5)
    ax.set_xlabel("b on implied volatility, with nominal 95% interval (21-session blocks)", fontsize=8.5, color=c.MUTED)
    ax.grid(axis="x", color=c.RULE, linewidth=.5, zorder=0)
    c._style_axes(ax)
    ax.scatter([], [], color=c.BLUE, marker="o", s=44, label="Open data that built the method")
    ax.scatter([], [], color=c.ORANGE, marker="s", s=44, label="One-time test, 2016-01 to 2018-04")
    ax.legend(loc="lower right", bbox_to_anchor=(1., 1.), ncol=2, frameon=False, fontsize=8.5)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def timeline_final(path: Path) -> None:
    fig, ax = plt.subplots(figsize=(7.2, 1.75))
    for start, end, color, label, ink in ((2013.25, 2016.0, "#c9c8c2", "Dropped", c.INK), (2016.0, 2018.33, c.ORANGE, "One-time test\nDone", "white"), (2018.33, 2026.83, c.BLUE, "", "white")):
        ax.barh(0, end - start - .04, left=start, height=.62, color=color)
        ax.text((start + end) / 2, 0, label, ha="center", va="center", fontsize=8.2, color=ink, fontweight="bold")
    ax.text(2021.7, 0, "Open data: builds the method. No verdict.", ha="center", va="center", fontsize=8.2, color="white", fontweight="bold")
    ax.plot([2025.17, 2025.17], [-.46, .46], color=c.INK, linewidth=1.3)
    ax.text(2025.17, .5, "2025-03 quote format break", ha="center", va="bottom", fontsize=8, color=c.INK)
    ax.set_ylim(-.5, .82)
    ax.set_xlim(2013, 2027)
    ax.set_xticks(range(2013, 2028, 2))
    ax.set_yticks([])
    c._style_axes(ax)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
