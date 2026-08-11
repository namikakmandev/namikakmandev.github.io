#!/usr/bin/env python3
"""LinkedIn carousel: vet-services inflation vs headline inflation
-> notes/vet-cpi-carousel.pdf + assets/vet-cpi-study/slide_NN.png

CONSUMER prices throughout: what households pay for veterinary and other pet
services (Eurostat HICP CP0935; US BLS "pet services including veterinary",
SS62031), against all-items inflation (CP00 / CPIAUCNS). Not farm animal
health costs.

Every figure is computed here from the committed data files, so a headline
cannot contradict the data:
    data/vet-cpi-eu.json   Eurostat prc_hicp_midx, monthly, 2015=100
    data/vet-cpi-us.json   BLS CPI via FRED, monthly, NSA

Scope decisions (stated on slide 6):
  - common window Jan 2021 -> Dec 2025 for every market on comparison slides
  - Ireland excluded: CP0935 stops at 2023-12
  - Türkiye excluded: reports only all-items HICP to Eurostat, no CP0935
  - the German step is the Nov 2022 veterinary fee schedule (GOT) revision,
    a regulatory repricing, not a data break
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.backends.backend_pdf import PdfPages

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PNGDIR = os.path.join(ROOT, "assets", "vet-cpi-study")
os.makedirs(PNGDIR, exist_ok=True)

SURFACE = "#0f1419"; INK = "#f4f6f8"; INK2 = "#9aa3ad"
GRID = "#232a33"; MUTED = "#3d4654"
BLUE = "#3987e5"; GREEN = "#199e70"; ORANGE = "#d95926"; YELLOW = "#c98500"
VIOLET = "#9085e9"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "text.color": INK, "font.family": "DejaVu Sans",
})

W, H = 7.2, 9.0
NSLIDES = 6
FRM, TO = "2021-01", "2025-12"          # common window, all comparison slides
FRM15 = "2015-01"                        # decade window, slide 4

EU = json.load(open(os.path.join(ROOT, "data", "vet-cpi-eu.json")))["series"]
US = json.load(open(os.path.join(ROOT, "data", "vet-cpi-us.json")))["series"]

NAMES = {"PL": "Poland", "SE": "Sweden", "DK": "Denmark", "HU": "Hungary",
         "CZ": "Czechia", "DE": "Germany", "NL": "Netherlands", "BE": "Belgium",
         "FI": "Finland", "US": "United States", "EA20": "Euro area",
         "FR": "France", "RO": "Romania", "PT": "Portugal", "ES": "Spain",
         "AT": "Austria", "IT": "Italy"}


def pct(series, frm, to):
    return (series[to] / series[frm] - 1) * 100


def window(geo, frm=FRM, to=TO):
    """(vet %, headline %) over the window; US comes from the FRED file."""
    if geo == "US":
        return pct(US["pet_svcs_nsa"], frm, to), pct(US["cpi_nsa"], frm, to)
    return pct(EU[f"{geo}|CP0935"], frm, to), pct(EU[f"{geo}|CP00"], frm, to)


ROWS = sorted(((g,) + window(g) for g in NAMES), key=lambda r: -(r[1] - r[2]))

DE_STEP = max((EU["DE|CP0935"][b] / EU["DE|CP0935"][a] - 1) * 100
              for a, b in zip(sorted(EU["DE|CP0935"]), sorted(EU["DE|CP0935"])[1:])
              if a >= "2019-01")
SE_STEP = max((EU["SE|CP0935"][b] / EU["SE|CP0935"][a] - 1) * 100
              for a, b in zip(sorted(EU["SE|CP0935"]), sorted(EU["SE|CP0935"])[1:])
              if a >= "2019-01")


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


def blank_ax(fig, rect):
    ax = fig.add_axes(rect)
    ax.set_facecolor(SURFACE)
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(False)
    return ax


def chip(ax, x, y, w, h, colour, alpha=1.0):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle="round,pad=0,rounding_size=0.09",
                                linewidth=0, facecolor=colour, alpha=alpha,
                                mutation_aspect=0.5))


def indexed(series, frm):
    keys = sorted(k for k in series if frm <= k <= TO)
    return keys, [series[k] / series[frm] * 100 for k in keys]


def xpos(keys):
    return [int(k[:4]) + (int(k[5:7]) - 1) / 12 for k in keys]


# ----------------------------------------------------------------- slides
def s1(pdf):
    """Cover: the hook is the split, not 'vet bills went up'."""
    pl_v, pl_c = window("PL")
    it_v, it_c = window("IT")
    fig = newslide()
    kicker(fig, "Vet bills vs inflation · 16 countries")
    fig.text(0.08, 0.870, "Your vet bill beat inflation.", fontsize=29,
             fontweight="bold", va="top")
    fig.text(0.08, 0.812, "Or did it?", fontsize=29, fontweight="bold",
             va="top", color=BLUE)
    fig.text(0.08, 0.730,
             "Prices of veterinary and other pet services versus\n"
             "all-items inflation, January 2021 to December 2025,\n"
             "in 15 European countries and the United States.",
             fontsize=15.5, va="top", linespacing=1.45)

    fig.text(0.08, 0.560, f"+{pl_v:.0f}%", fontsize=52, fontweight="bold",
             color=GREEN, va="top")
    fig.text(0.08, 0.478,
             f"vet services, Poland.\nHeadline was +{pl_c:.0f}%.",
             fontsize=15, va="top", linespacing=1.45)

    fig.text(0.55, 0.560, f"+{it_v:.0f}%", fontsize=52, fontweight="bold",
             color=ORANGE, va="top")
    fig.text(0.55, 0.478,
             f"vet services, Italy.\nHeadline was +{it_c:.0f}%.",
             fontsize=15, va="top", linespacing=1.45)

    fig.add_artist(plt.Line2D([0.08, 0.92], [0.380, 0.380], color=GRID, lw=1))
    fig.text(0.08, 0.335,
             "Same period, same measure. In the North and East vet\n"
             "prices ran far ahead of inflation; across the South they\n"
             "fell behind it. The split is the story — slides inside.",
             fontsize=14.5, va="top", linespacing=1.45)
    fig.text(0.08, 0.135,
             "Consumer prices — what pet owners pay. Not farm animal health\n"
             "costs. Sources and scope on the final slide.",
             fontsize=11, color=MUTED, va="top", linespacing=1.4)
    save(fig, pdf, 1)


def s2(pdf):
    """The main chart: gap in percentage points, every market, one window."""
    fig = newslide()
    kicker(fig, "The split · Jan 2021 → Dec 2025")
    fig.text(0.08, 0.895, "North and East: far ahead.\nSouth: behind inflation.",
             fontsize=24, fontweight="bold", va="top", linespacing=1.25)

    n = len(ROWS)
    ax = blank_ax(fig, [0.30, 0.145, 0.60, 0.63])
    ax.set_ylim(n - 0.5, -0.5)
    lo = min(r[1] - r[2] for r in ROWS); hi = max(r[1] - r[2] for r in ROWS)
    ax.set_xlim(lo - 3, hi + 8)
    ax.axvline(0, color=INK2, lw=1)
    for i, (g, v, c) in enumerate(ROWS):
        gap = v - c
        colour = GREEN if gap > 1 else (ORANGE if gap < -1 else INK2)
        if g in ("US", "EA20"):
            colour = VIOLET if g == "US" else MUTED
        ax.barh(i, gap, height=0.62, color=colour, zorder=3)
        ax.text(-0.4 if gap >= 0 else 0.4, i, NAMES[g],
                ha="right" if gap >= 0 else "left", va="center",
                fontsize=10.5, color=INK,
                fontweight="bold" if g == "US" else "normal")
        ax.text(gap + (0.5 if gap >= 0 else -0.5), i, f"{gap:+.0f}",
                ha="left" if gap >= 0 else "right", va="center",
                fontsize=10, color=colour, fontweight="bold")
    fig.text(0.08, 0.118,
             "Bar = vet-services inflation minus all-items inflation, in percentage\n"
             "points, per country, Jan 2021 → Dec 2025. Purple = United States.",
             fontsize=11, color=MUTED, va="top", linespacing=1.4)
    save(fig, pdf, 2)


def s3(pdf):
    """The jumps: Germany and Sweden repriced in a step, not a drift."""
    fig = newslide()
    kicker(fig, "How it happened")
    fig.text(0.08, 0.895, "Not a drift. Two jumps.", fontsize=27,
             fontweight="bold", va="top")

    ax = blank_ax(fig, [0.11, 0.30, 0.81, 0.50])
    for geo, colour, lw in (("EA20", MUTED, 1.6), ("SE", YELLOW, 2.4),
                            ("DE", BLUE, 2.4)):
        keys, vals = indexed(EU[f"{geo}|CP0935"], FRM)
        ax.plot(xpos(keys), vals, color=colour, lw=lw, solid_capstyle="round")
        ax.text(xpos(keys)[-1] + 0.06, vals[-1],
                {"EA20": "Euro area", "SE": "Sweden", "DE": "Germany"}[geo],
                color=colour, fontsize=11, fontweight="bold", va="center")
    ax.set_xlim(2021, 2026.9)
    ax.set_xticks([2021, 2022, 2023, 2024, 2025])
    ax.tick_params(colors=INK2, labelsize=10)
    for y in (100, 120, 140):
        ax.axhline(y, color=GRID, lw=0.8, zorder=0)
        ax.text(2021.02, y + 1, str(y), color=MUTED, fontsize=9)

    fig.text(0.08, 0.245,
             f"Germany: +{DE_STEP:.0f}% in a single month (Dec 2022), when the\n"
             "national veterinary fee schedule (GOT) was revised for the\n"
             f"first time since 1999. Sweden: +{SE_STEP:.0f}% in Oct 2022, as\n"
             "consolidated clinic chains repriced.",
             fontsize=14, va="top", linespacing=1.45)
    fig.text(0.08, 0.118,
             "Vet-services price index per market, Jan 2021 = 100, to Dec 2025.\n"
             "Regulated fee schedules move in steps — and reset the level for good.",
             fontsize=11, color=MUTED, va="top", linespacing=1.4)
    save(fig, pdf, 3)


def s4(pdf):
    """The US, a decade view — the famous story is mid-table."""
    us_v, us_c = window("US")
    us_v15, us_c15 = pct(US["pet_svcs_nsa"], FRM15, TO), pct(US["cpi_nsa"], FRM15, TO)
    fig = newslide()
    kicker(fig, "The United States · Jan 2015 → Dec 2025")
    fig.text(0.08, 0.895, "The loudest story\nis mid-table.", fontsize=27,
             fontweight="bold", va="top", linespacing=1.2)

    ax = blank_ax(fig, [0.11, 0.34, 0.81, 0.46])
    for key, colour, label in (("cpi_nsa", MUTED, "All items"),
                               ("pet_svcs_nsa", VIOLET, "Pet services\nincl. veterinary")):
        keys, vals = indexed(US[key], FRM15)
        ax.plot(xpos(keys), vals, color=colour, lw=2.4, solid_capstyle="round")
        ax.text(xpos(keys)[-1] + 0.15, vals[-1], label, color=colour,
                fontsize=11, fontweight="bold", va="center")
    ax.set_xlim(2015, 2028.4)
    ax.set_xticks([2015, 2017, 2019, 2021, 2023, 2025])
    ax.tick_params(colors=INK2, labelsize=10)
    for y in (100, 120, 140):
        ax.axhline(y, color=GRID, lw=0.8, zorder=0)
        ax.text(2015.05, y + 1, str(y), color=MUTED, fontsize=9)

    fig.text(0.08, 0.278,
             f"US pet services incl. veterinary: +{us_v15:.0f}% over the decade,\n"
             f"against +{us_c15:.0f}% for all items — ahead, but no Poland. Since\n"
             f"Jan 2021 the gap is {us_v - us_c:+.0f} points: less than Denmark's,\n"
             "Germany's or Sweden's.",
             fontsize=14, va="top", linespacing=1.45)
    fig.text(0.08, 0.118,
             "BLS CPI, US city average, not seasonally adjusted, Jan 2015 = 100.\n"
             "Same basket definition as the European series.",
             fontsize=11, color=MUTED, va="top", linespacing=1.4)
    save(fig, pdf, 4)


def s5(pdf):
    """Outcome slide: one instruction per reader, tied to what would change it."""
    fig = newslide()
    kicker(fig, "What to do with this")
    fig.text(0.08, 0.895, "Three readers, three moves.", fontsize=26,
             fontweight="bold", va="top")

    entries = [
        (GREEN, "Pet owners — budget by geography.",
         "In Poland, Sweden, Denmark or Germany, index your pet\n"
         "budget to vet prices, not to headline inflation — the gap\n"
         "has compounded to 14–32 points in five years."),
        (BLUE, "Insurers & clinic operators — watch the fee schedules.",
         "The big single moves were regulatory (Germany's GOT) or\n"
         "structural (Nordic chain consolidation). The next scheduled\n"
         "fee revision is the repricing event — not CPI drift."),
        (ORANGE, "Analysts — don't import the US narrative.",
         "Vet inflation is a country story, not a global one. Italy,\n"
         "Spain, Portugal and Austria sit below headline inflation.\n"
         "Check the local index before repeating the meme."),
    ]
    y = 0.800
    for colour, head, body in entries:
        fig.add_artist(plt.Line2D([0.08, 0.08], [y - 0.145, y - 0.005],
                                  color=colour, lw=3, solid_capstyle="round"))
        fig.text(0.105, y, head, fontsize=14.5, fontweight="bold", va="top",
                 color=colour)
        fig.text(0.105, y - 0.042, body, fontsize=13, va="top", linespacing=1.42)
        y -= 0.205

    fig.text(0.08, 0.155,
             "What would change this: a fee-schedule revision in a below-headline\n"
             "country, or a Southern-European consolidation wave, flips its lane.",
             fontsize=11, color=MUTED, va="top", linespacing=1.4)
    save(fig, pdf, 5)


def s6(pdf):
    """Scope, exclusions, sources — printed on the artefact itself."""
    fig = newslide()
    kicker(fig, "What this covers")
    fig.text(0.08, 0.895, "Scope and sources.", fontsize=27,
             fontweight="bold", va="top")

    blocks = [
        ("MEASURE", INK,
         "Consumer price indices: what households pay for veterinary\n"
         "and other pet services, versus all-items inflation. This is\n"
         "not farm animal health spending."),
        ("WINDOW", INK,
         "Jan 2021 → Dec 2025 on every comparison, all markets.\n"
         "The decade slide (US) is Jan 2015 → Dec 2025 and says so."),
        ("EXCLUDED", ORANGE,
         "Ireland — its vet-services index stops at Dec 2023.\n"
         "Türkiye — publishes only all-items HICP to Eurostat;\n"
         "a Turkish vet series would need TÜİK data."),
        ("KNOWN STEPS", YELLOW,
         f"Germany +{DE_STEP:.0f}% (Dec 2022, GOT fee-schedule revision) and\n"
         f"Sweden +{SE_STEP:.0f}% (Oct 2022) are real repricings, not data\n"
         "breaks. No methodology break spans the window."),
        ("SOURCES", INK,
         "Eurostat prc_hicp_midx, monthly, 2015=100: CP0935 veterinary\n"
         "and other services for pets; CP00 all items; 1996→2025.\n"
         "BLS CPI via FRED, monthly, NSA: CUUR0000SS62031 pet services\n"
         "incl. veterinary (1997→2026); CPIAUCNS all items.\n"
         "Data files: data/vet-cpi-eu.json · data/vet-cpi-us.json,\n"
         "cut 11 Aug 2026 — every figure recomputable from them."),
    ]
    y = 0.820
    for head, colour, body in blocks:
        fig.text(0.08, y, head, fontsize=11.5, fontweight="bold", color=INK2)
        fig.text(0.08, y - 0.026, body, fontsize=11.8, va="top",
                 linespacing=1.38, color=colour if colour != INK else INK)
        y -= 0.026 + 0.0215 * (body.count("\n") + 1) + 0.030

    fig.text(0.08, 0.095, "Personal analysis of public statistics. Views my own.",
             fontsize=11, color=MUTED)
    save(fig, pdf, 6)


def main():
    out = os.path.join(ROOT, "notes", "vet-cpi-carousel.pdf")
    with PdfPages(out) as pdf:
        for s in (s1, s2, s3, s4, s5, s6):
            s(pdf)
    print("wrote", out, "and PNGs in", PNGDIR)


if __name__ == "__main__":
    main()
