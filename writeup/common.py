"""Shared layout and charts for the two status papers. This folder is outside the freeze manifest. It reads no data file: the numbers are copied from the reports that each paper cites."""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import CondPageBreak, Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

HERE = Path(__file__).resolve().parent
FIGURES = HERE / "figures"
FONT_DIR = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, MUTED, RULE, TINT = "#0b0b0b", "#52514e", "#d9d8d3", "#f1f0ec"
WIDTH = A4[0] - 4.4 * cm
STATUS_LINE = "GGAL study, 2026-11-05. Step B has not run, so no verdict exists. Keep local: licensed-data results."


def register_fonts() -> None:
    for family, regular, bold, italic, both in (("Sans", "DejaVuSans", "DejaVuSans-Bold", "DejaVuSans-Oblique", "DejaVuSans-BoldOblique"), ("Serif", "DejaVuSerif", "DejaVuSerif-Bold", "DejaVuSerif-Italic", "DejaVuSerif-BoldItalic")):
        for name, file in ((family, regular), (f"{family}-Bold", bold), (f"{family}-Italic", italic), (f"{family}-BoldItalic", both)):
            pdfmetrics.registerFont(TTFont(name, str(FONT_DIR / f"{file}.ttf")))
        pdfmetrics.registerFontFamily(family, normal=family, bold=f"{family}-Bold", italic=f"{family}-Italic", boldItalic=f"{family}-BoldItalic")


def styles(family: str, size: float) -> dict[str, ParagraphStyle]:
    ink, muted = colors.HexColor(INK), colors.HexColor(MUTED)
    body = ParagraphStyle("body", fontName=family, fontSize=size, leading=size * 1.5, textColor=ink, spaceAfter=size * 0.65)
    return dict(
        body=body,
        title=ParagraphStyle("title", parent=body, fontName=f"{family}-Bold", fontSize=size * 2.05, leading=size * 2.5, spaceAfter=size * 0.6),
        subtitle=ParagraphStyle("subtitle", parent=body, textColor=muted, spaceAfter=size * 1.1),
        h1=ParagraphStyle("h1", parent=body, fontName=f"{family}-Bold", fontSize=size * 1.32, leading=size * 1.75, spaceBefore=size * 1.2, spaceAfter=size * 0.5, keepWithNext=1),
        h2=ParagraphStyle("h2", parent=body, fontName=f"{family}-Bold", fontSize=size * 1.05, leading=size * 1.45, spaceBefore=size * 0.6, spaceAfter=size * 0.3, keepWithNext=1),
        bullet=ParagraphStyle("bullet", parent=body, leftIndent=size * 1.3, bulletIndent=size * 0.2, spaceAfter=size * 0.35),
        cell=ParagraphStyle("cell", parent=body, fontSize=size * 0.86, leading=size * 1.22, spaceAfter=0),
        head=ParagraphStyle("head", parent=body, fontName=f"{family}-Bold", fontSize=size * 0.86, leading=size * 1.22, spaceAfter=0),
        caption=ParagraphStyle("caption", parent=body, fontSize=size * 0.84, leading=size * 1.22, textColor=muted, spaceBefore=size * 0.2, spaceAfter=size * 0.9),
        equation=ParagraphStyle("equation", parent=body, alignment=TA_CENTER, spaceBefore=size * 0.2, spaceAfter=size * 0.8),
        reference=ParagraphStyle("reference", parent=body, fontSize=size * 0.88, leading=size * 1.25, leftIndent=size * 1.2, firstLineIndent=-size * 1.2, spaceAfter=size * 0.3),
    )


class Paper:
    """A small wrapper, so each paper reads as a list of content calls."""

    def __init__(self, family: str, size: float, title: str, footer: str, output: Path):
        self.s = styles(family, size)
        self.story: list = []
        self.title, self.footer, self.output, self.family = title, footer, output, family

    def add(self, text: str, style: str = "body") -> None:
        self.story.append(Paragraph(text, self.s[style]))

    def section(self, text: str, room_cm: float) -> None:
        """A heading that starts a new page if the content after it would not fit."""
        self.story.append(CondPageBreak(room_cm * cm))
        self.add(text, "h1")

    def bullets(self, items: list[str]) -> None:
        for item in items:
            self.story.append(Paragraph(item, self.s["bullet"], bulletText="•"))

    def numbered(self, items: list[str]) -> None:
        for number, item in enumerate(items, 1):
            self.story.append(Paragraph(item, self.s["bullet"], bulletText=f"{number}."))

    def table(self, rows: list[list[str]], widths: list[float], caption: str | None = None) -> None:
        total = sum(widths)
        data = [[Paragraph(str(cell), self.s["head" if i == 0 else "cell"]) for cell in row] for i, row in enumerate(rows)]
        table = Table(data, colWidths=[WIDTH * w / total for w in widths], repeatRows=1)
        table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, 0), 0.9, colors.HexColor(INK)), ("LINEBELOW", (0, 1), (-1, -1), 0.35, colors.HexColor(RULE)), ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 5)]))
        block = [table, Paragraph(caption, self.s["caption"])] if caption else [table, Spacer(1, 8)]
        self.story.append(KeepTogether(block) if len(rows) <= 14 else table)
        if len(rows) > 14 and caption:
            self.story.append(block[1])

    def callout(self, text: str, tint: str = TINT, edge: str = BLUE) -> None:
        box = Table([[Paragraph(text, self.s["cell"])]], colWidths=[WIDTH])
        box.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(tint)), ("LINEBEFORE", (0, 0), (0, -1), 2.5, colors.HexColor(edge)), ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 9), ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10)]))
        self.story.extend([box, Spacer(1, 10)])

    def figure(self, path: Path, caption: str, height_ratio: float) -> None:
        self.story.append(KeepTogether([Image(str(path), width=WIDTH, height=WIDTH * height_ratio), Paragraph(caption, self.s["caption"])]))

    def build(self) -> None:
        family, footer = self.family, self.footer

        def decorate(canvas, doc):
            canvas.saveState()
            canvas.setFont(family, 7.2)
            canvas.setFillColor(colors.HexColor(MUTED))
            canvas.drawString(2.2 * cm, 1.15 * cm, footer)
            canvas.drawRightString(A4[0] - 2.2 * cm, 1.15 * cm, f"Page {doc.page}")
            canvas.restoreState()

        SimpleDocTemplate(str(self.output), pagesize=A4, leftMargin=2.2 * cm, rightMargin=2.2 * cm, topMargin=2.0 * cm, bottomMargin=2.0 * cm, title=self.title, author="Study owner, drafted with Claude Code").build(self.story, onFirstPage=decorate, onLaterPages=decorate)


def _style_axes(ax) -> None:
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(RULE)
    ax.tick_params(axis="x", colors=MUTED, length=0, labelsize=9)
    ax.tick_params(axis="y", colors=INK, length=0, labelsize=9)


def setup_matplotlib() -> None:
    for file in ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf"):
        font_manager.fontManager.addfont(str(FONT_DIR / file))
    plt.rcParams.update({"font.family": "DejaVu Sans", "figure.dpi": 240, "savefig.dpi": 240, "text.color": INK})


def timeline_chart(path: Path) -> None:
    """Periods from PROTOCOL.md."""
    fig, ax = plt.subplots(figsize=(7.2, 1.75))
    bars = [(2013.25, 2016.0, "#c9c8c2", "Dropped", INK), (2016.0, 2018.33, ORANGE, "One-time test\nStep B locked", "white"), (2018.33, 2026.83, BLUE, "", "white")]
    for start, end, color, label, ink in bars:
        ax.barh(0, end - start - 0.04, left=start, height=0.62, color=color)
        ax.text((start + end) / 2, 0, label, ha="center", va="center", fontsize=8.2, color=ink, fontweight="bold")
    ax.text(2021.7, 0, "Open data: builds the method. No verdict.", ha="center", va="center", fontsize=8.2, color="white", fontweight="bold")
    ax.plot([2025.17, 2025.17], [-0.46, 0.46], color=INK, linewidth=1.3)
    ax.text(2025.17, 0.5, "2025-03 quote format break", ha="center", va="bottom", fontsize=8, color=INK)
    ax.set_ylim(-0.5, 0.82)
    ax.set_xlim(2013, 2027)
    ax.set_xticks(range(2013, 2028, 2))
    ax.set_yticks([])
    _style_axes(ax)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def forest_chart(path: Path, rows: list[tuple[str, tuple | None, tuple | None]], size: tuple[float, float], show_legend: bool = True) -> None:
    """Each row: label, (b, low, high) with events, (b, low, high) with no events. Values from reports/stage4_descriptive.md."""
    fig, ax = plt.subplots(figsize=size)
    positions = list(range(len(rows)))[::-1]
    for y, (label, with_events, no_events) in zip(positions, rows):
        for values, color, offset, marker in ((with_events, BLUE, 0.14, "o"), (no_events, ORANGE, -0.14, "s")):
            if values is None:
                continue
            place = y + offset if with_events and no_events else y
            ax.plot([values[1], values[2]], [place, place], color=color, linewidth=2, solid_capstyle="round", zorder=2)
            ax.scatter([values[0]], [place], color=color, s=44, marker=marker, zorder=3, edgecolor="white", linewidth=1)
            ax.text(values[2] + 0.04, place, f"{values[0]:.2f}", va="center", fontsize=8, color=INK)
    ax.axvline(0, color=INK, linewidth=1)
    ax.axvline(0.37, color=MUTED, linewidth=1, linestyle=(0, (4, 3)))
    top = len(rows) - 0.42
    ax.text(-0.02, top, "0: no added information", ha="right", va="bottom", fontsize=7.8, color=INK)
    ax.text(0.39, top, ".37: lowest development estimate", ha="left", va="bottom", fontsize=7.8, color=MUTED)
    ax.set_yticks(positions, [row[0] for row in rows])
    ax.set_ylim(-0.6, len(rows) - 0.05)
    ax.set_xlim(-0.55, 1.85)
    ax.set_xlabel("b on implied volatility, with nominal 95% interval (21-session blocks)", fontsize=8.5, color=MUTED)
    ax.grid(axis="x", color=RULE, linewidth=0.5, zorder=0)
    _style_axes(ax)
    if show_legend:
        ax.scatter([], [], color=BLUE, marker="o", s=44, label="With events")
        ax.scatter([], [], color=ORANGE, marker="s", s=44, label="No events")
        ax.legend(loc="lower right", bbox_to_anchor=(1.0, 1.0), ncol=2, frameon=False, fontsize=8.5)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def outcomes_chart(path: Path, rows: list[tuple[str, float, float, float]], size: tuple[float, float]) -> None:
    """Each row: label, Supported, Smaller than .37, Inconclusive, in percent. Values from STAGE4_PLAN.md, section Expected results."""
    fig, ax = plt.subplots(figsize=size)
    positions = list(range(len(rows)))[::-1]
    names = ("Supported", "Smaller than .37", "Inconclusive")
    for y, row in zip(positions, rows):
        left = 0.0
        for value, color in zip(row[1:], (BLUE, ORANGE, AQUA)):
            ax.barh(y, value - 0.5, left=left, height=0.62, color=color)
            if value >= 3.5:
                ax.text(left + (value - 0.5) / 2, y, f"{value:.0f}%", ha="center", va="center", fontsize=8, color="white" if color != AQUA else INK, fontweight="bold")
            left += value
    ax.set_yticks(positions, [row[0] for row in rows])
    ax.set_xlim(0, 100.5)
    ax.set_xticks([])
    ax.spines["bottom"].set_visible(False)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.tick_params(axis="y", colors=INK, length=0, labelsize=9)
    for name, color in zip(names, (BLUE, ORANGE, AQUA)):
        ax.barh([0], [0], color=color, label=name)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3, frameon=False, fontsize=8.5)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
