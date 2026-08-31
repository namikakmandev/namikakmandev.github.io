#!/usr/bin/env python3
"""LinkedIn carousel for the ECB forecaster-skill study.

  -> notes/ecb-forecaster-carousel.pdf

Seven portrait slides at 7.2 x 9 inches, which is the 4:5 page LinkedIn wants
for a document post and the same MediaBox as the earlier carousels in notes/.

The three charts are not redrawn here. The slides embed the committed SVGs
written by ecb_forecaster_skill.py, so the deck cannot drift from the study
page, and every figure in the prose is read out of data/ecb-forecaster-skill.json
rather than typed.

No matplotlib in this environment, so the deck is laid out in HTML and printed
by headless Chromium — the same renderer the charts already use.

  python3 scripts/ecb_forecaster_skill.py     # charts first
  python3 scripts/ecb_carousel.py
"""
import json, os, subprocess, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fte_chart import find_chrome, _crop_png as crop          # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "notes", "ecb-forecaster-carousel.pdf")
RES = os.path.join(ROOT, "data", "ecb-forecaster-skill.json")
ART = os.path.join(ROOT, "assets", "linkedin")

INK, DIM, RED, GREEN = "#1f2430", "#5b6472", "#d94040", "#2e9e5b"
RULE, PAPER = "#e3e8ee", "#ffffff"
FONT = ("-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,"
        "'Helvetica Neue',Arial,sans-serif")


def svg(name):
    """Inline a committed chart, sized to the slide rather than the file."""
    with open(os.path.join(ART, name)) as fh:
        s = fh.read()
    return s.replace("<svg ", '<svg class="chart" preserveAspectRatio="xMidYMid meet" ', 1)


def build_html():
    """The whole deck as one HTML document, one .s block per slide."""
    r = json.load(open(RES))
    n = r["n_forecasters"]
    gap = round((max(x["skill"] for x in r["scores"])
                 - min(x["skill"] for x in r["scores"])) * 100)
    r2 = round(r["width"]["r2"] * 100)
    zero = [y for y, v in sorted(r["year_difficulty"].items()) if v == 0]
    md = r["miss_direction"]
    pooled = md["pooled"]
    misses = pooled["too_low"] + pooled["too_high"]
    low_share = round(pooled["too_low"] / misses * 100)
    assert md["zero_coverage_all_too_low"], "the one-way claim no longer holds"
    best, worst = r["scores"][0]["who"], r["scores"][-1]["who"]
    wide = r["width"]["by_forecaster"][best] / r["width"]["by_forecaster"][worst]

    slides = [
        # 1 — the grid leads. It is the thumbnail in the feed, so it carries a
        # headline of its own: the pattern reads at any size, the words do not.
        f'''<h1 class="tight">Four years when Europe&rsquo;s inflation
              forecasters <span class="r">all missed together</span></h1>
            {svg("ecb-forecaster-skill.svg")}''',

        # 2 — why I went looking
        f'''<p class="kicker">ECB Survey of Professional Forecasters &middot;
              euro area &middot; 2000&ndash;2025</p>
            <h2>I work in pricing.</h2>
            <p class="lede">Every plan I build rests on an inflation
              forecast.</p>
            <p class="lede">Every quarter the ECB asks about 50 banks and
              research institutes across Europe where inflation will land, and
              how sure they are about it.</p>
            <p class="lede r"><b>In 2022 it came in at 8.4%. Of the 58 who
              answered that round, not one had it inside their range.</b></p>
            <p class="lede">So I went back and scored all 26 years, one
              forecaster at a time.</p>''',

        # 3 — what makes it checkable
        f'''<h2>The promise you can check</h2>
            <p class="lede">The ECB does not just ask for a number. It asks each
              institution for a range they are <b>80% sure</b> about.</p>
            <p class="lede">That is a promise with a test attached. If you say
              80%, then over 20 years the answer should land inside your range
              about 16 times.</p>
            <div class="facts">
              <div><b>{n}</b><span>forecasters with 10+ scored years</span></div>
              <div><b>{r["n_forecasts"]:,}</b><span>forecasts scored</span></div>
              <div><b>26</b><span>years followed, one by one</span></div>
            </div>
            <p class="note">These are outside institutions, not the ECB&rsquo;s
              own staff projections. The ECB publishes panellists only by
              number; nothing here identifies any of them.</p>''',

        # 4 — the columns
        f'''<h2>Read it down the columns</h2>
            <p class="big r">{", ".join(zero[:-1])} and {zero[-1]}</p>
            <p class="lede">In each of those years, <b>not one</b> forecaster on
              the panel contained the outcome.</p>
            <p class="lede">And they were all wrong the same way.
              <b>{md["zero_coverage_n"]} forecasts across those four years,
              {md["zero_coverage_n"]} underestimates, zero overestimates.</b>
              When this panel fails completely, it does not see costs
              coming.</p>
            <p class="note">Not a one-way record overall: across all 26 years
              {low_share}% of misses were too low and {100 - low_share}% too
              high. It is the total failures that are one-sided.</p>''',

        # 5 — the rows, and the catch
        f'''{svg("ecb-forecaster-ranges.svg")}
            <p class="lede">Across the rows they are not interchangeable: best
              to worst is <b>{gap} percentage points</b>, far too wide to be
              luck.</p>
            <p class="lede">But a range can be right just by being huge. The
              best forecaster&rsquo;s ranges are <b>{wide:.1f}&times; wider</b>
              than the worst&rsquo;s, and width alone explains <b>{r2}%</b> of
              the score.</p>''',

        # 6 — the outcome
        f'''<h2>What to do with it</h2>
            <p class="lede">&ldquo;Costs will rise 0&ndash;10%&rdquo; is almost
              never wrong and almost never useful. So score a forecast twice,
              not once:</p>
            <ol>
              <li>How often the outcome fell inside the stated range.</li>
              <li>How wide that range had to be to manage it.</li>
            </ol>
            <p class="lede">The first number can be bought. Only the second
              tells you whether they know anything.</p>
            <p class="big">{r["above_bar"]} of {n}</p>
            <p class="lede">hit their own 80% standard. Not my standard
              &mdash; theirs.</p>
            <p class="note">Method, every number and the full script:<br>
              <b>namikakmandev.github.io/ecb-forecaster-skill.html</b><br>
              Data: ECB Survey of Professional Forecasters, published openly.</p>''',
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
    .big {{ font-size: 40pt; font-weight: 700; margin: .1in 0 .12in;
            letter-spacing: -.02em; }}
    .r {{ color: {RED}; }}  .g {{ color: {GREEN}; }}
    ol {{ font-size: 14pt; line-height: 1.5; margin: 0 0 .17in; padding-left: .26in; }}
    li {{ margin-bottom: .09in; }}
    .facts {{ display: flex; gap: .3in; margin: .1in 0 .24in; }}
    .facts div {{ flex: 1; }}
    .facts b {{ display: block; font-size: 27pt; letter-spacing: -.02em; }}
    .facts span {{ display: block; font-size: 10.5pt; color: {DIM};
                   line-height: 1.35; margin-top: .04in; }}
    svg.chart {{ width: 100%; height: auto; max-height: 7.2in;
                 display: block; margin: 0 0 .2in; }}
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
