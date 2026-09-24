#!/usr/bin/env python3
"""LinkedIn carousel for the debt study (part two of the bond study).

  -> notes/debt-carousel.pdf, notes/debt-carousel.html
  -> assets/linkedin/debt-*.svg and .png (the charts, also usable on their own)

Seven portrait slides at 7.2 x 9 inches, the 4:5 page LinkedIn wants for a
document post and the same MediaBox as the other carousels in notes/. Every
number is read out of data/debt-study.json, so the deck cannot drift from
debt.html.

  python3 scripts/debt_study.py
  python3 scripts/debt_carousel.py [--proof]
"""
import json, os, re, subprocess, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fte_chart import find_chrome, render_png, _crop_png as crop          # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "notes", "debt-carousel.pdf")
RES = os.path.join(ROOT, "data", "debt-study.json")
ART = os.path.join(ROOT, "assets", "linkedin")

INK, DIM, MUTED, RULE, PAPER = "#1f2430", "#5b6472", "#8a9099", "#e3e8ee", "#ffffff"
RED, GREEN = "#d94040", "#2e9e5b"
# the study's own colours, validated (scripts/validate_palette.js, light surface): all checks pass
PRIMARY, INTEREST, INFLATION, REAL = "#1c63c9", "#d9541e", "#7b3fd1", "#138a5a"
C = {"US": "#1c63c9", "GB": "#d9541e", "FR": "#7b3fd1", "IT": "#b7791f", "ES": "#0a8fb0"}
NAMES = {"US": "United States", "GB": "United Kingdom", "FR": "France", "IT": "Italy", "DE": "Germany",
         "JP": "Japan", "ES": "Spain", "NL": "Netherlands", "AU": "Australia"}
FONT = ("-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,"
        "'Helvetica Neue',Arial,sans-serif")


def open_svg(W, H, label):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
            f'font-family="{FONT}" role="img" aria-label="{label}">',
            f'<rect width="{W}" height="{H}" fill="{PAPER}"/>']


def nice(lo, hi, step):
    t, v = [], (lo // step) * step
    while v <= hi + 1e-9:
        if v >= lo - 1e-9:
            t.append(round(v, 6))
        v += step
    return t


def xaxis(o, X, ticks, y0, y1, fmt=lambda t: f"{t:+.0f}" if t else "0"):
    for t in ticks:
        o.append(f'<line x1="{X(t):.1f}" x2="{X(t):.1f}" y1="{y0}" y2="{y1}" stroke="{INK if t == 0 else RULE}" '
                 f'stroke-width="{1.4 if t == 0 else 1}"/>')
        o.append(f'<text x="{X(t):.1f}" y="{y1 + 18}" font-size="13" fill="{DIM}" text-anchor="middle">{fmt(t)}</text>')


def chart_without_inflation(S, order):
    """Dumbbell: the actual change in each debt ratio over 2021-25, and the change
    with the inflation term taken out. Every row crosses zero or moves right."""
    W, rowh, L, R, T = 700, 44, 132, 30, 46
    H = T + rowh * len(order) + 40
    rows = [(c, S[c]["dynamics"]["2021-25"]) for c in order]
    vals = [d["d_change"] for _, d in rows] + [d["d_change"] - d["c_inflation"] for _, d in rows]
    lo, hi = min(vals) - 9, max(vals) + 4
    X = lambda v: L + (v - lo) / (hi - lo) * (W - L - R)
    o = open_svg(W, H, "Change in debt ratio 2021-25, actual and without inflation")
    o.append(f'<text x="{L}" y="18" font-size="13" fill="{DIM}">Change in gross debt, points of GDP, 2021–25:  '
             f'<tspan fill="{DIM}" font-weight="700">&#9679;</tspan> actual   '
             f'<tspan fill="{RED}" font-weight="700">&#9679;</tspan> without inflation</text>')
    xaxis(o, X, nice(lo, hi, 10), T - 10, H - 34)
    for i, (c, d) in enumerate(sorted(rows, key=lambda r: r[1]["d_change"])):
        y = T + i * rowh + rowh / 2
        a, b = d["d_change"], d["d_change"] - d["c_inflation"]
        o.append(f'<text x="{L - 14}" y="{y + 5}" font-size="15" fill="{INK}" text-anchor="end">{NAMES[c]}</text>')
        o.append(f'<line x1="{X(a):.1f}" x2="{X(b):.1f}" y1="{y}" y2="{y}" stroke="{MUTED}" stroke-width="2.5"/>')
        o.append(f'<circle cx="{X(a):.1f}" cy="{y}" r="7" fill="{DIM}" stroke="#fff" stroke-width="2"/>')
        o.append(f'<circle cx="{X(b):.1f}" cy="{y}" r="7" fill="{RED}" stroke="#fff" stroke-width="2"/>')
        o.append(f'<text x="{X(b) + 13:.1f}" y="{y + 5}" font-size="13" font-weight="700" fill="{INK}">{b:+.1f}</text>')
        o.append(f'<text x="{X(a) - 13:.1f}" y="{y + 5}" font-size="13" fill="{DIM}" text-anchor="end">{a:+.1f}</text>')
    o.append("</svg>")
    return "".join(o)


def chart_forces(S, order, window, title):
    """Diverging stacked bars: primary deficit and interest push right, real growth and
    inflation push left; the residual is left out of the bar and shown as a number."""
    parts = [("c_primary", PRIMARY), ("c_interest", INTEREST), ("c_inflation", INFLATION), ("c_real", REAL)]
    W, rowh, L, R, T = 700, 40, 150, 70, 34
    H = T + rowh * len(order) + 40
    lo = min(sum(min(0, S[c]["dynamics"][window][k]) for k, _ in parts) for c in order)
    hi = max(sum(max(0, S[c]["dynamics"][window][k]) for k, _ in parts) for c in order)
    lo, hi = min(-50, lo - 2), max(50, hi + 2)
    X = lambda v: L + (v - lo) / (hi - lo) * (W - L - R)
    o = open_svg(W, H, title)
    o.append(f'<text x="{L}" y="16" font-size="13" fill="{DIM}">{title}</text>')
    xaxis(o, X, nice(lo, hi, 20), T - 6, H - 34)
    for i, c in enumerate(order):
        d = S[c]["dynamics"][window]
        y = T + i * rowh + 8
        h = rowh - 16
        o.append(f'<text x="{L - 14}" y="{y + h / 2 + 5}" font-size="15" fill="{INK}" text-anchor="end">{NAMES[c]}</text>')
        pos = neg = 0
        for k, col in parts:
            v = d[k]
            if not v:
                continue
            a = pos if v > 0 else neg + v
            if v > 0:
                pos += v
            else:
                neg += v
            w = X(a + abs(v)) - X(a)
            o.append(f'<rect x="{X(a) + 1:.1f}" y="{y}" width="{max(0.5, w - 2):.1f}" height="{h}" fill="{col}" rx="2"/>')
        net = d["d_change"]
        o.append(f'<path d="M{X(net):.1f} {y - 4}l6 {h / 2 + 4}l-6 {h / 2 + 4}l-6 {-h / 2 - 4}z" fill="#fff" stroke="{INK}" stroke-width="2"/>')
        o.append(f'<text x="{W - 6}" y="{y + h / 2 + 5}" font-size="13" font-weight="700" fill="{INK}" text-anchor="end">{net:+.1f}</text>')
    o.append("</svg>")
    return "".join(o)


def chart_revenue(S, cs):
    """Net interest as a share of revenue, 1990-2031, dashed after the last actual year."""
    W, H, L, R, T, B = 700, 470, 52, 118, 20, 34
    la = S["_last"]
    ser = {c: [(int(y), v) for y, v in S[c]["series"]["interest_rev"] if v is not None] for c in cs}
    x0, x1 = 1990, 2031
    hi = 26
    X = lambda x: L + (x - x0) / (x1 - x0) * (W - L - R)
    Y = lambda v: T + (hi - v) / hi * (H - T - B)
    o = open_svg(W, H, "Net interest as a share of government revenue")
    for t in range(0, hi + 1, 5):
        o.append(f'<line x1="{L}" x2="{W - R}" y1="{Y(t):.1f}" y2="{Y(t):.1f}" stroke="{INK if t == 0 else RULE}"/>')
        o.append(f'<text x="{L - 8}" y="{Y(t) + 5:.1f}" font-size="13" fill="{DIM}" text-anchor="end">{t}%</text>')
    for yr in range(1990, 2031, 10):
        o.append(f'<text x="{X(yr):.1f}" y="{H - 10}" font-size="13" fill="{DIM}" text-anchor="middle">{yr}</text>')
    o.append(f'<rect x="{X(int(la)):.1f}" y="{T}" width="{X(x1) - X(int(la)):.1f}" height="{H - T - B}" fill="#f3f4f6"/>')
    o.append(f'<text x="{X(int(la)) + 6:.1f}" y="{T + 14}" font-size="12" fill="{DIM}">IMF projection</text>')
    ends = []
    for c in cs:
        pts = ser[c]
        a = [p for p in pts if p[0] <= int(la)]
        b = [p for p in pts if p[0] >= int(la)]
        for seg, dash in ((a, ""), (b, ' stroke-dasharray="6 5"')):
            if len(seg) > 1:
                d = "M" + "L".join(f"{X(x):.1f} {Y(v):.1f}" for x, v in seg)
                o.append(f'<path d="{d}" fill="none" stroke="{C[c]}" stroke-width="2.6"{dash} stroke-linejoin="round"/>')
        ends.append([Y(pts[-1][1]), c, pts[-1][1]])
    ends.sort()
    for i in range(1, len(ends)):                      # keep end labels apart
        if ends[i][0] - ends[i - 1][0] < 17:
            ends[i][0] = ends[i - 1][0] + 17
    for y, c, v in ends:
        o.append(f'<text x="{W - R + 8}" y="{y + 5:.1f}" font-size="13" fill="{INK}"><tspan fill="{C[c]}" font-weight="700">&#9632;</tspan> {NAMES[c].replace("United ", "U. ")} {v:.1f}</text>')
    pk = max(ser["IT"], key=lambda p: p[1])
    o.append(f'<text x="{X(pk[0]) + 8:.1f}" y="{Y(pk[1]) + 4:.1f}" font-size="12.5" fill="{DIM}">Italy {pk[0]}: {pk[1]:.1f}%</text>')
    o.append("</svg>")
    return "".join(o)


def chart_rates(S, order):
    """Dot plot, 2031: IMF nominal growth, the IMF's rate on the debt, and the rate on the
    debt if the ten-year stays at today's level and the stock reprices at the pooled speed."""
    W, rowh, L, R, T = 700, 42, 150, 24, 50
    H = T + rowh * len(order) + 40
    X = lambda v: L + v / 5 * (W - L - R)
    o = open_svg(W, H, "Rate on the debt in 2031 against growth")
    o.append(f'<text x="{L}" y="18" font-size="13" fill="{DIM}">2031, per cent a year: '
             f'<tspan fill="{MUTED}" font-weight="700">&#9679;</tspan> nominal growth (IMF)  '
             f'<tspan fill="{PRIMARY}" font-weight="700">&#9679;</tspan> rate on the debt (IMF)</text>')
    o.append(f'<text x="{L}" y="36" font-size="13" fill="{DIM}">'
             f'<tspan fill="{RED}" font-weight="700">&#9679;</tspan> rate on the debt if the ten-year stays where it is</text>')
    xaxis(o, X, [0, 1, 2, 3, 4, 5], T - 4, H - 34, fmt=lambda t: f"{t:.0f}%")
    for i, c in enumerate(order):
        k = S[c]
        y = T + i * rowh + rowh / 2
        crossed = k["r_minus_g_2031_at_market"] > 0
        o.append(f'<text x="{L - 14}" y="{y + 5}" font-size="15" fill="{INK}" text-anchor="end"'
                 f'{" font-weight=&quot;700&quot;" if crossed else ""}>{NAMES[c]}</text>'.replace("&quot;", '"'))
        vs = [k["g_2031"], k["r_2031"], k["r_2031_at_market"]]
        o.append(f'<line x1="{X(min(vs)):.1f}" x2="{X(max(vs)):.1f}" y1="{y}" y2="{y}" stroke="{RULE}" stroke-width="3"/>')
        for v, col in zip(vs, (MUTED, PRIMARY, RED)):
            o.append(f'<circle cx="{X(v):.1f}" cy="{y}" r="7.5" fill="{col}" stroke="#fff" stroke-width="2"/>')
        if crossed:
            o.append(f'<text x="{X(max(vs)) + 14:.1f}" y="{y + 5}" font-size="12.5" font-weight="700" fill="{RED}">r &gt; g</text>')
    o.append("</svg>")
    return "".join(o)


def chart_gap(S, order):
    """Bars: projected 2031 primary balance minus the one that holds the debt ratio if the
    whole stock paid today's ten-year yield. Negative = the ratio rises."""
    rows = sorted(((c, S[c]["gap_at_market"]) for c in order), key=lambda r: r[1])
    W, rowh, L, R, T = 700, 42, 150, 60, 30
    H = T + rowh * len(rows) + 40
    lo, hi = -5, 1
    X = lambda v: L + (v - lo) / (hi - lo) * (W - L - R)
    o = open_svg(W, H, "Budget gap at today's yields")
    o.append(f'<text x="{L}" y="16" font-size="13" fill="{DIM}">Points of GDP, 2031. Left of zero: the IMF&#8217;s budget lets the debt ratio rise</text>')
    xaxis(o, X, [-5, -4, -3, -2, -1, 0, 1], T - 4, H - 34, fmt=lambda t: f"{t:+.0f}" if t else "0")
    for i, (c, v) in enumerate(rows):
        y = T + i * rowh + 9
        h = rowh - 18
        col = RED if v < 0 else GREEN
        a, b = (X(v), X(0)) if v < 0 else (X(0), X(v))
        o.append(f'<text x="{L - 14}" y="{y + h / 2 + 5}" font-size="15" fill="{INK}" text-anchor="end">{NAMES[c]}</text>')
        o.append(f'<rect x="{a:.1f}" y="{y}" width="{max(1, b - a):.1f}" height="{h}" fill="{col}" rx="3"/>')
        lx = a - 8 if v < 0 else b + 8
        o.append(f'<text x="{lx:.1f}" y="{y + h / 2 + 5}" font-size="13" font-weight="700" fill="{INK}" '
                 f'text-anchor="{"end" if v < 0 else "start"}">{v:+.1f}</text>')
    o.append("</svg>")
    return "".join(o)


def inline(s):
    return s.replace("<svg ", '<svg class="chart" preserveAspectRatio="xMidYMid meet" ', 1)


def build(web=False):
    D = json.load(open(RES))
    S, P = D["countries"], D["pass_through_pooled"]
    S["_last"] = D["weo_last_actual"]
    order = [c for c in D["core"] + D["more"] if c in S]
    n = len(order)
    infl = [S[c]["dynamics"]["2021-25"]["c_inflation"] for c in order]
    lead = [c for c in order if S[c]["dynamics"]["2026-31"]["c_interest"] > S[c]["dynamics"]["2026-31"]["c_primary"]]
    cross = [c for c in order if S[c]["r_minus_g_2031_at_market"] > 0]
    cross_imf = [c for c in order if S[c]["r_minus_g_2031"] > 0]
    us = S["US"]
    more_than_real = sum(1 for c in order if S[c]["dynamics"]["2021-25"]["c_inflation"] < S[c]["dynamics"]["2021-25"]["c_real"])
    names1 = lambda cs: ", ".join(NAMES[c] for c in cs)
    ym = us["ten_year"]["last"]
    charts = {
        "debt-without-inflation": chart_without_inflation(S, order),
        "debt-forces-2021-25": chart_forces(S, order, "2021-25", "Points of GDP added to (right) or taken off (left) gross debt, 2021–25"),
        "debt-forces-2026-31": chart_forces(S, order, "2026-31", "The same split, 2026–31, IMF projection"),
        "debt-interest-revenue": chart_revenue(S, ["US", "IT", "ES", "GB", "FR"]),
        "debt-rates-2031": chart_rates(S, order),
        "debt-budget-gap": chart_gap(S, order),
    }
    legend = (f'<p class="key"><i style="background:{PRIMARY}"></i>Primary deficit <i style="background:{INTEREST}"></i>Interest '
              f'<i style="background:{INFLATION}"></i>Inflation <i style="background:{REAL}"></i>Real growth '
              f'<span>&#9671; net change, incl. the residual</span></p>'
              f'<p class="key sm">Blue left of zero is a primary surplus.</p>')
    names = lambda cs: ", ".join(NAMES[c].replace("United States", "the US").replace("United Kingdom", "Britain") for c in cs[:-1]) + " and " + NAMES[cs[-1]].replace("United Kingdom", "Britain")
    brand = '<span class="brand">Inflation paid the debt &#183; namikakmandev.github.io/debt.html</span>'
    slides = [
        f'''<p class="kicker">Public debt, nine rich economies &#183; IMF data, 2021&#8211;25</p>
            <h1 class="tight">Rich-world debt ratios fell after the pandemic. <span class="r">Take inflation out and every one of them rose.</span></h1>
            {inline(charts["debt-without-inflation"])}''',

        f'''<p class="kicker">Five forces move a debt ratio</p>
            <h2>Budgets didn&#8217;t cut the debt. Inflation did.</h2>
            <p class="lede">All nine ran primary deficits over 2021&#8211;25. Inflation took
              <b>{-max(infl):.0f} to {-min(infl):.0f} points of GDP</b> off each ratio. That is more than real growth did in {more_than_real} of the nine.</p>
            {inline(charts["debt-forces-2021-25"])}{legend}''',

        f'''<p class="kicker">2026&#8211;31, the IMF&#8217;s own projection</p>
            <h2>From here, interest does the pushing</h2>
            <p class="lede">Inflation&#8217;s help shrinks in all nine. Interest becomes the biggest force raising debt in
              <b>{len(lead)} of {n}</b>, ahead of the budget deficit.</p>
            {inline(charts["debt-forces-2026-31"])}{legend}''',

        f'''<p class="kicker">Net interest as a share of government revenue</p>
            <h2>The US now spends {us["interest_rev_2025"]:.1f}% of its revenue on interest</h2>
            <p class="lede">Twice its 2015 share, and {us["interest_rev_2031"]:.1f}% by 2031 on the IMF&#8217;s path: above Spain&#8217;s 1990s peak.
              Italy, at {S["IT"]["interest_rev_2025"]:.1f}%, is under a third of its 1993 level.</p>
            {inline(charts["debt-interest-revenue"])}''',

        f'''<p class="kicker">How fast a higher yield reaches the debt</p>
            <div class="tiles">
              <div class="tile"><span class="val">{P["half_life"]:.0f} years</span><span class="lab">half-life of the gap between the ten-year yield and the rate paid on the debt</span></div>
              <div class="tile"><span class="val">{P["lambda"] * 100:.0f}%</span><span class="lab">of that gap closed each year, {P["n"]} country-years since 1996</span></div>
            </div>
            <p class="lede">At that speed, with yields where they are, the rate on the debt passes nominal growth by 2031 in
              <b class="r">{names(cross)}</b>. The IMF&#8217;s path has {len(cross_imf)}: {names1(cross_imf)}.</p>
            {inline(charts["debt-rates-2031"])}''',

        f'''<p class="kicker">What holding the debt ratio steady costs at today&#8217;s yields</p>
            <h2>The US is {-us["gap_at_market"]:.1f} points of GDP short. Italy, {-S["IT"]["gap_at_market"]:.1f}.</h2>
            <p class="lede">The IMF&#8217;s 2031 budget minus the one that holds each debt ratio if the whole stock paid today&#8217;s ten-year yield.
              Only Spain&#8217;s projected budget covers it.</p>
            {inline(charts["debt-budget-gap"])}''',

        f'''<p class="kicker">What to do with it</p>
            <h2>Three things to say, and one not to</h2>
            <div class="panel"><span class="n">1</span><div><b>&#8220;Flirting&#8221; is the right word.</b> The average rate is still at or below growth; the market rate is above it; the average closes about {P["lambda"] * 100:.0f}% of that gap a year.</div></div>
            <div class="panel"><span class="n">2</span><div><b>Rank by the budget gap, not the debt ratio.</b> On debt, Japan and Italy lead. On the gap, the US leads by a distance.</div></div>
            <div class="panel"><span class="n">3</span><div><b>Check the interest line in any 2031 debt path.</b> At today&#8217;s yields the IMF&#8217;s rate for the US is {us["r_2031_at_market"] - us["r_2031"]:.1f} points low.</div></div>
            <div class="panel no"><span class="n">&#215;</span><div><b>Not &#8220;they paid down pandemic debt&#8221;.</b> Inflation did. It worked because it was a surprise, and a surprise cannot be planned for twice.</div></div>
            <p class="note">Method, every number and the scripts: <b>namikakmandev.github.io/debt.html</b><br>
              IMF World Economic Outlook (debt, balances, revenue, GDP) and OECD ten-year yields via FRED, {ym}. Net interest; projections are the IMF&#8217;s.
              Canada and Korea left out: their net interest is negative.</p>''',
    ]

    css = f"""
    @page {{ size: 518.4pt 648pt; margin: 0; }}
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; padding: 0; background: {PAPER}; }}
    .s {{ width: 518.4pt; height: 648pt; padding: 44pt 40pt 40pt;
          page-break-after: always; position: relative; overflow: hidden;
          font-family: {FONT}; color: {INK}; background: {PAPER};
          display: flex; flex-direction: column; justify-content: center; }}
    .s::before {{ content: ""; position: absolute; left: 0; top: 0; width: 100%; height: 7pt; background: {INTEREST}; }}
    .s:last-child {{ page-break-after: auto; }}
    .kicker {{ font-size: 11pt; color: {DIM}; letter-spacing: .02em; text-transform: uppercase; margin: 0 0 .18in; }}
    h1 {{ font-size: 30pt; line-height: 1.14; margin: 0 0 .22in; letter-spacing: -.01em; }}
    h1.tight {{ font-size: 25pt; }}
    h2 {{ font-size: 22pt; line-height: 1.18; margin: 0 0 .14in; letter-spacing: -.01em; }}
    .lede {{ font-size: 13pt; line-height: 1.45; margin: 0 0 .14in; }}
    .note {{ font-size: 10pt; line-height: 1.5; color: {DIM}; margin: .14in 0 0; padding-top: .14in; border-top: 1px solid {RULE}; }}
    .r {{ color: {RED}; }}
    .key {{ font-size: 10.5pt; color: {DIM}; margin: 0; display: flex; flex-wrap: wrap; gap: 4pt 12pt; align-items: center; }}
    .key.sm {{ font-size: 9.5pt; margin-top: 4pt; }}
    .key i {{ display: inline-block; width: 10pt; height: 10pt; border-radius: 2pt; margin-right: -8pt; }}
    .tiles {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10pt; margin: 0 0 .16in; }}
    .tile {{ background: #f3f4f6; border-radius: 10pt; padding: 12pt 14pt 11pt; }}
    .tile .val {{ display: block; font-size: 32pt; font-weight: 700; letter-spacing: -.02em; line-height: 1.05; color: {INTEREST}; }}
    .tile .lab {{ display: block; font-size: 10.5pt; color: {DIM}; margin-top: 4pt; line-height: 1.35; }}
    .panel {{ display: flex; gap: 12pt; align-items: flex-start; background: #f3f4f6; border-radius: 10pt;
              padding: 11pt 14pt; margin: 0 0 10pt; font-size: 12.5pt; line-height: 1.42; }}
    .panel .n {{ flex: 0 0 24pt; height: 24pt; border-radius: 50%; background: {INTEREST}; color: #fff; font-weight: 700;
                 display: flex; align-items: center; justify-content: center; font-size: 13pt; }}
    .panel.no .n {{ background: {INK}; }}
    svg.chart {{ width: 100%; height: auto; max-height: 6.4in; display: block; margin: 0 0 .1in; }}
    .brand {{ position: absolute; left: 40pt; bottom: 18pt; font-size: 9.5pt; color: {DIM}; }}
    .num {{ position: absolute; right: 40pt; bottom: 18pt; font-size: 10pt; color: {DIM}; }}
    """
    body = "".join(f'<div class="s">{s_}{brand}<span class="num">{i + 1} / {len(slides)}</span></div>'
                   for i, s_ in enumerate(slides))
    if web:
        css += f"""
    body {{ background: #e9ecf0; padding: 24px 0 48px; }}
    .s {{ margin: 0 auto 24px; box-shadow: 0 6px 24px rgba(0,0,0,.12); border-radius: 6pt; }}
    .wrap {{ width: 691px; margin: 0 auto; }}
    .intro {{ max-width: 518.4pt; margin: 0 auto 18px; padding: 0 12px; font-family: {FONT}; color: {DIM}; font-size: 12pt; }}
    .intro a {{ color: {PRIMARY}; }}
    """
        body = (f'<p class="intro">The deck, as a web page. The study, every number and the scripts: '
                f'<a href="../debt.html">namikakmandev.github.io/debt.html</a>. Part one: <a href="../bonds.html">bonds.html</a>. '
                f'PDF: <a href="debt-carousel.pdf">debt-carousel.pdf</a>.</p><div class="wrap">{body}</div>'
                '<script>(function(){var w=document.querySelector(".wrap");function f(){'
                'w.style.zoom=Math.min(1,(window.innerWidth-16)/691);}'
                'window.addEventListener("resize",f);f();})();</script>')
        return (f"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
                f"<title>Inflation paid the debt &#8212; deck</title><style>{css}</style>{body}"), charts, len(slides)
    return f"<!doctype html><meta charset=utf-8><style>{css}</style>{body}", charts, len(slides)


def proof(html, n):
    """One PNG per slide, from the same HTML the PDF is printed from (see price_leverage_carousel)."""
    out = os.path.join(ART, "carousel-proof")
    os.makedirs(out, exist_ok=True)
    chrome = find_chrome()
    with tempfile.TemporaryDirectory() as tmp:
        for i in range(1, n + 1):
            page, shot = os.path.join(tmp, f"s{i}.html"), os.path.join(out, f"debt-slide-{i}.png")
            with open(page, "w") as fh:
                fh.write(html + f"<style>.s{{display:none}}.s:nth-of-type({i}){{display:flex}}</style>")
            subprocess.run([chrome, "--headless", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
                            "--force-device-scale-factor=2", "--window-size=692,1024",
                            "--default-background-color=FFFFFFFF", f"--screenshot={shot}", f"file://{page}"],
                           capture_output=True)
            crop(shot, 864 * 2)
    print(f"  proofs in {out}")


def main():
    html, charts, n = build()
    web, _, _ = build(web=True)
    for name, s in charts.items():
        p = os.path.join(ART, name + ".svg")
        with open(p, "w") as fh:
            fh.write(s)
        w, h = (int(v) for v in re.search(r'width="(\d+)" height="(\d+)"', s).groups())
        render_png(s, os.path.join(ART, name + ".png"), w, h)
    print(f"wrote {len(charts)} charts to assets/linkedin/debt-*.svg and .png")
    with open(os.path.join(ROOT, "notes", "debt-carousel.html"), "w") as fh:
        fh.write(web)
    print("wrote notes/debt-carousel.html")
    if "--proof" in sys.argv:
        proof(html, n)
    chrome = find_chrome()
    if not chrome:
        print("no chromium found - PDF skipped")
        return 1
    with tempfile.TemporaryDirectory() as tmp:
        page = os.path.join(tmp, "deck.html")
        with open(page, "w") as fh:
            fh.write(html)
        res = subprocess.run([chrome, "--headless", "--disable-gpu", "--no-sandbox", "--no-pdf-header-footer",
                              "--run-all-compositor-stages-before-draw", f"--print-to-pdf={OUT}", f"file://{page}"],
                             capture_output=True, text=True)
    if not os.path.exists(OUT):
        print(f"chromium failed\n{res.stderr[-500:]}")
        return 1
    print(f"wrote {OUT} ({os.path.getsize(OUT):,} bytes, {n} slides)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
