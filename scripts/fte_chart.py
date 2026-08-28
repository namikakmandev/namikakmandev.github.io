#!/usr/bin/env python3
"""The one chart for the FiveThirtyEight calibration post.

A reliability diagram: what 538 said would happen, against how often it did.
The 45-degree line is perfect calibration. Two series:

  all forecasts   255,057 final, non-live calls across politics and sports.
    They sit on the diagonal — the claim holds.
  competitive political races   the 1,122 forecasts between 10% and 90%, the
    ones anyone argued about. They bow ABOVE the line: 538's favourites won
    more often than 538 said.

Numbers come from data/fte-results.json, written by fte_calibration.py, so the
chart cannot drift away from the analysis. Stdlib only — writes an SVG.

  python3 scripts/fte_chart.py
"""
import json, os, sys

BLUE, ORANGE = "#2f9bff", "#ff6500"
INK, DIM, GRID, PAPER = "#1f2430", "#5b6472", "#d6dce4", "#ffffff"
W, H = 1600, 1000
PAD = 160          # headless Chromium returns a shorter viewport than asked
L, R, T, B = 130, 70, 150, 150          # margins
FONT = ("-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',"
        "Arial,sans-serif")


def main():
    res = json.load(open("data/fte-results.json"))
    hd = res["headline"]
    pw, ph = W - L - R, H - T - B

    def x(v):
        return L + v * pw

    def y(v):
        return T + (1 - v) * ph

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'viewBox="0 0 {W} {H}" font-family="{FONT}">',
           f'<rect width="{W}" height="{H}" fill="{PAPER}"/>']

    # ---- titles
    out += [f'<text x="{L}" y="58" font-size="40" font-weight="700" fill="{INK}">'
            f'When FiveThirtyEight said 70%, did it happen 70% of the time?</text>',
            f'<text x="{L}" y="100" font-size="24" fill="{DIM}">'
            f'{res["raw_rows"]:,} published forecasts, 2008–2022, reduced to '
            f'{hd["all"]["n"]:,} independent calls. Their own archive.</text>']

    # ---- grid + axes
    for i in range(11):
        v = i / 10
        out.append(f'<line x1="{x(v):.1f}" y1="{T}" x2="{x(v):.1f}" y2="{T + ph}" '
                   f'stroke="{GRID}" stroke-width="1"/>')
        out.append(f'<line x1="{L}" y1="{y(v):.1f}" x2="{L + pw}" y2="{y(v):.1f}" '
                   f'stroke="{GRID}" stroke-width="1"/>')
        out.append(f'<text x="{x(v):.1f}" y="{T + ph + 42}" font-size="22" '
                   f'fill="{DIM}" text-anchor="middle">{i * 10}%</text>')
        out.append(f'<text x="{L - 22}" y="{y(v) + 8:.1f}" font-size="22" '
                   f'fill="{DIM}" text-anchor="end">{i * 10}%</text>')

    # ---- perfect-calibration diagonal
    out.append(f'<line x1="{x(0)}" y1="{y(0):.1f}" x2="{x(1)}" y2="{y(1):.1f}" '
               f'stroke="{DIM}" stroke-width="2.5" stroke-dasharray="10 8"/>')

    def series(points, colour, width, dot):
        d = " ".join(f"{'M' if i == 0 else 'L'}{x(p['forecast']):.1f},"
                     f"{y(p['happened']):.1f}" for i, p in enumerate(points))
        out.append(f'<path d="{d}" fill="none" stroke="{colour}" '
                   f'stroke-width="{width}" stroke-linejoin="round"/>')
        for p in points:
            out.append(f'<circle cx="{x(p["forecast"]):.1f}" '
                       f'cy="{y(p["happened"]):.1f}" r="{dot}" fill="{colour}" '
                       f'stroke="{PAPER}" stroke-width="3"/>')

    series(res["curve_all"], BLUE, 4.5, 11)
    series(res["curve_politics_competitive"], ORANGE, 4.5, 11)

    # ---- callout on the underconfident bow
    pts = res["curve_politics_competitive"]
    hi = max(pts, key=lambda p: p["happened"] - p["forecast"])
    hx, hy = x(hi["forecast"]), y(hi["happened"])
    tx, ty = x(0.68), y(0.96)
    out += [f'<line x1="{hx:.1f}" y1="{hy - 14:.1f}" x2="{tx - 14:.1f}" '
            f'y2="{ty + 14:.1f}" stroke="{ORANGE}" stroke-width="2"/>',
            f'<text x="{tx:.1f}" y="{ty:.1f}" font-size="24" font-weight="700" '
            f'fill="{ORANGE}" text-anchor="end">said '
            f'{hi["forecast"] * 100:.0f}%, happened '
            f'{hi["happened"] * 100:.0f}%</text>',
            f'<text x="{tx:.1f}" y="{ty + 32:.1f}" font-size="22" fill="{DIM}" '
            f'text-anchor="end">too cautious, not too confident</text>']

    # ---- axis labels
    out += [f'<text x="{L + pw / 2:.0f}" y="{T + ph + 88}" font-size="25" '
            f'fill="{INK}" text-anchor="middle">what FiveThirtyEight said the '
            f'chance was</text>',
            f'<text x="34" y="{T + ph / 2:.0f}" font-size="25" fill="{INK}" '
            f'text-anchor="middle" transform="rotate(-90 34 '
            f'{T + ph / 2:.0f})">how often it actually happened</text>']

    # ---- legend
    lx, ly = x(0.50), y(0.30)
    out += [f'<line x1="{lx}" y1="{ly + 76:.1f}" x2="{lx + 46}" '
            f'y2="{ly + 76:.1f}" stroke="{DIM}" stroke-width="2.5" '
            f'stroke-dasharray="10 8"/>',
            f'<text x="{lx + 62}" y="{ly + 84:.1f}" font-size="23" fill="{DIM}">'
            f'perfect calibration</text>']
    for colour, label in (
            (BLUE, f'every forecast — slope {hd["all"]["slope"]:.2f} '
                   f'(1.00 = perfect), n={hd["all"]["n"]:,}'),
            (ORANGE, f'competitive political races — slope '
                     f'{hd["politics_competitive"]["slope"]:.2f}, '
                     f'n={hd["politics_competitive"]["n"]:,}')):
        out += [f'<line x1="{lx}" y1="{ly}" x2="{lx + 46}" y2="{ly}" '
                f'stroke="{colour}" stroke-width="4.5"/>',
                f'<circle cx="{lx + 23}" cy="{ly}" r="9" fill="{colour}"/>',
                f'<text x="{lx + 62}" y="{ly + 8}" font-size="23" fill="{INK}">'
                f'{label}</text>']
        ly += 38

    out.append(f'<text x="{L}" y="{H - 26}" font-size="18" fill="{DIM}">'
               f'Data: FiveThirtyEight’s own archive, '
               f'github.com/fivethirtyeight/checking-our-work-data  ·  '
               f'method and every number: '
               f'namikakmandev.github.io/fte-calibration.html</text>')
    out.append('</svg>')

    os.makedirs("assets/linkedin", exist_ok=True)
    path = "assets/linkedin/fte-calibration.svg"
    svg = "\n".join(out)
    with open(path, "w") as fh:
        fh.write(svg)
    print(f"wrote {path} ({os.path.getsize(path):,} bytes)")
    render_png(svg, "assets/linkedin/fte-calibration.png")
    return 0


def find_chrome():
    import glob, shutil
    for pat in ("/opt/pw-browsers/chromium-*/chrome-linux/chrome",
                "/opt/pw-browsers/chromium/chrome-linux/chrome"):
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[-1]
    for name in ("chromium", "chromium-browser", "google-chrome"):
        found = shutil.which(name)
        if found:
            return found
    return None


def _decode_png(raw):
    """-> (width, height, channels, [row bytes]). Enough to crop, no more."""
    import struct, zlib
    pos, idat, w, h, ct = 8, b"", 0, 0, 0
    while pos < len(raw):
        ln = struct.unpack(">I", raw[pos:pos + 4])[0]
        typ, data = raw[pos + 4:pos + 8], raw[pos + 8:pos + 8 + ln]
        if typ == b"IHDR":
            w, h, _, ct = struct.unpack(">IIBB", data[:10])
        elif typ == b"IDAT":
            idat += data
        pos += 12 + ln
    ch = {0: 1, 2: 3, 4: 2, 6: 4}[ct]
    d, stride = zlib.decompress(idat), w * ch
    prev, rows, i = bytearray(stride), [], 0
    for _ in range(h):
        f = d[i]; i += 1
        line = bytearray(d[i:i + stride]); i += stride
        if f:
            for x in range(stride):
                a = line[x - ch] if x >= ch else 0
                b = prev[x]
                c = prev[x - ch] if x >= ch else 0
                if f == 1:
                    line[x] = (line[x] + a) & 255
                elif f == 2:
                    line[x] = (line[x] + b) & 255
                elif f == 3:
                    line[x] = (line[x] + (a + b) // 2) & 255
                else:
                    pp = a + b - c
                    pa, pb, pc = abs(pp - a), abs(pp - b), abs(pp - c)
                    line[x] = (line[x] + (a if (pa <= pb and pa <= pc)
                                          else (b if pb <= pc else c))) & 255
        rows.append(bytes(line))
        prev = line
    return w, h, ch, rows


def _crop_png(path, height):
    """Trim a screenshot to `height` rows, in place."""
    import struct, zlib
    w, h, ch, rows = _decode_png(open(path, "rb").read())
    if h <= height:
        return
    body = b"".join(b"\x00" + r for r in rows[:height])
    ct = {1: 0, 2: 4, 3: 2, 4: 6}[ch]

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    with open(path, "wb") as fh:
        fh.write(b"\x89PNG\r\n\x1a\n"
                 + chunk(b"IHDR", struct.pack(">IIBBBBB", w, height, 8, ct, 0, 0, 0))
                 + chunk(b"IDAT", zlib.compress(body, 9))
                 + chunk(b"IEND", b""))


def render_png(svg, out_path):
    """Rasterise the SVG for LinkedIn, which will not accept an SVG upload.

    Inlined into a zero-margin page rather than loaded through <img>: a
    standalone SVG document picks up the browser's default body margin.
    Headless Chromium also hands back a viewport ~95px shorter than the window
    it was asked for, which silently cuts the axis label and the source line off
    the bottom, so the capture is padded and then cropped back to H.
    """
    import subprocess, tempfile
    chrome = find_chrome()
    if not chrome:
        print("  (no chromium found — SVG written, PNG skipped)")
        return
    with tempfile.TemporaryDirectory() as tmp:
        page = os.path.join(tmp, "chart.html")
        with open(page, "w") as fh:
            fh.write("<!doctype html><meta charset=utf-8>"
                     "<style>html,body{margin:0;padding:0;background:#fff}"
                     "svg{display:block}</style>" + svg)
        cmd = [chrome, "--headless", "--disable-gpu", "--no-sandbox",
               "--hide-scrollbars", "--force-device-scale-factor=1",
               f"--window-size={W},{H + PAD}", "--default-background-color=FFFFFFFF",
               f"--screenshot={out_path}", f"file://{page}"]
        r = subprocess.run(cmd, capture_output=True, text=True)
    if os.path.exists(out_path):
        _crop_png(out_path, H)
        print(f"wrote {out_path} ({os.path.getsize(out_path):,} bytes)")
    else:
        print(f"  (chromium failed, PNG skipped)\n{r.stderr[-400:]}")


if __name__ == "__main__":
    sys.exit(main())
