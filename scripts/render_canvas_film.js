// Render a deterministic canvas scene (one that exposes window.__seek(t),
// window.__W, window.__H, window.__DUR) frame by frame into an H.264 MP4.
//
//   node scripts/render_canvas_film.js film/tech-scalers.html notes/tech-scalers-post.mp4
//   node scripts/render_canvas_film.js film/tech-scalers.html --stills 2,8,14 /tmp/out
//
// Frames are PNGs piped straight into ffmpeg, nothing touches the disk but the
// MP4. A silent AAC track is added so every player and feed accepts the file.
// Needs: the playwright npm package with its Chromium, and ffmpeg on PATH.
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const args = process.argv.slice(2);
const scene = args[0];
const fps = Number((args.find(a => a.startsWith('--fps=')) || '--fps=30').slice(6));
const stillsIdx = args.indexOf('--stills');

if (!scene) { console.error('usage: render_canvas_film.js <scene.html> <out.mp4> | --stills t1,t2 <dir>'); process.exit(2); }

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1350 }, deviceScaleFactor: 1 });
  await page.goto('file://' + path.resolve(scene));
  await page.evaluate(() => document.fonts.ready);
  const meta = await page.evaluate(() => ({ W: window.__W, H: window.__H, DUR: window.__DUR }));
  await page.setViewportSize({ width: meta.W, height: meta.H });

  const frameAt = async (t) => {
    const dataUrl = await page.evaluate((t) => { window.__seek(t); return document.getElementById('c').toDataURL('image/png'); }, t);
    return Buffer.from(dataUrl.split(',')[1], 'base64');
  };

  if (stillsIdx >= 0) {
    const times = args[stillsIdx + 1].split(',').map(Number);
    const dir = args[stillsIdx + 2];
    fs.mkdirSync(dir, { recursive: true });
    for (const t of times) {
      fs.writeFileSync(path.join(dir, `t${t.toFixed(1).replace('.', '_')}.png`), await frameAt(t));
    }
    console.log(`${times.length} stills in ${dir}`);
    await browser.close();
    return;
  }

  const out = args[1];
  const n = Math.round(meta.DUR * fps);
  const ff = spawn('ffmpeg', [
    '-y', '-loglevel', 'error',
    '-f', 'image2pipe', '-framerate', String(fps), '-i', '-',
    '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo',
    '-shortest',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p',
    '-c:a', 'aac', '-b:a', '64k',
    '-movflags', '+faststart',
    out,
  ], { stdio: ['pipe', 'inherit', 'inherit'] });

  for (let i = 0; i < n; i++) {
    const buf = await frameAt(i / fps);
    if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
    if (i % (fps * 5) === 0) process.stdout.write(`frame ${i}/${n}\n`);
  }
  ff.stdin.end();
  const code = await new Promise((r) => ff.on('close', r));
  await browser.close();
  if (code !== 0) { console.error('ffmpeg failed'); process.exit(1); }
  console.log(`wrote ${out}: ${n} frames at ${fps} fps, ${meta.DUR} s`);
})();
