#!/usr/bin/env python3
"""Charts for the pharma-share-of-GDP study -> assets/pharma-study/*.png

Style matches the saas-study set: dark surface #0f1419, thin marks, hairline
grid, direct labels on the series that matter. Palette validated (dataviz
skill, dark mode, surface #0f1419): blue #3987e5 / orange #d95926 /
aqua #199e70 / yellow #c98500.
"""
import json, os, sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from pharma_share_audit import NAMES, load  # noqa: E402

OUT = os.path.join(ROOT, "assets", "pharma-study")
os.makedirs(OUT, exist_ok=True)

SURFACE = "#0f1419"
INK = "#e8eaed"
INK2 = "#9aa3ad"
GRID = "#232a33"
BLUE, ORANGE, AQUA, YELLOW = "#3987e5", "#d95926", "#199e70", "#c98500"
MUTED = "#3d4654"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "text.color": INK, "axes.edgecolor": GRID,
    "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.spines.left": False,
    "font.family": "DejaVu Sans", "font.size": 12,
})

share = json.load(open(os.path.join(ROOT, "data", "pharma-share.json")))["shares"]
eur = load("pharma-gva-eur.json")
gdp_eur = load("gdp-eur.json")

EXCLUDE = {"IS"}          # negative C21 GVA from 2017 — meaningless share
pct = FuncFormatter(lambda v, _: f"{v:g}%")


def series(geo, key="share_gdp"):
    rows = share[geo]
    ys = sorted(int(y) for y in rows)
    return ys, [rows[str(y)][key] for y in ys]


def title(fig, main, sub):
    """Figure-level title + subtitle with fixed clearance above the axes."""
    fig.subplots_adjust(top=0.84)
    fig.text(0.065, 0.975, main, fontsize=17, fontweight="bold",
             color=INK, va="top")
    fig.text(0.065, 0.925, sub, fontsize=11.5, color=INK2, va="top")


def save(fig, name):
    path = os.path.join(OUT, name)
    fig.savefig(path, dpi=110)
    plt.close(fig)
    print("wrote", path)


# ---------------------------------------------------------------- 1: hero lines
def chart_trajectories():
    fig, ax = plt.subplots(figsize=(12.6, 7.0))
    # context: every other country with >=20y, muted, no labels
    for geo in share:
        if geo in EXCLUDE or geo in ("DK", "CH", "SI", "BE", "IE"):
            continue
        ys, vs = series(geo)
        ys = [y for y in ys if y >= 1995]
        vs = vs[-len(ys):]
        if len(ys) >= 20:
            ax.plot(ys, vs, color=MUTED, lw=1.0, alpha=0.55, zorder=1)

    focus = [("DK", BLUE, "Denmark"), ("CH", ORANGE, "Switzerland"),
             ("SI", AQUA, "Slovenia"), ("BE", YELLOW, "Belgium")]
    for geo, c, label in focus:
        ys, vs = series(geo)
        ys2 = [y for y in ys if y >= 1995]
        vs2 = vs[-len(ys2):]
        ax.plot(ys2, vs2, color=c, lw=2.4, zorder=3, label=label)
        ax.annotate(f"{label}  {vs2[-1]:.1f}%", (ys2[-1], vs2[-1]),
                    xytext=(8, 0), textcoords="offset points",
                    color=c, fontsize=12, fontweight="bold", va="center")

    # Ireland: real but truncated by confidentiality — dashed, declared
    ys, vs = series("IE")
    ax.plot(ys, vs, color="#6b7482", lw=1.4, ls=(0, (4, 3)), zorder=2, alpha=0.9)
    ax.annotate("Ireland — peak 12.8% (2002);\nEurostat suppresses the series after 2014",
                (2014, vs[-1]), xytext=(12, 14), textcoords="offset points",
                color="#8a93a0", fontsize=10, va="bottom")

    ax.set_xlim(1995, 2031)
    ax.set_ylim(0, 13.4)
    ax.yaxis.set_major_formatter(pct)
    title(fig, "Pharma manufacturing as a share of GDP, 1995–2025",
          "Gross value added of NACE C21 ÷ GDP, current prices, national currency — "
          "30 European countries; grey = all others")
    ax.legend(ncols=4, loc="lower left", bbox_to_anchor=(0, 1.0),
              frameon=False, fontsize=11.5, labelcolor=INK, columnspacing=1.4)
    save(fig, "01_share_trajectories.png")


# ------------------------------------------------------------- 2: ranked, 2023
def chart_ranked_2023():
    rows = []
    for geo, r in share.items():
        if geo in EXCLUDE:
            continue
        v = r.get("2023")
        if v:
            rows.append((geo, v["share_gdp"]))
    rows.sort(key=lambda t: t[1])
    fig, ax = plt.subplots(figsize=(11.5, 9.2))
    fig.subplots_adjust(left=0.21)
    names = [NAMES.get(g, g).replace("Bosnia and Herzegovina", "Bosnia-Herzegovina")
             for g, _ in rows]
    vals = [v for _, v in rows]
    colors = [ORANGE if g == "TR" else BLUE for g, _ in rows]
    bars = ax.barh(names, vals, color=colors, height=0.62, zorder=3)
    for (g, v), b in zip(rows, bars):
        ax.annotate(f"{v:.2f}", (v, b.get_y() + b.get_height() / 2),
                    xytext=(5, 0), textcoords="offset points",
                    color=INK if g in ("DK", "CH", "TR") else INK2,
                    fontsize=10.5, va="center")
    ax.xaxis.set_major_formatter(pct)
    ax.grid(axis="y", visible=False)
    title(fig, "Pharma share of GDP, 2023 — every country with data",
          "% of GDP, 2023. Ireland ends 2014 → not shown; Iceland excluded "
          "(negative C21 GVA). Türkiye highlighted.")
    ax.tick_params(axis="y", labelsize=11)
    save(fig, "02_ranked_2023.png")


# ------------------------------------- 3: share of manufacturing — Denmark story
def chart_share_of_manufacturing():
    fig, ax = plt.subplots(figsize=(12.6, 6.6))
    for geo, c, label in [("DK", BLUE, "Denmark"), ("CH", ORANGE, "Switzerland"),
                          ("SI", AQUA, "Slovenia"), ("BE", YELLOW, "Belgium")]:
        rows = share[geo]
        ys = sorted(int(y) for y in rows)
        ys = [y for y in ys if y >= 1995 and rows[str(y)]["share_manu"]]
        vs = [rows[str(y)]["share_manu"] for y in ys]
        ax.plot(ys, vs, color=c, lw=2.4, zorder=3, label=label)
        ax.annotate(f"{label}  {vs[-1]:.0f}%", (ys[-1], vs[-1]),
                    xytext=(8, 0), textcoords="offset points",
                    color=c, fontsize=12, fontweight="bold", va="center")
    for geo in ("DE", "FR", "IT", "ES", "NL", "AT", "PL", "CZ", "HU"):
        rows = share[geo]
        ys = sorted(int(y) for y in rows)
        ys = [y for y in ys if y >= 1995 and rows[str(y)]["share_manu"]]
        vs = [rows[str(y)]["share_manu"] for y in ys]
        ax.plot(ys, vs, color=MUTED, lw=1.0, alpha=0.55, zorder=1)
    ax.set_xlim(1995, 2030)
    ax.yaxis.set_major_formatter(pct)
    title(fig, "Pharma as a share of ALL manufacturing value added, 1995–2025",
          "C21 GVA ÷ total manufacturing (NACE C) GVA — in Denmark nearly half of "
          "manufacturing is now pharma. Grey: DE FR IT ES NL AT PL CZ HU")
    ax.legend(ncols=4, loc="lower left", bbox_to_anchor=(0, 1.0),
              frameon=False, fontsize=11.5, labelcolor=INK, columnspacing=1.4)
    save(fig, "03_share_of_manufacturing.png")


# -------------------------------------------- 4: absolute size vs share, 2023
def chart_size_vs_share():
    fig, ax = plt.subplots(figsize=(12.6, 7.0))
    pts = []
    for geo, rows in eur.items():
        if geo in EXCLUDE or geo.startswith("EA") or geo == "EU27_2020":
            continue
        v = rows.get("2023")
        s = share.get(geo, {}).get("2023")
        g = gdp_eur.get(geo, {}).get("2023")
        if v and s and g and v > 0:
            pts.append((geo, v / 1000, s["share_gdp"], g))
    for geo, x, y, _ in pts:
        big = geo in ("DK", "CH", "DE", "FR", "IE", "BE", "TR", "SI", "NL", "IT", "ES")
        c = ORANGE if geo == "TR" else (BLUE if big else MUTED)
        ax.scatter(x, y, s=64, color=c, zorder=3,
                   edgecolors=SURFACE, linewidths=2)
        if big:
            off = {"ES": (-8, 10), "IT": (2, -16), "FR": (8, 4), "DE": (8, -6),
                   "NL": (8, 6), "BE": (8, 4), "DK": (8, 4), "CH": (8, 4),
                   "SI": (8, 4), "TR": (8, 4)}.get(geo, (7, 5))
            ha = "right" if geo == "ES" else "left"
            ax.annotate(NAMES.get(geo, geo), (x, y), xytext=off, ha=ha,
                        textcoords="offset points", color=INK if geo in ("DK", "CH", "TR") else INK2,
                        fontsize=10.5)
    ax.set_xscale("log")
    ax.set_xticks([0.1, 0.3, 1, 3, 10, 30, 60])
    ax.get_xaxis().set_major_formatter(FuncFormatter(lambda v, _: f"€{v:g}bn"))
    ax.yaxis.set_major_formatter(pct)
    ax.set_xlabel("Pharma gross value added, 2023 (log scale)")
    ax.set_ylabel("Share of GDP, 2023")
    title(fig, "Size is not weight — €26bn is 0.6% of Germany, €24bn is 6.5% of Denmark",
          "C21 GVA in € (x, log) vs share of own GDP (y), 2023. "
          "Blue: labelled economies · orange: Türkiye")
    save(fig, "04_size_vs_share.png")


if __name__ == "__main__":
    chart_trajectories()
    chart_ranked_2023()
    chart_share_of_manufacturing()
    chart_size_vs_share()
