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
BLUE = "#2f9bff"
RULE, PAPER = "#e3e8ee", "#ffffff"
FONT = ("-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,"
        "'Helvetica Neue',Arial,sans-serif")


def svg(name):
    """Inline a committed chart, sized to the slide rather than the file."""
    with open(os.path.join(ART, name)) as fh:
        s = fh.read()
    return s.replace("<svg ", '<svg class="chart" preserveAspectRatio="xMidYMid meet" ', 1)


def worked_table(ex):
    """Revenue 100, price +1%, volume held: the same one point of margin,
    three very different profit gains. Figures from the results file."""
    def col(m):
        cost = 100 * (1 - m)
        return cost, 100 * m, 101 - cost
    head = "".join(f"<th>{n}</th>" for n, _, _ in ex)
    rows = [("Operating margin", [f"{m:.1%}" for _, m, _ in ex]),
            ("Revenue", ["100"] * 3),
            ("Operating costs", [f"{col(m)[0]:.1f}" for _, m, _ in ex]),
            ("Operating profit", [f"{col(m)[1]:.2f}" for _, m, _ in ex]),
            ("Price +1%, same volume", ["101"] * 3),
            ("Costs, unchanged", [f"{col(m)[0]:.1f}" for _, m, _ in ex]),
            ("Operating profit", [f"{col(m)[2]:.2f}" for _, m, _ in ex]),
            ("<b>Profit gain</b>", [f"<b>+{l:.1f}%</b>" for _, _, l in ex])]
    body = "".join(f"<tr><th>{k}</th>{''.join(f'<td>{v}</td>' for v in vs)}</tr>" for k, vs in rows)
    return f'<table class="w"><thead><tr><th></th>{head}</tr></thead><tbody>{body}</tbody></table>'


def build_html():
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

    slides = [
        # 1 - the hook, on the regions chart
        f'''<h1 class="tight">Every pricing deck says 1% of price is worth 11% of
              profit. <span class="r">That was true in 1992.</span> Here is
              what it is worth now, by region.</h1>
            {svg("price-leverage-regions.svg")}''',

        # 2 - the famous number, and why it is arithmetic
        f'''<p class="kicker">Marn &amp; Rosiello, Harvard Business Review,
              1992</p>
            <h2>The famous number</h2>
            <p class="lede">A 1% improvement in price yields an <b>11.1%</b>
              increase in operating profit. More than volume, more than cost.</p>
            <p class="lede">It is not a finding. It is arithmetic: if volume holds,
              the gain is <b>one over the operating margin</b>. 11.1 is what a
              9% margin gives.</p>
            <p class="lede r"><b>So it is a fact about the margins of one sample of
              companies, 34 years ago. Nothing else.</b></p>''',

        # 3 - the arithmetic, worked, on three margins
        f'''<h2>How one price point becomes 44% or 3%</h2>
            <p class="lede">Raise price 1%, sell the same volume, change nothing
              else. The extra revenue has no cost attached, so all of it lands in
              operating profit. <b>Every business gains the same one point of
              margin.</b> What differs is how big that point is next to the
              profit it already had.</p>
            {worked_table(ex)}
            <p class="lede r"><b>Thin margin, huge leverage. Fat margin, small
              leverage. The rule is one divided by the operating margin.</b></p>''',

        # 4 - so I recomputed it, on the series chart
        f'''<h2>So I recomputed it, every year</h2>
            {svg("price-leverage-series.svg")}''',

        # 5 - the two numbers
        f'''<h2>The US today</h2>
            <p class="big b">{us["leverage"]:.1f}%</p>
            <p class="lede">operating profit per 1% of price. Below 11.1 in every
              edition since {us_first}. Europe: {t["Europe"]["leverage"]:.1f}%.</p>
            <h2 style="margin-top:.26in">Emerging markets</h2>
            <p class="big g">{em["leverage"]:.1f}%</p>
            <p class="lede">Within {em_dev:.1f} points of the rule in every edition
              since {em_years[0]}. Japan {t["Japan"]["leverage"]:.1f}%, China
              {t["China"]["leverage"]:.1f}%. <b>The rule moved. The decks did
              not.</b></p>''',

        # 6 - two things before you quote it
        f'''<h2>Two things before you quote it</h2>
            <p class="lede"><b>1. It is a formula, not a constant.</b> Your number
              is one over your operating margin. Pharmaceuticals at
              {pharma["op_margin"]*100:.0f}% margin: {pharma["leverage"]:.1f}%.
              Grocery retail at {hi["op_margin"]*100:.0f}%: {hi["leverage"]:.0f}%.
              Tobacco at {lo["op_margin"]*100:.0f}%: {lo["leverage"]:.1f}%.</p>
            <p class="lede"><b>2. Know which market the deck is in.</b> In the US
              and Europe, 11.1 flatters the price lever. For an emerging-market
              aggregate it is still a fair default when the margin is unknown.</p>
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
    .s {{ width: 518.4pt; height: 648pt; padding: 45pt 42pt 36pt;
          page-break-after: always; position: relative; overflow: hidden;
          font-family: {FONT}; color: {INK};
          display: flex; flex-direction: column; justify-content: center; }}
    .s:last-child {{ page-break-after: auto; }}
    .kicker {{ font-size: 12.5pt; color: {DIM}; letter-spacing: .02em;
               margin: 0 0 .28in; }}
    h1 {{ font-size: 33pt; line-height: 1.14; margin: 0 0 .28in;
          letter-spacing: -.01em; }}
    h1.tight {{ font-size: 27pt; margin: 0 0 .16in; }}
    h2 {{ font-size: 24pt; line-height: 1.18; margin: 0 0 .22in;
          letter-spacing: -.01em; }}
    .lede {{ font-size: 14pt; line-height: 1.5; color: {INK}; margin: 0 0 .17in; }}
    .note {{ font-size: 10.5pt; line-height: 1.5; color: {DIM};
             margin: .2in 0 0; padding-top: .18in;
             border-top: 1px solid {RULE}; }}
    .big {{ font-size: 62pt; font-weight: 700; margin: .04in 0 .06in;
            letter-spacing: -.03em; line-height: 1; }}
    .r {{ color: {RED}; }}  .g {{ color: {GREEN}; }}  .b {{ color: {BLUE}; }}
    ol {{ font-size: 14pt; line-height: 1.5; margin: 0 0 .17in; padding-left: .26in; }}
    li {{ margin-bottom: .09in; }}
    .facts {{ display: flex; gap: .3in; margin: .1in 0 .24in; }}
    .facts div {{ flex: 1; }}
    .facts b {{ display: block; font-size: 27pt; letter-spacing: -.02em; }}
    .facts span {{ display: block; font-size: 10.5pt; color: {DIM};
                   line-height: 1.35; margin-top: .04in; }}
    svg.chart {{ width: 100%; height: auto; max-height: 7.2in;
                 display: block; margin: 0 0 .2in; }}
    table.w {{ border-collapse: collapse; width: 100%; table-layout: fixed;
               font-size: 12pt; margin: .05in 0 .2in; }}
    table.w th, table.w td {{ padding: 5pt 4pt; border-bottom: 1px solid {RULE};
                              text-align: right; }}
    table.w th:first-child {{ width: 38%; }}
    table.w th:first-child {{ text-align: left; font-weight: 400; color: {DIM}; }}
    table.w thead th {{ font-weight: 700; color: {INK}; }}
    table.w tr:nth-child(4) td, table.w tr:nth-child(7) td {{ font-weight: 700; }}
    .num {{ position: absolute; right: 42pt; bottom: 24pt;
            font-size: 10pt; color: {DIM}; }}
    """
    body = "".join(f'<div class="s">{s}<span class="num">{i + 1} / '
                   f'{len(slides)}</span></div>'
                   for i, s in enumerate(slides))
    return (f"<!doctype html><meta charset=utf-8><style>{css}</style>{body}",
            len(slides))


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
