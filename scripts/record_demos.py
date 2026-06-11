# -*- coding: utf-8 -*-
"""Record short product-demo videos of the portfolio tools with Playwright.

A fake (but visible) mouse cursor is injected into each page; the script then
performs a scripted tour — logging in, switching tabs, typing numbers,
scrolling past charts — while Playwright records video. The .webm recordings
are converted to H.264 .mp4 (Safari/iPhone-safe) with imageio-ffmpeg, and a
poster frame is extracted for each.

Usage:  python scripts/record_demos.py
Needs:  a local server for the site root (default http://localhost:4317),
        `pip install playwright imageio-ffmpeg` + `playwright install chromium`.
"""
import os
import shutil
import subprocess
import sys

from playwright.sync_api import sync_playwright

BASE = os.environ.get("DEMO_BASE_URL", "http://localhost:4317")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "..", "assets", "demos")
REC_DIR = os.path.join(HERE, "_rec_tmp")
SIZE = {"width": 1280, "height": 720}

# Visible cursor + click ripple, re-created on every page load.
CURSOR_JS = """
(() => {
  function ready(fn){ if (document.body) fn(); else document.addEventListener('DOMContentLoaded', fn); }
  ready(() => {
    if (document.getElementById('__demo_cursor')) return;
    const style = document.createElement('style');
    style.textContent = `
      html { scrollbar-width: none; }
      ::-webkit-scrollbar { display: none; }
      #__demo_cursor { position: fixed; z-index: 2147483647; pointer-events: none;
        width: 26px; height: 26px; left: 0; top: 0; transition: transform .08s ease; }
      .__demo_ripple { position: fixed; z-index: 2147483646; pointer-events: none;
        width: 14px; height: 14px; border-radius: 50%; border: 3px solid #2F9BFF;
        transform: translate(-50%,-50%) scale(1); opacity: .9;
        animation: __demo_rip .55s ease-out forwards; }
      @keyframes __demo_rip { to { transform: translate(-50%,-50%) scale(3.4); opacity: 0; } }
    `;
    document.head.appendChild(style);
    const cur = document.createElement('div');
    cur.id = '__demo_cursor';
    cur.innerHTML = `<svg width="26" height="26" viewBox="0 0 24 24">
      <path d="M5 2 L5 19 L9.5 15.5 L12.5 21.5 L15 20 L12 14.5 L18 14 Z"
        fill="#fff" stroke="#1c2330" stroke-width="1.6" stroke-linejoin="round"
        style="filter: drop-shadow(0 2px 4px rgba(0,0,0,.45))"/></svg>`;
    document.body.appendChild(cur);
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
  });
})();
"""


def pause(page, ms):
    page.wait_for_timeout(ms)


def move_to(page, selector, dx=0, dy=0, ms_after=350):
    el = page.locator(selector).first
    el.wait_for(state="visible", timeout=15000)
    box = el.bounding_box()
    if not box:
        return None
    x = box["x"] + box["width"] / 2 + dx
    y = box["y"] + box["height"] / 2 + dy
    page.mouse.move(x, y, steps=32)
    pause(page, ms_after)
    return (x, y)


def click_el(page, selector, dx=0, dy=0, ms_after=700):
    pt = move_to(page, selector, dx, dy, ms_after=250)
    if pt:
        page.mouse.down()
        pause(page, 90)
        page.mouse.up()
        pause(page, ms_after)


def type_into(page, selector, text, ms_after=600):
    click_el(page, selector, ms_after=200)
    page.keyboard.press("Control+a")
    pause(page, 120)
    page.keyboard.type(text, delay=95)
    page.keyboard.press("Tab")
    pause(page, ms_after)


def smooth_scroll(page, dy, ms_after=900):
    page.evaluate("d => window.scrollBy({top: d, behavior: 'smooth'})", dy)
    pause(page, ms_after)


def tour_assetix(page):
    page.goto(BASE + "/assetix.html", wait_until="domcontentloaded")
    pause(page, 1800)
    click_el(page, ".demo-cred", ms_after=800)            # fill admin credentials
    click_el(page, "#loginForm button[type=submit]", ms_after=2000)
    page.mouse.move(640, 400, steps=25)
    smooth_scroll(page, 420, 1300)
    smooth_scroll(page, 420, 1300)
    smooth_scroll(page, -840, 1000)
    click_el(page, 'button[data-p="assets"]', ms_after=1500)
    smooth_scroll(page, 400, 1400)
    click_el(page, 'button[data-p="reports"]', ms_after=1600)
    smooth_scroll(page, 450, 1500)
    click_el(page, 'button[data-p="dash"]', ms_after=1200)
    page.mouse.move(900, 420, steps=30)
    pause(page, 1200)


def tour_dealer(page):
    page.goto(BASE + "/dealer-demo/index.html", wait_until="domcontentloaded")
    pause(page, 2200)
    page.mouse.move(640, 360, steps=25)
    smooth_scroll(page, 430, 1400)
    smooth_scroll(page, 430, 1400)
    smooth_scroll(page, -860, 900)
    click_el(page, '#tabs .tab[data-pane="pane-divisional"]', ms_after=1500)
    smooth_scroll(page, 450, 1500)
    click_el(page, '#tabs .tab[data-pane="pane-leakage"]', ms_after=1600)
    smooth_scroll(page, 400, 1400)
    click_el(page, '#tabs .tab[data-pane="pane-variance"]', ms_after=1600)
    smooth_scroll(page, 420, 1500)
    page.mouse.move(880, 400, steps=30)
    pause(page, 1400)


def tour_grosstonet(page):
    page.goto(BASE + "/gross-to-net.html", wait_until="domcontentloaded")
    pause(page, 1600)
    smooth_scroll(page, 250, 1000)
    click_el(page, 'button[data-p="distributor"]', ms_after=1600)
    click_el(page, 'button[data-p="usedcar"]', ms_after=1600)
    type_into(page, "#gross", "1500", ms_after=1400)
    type_into(page, "#rebates", "260", ms_after=1400)
    move_to(page, "#export-btn", ms_after=1500)


def tour_passthrough(page):
    page.goto("https://namikakmandev.github.io/commercial-finance-tools/",
              wait_until="domcontentloaded")
    pause(page, 4500)                                      # let live FRED data land
    page.mouse.move(640, 380, steps=25)
    smooth_scroll(page, 380, 1300)
    click_el(page, 'button.preset-btn[data-months="24"]', ms_after=1700)
    type_into(page, "#grossMargin", "42", ms_after=1500)
    smooth_scroll(page, 480, 1400)
    smooth_scroll(page, 480, 1500)
    page.mouse.move(820, 420, steps=30)
    pause(page, 1300)


def tour_saas(page):
    page.goto(BASE + "/saas-churn-pricing.html", wait_until="domcontentloaded")
    pause(page, 1600)
    page.mouse.move(640, 380, steps=25)
    for dy, wait in [(550, 1500), (650, 1500), (700, 1500), (700, 1400),
                     (800, 1500), (900, 1500)]:
        smooth_scroll(page, dy, wait)
        page.mouse.move(660 + (dy % 240), 400, steps=18)
    pause(page, 1000)


TOURS = {
    "assetix": tour_assetix,
    "dealer": tour_dealer,
    "gross-to-net": tour_grosstonet,
    "passthrough": tour_passthrough,
    "saas": tour_saas,
}


def ffmpeg_exe():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def main():
    only = sys.argv[1:] or list(TOURS)
    os.makedirs(OUT_DIR, exist_ok=True)
    shutil.rmtree(REC_DIR, ignore_errors=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for name in only:
            print(f"[rec] {name} ...", flush=True)
            ctx = browser.new_context(
                viewport=SIZE, record_video_dir=REC_DIR,
                record_video_size=SIZE, locale="tr-TR",
            )
            ctx.add_init_script(CURSOR_JS)
            page = ctx.new_page()
            try:
                TOURS[name](page)
                video = page.video
                ctx.close()                                # finalizes the file
                webm = video.path()
                target = os.path.join(REC_DIR, name + ".webm")
                shutil.move(webm, target)
                print(f"[rec] {name} done -> {target}", flush=True)
            except Exception as e:
                ctx.close()
                print(f"[rec] {name} FAILED: {e}", flush=True)
        browser.close()

    ff = ffmpeg_exe()
    for name in only:
        webm = os.path.join(REC_DIR, name + ".webm")
        if not os.path.exists(webm):
            continue
        mp4 = os.path.join(OUT_DIR, name + ".mp4")
        jpg = os.path.join(OUT_DIR, name + ".jpg")
        subprocess.run([ff, "-y", "-i", webm, "-c:v", "libx264", "-preset",
                        "slow", "-crf", "27", "-pix_fmt", "yuv420p",
                        "-movflags", "+faststart", "-an", mp4],
                       check=True, capture_output=True)
        subprocess.run([ff, "-y", "-ss", "4", "-i", mp4, "-frames:v", "1",
                        "-q:v", "4", jpg], check=True, capture_output=True)
        print(f"[enc] {name}: {os.path.getsize(mp4)//1024} KB mp4, "
              f"{os.path.getsize(jpg)//1024} KB poster", flush=True)
    shutil.rmtree(REC_DIR, ignore_errors=True)
    print("[done]", flush=True)


if __name__ == "__main__":
    main()
