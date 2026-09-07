#!/usr/bin/env python3
"""Fetch product logos for the animal pharma price tracker.

Runs on the Actions runner (the dev sandbox has no route to these hosts).
For each product it opens a few official pages, collects every image that
looks like the product's logo (alt text or file name), downloads the
candidates, keeps the ones that decode as images, and writes a manifest so
the page can pick the best one by hand. Nothing here is published on its
own; the chosen file gets embedded in the report as a data URI.
"""
import io, json, os, re, sys, time, hashlib
from html.parser import HTMLParser
from urllib.parse import urljoin
import urllib.request

OUT = "assets/logos/raw"
MANIFEST = "assets/logos/manifest.json"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/127.0 Safari/537.36")

PRODUCTS = {
    "apoquel": {
        "words": ["apoquel"],
        "pages": [
            "https://www.zoetisus.com/products/dogs/apoquel/index.aspx",
            "https://www.zoetisus.com/products/dogs/apoquel/",
            "https://www.zoetispetcare.com/products/apoquel",
            "https://www.apoquel.com/",
            "https://seekvectorlogo.net/apoquel-oclacitinib-tablet-vector-logo-svg/",
        ],
    },
    "cytopoint": {
        "words": ["cytopoint"],
        "pages": [
            "https://www.zoetisus.com/products/dogs/cytopoint/",
            "https://www.zoetispetcare.com/products/cytopoint",
            "https://www.cytopoint.com/",
        ],
    },
    "zenrelia": {
        "words": ["zenrelia"],
        "pages": [
            "https://yourpetandyou.elanco.com/us/our-products/zenrelia",
            "https://my.elanco.com/us/campaign/zenrelia",
            "https://www.zenrelia.com/",
            "https://www.elanco.com/en-us/products/zenrelia",
        ],
    },
    "numelvi": {
        "words": ["numelvi"],
        # the Numelvi hub draws its mark through CSS, so these are taken as-is
        "direct": [
            "https://www.merck-animal-health-usa.com/wp-content/uploads/sites/120/2025/10/Logo.svg",
            "https://www.merck-animal-health-usa.com/wp-content/uploads/sites/120/2025/12/Page-1.png",
            "https://www.merck-animal-health-usa.com/wp-content/uploads/sites/120/2025/12/Image-e1764603029187.png",
            "https://www.merck-animal-health-usa.com/wp-content/uploads/sites/120/2025/11/image-1-1.png",
            "https://www.merck-animal-health-usa.com/wp-content/uploads/sites/120/2026/02/numelvi-dog-icon.png",
            "https://www.merck-animal-health-usa.com/wp-content/uploads/sites/120/2025/11/4f2bc79b399debea828a92b91b6ff93d9f330cbf-e1785294957443.png",
            "https://www.merck-animal-health-usa.com/wp-content/uploads/sites/120/2025/11/6623f2642cca1b1bae587ce6ff4a7bf4961615e3.png",
            "https://www.merck-animal-health-usa.com/wp-content/uploads/sites/120/2025/11/731b0560649a53e9011746fe9af15c7b851834a3.png",
            "https://www.merck-animal-health-usa.com/wp-content/uploads/sites/120/2025/11/f3f7b5f59bb1fc7ebb61c388de96b531291bf97c.png",
            "https://www.merck-animal-health-usa.com/wp-content/uploads/sites/120/2025/11/dee8149206a331b339482fcbae360a8fc486a0cf.png",
            "https://www.merck-animal-health-usa.com/wp-content/uploads/sites/120/2025/11/4b172a6b402de7c137926a610315264d259daa0e.png",
            "https://www.merck-animal-health-usa.com/wp-content/uploads/sites/120/2025/11/6409c6cfea6256ec9bf5f283f8acf7c330a75d36.png",
            "https://www.merck-animal-health-usa.com/wp-content/uploads/sites/120/2025/11/88048a6ad7656bb14cd066e08c99fc761c254207.png",
            "https://www.merck-animal-health-usa.com/wp-content/uploads/sites/120/2025/11/a54e7473d6df980abb4f98dfcd85bdee607bca88.png",
            "https://www.merck-animal-health-usa.com/wp-content/uploads/sites/120/2025/11/e778cf858beadb037b655129ab05b6a50134bc1c-e1763731914425.png",
            "https://www.merck-animal-health-usa.com/wp-content/uploads/sites/120/2025/11/6821fc47721b1bdea59235fac701aa3bb45aced6.png",
            "https://www.merck-animal-health-usa.com/wp-content/uploads/sites/120/2025/10/b254335c6226aba4eb6302081e3496fcecbfec76.png",
        ],
        "pages": [
            "https://www.merck-animal-health-usa.com/hub/numelvi/about-numelvi/",
            "https://www.merck-animal-health-usa.com/hub/numelvi/",
            "https://www.merck-animal-health-usa.com/hub/numelvi/dosing-administration/",
            "https://www.merck-animal-health-usa.com/hub/numelvi/pet-owners/",
            "https://www.merck-animal-health-usa.com/species/dogs/numelvi/",
            "https://www.msd-animal-health.com/species/dogs/numelvi/",
            "https://www.numelvi.com/",
        ],
    },
}


class Imgs(HTMLParser):
    def __init__(self, base):
        super().__init__(); self.base = base; self.found = []; self._svg = 0; self._svgbuf = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("img", "source"):
            for key in ("src", "data-src", "srcset", "data-srcset"):
                v = a.get(key)
                if not v: continue
                for part in v.split(","):
                    u = part.strip().split(" ")[0]
                    if u: self.found.append((urljoin(self.base, u), a.get("alt", ""), a.get("class", "")))
        if tag == "meta" and a.get("property") in ("og:image", "og:image:url") and a.get("content"):
            self.found.append((urljoin(self.base, a["content"]), "og:image", ""))
        if tag == "a" and a.get("href", "").lower().endswith((".svg", ".png")):
            self.found.append((urljoin(self.base, a["href"]), a.get("title", "") or "link", ""))
        st = a.get("style", "")
        for u in re.findall(r"url\(['\"]?([^'\")]+)", st):
            self.found.append((urljoin(self.base, u), "css-bg", a.get("class", "")))
        if tag == "svg":
            self._svg += 1; self._svgbuf = [self.get_starttag_text()]
        elif self._svg:
            self._svgbuf.append(self.get_starttag_text())
    def handle_endtag(self, tag):
        if self._svg:
            self._svgbuf.append(f"</{tag}>")
            if tag == "svg":
                self._svg -= 1
                if not self._svg:
                    self.found.append(("inline-svg:" + "".join(self._svgbuf), "inline svg", ""))
    def handle_data(self, data):
        if self._svg: self._svgbuf.append(data)


def get(url, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=25) as r:
        data = r.read()
        return data if binary else data.decode("utf-8", "replace")


def looks_like(url, alt, cls, words):
    s = (url + " " + alt + " " + cls).lower()
    return any(w in s for w in words) and ("logo" in s or url.lower().endswith(".svg")
                                          or "brand" in s or "wordmark" in s)


def probe(data):
    """(kind, width, height) or None"""
    head = data[:600].lstrip()
    if head.startswith(b"<svg") or b"<svg" in head[:300]:
        m = re.search(rb'viewBox="[\d.\-\s]+?([\d.]+)\s+([\d.]+)"', data[:2000])
        return ("svg", float(m.group(1)) if m else None, float(m.group(2)) if m else None)
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(data)); return (im.format.lower(), im.width, im.height)
    except Exception:
        return None


def main():
    os.makedirs(OUT, exist_ok=True)
    manifest = {"fetched": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "products": {}}
    for pid, spec in PRODUCTS.items():
        cands, seen = [], set()
        for u in spec.get("direct", []):
            seen.add(u); cands.append({"page": "direct", "url": u, "alt": "direct"})
        for page in spec["pages"]:
            try:
                html = get(page)
            except Exception as e:
                manifest.setdefault("errors", []).append({"page": page, "error": str(e)[:200]}); continue
            p = Imgs(page); p.feed(html)
            # stylesheet background images too
            for u in re.findall(r"url\(['\"]?([^'\")]+\.(?:svg|png|webp))", html, re.I):
                p.found.append((urljoin(page, u), "css-url", ""))
            allseen = manifest.setdefault("all_images", {}).setdefault(pid, [])
            for url, alt, cls in p.found:
                if url in seen: continue
                seen.add(url)
                if not url.startswith("inline-svg:"):
                    allseen.append({"page": page, "url": url[:300], "alt": alt[:80]})
                if url.startswith("inline-svg:"):
                    svg = url[len("inline-svg:"):]
                    if any(w in svg.lower() for w in spec["words"]) and len(svg) > 300:
                        cands.append({"page": page, "url": "inline-svg", "alt": alt, "_data": svg.encode()})
                elif looks_like(url, alt, cls, spec["words"]):
                    cands.append({"page": page, "url": url, "alt": alt})
            # og:image and anything else on the product's own domain with the name in it
            time.sleep(1)
        kept = []
        for i, c in enumerate(cands[:30]):
            try:
                data = c.pop("_data", None) or get(c["url"], binary=True)
            except Exception as e:
                c["error"] = str(e)[:120]; continue
            info = probe(data)
            if not info: c["error"] = "not an image"; continue
            kind, w, h = info
            ext = "svg" if kind == "svg" else kind.replace("jpeg", "jpg")
            name = f"{pid}-{i}.{ext}"
            with open(os.path.join(OUT, name), "wb") as f: f.write(data)
            c.update({"file": name, "kind": kind, "w": w, "h": h, "bytes": len(data),
                      "sha1": hashlib.sha1(data).hexdigest()[:10]})
            kept.append(c)
        manifest["products"][pid] = {"candidates": cands, "kept": len(kept)}
        print(pid, "candidates", len(cands), "kept", len(kept), file=sys.stderr)
    with open(MANIFEST, "w") as f:
        json.dump(manifest, f, indent=1)


if __name__ == "__main__":
    main()
