#!/usr/bin/env python3
"""One question: how many tablets in a Petlove Apoquel box?
                                    -> data/_petlove-pack-probe.json (+ images)

The archived page proves strength and price per variant but never states the
tablet count. Three doors, tried patiently (the archive throttles bursts, and
a timeout is throttling, not absence):

  1. Petlove's own image CDN, live. The 403 was on the PRODUCT page; static
     images often sit behind a different, open door. The carton in the photo
     states its own count.
  2. The same images via the newest Wayback capture (im_ modifier).
  3. Count vocabulary anywhere in an older capture's text - earlier page copy
     sometimes stated what the current copy dropped.

Publishes nothing; a person reads the result.
"""
import gzip, io, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request

OUT = "data/_petlove-pack-probe.json"
CAP = 2 * 1024 * 1024
UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) "
                     "Chrome/126.0.0.0 Safari/537.36"),
      "Accept-Encoding": "gzip"}

PAGE = "https://www.petlove.com.br/apoquel-dermatologico-zoetis-para-caes/p"
IMAGES = [
    "https://www.petlove.com.br/images/products/179253/product/31153-1_1.jpg",
    "https://www.petlove.com.br/images/products/179254/product/31153-2_1.jpg",
    "https://www.petlove.com.br/images/products/179259/product/31153-3_1.jpg",
]
NEWEST_TS = "20251218064820"
OLDER_TS = ["20250913004046", "20240615064243", "20230123233201", "20211201023835"]


def get(url, timeout=120, tries=4):
    last = None
    for i in range(tries):
        if i:
            time.sleep(10 * (2 ** (i - 1)))
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read(CAP + 1)
                if r.headers.get("Content-Encoding") == "gzip" or body[:2] == b"\x1f\x8b":
                    try:
                        body = gzip.GzipFile(fileobj=io.BytesIO(body)).read(CAP + 1)
                    except OSError:
                        pass
                return r.status, body[:CAP]
        except Exception as ex:
            last = ex
    raise last


def pack_windows(text):
    wins = []
    for mm in re.finditer(
            r"(?:cont[eé]m|caixa|embalagem|cartela|com)\s+\d{1,3}\s*"
            r"(?:comprimidos?|cp\b|unidades?)|\d{1,3}\s*comprimidos?", text, re.I):
        wins.append(re.sub(r"\s+", " ", text[max(0, mm.start()-160):mm.end()+160]))
    return wins[:12]


def main():
    doc = {"probe": "petlove pack count",
           "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "images": [], "text_hunts": []}
    os.makedirs("data", exist_ok=True)

    for img in IMAGES:
        name = img.rsplit("/", 1)[1].replace(".jpg", "")
        rec = {"url": img}
        try:
            status, blob = get(img, tries=2)
            rec["route"], rec["status"], rec["bytes"] = "live-cdn", status, len(blob)
        except Exception as ex:
            rec["live_error"] = f"{type(ex).__name__}: {ex}"
            try:
                status, blob = get(
                    f"https://web.archive.org/web/{NEWEST_TS}im_/{img}")
                rec["route"], rec["status"], rec["bytes"] = "wayback", status, len(blob)
            except Exception as ex2:
                rec["wayback_error"] = f"{type(ex2).__name__}: {ex2}"
                blob = None
        if blob and blob[:3] == b"\xff\xd8\xff":
            path = f"data/_petlove-box-{name}.jpg"
            open(path, "wb").write(blob)
            rec["file"] = path
        elif blob is not None:
            rec["not_jpeg_head"] = blob[:40].decode("latin-1")
        doc["images"].append(rec)
        print("image", name, rec.get("route"), rec.get("status"),
              rec.get("bytes"), rec.get("file", rec.get("live_error", "")))
        time.sleep(4)

    for ts in OLDER_TS:
        rec = {"ts": ts}
        try:
            status, blob = get(f"https://web.archive.org/web/{ts}id_/{PAGE}")
            text = blob.decode("utf-8", "replace")
            rec["status"], rec["bytes"] = status, len(blob)
            rec["windows"] = pack_windows(text)
            print(f"capture {ts}: {len(rec['windows'])} pack windows")
            if rec["windows"]:
                doc["text_hunts"].append(rec)
                break
        except Exception as ex:
            rec["error"] = f"{type(ex).__name__}: {ex}"
            print(f"capture {ts}: {ex}")
        doc["text_hunts"].append(rec)
        time.sleep(6)

    json.dump(doc, open(OUT, "w"), indent=1, ensure_ascii=False)
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
