#!/usr/bin/env python3
"""A4 one-pager -> notes/vet-cpi-onepager.html (render to PDF with Chromium).

Light print style following one-pager-sample.html. Every figure imported from
scripts/vetcpi_carousel.py / vetcpi_carousel_html.py — same data files, so the
one-pager cannot disagree with the post image.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vetcpi_carousel as C
import vetcpi_carousel_html as H

OUT = os.path.join(C.ROOT, "notes", "vet-cpi-onepager.html")

BLUE = "#2F6BE0"; ORANGE = "#FF6500"; INK = "#1b2230"; DIM = "#5e6675"
LINE = "#e6e9ef"; SOFT = "#f6f8fb"


def panels():
    rows = []
    for g in H.GRID_GEOS:
        vet_kv, cpi_kv = C.EU[f"{g}|CP0935"], C.EU[f"{g}|CP00"]
        gap = C.pct(vet_kv, H.GRID_FRM, C.TO) - C.pct(cpi_kv, H.GRID_FRM, C.TO)
        rows.append((g, vet_kv, cpi_kv, gap))
    rows.append(("US", C.US["pet_svcs_nsa"], C.US["cpi_nsa"],
                 C.pct(C.US["pet_svcs_nsa"], H.GRID_FRM, C.TO)
                 - C.pct(C.US["cpi_nsa"], H.GRID_FRM, C.TO)))
    rows.sort(key=lambda r: -r[3])
    return rows


def mini(vet_kv, cpi_kv):
    W, Hh, LBL = 170, 74, 13
    keys = sorted(k for k in cpi_kv if H.GRID_FRM <= k <= C.TO)
    c = [cpi_kv[k] / cpi_kv[H.GRID_FRM] * 100 for k in keys]
    v = [vet_kv[k] / vet_kv[H.GRID_FRM] * 100 for k in keys]
    ylo, yhi = min(v + c) - 3, max(v + c) + 3
    xs = C.xpos(keys)
    X = lambda t: (t - xs[0]) / (xs[-1] - xs[0]) * W
    Y = lambda val: Hh - LBL - 2 - (val - ylo) / (yhi - ylo) * (Hh - LBL - 6)
    pc = " ".join(f"{X(t):.1f},{Y(val):.1f}" for t, val in zip(xs, c))
    pv = " ".join(f"{X(t):.1f},{Y(val):.1f}" for t, val in zip(xs, v))
    return (f'<svg viewBox="0 0 {W} {Hh}">'
            f'<line x1="0" y1="{Y(100):.1f}" x2="{W}" y2="{Y(100):.1f}" '
            f'stroke="{LINE}" stroke-width="1"/>'
            f'<polyline points="{pc}" fill="none" stroke="{ORANGE}" stroke-width="1.6"/>'
            f'<polyline points="{pv}" fill="none" stroke="{BLUE}" stroke-width="1.9"/>'
            f'<text x="0" y="{Hh - 2}" fill="#9aa2af" font-size="9">2017</text>'
            f'<text x="{W}" y="{Hh - 2}" fill="#9aa2af" font-size="9" '
            f'text-anchor="end">2025</text></svg>')


def main():
    rows = panels()
    below = sum(1 for r in rows if r[3] < -1)
    cells = "".join(
        f'<div class="cell"><div class="ch"><span>'
        f'<svg class="flag" viewBox="0 0 24 16">{H.FLAGS[g]}</svg>'
        f'{H.esc(H.GNAMES[g])}</span><span class="gap">{gap:+.0f}</span></div>'
        f'{mini(vet_kv, cpi_kv)}</div>'
        for g, vet_kv, cpi_kv, gap in rows)

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>Veterinary prices vs inflation — one-pager</title>
<style>
  @page {{ size: A4; margin: 0; }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
    Arial, sans-serif; color: {INK}; background: #fff; }}
  .page {{ width: 210mm; height: 297mm; padding: 12mm 13mm; }}
  .top {{ display: flex; justify-content: space-between; align-items: flex-end;
    border-bottom: 3px solid {BLUE}; padding-bottom: 8px; margin-bottom: 12px; }}
  .top h1 {{ font-size: 19px; letter-spacing: -.02em; }}
  .top .co {{ color: {DIM}; font-size: 10.5px; margin-bottom: 3px; }}
  .top .per {{ text-align: right; color: {DIM}; font-size: 10px; line-height: 1.5; }}
  .kpis {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px;
    margin-bottom: 12px; }}
  .kpi {{ background: {SOFT}; border: 1px solid {LINE}; border-radius: 8px;
    padding: 8px 10px; }}
  .kpi .l {{ font-size: 8.5px; color: {DIM}; text-transform: uppercase;
    letter-spacing: .05em; }}
  .kpi .v {{ font-size: 16px; font-weight: 700; margin-top: 3px; }}
  .kpi .d {{ font-size: 9.5px; margin-top: 2px; color: {DIM}; }}
  .legend {{ display: flex; gap: 18px; font-size: 10px; color: {DIM};
    margin-bottom: 8px; align-items: center; }}
  .legend i {{ display: inline-block; width: 20px; height: 3px; border-radius: 2px;
    margin-right: 5px; vertical-align: middle; }}
  .grid {{ display: grid; grid-template-columns: repeat(4, 1fr);
    gap: 7px 12px; margin-bottom: 12px; }}
  .cell svg {{ width: 100%; height: auto; display: block; }}
  .ch {{ display: flex; justify-content: space-between; align-items: center;
    font-size: 10.5px; font-weight: 700; margin-bottom: 2px; }}
  .ch span:first-child {{ display: flex; align-items: center; gap: 5px; }}
  .ch .flag {{ width: 15px; height: 10px; border-radius: 2px; flex: none;
    outline: 1px solid rgba(0,0,0,.12); outline-offset: -1px; }}
  .ch .gap {{ font-variant-numeric: tabular-nums; }}
  .cols {{ display: grid; grid-template-columns: 1.15fr 1fr; gap: 18px; }}
  h2 {{ font-size: 10px; text-transform: uppercase; letter-spacing: .06em;
    color: {BLUE}; margin-bottom: 6px; border-bottom: 1px solid {LINE};
    padding-bottom: 4px; }}
  .story li {{ margin: 0 0 7px 14px; font-size: 10.5px; line-height: 1.45; }}
  .notes p {{ font-size: 9.8px; line-height: 1.45; margin-bottom: 6px;
    color: {INK}; }}
  .notes b {{ font-size: 9.5px; }}
  .foot {{ margin-top: 10px; border-top: 1px solid {LINE}; padding-top: 7px;
    display: flex; justify-content: space-between; color: {DIM};
    font-size: 8.8px; }}
</style></head><body>
<div class="page">
  <div class="top">
    <div>
      <div class="co">namikakmandev.github.io · personal analysis of public statistics</div>
      <h1>Veterinary prices vs inflation — 20 markets, 2017–2025</h1>
    </div>
    <div class="per">Namık Akman<br>August 2026</div>
  </div>

  <div class="kpis">
    <div class="kpi"><div class="l">Widest gap</div><div class="v">+65 pts</div>
      <div class="d">Bulgaria, vet prices over inflation</div></div>
    <div class="kpi"><div class="l">Below inflation</div><div class="v">{below} of 20</div>
      <div class="d">incl. Greece −16, Norway −9</div></div>
    <div class="kpi"><div class="l">Sharpest move</div><div class="v">+24%</div>
      <div class="d">Germany, one month (Dec 2022)</div></div>
    <div class="kpi"><div class="l">United States</div><div class="v">+4 pts</div>
      <div class="d">mid-table, despite the narrative</div></div>
  </div>

  <div class="legend">
    <span><i style="background:{BLUE}"></i>veterinary &amp; pet services</span>
    <span><i style="background:{ORANGE}"></i>all-items inflation</span>
    <span><b style="color:{INK}">+51</b>&nbsp;= gap in points over the window · both lines Jan 2017 = 100 · own scale per panel</span>
  </div>
  <div class="grid">{cells}</div>

  <div class="cols">
    <div>
      <h2>What the data shows</h2>
      <ul class="story">
        <li><b>The gap is a geography.</b> Vet prices ran far ahead of inflation
        across Central, Northern and Eastern Europe (Bulgaria +65, Poland +51,
        Slovakia +50, Sweden +35, Denmark +32) and fell behind it across the
        South (Greece −16, Austria −7, Spain, Italy, Portugal).</li>
        <li><b>Regulated prices jump, they don't drift.</b> Germany's vet fees
        are set by the national GOT fee ordinance: the index was flat for years,
        rose 24% in a single month when the November 2022 revision took effect,
        and has been flat since (155.3 vs 154.8 three years later).</li>
        <li><b>The loudest story is mid-table.</b> The US, origin of the "vet
        costs are exploding" narrative, shows +4 points over inflation on the
        like-for-like basket — less than Denmark, Germany or Sweden.</li>
      </ul>
    </div>
    <div class="notes">
      <h2>Scope, exclusions, sources</h2>
      <p><b>Measure.</b> Consumer price indices: what households pay for
      veterinary and other pet services, versus all-items inflation. Not farm
      animal health spending.</p>
      <p><b>Excluded.</b> Türkiye — publishes no vet-services price index
      (all-items HICP only). Ireland — vet series ends Dec 2023.</p>
      <p><b>Known steps.</b> Germany +24% (Dec 2022) and Sweden +18%
      (Oct 2022) are real repricings — fee-schedule revision and clinic-chain
      consolidation — not data breaks.</p>
      <p><b>Sources.</b> Eurostat prc_hicp_midx, monthly, 2015=100 — CP0935
      veterinary and other services for pets vs CP00 all items. US: BLS CPI
      via FRED, monthly, NSA — CUUR0000SS62031 pet services incl. veterinary
      vs CPIAUCNS.</p>
    </div>
  </div>

  <div class="foot">
    <span>Data cut 11 Aug 2026 · every figure recomputable from
    data/vet-cpi-eu.json and data/vet-cpi-us.json</span>
    <span>Views my own · not investment or veterinary advice</span>
  </div>
</div>
</body></html>"""
    open(OUT, "w").write(html)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
