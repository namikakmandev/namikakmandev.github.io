# -*- coding: utf-8 -*-
"""Capture still poster frames for project cards that have no recorded demo.

Serves the site root on a local port, opens each page at the same 1280x720 frame
the demo recordings use, waits for charts/data to settle, and writes a .jpg into
assets/demos/ — so a card without a video still gets a real screenshot rather
than a placeholder.

Usage:  python scripts/shoot_posters.py
Needs:  `pip install playwright` + `playwright install chromium`.
"""
import functools
import http.server
import os
import socketserver
import threading

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
OUT_DIR = os.path.join(ROOT, "assets", "demos")
PORT = 4318
SIZE = {"width": 1280, "height": 720}

# (page, output name, css selector to wait for, extra settle time in ms)
SHOTS = [
    ("broiler-margin.html", "broiler-margin.jpg", "#svg path", 2500),
    ("report-to-dashboard.html", "report-to-dashboard.jpg", ".section-title", 2000),
]


def serve():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("127.0.0.1", PORT), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def main():
    httpd = serve()
    os.makedirs(OUT_DIR, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport=SIZE, device_scale_factor=2)
        # Hide scrollbars so the frame matches the recorded demos.
        page.add_init_script(
            "document.addEventListener('DOMContentLoaded',()=>{"
            "const s=document.createElement('style');"
            "s.textContent='html{scrollbar-width:none}::-webkit-scrollbar{display:none}';"
            "document.head.appendChild(s);});"
        )
        for src, out, wait_for, settle in SHOTS:
            page.goto(f"http://127.0.0.1:{PORT}/{src}", wait_until="networkidle")
            try:
                page.wait_for_selector(wait_for, timeout=15000)
            except Exception:
                print(f"  ! {src}: '{wait_for}' never appeared, shooting anyway")
            page.wait_for_timeout(settle)
            path = os.path.join(OUT_DIR, out)
            page.screenshot(path=path, type="jpeg", quality=82)
            print(f"  + {out}  ({os.path.getsize(path) // 1024} KB)")
        browser.close()
    httpd.shutdown()


if __name__ == "__main__":
    main()
