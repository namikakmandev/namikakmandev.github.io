#!/usr/bin/env python3
"""LinkedIn carousel: the GLP-1 molecule landscape -> notes/glp1-molecules-carousel.pdf

Option A. A science deck, not a markets deck: NO share prices, NO valuation, NO
company names. Subject is the molecules — mechanism, stage and indication. For an
author employed in the pharmaceutical industry this removes securities commentary
and competitor commentary entirely.

6 portrait slides (1080x1350), same house style as scripts/glp1_carousel.py.

Unlike the markets deck, these facts cannot be computed from a price file, so they
are stated here with their source. Every claim below traces to one of:

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

No trade names appear anywhere in this deck, by design.
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PNGDIR = os.path.join(ROOT, "assets", "glp1-study", "molecules")
os.makedirs(PNGDIR, exist_ok=True)

SURFACE = "#0f1419"; INK = "#f4f6f8"; INK2 = "#9aa3ad"
GRID = "#232a33"; MUTED = "#3d4654"
BLUE = "#3987e5"; GREEN = "#199e70"; ORANGE = "#d95926"; YELLOW = "#c98500"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "text.color": INK, "font.family": "DejaVu Sans",
})

W, H = 7.2, 9.0
NSLIDES = 6

# molecule, mechanism, stage, stage-rank (for the pipeline graphic), source refs
PIPELINE = [
    ("semaglutide",                 "GLP-1 receptor agonist",        "Approved",  4, "[8]"),
    ("tirzepatide",                 "dual GIP/GLP-1 agonist",        "Approved",  4, "[8]"),
    ("oral semaglutide 25 mg",      "GLP-1 agonist, tablet",         "Approved",  4, "[5]"),
    ("cagrilintide + semaglutide",  "GLP-1 + amylin",                "Filed",     3, "[6][7]"),
    ("aleniglipron",                "oral GLP-1, small molecule",    "Phase 3",   2, "[1][2]"),
    ("pemvidutide",                 "glucagon/GLP-1, 1:1",           "Phase 3",   2, "[3][4]"),
    ("zenagamtide",                 "GLP-1 + amylin",                "Phase 3",   2, "[7]"),
    ("petrelintide",                "amylin analogue",               "Phase 2",   1, "[6]"),
    ("ACCG-2671",                   "oral amylin, small molecule",   "Phase 1",   0, "[1][6]"),
]
STAGE_COLOUR = {4: GREEN, 3: BLUE, 2: BLUE, 1: YELLOW, 0: ORANGE}


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


def rows(fig, items, y0, gap=0.105):
    """molecule / mechanism / stage blocks."""
    for i, (mol, mech, stage, rank) in enumerate(items):
        y = y0 - i * gap
        fig.text(0.08, y, mol, fontsize=20, fontweight="bold", color=INK)
        fig.text(0.08, y - 0.032, mech, fontsize=13, color=INK2)
        fig.text(0.92, y, stage, fontsize=15, fontweight="bold",
                 color=STAGE_COLOUR[rank], ha="right")
        fig.add_artist(plt.Line2D([0.08, 0.92], [y - 0.055, y - 0.055], color=GRID, lw=1))


# ----------------------------------------------------------------- slides
def s1(pdf):
    fig = newslide()
    kicker(fig, "GLP-1 · the molecules")
    fig.text(0.08, 0.815, "Two molecules", fontsize=38, fontweight="bold", va="top")
    fig.text(0.08, 0.740, "approved.", fontsize=38, fontweight="bold", va="top")
    fig.text(0.08, 0.650, "Nine in the race.", fontsize=38, fontweight="bold",
             va="top", color=BLUE)
    fig.text(0.08, 0.545,
             "GLP-1 medicines reshaped the treatment of\ntype 2 diabetes, then of obesity.\n\n"
             "What follows is the landscape by molecule:\nmechanism, stage and indication.\n\n"
             "No share prices. No companies. Just the\nmolecules and where they stand.",
             fontsize=17, va="top", linespacing=1.45)
    fig.add_artist(plt.Line2D([0.08, 0.92], [0.235, 0.235], color=GRID, lw=1))
    fig.text(0.08, 0.185,
             "US prescriptions for GLP-1 receptor agonists rose\n587% between 2019 and 2024.",
             fontsize=14, va="top", color=INK, linespacing=1.4)
    fig.text(0.08, 0.095, "Sources listed on the final slide. As at August 2026.",
             fontsize=11, color=MUTED)
    save(fig, pdf, 1)


def s2(pdf):
    fig = newslide()
    kicker(fig, "Approved for obesity", GREEN)
    fig.text(0.08, 0.895, "Only two mechanisms\nare on the market.", fontsize=28,
             fontweight="bold", va="top", linespacing=1.2)
    rows(fig, [
        ("semaglutide", "GLP-1 receptor agonist · injectable and oral", "Approved", 4),
        ("tirzepatide", "dual GIP/GLP-1 agonist · injectable", "Approved", 4),
    ], 0.700, gap=0.135)
    fig.text(0.08, 0.475,
             "One activates the GLP-1 receptor alone.\nThe other adds GIP, a second incretin receptor.",
             fontsize=16.5, va="top", linespacing=1.45)
    fig.text(0.08, 0.355,
             "Everything else in obesity is still in trials.",
             fontsize=18, fontweight="bold", color=INK)
    fig.text(0.08, 0.265,
             "That is unusual for a therapy area this large, and it\nis why each trial readout moves the field so much.",
             fontsize=15, va="top", color=INK2, linespacing=1.45)
    fig.text(0.08, 0.135, "Obesity prevalence is projected to exceed 50% of adults by 2030.",
             fontsize=12.5, color=MUTED)
    save(fig, pdf, 2)


def s3(pdf):
    fig = newslide()
    kicker(fig, "The shift to a tablet")
    fig.text(0.08, 0.895, "The next contest is\noral.", fontsize=29,
             fontweight="bold", va="top", linespacing=1.2)
    fig.text(0.08, 0.740, "oral semaglutide 25 mg", fontsize=21, fontweight="bold")
    fig.text(0.08, 0.708, "peptide in tablet form", fontsize=13, color=INK2)
    fig.text(0.92, 0.740, "Approved", fontsize=15, fontweight="bold",
             color=GREEN, ha="right")
    fig.text(0.08, 0.648,
             "Authorised in the EU in July 2026 — the first\nGLP-1 receptor agonist in tablet form for weight\n"
             "management there, and its fifth authorisation\nafter the US, UK, UAE and Bahrain.",
             fontsize=15, va="top", linespacing=1.45)
    fig.text(0.08, 0.488, "About 17% weight loss versus 3% on placebo in Phase 3b.",
             fontsize=12.5, color=INK2)
    fig.add_artist(plt.Line2D([0.08, 0.92], [0.452, 0.452], color=GRID, lw=1))
    fig.text(0.08, 0.402, "aleniglipron", fontsize=21, fontweight="bold")
    fig.text(0.08, 0.370, "oral GLP-1, small molecule", fontsize=13, color=INK2)
    fig.text(0.92, 0.402, "Phase 3", fontsize=15, fontweight="bold", color=BLUE, ha="right")
    fig.text(0.08, 0.310,
             "A small molecule rather than a peptide, which is\nsimpler to manufacture at scale. Phase 2b showed\n"
             "up to 16.2% weight loss in the extension study,\nwith a 10.4% discontinuation rate.",
             fontsize=15, va="top", linespacing=1.45)
    fig.text(0.08, 0.135,
             "A tablet changes who can be treated, not just how well.",
             fontsize=12, color=MUTED)
    save(fig, pdf, 3)


def s4(pdf):
    fig = newslide()
    kicker(fig, "Beyond GLP-1 alone", YELLOW)
    fig.text(0.08, 0.895, "Amylin is the second\nmechanism.", fontsize=28,
             fontweight="bold", va="top", linespacing=1.2)
    rows(fig, [
        ("cagrilintide + semaglutide", "GLP-1 + amylin · injectable", "Filed", 3),
        ("zenagamtide", "GLP-1 + amylin receptor agonist", "Phase 3", 2),
        ("petrelintide", "amylin analogue", "Phase 2", 1),
        ("ACCG-2671", "oral amylin, small molecule", "Phase 1", 0),
    ], 0.715, gap=0.108)
    fig.text(0.08, 0.275,
             "If approved, the first combination would pair a\nGLP-1 receptor agonist with an amylin analogue\nfor the first time. A decision is expected in Q4.",
             fontsize=15.5, va="top", linespacing=1.45)
    fig.text(0.08, 0.135,
             "Amylin targets satiety by a different route, so the two mechanisms may add\nrather than overlap.",
             fontsize=12.5, va="top", color=MUTED, linespacing=1.35)
    save(fig, pdf, 4)


def s5(pdf):
    fig = newslide()
    kicker(fig, "Beyond obesity", ORANGE)
    fig.text(0.08, 0.895, "The same biology is\nmoving into the liver.", fontsize=27,
             fontweight="bold", va="top", linespacing=1.2)
    fig.text(0.08, 0.735, "semaglutide", fontsize=20, fontweight="bold")
    fig.text(0.08, 0.703, "GLP-1 receptor agonist", fontsize=13, color=INK2)
    fig.text(0.92, 0.735, "Approved in MASH", fontsize=14, fontweight="bold",
             color=GREEN, ha="right")
    fig.text(0.08, 0.645,
             "One of only two treatments approved for MASH.\nThe other works on a thyroid hormone receptor.",
             fontsize=15, va="top", linespacing=1.45)
    fig.add_artist(plt.Line2D([0.08, 0.92], [0.575, 0.575], color=GRID, lw=1))
    fig.text(0.08, 0.520, "pemvidutide", fontsize=20, fontweight="bold")
    fig.text(0.08, 0.488, "balanced 1:1 glucagon/GLP-1 agonist", fontsize=13, color=INK2)
    fig.text(0.92, 0.520, "Phase 3", fontsize=14, fontweight="bold", color=BLUE, ha="right")
    fig.text(0.08, 0.430,
             "Adding glucagon acts directly on the liver, while\nGLP-1 handles appetite and weight. In Phase 3 for\n"
             "MASH from August 2026: about 1,790 patients,\n52-week data expected in 2029.",
             fontsize=15, va="top", linespacing=1.45)
    fig.text(0.08, 0.265,
             "Also in development for alcohol use disorder and\nalcohol-associated liver disease, with FDA Fast Track\nin both, and Breakthrough Therapy status in MASH.",
             fontsize=14, va="top", color=INK2, linespacing=1.45)
    fig.text(0.08, 0.135,
             "Metabolic, hepatic and addiction pathways converge on one receptor family.",
             fontsize=11.5, color=MUTED)
    save(fig, pdf, 5)


def s6(pdf):
    fig = newslide()
    kicker(fig, "Scope and sources")
    fig.text(0.08, 0.895, "What this covers.", fontsize=30,
             fontweight="bold", va="top")
    fig.text(0.08, 0.790,
             "Approval status, mechanism and trial stage as at\nAugust 2026, taken from company filings, company\nreleases and industry landscape reviews.\n\n"
             "No trade names are used. No share prices,\nvaluations or company comparisons appear here —\nthis is a view of the science, not of the market.\n\n"
             "Trial results are point-in-time and stages change.\nNothing here is medical or investment advice.",
             fontsize=15.5, va="top", linespacing=1.45)
    fig.add_artist(plt.Line2D([0.08, 0.92], [0.335, 0.335], color=GRID, lw=1))
    fig.text(0.08, 0.285, "Sources", fontsize=13, fontweight="bold", color=INK)
    fig.text(0.08, 0.250,
             "SEC filings (10-Q, 8-K) and company releases, Dec 2025 – Aug 2026;\n"
             "regulatory announcements; industry landscape reviews.",
             fontsize=11.5, va="top", color=INK2, linespacing=1.4)
    fig.text(0.08, 0.160, "Related work", fontsize=13, fontweight="bold", color=INK)
    fig.text(0.08, 0.128, "namikakmandev.github.io", fontsize=13, color=BLUE)
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
