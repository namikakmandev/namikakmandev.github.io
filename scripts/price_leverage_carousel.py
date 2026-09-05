#!/usr/bin/env python3
"""LinkedIn carousel for the 11% rule study.

  -> notes/price-leverage-carousel.pdf

Six portrait slides at 7.2 x 9 inches, the 4:5 page LinkedIn wants for a
document post and the same MediaBox as the other carousels in notes/.

The charts are not redrawn here. The slides embed the committed SVGs written by
price_leverage.py, so the deck cannot drift from the study page, and every
figure in the prose is read out of data/price-leverage-results.json rather
than typed.

No matplotlib in this environment, so the deck is laid out in HTML and printed
by headless Chromium — the same renderer the charts already use.

  python3 scripts/price_leverage.py          # charts first
  python3 scripts/price_leverage_carousel.py
"""
import json, os, subprocess, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fte_chart import find_chrome, _crop_png as crop          # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "notes", "price-leverage-carousel.pdf")
RES = os.path.join(ROOT, "data", "price-leverage-results.json")
ART = os.path.join(ROOT, "assets", "linkedin")

INK, DIM, RED, GREEN = "#1f2430", "#5b6472", "#d94040", "#2e9e5b"
BLUE, ORANGE = "#2a78d6", "#eb6834"
RULE, PAPER = "#e3e8ee", "#ffffff"
FONT = ("-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,"
        "'Helvetica Neue',Arial,sans-serif")


def svg(name):
    """Inline a committed chart, sized to the slide rather than the file."""
    with open(os.path.join(ART, name)) as fh:
        s = fh.read()
    return s.replace("<svg ", '<svg class="chart" preserveAspectRatio="xMidYMid meet" ', 1)


def mechanism_svg(ex):
    """The profit block before and the +1 from price, on one scale, for the
    three margins. Revenue 100 -> 101, costs unchanged: the orange block is
    the same size on every row; the blue block is what it is measured against."""
    W, H = 700, 250
    L, R = 170, 90
    rowh = 62
    top = 30
    scale = (W - L - R) / max(100 * m + 1 for _, m, _ in ex)
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
         f'font-family="{FONT}" class="mech">']
    o.append(f'<text x="{L}" y="16" font-size="11" fill="{DIM}">Operating profit at revenue 100 '
             f'<tspan fill="{BLUE}" font-weight="700">&#9632;</tspan>  and the +1 that a 1% price rise adds '
             f'<tspan fill="{ORANGE}" font-weight="700">&#9632;</tspan></text>')
    for i, (name, m, lev) in enumerate(ex):
        y = top + i * rowh + 14
        p0 = 100 * m
        o.append(f'<text x="{L - 12}" y="{y + 22}" font-size="13" font-weight="700" fill="{INK}" '
                 f'text-anchor="end">{name}</text>')
        o.append(f'<text x="{L - 12}" y="{y + 38}" font-size="10.5" fill="{DIM}" text-anchor="end">'
                 f'margin {m:.1%}</text>')
        o.append(f'<rect x="{L}" y="{y + 6}" width="{p0 * scale:.1f}" height="28" fill="{BLUE}" rx="3"/>')
        o.append(f'<rect x="{L + p0 * scale + 2:.1f}" y="{y + 6}" width="{1 * scale - 2:.1f}" height="28" '
                 f'fill="{ORANGE}" rx="3"/>')
        o.append(f'<text x="{L + (p0 + 1) * scale + 10:.1f}" y="{y + 26}" font-size="15" font-weight="700" '
                 f'fill="{INK}">+{lev:.1f}%</text>')
        o.append(f'<text x="{L + 4}" y="{y + 25}" font-size="11" fill="#fff" font-weight="700">'
                 f'{p0:.2f}</text>' if p0 * scale > 40 else
                 f'<text x="{L + p0 * scale + 1 * scale + 4:.1f}" y="{y + 50}" font-size="10.5" fill="{DIM}">'
                 f'{p0:.2f} &#8594; {p0 + 1:.2f}</text>')
    o.append('</svg>')
    return "".join(o)


def tiles(t, claim):
    """Six regions as stat tiles: the value, and its distance from 11.1."""
    order = ["US", "Europe", "Emerging markets", "India", "Japan", "China"]
    out = []
    for k in order:
        v = t[k]["leverage"]
        d = v - claim
        arrow = "&#9650;" if d >= 0 else "&#9660;"
        cls = "up" if d >= 0 else "down"
        out.append(f'''<div class="tile">
              <span class="lab">{k}</span>
              <span class="val">{v:.1f}%</span>
              <span class="delta {cls}">{arrow} {d:+.1f} vs 11.1 &#183; margin {t[k]["op_margin"]:.1%}</span>
            </div>''')
    return '<div class="tiles">' + "".join(out) + "</div>"


def build_html(web=False):
    """The whole deck as one HTML document, one .s block per slide."""
    r = json.load(open(RES))
    t, v = r["today"], r["verdict"]
    us, em = t["US"], t["Emerging markets"]
    ser = {k: {int(y): p["leverage"] for y, p in r["series"][k].items()} for k in r["series"]}
    us_first = min(ser["US"])
    em_years = sorted(ser["Emerging markets"])
    em_dev = max(abs(ser["Emerging markets"][y] - 11.1) for y in em_years)
    iu = r["industries_us"]
    pharma = next(w for w in iu["watch"] if w["industry"] == "Drugs (Pharmaceutical)")
    lo, hi = iu["lowest"], iu["highest"]
    claim = r["claim"]["price_leverage_pct"]
    ex = [("Grocery (US)", hi["op_margin"], hi["leverage"]),
          ("1992 sample", round(1 / claim, 3), claim),
          ("Pharma (US)", pharma["op_margin"], pharma["leverage"])]
    brand = '<span class="brand">The 11% rule, retested &#183; namikakmandev.github.io/price-leverage.html</span>'

    slides = [
        # 1 - the hook, on the regions chart
        f'''<p class="kicker">A pricing study on open data &#183; margins as of January 2026</p>
            <h1 class="tight">Every pricing deck says 1% of price is worth 11% of
              profit. <span class="r">That was true in 1992.</span> Here is
              what it is worth now, by region.</h1>
            {svg("price-leverage-regions.svg")}''',

        # 2 - the famous number, as a hero figure and a formula
        f'''<p class="kicker">Marn &amp; Rosiello, Harvard Business Review, 1992</p>
            <h2>The famous number</h2>
            <p class="hero">11.1%</p>
            <p class="lede">more operating profit from a <b>1% price improvement</b>,
              volume held. More than volume, more than cost. It is on every
              pricing slide, including mine.</p>
            <div class="formula">
              <span class="f1">profit gain&nbsp;=</span>
              <span class="frac"><span>1</span><span>operating margin</span></span>
              <span class="f2">so&nbsp; 1 &#247; 9% &nbsp;=&nbsp; <b>11.1</b></span>
            </div>
            <p class="lede r"><b>Not a finding. Arithmetic. A fact about the margins of
              one sample of companies, 34 years ago.</b></p>''',

        # 3 - the mechanism, drawn
        f'''<p class="kicker">Revenue 100 &#8594; 101, same volume, costs unchanged</p>
            <h2>How one price point becomes {hi["leverage"]:.0f}% or {pharma["leverage"]:.0f}%</h2>
            <p class="lede">The extra revenue has no cost attached, so all of it lands in
              operating profit. <b>Every business gains the same +1.</b> What differs is the
              profit it is added to.</p>
            {mechanism_svg(ex)}
            {worked_table(ex)}
            <p class="lede r"><b>Thin margin, huge leverage. Fat margin, small leverage.
              The rule is one divided by the operating margin.</b></p>''',

        # 4 - so I recomputed it, on the series chart
        f'''<p class="kicker">Damodaran&#8217;s industry tables, every archived edition</p>
            <h2>So I recomputed it, every year</h2>
            {svg("price-leverage-series.svg")}''',

        # 5 - the regions as tiles
        f'''<p class="kicker">One over the aggregate operating margin, January 2026</p>
            <h2>What 1% of price buys now</h2>
            {tiles(t, claim)}
            <p class="lede">The US, where the rule was published, has been below 11.1 in
              every edition since {us_first}. Emerging markets have stayed within
              {em_dev:.1f} points of it since {em_years[0]}. <b>The rule moved. The decks
              did not.</b></p>''',

        # 6 - two things before you quote it
        f'''<p class="kicker">What to do with it</p>
            <h2>Two things before you quote it</h2>
            <div class="panel"><span class="n">1</span>
              <div><b>It is a formula, not a constant.</b> Your number is one over your
                operating margin. Pharmaceuticals at {pharma["op_margin"]*100:.0f}%:
                {pharma["leverage"]:.1f}%. Grocery retail at {hi["op_margin"]*100:.0f}%:
                {hi["leverage"]:.0f}%. Tobacco at {lo["op_margin"]*100:.0f}%:
                {lo["leverage"]:.1f}%.</div></div>
            <div class="panel"><span class="n">2</span>
              <div><b>Know which market the deck is in.</b> In the US and Europe, 11.1
                flatters the price lever. For an emerging-market aggregate it is still a
                fair default when the margin is unknown.</div></div>
            <p class="note">Method, every number and both scripts:<br>
              <b>namikakmandev.github.io/price-leverage.html</b><br>
              Data: Damodaran, NYU Stern, industry margin tables, eight regions,
              every archived edition; revenue-weighted, listed companies, volume
              held constant. Only the price lever is retested.</p>''',
    ]

    css = f"""
    @page {{ size: 518.4pt 648pt; margin: 0; }}
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; padding: 0; background: {PAPER}; }}
    .s {{ width: 518.4pt; height: 648pt; padding: 48pt 42pt 40pt;
          page-break-after: always; position: relative; overflow: hidden;
          font-family: {FONT}; color: {INK}; background: {PAPER};
          display: flex; flex-direction: column; justify-content: center; }}
    .s::before {{ content: ""; position: absolute; left: 0; top: 0; width: 100%;
                  height: 7pt; background: {BLUE}; }}
    .s:last-child {{ page-break-after: auto; }}
    .kicker {{ font-size: 11.5pt; color: {DIM}; letter-spacing: .02em;
               text-transform: uppercase; margin: 0 0 .22in; }}
    h1 {{ font-size: 33pt; line-height: 1.14; margin: 0 0 .28in; letter-spacing: -.01em; }}
    h1.tight {{ font-size: 26pt; margin: 0 0 .16in; }}
    h2 {{ font-size: 24pt; line-height: 1.18; margin: 0 0 .2in; letter-spacing: -.01em; }}
    .lede {{ font-size: 13.5pt; line-height: 1.5; color: {INK}; margin: 0 0 .16in; }}
    .note {{ font-size: 10.5pt; line-height: 1.5; color: {DIM}; margin: .2in 0 0;
             padding-top: .18in; border-top: 1px solid {RULE}; }}
    .hero {{ font-size: 96pt; font-weight: 700; margin: 0 0 .06in; letter-spacing: -.04em;
             line-height: 1; color: {BLUE}; }}
    .big {{ font-size: 62pt; font-weight: 700; margin: .04in 0 .06in; letter-spacing: -.03em; line-height: 1; }}
    .r {{ color: {RED}; }}  .g {{ color: {GREEN}; }}  .b {{ color: {BLUE}; }}
    .formula {{ display: flex; align-items: center; gap: 14pt; background: #f3f4f6;
                border-radius: 10pt; padding: 12pt 16pt; margin: 0 0 .2in; font-size: 15pt; }}
    .formula .frac {{ display: inline-flex; flex-direction: column; align-items: center; }}
    .formula .frac span:first-child {{ border-bottom: 2px solid {INK}; padding: 0 10pt 2pt; }}
    .formula .frac span:last-child {{ padding-top: 2pt; font-size: 12.5pt; }}
    .formula .f2 {{ margin-left: auto; color: {DIM}; }}
    .formula .f2 b {{ color: {BLUE}; font-size: 20pt; }}
    svg.mech {{ width: 100%; height: auto; display: block; margin: 0 0 .1in; }}
    table.w {{ border-collapse: collapse; width: 100%; table-layout: fixed;
               font-size: 11pt; margin: 0 0 .16in; }}
    table.w th, table.w td {{ padding: 3.5pt 4pt; border-bottom: 1px solid {RULE}; text-align: right; }}
    table.w th:first-child {{ width: 40%; text-align: left; font-weight: 400; color: {DIM}; }}
    table.w thead th {{ font-weight: 700; color: {INK}; }}
    .tiles {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10pt; margin: 0 0 .22in; }}
    .tile {{ background: #f3f4f6; border-radius: 10pt; padding: 12pt 14pt 11pt; }}
    .tile .lab {{ display: block; font-size: 11.5pt; color: {DIM}; }}
    .tile .val {{ display: block; font-size: 30pt; font-weight: 700; letter-spacing: -.02em;
                  line-height: 1.1; margin: 2pt 0; }}
    .tile .delta {{ display: block; font-size: 10pt; color: {DIM}; }}
    .tile .delta.up {{ color: {GREEN}; }}  .tile .delta.down {{ color: {ORANGE}; }}
    .panel {{ display: flex; gap: 12pt; align-items: flex-start; background: #f3f4f6;
              border-radius: 10pt; padding: 12pt 14pt; margin: 0 0 12pt; font-size: 13pt; line-height: 1.45; }}
    .panel .n {{ flex: 0 0 26pt; width: 26pt; height: 26pt; border-radius: 50%; background: {BLUE};
                 color: #fff; font-weight: 700; display: flex; align-items: center; justify-content: center;
                 font-size: 14pt; }}
    svg.chart {{ width: 100%; height: auto; max-height: 7.2in; display: block; margin: 0 0 .2in; }}
    .brand {{ position: absolute; left: 42pt; bottom: 20pt; font-size: 9.5pt; color: {DIM}; }}
    .num {{ position: absolute; right: 42pt; bottom: 20pt; font-size: 10pt; color: {DIM}; }}
    """
    if web:
        css += f"""
    body {{ background: #e9ecf0; padding: 24px 0 48px; }}
    .s {{ margin: 0 auto 24px; box-shadow: 0 6px 24px rgba(0,0,0,.12); border-radius: 6pt; }}
    .wrap {{ width: 691px; margin: 0 auto; }}
    .intro {{ max-width: 518.4pt; margin: 0 auto 18px; padding: 0 12px; font-family: {FONT};
              color: {DIM}; font-size: 12pt; }}
    .intro a {{ color: {BLUE}; }}
    """
    body = "".join(f'<div class="s">{s_}{brand}<span class="num">{i + 1} / {len(slides)}</span></div>'
                   for i, s_ in enumerate(slides))
    if web:
        body = (f'<p class="intro">The deck, as a web page. The study, every number and both scripts: '
                f'<a href="../price-leverage.html">namikakmandev.github.io/price-leverage.html</a>. '
                f'PDF: <a href="price-leverage-carousel.pdf">price-leverage-carousel.pdf</a>.</p>'
                f'<div class="wrap">{body}</div>'
                '<script>(function(){var w=document.querySelector(".wrap");function f(){'
                'w.style.zoom=Math.min(1,(window.innerWidth-16)/691);}'
                'window.addEventListener("resize",f);f();})();</script>')
        return (f"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
                f"<title>The 11% rule, retested &#8212; deck</title><style>{css}</style>{body}", len(slides))
    return (f"<!doctype html><meta charset=utf-8><style>{css}</style>{body}", len(slides))


def worked_table(ex):
    """Three columns, the numbers behind the picture above."""
    def col(m):
        cost = 100 * (1 - m)
        return cost, 100 * m, 101 - cost
    head = "".join(f"<th>{n}</th>" for n, _, _ in ex)
    rows = [("Operating margin", [f"{m:.1%}" for _, m, _ in ex]),
            ("Costs (unchanged)", [f"{col(m)[0]:.1f}" for _, m, _ in ex]),
            ("Profit at revenue 100", [f"{col(m)[1]:.2f}" for _, m, _ in ex]),
            ("Profit at revenue 101", [f"{col(m)[2]:.2f}" for _, m, _ in ex]),
            ("<b>Profit gain</b>", [f"<b>+{l:.1f}%</b>" for _, _, l in ex])]
    body = "".join(f"<tr><th>{k}</th>{''.join(f'<td>{v}</td>' for v in vs)}</tr>" for k, vs in rows)
    return f'<table class="w"><thead><tr><th></th>{head}</tr></thead><tbody>{body}</tbody></table>'


def proof(html, n):
    """Screenshot each slide, so the deck can be looked at without a PDF
    rasteriser. Same HTML the PDF is printed from.

    Headless Chromium hands back a viewport ~95px shorter than the window it is
    asked for, which silently cuts the bottom of the slide off the capture, so
    the window is padded and the shot cropped back. Only affects these proofs;
    --print-to-pdf paginates correctly.
    """
    out = os.path.join(ROOT, "assets", "linkedin", "carousel-proof")
    os.makedirs(out, exist_ok=True)
    chrome = find_chrome()
    with tempfile.TemporaryDirectory() as tmp:
        for i in range(1, n + 1):
            page = os.path.join(tmp, f"s{i}.html")
            shot = os.path.join(out, f"slide-{i}.png")
            with open(page, "w") as fh:
                fh.write(html + f"<style>.s{{display:none}}"
                                f".s:nth-of-type({i}){{display:flex}}</style>")
            subprocess.run(
                [chrome, "--headless", "--disable-gpu", "--no-sandbox",
                 "--hide-scrollbars", "--force-device-scale-factor=2",
                 "--window-size=692,1024", "--default-background-color=FFFFFFFF",
                 f"--screenshot={shot}",
                 f"file://{page}"], capture_output=True)
            crop(shot, 864 * 2)
        print(f"  proofs in {out}")


def main():
    html, n = build_html()
    web, _ = build_html(web=True)
    with open(os.path.join(ROOT, "notes", "price-leverage-carousel.html"), "w") as fh:
        fh.write(web)
    print("wrote notes/price-leverage-carousel.html")
    if "--proof" in sys.argv:
        proof(html, n)

    chrome = find_chrome()
    if not chrome:
        print("no chromium found — PDF skipped")
        return 1
    with tempfile.TemporaryDirectory() as tmp:
        page = os.path.join(tmp, "deck.html")
        with open(page, "w") as fh:
            fh.write(html)
        cmd = [chrome, "--headless", "--disable-gpu", "--no-sandbox",
               "--no-pdf-header-footer", "--run-all-compositor-stages-before-draw",
               f"--print-to-pdf={OUT}", f"file://{page}"]
        res = subprocess.run(cmd, capture_output=True, text=True)
    if not os.path.exists(OUT):
        print(f"chromium failed\n{res.stderr[-500:]}")
        return 1
    print(f"wrote {OUT} ({os.path.getsize(OUT):,} bytes, {n} slides)")
    print("  note: Chromium stamps a creation date, so the bytes differ between")
    print("  runs even though the rendered pages do not.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
