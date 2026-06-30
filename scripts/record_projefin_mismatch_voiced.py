# -*- coding: utf-8 -*-
"""Record a ~3-min, captioned AND VOICED ProjeFin walkthrough on currency mismatch.

Pipeline:
  1) Synthesize one narration clip per beat with Windows SAPI (Microsoft David).
  2) Probe each clip's length.
  3) Drive the tool with Playwright; each beat shows its caption and waits for that
     clip's length, logging the exact wall-clock offset the caption appears.
  4) Encode the silent video, then mux the clips back in at their logged offsets
     (adelay + amix), so voice and subtitles stay in sync regardless of action jitter.

Caption text may use pretty glyphs; NARRATION text is kept plain ASCII so SAPI reads
it cleanly and PowerShell 5.1 doesn't mangle it.

Output: assets/demos/projefin-mismatch.mp4 (+ .jpg poster) — now with a voice track.
Usage:  python scripts/record_projefin_mismatch_voiced.py
Needs:  local server on :4317, playwright (+chromium), imageio-ffmpeg, Windows SAPI.
"""
import os
import re
import shutil
import subprocess
import time

from playwright.sync_api import sync_playwright

URL = "http://localhost:4317/project-finance.html"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "..", "assets", "demos")
REC_DIR = os.path.join(HERE, "_rec_pf_tmp")
AUD_DIR = os.path.join(HERE, "_aud_tmp")
SIZE = {"width": 1920, "height": 1080}
NAME = "projefin-mismatch"
LEAD = 0.25        # shift audio later to match video startup lag (seconds)
TAIL = 0.55        # extra dwell after each narration clip (seconds)

# ---- the script: (kind, caption_html, narration_ascii, [pre-actions]) ----
# pre-actions: ('scroll', sel[, block]) | ('move', sel[, dx, dy]) | ('click', sel) | ('shock', pct)
BEATS = [
    ("intro", None,
     "This is Proje Fin, a project finance model. Let me show you how a cheap dollar loan can quietly sink a lira project.",
     []),
    ("cap", "Meet a city hospital, built as a public-private project",
     "Here is a city hospital, built as a public private partnership.",
     [("scroll", ".presets", "start"), ("click", '.preset[data-preset="hospital"]')]),
    ("cap", "Paid in lira &mdash; but it borrowed <span class='big'>85%</span> of its debt in dollars",
     "It earns its money in Turkish lira. But to save on interest, it borrowed eighty five percent of its debt in U S dollars.",
     [("scroll", "#usdDebtShare", "center"), ("move", "#usdDebtShare")]),
    ("cap", "Only <span class='big'>15%</span> of revenue is dollar-linked &mdash; income lira, debt dollars",
     "Only fifteen percent of its revenue is linked to the dollar. Income in lira, debt in dollars. That is the mismatch.",
     [("move", "#fxRevPct")]),
    ("cap", "On paper it looks financeable &mdash; 1.23&times; coverage, 15% return",
     "On paper, it looks perfectly financeable. Debt coverage of one point two three, and an equity return around fifteen percent.",
     [("scroll", ".kpis", "start"), ("move", "#k-dscr")]),
    ("cap", "But here is what a normal model hides &mdash; the currency mismatch",
     "But here is what an ordinary model hides. The currency mismatch.",
     [("scroll", "#fx-tag", "center"), ("move", "#fx-tag")]),
    ("cap", "<span class='big'>FX cover 0.40</span> &mdash; it owes far more dollars than it earns",
     "Dollar cover is just zero point four. The project owes far more dollars than it earns.",
     [("move", "#fx-body", 0, -40)]),
    ("cap", "Red bars = years dollar income can&rsquo;t cover dollar debt",
     "Every red bar is a year where dollar income cannot cover the dollar debt.",
     [("move", "#fx-body", 0, 40)]),
    ("cap", "So the real question: what if the lira falls?",
     "So let us ask the real question. What happens if the lira falls?",
     [("scroll", "#ds-table", "center"), ("move", "#ds-table")]),
    ("cap", "Lira shock <span class='big'>+0%</span> &mdash; coverage holds at 1.23&times;",
     "With no shock, coverage holds at one point two three.",
     [("shock", 0)]),
    ("cap", "Lira falls <span class='big'>+30%</span> &mdash; the cushion is gone, 1.01&times;",
     "Let the lira fall thirty percent, and the cushion is gone. One point zero one.",
     [("shock", 30)]),
    ("cap", "Lira falls <span class='big'>+50%</span> &mdash; below 1.0&times;, it can&rsquo;t pay its loan",
     "A fifty percent fall pushes it below one. The project can no longer pay its loan.",
     [("shock", 50)]),
    ("cap", "Same project, same revenue &mdash; one currency move and it defaults",
     "Same project, same revenue. One currency move, and it defaults.",
     [("shock", 60)]),
    ("cap", "Now a well-structured deal &mdash; a toll road with dollar-linked tolls",
     "Now compare a well structured deal. A toll road, with dollar linked toll revenue.",
     [("scroll", ".presets", "start"), ("click", '.preset[data-preset="toll"]')]),
    ("cap", "Dollar revenue matches dollar debt &mdash; cover above 1, all green",
     "Here, dollar revenue matches dollar debt. Cover above one, all green. The same shock barely touches it.",
     [("scroll", "#fx-body", "center"), ("move", "#fx-body")]),
    ("outro", None,
     "The structure, not the spreadsheet, is what survives a shock. Proje Fin shows you which side of that line you are on, before you sign.",
     []),
]

PS_TTS = r"""
param([string]$Manifest,[string]$OutDir)
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
try { $s.SelectVoice("Microsoft David Desktop") } catch {}
$s.Rate = -1
Get-Content -LiteralPath $Manifest -Encoding UTF8 | ForEach-Object {
  if ($_ -match '^(\d+)\t(.*)$') {
    $idx = $Matches[1]; $txt = $Matches[2]
    $out = Join-Path $OutDir ("seg{0}.wav" -f $idx)
    $s.SetOutputToWaveFile($out)
    [void]$s.Speak($txt)
  }
}
$s.Dispose()
"""

INIT_JS = r"""
(() => {
  function ready(fn){ if (document.body) fn(); else document.addEventListener('DOMContentLoaded', fn); }
  ready(() => {
    if (document.getElementById('__demo_cursor')) return;
    const style = document.createElement('style');
    style.textContent = `
      html { scrollbar-width: none; } ::-webkit-scrollbar { display: none; }
      .layout { grid-template-columns: 360px 1fr !important; max-width: 1840px !important; }
      #__demo_cursor { position: fixed; z-index: 2147483647; pointer-events: none;
        width: 32px; height: 32px; left: 0; top: 0; transition: transform .08s ease, opacity .25s ease; }
      .__demo_ripple { position: fixed; z-index: 2147483646; pointer-events: none;
        width: 18px; height: 18px; border-radius: 50%; border: 3px solid #2F9BFF;
        transform: translate(-50%,-50%) scale(1); opacity:.9; animation: __demo_rip .55s ease-out forwards; }
      @keyframes __demo_rip { to { transform: translate(-50%,-50%) scale(3.6); opacity: 0; } }
      #__cap { position: fixed; left:0; right:0; bottom:0; z-index: 2147483600;
        background: linear-gradient(0deg, rgba(15,17,23,.985), rgba(15,17,23,.90));
        border-top: 2px solid #19C37D; padding: 26px 44px 32px; min-height: 104px;
        font-family: 'IBM Plex Sans', sans-serif; color:#E6E8EE; font-size: 31px;
        font-weight: 600; line-height: 1.32; display:flex; align-items:center; gap:20px; transition: opacity .25s ease; }
      #__cap.hidden { opacity: 0; }
      #__cap .dot { width:14px; height:14px; border-radius:50%; background:#19C37D; flex-shrink:0; box-shadow:0 0 16px #19C37D; }
      #__cap .big { font-family:'IBM Plex Mono',monospace; color:#FF6500; font-weight:600; }
      #__ovl { position: fixed; inset:0; z-index: 2147483640; background:#0F1117; display:flex; flex-direction:column;
        align-items:center; justify-content:center; text-align:center; padding:80px;
        font-family:'IBM Plex Sans',sans-serif; color:#E6E8EE; transition: opacity .45s ease; opacity:1; }
      #__ovl.hidden { opacity:0; pointer-events:none; }
    `;
    document.head.appendChild(style);
    const cur = document.createElement('div');
    cur.id = '__demo_cursor';
    cur.innerHTML = `<svg width="32" height="32" viewBox="0 0 24 24"><path d="M5 2 L5 19 L9.5 15.5 L12.5 21.5 L15 20 L12 14.5 L18 14 Z" fill="#fff" stroke="#1c2330" stroke-width="1.6" stroke-linejoin="round" style="filter: drop-shadow(0 2px 5px rgba(0,0,0,.5))"/></svg>`;
    document.body.appendChild(cur);
    const cap = document.createElement('div');
    cap.id = '__cap'; cap.className = 'hidden';
    cap.innerHTML = '<span class="dot"></span><span id="__captxt"></span>';
    document.body.appendChild(cap);
    const ovl = document.createElement('div'); ovl.id = '__ovl'; document.body.appendChild(ovl);
    window.addEventListener('mousemove', e => { cur.style.left = e.clientX+'px'; cur.style.top = e.clientY+'px'; }, true);
    window.addEventListener('mousedown', e => { cur.style.transform='scale(.82)';
      const r=document.createElement('div'); r.className='__demo_ripple'; r.style.left=e.clientX+'px'; r.style.top=e.clientY+'px';
      document.body.appendChild(r); setTimeout(()=>r.remove(),600); }, true);
    window.addEventListener('mouseup', ()=>{ cur.style.transform='scale(1)'; }, true);
    window.__setCap = (html) => { const t=document.getElementById('__captxt'), bar=document.getElementById('__cap');
      if (html===null){ bar.classList.add('hidden'); return; } t.innerHTML=html; bar.classList.remove('hidden'); };
    window.__overlay = (html) => { ovl.innerHTML=html; ovl.classList.remove('hidden'); cur.style.opacity='0'; };
    window.__hideOverlay = () => { ovl.classList.add('hidden'); cur.style.opacity='1'; };
    window.__flashDSCR = () => { const rows=[...document.querySelectorAll('#ds-body tr')];
      const r=rows.find(tr=>tr.cells[0].textContent.includes('Min DSCR')); if(!r)return; const c=r.cells[2];
      c.style.transition='all .25s ease'; c.style.outline='3px solid #FF6500'; c.style.background='rgba(255,101,0,.20)';
      setTimeout(()=>{c.style.outline='';c.style.background='';},1200); };
    window.__setShock = (v) => { const e=document.getElementById('dsFx'); e.value=v; e.dispatchEvent(new Event('input',{bubbles:true})); };
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


def ff_exe():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def probe_dur(ff, path):
    out = subprocess.run([ff, "-i", path], capture_output=True, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", out)
    if not m:
        return 3.0
    h, mn, s = m.groups()
    return int(h) * 3600 + int(mn) * 60 + float(s)


def synth_all(ff, texts):
    os.makedirs(AUD_DIR, exist_ok=True)
    manifest = os.path.join(AUD_DIR, "lines.tsv")
    with open(manifest, "w", encoding="utf-8") as f:
        for i, t in enumerate(texts):
            f.write(f"{i}\t{t}\n")
    ps = os.path.join(AUD_DIR, "tts.ps1")
    with open(ps, "w", encoding="utf-8") as f:
        f.write(PS_TTS)
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-File", ps, "-Manifest", manifest, "-OutDir", AUD_DIR], check=True)
    durs = []
    for i in range(len(texts)):
        w = os.path.join(AUD_DIR, f"seg{i}.wav")
        if not os.path.exists(w):
            raise RuntimeError(f"TTS clip missing: {w}")
        durs.append(probe_dur(ff, w))
    return durs


# ---- playwright helpers ----
def pause(page, ms):
    page.wait_for_timeout(int(ms))


def move_to(page, selector, dx=0, dy=0, ms_after=300):
    el = page.locator(selector).first
    el.wait_for(state="visible", timeout=15000)
    box = el.bounding_box()
    if not box:
        return
    x = box["x"] + box["width"] / 2 + dx
    y = box["y"] + box["height"] / 2 + dy
    page.mouse.move(x, y, steps=26)
    pause(page, ms_after)


def click_el(page, selector, ms_after=900):
    move_to(page, selector, ms_after=260)
    page.mouse.down(); pause(page, 90); page.mouse.up()
    pause(page, ms_after)


def scroll_to(page, selector, block="center", ms_after=600):
    page.evaluate("(s,b)=>{const e=document.querySelector(s); if(e) e.scrollIntoView({behavior:'smooth',block:b});}",
                  [selector, block])
    pause(page, ms_after)


def run_pre(page, pre):
    for a in pre:
        op = a[0]
        if op == "scroll":
            scroll_to(page, a[1], a[2] if len(a) > 2 else "center", 650)
        elif op == "move":
            move_to(page, a[1], a[2] if len(a) > 2 else 0, a[3] if len(a) > 3 else 0, 300)
        elif op == "click":
            click_el(page, a[1], ms_after=900)
        elif op == "shock":
            page.evaluate("v=>window.__setShock(v)", a[1])
            page.evaluate("()=>window.__flashDSCR()")
            pause(page, 280)


def tour(page, durs):
    t0 = time.time()
    seg = []   # (idx, offset_seconds)
    page.goto(URL, wait_until="domcontentloaded")
    for i, (kind, cap_html, _say, pre) in enumerate(BEATS):
        run_pre(page, pre)
        if kind == "intro":
            page.evaluate("h=>window.__overlay(h)", INTRO_HTML)
        elif kind == "outro":
            page.evaluate("() => window.__setCap(null)")
            page.evaluate("h=>window.__overlay(h)", OUTRO_HTML)
        else:
            page.evaluate("h=>window.__setCap(h)", cap_html)
        seg.append((i, time.time() - t0))
        pause(page, (durs[i] + TAIL) * 1000)
        if kind == "intro":
            page.evaluate("()=>window.__hideOverlay()")
            pause(page, 400)
    return seg


def main():
    ff = ff_exe()
    texts = [b[2] for b in BEATS]
    print("[tts] synthesizing", len(texts), "clips...", flush=True)
    durs = synth_all(ff, texts)
    print("[tts] done. total speech %.1fs" % sum(durs), flush=True)

    os.makedirs(OUT_DIR, exist_ok=True)
    shutil.rmtree(REC_DIR, ignore_errors=True)
    seg = None
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport=SIZE, record_video_dir=REC_DIR,
                                  record_video_size=SIZE, locale="en-US", device_scale_factor=1)
        ctx.add_init_script(INIT_JS)
        page = ctx.new_page()
        try:
            seg = tour(page, durs)
            video = page.video
            ctx.close()
            shutil.move(video.path(), os.path.join(REC_DIR, NAME + ".webm"))
            print("[rec] video captured", flush=True)
        except Exception as e:
            ctx.close(); browser.close()
            print(f"[rec] FAILED: {e}", flush=True)
            return
        browser.close()

    webm = os.path.join(REC_DIR, NAME + ".webm")
    silent = os.path.join(REC_DIR, NAME + "_silent.mp4")
    subprocess.run([ff, "-y", "-i", webm, "-c:v", "libx264", "-preset", "slow", "-crf", "22",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", silent],
                   check=True, capture_output=True)

    # mux: place each clip at its logged offset (adelay) and mix (normalize=0 keeps full volume)
    mp4 = os.path.join(OUT_DIR, NAME + ".mp4")
    jpg = os.path.join(OUT_DIR, NAME + ".jpg")
    cmd = [ff, "-y", "-i", silent]
    for i in range(len(BEATS)):
        cmd += ["-i", os.path.join(AUD_DIR, f"seg{i}.wav")]
    parts, mix = [], ""
    for idx, off in seg:
        d = max(0, int((off + LEAD) * 1000))
        parts.append(f"[{idx + 1}]adelay={d}:all=1[a{idx}]")
        mix += f"[a{idx}]"
    fc = ";".join(parts) + ";" + mix + f"amix=inputs={len(seg)}:normalize=0[aout]"
    cmd += ["-filter_complex", fc, "-map", "0:v", "-map", "[aout]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", mp4]
    subprocess.run(cmd, check=True, capture_output=True)
    subprocess.run([ff, "-y", "-ss", "10", "-i", mp4, "-frames:v", "1", "-q:v", "3", jpg],
                   check=True, capture_output=True)
    print(f"[enc] {os.path.getsize(mp4)//1024} KB mp4 (voiced), {os.path.getsize(jpg)//1024} KB poster", flush=True)
    shutil.rmtree(REC_DIR, ignore_errors=True)
    shutil.rmtree(AUD_DIR, ignore_errors=True)
    print("[done]", flush=True)


if __name__ == "__main__":
    main()
