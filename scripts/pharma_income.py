#!/usr/bin/env python3
"""Who books the production, and who books the income.

Trade and value-added data say where medicines are MADE. They say nothing
about who ends up with the earnings. Gross national income does: GNI is GDP
plus income a country's residents earn abroad, minus income foreign owners
earn inside it.

  GNI < GDP  -> production happens here, the profit leaves
  GNI > GDP  -> the country's firms earn more abroad than foreigners earn here

Ireland runs at 75% and Denmark at 102%, which is the same story from both
ends: a manufacturing location versus an owner of manufacturing.

Writes assets/pharma-study/10_income_vs_production.png
"""
import json, os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "pharma-study")

SURFACE = "#0f1419"; INK = "#e8eaed"; INK2 = "#9aa3ad"; GRID = "#232a33"
BLUE, ORANGE, GREEN, MUTED = "#3987e5", "#d95926", "#199e70", "#3d4654"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "text.color": INK, "axes.edgecolor": GRID, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "axes.grid": True,
    "grid.color": GRID, "grid.linewidth": 0.8, "axes.spines.top": False,
    "axes.spines.right": False, "axes.spines.left": False,
    "font.family": "DejaVu Sans", "font.size": 12,
})

gni = json.load(open(os.path.join(ROOT, "data", "gni-gdp.json")))["series"]
gdp = json.load(open(os.path.join(ROOT, "data", "gdp-total.json")))["series"]

NAMES = {"IE": "Ireland", "LU": "Luxembourg", "CH": "Switzerland", "HU": "Hungary",
         "NL": "Netherlands", "SI": "Slovenia", "AT": "Austria", "IT": "Italy",
         "FR": "France", "BE": "Belgium", "DK": "Denmark", "DE": "Germany"}


def series(geo):
    s = gni.get(f"{geo}|RECV") or gni.get(f"{geo}|PAID") or {}
    ys = sorted(set(s) & set(gdp.get(geo, {})), key=int)
    return [int(y) for y in ys], [100 * s[y] / gdp[geo][y] for y in ys]


def main():
    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(12.6, 6.4), gridspec_kw={"width_ratios": [1.15, 1]})
    fig.subplots_adjust(top=0.78, bottom=0.10, wspace=0.30, left=0.105, right=0.93)

    # left: latest ranking
    rows = []
    for geo in NAMES:
        ys, vs = series(geo)
        if ys:
            rows.append((geo, ys[-1], vs[-1]))
    rows.sort(key=lambda r: r[2])
    names = [f"{NAMES[g]}" for g, _, _ in rows]
    vals = [v for _, _, v in rows]
    cols = [ORANGE if v < 95 else (GREEN if v > 101 else MUTED) for v in vals]
    ax1.barh(names, [v - 100 for v in vals], left=100, color=cols, height=.66, zorder=3)
    for (g, y, v), n in zip(rows, names):
        ax1.annotate(f"{v:.0f}%", (v, n), xytext=(6 if v >= 100 else -6, 0),
                     textcoords="offset points", ha="left" if v >= 100 else "right",
                     color=INK, fontsize=10.5, va="center", fontweight="bold")
    ax1.axvline(100, color=INK2, lw=1)
    ax1.set_xlim(58, 116)
    ax1.grid(axis="y", visible=False)
    ax1.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}%"))
    ax1.tick_params(axis="y", labelsize=11)

    # right: Ireland vs Denmark over time
    for geo, col in (("IE", ORANGE), ("DK", GREEN)):
        ys, vs = series(geo)
        keep = [(y, v) for y, v in zip(ys, vs) if y >= 1995]
        ax2.plot([k[0] for k in keep], [k[1] for k in keep], color=col, lw=2.6)
        ax2.annotate(f"{NAMES[geo]}  {keep[-1][1]:.0f}%", (keep[-1][0], keep[-1][1]),
                     xytext=(7, 0), textcoords="offset points", color=col,
                     fontsize=12, fontweight="bold", va="center")
    ax2.axhline(100, color=INK2, lw=1)
    ax2.set_xlim(1995, 2036); ax2.set_ylim(68, 110)
    ax2.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}%"))

    fig.text(0.065, 0.965, "Who books the production, and who books the income",
             fontsize=17, fontweight="bold", color=INK, va="top")
    fig.text(0.065, 0.915,
             "Gross national income as a share of GDP. Below 100%: profits earned in the country "
             "flow out to\nforeign owners. Above 100%: the country's own firms earn more abroad "
             "than foreigners earn inside it.",
             fontsize=11.5, color=INK2, va="top", linespacing=1.5)

    path = os.path.join(OUT, "10_income_vs_production.png")
    fig.savefig(path, dpi=110)
    print("wrote", path)

    for g, y, v in rows:
        print(f"  {NAMES[g]:<13}{y}  {v:.1f}%")


if __name__ == "__main__":
    main()
