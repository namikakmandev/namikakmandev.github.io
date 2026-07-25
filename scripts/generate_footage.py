#!/usr/bin/env python3
"""Parite: Sığır — Runway API ile çekim üretimi (GitHub Actions içinde koşar).

Kullanım (workflow input'ları):
  SHOTS="1"      → yalnızca 1. çekim (ilk test için)
  SHOTS="1-12"   → tüm çekimler
  TAKES="1"      → çekim başına deneme sayısı

RUNWAY_API_KEY repo secret'ından gelir. Üretilen MP4'ler footage/shotNN-X.mp4
olarak kaydedilir; commit işini workflow yapar.

API notu: Runway dev API (api.dev.runwayml.com). Metinden-videoya uç noktası
birden fazla sürümde değiştiği için script iki şemayı da dener ve ham yanıtları
loglar — ilk koşu, gerekirse şemayı netleştirmek için de kullanılır.
"""
import json, os, sys, time, urllib.request, urllib.error

API = "https://api.dev.runwayml.com/v1"
KEY = os.environ.get("RUNWAY_API_KEY", "").strip()
VER = os.environ.get("RUNWAY_VERSION", "2024-11-06")

STYLE = ("Cinematic documentary footage, shot on ARRI Alexa with 35mm anamorphic lens, "
         "golden hour warm backlight, volumetric dust in air, shallow depth of field, "
         "natural film grain, muted earthy palette of amber ochre and deep blue shadows, "
         "National Geographic style, photorealistic, steady professional camera work. "
         "No text, no watermark, no logos, no human faces in close-up. ")

SHOTS = {
 1:"Aerial drone shot slowly pushing forward over a large herd of cattle grazing on a vast dry golden steppe at sunset, long shadows stretching across the land, warm haze on the horizon.",
 2:"Low tracking shot moving alongside walking beef cattle, backlit dust glowing around their legs, golden rim light on their backs, dry grass in foreground bokeh.",
 3:"Close-up of a single cow's head in profile at dawn, warm breath visible in cold air, catchlight in the eye, soft focus background of the herd.",
 4:"Vintage 16mm archival film look with scratches and gate weave: 1970s American cattle feedlot, cowboys on horseback in far distance as silhouettes, faded Kodachrome colors, slight flicker.",
 5:"Cracked dry lakebed earth in extreme foreground, a thin line of cattle walking across shimmering heat haze in the distance, harsh midday sun, bleached colors, slow dolly forward.",
 6:"Empty cattle feedlot pens at blue-hour dusk, gates slightly open, dust and straw blowing in wind, one distant silhouetted cow, melancholic mood, static wide shot.",
 7:"Macro slow-motion shot of golden corn kernels pouring and cascading inside a grain silo, individual kernels catching warm light, dust particles floating.",
 8:"Massive bulk cargo ship loaded with grain at an industrial port at sunset, cranes silhouetted, slow aerial orbit, dramatic orange sky with dark clouds gathering.",
 9:"Misty green European pasture at early morning, young bulls grazing near an old stone barn, soft diffused light, dew on grass, gentle push-in.",
 10:"Rustic Anatolian village barn interior at dawn, warm lantern light, cattle at a feed trough eating hay, steam rising, farmer's hands pouring feed seen from behind, documentary handheld feel.",
 11:"Livestock auction yard at golden hour seen from high angle, cattle moving through wooden corridors, buyers as distant silhouettes on fences, dust in light shafts.",
 12:"Single cow standing on a ridge in silhouette against deep orange twilight sky, first stars appearing above, camera slowly pulling back, vast empty landscape, contemplative and still.",
}

def call(path, body=None, method=None):
    req = urllib.request.Request(API + path,
        data=json.dumps(body).encode() if body is not None else None,
        method=method or ("POST" if body is not None else "GET"),
        headers={"Authorization": f"Bearer {KEY}",
                 "X-Runway-Version": VER,
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")

# API'nin kabul ettiği modeller (ilk koşunun 400 yanıtından): gen3a_turbo, gen4.5,
# kling2.5_turbo_pro, kling3.0_pro/standard/4k, klingO3_pro/standard/4k,
# seedance2, seedance2_fast, seedance2_mini, happyhorse_1_0.
# gen4_turbo artık yok → taslak için gen3a_turbo (~$0.05/sn), final gen4.5 (~$0.15/sn).
MODEL = os.environ.get("MODEL", "gen3a_turbo")
DUR = int(os.environ.get("DURATION", "10"))
COST = {"gen4.5": 0.15, "gen3a_turbo": 0.05}

FALLBACK = os.environ.get("FALLBACK", "1") == "1"

def pick_vertical(vals):
    """İzin verilen oranlardan dikey (9:16'ya en yakın, en yüksek çözünürlüklü) olanı seç."""
    best = None
    for v in vals:
        try:
            w, h = map(int, str(v).split(":"))
        except ValueError:
            continue
        if h > w and (best is None or w > best[0]):
            best = (w, h, v)
    return best[2] if best else None

def start_task(prompt):
    """Metinden-videoya. 400 dönerse hata mesajındaki izinli değerlere uyum sağlar:
    oran/süre modele göre düzeltilir; model geçersizse (FALLBACK=1 iken) gen4.5'e düşer."""
    body = {"model": MODEL, "promptText": prompt, "ratio": "720:1280", "duration": DUR}
    for _ in range(4):
        st, js = call("/text_to_video", body)
        print(f"  POST /text_to_video model={body['model']} ratio={body['ratio']} dur={body['duration']} -> {st}: {json.dumps(js)[:300]}")
        if st in (200, 201) and js.get("id"):
            return js["id"]
        if st != 400:
            return None
        fixed = False
        for iss in js.get("issues", []):
            vals = [str(v) for v in (iss.get("values") or [])]
            if not vals:
                continue
            if all(":" in v for v in vals):                     # izinli oran listesi
                nv = pick_vertical(vals)
                if nv and body["ratio"] != nv:
                    body["ratio"] = nv; fixed = True
            elif all(v.isdigit() for v in vals):                # izinli süre listesi
                nd = int(min(vals, key=lambda x: abs(int(x) - DUR)))
                if body["duration"] != nd:
                    body["duration"] = nd; fixed = True
            elif body["model"] not in vals:                     # izinli model listesi
                if FALLBACK and "gen4.5" in vals and body["model"] != "gen4.5":
                    body["model"] = "gen4.5"; fixed = True
        if not fixed:
            return None
    return None

def wait_task(tid, timeout=900):
    t0 = time.time()
    while time.time() - t0 < timeout:
        st, js = call(f"/tasks/{tid}")
        status = js.get("status")
        if status in ("SUCCEEDED", "FAILED", "CANCELLED"):
            return js
        time.sleep(10)
    return {"status": "TIMEOUT"}

def main():
    if not KEY:
        sys.exit("RUNWAY_API_KEY yok")
    spec = os.environ.get("SHOTS", "1")
    takes = int(os.environ.get("TAKES", "1"))
    if "-" in spec:
        a, b = spec.split("-"); ids = range(int(a), int(b) + 1)
    else:
        ids = [int(x) for x in spec.split(",")]
    os.makedirs("footage", exist_ok=True)
    n = len(list(ids)) * takes
    est = n * DUR * COST.get(MODEL, 0.15)
    print(f"PLAN: {n} üretim × {DUR}sn × {MODEL} ≈ ${est:.2f} tahmini maliyet")
    ok, fail = [], []
    mtag = "".join(c for c in MODEL if c.isalnum())   # kling3.0_pro -> kling30pro
    for i in ids:
        for t in range(takes):
            tag = chr(ord('a') + t)
            out = f"footage/shot{i:02d}-{mtag}-{tag}.mp4"
            if os.path.exists(out):
                print(f"skip {out} (var)"); continue
            print(f"== SHOT {i} take {tag} ==")
            tid = start_task(STYLE + SHOTS[i])
            if not tid:
                fail.append(out); continue
            js = wait_task(tid)
            print("  task:", js.get("status"), json.dumps(js)[:300])
            if js.get("status") == "SUCCEEDED":
                url = (js.get("output") or [None])[0]
                if url:
                    urllib.request.urlretrieve(url, out)
                    print("  saved", out, os.path.getsize(out), "bytes")
                    ok.append(out); continue
            fail.append(out)
    print("OK:", ok); print("FAIL:", fail)
    if not ok and fail:
        sys.exit(1)

if __name__ == "__main__":
    main()
