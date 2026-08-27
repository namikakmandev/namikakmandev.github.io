#!/usr/bin/env python3
"""The one chart for the Big Mac half-life post.

Two decay curves: how much of a Big Mac valuation gap remains after t years,
(a) measured against the currency's own historical normal - the reading that
works - and (b) read as raw cross-country cheapness - the reading everyone
uses, which barely moves. Points are measured remaining fractions at 1/2/3y
from scripts/bigmac_reversion.py (expanding-window method, EUR base); curves
are the exponential decay implied by each measured half-life.

Writes assets/linkedin/bigmac-halflife.png (1600x1000).
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BLUE, ORANGE = "#2f9bff", "#ff6500"
INK, DIM, GRID = "#1f2430", "#5b6472", "#d6dce4"

# measured remaining fractions (1 + slope) from bigmac_reversion.py
T_PTS = [1, 2, 3]
OWN   = [1 - 0.241, 1 - 0.382, 1 - 0.481]     # half-life ~2.9y
RAW   = [1 - 0.125, 1 - 0.196, 1 - 0.253]     # half-life ~6.4y
HL_OWN, HL_RAW = 2.9, 6.4

t = np.linspace(0, 8, 300)
own_curve = 0.5 ** (t / HL_OWN)
raw_curve = 0.5 ** (t / HL_RAW)

fig, ax = plt.subplots(figsize=(16, 10), dpi=100)
fig.patch.set_facecolor("white"); ax.set_facecolor("white")

ax.plot(t, raw_curve, color=ORANGE, lw=3)
ax.plot(t, own_curve, color=BLUE, lw=3.5)
ax.scatter(T_PTS, RAW, s=90, color=ORANGE, zorder=5)
ax.scatter(T_PTS, OWN, s=90, color=BLUE, zorder=5)

# half-life droplines
for hl, col in ((HL_OWN, BLUE), (HL_RAW, ORANGE)):
    ax.plot([hl, hl], [0, 0.5], color=col, lw=1.2, ls=(0, (4, 4)), alpha=0.6)
ax.axhline(0.5, color=GRID, lw=1.2, ls=(0, (4, 4)))
ax.text(0.08, 0.515, "half the gap closed", fontsize=15, color=DIM)

# direct labels, not a legend box
label_bg = dict(facecolor="white", edgecolor="none", pad=1.5)
ax.text(4.7, 0.435, "vs the currency's own normal", fontsize=19, color=BLUE,
        fontweight="bold", bbox=label_bg, zorder=6)
ax.text(4.7, 0.38, f"half-life ≈ {HL_OWN:.0f} years — the reading that works",
        fontsize=15, color=BLUE, bbox=label_bg, zorder=6)
ax.text(4.9, 0.66, "“which countries are cheap”", fontsize=19,
        color=ORANGE, fontweight="bold")
ax.text(4.9, 0.605, f"half-life ≈ {HL_RAW:.0f} years — cheap countries just stay cheap",
        fontsize=15, color=ORANGE)
ax.text(HL_OWN, -0.055, f"{HL_OWN:.1f}y", fontsize=15, color=BLUE,
        ha="center", fontweight="bold")
ax.text(HL_RAW, -0.055, f"{HL_RAW:.1f}y", fontsize=15, color=ORANGE,
        ha="center", fontweight="bold")

ax.set_xlim(0, 8); ax.set_ylim(0, 1.02)
ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
ax.set_yticklabels(["0%", "25%", "50%", "75%", "100%"], fontsize=14, color=DIM)
ax.set_xticks(range(0, 9))
ax.tick_params(colors=DIM, labelsize=14)
ax.set_xlabel("years later", fontsize=16, color=DIM)
ax.set_ylabel("share of the valuation gap still open", fontsize=16, color=DIM)
for s in ("top", "right"): ax.spines[s].set_visible(False)
for s in ("left", "bottom"): ax.spines[s].set_color(GRID)
ax.grid(axis="y", color=GRID, lw=0.6, alpha=0.5)

fig.suptitle("The Big Mac index works — just not the way people read it",
             fontsize=27, color=INK, fontweight="bold", x=0.045, ha="left", y=0.97)
ax.set_title("How fast a currency's burger-price gap closes · 55 countries, 2000–2026",
             fontsize=17, color=DIM, loc="left", pad=14)
fig.text(0.045, 0.012,
         "Data: The Economist Big Mac index (open data, github.com/TheEconomist/big-mac-data), euro-relative valuations, semi-annual 2000–2026.\n"
         "Points: measured remaining gap at 1/2/3 years, pooled across 55 currencies, deviations vs an expanding past-only average (no look-ahead).\n"
         "Curves: exponential decay implied by each measured half-life. Country-clustered bootstrap CIs exclude zero at every horizon.  "
         "Method & code: namikakmandev.github.io/bigmac-halflife.html",
         fontsize=10.5, color=DIM, va="bottom", linespacing=1.5)
plt.subplots_adjust(left=0.075, right=0.97, top=0.87, bottom=0.13)
fig.savefig("assets/linkedin/bigmac-halflife.png", facecolor="white")
print("chart written")
