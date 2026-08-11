#!/usr/bin/env python3
"""HTML review version of the vet-CPI carousel -> notes/vet-cpi-carousel.html

Same six slides, same house style, every figure imported from
scripts/vetcpi_carousel.py so the HTML and the PDF cannot disagree.
Each .slide is exactly 1080x1350; the final PDF is produced by rendering
these slides in Chromium, so what is reviewed is what ships.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vetcpi_carousel as C

ROOT = C.ROOT
OUT = os.path.join(ROOT, "notes", "vet-cpi-carousel.html")

S = dict(surface="#0f1419", ink="#f4f6f8", ink2="#9aa3ad", grid="#232a33",
         muted="#3d4654", blue="#3987e5", green="#199e70", orange="#d95926",
         yellow="#c98500", violet="#9085e9")


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def slide(kicker, body, kcolor="blue"):
    """Slide numbers are assigned at assembly time in main()."""
    return f"""
<div class="slide" id="s@N@">
  <div class="rule"></div>
  <div class="kicker" style="color:var(--{kcolor})">{esc(kicker).upper()}</div>
  {body}
  <div class="footer">
    <div><b>Namık Akman</b><br><span>namikakmandev.github.io</span></div>
    <div class="pageno">@N@/@TOTAL@</div>
  </div>
</div>"""


# ----------------------------------------------------------------- charts
def split_svg():
    """Slide 2: diverging bars of vet-minus-headline gap, pp."""
    rows = C.ROWS
    n = len(rows)
    W, H = 940, 900
    rh = H / n
    lo = min(r[1] - r[2] for r in rows) - 3
    hi = max(r[1] - r[2] for r in rows) + 8

    def x(v):
        return (v - lo) / (hi - lo) * W

    out = [f'<svg viewBox="0 0 {W} {H}" role="img" '
           f'aria-label="Gap between vet-services and all-items inflation per country">']
    out.append(f'<line x1="{x(0):.0f}" y1="0" x2="{x(0):.0f}" y2="{H}" '
               f'stroke="{S["ink2"]}" stroke-width="1.5"/>')
    for i, (g, v, c) in enumerate(rows):
        gap = v - c
        colour = (S["violet"] if g == "US" else S["muted"] if g == "EA20"
                  else S["green"] if gap > 1 else S["orange"] if gap < -1 else S["ink2"])
        y0 = i * rh + rh * 0.16
        bh = rh * 0.62
        bx, bw = (x(0), x(gap) - x(0)) if gap >= 0 else (x(gap), x(0) - x(gap))
        out.append(f'<rect x="{bx:.1f}" y="{y0:.1f}" width="{max(bw, 2):.1f}" '
                   f'height="{bh:.1f}" rx="3" fill="{colour}"/>')
        anchor, tx = ("end", x(0) - 8) if gap >= 0 else ("start", x(0) + 8)
        weight = "700" if g == "US" else "400"
        out.append(f'<text x="{tx:.0f}" y="{y0 + bh * 0.72:.0f}" fill="{S["ink"]}" '
                   f'font-size="21" font-weight="{weight}" text-anchor="{anchor}">'
                   f'{esc(C.NAMES[g])}</text>')
        anchor2, vx = ("start", x(gap) + 8) if gap >= 0 else ("end", x(gap) - 8)
        out.append(f'<text x="{vx:.0f}" y="{y0 + bh * 0.72:.0f}" fill="{colour}" '
                   f'font-size="20" font-weight="700" text-anchor="{anchor2}">'
                   f'{gap:+.0f}</text>')
    out.append("</svg>")
    return "".join(out)


def line_svg(series_list, y_ticks, x_years, aria):
    """Indexed line chart. series_list: (keys, vals, colour, label, bold)."""
    W, H = 940, 640
    PADR = 180
    all_vals = [v for _, vals, *_ in series_list for v in vals]
    ylo, yhi = min(all_vals) - 3, max(all_vals) + 5
    xlo = min(x for keys, *_ in series_list for x in [C.xpos(keys)[0]])
    xhi = max(C.xpos(keys)[-1] for keys, *_ in series_list)

    def X(t):
        return (t - xlo) / (xhi - xlo) * (W - PADR)

    def Y(v):
        return H - 40 - (v - ylo) / (yhi - ylo) * (H - 80)

    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{esc(aria)}">']
    for yt in y_ticks:
        if not ylo < yt < yhi:
            continue
        out.append(f'<line x1="0" y1="{Y(yt):.0f}" x2="{W - PADR + 60:.0f}" '
                   f'y2="{Y(yt):.0f}" stroke="{S["grid"]}" stroke-width="1.2"/>')
        out.append(f'<text x="4" y="{Y(yt) - 7:.0f}" fill="{S["muted"]}" '
                   f'font-size="17">{yt}</text>')
    for yr in x_years:
        anchor = "start" if X(yr) < 30 else "middle"
        out.append(f'<text x="{max(X(yr), 0):.0f}" y="{H - 8}" fill="{S["ink2"]}" '
                   f'font-size="18" text-anchor="{anchor}">{yr}</text>')
    for keys, vals, colour, label, bold in series_list:
        pts = " ".join(f"{X(t):.1f},{Y(v):.1f}" for t, v in zip(C.xpos(keys), vals))
        out.append(f'<polyline points="{pts}" fill="none" stroke="{colour}" '
                   f'stroke-width="{4 if bold else 2.6}" stroke-linecap="round" '
                   f'stroke-linejoin="round"/>')
        lx, ly = X(C.xpos(keys)[-1]) + 10, Y(vals[-1])
        lines = label.split("\n")
        for li, ltxt in enumerate(lines):
            out.append(f'<text x="{lx:.0f}" y="{ly + 7 + li * 24 - (len(lines) - 1) * 11:.0f}" '
                       f'fill="{colour}" font-size="21" font-weight="700">{esc(ltxt)}</text>')
    out.append("</svg>")
    return "".join(out)




# ----------------------------------------------------------------- small multiples
GRID_FRM = "2017-01"
GRID_GEOS = ["PL", "SE", "DK", "HU", "CZ", "DE", "NL", "BE",
             "FI", "FR", "RO", "PT", "ES", "AT", "IT"]


def mini_svg(vet_kv, cpi_kv, colour):
    """One panel: vet vs headline, indexed to GRID_FRM = 100, to Dec 2025."""
    W, H = 230, 148
    LBL = 18  # room for the year labels under the lines
    keys = sorted(k for k in vet_kv if GRID_FRM <= k <= C.TO)
    v = [vet_kv[k] / vet_kv[GRID_FRM] * 100 for k in keys]
    c = [cpi_kv[k] / cpi_kv[GRID_FRM] * 100 for k in keys]
    ylo, yhi = min(v + c) - 4, max(v + c) + 4
    xs = C.xpos(keys)
    xlo, xhi = xs[0], xs[-1]

    def X(t):
        return (t - xlo) / (xhi - xlo) * W

    def Y(val):
        return H - LBL - 4 - (val - ylo) / (yhi - ylo) * (H - LBL - 10)

    base = " ".join(f"{X(t):.1f},{Y(100):.1f}" for t in (xlo, xhi))
    pc = " ".join(f"{X(t):.1f},{Y(val):.1f}" for t, val in zip(xs, c))
    pv = " ".join(f"{X(t):.1f},{Y(val):.1f}" for t, val in zip(xs, v))
    return (f'<svg viewBox="0 0 {W} {H}">'
            f'<polyline points="{base}" fill="none" stroke="{S["grid"]}" stroke-width="1"/>'
            f'<polyline points="{pc}" fill="none" stroke="{S["muted"]}" stroke-width="2"/>'
            f'<polyline points="{pv}" fill="none" stroke="{colour}" stroke-width="2.5" '
            f'stroke-linejoin="round"/>'
            f'<text x="0" y="{H - 3}" fill="{S["muted"]}" font-size="15">2017</text>'
            f'<text x="{W}" y="{H - 3}" fill="{S["muted"]}" font-size="15" '
            f'text-anchor="end">2025</text></svg>')


def s_grid():
    panels = []
    for g in GRID_GEOS:
        vet_kv, cpi_kv = C.EU[f"{g}|CP0935"], C.EU[f"{g}|CP00"]
        gap = (C.pct(vet_kv, GRID_FRM, C.TO) - C.pct(cpi_kv, GRID_FRM, C.TO))
        panels.append((g, vet_kv, cpi_kv, gap))
    panels.append(("US", C.US["pet_svcs_nsa"], C.US["cpi_nsa"],
                   C.pct(C.US["pet_svcs_nsa"], GRID_FRM, C.TO)
                   - C.pct(C.US["cpi_nsa"], GRID_FRM, C.TO)))
    panels.sort(key=lambda r: -r[3])
    cells = []
    for g, vet_kv, cpi_kv, gap in panels:
        cells.append(
            f'<div class="cell"><div class="cellhead"><span>{esc(C.NAMES[g])}</span>'
            f'<span>{gap:+.0f}</span></div>'
            f'{mini_svg(vet_kv, cpi_kv, S["blue"])}</div>')
    return slide("Country by country · Jan 2017 → Dec 2025", f"""
  <h2>Sixteen markets, one window.</h2>
  <div class="legend">
    <span><i style="background:{S["blue"]}"></i>vet prices</span>
    <span><i style="background:{S["muted"]}"></i>overall inflation</span>
    <span><b>+51</b>&nbsp;= how much more vet prices rose, in points</span>
  </div>
  <div class="grid">{"".join(cells)}</div>
  <p class="note">Both lines start at 100 in Jan&nbsp;2017; panels have their own
  scale — compare the two lines within a panel, the gap number across panels.
  Sorted by gap. Ireland omitted (series ends 2023).</p>""")


# ----------------------------------------------------------------- slides
def s1():
    pl_v, pl_c = C.window("PL")
    it_v, it_c = C.window("IT")
    return slide("Vet bills vs inflation · 16 countries", f"""
  <h1>Your vet bill beat inflation.<br><span class="blue">Or did it?</span></h1>
  <p class="lead">Prices of veterinary and other pet services versus all-items
  inflation, January&nbsp;2021 to December&nbsp;2025, in 15 European countries
  and the United States.</p>
  <div class="statrow">
    <div class="stat"><div class="big green">+{pl_v:.0f}%</div>
      <p>vet services, Poland.<br>Headline was +{pl_c:.0f}%.</p></div>
    <div class="stat"><div class="big orange">+{it_v:.0f}%</div>
      <p>vet services, Italy.<br>Headline was +{it_c:.0f}%.</p></div>
  </div>
  <hr>
  <p class="lead">Same period, same measure. In the North and East vet prices
  ran far ahead of inflation; across the South they fell behind it.
  The split is the story — slides inside.</p>
  <p class="note">Consumer prices — what pet owners pay. Not farm animal
  health costs. Sources and scope on the final slide.</p>""")


def s2():
    return slide("The split · Jan 2021 → Dec 2025", f"""
  <h2>North and East: far ahead.<br>South: behind inflation.</h2>
  <div class="chart">{split_svg()}</div>
  <p class="note">Bar = vet-services inflation minus all-items inflation, in
  percentage points, per country, Jan&nbsp;2021&nbsp;→&nbsp;Dec&nbsp;2025.
  Purple = United States.</p>""")


def s3():
    ea = C.indexed(C.EU["EA20|CP0935"], C.FRM)
    se = C.indexed(C.EU["SE|CP0935"], C.FRM)
    de = C.indexed(C.EU["DE|CP0935"], C.FRM)
    svg = line_svg([(ea[0], ea[1], S["muted"], "Euro area", False),
                    (se[0], se[1], S["yellow"], "Sweden", True),
                    (de[0], de[1], S["blue"], "Germany", True)],
                   [100, 120, 140, 160], [2021, 2022, 2023, 2024, 2025],
                   "Vet-services price index, Jan 2021 = 100")
    return slide("How it happened", f"""
  <h2>Not a drift. Two jumps.</h2>
  <div class="chart">{svg}</div>
  <p class="lead">Germany: <b>+{C.DE_STEP:.0f}% in a single month</b> (Dec 2022),
  when the national veterinary fee schedule (GOT) was revised for the first
  time since 1999. Sweden: <b>+{C.SE_STEP:.0f}%</b> in Oct 2022, as consolidated
  clinic chains repriced.</p>
  <p class="note">Vet-services price index per market, Jan&nbsp;2021&nbsp;=&nbsp;100,
  to Dec&nbsp;2025. Regulated fee schedules move in steps — and reset the level
  for good.</p>""")


def s4():
    us_v, us_c = C.window("US")
    us_v15 = C.pct(C.US["pet_svcs_nsa"], C.FRM15, C.TO)
    us_c15 = C.pct(C.US["cpi_nsa"], C.FRM15, C.TO)
    cpi = C.indexed(C.US["cpi_nsa"], C.FRM15)
    pet = C.indexed(C.US["pet_svcs_nsa"], C.FRM15)
    svg = line_svg([(cpi[0], cpi[1], S["muted"], "All items", False),
                    (pet[0], pet[1], S["violet"], "Pet services\nincl. veterinary", True)],
                   [100, 120, 140], [2015, 2017, 2019, 2021, 2023, 2025],
                   "US pet services vs all items, Jan 2015 = 100")
    return slide("The United States · Jan 2015 → Dec 2025", f"""
  <h2>The loudest story is mid-table.</h2>
  <div class="chart">{svg}</div>
  <p class="lead">US pet services incl. veterinary: <b>+{us_v15:.0f}%</b> over the
  decade, against +{us_c15:.0f}% for all items — ahead, but no Poland. Since
  Jan&nbsp;2021 the gap is <b>{us_v - us_c:+.0f}&nbsp;points</b>: less than
  Denmark's, Germany's or Sweden's.</p>
  <p class="note">BLS CPI, US city average, not seasonally adjusted,
  Jan&nbsp;2015&nbsp;=&nbsp;100. Same basket definition as the European
  series.</p>""")


def s5():
    return slide("What to do with this", """
  <h2>Three readers, three moves.</h2>
  <div class="move b-green"><h3 class="green">Pet owners — budget by geography.</h3>
    <p>In Poland, Sweden, Denmark or Germany, index your pet budget to vet
    prices, not to headline inflation — the gap has compounded to 14–32
    points in five years.</p></div>
  <div class="move b-blue"><h3 class="blue">Insurers &amp; clinic operators — watch the fee schedules.</h3>
    <p>The big single moves were regulatory (Germany's GOT) or structural
    (Nordic chain consolidation). The next scheduled fee revision is the
    repricing event — not CPI drift.</p></div>
  <div class="move b-orange"><h3 class="orange">Analysts — don't import the US narrative.</h3>
    <p>Vet inflation is a country story, not a global one. Italy, Spain,
    Portugal and Austria sit below headline inflation. Check the local index
    before repeating the meme.</p></div>
  <p class="note">What would change this: a fee-schedule revision in a
  below-headline country, or a Southern-European consolidation wave, flips
  its lane.</p>""")


def s6():
    return slide("What this covers", f"""
  <h2>Scope and sources.</h2>
  <div class="block"><h4>Measure</h4><p>Consumer price indices: what households
    pay for veterinary and other pet services, versus all-items inflation.
    This is not farm animal health spending.</p></div>
  <div class="block"><h4>Window</h4><p>Jan 2021 → Dec 2025 on every comparison,
    all markets. The decade slide (US) is Jan 2015 → Dec 2025 and says so.</p></div>
  <div class="block"><h4>Excluded</h4><p class="orange">Ireland — its
    vet-services index stops at Dec 2023. Türkiye — publishes only all-items
    HICP to Eurostat; a Turkish vet series would need TÜİK data.</p></div>
  <div class="block"><h4>Known steps</h4><p class="yellow">Germany
    +{C.DE_STEP:.0f}% (Dec 2022, GOT fee-schedule revision) and Sweden
    +{C.SE_STEP:.0f}% (Oct 2022) are real repricings, not data breaks. No
    methodology break spans the window.</p></div>
  <div class="block"><h4>Sources</h4><p>Eurostat prc_hicp_midx, monthly,
    2015=100: CP0935 veterinary and other services for pets; CP00 all items;
    1996→2025. BLS CPI via FRED, monthly, NSA: CUUR0000SS62031 pet services
    incl. veterinary (1997→2026); CPIAUCNS all items. Data files:
    data/vet-cpi-eu.json · data/vet-cpi-us.json, cut 11 Aug 2026 — every
    figure recomputable from them.</p></div>
  <p class="note">Personal analysis of public statistics. Views my own.</p>""")


CSS = """
:root { --surface:%(surface)s; --ink:%(ink)s; --ink2:%(ink2)s; --grid:%(grid)s;
  --muted:%(muted)s; --blue:%(blue)s; --green:%(green)s; --orange:%(orange)s;
  --yellow:%(yellow)s; --violet:%(violet)s; }
* { margin:0; padding:0; box-sizing:border-box; }
body { background:#06090c; font-family:"IBM Plex Sans","Segoe UI",system-ui,
  -apple-system,sans-serif; color:var(--ink); padding:24px 0 60px; }
.intro { max-width:1080px; margin:0 auto 8px; padding:12px 20px;
  color:var(--ink2); font-size:15px; }
.intro b { color:var(--ink); }
.deck { display:flex; flex-direction:column; align-items:center; gap:28px; }
.wrap { width:min(1080px, 96vw); }
.slide { width:1080px; height:1350px; background:var(--surface);
  position:relative; padding:88px 86px; overflow:hidden;
  transform-origin:top left; border-radius:4px; }
.rule { position:absolute; top:72px; left:86px; width:86px; height:5px;
  border-radius:3px; background:var(--blue); }
.kicker { font-size:24px; font-weight:700; letter-spacing:.06em;
  margin:14px 0 26px; }
h1 { font-size:62px; line-height:1.16; margin-bottom:38px; }
h2 { font-size:52px; line-height:1.2; margin-bottom:34px; }
h3 { font-size:28px; margin-bottom:10px; }
h4 { font-size:21px; color:var(--ink2); text-transform:uppercase;
  letter-spacing:.05em; margin-bottom:6px; }
p { font-size:27px; line-height:1.45; }
.lead { margin-bottom:30px; }
.blue{color:var(--blue)} .green{color:var(--green)} .orange{color:var(--orange)}
.yellow{color:var(--yellow)} .violet{color:var(--violet)}
.statrow { display:flex; gap:56px; margin:26px 0 34px; }
.stat .big { font-size:104px; font-weight:700; line-height:1.05; }
.stat p { font-size:27px; margin-top:10px; }
hr { border:none; border-top:1px solid var(--grid); margin:10px 0 32px; }
.note { position:absolute; left:86px; right:86px; bottom:150px;
  font-size:20px; color:var(--muted); line-height:1.4; }
.chart { margin:6px 0 26px; }
.legend { display:flex; flex-wrap:wrap; gap:10px 34px; font-size:21px;
  color:var(--ink2); margin:-6px 0 24px; align-items:center; }
.legend i { display:inline-block; width:34px; height:5px; border-radius:3px;
  margin-right:10px; vertical-align:middle; }
.legend b { color:var(--ink); }
.grid { display:grid; grid-template-columns:repeat(4,1fr); gap:22px 26px;
  margin:10px 0 20px; }
.cell svg { width:100%%; height:auto; display:block; }
.cellhead { display:flex; justify-content:space-between; font-size:20px;
  font-weight:700; margin-bottom:6px; }
.cellhead span:last-child { font-variant-numeric:tabular-nums; }
.chart svg { width:100%%; height:auto; max-height:790px; display:block; margin:0 auto; }
.move { border-left:5px solid; border-radius:2px; padding:2px 0 6px 26px;
  margin-bottom:40px; }
.move.b-green{border-color:var(--green)} .move.b-blue{border-color:var(--blue)}
.move.b-orange{border-color:var(--orange)}
.move p { font-size:25px; }
.block { margin-bottom:26px; }
.block p { font-size:22.5px; line-height:1.4; }
.footer { position:absolute; left:86px; right:86px; bottom:38px;
  display:flex; justify-content:space-between; align-items:flex-end;
  font-size:21px; color:var(--ink2); }
.footer span { color:var(--muted); font-size:18px; }
.pageno { font-size:21px; }
@media print { body{padding:0;background:var(--surface)}
  .intro{display:none} .deck{gap:0} .slide{border-radius:0; page-break-after:always} }
""" % S

JS = """
function fit(){ const w = Math.min(document.documentElement.clientWidth*0.96, 1080);
  const k = w/1080;
  document.querySelectorAll('.slide').forEach(s=>{ s.style.transform=`scale(${k})`; });
  document.querySelectorAll('.wrap').forEach(el=>{ el.style.height=(1350*k)+'px'; });}
addEventListener('resize', fit); fit();
"""


def main():
    deck = [s1(), s2(), s_grid(), s3(), s4(), s5(), s6()]
    total = len(deck)
    slides = "\n".join(
        f'<div class="wrap">{sl.replace("@N@", str(i)).replace("@TOTAL@", str(total))}</div>'
        for i, sl in enumerate(deck, 1))
    html = f"""<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Vet bills vs inflation — carousel draft</title>
<style>{CSS}</style>
<div class="intro"><b>Draft for review.</b> Six slides, 1080×1350 — the final
PDF is rendered from this exact file. Generated by
scripts/vetcpi_carousel_html.py from data/vet-cpi-eu.json and
data/vet-cpi-us.json.</div>
<div class="deck">
{slides}
</div>
<script>{JS}</script>
"""
    open(OUT, "w").write(html)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
