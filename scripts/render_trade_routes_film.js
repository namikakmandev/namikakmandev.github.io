// Renders film/trade-routes-square.html to PNG frames. Serve the repo root first (python3 -m http.server 8765), then:
//   node scripts/render_trade_routes_film.js <frames-dir> [fps]
//   ffmpeg -framerate 30 -i <frames-dir>/f%04d.png -c:v libx264 -pix_fmt yuv420p -crf 14 -movflags +faststart out.mp4
const { chromium } = require('playwright');
(async () => {
  const dir = process.argv[2], fps = +process.argv[3] || 30;
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1080, height: 1080 }, deviceScaleFactor: 1 });
  const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.goto('http://localhost:8765/film/trade-routes-square.html');
  // fonts load on first use: draw a frame from each part of the film, then wait for them
  for (const t of [0, 10, 39]) await p.evaluate(t => window.film.render(t), t);
  await p.evaluate(() => document.fonts.ready); await p.waitForTimeout(800);
  const only = process.argv[4] ? process.argv[4].split(',').map(Number) : null;
  const n = Math.round((await p.evaluate(() => window.film.duration)) * fps);
  const cv = await p.$('#cv');
  for (let i = 0; i < n; i++) {
    if (only && !only.includes(i)) continue;
    await p.evaluate(t => window.film.render(t), i / fps);
    await cv.screenshot({ path: `${dir}/f${String(i).padStart(4, '0')}.png` });
  }
  console.log('frames', n, 'errors', errs); await b.close();
})();
