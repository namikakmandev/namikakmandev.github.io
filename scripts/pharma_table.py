#!/usr/bin/env python3
"""The full 41-country table, generated — share AND absolute size.

Shares are computed in national currency (no exchange rate touches them).
Absolute size needs a common currency, so pharmaceutical value added is
converted to euro at the annual average rate for its own year:

  Eurostat countries -> already published in EUR (pharma-gva-eur)
  OECD STAN countries -> national currency / EUR rate for that year

Chile, Colombia and Costa Rica have no euro reference rate in the Eurostat
series, so they carry a share but no euro figure, and are labelled as such
rather than dropped.

Writes the table into pharma-gdp-share.html between the TABLE-42 markers,
and assets/pharma-study/11_size_vs_share.png.
"""
import json, os, re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "pharma-study")

SURFACE = "#0f1419"; INK = "#e8eaed"; INK2 = "#9aa3ad"; GRID = "#232a33"
BLUE, ORANGE, GREEN, MUTED = "#3987e5", "#d95926", "#199e70", "#3d4654"


def load(name, key="series"):
    with open(os.path.join(ROOT, "data", name)) as f:
        d = json.load(f)
    return d[key] if key else d


share_eu = load("pharma-share.json", "shares")
share_st = load("pharma-share-stan.json", "shares")
gva_eur = load("pharma-gva-eur.json")
stan_nac = load("stan-pharma.json")
fx = load("fx-eur.json")

# ISO3 (STAN) -> currency, and the display name
STAN_CUR = {"USA": "USD", "JPN": "JPY", "KOR": "KRW", "CAN": "CAD", "MEX": "MXN",
            "AUS": "AUD", "GBR": "GBP", "ISR": "ILS", "TUR": "TRY",
            "IRL": "EUR", "CHL": None, "COL": None, "CRI": None}
NAME = {
    "AT": "Austria", "BE": "Belgium", "BG": "Bulgaria", "CH": "Switzerland",
    "CY": "Cyprus", "CZ": "Czechia", "DE": "Germany", "DK": "Denmark",
    "EE": "Estonia", "EL": "Greece", "ES": "Spain", "FI": "Finland",
    "FR": "France", "HR": "Croatia", "HU": "Hungary", "IS": "Iceland",
    "IT": "Italy", "LT": "Lithuania", "LU": "Luxembourg", "LV": "Latvia",
    "MT": "Malta", "NL": "Netherlands", "NO": "Norway", "PL": "Poland",
    "PT": "Portugal", "RO": "Romania", "SE": "Sweden", "SI": "Slovenia",
    "SK": "Slovakia", "RS": "Serbia", "MK": "North Macedonia",
    "BA": "Bosnia & Herz.", "USA": "United States", "JPN": "Japan",
    "KOR": "South Korea", "CAN": "Canada", "MEX": "Mexico", "AUS": "Australia",
    "GBR": "United Kingdom", "ISR": "Israel", "TUR": "Türkiye", "IRL": "Ireland",
    "CHL": "Chile", "COL": "Colombia", "CRI": "Costa Rica",
}
# currency of each Eurostat reporter, for the ones outside the euro area
EU_CUR = {"CH": "CHF", "DK": "DKK", "SE": "SEK", "NO": "NOK", "PL": "PLN",
          "HU": "HUF", "CZ": "CZK", "RO": "RON", "IS": "ISK", "BG": "BGN"}
EXCLUDE = {"IS"}          # negative C21 value added from 2017


def eur(geo, year, from_stan):
    """Pharma value added in € billion for the given year, or None."""
    if not from_stan:
        v = gva_eur.get(geo, {}).get(str(year))
        return v / 1000 if v else None          # published in million EUR
    cur = STAN_CUR.get(geo)
    if cur is None:
        return None
    v = stan_nac.get(geo, {}).get(str(year))
    if not v:
        return None
    if cur == "EUR":
        return v / 1000
    rate = fx.get(cur, {}).get(str(year))
    return (v / rate) / 1000 if rate else None  # million NAC -> bn EUR


def rows():
    out = []
    for geo, r in share_eu.items():
        if geo in EXCLUDE or geo in ("IE", "TR"):
            continue
        yrs = [int(y) for y in r if r[y].get("share_gva")]
        if not yrs:
            continue
        y = max(yrs)
        out.append({"geo": geo, "name": NAME.get(geo, geo), "year": y,
                    "share": r[str(y)]["share_gva"], "eur": eur(geo, y, False),
                    "src": "Eurostat"})
    for geo, r in share_st.items():
        y = max(int(x) for x in r)
        out.append({"geo": geo, "name": NAME.get(geo, geo), "year": y,
                    "share": r[str(y)]["share_gva"], "eur": eur(geo, y, True),
                    "src": "OECD"})
    out.sort(key=lambda d: -d["share"])
    return out


def html_table(rs):
    head = ('<table class="tbl">\n<thead><tr>'
            '<th>#</th><th>Country</th><th class="num">Share of economy</th>'
            '<th class="num">Pharma value added</th><th class="num">Year</th>'
            '<th>Source</th></tr></thead>\n<tbody>\n')
    body = ""
    for i, d in enumerate(rs, 1):
        hi = ' class="hi"' if d["share"] >= 2 else ""
        e = f"&euro;{d['eur']:,.1f}bn" if d["eur"] else "&mdash;"
        body += (f'<tr{hi}><td>{i}</td><td><b>{d["name"]}</b></td>'
                 f'<td class="num">{d["share"]:.2f}%</td>'
                 f'<td class="num">{e}</td>'
                 f'<td class="num">{d["year"]}</td><td>{d["src"]}</td></tr>\n')
    return head + body + "</tbody>\n</table>\n"


def chart(rs):
    pts = [d for d in rs if d["eur"] and d["eur"] > 0.05]
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE, "text.color": INK, "axes.edgecolor": GRID,
        "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.spines.left": False, "font.family": "DejaVu Sans", "font.size": 12,
    })
    fig, ax = plt.subplots(figsize=(12.6, 7.2))
    fig.subplots_adjust(top=0.82, bottom=0.11, left=0.075, right=0.97)
    # hand-placed offsets where the cloud is dense; (dx, dy, ha)
    OFF = {"USA": (-9, 6, "right"), "IRL": (-9, 6, "right"), "CH": (-9, 6, "right"),
           "DK": (-9, 6, "right"), "GBR": (7, 6, "left"), "JPN": (7, 7, "left"),
           "DE": (7, -13, "left"), "FR": (-9, -13, "right"), "IT": (-9, 6, "right"),
           "ES": (-9, -13, "right"), "NL": (-9, 7, "right"), "KOR": (7, 5, "left"),
           "BE": (-9, 6, "right"), "SI": (7, 5, "left"), "HU": (7, 5, "left"),
           "AT": (7, 4, "left"), "CAN": (7, 4, "left"), "MEX": (7, -12, "left"),
           "TUR": (7, 6, "left"), "PL": (7, -13, "left")}
    for d in pts:
        big = d["geo"] in OFF
        c = (ORANGE if d["geo"] == "TUR" else
             GREEN if d["share"] >= 2 else (BLUE if big else MUTED))
        ax.scatter(d["eur"], d["share"], s=74 if big else 34, color=c, zorder=3,
                   edgecolors=SURFACE, linewidths=1.6)
        if big:
            dx, dy, ha = OFF[d["geo"]]
            ax.annotate(d["name"], (d["eur"], d["share"]), xytext=(dx, dy),
                        textcoords="offset points", ha=ha, zorder=4,
                        color=INK if d["share"] >= 2 or d["geo"] == "TUR" else INK2,
                        fontsize=10.5)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlim(0.03, 400)
    ax.set_xticks([0.1, 0.5, 1, 5, 10, 30, 100, 300])
    ax.get_xaxis().set_major_formatter(FuncFormatter(lambda v, _: f"€{v:g}bn"))
    ax.set_yticks([0.05, 0.1, 0.5, 1, 2, 5, 10, 20])
    ax.get_yaxis().set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}%"))
    ax.set_xlabel("Pharmaceutical value added, € billion (log scale)")
    ax.set_ylabel("Share of the economy (log scale)")
    fig.text(0.075, 0.965, "Size and weight are different questions",
             fontsize=17, fontweight="bold", color=INK, va="top")
    fig.text(0.075, 0.915,
             "Pharmaceutical value added, most recent year each. The United States produces "
             "the most\n(\u20ac212bn) at 0.87% of its economy; Ireland produces \u20ac83bn at 16.7%. "
             "Only four countries sit in both corners.",
             fontsize=11.5, color=INK2, va="top", linespacing=1.5)
    path = os.path.join(OUT, "11_size_vs_share.png")
    fig.savefig(path, dpi=110); plt.close(fig)
    print("wrote", path)


def main():
    rs = rows()
    chart(rs)
    page = os.path.join(ROOT, "pharma-gdp-share.html")
    s = open(page).read()
    block = re.search(r"(<!-- TABLE-42-START -->)(.*?)(<!-- TABLE-42-END -->)", s, re.S)
    if block:
        s = s[:block.start(2)] + "\n" + html_table(rs) + "        " + s[block.end(2):]
        open(page, "w").write(s)
        print(f"table written into the page ({len(rs)} rows)")
    else:
        print("markers not found — table not injected")
    n_eur = sum(1 for d in rs if d["eur"])
    print(f"{len(rs)} countries, {n_eur} with a euro figure")
    for d in rs[:6]:
        print(f"  {d['name']:<16}{d['share']:>6.2f}%  "
              f"{('€%.1fbn' % d['eur']) if d['eur'] else '—':>10}  {d['year']}")


if __name__ == "__main__":
    main()
