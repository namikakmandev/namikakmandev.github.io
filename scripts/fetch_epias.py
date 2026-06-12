# Refreshes assets/epias-live.json: last ~2 years of real Turkish national
# hourly electricity consumption (EPIAS Transparency 2.0) + matching hourly
# temperature (Open-Meteo, Ist/Ank/Izm blend 50/30/20).
# Credentials come from env vars EPIAS_USERNAME / EPIAS_PASSWORD (repo secrets).
import json, os, re, sys, datetime, urllib.request, urllib.parse, urllib.error

CAS_URL = "https://giris.epias.com.tr/cas/v1/tickets"
DATA_URL = "https://seffaflik.epias.com.tr/electricity-service/v1/consumption/data/realtime-consumption"
OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "epias-live.json")
CITIES = [(41.01, 28.98, 0.5), (39.93, 32.86, 0.3), (38.42, 27.14, 0.2)]
DAYS = 730

def http(req):
    return urllib.request.urlopen(req, timeout=120)

def get_tgt(user, pwd):
    body = urllib.parse.urlencode({"username": user, "password": pwd}).encode()
    req = urllib.request.Request(CAS_URL, data=body, headers={
        "Content-Type": "application/x-www-form-urlencoded", "Accept": "text/plain"})
    try:
        r = http(req)
    except urllib.error.HTTPError as e:
        sys.exit(f"EPIAS login failed: HTTP {e.code} — check EPIAS_USERNAME/EPIAS_PASSWORD secrets")
    loc = r.headers.get("Location", "")
    text = r.read().decode("utf-8", "ignore")
    m = re.search(r"TGT-[^\s\"'/]+", loc) or re.search(r"TGT-[^\s\"'/]+", text)
    if not m:
        sys.exit("EPIAS login: no TGT found in response")
    return m.group(0)

def fetch_consumption(tgt, start, end):
    # chunked POSTs; returns {local-hour-key: MWh}
    out = {}
    cur = start
    while cur < end:
        nxt = min(cur + datetime.timedelta(days=60), end)
        body = json.dumps({
            "startDate": cur.strftime("%Y-%m-%dT%H:%M:%S+03:00"),
            "endDate": nxt.strftime("%Y-%m-%dT23:00:00+03:00"),
        }).encode()
        req = urllib.request.Request(DATA_URL, data=body, headers={
            "Content-Type": "application/json", "TGT": tgt})
        j = json.load(http(req))
        for it in j.get("items", []):
            k = it["date"][:13] + ":00"          # 2026-06-12T14:00
            v = it.get("consumption")
            if v is not None:
                out[k.replace("T", "T")] = float(v)
        cur = nxt + datetime.timedelta(days=1)
        cur = cur.replace(hour=0)
    return out

def fetch_weather(start, end):
    blend = {}
    for lat, lon, w in CITIES:
        per_city = {}
        # archive (reliable, ~5 days behind)
        url = (f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}"
               f"&start_date={start.date()}&end_date={end.date()}"
               f"&hourly=temperature_2m&timezone=Europe%2FIstanbul")
        j = json.load(http(urllib.request.Request(url)))
        for t, v in zip(j["hourly"]["time"], j["hourly"]["temperature_2m"]):
            if v is not None:
                per_city[t] = v
        # recent tail (archive lag) from the forecast endpoint's past days
        url2 = (f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
                f"&hourly=temperature_2m&past_days=14&forecast_days=1&timezone=Europe%2FIstanbul")
        j2 = json.load(http(urllib.request.Request(url2)))
        for t, v in zip(j2["hourly"]["time"], j2["hourly"]["temperature_2m"]):
            if v is not None and t not in per_city:
                per_city[t] = v
        for t, v in per_city.items():
            blend[t] = blend.get(t, 0.0) + w * v
    return blend

def main():
    user, pwd = os.environ.get("EPIAS_USERNAME"), os.environ.get("EPIAS_PASSWORD")
    if not user or not pwd:
        sys.exit("EPIAS_USERNAME / EPIAS_PASSWORD env vars missing")
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3)))
    end = now.replace(minute=0, second=0, microsecond=0, tzinfo=None) - datetime.timedelta(hours=3)
    start = (end - datetime.timedelta(days=DAYS)).replace(hour=0)
    tgt = get_tgt(user, pwd)
    load = fetch_consumption(tgt, start, end)
    print(f"consumption hours: {len(load)}")
    if len(load) < 24 * 365:
        sys.exit("too little consumption data — aborting, keeping previous file")
    temp = fetch_weather(start, end)
    print(f"weather hours: {len(temp)}")
    # continuous series over hours where BOTH exist; trim ragged tail
    hours = []
    t = start
    while t <= end:
        hours.append(t)
        t += datetime.timedelta(hours=1)
    keys = [h.strftime("%Y-%m-%dT%H:00") for h in hours]
    last_ok = max(i for i, k in enumerate(keys) if k in load and k in temp)
    keys = keys[:last_ok + 1]
    miss_l = miss_t = 0
    loads, temps, prev_l, prev_t = [], [], None, 15.0
    for k in keys:
        v = load.get(k)
        if v is None:
            v = prev_l; miss_l += 1
        prev_l = v
        w = temp.get(k)
        if w is None:
            w = prev_t; miss_t += 1
        prev_t = w
        loads.append(int(round(v)))
        temps.append(round(w, 1))
    print(f"series: {len(keys)} hours ({keys[0]} -> {keys[-1]}), filled load {miss_l}, temp {miss_t}")
    if miss_l > len(keys) * 0.05:
        sys.exit("too many consumption gaps — aborting")
    out = {
        "start": keys[0],
        "src": "EPİAŞ gerçek zamanlı tüketim · Open-Meteo (İst/Ank/İzm 50/30/20)",
        "updated": now.strftime("%Y-%m-%d %H:%M+03:00"),
        "load": loads,
        "temp": temps,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print(f"wrote {OUT} ({os.path.getsize(OUT)//1024} KB)")

if __name__ == "__main__":
    main()
