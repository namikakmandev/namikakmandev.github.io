#!/usr/bin/env python3
"""LinkedIn carousel: the GLP-1 molecule landscape -> notes/glp1-molecules-carousel.pdf

Option A. A science deck, not a markets deck: NO share prices, NO valuation, NO
company names, NO trade names. Subject is the molecules — receptor targets, stage
and indication. For an author employed in the pharmaceutical industry this removes
securities commentary and competitor commentary entirely.

Built around three graphics rather than text lists:
  slide 2  receptor matrix     — which molecule hits which receptor
  slide 3  pipeline by stage   — where each one stands
  slide 4  weight loss         — the two oral candidates, cross-trial caveat shown
  slide 5  indication map      — the biology spreading beyond obesity

6 portrait slides (1080x1350), same house style as scripts/glp1_carousel.py.

These facts cannot be computed from a price file, so each is stated here against
its source:

  [1] Structure Therapeutics 10-Q, FY2026 Q1 (7 May 2026) — aleniglipron
      (GSBR-1290) is "an oral small molecule selective glucagon-like-peptide-1
      receptor agonist currently in five ongoing clinical studies for the
      treatment of obesity, overweight and related conditions"; also two oral
      amylin receptor agonists, ACCG-2671 (Phase 1) and ACCG-3535.
  [2] Structure Therapeutics release (5 Jun 2026) — Phase 2b ACCESS published in
      Nature Medicine; weight loss "up to 16.2% during the open-label extension";
      "overall low (10.4%) discontinuation rate"; Phase 3 on track for Q3 2026.
  [3] Altimmune 8-K (28 Jul 2026) — pemvidutide is a "balanced 1:1
      glucagon/GLP-1 dual receptor agonist" for MASH, alcohol use disorder and
      alcohol-associated liver disease; FDA Fast Track for MASH and AUD, plus
      Breakthrough Therapy Designation for MASH.
  [4] Altimmune release (3 Aug 2026) — Phase 3 PERFORMA in MASH began enrolling,
      about 1,790 patients across two cohorts, 52-week data expected 2029.
  [5] Regulatory news (15 Jul 2026) — EU marketing authorisation for oral
      semaglutide for weight management, the first GLP-1 receptor agonist in
      tablet form for that use in the EU, and the fifth such authorisation after
      the US, UK, UAE and Bahrain; in the Phase 3b OASIS 4 trial once-daily oral
      semaglutide 25 mg showed about 17% weight loss versus 3% for placebo.
  [6] Industry landscape review (28 Jul 2026) — NDA filed for once-weekly
      cagrilintide 2.4 mg + semaglutide 2.4 mg, which "would become the first
      injectable GLP-1 receptor agonist and amylin analogue combination
      treatment"; petrelintide (an amylin analogue) Phase 2 topline in 493 people
      with overweight and obesity (Mar 2026); ACCG-2671 Phase 1 initiated
      (Dec 2025).
  [7] Sector review (3 Aug 2026) — zenagamtide (formerly amycretin), a
      long-acting GLP-1 and amylin receptor agonist, in Phase 3; a decision on the
      cagrilintide + semaglutide filing expected in Q4.
  [8] Competitor 10-Q (6 Aug 2026) — "There are currently two FDA-approved
      treatments for MASH": a THR-beta agonist and semaglutide. Approved obesity
      treatments comprise GLP-1 receptor agonists such as semaglutide and dual
      agonists such as tirzepatide.
  [9] Clarivate commentary (5 Aug 2026) — US GLP-1 receptor agonist prescriptions
      rose 587% from 2019 to 2024; obesity rates on track to exceed 50% by 2030.
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.backends.backend_pdf import PdfPages

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PNGDIR = os.path.join(ROOT, "assets", "glp1-study", "molecules")
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

RECEPTORS = ["GLP-1", "GIP", "amylin", "glucagon"]
RCOLOUR = {"GLP-1": BLUE, "GIP": GREEN, "amylin": YELLOW, "glucagon": ORANGE}

# molecule, receptors hit, stage, stage index (0=Ph1 .. 4=Approved), source
MOLECULES = [
    ("semaglutide",                ["GLP-1"],               "Approved", 4, "[8]"),
    ("tirzepatide",                ["GLP-1", "GIP"],        "Approved", 4, "[8]"),
    ("cagrilintide + semaglutide", ["GLP-1", "amylin"],     "Filed",    3, "[6][7]"),
    ("aleniglipron",               ["GLP-1"],               "Phase 3",  2, "[1][2]"),
    ("pemvidutide",                ["GLP-1", "glucagon"],   "Phase 3",  2, "[3][4]"),
    ("zenagamtide",                ["GLP-1", "amylin"],     "Phase 3",  2, "[7]"),
    ("petrelintide",               ["amylin"],              "Phase 2",  1, "[6]"),
    ("ACCG-2671",                  ["amylin"],              "Phase 1",  0, "[1][6]"),
]
STAGES = ["Phase 1", "Phase 2", "Phase 3", "Filed", "Approved"]
STAGE_COLOUR = [ORANGE, YELLOW, BLUE, VIOLET, GREEN]

N_TOTAL = len(MOLECULES)
N_STAGE = [sum(1 for _, _, _, si, _ in MOLECULES if si == i) for i in range(len(STAGES))]
N_APPROVED = N_STAGE[4]
N_PENDING = N_TOTAL - N_APPROVED
WORD = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six",
        7: "Seven", 8: "Eight", 9: "Nine", 10: "Ten"}

# indication, molecules, colour — approval status noted in the label
INDICATIONS = [
    ("Obesity /\noverweight", GREEN,
     ["semaglutide", "tirzepatide", "cagrilintide + semaglutide",
      "aleniglipron", "zenagamtide", "petrelintide", "ACCG-2671"]),
    ("Liver disease\n(MASH)", YELLOW, ["semaglutide", "pemvidutide"]),
    ("Alcohol use\ndisorder", ORANGE, ["pemvidutide"]),
]


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


# ----------------------------------------------------------------- slides
def s1(pdf):
    """Cover. Plain language first: what these drugs are, then how far along."""
    fig = newslide()
    kicker(fig, "GLP-1 · the molecules")
    fig.text(0.08, 0.870, f"{WORD[N_TOTAL]} molecules.", fontsize=35,
             fontweight="bold", va="top")
    fig.text(0.08, 0.800, f"{WORD[N_APPROVED]} have arrived.", fontsize=35,
             fontweight="bold", va="top", color=BLUE)
    approved = [m for m, _, _, si, _ in MOLECULES if si == 4]
    fig.text(0.08, 0.712,
             "GLP-1 medicines copy the gut hormones that tell the\n"
             f"body it has eaten. {WORD[N_APPROVED]} are approved for obesity:\n"
             f"{' and '.join(approved)}. {WORD[N_PENDING]} more are in trials.",
             fontsize=16, va="top", linespacing=1.45)

    # one square per molecule, grouped and coloured by how far it has got
    ax = blank_ax(fig, [0.08, 0.470, 0.84, 0.115])
    ax.set_xlim(0, N_TOTAL); ax.set_ylim(0, 1)
    x = 0
    for i, st in enumerate(STAGES):
        n = N_STAGE[i]
        if not n:
            continue
        for k in range(n):
            chip(ax, x + k + 0.06, 0.52, 0.88, 0.40, STAGE_COLOUR[i])
        short = st.replace("Phase ", "Ph ")
        ax.text(x + n / 2, 0.30, f"{short} · {n}", ha="center", va="top",
                fontsize=10.5, color=INK2, fontweight="bold")
        x += n
    ax.text(N_TOTAL / 2, 0.03, "one square = one molecule", ha="center",
            fontsize=10, color=MUTED)

    fig.text(0.08, 0.408, "587%", fontsize=58, fontweight="bold",
             color=GREEN, va="top")
    fig.text(0.08, 0.315,
             "growth in US prescriptions for these\nmedicines between 2019 and 2024.",
             fontsize=15.5, va="top", linespacing=1.45)
    fig.add_artist(plt.Line2D([0.08, 0.92], [0.232, 0.232], color=GRID, lw=1))
    fig.text(0.08, 0.192,
             "What follows: what each molecule targets, how far\nit has got, and which diseases it is aimed at.",
             fontsize=14.5, va="top", linespacing=1.42, color=INK)
    fig.text(0.08, 0.100,
             "No trade names, companies or share prices. Sources on the final slide.",
             fontsize=11, color=MUTED)
    save(fig, pdf, 1)


def s2(pdf):
    """Receptor matrix: the single most informative graphic in the deck."""
    fig = newslide()
    kicker(fig, "How they work")
    fig.text(0.08, 0.895, "One target became four.", fontsize=27,
             fontweight="bold", va="top")

    n = len(MOLECULES)
    ax = blank_ax(fig, [0.40, 0.235, 0.52, 0.60])
    ax.set_xlim(-0.5, len(RECEPTORS) - 0.5)
    ax.set_ylim(n - 0.5, -1.3)                     # header row above the grid

    for j, r in enumerate(RECEPTORS):              # column heads
        ax.text(j, -0.95, r, ha="center", va="center", fontsize=11,
                fontweight="bold", color=RCOLOUR[r], rotation=0)
    for i in range(n):                             # faint row rules
        ax.plot([-0.5, len(RECEPTORS) - 0.5], [i + 0.5, i + 0.5],
                color=GRID, lw=0.8, zorder=0)

    for i, (mol, hits, stage, si, _) in enumerate(MOLECULES):
        ax.text(-0.72, i, mol, ha="right", va="center", fontsize=12,
                fontweight="bold", color=INK, transform=ax.transData)
        for j, r in enumerate(RECEPTORS):
            if r in hits:
                ax.scatter([j], [i], s=200, color=RCOLOUR[r], zorder=3)
            else:
                ax.scatter([j], [i], s=44, color=GRID, zorder=2)

    fig.text(0.08, 0.196,
             "The first medicines hit one receptor. The newer ones pair\nGLP-1 with a second — to add effects, not just dose harder.",
             fontsize=14.5, va="top", linespacing=1.42)
    fig.text(0.08, 0.086,
             "A filled dot means the molecule targets that receptor.",
             fontsize=11, color=MUTED)
    save(fig, pdf, 2)


def s3(pdf):
    """Pipeline by stage."""
    fig = newslide()
    kicker(fig, "Where each one stands")
    fig.text(0.08, 0.895, f"{WORD[N_APPROVED]} on the market.\n{WORD[N_PENDING]} behind them.",
             fontsize=28, fontweight="bold", va="top", linespacing=1.2)

    ax = blank_ax(fig, [0.08, 0.255, 0.84, 0.545])
    ax.set_xlim(-0.6, 4.6); ax.set_ylim(-0.4, 3.5)

    # stage columns
    for i, st in enumerate(STAGES):
        chip(ax, i - 0.44, 3.06, 0.88, 0.30, STAGE_COLOUR[i], alpha=0.9)
        ax.text(i, 3.21, st, ha="center", va="center", fontsize=10.5,
                fontweight="bold",
                color="#0f1419" if STAGE_COLOUR[i] in (YELLOW, GREEN) else "#ffffff")
        ax.plot([i, i], [-0.35, 2.92], color=GRID, lw=0.9, zorder=0)

    # molecules stacked within their stage column
    by_stage = {}
    for mol, hits, stage, si, _ in MOLECULES:
        by_stage.setdefault(si, []).append((mol, hits))
    for si, items in by_stage.items():
        for k, (mol, hits) in enumerate(items):
            y = 2.45 - k * 0.72
            ax.scatter([si], [y], s=150, color=STAGE_COLOUR[si], zorder=3)
            short = mol.replace("cagrilintide + semaglutide", "cagrilintide\n+ semaglutide")
            ax.text(si, y - 0.20, short, ha="center", va="top", fontsize=9.6,
                    color=INK, fontweight="bold", linespacing=1.25)
            ax.text(si, y - 0.20 - (0.30 if "\n" in short else 0.14),
                    " · ".join(hits), ha="center", va="top", fontsize=8.2, color=INK2)

    fig.text(0.08, 0.212,
             "Only two mechanisms have reached patients. Everything\nelse — oral formats, combinations, new receptors — is\nstill being tested.",
             fontsize=14.5, va="top", linespacing=1.42)
    fig.text(0.08, 0.098,
             "Stage as at August 2026. Development stages change; several readouts are due.",
             fontsize=11, color=MUTED)
    save(fig, pdf, 3)


def s4(pdf):
    """The oral shift, with weight-loss figures and the cross-trial caveat."""
    fig = newslide()
    kicker(fig, "The shift to a tablet")
    fig.text(0.08, 0.895, "The next contest\nis oral.", fontsize=29,
             fontweight="bold", va="top", linespacing=1.2)

    bars = [("oral semaglutide\n25 mg", 17.0, GREEN, "peptide, tablet · approved"),
            ("aleniglipron", 16.2, BLUE, "small molecule · Phase 3"),
            ("placebo", 3.0, MUTED, "same trial as the first bar")]
    ax = fig.add_axes([0.30, 0.365, 0.62, 0.40])
    ax.set_facecolor(SURFACE)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=10.5)
    ax.grid(axis="x", color=GRID, lw=0.8)
    ax.barh(range(len(bars)), [b[1] for b in bars],
            color=[b[2] for b in bars], height=0.52)
    ax.set_yticks(range(len(bars))); ax.set_yticklabels([])
    ax.invert_yaxis()
    tr = ax.get_yaxis_transform()
    for i, (lab, v, c, sub) in enumerate(bars):
        ax.text(-0.04, i - (0.16 if "\n" in lab else 0.09), lab, transform=tr,
                ha="right", va="center", fontsize=11.5, fontweight="bold",
                color=INK, linespacing=1.2)
        ax.text(-0.04, i + (0.26 if "\n" in lab else 0.20), sub, transform=tr,
                ha="right", va="center", fontsize=8.6, color=INK2)
        ax.annotate(f"{v:.1f}%", (v, i), xytext=(7, 0), textcoords="offset points",
                    va="center", fontsize=13, fontweight="bold", color=INK)
    ax.set_xlim(0, 21)
    ax.set_xlabel("Weight loss reported in trials  (%)", fontsize=10.5,
                  color=INK2, labelpad=8)

    fig.text(0.08, 0.315,
             "A tablet changes who can realistically be treated, not\njust how much weight comes off. One is a peptide in\ntablet form; the other a small molecule, simpler to\nmanufacture at scale.",
             fontsize=14.5, va="top", linespacing=1.42)
    fig.text(0.08, 0.150,
             "Not a head-to-head comparison. Different trials, populations and\ndurations: 17% versus 3% placebo at Phase 3b; 16.2% is the upper end of\nan open-label extension, with a 10.4% discontinuation rate.",
             fontsize=10.5, va="top", color=MUTED, linespacing=1.4)
    save(fig, pdf, 4)


def s5(pdf):
    """Indication map — the biology spreading beyond obesity."""
    fig = newslide()
    kicker(fig, "Beyond obesity", ORANGE)
    fig.text(0.08, 0.895, "The same biology is\nmoving into the liver.", fontsize=27,
             fontweight="bold", va="top", linespacing=1.2)

    ax = blank_ax(fig, [0.08, 0.285, 0.84, 0.51])
    ax.set_xlim(0, 3); ax.set_ylim(0, 1)
    for i, (title, colour, mols) in enumerate(INDICATIONS):
        chip(ax, i + 0.04, 0.82, 0.92, 0.15, colour, alpha=0.92)
        ax.text(i + 0.5, 0.895, title.replace("\n", " "), ha="center", va="center",
                fontsize=10.2, fontweight="bold",
                color="#0f1419" if colour in (YELLOW, GREEN) else "#ffffff")
        for k, m in enumerate(mols):
            short = m.replace("cagrilintide + semaglutide", "cagrilintide\n+ semaglutide")
            ax.text(i + 0.5, 0.72 - k * 0.098, short, ha="center", va="top",
                    fontsize=9.8, color=INK, linespacing=1.2)
        if i:
            ax.plot([i, i], [0.02, 0.99], color=GRID, lw=0.9)

    fig.text(0.08, 0.245,
             "Adding glucagon acts directly on the liver while GLP-1\nhandles appetite. That widened the field from weight\nto liver disease, and now to addiction.",
             fontsize=14.5, va="top", linespacing=1.42)
    fig.text(0.08, 0.126,
             "One molecule is approved in MASH, one of only two treatments for it. A\nglucagon/GLP-1 agonist began Phase 3 there in Aug 2026; data due 2029.",
             fontsize=10.5, va="top", color=MUTED, linespacing=1.4)
    save(fig, pdf, 5)


def s6(pdf):
    fig = newslide()
    kicker(fig, "Scope and sources")
    fig.text(0.08, 0.895, "What this covers.", fontsize=30,
             fontweight="bold", va="top")
    fig.text(0.08, 0.790,
             "Receptor targets, approval status and trial stage as\nat August 2026, from company filings, company\nreleases and industry landscape reviews.\n\n"
             "No trade names. No share prices, valuations or\ncompany comparisons — this is a view of the science,\nnot of the market.\n\n"
             "Trial results are point-in-time and stages change.\nCross-trial figures are not head-to-head.",
             fontsize=15.5, va="top", linespacing=1.45)
    fig.add_artist(plt.Line2D([0.08, 0.92], [0.335, 0.335], color=GRID, lw=1))
    fig.text(0.08, 0.285, "Sources", fontsize=13, fontweight="bold", color=INK)
    fig.text(0.08, 0.250,
             "SEC filings (10-Q, 8-K) and company releases, Dec 2025 – Aug 2026;\n"
             "regulatory announcements; industry landscape reviews.",
             fontsize=11.5, va="top", color=INK2, linespacing=1.4)
    fig.text(0.08, 0.160, "Related work", fontsize=13, fontweight="bold", color=INK)
    fig.text(0.08, 0.128, "namikakmandev.github.io", fontsize=13, color=BLUE)
    fig.text(0.08, 0.088, "Not medical or investment advice.", fontsize=11, color=MUTED)
    save(fig, pdf, 6)


def main():
    out = os.path.join(ROOT, "notes", "glp1-molecules-carousel.pdf")
    with PdfPages(out) as pdf:
        for f in (s1, s2, s3, s4, s5, s6):
            f(pdf)
    print(f"wrote {out} · {NSLIDES} slides")
    print("slides in", PNGDIR)


if __name__ == "__main__":
    main()
