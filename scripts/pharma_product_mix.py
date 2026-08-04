#!/usr/bin/env python3
"""What kind of medicine? — product mix from trade composition.

The value-added series (Eurostat/OECD) says how BIG pharma is in each economy.
It cannot say WHAT is made. Trade by HS chapter-30 class can, as a proxy:

  3002  immunological products — vaccines, antisera, blood fractions, mAbs ("biologics")
  3004  medicaments in measured doses / retail packs ("finished dosage")
  3003  medicaments, not in measured doses ("bulk formulated")
  2937  hormones (incl. insulin, and GLP-1 falls here or in 3004 by form)
  2941  antibiotics (active substances)

Two datasets, both Eurostat Comext DS-045409, value in EUR:
  pharma-exports  — EU/EFTA reporters' exports to the world  → the maker's own mix
  pharma-mirror   — EU27 imports by partner                  → a non-EU maker's mix
                    seen from the EU (a partial, EU-facing view — labelled as such)

Writes data/pharma-product-mix.json and two charts.
"""
import json, os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "pharma-study")

SURFACE = "#0f1419"; INK = "#e8eaed"; INK2 = "#9aa3ad"; GRID = "#232a33"
# 5 classes, palette validated for dark surface (dataviz skill)
CLASS = [
    ("3002", "Biologics / vaccines", "#3987e5"),
    ("3004", "Finished dosage",      "#199e70"),
    ("2937", "Hormones",             "#c98500"),
    ("2941", "Antibiotics",          "#d95926"),
    ("3003", "Bulk formulated",      "#6b7482"),
]
plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "text.color": INK, "axes.edgecolor": GRID, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "axes.grid": False,
    "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
    "font.family": "DejaVu Sans", "font.size": 12,
})

ex = json.load(open(os.path.join(ROOT, "data", "pharma-exports.json")))["series"]
mi = json.load(open(os.path.join(ROOT, "data", "pharma-mirror.json")))["series"]

NAME = {"DK": "Denmark", "IE": "Ireland", "BE": "Belgium", "DE": "Germany",
        "FR": "France", "SI": "Slovenia", "HU": "Hungary", "NL": "Netherlands",
        "AT": "Austria", "IT": "Italy", "ES": "Spain", "PL": "Poland",
        "CH": "Switzerland", "US": "United States", "GB": "United Kingdom",
        "CN": "China", "IN": "India", "JP": "Japan", "KR": "South Korea",
        "IL": "Israel", "SG": "Singapore", "CA": "Canada"}


def mix(src, geo, year="2024"):
    tot = {}
    for code, _, _ in CLASS:
        s = src.get(f"{geo}|{code}", {})
        if year in s:
            tot[code] = s[year]
    T = sum(tot.values())
    return ({c: 100 * tot.get(c, 0) / T for c, _, _ in CLASS}, T / 1e9) if T else (None, 0)


def title(fig, main, sub):
    fig.subplots_adjust(top=0.86)
    fig.text(0.065, 0.975, main, fontsize=17, fontweight="bold", color=INK, va="top")
    fig.text(0.065, 0.928, sub, fontsize=11.5, color=INK2, va="top")


def save(fig, name):
    p = os.path.join(OUT, name)
    fig.savefig(p, dpi=110); plt.close(fig); print("wrote", p)


def stacked(src, geos, fname, main, sub, note_total="exports to world"):
    rows = []
    for g in geos:
        m, t = mix(src, g)
        if m:
            rows.append((g, m, t))
    rows.sort(key=lambda r: -r[1]["3002"])   # most biologics-heavy on top
    fig, ax = plt.subplots(figsize=(12.2, 0.62 * len(rows) + 2.4))
    fig.subplots_adjust(left=0.17, top=0.86, right=0.87)
    ylabels = [f"{NAME[g]}  ·  €{t:.0f}bn" for g, _, t in rows]
    y = range(len(rows))
    left = [0.0] * len(rows)
    for code, label, color in CLASS:
        widths = [r[1][code] for r in rows]
        ax.barh(list(y), widths, left=left, color=color, height=0.66,
                label=label, zorder=3)
        for i, w in enumerate(widths):
            if w >= 8:
                ax.annotate(f"{w:.0f}", (left[i] + w / 2, i), ha="center", va="center",
                            color="#0f1419" if code in ("2937",) else "#f4f6f8",
                            fontsize=9.5, fontweight="bold")
        left = [l + w for l, w in zip(left, widths)]
    ax.set_yticks(list(y)); ax.set_yticklabels(ylabels, fontsize=10.5)
    ax.set_xlim(0, 100); ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}%"))
    ax.invert_yaxis()
    title(fig, main, sub)
    ax.legend(ncols=5, loc="lower left", bbox_to_anchor=(0, 1.005),
              frameon=False, fontsize=10.5, labelcolor=INK, columnspacing=1.2,
              handlelength=1.1, handletextpad=0.5)
    save(fig, fname)


def chart_kr_biologics():
    """South Korea's export mix to the EU, 2002 → 2024 — the biosimilar pivot."""
    fig, ax = plt.subplots(figsize=(12.2, 6.4))
    years = [str(y) for y in range(2002, 2025)]
    bio = []
    for y in years:
        m, _ = mix(mi, "KR", y)
        bio.append(m["3002"] if m else None)
    xs = [int(y) for y, b in zip(years, bio) if b is not None]
    ys = [b for b in bio if b is not None]
    ax.plot(xs, ys, color="#3987e5", lw=2.6, zorder=3)
    ax.fill_between(xs, ys, color="#3987e5", alpha=0.12)
    ax.annotate(f"Biologics {ys[-1]:.0f}% of Korea's\npharma exports to the EU",
                (xs[-1], ys[-1]), xytext=(-4, -46), textcoords="offset points",
                ha="right", color="#3987e5", fontsize=12, fontweight="bold")
    ax.set_xlim(2002, 2025); ax.set_ylim(0, 100)
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}%"))
    title(fig, "South Korea built a biologics export machine",
          "Immunological products (HS 3002 — vaccines, antibodies, biosimilars) as a share\n"
          "of Korea's pharma exports to the EU — the 2013–17 jump is Samsung Biologics and Celltrion.")
    save(fig, "08_korea_biologics.png")


def main():
    # Slovenia excluded: its dosage "exports" jump from €2.8bn (2018) to €23bn
    # (2024) — a distribution-hub re-export surge, not domestic production
    # (its value-added share is a modest 2.8%).
    stacked(ex, ["DK", "IE", "BE", "DE", "FR", "HU", "NL", "AT", "IT", "ES", "PL"],
            "07_product_mix_eu.png",
            "What each country exports — pharma export mix, 2024",
            "Share of pharma exports by HS class. Biologics-led (Ireland, Belgium, "
            "Netherlands, Austria) vs finished-dosage-led (France, Italy, Spain).")
    stacked(mi, ["CH", "US", "GB", "CN", "IN", "JP", "KR", "SG", "CA"],
            "09_product_mix_world.png",
            "What the world ships into the EU — by product class, 2024",
            "Share of each partner's pharma exports to the EU — a partial, EU-facing view.\n"
            "Korea 97% biologics; China antibiotics-heavy; India finished generics.")
    chart_kr_biologics()

    out = {"note": "Product mix as share of pharma trade value by HS class "
                   "(3002 biologics, 3004 dosage, 3003 bulk, 2937 hormones, 2941 antibiotics). "
                   "Eurostat Comext DS-045409. EU/EFTA rows = exports to world; non-EU rows "
                   "= exports to the EU only (mirror). Proxy for product mix, NOT production.",
           "eu_exporters": {}, "world_to_eu": {}}
    for g in NAME:
        src = ex if g in ("DK", "IE", "BE", "DE", "FR", "HU", "NL", "AT", "IT", "ES", "PL") else mi
        bucket = "eu_exporters" if src is ex else "world_to_eu"
        m, t = mix(src, g)
        if m:
            out[bucket][g] = {"eur_bn": round(t, 2),
                              "mix_pct": {c: round(v, 1) for c, v in m.items()}}
    json.dump(out, open(os.path.join(ROOT, "data", "pharma-product-mix.json"), "w"),
              separators=(",", ":"))
    print("wrote data/pharma-product-mix.json")


if __name__ == "__main__":
    main()
