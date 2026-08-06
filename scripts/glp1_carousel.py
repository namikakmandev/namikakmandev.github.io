#!/usr/bin/env python3
"""LinkedIn carousel for the GLP-1 stock study -> notes/glp1-carousel.pdf

6 portrait slides (1080x1350, LinkedIn document format) in the study's dark
house style, matching scripts/pharma_carousel.py. Plain corporate register:
short sentences, no rhetorical constructions, no second-person address.

Every figure is computed from data/glp1-stocks.json and data/glp1-valuation.json,
never retyped, so the deck cannot drift from the study page.

Basis: the last COMPLETE month. The newest bar in the price file is a partial
month captured mid-session, so publishing off it would print a figure that is
neither the month's close nor the live price.

Company descriptors: only claims that a source supports. Lilly's and Novo's
molecules and brands are universally documented. For the two clinical-stage
names the entity descriptions do not name a GLP-1 candidate (and Altimmune's is
stale, still describing a vaccine business), so those rows say only that the
company is clinical stage with no approved product — which is the distinction
the slide actually rests on.
"""
import json, os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PNGDIR = os.path.join(ROOT, "assets", "glp1-study", "carousel")
os.makedirs(PNGDIR, exist_ok=True)

SURFACE = "#0f1419"; INK = "#f4f6f8"; INK2 = "#9aa3ad"
GRID = "#232a33"; MUTED = "#3d4654"
BLUE = "#3987e5"; GREEN = "#199e70"; ORANGE = "#d95926"

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
NSLIDES = 6
W, H = 7.2, 9.0               # 1080 x 1350 at dpi 150


def mult(k, frm=BASE, to=None):
    return S[k][to or NOW] / S[k][frm]


def ret(k, frm=BASE, to=None):
    return (mult(k, frm, to) - 1) * 100


def pc(v, dp=0):
    return f"{'+' if v >= 0 else ''}{v:,.{dp}f}%"


def fmt_month(m):
    y, mo = m.split("-")
    return ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul",
            "Aug", "Sep", "Oct", "Nov", "Dec"][int(mo) - 1] + " " + y


def yr_ago(m):
    y, mo = m.split("-")
    return f"{int(y)-1}-{mo}"


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
    fig.text(0.92, 0.037, f"{n}/{NSLIDES}", color=INK2, fontsize=11, ha="right")


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


def rowstrip(fig, rows, y0, gap=0.062):
    """name / descriptor / value rows with a rule under each."""
    for i, (name, desc, val, colour) in enumerate(rows):
        y = y0 - i * gap
        fig.text(0.08, y, name, fontsize=15.5, color=INK, fontweight="bold")
        if desc:
            fig.text(0.08, y - 0.020, desc, fontsize=11.5, color=INK2)
        fig.text(0.92, y, val, fontsize=22, color=colour, fontweight="bold", ha="right")
        fig.add_artist(plt.Line2D([0.08, 0.92], [y - 0.032, y - 0.032], color=GRID, lw=1))


# ----------------------------------------------------------------- slides
def s1(pdf):
    """Cover: the chart. Sized and shaded so the split reads at thumbnail size."""
    fig = newslide()
    kicker(fig, "GLP-1 market study")
    fig.text(0.08, 0.875, "Same medicine.", fontsize=35, fontweight="bold", va="top")
    fig.text(0.08, 0.808, "Opposite outcomes.", fontsize=35, fontweight="bold",
             va="top", color=BLUE)

    ax = axes(fig, [0.13, 0.30, 0.74, 0.43])
    b = "2021-01"
    ms = [m for m in MONTHS if b <= m <= NOW]
    xs = list(range(len(ms)))
    lly = [S["LLY"][m] / S["LLY"][b] * 100 for m in ms]
    nvo = [S["NVO"][m] / S["NVO"][b] * 100 for m in ms]
    spx = [S["SPX"][m] / S["SPX"][b] * 100 for m in ms]
    # shade the gap: the divergence is the story, so make it a visible area
    ax.fill_between(xs, lly, nvo, where=[a > c for a, c in zip(lly, nvo)],
                    color=BLUE, alpha=0.13, linewidth=0)
    ax.plot(xs, spx, color=MUTED, lw=1.5, ls=(0, (4, 3)))
    ax.plot(xs, nvo, color=ORANGE, lw=3.4)
    ax.plot(xs, lly, color=BLUE, lw=3.4)
    for k, ys, c, lab in (("LLY", lly, BLUE, "Eli Lilly"),
                          ("NVO", nvo, ORANGE, "Novo Nordisk"),
                          ("SPX", spx, MUTED, "S&P 500")):
        ax.annotate(lab, (len(ms) - 1, ys[-1]), xytext=(9, 0),
                    textcoords="offset points", color=c,
                    fontsize=12.5 if k != "SPX" else 10.5,
                    fontweight="bold", va="center")
    yrs = [(i, m[:4]) for i, m in enumerate(ms) if m.endswith("-01") and int(m[:4]) % 2 == 1]
    ax.set_xticks([i for i, _ in yrs]); ax.set_xticklabels([t for _, t in yrs], fontsize=12)
    ax.set_xlim(0, len(ms) + 28)

    fig.text(0.13, 0.255, "Indexed: Jan 2021 = 100", fontsize=11, color=MUTED)
    fig.add_artist(plt.Line2D([0.08, 0.92], [0.215, 0.215], color=GRID, lw=1))
    fig.text(0.08, 0.168,
             "Two companies built the defining medicine of\nthe decade. One produced almost all of the return.",
             fontsize=16.5, va="top", linespacing=1.45)
    fig.text(0.08, 0.088, f"Total return, Jan 2021 – {fmt_month(NOW)}. USD, dividends reinvested.",
             fontsize=11.5, color=MUTED)
    save(fig, pdf, 1)


def s2(pdf):
    """The same story as a number, now that the cover has shown the shape."""
    fig = newslide()
    kicker(fig, "Performance since 2015")
    fig.text(0.08, 0.885, "A decade apart.", fontsize=34, fontweight="bold", va="top")

    for i, (k, colour, name, drug) in enumerate([
            ("LLY", BLUE, "Eli Lilly", "tirzepatide — Mounjaro, Zepbound"),
            ("NVO", ORANGE, "Novo Nordisk", "semaglutide — Ozempic, Wegovy")]):
        y = 0.700 - i * 0.205
        fig.text(0.08, y, pc(ret(k)), fontsize=62, fontweight="bold",
                 color=colour, va="center")
        fig.text(0.08, y - 0.068, name, fontsize=17, fontweight="bold", color=INK)
        fig.text(0.08, y - 0.098, drug, fontsize=12.5, color=INK2)

    fig.add_artist(plt.Line2D([0.08, 0.92], [0.375, 0.375], color=GRID, lw=1))
    fig.text(0.08, 0.325, "S&P 500", fontsize=16, fontweight="bold", color=INK)
    fig.text(0.92, 0.330, pc(ret("SPX")), fontsize=26, fontweight="bold",
             color=INK2, ha="right", va="center")
    fig.text(0.08, 0.297, "market benchmark", fontsize=12, color=INK2)
    fig.add_artist(plt.Line2D([0.08, 0.92], [0.265, 0.265], color=GRID, lw=1))

    fig.text(0.08, 0.205,
             "Novo Nordisk created the category and still\ntrailed the index over the decade.",
             fontsize=16.5, va="top", linespacing=1.45)
    fig.text(0.08, 0.115, f"Total return, Jan 2015 – {fmt_month(NOW)}",
             fontsize=11.5, color=MUTED)
    save(fig, pdf, 2)


def s3(pdf):
    fig = newslide()
    kicker(fig, "Within the sector")
    fig.text(0.08, 0.895, "Results varied widely.", fontsize=30,
             fontweight="bold", va="top")

    # best and worst of the ten, plus the two leaders and the sector benchmark
    ten = ["LLY", "NVO", "AMGN", "AZN", "RHHBY", "PFE", "VKTX", "GPCR", "ALT", "ZLDPF"]
    frm = yr_ago(NOW)
    yr = {k: ret(k, frm) for k in ten if frm in S[k]}
    best = max(yr, key=yr.get); worst = min(yr, key=yr.get)
    # XBI deliberately excluded: it is a broad biotech index across all disease
    # areas, not a GLP-1 basket, so a bar beside GLP-1 companies would mislead.
    # Its return is given in the footnote instead.
    picks = [best, "LLY", "NVO", worst]
    seen = set(); picks = [k for k in picks if not (k in seen or seen.add(k))]

    # Descriptors: molecule names only where a filing or release confirms them.
    LABEL = {
        "LLY": ("Eli Lilly", "tirzepatide — approved, on sale"),
        "NVO": ("Novo Nordisk", "semaglutide — approved, on sale"),
        "GPCR": ("Structure Therapeutics", "aleniglipron — oral GLP-1, Phase 3"),
        "ALT": ("Altimmune", "pemvidutide — liver disease, Phase 3"),
        "VKTX": ("Viking Therapeutics", "clinical stage, no approved product"),
        "ZLDPF": ("Zealand Pharma", "clinical stage, no approved product"),
        "AMGN": ("Amgen", "GLP-1 in development only"),
        "AZN": ("AstraZeneca", "GLP-1 in development only"),
        "RHHBY": ("Roche", "GLP-1 in development only"),
        "PFE": ("Pfizer", "GLP-1 in development only"),
    }
    vals = [ret(k, frm) for k in picks]

    ax = axes(fig, [0.40, 0.345, 0.52, 0.455])
    ax.barh(range(len(picks)), vals,
            color=[GREEN if v >= 0 else ORANGE for v in vals], height=.55)
    ax.set_yticks(range(len(picks))); ax.set_yticklabels([])
    ax.invert_yaxis()
    ax.axvline(0, color=INK2, lw=1)
    ax.grid(axis="y", lw=0); ax.grid(axis="x", color=GRID, lw=.8)

    tr = ax.get_yaxis_transform()          # x in axes fraction, y in data units
    for i, k in enumerate(picks):
        nm, desc = LABEL[k]
        ax.text(-0.04, i - 0.17, nm, transform=tr, ha="right", va="center",
                fontsize=13, color=INK, fontweight="bold")
        ax.text(-0.04, i + 0.20, desc, transform=tr, ha="right", va="center",
                fontsize=9.3, color=INK2)
    for i, v in enumerate(vals):
        ax.annotate(pc(v), (v, i), xytext=(7 if v >= 0 else -7, 0),
                    textcoords="offset points", color=INK, fontsize=12.5,
                    fontweight="bold", va="center", ha="left" if v >= 0 else "right")
    ax.set_xlim(min(min(vals) * 2.6 - 15, -55), max(vals) * 1.30)
    ax.set_xlabel(f"Total return, 12 months to {fmt_month(NOW)}  (%)",
                  fontsize=11, color=INK2, labelpad=9)

    fig.text(0.08, 0.245,
             "The highest and lowest performers are both pre-revenue.\nTheir share prices move on trial results, not on sales.",
             fontsize=14, va="top", linespacing=1.4, color=INK)
    fig.text(0.08, 0.135,
             f"Selection: best and worst of the ten companies, plus the two leaders. All four\n"
             f"develop or sell GLP-1 medicines. The broad biotech index rose {pc(ret('XBI', frm))} over the\n"
             f"same period; it is not GLP-1 specific.",
             fontsize=10.5, va="top", color=MUTED, linespacing=1.35)
    save(fig, pdf, 3)


def s4(pdf):
    fig = newslide()
    six = [k for k in SIX if BASE in S[k]]
    basket = (sum(mult(k) for k in six) / len(six) - 1) * 100
    ex = (sum(mult(k) for k in six if k != "LLY") / (len(six) - 1) - 1) * 100
    kicker(fig, "The main finding", GREEN)
    fig.text(0.08, 0.895, "Returns came from\none company.", fontsize=30,
             fontweight="bold", va="top", linespacing=1.2)
    rowstrip(fig, [
        ("All six GLP-1 companies", "equally weighted", pc(basket), GREEN),
        ("S&P 500", "market benchmark", pc(ret("SPX")), INK2),
        ("The same six, excluding Lilly", "equally weighted", pc(ex), ORANGE),
    ], 0.70, gap=0.115)
    fig.text(0.08, 0.36, "Sector exposure alone did not deliver the return.",
             fontsize=17, color=INK, fontweight="bold")
    fig.text(0.08, 0.285,
             "Excluding one company, the group returned less\nthan the index over the same period.",
             fontsize=15, va="top", linespacing=1.4, color=INK)
    fig.text(0.08, 0.165, f"Held from Jan 2015 to {fmt_month(NOW)}. Total return.",
             fontsize=11.5, color=MUTED)
    save(fig, pdf, 4)


def s5(pdf):
    fig = newslide()
    nvo, lly = VAL.get("NVO", {}), VAL.get("LLY", {})
    kicker(fig, "Valuation")
    fig.text(0.08, 0.895, "A lower multiple reflects\nlower expected growth.", fontsize=26,
             fontweight="bold", va="top", linespacing=1.22)
    for t, x in (("Novo Nordisk", 0.62), ("Eli Lilly", 0.86)):
        fig.text(x, 0.735, t, fontsize=12.5, color=INK2, fontweight="bold", ha="center")
    rows = [("Price ÷ earnings", f"{nvo.get('trailing_pe', 0):.1f}x",
             f"{lly.get('trailing_pe', 0):.1f}x", False),
            ("Expected growth, 5-yr",
             pc(nvo.get("eps_growth_5y_cagr", 0) * 100),
             pc(lly.get("eps_growth_5y_cagr", 0) * 100), False),
            ("PEG (multiple ÷ growth)", f"{nvo.get('peg_5y', 0):.2f}",
             f"{lly.get('peg_5y', 0):.2f}", True)]
    for i, (lab, a, b, hi) in enumerate(rows):
        y = 0.655 - i * 0.088
        fig.text(0.08, y, lab, fontsize=14, color=INK)
        fig.text(0.62, y, a, fontsize=23 if hi else 19, ha="center",
                 color=ORANGE if hi else INK, fontweight="bold")
        fig.text(0.86, y, b, fontsize=23 if hi else 19, ha="center",
                 color=GREEN if hi else INK, fontweight="bold")
        fig.add_artist(plt.Line2D([0.08, 0.92], [y - 0.030, y - 0.030], color=GRID, lw=1))
    fig.text(0.08, 0.355, "A lower PEG indicates better value for the growth expected.",
             fontsize=11.5, color=MUTED)
    fig.text(0.08, 0.295,
             "Adjusted for growth, Novo Nordisk is the more\nexpensive of the two.",
             fontsize=17, va="top", fontweight="bold", linespacing=1.4)
    fig.text(0.08, 0.205,
             "Only these two companies have approved GLP-1 medicines for\nobesity on the market. The comparison is the whole market.",
             fontsize=14, va="top", color=INK, linespacing=1.4)
    fig.text(0.08, 0.115,
             "Trailing multiples are on reported earnings; consensus growth is on an adjusted\nbasis. Snapshot, not a live figure.",
             fontsize=10.5, va="top", color=MUTED, linespacing=1.35)
    save(fig, pdf, 5)


def s6(pdf):
    fig = newslide()
    kicker(fig, "Scope and limitations")
    fig.text(0.08, 0.895, "What this does\nnot cover.", fontsize=31,
             fontweight="bold", va="top", linespacing=1.2)
    fig.text(0.08, 0.715,
             "These figures show what the market\ncurrently expects.\n\n"
             "They do not forecast trial outcomes,\nregulatory decisions, manufacturing\ncapacity or pricing.\n\n"
             "Valuation figures are a point-in-time\nsnapshot and move with estimate\nrevisions as well as price.",
             fontsize=17, va="top", linespacing=1.45)
    fig.add_artist(plt.Line2D([0.08, 0.92], [0.30, 0.30], color=GRID, lw=1))
    fig.text(0.08, 0.245, "Full study, charts, data and method",
             fontsize=15, color=INK, fontweight="bold")
    fig.text(0.08, 0.205, "namikakmandev.github.io/glp1-stocks.html",
             fontsize=13.5, color=BLUE)
    fig.text(0.08, 0.145, "Not investment advice.", fontsize=12.5, color=MUTED)
    save(fig, pdf, 6)


def main():
    out = os.path.join(ROOT, "notes", "glp1-carousel.pdf")
    with PdfPages(out) as pdf:
        for f in (s1, s2, s3, s4, s5, s6):
            f(pdf)
    print(f"wrote {out} · {NSLIDES} slides · basis month {NOW}")
    print("slides in", PNGDIR)


if __name__ == "__main__":
    main()
