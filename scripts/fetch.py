#!/usr/bin/env python3
"""Generic public-data fetcher. Config-driven, runs in GitHub Actions.

Why it exists: this sandbox cannot reach FRED/Eurostat/USDA/OWID directly, so all
fetching happens in Actions. Adding a new series should mean editing JSON, not
writing a new script.

Usage
  python scripts/fetch.py                 # fetch everything enabled in data-sources.json
  python scripts/fetch.py NAME [NAME...]  # fetch only these entries
  MODE=discover python scripts/fetch.py NAME
        -> do not parse; dump what the source actually returns (columns, dimension
           names, category codes) so a parser can be written against reality

Providers: fred | eurostat | owid | csv | yahoo | yahoo_valuation | evds | xlsx | fao | imf | worldbank
Every run writes data/_fetch-report.json recording what each source returned, so a
silent zero is visible instead of looking like a real answer.
"""
import calendar, csv, http.cookiejar, io, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, "data-sources.json")
UA = {"User-Agent": "namikakmandev-data/1.0 (github actions)"}
# Yahoo's gated endpoints reject the plain UA above; they want a browser string.
BROWSER_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")
MODE = os.environ.get("MODE", "").strip()
report = {}


def get(url, timeout=120):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


# ----------------------------------------------------------------- providers
def fred(entry):
    """Any FRED series -> {series_key: {YYYY-MM: value}}. Keyless CSV endpoint."""
    out = {}
    for key, sid in entry["series"].items():
        try:
            raw = get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}").decode()
        except Exception as ex:  # a bad id must not kill the source's other series
            out[key] = {"error": f"{sid}: {type(ex).__name__}: {ex}"}
            continue
        vals = {}
        for row in csv.DictReader(io.StringIO(raw)):
            date = (row.get("DATE") or row.get("observation_date") or "").strip()
            val = (row.get(sid) or "").strip()
            if len(date) >= 7 and val not in ("", "."):
                vals[date[:7]] = float(val)
        out[key] = vals
    return out


def _jsonstat(j):
    """JSON-stat 2.0 -> list of (dict_of_dimension_codes, value). Handles any shape."""
    ids = j["id"]
    sizes = j["size"]
    dims = j["dimension"]
    # position -> code, per dimension
    codes = []
    for d in ids:
        idx = dims[d]["category"]["index"]
        if isinstance(idx, dict):
            inv = {v: k for k, v in idx.items()}
            codes.append([inv[i] for i in range(len(inv))])
        else:  # already a list
            codes.append(list(idx))
    strides = [1] * len(sizes)
    for i in range(len(sizes) - 2, -1, -1):
        strides[i] = strides[i + 1] * sizes[i + 1]
    out = []
    for pos, val in (j.get("value") or {}).items():
        if val is None:
            continue
        p = int(pos)
        key = {}
        for i, d in enumerate(ids):
            key[d] = codes[i][(p // strides[i]) % sizes[i]]
        out.append((key, float(val)))
    return out


def eurostat(entry):
    """Any Eurostat dataset. entry['dataset'] + entry['params'] (dict).

    entry['api']='comext' switches to the Comext endpoint, which serves the
    DS-* datasets (international trade, PRODCOM) the statistics API does not.
    """
    host = ("https://ec.europa.eu/eurostat/api/comext/dissemination/statistics/1.0/data/"
            if entry.get("api") == "comext" else
            "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/")
    base = host + entry["dataset"] + "?format=JSON&lang=EN"
    qs = ""
    for k, v in entry.get("params", {}).items():
        for vi in (v if isinstance(v, list) else [v]):   # repeated params, e.g. several geos
            qs += f"&{k}={vi}"
    j = json.loads(get(base + qs).decode())
    if MODE == "discover":
        dims = {d: list(j["dimension"][d]["category"]["label"].items())[:250]
                for d in j["id"]}
        return {"_discover": {"dimension_ids": j["id"], "sizes": j["size"],
                              "categories": dims}}
    rows = _jsonstat(j)
    # series key: entry['group_dims'] joined with '|' (e.g. reporter|product),
    # else the geo dimension, else everything under 'ALL'
    gd = entry.get("group_dims") or (["geo"] if "geo" in j["id"] else [])
    out = defaultdict(dict)
    for key, val in rows:
        t = key.get("time")
        g = "|".join(key[d] for d in gd) if gd else "ALL"
        if t:
            out[g][t] = val
    return dict(out)


def owid(entry):
    """Any Our World in Data grapher slug. entry['slug'] + entry['entities'] map."""
    raw = get(f"https://ourworldindata.org/grapher/{entry['slug']}.csv"
              "?v=1&csvType=full&useColumnShortNames=true").decode()
    rdr = csv.DictReader(io.StringIO(raw))
    cols = rdr.fieldnames or []
    if MODE == "discover":
        rows = list(rdr)[:3]
        ents = sorted({r.get("entity") or r.get("Entity") or "" for r in csv.DictReader(
            io.StringIO(raw))})
        return {"_discover": {"columns": cols, "sample": rows,
                              "n_entities": len(ents), "entities_sample": ents[:60]}}
    ent_col = "entity" if "entity" in cols else "Entity"
    yr_col = "year" if "year" in cols else "Year"
    valcol = next(c for c in cols if c.lower() not in ("entity", "code", "year"))
    want = entry.get("entities") or {}
    out = defaultdict(dict)
    for row in rdr:
        name = (row.get(ent_col) or "").strip()
        key = want.get(name)
        if not key:
            continue
        try:
            out[key][int(row[yr_col])] = float(row[valcol])
        except (ValueError, TypeError, KeyError):
            continue
    return dict(out)


def csv_source(entry):
    """Any plain CSV. entry['url'] + optional 'filters' (col->value) and 'pivot'."""
    text = get(entry["url"]).decode("utf-8", "replace")
    rdr = csv.DictReader(io.StringIO(text))
    cols = rdr.fieldnames or []
    if MODE == "discover":
        rows = list(rdr)[:5]
        return {"_discover": {"columns": cols, "sample": rows}}
    filters = entry.get("filters", {})
    kcol, vcol = entry["key_col"], entry["value_col"]
    group = entry.get("group_col")
    out = defaultdict(dict)
    for row in rdr:
        if any((row.get(c) or "").strip() != v for c, v in filters.items()):
            continue
        try:
            g = (row.get(group) or "ALL").strip() if group else "ALL"
            out[g][row[kcol].strip()] = float(row[vcol])
        except (ValueError, TypeError, KeyError):
            continue
    return dict(out)


def yahoo(entry):
    """Yahoo Finance chart API -> {series_key: {YYYY-MM: adjusted close}}. Keyless JSON.

    entry['series'] maps output key -> yahoo symbol (e.g. 'LLY', '^GSPC').
    entry['interval']: 1d/1wk/1mo (default 1mo). Window: entry['start']
    (YYYY-MM-DD, sent as period1) or entry['range'] ('1y'...'max'). Prefer
    'start': with range=max Yahoo silently downgrades 1mo bars to quarterly
    once the span gets long (~40y+), which is invisible in a spot check.
    Uses adjclose (split- AND dividend-adjusted = total return); falls back to
    raw close for indices, which pay no dividends. Stooq was tried first but
    serves an anti-bot JS challenge to GitHub Actions IPs.
    """
    interval = entry.get("interval", "1mo")
    out = {}
    disc = {}
    for key, sym in entry["series"].items():
        if "start" in entry:
            p1 = calendar.timegm(time.strptime(entry["start"], "%Y-%m-%d"))
            window = f"period1={p1}&period2={int(time.time())}"
        else:
            window = f"range={entry.get('range', '10y')}"
        url = (f"https://query1.finance.yahoo.com/v8/finance/chart/"
               f"{urllib.parse.quote(sym)}?{window}&interval={interval}")
        j = json.loads(get(url).decode())
        r = ((j.get("chart") or {}).get("result") or [{}])[0]
        ind = r.get("indicators") or {}
        ts = r.get("timestamp") or []
        adj = ((ind.get("adjclose") or [{}])[0].get("adjclose")) or []
        raw = ((ind.get("quote") or [{}])[0].get("close")) or []
        if MODE == "discover":
            meta = r.get("meta") or {}
            disc[key] = {"symbol": sym, "result_keys": sorted(r.keys()),
                         "indicator_keys": sorted(ind.keys()),
                         "currency": meta.get("currency"),
                         "n_timestamps": len(ts), "n_adjclose": len(adj),
                         "first_ts": ts[:2], "last_ts": ts[-2:],
                         "error": (j.get("chart") or {}).get("error")}
            continue
        series = adj if any(v is not None for v in adj) else raw
        vals = {}
        for t, v in zip(ts, series):
            if v is None:
                continue
            vals[time.strftime("%Y-%m", time.gmtime(t))] = round(float(v), 4)
        out[key] = vals
    if MODE == "discover":
        return {"_discover": disc}
    return out


def _yahoo_session():
    """Yahoo gates quoteSummary behind a cookie+crumb pair. Get both, once.

    Actions runners share heavily-used IPs, so getcrumb often answers 429; retry
    with backoff and fall back to the query2 host before giving up.
    """
    jar = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    op.addheaders = [("User-Agent", BROWSER_UA), ("Accept", "*/*"),
                     ("Accept-Language", "en-US,en;q=0.9")]
    for seed in ("https://fc.yahoo.com", "https://finance.yahoo.com/quote/AAPL"):
        try:
            op.open(seed, timeout=30).read()
        except Exception:
            pass  # these may 404/403 — we only want the Set-Cookie they carry
    last = None
    for attempt in range(6):
        for host in ("query1", "query2"):
            try:
                c = op.open(f"https://{host}.finance.yahoo.com/v1/test/getcrumb",
                            timeout=30).read().decode().strip()
                if c and "<" not in c:
                    return op, c
                last = f"empty crumb from {host}"
            except Exception as ex:
                last = f"{type(ex).__name__}: {ex}"
        # Actions IPs get throttled in bursts; wait it out rather than hammering
        time.sleep(min(60, 5 * 2 ** attempt))
    raise RuntimeError(f"could not obtain Yahoo crumb after retries: {last}")


def _yahoo_probe():
    """Discovery: which access strategy actually works from this runner?

    Yahoo's fundamentals endpoints are gated and rate-limited differently per
    host and path; probe each and report, rather than guessing one and retrying.
    """
    out = {}
    jar = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    op.addheaders = [("User-Agent", BROWSER_UA), ("Accept", "*/*")]
    for seed in ("https://fc.yahoo.com", "https://finance.yahoo.com/quote/AAPL"):
        try:
            r = op.open(seed, timeout=30); r.read()
            out["seed " + seed] = f"HTTP {r.status}, cookies now={len(jar)}"
        except Exception as ex:
            out["seed " + seed] = f"{type(ex).__name__}: {ex} (cookies={len(jar)})"
    crumb = None
    for host in ("query1", "query2"):
        try:
            crumb = op.open(f"https://{host}.finance.yahoo.com/v1/test/getcrumb",
                            timeout=30).read().decode().strip()
            out[f"getcrumb {host}"] = f"OK crumb={crumb!r}"
        except Exception as ex:
            out[f"getcrumb {host}"] = f"{type(ex).__name__}: {ex}"
    # A screener endpoint would beat per-ticker calls outright: one request, every
    # US ticker, exactly the three columns this page needs. Probe it first.
    sa = ("https://stockanalysis.com/api/screener/s/f"
          "?m=marketCap&s=desc&c=no,s,n,marketCap,price,peRatio,peForward,pegRatio,"
          "epsGrowth5Y,epsThis,epsNext&cn=20&i=stocks")
    for label, u in (("stockanalysis screener", sa),
                     ("stockanalysis quote META",
                      "https://stockanalysis.com/api/symbol/s/meta/overview")):
        try:
            rq = urllib.request.Request(u, headers={"User-Agent": BROWSER_UA,
                                                    "Accept": "application/json"})
            body = urllib.request.urlopen(rq, timeout=45).read().decode()
            out[label] = f"OK {len(body)}B :: {body[:400]}"
        except Exception as ex:
            out[label] = f"{type(ex).__name__}: {ex}"
    tries = {
        "quoteSummary q1 +crumb": "https://query1.finance.yahoo.com/v10/finance/quoteSummary/AAPL?modules=defaultKeyStatistics&crumb=CRUMB",
        "quoteSummary q2 +crumb": "https://query2.finance.yahoo.com/v10/finance/quoteSummary/AAPL?modules=defaultKeyStatistics&crumb=CRUMB",
        "quoteSummary q1 no-crumb": "https://query1.finance.yahoo.com/v10/finance/quoteSummary/AAPL?modules=defaultKeyStatistics",
        "v7 quote +crumb": "https://query1.finance.yahoo.com/v7/finance/quote?symbols=AAPL&crumb=CRUMB",
        "chart api (control)": "https://query1.finance.yahoo.com/v8/finance/chart/AAPL?range=1mo&interval=1mo",
    }
    for label, url in tries.items():
        if "CRUMB" in url and not crumb:
            out[label] = "skipped — no crumb"
            continue
        u = url.replace("CRUMB", urllib.parse.quote(crumb or ""))
        try:
            body = op.open(u, timeout=45).read().decode()
            out[label] = f"OK {len(body)}B :: {body[:160]}"
        except Exception as ex:
            out[label] = f"{type(ex).__name__}: {ex}"
    return out


def yahoo_valuation(entry):
    """Valuation multiples per ticker -> {TICKER: {metric: value}}.

    entry['tickers']: list of Yahoo symbols. Pulls quoteSummary modules
    defaultKeyStatistics (trailing/forward EPS, pegRatio), summaryDetail
    (trailing/forward PE), financialData (price, growth), price (name), and
    earningsTrend (per-year consensus EPS + growth) so PEG can be COMPUTED —
    Yahoo's own pegRatio and the vendor ratio feeds are unreliable/negative.
    """
    if MODE == "discover":
        return {"_discover": {"probe": _yahoo_probe()}}
    op, crumb = _yahoo_session()
    mods = "defaultKeyStatistics,summaryDetail,financialData,price,earningsTrend"
    out, disc = {}, {}
    for n, sym in enumerate(entry["tickers"]):
        if n:
            time.sleep(1.5)  # pace the burst — Yahoo 429s Actions IPs readily
        url = ("https://query1.finance.yahoo.com/v10/finance/quoteSummary/"
               f"{urllib.parse.quote(sym)}?modules={mods}&crumb={urllib.parse.quote(crumb)}")
        j = None
        for attempt in range(3):
            try:
                j = json.loads(op.open(url, timeout=60).read().decode())
                break
            except Exception as ex:
                err = f"{type(ex).__name__}: {ex}"
                time.sleep(5 * 2 ** attempt)
        if j is None:
            out[sym] = {"error": err}
            continue
        res = ((j.get("quoteSummary") or {}).get("result") or [None])[0]
        if not res:
            out[sym] = {"error": "no result: " + json.dumps(j)[:200]}
            if MODE == "discover":
                disc[sym] = out[sym]
            continue
        if MODE == "discover":
            disc[sym] = {"modules": sorted(res.keys()),
                         "keystats_keys": sorted((res.get("defaultKeyStatistics") or {}).keys()),
                         "summary_keys": sorted((res.get("summaryDetail") or {}).keys()),
                         "trend_periods": [t.get("period") for t in
                                           (res.get("earningsTrend") or {}).get("trend", [])],
                         "sample": {k: _raw((res.get("defaultKeyStatistics") or {}).get(k))
                                    for k in ("trailingEps", "forwardEps", "pegRatio")}}
            continue
        ks, sd = res.get("defaultKeyStatistics") or {}, res.get("summaryDetail") or {}
        fd, pr = res.get("financialData") or {}, res.get("price") or {}
        rec = {
            "name": pr.get("longName") or pr.get("shortName") or sym,
            "price": _raw(fd.get("currentPrice")) or _raw(pr.get("regularMarketPrice")),
            "market_cap": _raw(pr.get("marketCap")),
            "trailing_eps": _raw(ks.get("trailingEps")),
            "forward_eps": _raw(ks.get("forwardEps")),
            "trailing_pe": _raw(sd.get("trailingPE")),
            "forward_pe": _raw(sd.get("forwardPE")),
            "yahoo_peg": _raw(ks.get("pegRatio")),
            "earnings_growth": _raw(fd.get("earningsGrowth")),
            "revenue_growth": _raw(fd.get("revenueGrowth")),
            "profit_margin": _raw(fd.get("profitMargins")),
        }
        # consensus EPS by horizon, for a PEG we compute ourselves
        for t in (res.get("earningsTrend") or {}).get("trend", []):
            p = t.get("period")
            if p in ("0q", "+1q", "0y", "+1y", "+5y"):
                rec["eps_" + p] = _raw((t.get("earningsEstimate") or {}).get("avg"))
                rec["growth_" + p] = _raw(t.get("growth"))
        out[sym] = rec
    if MODE == "discover":
        return {"_discover": disc}
    return out


def _raw(v):
    """Yahoo wraps numbers as {'raw':x,'fmt':...}; unwrap, tolerate plain/None."""
    if isinstance(v, dict):
        return v.get("raw")
    return v if isinstance(v, (int, float)) else None


def geojson_filter(entry):
    """Download a GeoJSON, keep features whose `prop` is in `keep`, round
    coordinates to `precision` decimals. Returns {"_geojson": subset} which
    run() writes verbatim (not a time series)."""
    j = json.loads(get(entry["url"]).decode("utf-8", "replace"))
    prop = entry["prop"]
    keep = set(entry["keep"])
    prec = entry.get("precision", 2)
    if MODE == "discover":
        sample = j["features"][0]["properties"]
        return {"_discover": {"n_features": len(j["features"]),
                              "property_keys": sorted(sample.keys()),
                              "sample_props": {k: sample[k] for k in list(sample)[:20]}}}

    def rnd(c):
        if isinstance(c, (int, float)):
            return round(c, prec)
        return [rnd(x) for x in c]

    feats = []
    for f in j["features"]:
        code = f["properties"].get(prop)
        if code in keep:
            feats.append({"type": "Feature",
                          "properties": {"iso2": code,
                                         "name": f["properties"].get("NAME", code)},
                          "geometry": {"type": f["geometry"]["type"],
                                       "coordinates": rnd(f["geometry"]["coordinates"])}})
    missing = sorted(keep - {f["properties"]["iso2"] for f in feats})
    return {"_geojson": {"type": "FeatureCollection", "features": feats},
            "_missing": missing}



def _evds_date(t):
    """EVDS 'Tarih' -> YYYY, YYYY-MM or YYYY-MM-DD."""
    m = re.match(r"^(\d{4})-(\d{1,2})$", t)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}"
    m = re.match(r"^(\d{2})-(\d{2})-(\d{4})$", t)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    if re.match(r"^\d{4}$", t):
        return t
    m = re.match(r"^(\d{4})-Q(\d)$", t)
    if m:
        return t
    return None


def evds(entry):
    """TCMB EVDS (Central Bank of Türkiye). entry['series'] {key: code}.
    Optional: 'start' (dd-mm-yyyy, default 01-01-1990); 'frequency' as EVDS codes
    (1 daily, 3 weekly, 5 monthly, 6 quarterly, 8 annual); 'aggregation'
    (avg|last|first|sum|max|min) applied to every series when resampling.
    Needs EVDS_KEY in the environment. Uses the evds3 endpoint the evds
    Python package targets; the older evds2 service path now serves the web app."""
    key = os.environ.get("EVDS_KEY", "").strip()
    if not key:
        raise RuntimeError("EVDS_KEY not set")
    codes = list(entry["series"].values())
    params = {"series": "-".join(codes),
              "startDate": entry.get("start", "01-01-1990"),
              "endDate": time.strftime("%d-%m-%Y", time.gmtime()),
              "type": "json"}
    if entry.get("frequency"):
        params["frequency"] = str(entry["frequency"])
    if entry.get("aggregation"):
        params["aggregationTypes"] = "-".join([entry["aggregation"]] * len(codes))
    url = "https://evds3.tcmb.gov.tr/igmevdsms-dis/" + "&".join(f"{k}={v}" for k, v in params.items())
    req = urllib.request.Request(url, headers={**UA, "key": key})
    with urllib.request.urlopen(req, timeout=120) as r:
        raw = r.read().decode("utf-8", "replace")
    if raw.lstrip().startswith("<"):
        raise RuntimeError("EVDS returned HTML instead of JSON: key rejected or endpoint moved")
    items = json.loads(raw).get("items", [])
    if MODE == "discover":
        # Also probe the catalogue endpoints, whose parameter rules are undocumented,
        # so the MCP server's search can be pointed at the variant that answers.
        base = "https://evds3.tcmb.gov.tr/igmevdsms-dis/"
        # No '?' before the parameters: EVDS routes on the path, as the data endpoint does.
        probes = {
            "categories": (base + "categories/type=json", True),
            "datagroups_all": (base + "datagroups/mode=0&code=&type=json", True),
            "datagroups_tufe": (base + "datagroups/mode=2&code=bie_fiyattufe&type=json", True),
            "serieList_tufe": (base + "serieList/type=json&code=bie_fiyattufe", True),
        }
        catalogue = {}
        for name, (purl, header) in probes.items():
            try:
                preq = urllib.request.Request(purl, headers={**UA, **({"key": key} if header else {})})
                with urllib.request.urlopen(preq, timeout=60) as r:
                    body = r.read().decode("utf-8", "replace")
                catalogue[name] = {"status": 200, "head": body[:400]}
            except urllib.error.HTTPError as ex:
                catalogue[name] = {"status": ex.code, "head": ex.read().decode("utf-8", "replace")[:400]}
            except Exception as ex:
                catalogue[name] = {"error": f"{type(ex).__name__}: {ex}"}
        return {"_discover": {"url": url, "n_items": len(items), "sample": items[:3],
                              "keys": sorted({k for it in items for k in it}),
                              "catalogue": catalogue}}
    out = defaultdict(dict)
    for it in items:
        t = _evds_date(str(it.get("Tarih", "")))
        if not t:
            continue
        for k, code in entry["series"].items():
            v = it.get(code.replace(".", "_"))
            if v in (None, "", "null"):
                continue
            try:
                out[k][t] = float(v)
            except (TypeError, ValueError):
                continue
    return dict(out)


def _fao_token():
    """FAOSTAT needs a JWT since 2025: a free developer account, POST /auth/login."""
    tok = os.environ.get("FAOSTAT_API_TOKEN", "").strip()
    if tok:
        return tok
    user, pw = os.environ.get("FAOSTAT_USER", "").strip(), os.environ.get("FAOSTAT_PASSWORD", "").strip()
    if not (user and pw):
        raise RuntimeError("FAOSTAT needs FAOSTAT_USER and FAOSTAT_PASSWORD (free account at "
                           "www.fao.org/faostat/en/#developer-portal) as repository secrets")
    body = urllib.parse.urlencode({"username": user, "password": pw}).encode()
    req = urllib.request.Request("https://faostatservices.fao.org/api/v1/auth/login", data=body,
                                 headers={**UA, "Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=60) as r:
        j = json.loads(r.read().decode("utf-8", "replace"))
    tok = (j.get("AuthenticationResult") or {}).get("AccessToken")
    if not tok:
        raise RuntimeError("FAOSTAT login returned no AccessToken")
    return tok


def fao(entry):
    """FAOSTAT JSON API (developer account required). entry['domain'] (QCL, PP, TCL, ...),
    entry['areas'] {key: area_code}, entry['items'] {key: item_code}, entry['element']
    code (or 'elements' {key: code}). Series keys: item key, prefixed 'area|' when several
    areas, suffixed '|element' when several elements. Optional 'year' as '2000:2024'."""
    areas = entry.get("areas") or {"turkey": "223"}
    items = entry["items"]
    elements = entry.get("elements") or {"value": entry["element"]}
    params = {"area": ",".join(areas.values()), "item": ",".join(items.values()),
              "element": ",".join(elements.values()), "show_codes": "true", "show_unit": "true",
              "show_flags": "false", "null_values": "false", "output_type": "objects"}
    if entry.get("year"):
        m = re.match(r"^(\d{4}):(\d{4})$", entry["year"])
        params["year"] = ",".join(str(y) for y in range(int(m.group(1)), int(m.group(2)) + 1)) if m else entry["year"]
    # The API answers nothing to some element filters even when the code is right, so the
    # element is not sent; rows are kept by 'Element Code' below.
    params.pop("element", None)
    url = f"https://faostatservices.fao.org/api/v1/en/data/{entry['domain']}?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={**UA, "Authorization": "Bearer " + _fao_token()})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            raw = json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as ex:
        raise RuntimeError(f"FAOSTAT HTTP {ex.code}: {ex.read().decode('utf-8', 'replace')[:300]}")
    rows = raw.get("data") or []
    if MODE == "discover":
        return {"_discover": {"url": url, "n_rows": len(rows), "sample": rows[:3],
                              "keys": sorted({k for r in rows for k in r})}}
    inv_area = {v: k for k, v in areas.items()}
    inv_item = {v: k for k, v in items.items()}
    inv_el = {v: k for k, v in elements.items()}
    months = {f"70{m:02d}": f"{m:02d}" for m in range(1, 13)}
    out = defaultdict(dict)
    for r in rows:
        a = inv_area.get(str(r.get("Area Code")))
        it = inv_item.get(str(r.get("Item Code")))
        el = inv_el.get(str(r.get("Element Code")))
        if a is None or it is None or el is None:
            continue
        y = str(r.get("Year") or "")
        if not re.match(r"^\d{4}$", y):
            continue
        mc = str(r.get("Months Code") or "")
        t = f"{y}-{months[mc]}" if mc in months else y   # 7021 and the like mark annual values
        key = it
        if len(areas) > 1:
            key = f"{a}|{key}"
        if len(elements) > 1:
            key = f"{key}|{el}"
        try:
            out[key][t] = float(r.get("Value"))
        except (TypeError, ValueError):
            continue
    return dict(out)


def worldbank(entry):
    """World Bank indicators API (keyless JSON). entry['countries'] {key: ISO3},
    entry['indicators'] {key: WB code}, optional 'start' year and 'scale' {indicator_key:
    multiplier}. Series keys are country|indicator."""
    countries = entry["countries"]
    inv = {v: k for k, v in countries.items()}
    start = entry.get("start", 1960)
    scale = entry.get("scale", {})
    out = defaultdict(dict)
    # Thirty countries and sixty-five years in one request times out often enough to lose
    # whole indicators, so countries go in chunks and each chunk gets a second attempt.
    iso = list(countries.values())
    chunks = [iso[i:i + 10] for i in range(0, len(iso), 10)] or [[]]
    for ikey, code in entry["indicators"].items():
        rows, failures = [], []
        for chunk in chunks:
            url = (f"https://api.worldbank.org/v2/country/{';'.join(chunk)}/indicator/{code}"
                   f"?format=json&per_page=20000&date={start}:{time.gmtime().tm_year}")
            for attempt in (1, 2):
                try:
                    j = json.loads(get(url).decode("utf-8", "replace"))
                    rows.extend(j[1] if isinstance(j, list) and len(j) > 1 and j[1] else [])
                    break
                except Exception as ex:
                    if attempt == 2:
                        failures.append(f"{'+'.join(chunk)}: {type(ex).__name__}: {ex}")
                    else:
                        time.sleep(5)
            if MODE == "discover":
                return {"_discover": {"url": url, "n_rows": len(rows), "sample": rows[:3]}}
        if failures:
            out[f"_error|{ikey}"] = {"error": f"{code}: " + "; ".join(failures)}
        for r in rows:
            v = r.get("value")
            iso = r.get("countryiso3code") or (r.get("country") or {}).get("id")
            ckey = inv.get(iso)
            if v is None or ckey is None:
                continue
            out[f"{ckey}|{ikey}"][str(r["date"])] = float(v) * scale.get(ikey, 1)
    return dict(out)


def imf(entry):
    """IMF Data (SDMX 3.0, keyless). entry['agency'] (IMF.RES, IMF.STA), entry['dataflow']
    (WEO, CPI, ...), entry['key'] as in the portal's API tab with '+' lists and '*' wildcards,
    optional 'version' (default latest). Series keys join the dimension values that vary,
    with '|'; entry['rename'] {dimension_value: key} relabels values (e.g. TUR -> TR)."""
    version = entry.get("version", "+")
    url = (f"https://api.imf.org/external/sdmx/3.0/data/dataflow/{entry['agency']}/"
           f"{entry['dataflow']}/{urllib.parse.quote(version, safe='')}/{entry['key']}")
    req = urllib.request.Request(url, headers={**UA, "Accept": "text/csv"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            text = r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as ex:
        raise RuntimeError(f"IMF HTTP {ex.code}: {ex.read().decode('utf-8', 'replace')[:300]}")
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        raise RuntimeError("IMF returned an empty body")
    header = rows[0]
    if MODE == "discover":
        return {"_discover": {"url": url, "columns": header, "n_rows": len(rows) - 1, "sample": rows[1:4]}}
    try:
        a, t, v = header.index("ACTION"), header.index("TIME_PERIOD"), header.index("OBS_VALUE")
    except ValueError:
        raise RuntimeError(f"unexpected IMF CSV columns: {header[:10]}")
    dims = list(range(a + 1, t))
    body = [r for r in rows[1:] if len(r) > v]
    varying = [i for i in dims if len({r[i] for r in body}) > 1]
    rename = entry.get("rename", {})
    out = defaultdict(dict)
    for r in body:
        try:
            val = float(r[v])
        except ValueError:
            continue
        per = r[t].strip()
        m = re.match(r"^(\d{4})-?(Q[1-4]|M\d{2})?$", per)
        if not m:
            continue
        period = m.group(1) + (("-" + m.group(2)) if m.group(2) and m.group(2).startswith("Q") else
                               ("-" + m.group(2)[1:]) if m.group(2) else "")
        key = "|".join(rename.get(r[i], r[i]) for i in varying) or "value"
        out[key][period] = val
    return dict(out)


def xlsx(entry):
    """An Excel workbook with one code row and a date in the first column, such as
    the World Bank Pink Sheet. entry['url'], or entry['page'] + 'match' (a regex for
    the file link on a landing page, for files whose URL changes each release) with
    optional 'fallback_url'. 'sheet' (name, default first), 'columns' {key: CODE},
    'code_row_contains' (a cell that identifies the code row), 'date_re' (groups
    joined with '-', default YYYYMmm)."""
    import openpyxl  # installed in the workflow, not needed elsewhere
    url = entry.get("url")
    if not url:
        try:
            html = get(entry["page"]).decode("utf-8", "replace")
            m = re.search(entry["match"], html)
            if not m:
                raise RuntimeError(f"no link matching {entry['match']} on {entry['page']}")
            url = m.group(0)
            if url.startswith("/"):
                url = urllib.parse.urljoin(entry["page"], url)
        except Exception as ex:
            if not entry.get("fallback_url"):
                raise
            print(f"[warn] landing page failed ({type(ex).__name__}: {ex}); using fallback_url")
            url = entry["fallback_url"]
    wb = openpyxl.load_workbook(io.BytesIO(get(url)), read_only=True, data_only=True)
    ws = wb[entry["sheet"]] if entry.get("sheet") else wb.worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    if MODE == "discover":
        return {"_discover": {"url": url, "sheets": wb.sheetnames, "n_rows": len(rows),
                              "first_rows": [list(r[:14]) for r in rows[:10]]}}
    # The header row is found by one of its cells. Cells are matched after dropping
    # footnote asterisks and stray spaces ('Coal, South African **'); a column that has
    # no exact match falls back to the first header containing it ('Meat, beef' for 'beef').
    norm = lambda c: re.sub(r"[\s*]+", " ", str(c)).strip().upper()
    marker = norm(entry.get("code_row_contains", "Crude oil, average"))
    start_row = next((i for i, r in enumerate(rows) if any(norm(c) == marker for c in r if c is not None)), None)
    if start_row is None:
        sample = [[c for c in r[:8]] for r in rows[:8]]
        raise RuntimeError(f"no row containing {marker!r} in sheet {ws.title}; first rows: {sample}")
    # The Pink Sheet's index sheet spreads its headers down a staircase of rows, one per
    # level of the grouping, so 'code_row_span' merges that many rows into one header,
    # taking the first non-blank cell in each column.
    span = int(entry.get("code_row_span", 1))
    if span > 1:
        block = rows[start_row:start_row + span]
        width = max((len(r) for r in block), default=0)
        code_row = []
        for col in range(width):
            val = None
            for r in block:
                c = r[col] if col < len(r) else None
                if c is not None and str(c).strip():
                    val = c
                    break
            code_row.append(val)
    else:
        code_row = rows[start_row]
    headers = [(norm(c), i) for i, c in enumerate(code_row) if c is not None]
    idx = {}
    for k, want in entry["columns"].items():
        w = norm(want)
        hit = next((i for h, i in headers if h == w), None)
        if hit is None:
            hit = next((i for h, i in headers if w in h), None)
        if hit is not None:
            idx[want] = hit
    missing = [c for c in entry["columns"].values() if c not in idx]
    if missing:
        print(f"[warn] {entry['name']}: columns not in header row: {missing}; headers: {[h for h, _ in headers]}")
    date_re = re.compile(entry.get("date_re", r"^(\d{4})M(\d{2})$"))
    out = defaultdict(dict)
    for r in rows:
        if not r or r[0] is None:
            continue
        m = date_re.match(str(r[0]).strip())
        if not m:
            continue
        t = "-".join(m.groups())
        for k, code in entry["columns"].items():
            i = idx.get(code)
            if i is None or i >= len(r):
                continue
            v = r[i]
            if isinstance(v, (int, float)):
                out[k][t] = float(v)
    return dict(out)

PROVIDERS = {"fred": fred, "eurostat": eurostat, "owid": owid, "csv": csv_source,
             "yahoo": yahoo, "yahoo_valuation": yahoo_valuation,
             "geojson_filter": geojson_filter, "evds": evds, "xlsx": xlsx, "fao": fao, "imf": imf, "worldbank": worldbank}


# ----------------------------------------------------------------- runner
def run(entry):
    name = entry["name"]
    fn = PROVIDERS[entry["provider"]]
    data = fn(entry)
    if "_discover" in data:
        report[name] = {"mode": "discover", **data["_discover"]}
        print(json.dumps(data["_discover"], indent=1, default=str)[:24000])
        return
    if "_geojson" in data:
        out_path = os.path.join(ROOT, entry["out"])
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        json.dump(data["_geojson"], open(out_path, "w"), separators=(",", ":"))
        report[name] = {"ok": True, "n_features": len(data["_geojson"]["features"]),
                        "missing_codes": data["_missing"]}
        print(f"[ok]   {name}: {len(data['_geojson']['features'])} features; "
              f"missing {data['_missing']}")
        return
    errs = {k: v["error"] for k, v in data.items() if isinstance(v, dict) and "error" in v}
    # An error belongs in the report, not in the published file: a '_error|reserves' key
    # sitting where thirty country series used to be reads as data to everything
    # downstream. Drop them, then put last month's values back for whatever failed, so a
    # timeout costs freshness rather than the series itself.
    data = {k: v for k, v in data.items() if k not in errs}
    out_path = os.path.join(ROOT, entry["out"])
    carried = []
    if errs and os.path.exists(out_path):
        try:
            prev = json.load(open(out_path)).get("series") or {}
        except Exception:  # noqa: BLE001 — an unreadable previous file is not fatal
            prev = {}
        for k, v in prev.items():
            if k.startswith("_error|") or k in data or not isinstance(v, dict) or not v:
                continue
            data[k] = v
            carried.append(k)
        carried.sort()
    counts = {k: len(v) for k, v in data.items()}
    empty = [k for k, n in counts.items() if n == 0]
    # span is only meaningful for time-keyed series; a per-ticker metric dict is not one
    dated = all(re.match(r"^\d{4}(-\d{2})?$", str(t)) for v in data.values() for t in v)
    report[name] = {"ok": bool(data) and not empty and not errs, "counts": counts,
                    "empty_keys": empty,
                    "errors": errs,
                    "carried_over": carried,
                    "span": ({k: [min(v), max(v)] for k, v in data.items() if v}
                             if dated else "n/a (not a time series)")}
    if carried:
        print(f"[WARN] {name}: kept {len(carried)} series from the previous file because this fetch failed for them")
    if not data or empty:
        print(f"[WARN] {name}: empty series {empty or 'all'}")
    else:
        print(f"[ok]   {name}: " + ", ".join(f"{k}={n}" for k, n in counts.items()))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    json.dump({"source": entry.get("source", entry["provider"]),
               "fetched_by": "scripts/fetch.py",
               "fetched_at": time.strftime("%Y-%m-%d", time.gmtime()),
               "config": {k: entry[k] for k in entry if k not in ("out",)},
               "series": data},
              open(out_path, "w"), separators=(",", ":"))


def main():
    cfg = json.load(open(CONFIG))
    only = set(sys.argv[1:])
    entries = [e for e in cfg["sources"]
               if e.get("enabled", True) and (not only or e["name"] in only)]
    if not entries:
        sys.exit(f"no matching sources (asked for {only or 'all'})")
    failed = []
    for e in entries:
        try:
            run(e)
        except Exception as ex:  # noqa: BLE001 — one bad source must not stop the rest
            report[e["name"]] = {"ok": False, "error": f"{type(ex).__name__}: {ex}"}
            print(f"[FAIL] {e['name']}: {type(ex).__name__}: {ex}")
            failed.append(e["name"])
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    json.dump(report, open(os.path.join(ROOT, "data", "_fetch-report.json"), "w"), indent=1)
    print("\n" + json.dumps(report, indent=1, default=str)[:3000])
    degraded = sorted(n for n, r in report.items() if isinstance(r, dict) and r.get("ok") is False)
    if failed:
        print(f"\n{len(failed)} source(s) failed: {failed}")
    if degraded:
        # Everything written so far still gets committed: the later workflow steps run on
        # always(). Exiting non-zero is what turns the run red, so a source that quietly
        # loses an indicator stops passing for green.
        print(f"\n{len(degraded)} source(s) came back degraded: {degraded}")
        sys.exit(1)


if __name__ == "__main__":
    main()
