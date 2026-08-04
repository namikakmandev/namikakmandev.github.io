#!/usr/bin/env python3
"""LinkedIn carousel for the pharma-share study -> notes/pharma-carousel.pdf

10 portrait slides (1080x1350, LinkedIn document format) in the study's dark
house style. Numbers are pulled from the data files, not retyped, so the
carousel can never drift from the page. Also drops each slide as a PNG in
assets/pharma-study/carousel/ for preview and single-image posting.
"""
import json, os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.ticker import FuncFormatter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PNGDIR = os.path.join(ROOT, "assets", "pharma-study", "carousel")
os.makedirs(PNGDIR, exist_ok=True)

SURFACE = "#0f1419"; CARD = "#151b22"; INK = "#f4f6f8"; INK2 = "#9aa3ad"
GRID = "#232a33"; MUTED = "#3d4654"
BLUE = "#3987e5"; GREEN = "#199e70"; ORANGE = "#d95926"; YELLOW = "#c98500"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "text.color": INK, "font.family": "DejaVu Sans",
})

share = json.load(open(os.path.join(ROOT, "data", "pharma-share.json")))["shares"]
stan = json.load(open(os.path.join(ROOT, "data", "pharma-share-stan.json")))["shares"]
mix = json.load(open(os.path.join(ROOT, "data", "pharma-product-mix.json")))

W, H = 7.2, 9.0          # 1080 x 1350 at dpi 150
pct = FuncFormatter(lambda v, _: f"{v:g}%")


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


def s1(pdf):
    fig = newslide()
    kicker(fig, "Data study")
    fig.text(0.08, 0.78, "The pharma", fontsize=46, fontweight="bold", va="top")
    fig.text(0.08, 0.70, "states", fontsize=46, fontweight="bold", va="top", color=BLUE)
    fig.text(0.08, 0.605,
             "How big is the pharmaceutical industry\ninside a national economy — and what\ndoes each country actually make?",
             fontsize=18, color=INK2, va="top", linespacing=1.5)
    for i, t in enumerate(["42 countries", "35 years", "Eurostat · OECD · trade"]):
        fig.text(0.08, 0.40 - i * 0.055, "•  " + t, fontsize=15, color=INK)
    fig.text(0.08, 0.15, "Swipe →", fontsize=15, color=BLUE, fontweight="bold")
    save(fig, pdf, 1)


def s2(pdf):
    fig = newslide()
    kicker(fig, "The frame")
    fig.text(0.08, 0.85, 'One number hides\nthree questions.', fontsize=30,
             fontweight="bold", va="top", linespacing=1.2)
    rows = [("How big?", "Pharma's share of the whole economy", BLUE),
            ("How concentrated?", "How much of one economy rides on it", GREEN),
            ("What kind?", "Biologics, pills, or raw ingredients", YELLOW)]
    for i, (h, sub, c) in enumerate(rows):
        y = 0.60 - i * 0.15
        fig.add_artist(plt.Line2D([0.08, 0.08], [y - 0.055, y + 0.02], color=c, lw=4))
        fig.text(0.13, y, h, fontsize=22, fontweight="bold", color=c, va="top")
        fig.text(0.13, y - 0.045, sub, fontsize=14.5, color=INK2, va="top")
    fig.text(0.08, 0.12, "Answer all three and the same industry looks\ncompletely different.",
             fontsize=14.5, color=INK2, linespacing=1.45)
    save(fig, pdf, 2)


def s3(pdf):
    fig = newslide()
    kicker(fig, "Surprise 1 · how big")
    fig.text(0.08, 0.87, "≈1%", fontsize=88, fontweight="bold", color=BLUE, va="top")
    fig.text(0.08, 0.66,
             "Every large economy holds pharma\nmanufacturing near 1% of GDP —\nand has for thirty years.",
             fontsize=20, va="top", linespacing=1.4)
    for i, (c, v) in enumerate([("United States", "0.87%"), ("United Kingdom", "0.95%"),
                                ("Japan", "0.66%"), ("Germany", "0.67%")]):
        y = 0.40 - i * 0.062
        fig.text(0.08, y, c, fontsize=16, color=INK2)
        fig.text(0.55, y, v, fontsize=16, color=INK, fontweight="bold")
    save(fig, pdf, 3)


def s4(pdf):
    fig = newslide()
    kicker(fig, "Thirty years, one band")
    fig.text(0.08, 0.90, "The big economies never move",
             fontsize=24, fontweight="bold", va="top")
    ax = fig.add_axes([0.11, 0.16, 0.82, 0.66])
    ax.set_facecolor(SURFACE)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=12)
    ax.grid(axis="y", color=GRID, lw=0.8)
    focus = [("USA", BLUE, "United States"), ("JPN", ORANGE, "Japan"),
             ("GBR", YELLOW, "United Kingdom"), ("KOR", GREEN, "South Korea")]
    for geo in ("CAN", "MEX", "AUS", "FRA", "ITA", "ESP", "DEU"):
        d = stan.get(geo) or {}
        if not d:
            continue
        ys = sorted(int(y) for y in d)
        ax.plot(ys, [d[str(y)]["share_gva"] for y in ys], color=MUTED, lw=1, alpha=.5)
    for geo, c, lab in focus:
        d = stan[geo]; ys = sorted(int(y) for y in d)
        vs = [d[str(y)]["share_gva"] for y in ys]
        ax.plot(ys, vs, color=c, lw=2.6)
        ax.annotate(f"{lab} {vs[-1]:.2f}%", (ys[-1], vs[-1]), xytext=(6, 0),
                    textcoords="offset points", color=c, fontsize=11,
                    fontweight="bold", va="center")
    ax.set_xlim(1990, 2032); ax.set_ylim(0, 1.4)
    ax.yaxis.set_major_formatter(pct)
    fig.text(0.08, 0.11, "Pharma value added ÷ total value added, 1990→. Grey: other economies.",
             fontsize=11.5, color=INK2)
    save(fig, pdf, 4)


def s5(pdf):
    fig = newslide()
    kicker(fig, "Surprise 2 · how concentrated", GREEN)
    fig.text(0.08, 0.88, "The exceptions\naren't big.", fontsize=32,
             fontweight="bold", va="top", linespacing=1.2)
    fig.text(0.08, 0.70, "They're small economies that let\none industry become the economy.",
             fontsize=18, color=INK2, va="top", linespacing=1.4)
    for i, (c, v, note) in enumerate([
            ("Ireland", "16.7%", "of the whole economy"),
            ("Denmark", "8.7%", "and ~49% of all manufacturing"),
            ("Switzerland", "6.7%", "")]):
        y = 0.50 - i * 0.135
        fig.text(0.08, y, v, fontsize=40, fontweight="bold", color=GREEN, va="top")
        fig.text(0.40, y - 0.008, c, fontsize=19, fontweight="bold", va="top")
        if note:
            fig.text(0.40, y - 0.052, note, fontsize=13, color=INK2, va="top")
    save(fig, pdf, 5)


def s6(pdf):
    fig = newslide()
    kicker(fig, "One country, one industry", GREEN)
    fig.text(0.08, 0.90, "Denmark: 0.8% → 8.7% of GDP",
             fontsize=23, fontweight="bold", va="top")
    ax = fig.add_axes([0.11, 0.16, 0.82, 0.66])
    ax.set_facecolor(SURFACE)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=12)
    ax.grid(axis="y", color=GRID, lw=0.8)
    for geo in share:
        if geo in ("DK", "CH", "IE", "SI", "BE"):
            continue
        d = share[geo]; ys = sorted(int(y) for y in d if int(y) >= 1995)
        vs = [d[str(y)]["share_gdp"] for y in ys]
        if len(ys) >= 20:
            ax.plot(ys, vs, color=MUTED, lw=1, alpha=.5)
    for geo, c, lab in [("DK", GREEN, "Denmark"), ("CH", ORANGE, "Switzerland")]:
        d = share[geo]; ys = sorted(int(y) for y in d if int(y) >= 1995)
        vs = [d[str(y)]["share_gdp"] for y in ys]
        ax.plot(ys, vs, color=c, lw=2.8)
        ax.annotate(f"{lab} {vs[-1]:.1f}%", (ys[-1], vs[-1]), xytext=(6, 0),
                    textcoords="offset points", color=c, fontsize=12,
                    fontweight="bold", va="center")
    ax.set_xlim(1995, 2032); ax.set_ylim(0, 9.6)
    ax.yaxis.set_major_formatter(pct)
    fig.text(0.08, 0.11, "Pharma ÷ GDP, 1995→2025. Grey: 25 other European countries.",
             fontsize=11.5, color=INK2)
    save(fig, pdf, 6)


def s7(pdf):
    fig = newslide()
    kicker(fig, "The paradox", ORANGE)
    fig.text(0.08, 0.86, "Same industry.\nSame €value.", fontsize=30,
             fontweight="bold", va="top", linespacing=1.2)
    fig.text(0.08, 0.68, "In 2023 Germany and Denmark each\nproduced ~€25bn of pharma.",
             fontsize=17.5, color=INK2, va="top", linespacing=1.4)
    box = [("Germany", "€26bn", "0.6% of GDP", "a rounding error", INK),
           ("Denmark", "€24bn", "6.5% of GDP", "the growth engine", GREEN)]
    for i, (c, e, p, note, col) in enumerate(box):
        y = 0.52 - i * 0.185
        fig.add_artist(plt.Rectangle((0.08, y - 0.13), 0.84, 0.15, transform=fig.transFigure,
                                     facecolor=CARD, edgecolor=GRID, lw=1))
        fig.text(0.11, y - 0.01, c, fontsize=18, fontweight="bold", va="top", color=col)
        fig.text(0.11, y - 0.06, e, fontsize=15, color=INK2, va="top")
        fig.text(0.55, y - 0.01, p, fontsize=22, fontweight="bold", color=col, va="top")
        fig.text(0.55, y - 0.065, note, fontsize=13.5, color=INK2, va="top")
    fig.text(0.08, 0.10, "Concentration, not pharma, is the phenomenon.",
             fontsize=15.5, color=INK, fontweight="bold")
    save(fig, pdf, 7)


def s8(pdf):
    fig = newslide()
    kicker(fig, "Surprise 3 · what kind", YELLOW)
    fig.text(0.08, 0.90, "Two industries hide\ninside “pharma”", fontsize=26,
             fontweight="bold", va="top", linespacing=1.2)
    ax = fig.add_axes([0.31, 0.16, 0.60, 0.55])
    ax.set_facecolor(SURFACE)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.tick_params(colors=INK2, labelsize=12, length=0)
    CLASSES = [("3002", "Biologics/vaccines", BLUE), ("3004", "Finished dose", GREEN),
               ("2937", "Hormones", YELLOW), ("2941", "Antibiotics", ORANGE),
               ("3003", "Bulk", MUTED)]
    geos = ["IE", "BE", "NL", "DE", "FR", "IT", "ES"]
    names = {"IE": "Ireland", "BE": "Belgium", "NL": "Netherlands", "DE": "Germany",
             "FR": "France", "IT": "Italy", "ES": "Spain"}
    data = mix["eu_exporters"]
    y = range(len(geos)); left = [0] * len(geos)
    for code, lab, c in CLASSES:
        w = [data[g]["mix_pct"][code] for g in geos]
        ax.barh(list(y), w, left=left, color=c, height=.66)
        for i, wi in enumerate(w):
            if wi >= 14:
                ax.annotate(f"{wi:.0f}", (left[i] + wi / 2, i), ha="center", va="center",
                            color="#0f1419" if code == "2937" else "#f4f6f8",
                            fontsize=10, fontweight="bold")
        left = [l + wi for l, wi in zip(left, w)]
    ax.set_yticks(list(y)); ax.set_yticklabels([names[g] for g in geos], fontsize=13)
    ax.invert_yaxis(); ax.set_xlim(0, 100); ax.set_xticks([])
    # horizontal legend strip above the chart, two rows of chips
    legend = [("Biologics/vaccines", BLUE, 0.08), ("Finished dose", GREEN, 0.45),
              ("Hormones", YELLOW, 0.08), ("Antibiotics", ORANGE, 0.45)]
    for i, (lab, c, x) in enumerate(legend):
        yy = 0.755 if i < 2 else 0.715
        fig.add_artist(plt.Rectangle((x, yy), 0.022, 0.024, transform=fig.transFigure, facecolor=c))
        fig.text(x + 0.032, yy + 0.012, lab, fontsize=12, color=INK2, va="center")
    fig.text(0.08, 0.115, "Biologics-led (Ireland, Belgium) vs finished-pill-led\n(France, Italy). Export mix by product class, 2024.",
             fontsize=11.5, color=INK2, linespacing=1.4)
    save(fig, pdf, 8)


def s9(pdf):
    fig = newslide()
    kicker(fig, "The kicker", BLUE)
    fig.text(0.08, 0.90, "97%", fontsize=64, fontweight="bold", color=BLUE, va="top")
    fig.text(0.34, 0.845, "of what South Korea now\nships to the EU is biologics",
             fontsize=17, va="top", linespacing=1.35)
    ax = fig.add_axes([0.11, 0.20, 0.82, 0.44])
    ax.set_facecolor(SURFACE)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=12)
    ax.grid(axis="y", color=GRID, lw=0.8)
    ex = json.load(open(os.path.join(ROOT, "data", "pharma-mirror.json")))["series"]
    P = ["3002", "3004", "3003", "2937", "2941"]
    ys = sorted(int(y) for y in ex["KR|3002"])
    vals = []
    for y in ys:
        tot = sum(ex.get(f"KR|{p}", {}).get(str(y), 0) for p in P)
        vals.append(100 * ex["KR|3002"].get(str(y), 0) / tot if tot else None)
    ax.plot(ys, vals, color=BLUE, lw=2.8)
    ax.fill_between(ys, vals, color=BLUE, alpha=.12)
    ax.set_xlim(2002, 2025); ax.set_ylim(0, 100); ax.yaxis.set_major_formatter(pct)
    fig.text(0.08, 0.135, "Up from under 20% in 2013 — Samsung Biologics and Celltrion",
             fontsize=13.5, color=INK, fontweight="bold")
    fig.text(0.08, 0.115, "coming online. A national bet, visible in customs data first.",
             fontsize=13.5, color=INK2)
    save(fig, pdf, 9)


def s10(pdf):
    fig = newslide()
    kicker(fig, "Takeaway")
    fig.text(0.08, 0.86, "Big. Concentrated.\nOr strategic.", fontsize=30,
             fontweight="bold", va="top", linespacing=1.2)
    fig.text(0.08, 0.68,
             "The same industry is a rounding error\nin one country, a national growth engine\nin another, and a bet on the future in a third.",
             fontsize=17, color=INK2, va="top", linespacing=1.45)
    fig.add_artist(plt.Rectangle((0.08, 0.30), 0.84, 0.20, transform=fig.transFigure,
                                 facecolor=CARD, edgecolor=GRID, lw=1))
    fig.add_artist(plt.Rectangle((0.11, 0.452), 0.028, 0.02, transform=fig.transFigure,
                                 facecolor=ORANGE))
    fig.text(0.15, 0.47, "Türkiye", fontsize=17, fontweight="bold", va="top")
    fig.text(0.11, 0.425, "0.35% of GDP, flat for two decades — while Korea, a fair\npeer, built biosimilar champions from a similar start.\nThe gap is strategy, not statistics.",
             fontsize=13.5, color=INK2, va="top", linespacing=1.4)
    fig.text(0.08, 0.20, "Full study · 42 countries · open data pipeline", fontsize=15,
             color=INK, fontweight="bold")
    fig.text(0.08, 0.165, "namikakmandev.github.io/pharma-gdp-share.html",
             fontsize=14, color=BLUE)
    fig.text(0.08, 0.11, "Follow for more data studies →", fontsize=13.5, color=INK2)
    save(fig, pdf, 10)


def main():
    out = os.path.join(ROOT, "notes", "pharma-carousel.pdf")
    with PdfPages(out) as pdf:
        for f in (s1, s2, s3, s4, s5, s6, s7, s8, s9, s10):
            f(pdf)
    print("wrote", out)
    print("slides in", PNGDIR)


if __name__ == "__main__":
    main()
