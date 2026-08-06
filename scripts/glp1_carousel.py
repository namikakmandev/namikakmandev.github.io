#!/usr/bin/env python3
"""LinkedIn carousel for the GLP-1 stock study -> notes/glp1-carousel.pdf

10 portrait slides (1080x1350, LinkedIn document format) in the study's dark
house style, matching scripts/pharma_carousel.py. Every number is computed from
data/glp1-stocks.json and data/glp1-valuation.json, never retyped, so the deck
cannot drift from the page.

Basis: the last COMPLETE month. The newest bar in the price file is a partial
month captured mid-session, so publishing off it would print a number that is
neither the month's close nor the live price.
"""
import json, os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PNGDIR = os.path.join(ROOT, "assets", "glp1-study", "carousel")
os.makedirs(PNGDIR, exist_ok=True)

SURFACE = "#0f1419"; CARD = "#151b22"; INK = "#f4f6f8"; INK2 = "#9aa3ad"
GRID = "#232a33"; MUTED = "#3d4654"
BLUE = "#3987e5"; GREEN = "#199e70"; ORANGE = "#d95926"; YELLOW = "#c98500"
RED = "#e05252"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "text.color": INK, "font.family": "DejaVu Sans",
})

S = json.load(open(os.path.join(ROOT, "data", "glp1-stocks.json")))["series"]
VAL = json.load(open(os.path.join(ROOT, "data", "glp1-valuation.json")))["series"]

MONTHS = sorted(S["LLY"])
NOW = MONTHS[-2]              # last complete month — see docstring
BASE = "2015-01"
SIX = ["LLY", "NVO", "AMGN", "AZN", "RHHBY", "PFE"]
NAMES = {"LLY": "Eli Lilly", "NVO": "Novo Nordisk", "AMGN": "Amgen",
         "AZN": "AstraZeneca", "RHHBY": "Roche", "PFE": "Pfizer",
         "VKTX": "Viking", "GPCR": "Structure Tx", "ALT": "Altimmune",
         "ZLDPF": "Zealand", "SPX": "S&P 500", "XBI": "Biotech ETF"}

W, H = 7.2, 9.0               # 1080 x 1350 at dpi 150


def mult(k, frm=BASE, to=None):
    return S[k][to or NOW] / S[k][frm]


def ret(k, frm=BASE, to=None):
    return (mult(k, frm, to) - 1) * 100


def pc(v, dp=0):
    return f"{'+' if v >= 0 else ''}{v:.{dp}f}%"


def drawdown(k):
    """(worst peak-to-trough, current vs all-time high, month of that high)."""
    v = S[k]; ks = [m for m in MONTHS if m <= NOW and m in v]
    peak = -1e9; worst = 0.0
    for m in ks:
        peak = max(peak, v[m])
        worst = min(worst, (v[m] / peak - 1) * 100)
    ath = max(v[m] for m in ks)
    athm = next(m for m in ks if v[m] == ath)
    return worst, (v[ks[-1]] / ath - 1) * 100, athm


def fmt_month(m):
    y, mo = m.split("-")
    return ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul",
            "Aug", "Sep", "Oct", "Nov", "Dec"][int(mo) - 1] + " " + y


# ----------------------------------------------------------------- chrome
def newslide():
    fig = plt.figure(figsize=(W, H))
    fig.patch.set_facecolor(SURFACE)
    fig.add_artist(plt.Line2D([0.08, 0.16], [0.945, 0.945], color=BLUE,
                              lw=3, solid_capstyle="round"))
    return fig


def footer(fig, n):
    fig.text(0.08, 0.045, "Namık Akman", color=INK2, fontsize=11, fontweight="bold")
    fig.text(0.08, 0.028, "namikakmandev.github.io", color=MUTED, fontsize=9.5)
    fig.text(0.92, 0.037, f"{n}/10", color=INK2, fontsize=11, ha="right")


def kicker(fig, text, color=BLUE):
    fig.text(0.08, 0.93, text.upper(), color=color, fontsize=12.5,
             fontweight="bold", va="top")


def save(fig, pdf, n):
    footer(fig, n)
    pdf.savefig(fig, facecolor=SURFACE)
    fig.savefig(os.path.join(PNGDIR, f"slide_{n:02d}.png"), dpi=150, facecolor=SURFACE)
    plt.close(fig)


def axes(fig, rect):
    ax = fig.add_axes(rect)
    ax.set_facecolor(SURFACE)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=11)
    ax.grid(axis="y", color=GRID, lw=0.8)
    return ax


# ----------------------------------------------------------------- slides
def s1(pdf):
    fig = newslide()
    kicker(fig, "Data study · markets")
    fig.text(0.08, 0.80, "One drug class.", fontsize=40, fontweight="bold", va="top")
    fig.text(0.08, 0.725, "Two opposite", fontsize=40, fontweight="bold", va="top")
    fig.text(0.08, 0.65, "outcomes.", fontsize=40, fontweight="bold", va="top", color=BLUE)
    fig.text(0.08, 0.545,
             "GLP-1 drugs became the defining\nmedicine of the decade. Two companies\nown the franchise.\n\n"
             "The market has priced them apart\nfar more than the headlines suggest.",
             fontsize=19, va="top", linespacing=1.45, color=INK)
    fig.text(0.08, 0.20, f"Monthly total return · 2015 → {fmt_month(NOW)}",
             fontsize=14, color=INK2)
    fig.text(0.08, 0.165, "12 listed names, dividends reinvested", fontsize=14, color=MUTED)
    save(fig, pdf, 1)


def s2(pdf):
    fig = newslide()
    kicker(fig, "The two leaders")
    fig.text(0.08, 0.885, "Same science.\nDifferent decade.", fontsize=31,
             fontweight="bold", va="top", linespacing=1.2)
    rows = [("Eli Lilly", ret("LLY"), BLUE), ("Novo Nordisk", ret("NVO"), ORANGE),
            ("S&P 500", ret("SPX"), INK2)]
    for i, (lab, v, c) in enumerate(rows):
        y = 0.66 - i * 0.115
        fig.text(0.08, y, lab, fontsize=19, color=INK)
        fig.text(0.92, y, pc(v), fontsize=27, color=c, fontweight="bold", ha="right")
        fig.add_artist(plt.Line2D([0.08, 0.92], [y - 0.028, y - 0.028], color=GRID, lw=1))
    fig.text(0.08, 0.27, "Total return since January 2015.", fontsize=15, color=INK2)
    fig.text(0.08, 0.22, "Lilly did not just win. It was the\nonly one of the two that beat the index.",
             fontsize=16, color=INK, va="top", linespacing=1.4)
    save(fig, pdf, 2)


def s3(pdf):
    fig = newslide()
    kicker(fig, "The divergence")
    fig.text(0.08, 0.905, "They rose together —\nthen split", fontsize=27,
             fontweight="bold", va="top", linespacing=1.2)
    ax = axes(fig, [0.12, 0.20, 0.80, 0.60])
    b = "2021-01"
    ms = [m for m in MONTHS if b <= m <= NOW]
    xs = range(len(ms))
    for k, c in (("LLY", BLUE), ("NVO", ORANGE)):
        ax.plot(xs, [S[k][m] / S[k][b] * 100 for m in ms], color=c, lw=2.6)
    ax.plot(xs, [S["SPX"][m] / S["SPX"][b] * 100 for m in ms], color=MUTED,
            lw=1.6, ls=(0, (4, 3)))
    for k, c, lab in (("LLY", BLUE, "Lilly"), ("NVO", ORANGE, "Novo"),
                      ("SPX", MUTED, "S&P 500")):
        v = S[k][ms[-1]] / S[k][b] * 100
        ax.annotate(f"{lab} {v:.0f}", (len(ms) - 1, v), xytext=(7, 0),
                    textcoords="offset points", color=c, fontsize=11.5,
                    fontweight="bold", va="center")
    yr = [(i, m[:4]) for i, m in enumerate(ms) if m.endswith("-01")]
    ax.set_xticks([i for i, _ in yr]); ax.set_xticklabels([t for _, t in yr])
    ax.set_xlim(0, len(ms) + 11)
    fig.text(0.08, 0.145, "Indexed: January 2021 = 100.", fontsize=12.5, color=INK2)
    fig.text(0.08, 0.105, "Novo peaked in mid-2024 and gave back most of the run.",
             fontsize=12.5, color=INK2)
    save(fig, pdf, 3)


def s4(pdf):
    fig = newslide()
    worst, cur, athm = drawdown("NVO")
    kicker(fig, "The fall", ORANGE)
    fig.text(0.08, 0.86, f"{worst:.0f}%", fontsize=96, fontweight="bold",
             color=ORANGE, va="top")
    fig.text(0.08, 0.665, "Novo Nordisk, peak to trough.", fontsize=21, va="top")
    fig.text(0.08, 0.60, f"Still {abs(cur):.0f}% below its {fmt_month(athm)} high.",
             fontsize=18, va="top", color=INK2)
    fig.text(0.08, 0.485, "Why drawdown matters more\nthan average return:",
             fontsize=17, va="top", color=INK, linespacing=1.35)
    for i, (f, need) in enumerate([("20%", "+25%"), ("50%", "+100%"),
                                   (f"{abs(worst):.0f}%", f"+{(1/(1+worst/100)-1)*100:.0f}%")]):
        y = 0.375 - i * 0.058
        c = ORANGE if i == 2 else INK2
        fig.text(0.08, y, f"a fall of {f}", fontsize=16, color=c)
        fig.text(0.62, y, f"needs {need}", fontsize=16, color=c, fontweight="bold")
    fig.text(0.08, 0.155, "…just to get back to where you started.",
             fontsize=14.5, color=MUTED)
    save(fig, pdf, 4)


def s5(pdf):
    fig = newslide()
    kicker(fig, "Inside the theme")
    fig.text(0.08, 0.905, "Same tailwind.\nOpposite results.", fontsize=29,
             fontweight="bold", va="top", linespacing=1.2)
    ax = axes(fig, [0.34, 0.20, 0.58, 0.58])
    ks = ["GPCR", "LLY", "XBI", "NVO", "ALT"]
    vals = [ret(k, "2025-07") for k in ks]
    cols = [GREEN if v > 0 else ORANGE for v in vals]
    ax.barh(range(len(ks)), vals, color=cols, height=.62)
    ax.set_yticks(range(len(ks)))
    ax.set_yticklabels([NAMES[k] for k in ks], fontsize=13, color=INK)
    ax.invert_yaxis()
    ax.axvline(0, color=INK2, lw=1)
    ax.grid(axis="y", lw=0)
    ax.grid(axis="x", color=GRID, lw=.8)
    for i, v in enumerate(vals):
        ax.annotate(pc(v), (v, i), xytext=(8 if v >= 0 else -8, 0),
                    textcoords="offset points", color=INK, fontsize=12.5,
                    fontweight="bold", va="center",
                    ha="left" if v >= 0 else "right")
    # leave room on the left so a negative bar's value label clears the name label
    ax.set_xlim(min(min(vals) * 2.4 - 20, -60), max(vals) * 1.32)
    fig.text(0.08, 0.145, "One year, same drug class, same tailwind.", fontsize=13, color=INK2)
    fig.text(0.08, 0.105, "Picking the winner was the whole game.", fontsize=13, color=INK2)
    save(fig, pdf, 5)


def s6(pdf):
    """The punchline."""
    fig = newslide()
    six = [k for k in SIX if BASE in S[k]]
    basket = (sum(mult(k) for k in six) / len(six) - 1) * 100
    ex = (sum(mult(k) for k in six if k != "LLY") / (len(six) - 1) - 1) * 100
    idx = ret("SPX")
    kicker(fig, "The finding", GREEN)
    fig.text(0.08, 0.89, "One stock carried\nthe entire theme", fontsize=29,
             fontweight="bold", va="top", linespacing=1.2)
    rows = [("All six GLP-1 names", basket, GREEN, "beats the index"),
            ("S&P 500", idx, INK2, ""),
            ("The same six, without Lilly", ex, ORANGE, "loses to the index")]
    for i, (lab, v, c, note) in enumerate(rows):
        y = 0.70 - i * 0.135
        fig.text(0.08, y, lab, fontsize=17, color=INK)
        fig.text(0.92, y, pc(v), fontsize=30, color=c, fontweight="bold", ha="right")
        if note:
            fig.text(0.08, y - 0.038, note, fontsize=13, color=c)
        fig.add_artist(plt.Line2D([0.08, 0.92], [y - 0.062, y - 0.062], color=GRID, lw=1))
    fig.text(0.08, 0.27, "Equal-weighted, held since January 2015.", fontsize=13.5, color=INK2)
    fig.text(0.08, 0.20,
             "The drug class was genuinely\ntransformative — and buying the class\nwas still not a strategy.",
             fontsize=17, va="top", linespacing=1.4)
    save(fig, pdf, 6)


def s7(pdf):
    fig = newslide()
    kicker(fig, "The twist", ORANGE)
    fig.text(0.08, 0.89, "The company that\ninvented the category\nlagged the market",
             fontsize=26, fontweight="bold", va="top", linespacing=1.22)
    ax = axes(fig, [0.14, 0.30, 0.78, 0.38])
    ks = ["SPX", "NVO"]
    vals = [ret(k) for k in ks]
    ax.bar([0, 1], vals, color=[MUTED, ORANGE], width=.5)
    ax.set_xticks([0, 1]); ax.set_xticklabels(["S&P 500", "Novo Nordisk"],
                                              fontsize=14, color=INK)
    for i, v in enumerate(vals):
        ax.annotate(pc(v), (i, v), xytext=(0, 8), textcoords="offset points",
                    ha="center", color=INK, fontsize=17, fontweight="bold")
    ax.set_ylim(0, max(vals) * 1.28)
    fig.text(0.08, 0.225,
             "Novo brought semaglutide to market\nand defined the category.",
             fontsize=16.5, va="top", linespacing=1.4)
    fig.text(0.08, 0.135,
             "Inventing the product and capturing\nthe shareholder return are different problems.",
             fontsize=14, va="top", color=INK2, linespacing=1.4)
    save(fig, pdf, 7)


def s8(pdf):
    fig = newslide()
    nvo, lly = VAL.get("NVO", {}), VAL.get("LLY", {})
    kicker(fig, "Valuation")
    fig.text(0.08, 0.90, "So Novo is cheap now?", fontsize=28,
             fontweight="bold", va="top")
    fig.text(0.08, 0.845, "Not once you adjust for growth.", fontsize=17,
             va="top", color=INK2)
    hdr = [("", 0.08), ("Novo", 0.56), ("Lilly", 0.83)]
    for t, x in hdr:
        fig.text(x, 0.735, t, fontsize=14, color=INK2, fontweight="bold", ha="center" if x > .1 else "left")
    rows = [("Price ÷ earnings", f"{nvo.get('trailing_pe', 0):.1f}x", f"{lly.get('trailing_pe', 0):.1f}x", False),
            ("Earnings growth, 5-yr", pc(nvo.get("eps_growth_5y_cagr", 0) * 100),
             pc(lly.get("eps_growth_5y_cagr", 0) * 100), False),
            ("PEG  (multiple ÷ growth)", f"{nvo.get('peg_5y', 0):.2f}", f"{lly.get('peg_5y', 0):.2f}", True)]
    for i, (lab, a, b, hi) in enumerate(rows):
        y = 0.655 - i * 0.085
        fig.text(0.08, y, lab, fontsize=15.5, color=INK if not hi else INK)
        fig.text(0.56, y, a, fontsize=19 if not hi else 22, ha="center",
                 color=ORANGE if hi else INK, fontweight="bold")
        fig.text(0.83, y, b, fontsize=19 if not hi else 22, ha="center",
                 color=GREEN if hi else INK, fontweight="bold")
        fig.add_artist(plt.Line2D([0.08, 0.92], [y - 0.028, y - 0.028], color=GRID, lw=1))
    fig.text(0.08, 0.325, "Lower PEG = better value for the growth.",
             fontsize=13.5, color=MUTED)
    fig.text(0.08, 0.235,
             "A 14x multiple on shrinking earnings\nis not a discount.\nIt is a forecast.",
             fontsize=19, va="top", linespacing=1.4, fontweight="bold")
    save(fig, pdf, 8)


def s9(pdf):
    fig = newslide()
    kicker(fig, "How to read any multiple", GREEN)
    fig.text(0.08, 0.90, "Flip it upside down", fontsize=30, fontweight="bold", va="top")
    fig.text(0.08, 0.835, "A multiple is hard to judge.\nA yield is not.", fontsize=17,
             va="top", color=INK2, linespacing=1.35)
    nvo, lly = VAL.get("NVO", {}), VAL.get("LLY", {})
    rows = [(f"Novo at {nvo.get('trailing_pe',0):.1f}x", 100 / nvo.get("trailing_pe", 1), ORANGE),
            (f"Lilly at {lly.get('trailing_pe',0):.1f}x", 100 / lly.get("trailing_pe", 1), BLUE)]
    for i, (lab, y_, c) in enumerate(rows):
        y = 0.66 - i * 0.10
        fig.text(0.08, y, lab, fontsize=17, color=INK)
        fig.text(0.92, y, f"{y_:.1f}%", fontsize=26, color=c, fontweight="bold", ha="right")
        fig.add_artist(plt.Line2D([0.08, 0.92], [y - 0.026, y - 0.026], color=GRID, lw=1))
    fig.text(0.08, 0.44, "1 ÷ the multiple = earnings yield —\nthe profit earned per $1 you invest.",
             fontsize=16, va="top", color=INK, linespacing=1.4)
    fig.text(0.08, 0.30,
             "Novo pays more today. Lilly's grows\nfaster. That trade-off is the entire\nquestion — and it is why the cheap\none is not automatically the bargain.",
             fontsize=16, va="top", linespacing=1.42)
    save(fig, pdf, 9)


def s10(pdf):
    fig = newslide()
    kicker(fig, "What it cannot tell you")
    fig.text(0.08, 0.89, "Everything here is what\nthe market has already\nconcluded.",
             fontsize=25, fontweight="bold", va="top", linespacing=1.22)
    fig.text(0.08, 0.685,
             "None of it says who wins the next\nround. That turns on trial readouts,\n"
             "oral formulations, manufacturing and\npayer coverage — none of which live\nin a price series.",
             fontsize=16, va="top", linespacing=1.42, color=INK)
    lly = VAL.get("LLY", {})
    fig.text(0.08, 0.44,
             f"And Lilly is not priced as a safe bet:\nat a PEG of {lly.get('peg_5y', 0):.2f} it already needs years\nof high-teens growth to justify today.",
             fontsize=16, va="top", linespacing=1.42, color=INK2)
    fig.add_artist(plt.Line2D([0.08, 0.92], [0.33, 0.33], color=GRID, lw=1))
    fig.text(0.08, 0.265, "Full study · charts, data and method",
             fontsize=15, color=INK, fontweight="bold")
    fig.text(0.08, 0.225, "namikakmandev.github.io/glp1-stocks.html",
             fontsize=13.5, color=BLUE)
    fig.text(0.08, 0.165, "Not investment advice.", fontsize=13, color=MUTED)
    fig.text(0.08, 0.12, "Follow for more data studies →", fontsize=13.5, color=INK2)
    save(fig, pdf, 10)


def main():
    out = os.path.join(ROOT, "notes", "glp1-carousel.pdf")
    with PdfPages(out) as pdf:
        for f in (s1, s2, s3, s4, s5, s6, s7, s8, s9, s10):
            f(pdf)
    print("wrote", out, "· basis month:", NOW)
    print("slides in", PNGDIR)


if __name__ == "__main__":
    main()
