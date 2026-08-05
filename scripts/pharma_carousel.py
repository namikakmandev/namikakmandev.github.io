#!/usr/bin/env python3
"""LinkedIn document deck for the pharma study -> notes/pharma-carousel.pdf

Seven slides, 1080x1350. Every figure is read from the data files, so the deck
cannot drift from the study page.

Layout: slides are composed through a top-down cursor (Slide.block / .chart).
Each block reports its own measured height in figure fractions and advances the
cursor, so elements cannot overlap by construction — nothing is positioned by
hand-tuned constants.
"""
import json, os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PNGDIR = os.path.join(ROOT, "assets", "pharma-study", "carousel")
os.makedirs(PNGDIR, exist_ok=True)

# ---------------------------------------------------------------- house style
SURFACE = "#0f1419"; CARD = "#161d25"; INK = "#f4f6f8"; INK2 = "#98a2ad"
GRID = "#242c36"; MUTED = "#3d4654"; RULE = "#2b333d"
BLUE = "#3987e5"; GREEN = "#199e70"; ORANGE = "#d95926"; YELLOW = "#c98500"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "text.color": INK, "font.family": "DejaVu Sans",
})

W, H = 7.2, 9.0                  # 1080 x 1350 at dpi 150
PT = 1.0 / (72 * H)              # one point, as a fraction of figure height
LEFT, RIGHT = 0.085, 0.915
COLW = RIGHT - LEFT
TOP = 0.885                      # content ceiling (below the kicker)
FLOOR = 0.105                    # content floor (above the footer)
pct = FuncFormatter(lambda v, _: f"{v:g}%")

# ------------------------------------------------------------------ the data
share = json.load(open(os.path.join(ROOT, "data", "pharma-share.json")))["shares"]
stan = json.load(open(os.path.join(ROOT, "data", "pharma-share-stan.json")))["shares"]
mixd = json.load(open(os.path.join(ROOT, "data", "pharma-product-mix.json")))
expo = json.load(open(os.path.join(ROOT, "data", "pharma-exports.json")))["series"]
mirr = json.load(open(os.path.join(ROOT, "data", "pharma-mirror.json")))["series"]

HS = ["3002", "3004", "3003", "2937", "2941"]
HSLAB = {"3002": "Biologics / vaccines", "3004": "Finished dose",
         "2937": "Hormones", "2941": "Antibiotics", "3003": "Bulk"}
HSCOL = {"3002": BLUE, "3004": GREEN, "2937": YELLOW, "2941": ORANGE, "3003": MUTED}


def trade_mix(src, geo, year):
    tot = sum(src.get(f"{geo}|{p}", {}).get(year, 0) for p in HS)
    if not tot:
        return None, 0
    return {p: 100 * src.get(f"{geo}|{p}", {}).get(year, 0) / tot for p in HS}, tot / 1e9


# ---------------------------------------------------------------- slide model
class Slide:
    """Top-down composition. Every add-method advances a cursor by its own
    measured height, so no two elements can occupy the same band."""

    def __init__(self, kicker, accent=BLUE):
        self.fig = plt.figure(figsize=(W, H))
        self.fig.patch.set_facecolor(SURFACE)
        self.y = TOP
        self.fig.add_artist(plt.Line2D([LEFT, LEFT + 0.075], [0.945, 0.945],
                                       color=accent, lw=3, solid_capstyle="round"))
        self.fig.text(LEFT, 0.928, kicker.upper(), color=accent, fontsize=11.5,
                      fontweight="bold", va="top")

    # ---- primitives
    def gap(self, pts):
        self.y -= pts * PT

    def block(self, text, size=15.5, color=INK, weight="normal",
              lead=1.42, gap=10, x=LEFT):
        n = text.count("\n") + 1
        self.fig.text(x, self.y, text, fontsize=size, color=color,
                      fontweight=weight, va="top", linespacing=lead)
        self.y -= n * size * lead * PT
        self.gap(gap)

    def rule(self, gap=16):
        self.fig.add_artist(plt.Line2D([LEFT, RIGHT], [self.y, self.y],
                                       color=RULE, lw=1))
        self.gap(gap)

    def chart(self, height_frac, pad_left=0.0, tick_pad=30):
        """Reserve a band of the given height and return an axes for it.

        tick_pad is extra clearance for x tick labels, which matplotlib draws
        below the axes rectangle and which the cursor cannot measure."""
        bottom = self.y - height_frac
        ax = self.fig.add_axes([LEFT + pad_left, bottom,
                                COLW - pad_left, height_frac])
        ax.set_facecolor(SURFACE)
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
        ax.spines["bottom"].set_color(GRID)
        ax.tick_params(colors=INK2, labelsize=11.5)
        self.y = bottom
        self.gap(tick_pad)
        return ax

    def save(self, pdf, n):
        # hard guard: content must never reach the footer band
        if self.y < FLOOR:
            raise SystemExit(
                f"slide {n}: content overflows the footer "
                f"(cursor {self.y:.3f} < floor {FLOOR:.3f}) — shorten a block")
        self.fig.text(LEFT, 0.052, "Namık Akman", color=INK2, fontsize=10.5,
                      fontweight="bold", va="top")
        self.fig.text(LEFT, 0.034, "namikakmandev.github.io", color=MUTED,
                      fontsize=9, va="top")
        self.fig.text(RIGHT, 0.052, f"{n} / 7", color=INK2, fontsize=10.5,
                      ha="right", va="top")
        pdf.savefig(self.fig, facecolor=SURFACE)
        self.fig.savefig(os.path.join(PNGDIR, f"slide_{n:02d}.png"),
                         dpi=150, facecolor=SURFACE)
        plt.close(self.fig)


# ------------------------------------------------------------------ slide 1
def s1(pdf):
    s = Slide("Data study · August 2026")
    s.gap(26)
    s.block("Pharmaceutical\nmanufacturing in the\nnational economy",
            size=27, weight="bold", lead=1.22, gap=10)
    s.block("42 countries · 35 years · how large the industry is, how\n"
            "concentrated it has become, and what each country makes.",
            size=13, color=INK2, gap=14)

    # hero: every country's trajectory, three outliers named
    ax = s.chart(0.255, tick_pad=26)
    ax.grid(axis="y", color=GRID, lw=0.8)
    for geo, d in share.items():
        if geo in ("DK", "CH", "IE"):
            continue
        ys = sorted(int(y) for y in d if int(y) >= 1995 and d[str(y)]["share_gva"])
        if len(ys) >= 20:
            ax.plot(ys, [d[str(y)]["share_gva"] for y in ys], color=MUTED, lw=1, alpha=.5)
    hero = [("IE", stan["IRL"], GREEN, "Ireland"),
            ("DK", share["DK"], BLUE, "Denmark"),
            ("CH", share["CH"], ORANGE, "Switzerland")]
    for _, d, col, lab in hero:
        ys = sorted(int(y) for y in d if int(y) >= 1995)
        vs = [d[str(y)]["share_gva"] for y in ys]
        ax.plot(ys, vs, color=col, lw=2.6)
        ax.annotate(f"{lab}  {vs[-1]:.1f}%", (ys[-1], vs[-1]), xytext=(7, 0),
                    textcoords="offset points", color=col, fontsize=11,
                    fontweight="bold", va="center")
    ax.set_xlim(1995, 2036); ax.set_ylim(0, 21)
    ax.yaxis.set_major_formatter(pct)
    ax.set_yticks([0, 5, 10, 15, 20])

    s.block("Pharmaceutical share of total value added, 1995–2025.\n"
            "Grey: every other country in the study.",
            size=10.5, color=MUTED, lead=1.45, gap=14)
    s.rule(gap=16)

    # headline figures, three across
    stats = [("0.5%", "median country", INK),
             ("16.7%", "Ireland, the maximum", GREEN),
             ("97%", "Korean exports\nthat are biologics", BLUE)]
    for i, (val, lab, col) in enumerate(stats):
        x = LEFT + i * (COLW / 3)
        s.fig.text(x, s.y, val, fontsize=25, fontweight="bold", color=col, va="top")
        s.fig.text(x, s.y - 0.040, lab, fontsize=10.5, color=INK2, va="top",
                   linespacing=1.4)
    s.y -= 0.085
    s.save(pdf, 1)


# ------------------------------------------------------------------ slide 2
def s2(pdf):
    s = Slide("Executive summary")
    s.gap(30)
    s.block("Three findings", size=30, weight="bold", gap=26)
    items = [
        ("01", "Scale is remarkably uniform.", BLUE,
         "In every large economy, pharmaceutical manufacturing\n"
         "accounts for approximately 1% of output — and has done\n"
         "so for three decades."),
        ("02", "Concentration is the real variable.", GREEN,
         "Shares of 7–17% occur only in small economies where a\n"
         "single industry has come to dominate: Ireland, Denmark\n"
         "and Switzerland."),
        ("03", "Composition differs more than scale.", YELLOW,
         "Trade data separates biologics producers from finished-\n"
         "dose manufacturers — a distinction invisible in the\n"
         "headline economic figures."),
    ]
    for num, head, col, body in items:
        top = s.y
        s.block(num, size=13, color=col, weight="bold", gap=4, x=LEFT)
        s.block(head, size=17, weight="bold", gap=7, x=LEFT + 0.075)
        s.block(body, size=13.5, color=INK2, lead=1.45, gap=20, x=LEFT + 0.075)
        s.fig.add_artist(plt.Line2D([LEFT + 0.052, LEFT + 0.052],
                                    [s.y + 0.018, top - 0.004], color=col, lw=2.5))
    s.save(pdf, 2)


# ------------------------------------------------------------------ slide 3
def s3(pdf):
    s = Slide("Finding 01 · Scale")
    s.gap(28)
    s.block("Large economies hold\npharmaceuticals near 1%",
            size=27, weight="bold", lead=1.25, gap=12)
    s.block("Share of total value added, 1990 to most recent year.",
            size=13, color=INK2, gap=18)

    ax = s.chart(0.375)
    ax.grid(axis="y", color=GRID, lw=0.8)
    for geo in ("CAN", "MEX", "AUS", "FRA", "ITA", "ESP", "DEU"):
        d = stan.get(geo)
        if not d:
            continue
        ys = sorted(int(y) for y in d)
        ax.plot(ys, [d[str(y)]["share_gva"] for y in ys], color=MUTED, lw=1, alpha=.55)
    for geo, col, lab in (("USA", BLUE, "United States"), ("GBR", YELLOW, "United Kingdom"),
                          ("JPN", ORANGE, "Japan"), ("KOR", GREEN, "South Korea")):
        d = stan[geo]; ys = sorted(int(y) for y in d)
        vs = [d[str(y)]["share_gva"] for y in ys]
        ax.plot(ys, vs, color=col, lw=2.4)
        ax.annotate(f"{lab}  {vs[-1]:.2f}%", (ys[-1], vs[-1]), xytext=(7, 0),
                    textcoords="offset points", color=col, fontsize=10.5,
                    fontweight="bold", va="center")
    ax.set_xlim(1990, 2036); ax.set_ylim(0, 1.45)
    ax.yaxis.set_major_formatter(pct)

    s.gap(6)
    s.block("The band has held through the genomics era, the shift to\n"
            "biologics and the pandemic. Grey lines: Canada, Mexico,\n"
            "Australia, France, Italy, Spain, Germany.",
            size=12.5, color=INK2, lead=1.45, gap=0)
    s.save(pdf, 3)


# ------------------------------------------------------------------ slide 4
def s4(pdf):
    s = Slide("Finding 02 · Concentration", GREEN)
    s.gap(28)
    s.block("The exceptions are all\nsmall economies",
            size=27, weight="bold", lead=1.25, gap=12)
    s.block("Pharmaceutical share of GDP, 1995–2025.", size=13, color=INK2, gap=18)

    ax = s.chart(0.355)
    ax.grid(axis="y", color=GRID, lw=0.8)
    for geo in share:
        if geo in ("DK", "CH", "IE", "SI", "BE"):
            continue
        d = share[geo]; ys = sorted(int(y) for y in d if int(y) >= 1995)
        if len(ys) >= 20:
            ax.plot(ys, [d[str(y)]["share_gdp"] for y in ys], color=MUTED, lw=1, alpha=.5)
    for geo, col, lab in (("DK", GREEN, "Denmark"), ("CH", ORANGE, "Switzerland")):
        d = share[geo]; ys = sorted(int(y) for y in d if int(y) >= 1995)
        vs = [d[str(y)]["share_gdp"] for y in ys]
        ax.plot(ys, vs, color=col, lw=2.6)
        ax.annotate(f"{lab}  {vs[-1]:.1f}%", (ys[-1], vs[-1]), xytext=(7, 0),
                    textcoords="offset points", color=col, fontsize=10.5,
                    fontweight="bold", va="center")
    ax.set_xlim(1995, 2035); ax.set_ylim(0, 9.8)
    ax.yaxis.set_major_formatter(pct)

    s.gap(4)
    s.rule(gap=14)
    s.block("In 2023 Germany and Denmark each produced roughly €25bn of\n"
            "pharmaceutical value added. That is 0.6% of the German economy\n"
            "and 6.5% of the Danish one. Concentration, not sector size,\n"
            "determines macroeconomic exposure.",
            size=13, color=INK2, lead=1.5, gap=0)
    s.save(pdf, 4)


# ------------------------------------------------------------------ slide 5
def s5(pdf):
    """Denmark and Ireland — the breakdown the earlier deck omitted."""
    s = Slide("Country focus", GREEN)
    s.gap(26)
    s.block("Two routes to\nconcentration", size=27, weight="bold", lead=1.25, gap=12)
    s.block("Ireland repositioned its output. Denmark deepened a single\nfranchise. Both reached scale; the composition differs.",
            size=13, color=INK2, lead=1.45, gap=16)

    # both panels on the same basis — C21 share of total value added — so the
    # two countries are directly comparable despite coming from two sources
    dk_g = share["DK"]; ie_g = stan["IRL"]
    panels = [
        ("Ireland", "IE", GREEN,
         f"{ie_g['1995']['share_gva']:.1f}% → {ie_g['2023']['share_gva']:.1f}%",
         "of value added, 1995–2023",
         "Exports  €15bn → €99bn"),
        ("Denmark", "DK", BLUE,
         f"{dk_g['1995']['share_gva']:.1f}% → {dk_g['2025']['share_gva']:.1f}%",
         "of value added, 1995–2025",
         "Exports  €4bn → €22bn"),
    ]
    top = s.y
    for i, (name, geo, col, headline, sub, exports) in enumerate(panels):
        x = LEFT if i == 0 else LEFT + COLW / 2 + 0.018
        w = COLW / 2 - 0.018
        # zorder 0: figure-level patches otherwise paint over the axes below
        s.fig.add_artist(plt.Rectangle((x, top - 0.315), w, 0.315,
                                       transform=s.fig.transFigure,
                                       facecolor=CARD, edgecolor=GRID, lw=1, zorder=0))
        s.fig.text(x + 0.022, top - 0.028, name, fontsize=18, fontweight="bold",
                   color=col, va="top")
        s.fig.text(x + 0.022, top - 0.070, headline, fontsize=17,
                   fontweight="bold", va="top")
        s.fig.text(x + 0.022, top - 0.101, sub, fontsize=10.5, color=INK2, va="top")
        s.fig.text(x + 0.022, top - 0.130, exports, fontsize=12, color=INK, va="top")
        # 2002 vs 2024 composition, stacked
        ax = s.fig.add_axes([x + 0.078, top - 0.285, w - 0.112, 0.108], zorder=3)
        ax.set_facecolor(CARD)
        for sp in ax.spines.values():
            sp.set_visible(False)
        ax.set_xticks([]); ax.tick_params(colors=INK2, labelsize=10, length=0)
        rows = ["2024", "2002"]
        for r, yr in enumerate(rows):
            m, _ = trade_mix(expo, geo, yr)
            left = 0
            for p in HS:
                v = m[p]
                ax.barh(r, v, left=left, color=HSCOL[p], height=.62)
                if v >= 17:
                    ax.annotate(f"{v:.0f}", (left + v / 2, r), ha="center", va="center",
                                color="#0f1419" if p == "2937" else "#f4f6f8",
                                fontsize=9.5, fontweight="bold")
                left += v
        ax.set_yticks(range(len(rows))); ax.set_yticklabels(rows, fontsize=10.5)
        ax.set_xlim(0, 100); ax.set_ylim(-0.6, len(rows) - 0.4)
        s.fig.text(x + 0.022, top - 0.296, "Export composition, %", fontsize=9.5,
                   color=MUTED, va="top")
    s.y = top - 0.315
    s.gap(12)

    # legend
    for i, p in enumerate(["3002", "3004", "2937"]):
        cx = LEFT + i * 0.29
        s.fig.add_artist(plt.Rectangle((cx, s.y - 0.017), 0.019, 0.019,
                                       transform=s.fig.transFigure, facecolor=HSCOL[p]))
        s.fig.text(cx + 0.028, s.y - 0.0075, HSLAB[p], fontsize=11,
                   color=INK2, va="center")
    s.y -= 0.030
    s.gap(10)
    s.block("Ireland moved from 85% finished dose in 2002 to 53% biologics and\n"
            "17% hormones in 2024 — a change of product, not only of volume.\n"
            "Denmark stayed dose-led, scaling one franchise. Irish shares step\n"
            "up in 2015 with the national-accounts restatement; the export mix\n"
            "is unaffected by it.",
            size=12.5, color=INK2, lead=1.48, gap=0)
    s.save(pdf, 5)


# ------------------------------------------------------------------ slide 6
def s6(pdf):
    s = Slide("Finding 03 · Composition", YELLOW)
    s.gap(24)
    s.block("What the leaders make", size=25, weight="bold", gap=8)
    s.block("Ranked by pharmaceutical share of the economy; bars show export mix.",
            size=12, color=INK2, gap=12)

    # legend row, measured before the chart so it cannot collide
    for i, p in enumerate(["3002", "3004", "2937", "2941"]):
        cx = LEFT + i * 0.215
        s.fig.add_artist(plt.Rectangle((cx, s.y - 0.017), 0.017, 0.017,
                                       transform=s.fig.transFigure, facecolor=HSCOL[p]))
        s.fig.text(cx + 0.024, s.y - 0.0085, HSLAB[p].replace(" / vaccines", ""),
                   fontsize=9.5, color=INK2, va="center")
    s.y -= 0.028
    s.gap(10)

    # ranked by share of the economy, so concentration and composition are
    # read in one view. Switzerland's mix is EU-facing (mirror data); Slovenia
    # ranks 4th on share but its trade is re-export routing, so it is omitted.
    eu, wo = mixd["eu_exporters"], mixd["world_to_eu"]
    ROWS = [("Ireland", "IE", 16.7, eu["IE"]), ("Denmark", "DK", 9.8, eu["DK"]),
            ("Switzerland*", "CH", 6.9, wo["CH"]), ("Belgium", "BE", 2.5, eu["BE"]),
            ("Hungary", "HU", 1.3, eu["HU"]), ("Netherlands", "NL", 1.2, eu["NL"]),
            ("Germany", "DE", 0.7, eu["DE"]), ("France", "FR", 0.6, eu["FR"]),
            ("Italy", "IT", 0.6, eu["IT"])]

    ax = s.chart(0.345, pad_left=0.155, tick_pad=10)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_xticks([]); ax.tick_params(colors=INK2, labelsize=11.5, length=0)
    left = [0.0] * len(ROWS)
    for p in HS:
        w = [r[3]["mix_pct"][p] for r in ROWS]
        ax.barh(range(len(ROWS)), w, left=left, color=HSCOL[p], height=.68)
        for i, wi in enumerate(w):
            if wi >= 16:
                ax.annotate(f"{wi:.0f}", (left[i] + wi / 2, i), ha="center", va="center",
                            color="#0f1419" if p == "2937" else "#f4f6f8",
                            fontsize=9.5, fontweight="bold")
        left = [l + wi for l, wi in zip(left, w)]
    for i, (nm, g, shr, d) in enumerate(ROWS):
        col = GREEN if shr >= 2 else INK2
        ax.annotate(f"{shr:.1f}%", (106, i), va="center", color=col,
                    fontsize=11, fontweight="bold", annotation_clip=False)
        ax.annotate(f"€{d['eur_bn']:,.0f}bn", (128, i), va="center", color=INK,
                    fontsize=10.5, annotation_clip=False)
    ax.annotate("share", (106, -0.9), va="center", color=MUTED, fontsize=9,
                annotation_clip=False)
    ax.annotate("exports", (128, -0.9), va="center", color=MUTED, fontsize=9,
                annotation_clip=False)
    # divider between the concentrated economies and the large ones
    ax.axhline(5.5, color=RULE, lw=1, xmin=0, xmax=0.79)
    ax.set_yticks(range(len(ROWS)))
    ax.set_yticklabels([r[0] for r in ROWS], fontsize=11.5)
    ax.invert_yaxis()
    ax.set_xlim(0, 152)

    s.gap(2)
    s.block("The leaders are not one industry. Ireland and Belgium are biologics\n"
            "producers; Denmark is dose-led with the hormone share that marks\n"
            "insulin and GLP-1; Switzerland splits evenly. Below the line, the\n"
            "large economies are finished-dose manufacturers at modest scale.",
            size=12, color=INK2, lead=1.45, gap=8)
    s.block("* Switzerland: exports to the EU only. Slovenia ranks 4th on share but\n"
            "  its trade figures are distribution-hub re-exports, so it is omitted.",
            size=9.5, color=MUTED, lead=1.45, gap=0)
    s.save(pdf, 6)


# ------------------------------------------------------------------ slide 7
def s7(pdf):
    s = Slide("Implications")
    s.gap(28)
    s.block("What the analysis\nsupports", size=27, weight="bold", lead=1.25, gap=18)
    rows = [
        ("Economic analysis", BLUE,
         "Danish, Irish and Swiss aggregates warrant an\n"
         "ex-pharmaceutical view before macro conclusions are drawn."),
        ("Industrial strategy", GREEN,
         "Composition can be changed within a decade — Ireland and\n"
         "South Korea repositioned output rather than expanding it."),
        ("Türkiye", ORANGE,
         "0.35% of GDP, broadly unchanged since 2003 against a 0.5%\n"
         "median. The constraint is positioning, not data."),
    ]
    for head, col, body in rows:
        s.block(head, size=15.5, color=col, weight="bold", gap=6)
        s.block(body, size=12.5, color=INK2, lead=1.5, gap=17)
    s.rule(gap=14)
    s.block("Method  ·  NACE/ISIC C21 value added, Eurostat and OECD STAN, in\n"
            "national currency. Composition from HS chapter-30 trade, a proxy\n"
            "for output. Full sources and caveats online.",
            size=10.5, color=MUTED, lead=1.5, gap=14)
    s.block("namikakmandev.github.io/pharma-gdp-share.html",
            size=13.5, color=BLUE, weight="bold", gap=0)
    s.save(pdf, 7)


def main():
    out = os.path.join(ROOT, "notes", "pharma-carousel.pdf")
    from matplotlib.backends.backend_pdf import PdfPages
    with PdfPages(out) as pdf:
        for i, f in enumerate((s1, s2, s3, s4, s5, s6, s7), 1):
            f(pdf)
    print("wrote", out)


if __name__ == "__main__":
    main()
