#!/usr/bin/env python3
"""LinkedIn carousel for the Eroom's Law study.

  -> notes/pharma-eroom-carousel.pdf

Six portrait slides at 7.2 x 9 inches, the 4:5 page LinkedIn wants for a
document post and the same MediaBox as the other carousels in notes/.

The charts are not redrawn here. The slides embed the committed SVGs written by
pharma_eroom.py, so the deck cannot drift from the study page, and every figure
in the prose is read out of data/pharma-eroom-results.json rather than typed.

No matplotlib in this environment, so the deck is laid out in HTML and printed
by headless Chromium — the same renderer the charts already use.

  python3 scripts/pharma_eroom.py     # charts first
  python3 scripts/eroom_carousel.py
"""
import json, os, subprocess, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fte_chart import find_chrome, _crop_png as crop          # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "notes", "pharma-eroom-carousel.pdf")
RES = os.path.join(ROOT, "data", "pharma-eroom-results.json")
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
    h, c, sh = r["headline"], r["checks"], r["approvals_shift"]
    ser = {int(k): v for k, v in r["us_series"].items()}
    yrs = sorted(ser)
    pred_end = ser[yrs[0]] * (0.5 ** ((yrs[-1] - yrs[0]) / 9.0))
    times = ser[yrs[-1]] / pred_end
    den = c["denominator_share_of_movement"] * 100

    slides = [
        # 1 - the chart leads: it is the thumbnail, so it carries a headline
        f'''<h1 class="tight">Pharma&rsquo;s most quoted number
              <span class="r">stopped being true</span></h1>
            {svg("pharma-eroom.svg")}''',

        # 2 - what the claim is
        f'''<p class="kicker">Scannell et al., Nature Reviews Drug Discovery,
              2012</p>
            <h2>Moore&rsquo;s Law, backwards</h2>
            <p class="lede">Moore&rsquo;s Law says computing power doubles every
              two years. In 2012 four researchers went looking for the same
              thing in drug research and found its exact opposite.</p>
            <p class="lede">New drugs approved per billion dollars of research
              had <b>halved every nine years since 1950</b>. Sixty years, no
              exceptions. They spelled Moore backwards and called it
              <b>Eroom&rsquo;s Law</b>.</p>
            <p class="lede r"><b>Its data stops in 2010. It is still on slides
              today.</b></p>''',

        # 3 - the test
        f'''<h2>So I rebuilt it</h2>
            <p class="lede">Approvals from the FDA&rsquo;s own submission
              records &mdash; the count reproduces the FDA&rsquo;s published
              figures almost exactly. Spending from Eurostat&rsquo;s R&amp;D
              accounts, deflated.</p>
            <div class="facts">
              <div><b>{h["slope"]:+.3f}</b><span>fitted slope per year,
                {h["first"]}&ndash;{h["last"]}</span></div>
              <div><b>{h["eroom_slope"]:+.3f}</b><span>what Eroom&rsquo;s Law
                implies</span></div>
              <div><b>{r["n_us_specs"]} of {r["n_us_specs"]}</b><span>US
                specifications reject it</span></div>
            </div>
            <p class="lede">By {yrs[-1]} the law implies <b>{pred_end:.2f}</b>
              approvals per billion dollars. The figure was
              <b>{ser[yrs[-1]]:.2f}</b> &mdash; more than {times:.0f} times
              higher.</p>
            <p class="note">This tests whether the published rate continued. The
              paper&rsquo;s own 1950&ndash;2010 window cannot be re-measured:
              no open R&amp;D series reaches back that far.</p>''',

        # 4 - the question everyone asks
        f'''<h2>Was it AI?</h2>
            {svg("pharma-approvals.svg")}''',

        # 5 - no, on timing
        f'''<h2 class="r">No &mdash; on timing alone</h2>
            <p class="lede">Approvals step up once, and the step is complete by
              <b>{sh["level_shift_year"]}</b>: {sh["mean_before"]:.0f} a year
              before, {sh["mean_after"]:.0f} after. The break year is chosen by
              fit, not by eye.</p>
            <p class="lede">AI-designed molecules reached the clinic around 2020
              and have almost no approvals yet. <b>A cause cannot postdate its
              effect.</b></p>
            <p class="lede">What did cause it is not tested here and this deck
              does not guess. The step is established; the cause stays
              open.</p>''',

        # 6 - the catch, and the instruction
        f'''<h2>The honest catch</h2>
            <p class="lede">The ratio held up because <b>approvals rose</b>, not
              because spending fell. Real R&amp;D grew steadily throughout and
              accounts for only <b>{den:.0f}%</b> of the ratio&rsquo;s
              movement.</p>
            <p class="lede">So this is an approvals story with a slow
              denominator. Calling it a productivity story would overstate
              it.</p>
            <p class="big">Date the claim</p>
            <p class="lede">If the nine-year halving goes into a business case,
              say which years it describes: <b>1950&ndash;2010</b>. On the years
              since, it is rejected.</p>
            <p class="note">Method, every number and both scripts:<br>
              <b>namikakmandev.github.io/pharma-eroom.html</b><br>
              Data: FDA Drugs@FDA submission records; Eurostat rd_e_berdindr2
              NACE C21; US GDP deflator.</p>''',
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
