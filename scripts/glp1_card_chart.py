#!/usr/bin/env python3
"""Preview chart for the GLP-1 study card on projects.html.

The study page draws its charts in the browser from data/glp1-stocks.json, so
there is no static image to put on the card. This renders one: the divergence
between the two GLP-1 pure plays, rebased so the comparison is honest.
"""
import json, os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "glp1-study")
os.makedirs(OUT, exist_ok=True)

SURFACE = "#0f1419"; INK = "#f4f6f8"; INK2 = "#98a2ad"; GRID = "#242c36"
BLUE = "#3987e5"; GREEN = "#199e70"; MUTED = "#3d4654"
BASE = "2021-01"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE, "text.color": INK, "font.family": "DejaVu Sans",
})

series = json.load(open(os.path.join(ROOT, "data", "glp1-stocks.json")))["series"]


def rebased(ticker):
    """Total return indexed to 100 at BASE, as (x positions, values, labels)."""
    d = series[ticker]
    months = [m for m in sorted(d) if m >= BASE]
    base = d[months[0]]
    return months, [100 * d[m] / base for m in months]


fig, ax = plt.subplots(figsize=(12.0, 6.6))
fig.subplots_adjust(left=0.075, right=0.815, top=0.84, bottom=0.11)

months, _ = rebased("LLY")
xs = range(len(months))
for tick, col, lab in (("SPX", MUTED, "S&P 500"),
                       ("NVO", BLUE, "Novo Nordisk"),
                       ("LLY", GREEN, "Eli Lilly")):
    _, vals = rebased(tick)
    ax.plot(xs, vals, color=col, lw=2.6 if tick != "SPX" else 1.8, zorder=3)
    ax.annotate(f"{lab}  {vals[-1]:,.0f}", (len(months) - 1, vals[-1]),
                xytext=(8, 0), textcoords="offset points", color=col,
                fontsize=12, fontweight="bold", va="center", annotation_clip=False)

# Novo's round trip is the point of the chart, so mark the peak it gave back
_, nvo = rebased("NVO")
pk = nvo.index(max(nvo))
ax.plot([pk], [nvo[pk]], "o", color=BLUE, ms=7, zorder=4)
ax.annotate(f"peak {nvo[pk]:,.0f}", (pk, nvo[pk]), xytext=(0, 12),
            textcoords="offset points", color=BLUE, fontsize=11,
            fontweight="bold", ha="center")

ax.axhline(100, color=GRID, lw=1)
ax.grid(axis="y", color=GRID, lw=0.8)
ax.set_axisbelow(True)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.spines["bottom"].set_color(GRID)
ticks = [i for i, m in enumerate(months) if m.endswith("-01")]
ax.set_xticks(ticks)
ax.set_xticklabels([months[i][:4] for i in ticks])
ax.tick_params(colors=INK2, labelsize=11)
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
ax.set_xlim(0, len(months) - 1)

fig.text(0.075, 0.965, "One molecule class, two very different stocks",
         fontsize=17, fontweight="bold", color=INK, va="top")
fig.text(0.075, 0.905,
         f"Total return indexed to 100 at {BASE}. Lilly held its re-rating; "
         "Novo gave almost all of its back.",
         fontsize=11.5, color=INK2, va="top")

p = os.path.join(OUT, "01_lly_vs_nvo.png")
fig.savefig(p, dpi=110)
print("wrote", p, "|", months[0], "->", months[-1])
