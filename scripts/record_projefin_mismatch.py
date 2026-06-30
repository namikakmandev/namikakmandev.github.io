# -*- coding: utf-8 -*-
"""Record a ~3-minute, captioned ProjeFin walkthrough about CURRENCY MISMATCH.

Landscape 1920x1080 with on-screen step captions, a robot cursor, and intro/outro
cards. Built to teach with sound OFF. It is driven against the LOCAL server so it
captures exactly what was just edited (no GitHub-Pages rebuild race) and does not
need the AI proxy (the AI assistant is not used in this tour).

The whole point: show the numbers ACTUALLY changing where they change —
  1) switching presets (Hospital vs Toll) flips the KPIs and the mismatch card,
  2) dragging the USD/TRY shock drops the bank-case (Downside) DSCR live.

Output: assets/demos/projefin-mismatch.mp4 (+ .jpg poster).
Usage:  python scripts/record_projefin_mismatch.py
Needs:  a local server on :4317 (python -m http.server 4317 --directory portfolio-website),
        playwright (+ chromium), imageio-ffmpeg.
"""
import os
import shutil
import subprocess

from playwright.sync_api import sync_playwright

URL = "http://localhost:4317/project-finance.html"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "..", "assets", "demos")
REC_DIR = os.path.join(HERE, "_rec_pf_tmp")
SIZE = {"width": 1920, "height": 1080}
NAME = "projefin-mismatch"

INIT_JS = r"""
(() => {
  function ready(fn){ if (document.body) fn(); else document.addEventListener('DOMContentLoaded', fn); }
  ready(() => {
    if (document.getElementById('__demo_cursor')) return;
    const style = document.createElement('style');
    style.textContent = `
      html { scrollbar-width: none; }
      ::-webkit-scrollbar { display: none; }
      .layout { grid-template-columns: 360px 1fr !important; max-width: 1840px !important; }
      #__demo_cursor { position: fixed; z-index: 2147483647; pointer-events: none;
        width: 32px; height: 32px; left: 0; top: 0; transition: transform .08s ease, opacity .25s ease; }
      .__demo_ripple { position: fixed; z-index: 2147483646; pointer-events: none;
        width: 18px; height: 18px; border-radius: 50%; border: 3px solid #2F9BFF;
        transform: translate(-50%,-50%) scale(1); opacity: .9;
        animation: __demo_rip .55s ease-out forwards; }
      @keyframes __demo_rip { to { transform: translate(-50%,-50%) scale(3.6); opacity: 0; } }
      #__cap { position: fixed; left:0; right:0; bottom:0; z-index: 2147483600;
        background: linear-gradient(0deg, rgba(15,17,23,.985), rgba(15,17,23,.90));
        border-top: 2px solid #19C37D; padding: 26px 44px 32px; min-height: 104px;
        font-family: 'IBM Plex Sans', sans-serif; color:#E6E8EE; font-size: 31px;
        font-weight: 600; line-height: 1.32; display:flex; align-items:center; gap:20px;
        transition: opacity .25s ease; }
      #__cap.hidden { opacity: 0; }
      #__cap .dot { width:14px; height:14px; border-radius:50%; background:#19C37D;
        flex-shrink:0; box-shadow:0 0 16px #19C37D; }
      #__cap .big { font-family:'IBM Plex Mono',monospace; color:#FF6500; font-weight:600; }
      #__ovl { position: fixed; inset:0; z-index: 2147483640; background:#0F1117;
        display:flex; flex-direction:column; align-items:center; justify-content:center;
        text-align:center; padding:80px; font-family:'IBM Plex Sans',sans-serif;
        color:#E6E8EE; transition: opacity .45s ease; opacity:1; }
      #__ovl.hidden { opacity:0; pointer-events:none; }
    `;
    document.head.appendChild(style);

    const cur = document.createElement('div');
    cur.id = '__demo_cursor';
    cur.innerHTML = `<svg width="32" height="32" viewBox="0 0 24 24">
      <path d="M5 2 L5 19 L9.5 15.5 L12.5 21.5 L15 20 L12 14.5 L18 14 Z"
        fill="#fff" stroke="#1c2330" stroke-width="1.6" stroke-linejoin="round"
        style="filter: drop-shadow(0 2px 5px rgba(0,0,0,.5))"/></svg>`;
    document.body.appendChild(cur);

    const cap = document.createElement('div');
    cap.id = '__cap'; cap.className = 'hidden';
    cap.innerHTML = '<span class="dot"></span><span id="__captxt"></span>';
    document.body.appendChild(cap);

    const ovl = document.createElement('div');
    ovl.id = '__ovl';
    document.body.appendChild(ovl);

    window.addEventListener('mousemove', e => {
      cur.style.left = e.clientX + 'px'; cur.style.top = e.clientY + 'px';
    }, true);
    window.addEventListener('mousedown', e => {
      cur.style.transform = 'scale(.82)';
      const r = document.createElement('div');
      r.className = '__demo_ripple';
      r.style.left = e.clientX + 'px'; r.style.top = e.clientY + 'px';
      document.body.appendChild(r);
      setTimeout(() => r.remove(), 600);
    }, true);
    window.addEventListener('mouseup', () => { cur.style.transform = 'scale(1)'; }, true);

    window.__setCap = (html) => {
      const t = document.getElementById('__captxt');
      const bar = document.getElementById('__cap');
      if (html === null) { bar.classList.add('hidden'); return; }
      t.innerHTML = html; bar.classList.remove('hidden');
    };
    window.__overlay = (html) => {
      ovl.innerHTML = html; ovl.classList.remove('hidden');
      cur.style.opacity = '0';
    };
    window.__hideOverlay = () => {
      ovl.classList.add('hidden'); cur.style.opacity = '1';
    };
    // flash the bank-case Min DSCR cell so the eye lands on the number that moves
    window.__flashDSCR = () => {
      const rows = [...document.querySelectorAll('#ds-body tr')];
      const r = rows.find(tr => tr.cells[0].textContent.includes('Min DSCR'));
      if (!r) return;
      const c = r.cells[2];
      c.style.transition = 'all .25s ease';
      c.style.outline = '3px solid #FF6500';
      c.style.background = 'rgba(255,101,0,.20)';
      setTimeout(() => { c.style.outline=''; c.style.background=''; }, 1200);
    };
    window.__setShock = (v) => {
      const e = document.getElementById('dsFx');
      e.value = v; e.dispatchEvent(new Event('input', {bubbles:true}));
    };
  });
})();
"""

INTRO_HTML = """
<div style="font-size:96px;font-weight:700;letter-spacing:.5px">Proje<span style="color:#19C37D">Fin</span></div>
<div style="font-size:34px;color:#A3A8B5;margin-top:22px">Currency mismatch &mdash; made visible</div>
<div style="font-size:24px;color:#5B6472;margin-top:14px">Why a cheap dollar loan can sink a lira project</div>
<div style="margin-top:40px;height:4px;width:150px;background:#2F9BFF;border-radius:2px"></div>
"""

OUTRO_HTML = """
<div style="font-size:46px;font-weight:700;line-height:1.32">Earn in lira, borrow in dollars,<br>and a devaluation does the rest.</div>
<div style="font-size:30px;color:#A3A8B5;margin-top:26px">ProjeFin shows which side of that line you&rsquo;re on &mdash; before you sign.</div>
<div style="font-size:30px;color:#2F9BFF;margin-top:30px;font-family:'IBM Plex Mono',monospace">namikakmandev.github.io/project-finance.html</div>
"""


# Global dwell multiplier so subtitles are readable and the numbers can be watched.
# Intro/outro cards bypass this (they call page.wait_for_timeout directly).
SCALE = 3.1


def pause(page, ms):
    page.wait_for_timeout(int(ms * SCALE))


def cap(page, html):
    page.evaluate("h => window.__setCap(h)", html)


def move_to(page, selector, dx=0, dy=0, ms_after=350):
    el = page.locator(selector).first
    el.wait_for(state="visible", timeout=15000)
    box = el.bounding_box()
    if not box:
        return None
    x = box["x"] + box["width"] / 2 + dx
    y = box["y"] + box["height"] / 2 + dy
    page.mouse.move(x, y, steps=30)
    pause(page, ms_after)
    return (x, y)


def click_el(page, selector, dx=0, dy=0, ms_after=900):
    pt = move_to(page, selector, dx, dy, ms_after=280)
    if pt:
        page.mouse.down(); pause(page, 90); page.mouse.up()
        pause(page, ms_after)


def scroll_to(page, selector, block="center", ms_after=900):
    page.evaluate(
        "(s,b) => { const e=document.querySelector(s); if(e) e.scrollIntoView({behavior:'smooth',block:b}); }",
        [selector, block],
    )
    pause(page, ms_after)


def set_shock(page, v, ms_after=1300):
    page.evaluate("v => window.__setShock(v)", v)
    page.evaluate("() => window.__flashDSCR()")
    pause(page, ms_after)


def tour(page):
    page.goto(URL, wait_until="domcontentloaded")
    page.evaluate("h => window.__overlay(h)", INTRO_HTML)
    page.wait_for_timeout(4600)                         # OVP + charts build behind the card (raw, unscaled)
    page.evaluate("() => window.__hideOverlay()")
    pause(page, 700)

    # 1) Load the mismatch teaching case
    cap(page, "Meet a city hospital, built as a public-private project")
    scroll_to(page, ".presets", "start", 700)
    click_el(page, '.preset[data-preset="hospital"]', ms_after=1800)
    pause(page, 800)

    # 2) It earns lira but borrows dollars
    cap(page, "It is paid in lira &mdash; but it borrowed <span class='big'>85%</span> of its debt in dollars, to save on interest")
    scroll_to(page, "#usdDebtShare", "center", 900)
    move_to(page, "#usdDebtShare", ms_after=1500)
    move_to(page, "#fxRevPct", ms_after=300)            # USD-linked revenue is only 15%
    cap(page, "Only <span class='big'>15%</span> of its revenue is dollar-linked. Income lira, debt dollars.")
    move_to(page, "#fxRevPct", ms_after=2200)

    # 3) On paper it looks financeable
    cap(page, "On paper it looks fine &mdash; coverage 1.23&times;, equity return 15%")
    scroll_to(page, ".kpis", "start", 900)
    move_to(page, "#k-dscr", ms_after=1700)
    move_to(page, "#k-eirr", ms_after=1900)

    # 4) The hidden currency mismatch
    cap(page, "But here is what a normal model hides &mdash; the currency mismatch")
    scroll_to(page, "#fx-tag", "center", 1100)
    move_to(page, "#fx-tag", ms_after=1400)
    cap(page, "<span class='big'>FX cover 0.40</span> &mdash; it owes far more dollars than it earns")
    move_to(page, "#fx-body", dy=-40, ms_after=1500)
    cap(page, "Red bars = years where dollar income can&rsquo;t cover dollar debt")
    move_to(page, "#fx-body", dy=40, ms_after=2400)

    # 5) THE STRESS — drag the lira shock, watch the bank-case DSCR fall
    cap(page, "So the real question: what if the lira falls?")
    scroll_to(page, "#ds-table", "center", 1100)
    move_to(page, "#ds-table", ms_after=1200)
    cap(page, "Bank case, lira shock <span class='big'>+0%</span> &mdash; coverage holds at 1.23&times;")
    set_shock(page, 0, ms_after=1700)
    cap(page, "Lira falls <span class='big'>+30%</span> &mdash; the cushion is gone, 1.01&times;")
    set_shock(page, 30, ms_after=2300)
    cap(page, "Lira falls <span class='big'>+50%</span> &mdash; below 1.0&times;, the project can&rsquo;t pay its loan")
    set_shock(page, 50, ms_after=2600)
    cap(page, "Same project, same revenue &mdash; one currency move and it defaults")
    set_shock(page, 60, ms_after=2600)

    # 6) Contrast — a well-structured deal survives
    cap(page, "Now a well-structured deal &mdash; a toll road with dollar-linked tolls")
    scroll_to(page, ".presets", "start", 700)
    click_el(page, '.preset[data-preset="toll"]', ms_after=1800)
    cap(page, "Dollar revenue matches dollar debt &mdash; FX cover above 1, all green")
    scroll_to(page, "#fx-body", "center", 1100)
    move_to(page, "#fx-body", ms_after=2600)
    cap(page, "The structure &mdash; not the spreadsheet &mdash; is what survives a shock")
    pause(page, 1600)

    # outro
    cap(page, None)
    page.evaluate("h => window.__overlay(h)", OUTRO_HTML)
    page.wait_for_timeout(5000)                         # raw, unscaled


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    shutil.rmtree(REC_DIR, ignore_errors=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            viewport=SIZE, record_video_dir=REC_DIR,
            record_video_size=SIZE, locale="en-US",
            device_scale_factor=1,
        )
        ctx.add_init_script(INIT_JS)
        page = ctx.new_page()
        try:
            tour(page)
            video = page.video
            ctx.close()
            webm = video.path()
            target = os.path.join(REC_DIR, NAME + ".webm")
            shutil.move(webm, target)
            print(f"[rec] done -> {target}", flush=True)
        except Exception as e:
            ctx.close()
            print(f"[rec] FAILED: {e}", flush=True)
            browser.close()
            return
        browser.close()

    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    webm = os.path.join(REC_DIR, NAME + ".webm")
    mp4 = os.path.join(OUT_DIR, NAME + ".mp4")
    jpg = os.path.join(OUT_DIR, NAME + ".jpg")
    subprocess.run([ff, "-y", "-i", webm, "-c:v", "libx264", "-preset", "slow",
                    "-crf", "22", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                    "-an", mp4], check=True, capture_output=True)
    subprocess.run([ff, "-y", "-ss", "10", "-i", mp4, "-frames:v", "1",
                    "-q:v", "3", jpg], check=True, capture_output=True)
    print(f"[enc] {os.path.getsize(mp4)//1024} KB mp4, "
          f"{os.path.getsize(jpg)//1024} KB poster", flush=True)
    shutil.rmtree(REC_DIR, ignore_errors=True)
    print("[done]", flush=True)


if __name__ == "__main__":
    main()
