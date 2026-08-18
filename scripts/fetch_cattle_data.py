#!/usr/bin/env python3
"""Fetch cattle vs feed price series for the cattle-parity story.

Runs inside GitHub Actions (open internet). Writes JSON files under data/:
  data/cattle-us.json  — FRED monthly PPIs since 1926: slaughter cattle (WPU0131)
                         and corn (WPU012202) + parity ratio (cattle/corn, indexed)
  data/cattle-eu.json  — EU young-bull R3 carcass price (weekly -> monthly avg)
                         and EU feed maize price, from the EC agrifood API (best effort)

Each source is independent: a failure in one does not block the others.
"""
import csv, io, json, re, sys, urllib.parse, urllib.request
from collections import defaultdict

UA = {"User-Agent": "namikakmandev-cattle-story/1.0 (github actions)"}

def get(url, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def fred_series(series_id):
    """FRED keyless CSV endpoint -> {YYYY-MM: value}"""
    raw = get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}").decode()
    out = {}
    for row in csv.DictReader(io.StringIO(raw)):
        date = (row.get("DATE") or row.get("observation_date") or "").strip()
        val = (row.get(series_id) or "").strip()
        if len(date) >= 7 and val not in ("", "."):
            out[date[:7]] = float(val)
    return out

def build_us():
    cattle = fred_series("WPU0131")     # PPI slaughter cattle, monthly, 1926->
    corn = fred_series("WPU012202")     # PPI corn, monthly
    months = sorted(set(cattle) & set(corn))
    rows = [[m, round(cattle[m], 2), round(corn[m], 2),
             round(cattle[m] / corn[m], 4)] for m in months]
    return {
        "source": "FRED/BLS producer price indexes: WPU0131 (slaughter cattle), WPU012202 (corn)",
        "columns": ["month", "cattle_ppi", "corn_ppi", "parity_cattle_over_corn"],
        "rows": rows,
    }

def _agrifood_monthly(url):
    """EC agrifood weekly records -> {YYYY-MM: monthly mean}. Tolerant field parsing."""
    recs = json.loads(get(url).decode())
    monthly = defaultdict(list)
    for rec in recs:
        d = rec.get("beginDate") or rec.get("referencePeriod") or ""
        p = rec.get("price") or rec.get("unitPrice")
        if not d or p is None:
            continue
        if isinstance(p, str):
            p = p.replace("€", "").replace(".", "").replace(",", ".").strip()
        try:
            p = float(p)
        except ValueError:
            continue
        dd = d.split("/")
        if len(dd) == 3:
            monthly[f"{dd[2]}-{dd[1]}"].append(p)
    return {m: sum(v) / len(v) for m, v in monthly.items()}

def build_eu():
    # Young bulls R3 carcass price. API returns a 100x-scaled figure; normalise to EUR/100kg
    # (sanity anchor: EU young-bull R3 was ~EUR320/100kg in 2010).
    beef = _agrifood_monthly(
        "https://www.ec.europa.eu/agrifood/api/beef/prices"
        "?memberStateCodes=EU&categories=young%20bulls&qualities=R3"
        "&beginDate=01/01/2010&endDate=31/12/2026")
    if not beef:
        raise RuntimeError("EU beef API returned no parsable rows")
    scale = 100 if sum(beef.values()) / len(beef) > 3000 else 1
    beef = {m: v / scale for m, v in beef.items()}
    # Feed grain, member states averaged as EU proxy. The portal's parameter names vary
    # between dataset versions — probe several shapes and keep whichever yields data.
    feed = {}
    probes = [
        "https://www.ec.europa.eu/agrifood/api/cereal/prices?productCodes=MAI&beginDate=01/01/2010&endDate=31/12/2026",
        "https://www.ec.europa.eu/agrifood/api/cereal/prices?productCodes=ORG&beginDate=01/01/2010&endDate=31/12/2026",
        "https://www.ec.europa.eu/agrifood/api/cereal/prices?products=Feed%20maize&beginDate=01/01/2010&endDate=31/12/2026",
        "https://www.ec.europa.eu/agrifood/api/cereal/prices?productNames=Feed%20maize&beginDate=01/01/2010&endDate=31/12/2026",
        "https://www.ec.europa.eu/agrifood/api/cereal/prices?beginDate=01/01/2010&endDate=31/12/2026",
    ]
    for url in probes:
        try:
            feed = _agrifood_monthly(url)
        except Exception as e:
            print("[eu feed] probe failed:", url.split('?')[1][:40], repr(e))
            feed = {}
        if feed:
            print("[eu feed] probe OK:", url.split('?')[1][:60], "months:", len(feed))
            fscale = 100 if sum(feed.values()) / len(feed) > 2000 else 1
            feed = {m: v / fscale for m, v in feed.items()}
            break
    months = sorted(set(beef) & set(feed)) if feed else sorted(beef)
    rows = []
    for m in months:
        b = round(beef[m], 2)
        f = round(feed[m], 2) if feed else None
        rows.append([m, b, f, round(b / f, 4) if f else None])
    return {
        "source": "EC agri-food data portal: young bulls R3 EU avg (EUR/100kg) + feed grain MS avg (EUR/t), monthly means of weekly quotes",
        "columns": ["month", "beef_r3_eur_100kg", "feed_eur_t", "parity_beef_over_feed"],
        "rows": rows,
    }

def build_tr_discovery():
    """Dump the FULL series catalog of agriculture/PPI-flavoured EVDS datagroups.

    Keyword-hunting across all of EVDS proved noisy; instead we list every series
    of every datagroup whose name mentions agriculture/producer prices, and pick
    the cattle & feed codes from the catalog by eye.
    """
    import os
    key = os.environ.get("EVDS_KEY", "").strip()
    if not key:
        raise RuntimeError("EVDS_KEY not set — skipping TR discovery")
    from evds import evdsAPI
    api = evdsAPI(key)
    # WIDE=1: anahtar kelime filtresi yok — tüm katalog taranır (mısır avı)
    wide = os.environ.get("WIDE", "").strip() == "1"
    want = ("tarım", "tarim", "üretici fiyat", "uretici fiyat", "üfe", "ufe",
            "fiyat", "emtia", "toptan")
    catalog = []
    mains = api.main_categories
    for _, mrow in mains.iterrows():
        try:
            subs = api.get_sub_categories(mrow["CATEGORY_ID"])
        except Exception:
            continue
        for _, srow in subs.iterrows():
            gname = str(srow.get("DATAGROUP_NAME", ""))
            if not wide and not any(k in gname.lower() for k in want):
                continue
            code = srow.get("DATAGROUP_CODE")
            try:
                series = api.get_series(code)
            except Exception as e:
                catalog.append({"group": gname, "error": repr(e)})
                continue
            catalog.append({
                "group": gname, "group_code": str(code),
                "series": [{"code": row.get("SERIE_CODE"), "name": str(row.get("SERIE_NAME", ""))}
                           for _, row in series.iterrows()],
            })
    if not catalog:
        raise RuntimeError("no agriculture/PPI datagroups found")
    return {"source": "TCMB EVDS catalog dump: datagroups matching tarım/üretici fiyat/ÜFE",
            "groups": catalog}

def build_tr():
    """TR monthly PPIs from TCMB EVDS: meat products (T17) vs prepared animal feeds (T25).

    Same Yİ-ÜFE family the broiler story used (C10.91 feeds), so TR methodology
    matches the US index-ratio approach one-to-one.
    """
    import os
    key = os.environ.get("EVDS_KEY", "").strip()
    if not key:
        raise RuntimeError("EVDS_KEY not set")
    from evds import evdsAPI
    api = evdsAPI(key)
    codes = ["TP.TUFE1YI.T17", "TP.TUFE1YI.T25"]
    df = api.get_data(codes, startdate="01-01-2010", enddate="31-12-2026")
    cm, cf = [c.replace(".", "_") for c in codes]
    rows = []
    for _, r in df.iterrows():
        t = str(r.get("Tarih", ""))
        m_, f_ = r.get(cm), r.get(cf)
        if m_ is None or f_ is None or str(m_) == "nan" or str(f_) == "nan":
            continue
        parts = t.replace("/", "-").split("-")
        if len(parts) < 2:
            continue
        ym = f"{parts[0]}-{int(parts[1]):02d}"
        rows.append([ym, round(float(m_), 2), round(float(f_), 2),
                     round(float(m_) / float(f_), 4)])
    if not rows:
        raise RuntimeError("EVDS returned no rows for T17/T25")
    return {
        "source": "TCMB EVDS / TÜİK Yİ-ÜFE: TP.TUFE1YI.T17 (korunmuş et ve et ürünleri), TP.TUFE1YI.T25 (hazır hayvan yemleri)",
        "columns": ["month", "meat_ppi", "feed_ppi", "parity_meat_over_feed"],
        "rows": rows,
    }

def _walk(obj, want_keys):
    """Yield every dict in a nested JSON blob that carries all of want_keys (case-insensitive).

    The CBS and GASTAT payload shapes are undocumented and have changed between
    versions, so we search for the shape we need instead of asserting a key path.
    """
    if isinstance(obj, dict):
        low = {k.lower(): k for k in obj}
        if all(any(w in lk for lk in low) for w in want_keys):
            yield obj
        for v in obj.values():
            yield from _walk(v, want_keys)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk(v, want_keys)


def _pick(d, *fragments):
    """First value in d whose key contains any fragment. None if nothing matches."""
    for k, v in d.items():
        if any(f in k.lower() for f in fragments):
            return v
    return None


def _num(v, depth=0):
    """Coerce to float, digging through wrapper dicts.

    CBS nests the figure one level down (currBase: {value: ...}) and the wrapper key
    varies by index, so unwrap rather than assert a path.
    """
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v.replace(",", "").strip())
        except ValueError:
            return None
    if isinstance(v, dict) and depth < 3:
        for frag in ("value", "index", "curr", "price"):
            hit = _pick(v, frag)
            if hit is not None:
                n = _num(hit, depth + 1)
                if n is not None:
                    return n
        for sub in v.values():
            n = _num(sub, depth + 1)
            if n is not None:
                return n
    return None


def _il_resolve(catalog_json, keywords, exclude=()):
    """Find a CBS index code by matching its English name. Returns (code, name)."""
    best = None
    for rec in _walk(catalog_json, ("name",)):
        name = str(_pick(rec, "name") or "")
        low = name.lower()
        if not all(k in low for k in keywords) or any(x in low for x in exclude):
            continue
        code = _pick(rec, "code", "id")
        if code is None:
            continue
        # prefer the shortest matching name: the parent index, not a sub-item
        if best is None or len(name) < len(best[1]):
            best = (str(code), name)
    return best


def _il_series(code):
    """CBS price API -> {YYYY-MM: value}. Tolerant of the payload's exact shape."""
    url = ("https://api.cbs.gov.il/index/data/price?id=" + urllib.parse.quote(str(code))
           + "&format=json&download=false&startPeriod=01-2005")
    j = json.loads(get(url).decode())
    out = {}
    for rec in _walk(j, ("year", "month")):
        y, m = _pick(rec, "year"), _pick(rec, "month")
        v = _num(_pick(rec, "currbase", "value", "index"))
        if y is None or m is None or v is None:
            continue
        try:
            ym = f"{int(y):04d}-{int(m):02d}"
        except (TypeError, ValueError):
            continue
        out[ym] = v
    return out


def build_il():
    """Israel: CBS agricultural OUTPUT price index / agricultural INPUT fodder index.

    Same object as the TR series — an output PPI over an input PPI from one national
    office, monthly. The CBS index ids are not documented, so they are resolved from
    the catalog by name at run time; pin them with IL_OUTPUT_ID / IL_FODDER_ID once
    a run has printed them.
    """
    import os
    out_id, out_name = os.environ.get("IL_OUTPUT_ID", "").strip(), "pinned via IL_OUTPUT_ID"
    fod_id, fod_name = os.environ.get("IL_FODDER_ID", "").strip(), "pinned via IL_FODDER_ID"
    if not (out_id and fod_id):
        cat = json.loads(get("https://api.cbs.gov.il/index/catalog/catalog"
                             "?lang=en&format=json&download=false").decode())
        if not out_id:
            hit = _il_resolve(cat, ("agricultur", "output"))
            if not hit:
                raise RuntimeError("CBS catalog: no agricultural output price index found")
            out_id, out_name = hit
        if not fod_id:
            hit = _il_resolve(cat, ("fodder",)) or _il_resolve(cat, ("agricultur", "input"))
            if not hit:
                raise RuntimeError("CBS catalog: no fodder / agricultural input index found")
            fod_id, fod_name = hit
    print(f"[il] output id={out_id} ({out_name}) | fodder id={fod_id} ({fod_name})")
    meat, feed = _il_series(out_id), _il_series(fod_id)
    months = sorted(set(meat) & set(feed))
    if not months:
        raise RuntimeError(f"CBS returned no overlapping months (output={len(meat)}, fodder={len(feed)})")
    rows = [[m, round(meat[m], 2), round(feed[m], 2), round(meat[m] / feed[m], 4)]
            for m in months]
    return {
        "source": f"Israel CBS: agricultural output price index (id {out_id}) / "
                  f"agricultural input price index, fodder (id {fod_id})",
        "columns": ["month", "output_idx", "fodder_idx", "parity_output_over_fodder"],
        "rows": rows,
    }


def build_sa():
    """Saudi Arabia: GASTAT Wholesale Price Index — live animals / cereals divisions.

    CAVEAT THAT MUST TRAVEL WITH EVERY NUMBER: Saudi feed is almost entirely imported
    and sat under a subsidy regime restructured in the mid-2010s. This ratio is
    domestic meat price over imported feed cost, not the domestic grain cycle the
    US/EU/TR series measure. Never plot it on the same axis unlabelled.

    No machine-readable GASTAT endpoint is documented, so this probes candidates and
    accepts a human-supplied CSV via SA_WPI_CSV. It raises rather than returning an
    empty region — a silent zero would read as "Saudi has no parity", which is a
    different claim from "we could not fetch it".
    """
    import os
    csv_url = os.environ.get("SA_WPI_CSV", "").strip()
    probes = ([csv_url] if csv_url else []) + [
        "https://open.data.gov.sa/data/api/v1/datasets?q=wholesale%20price%20index",
        "https://datasaudi.sa/en/api/indicators?search=wholesale%20price%20index",
    ]
    meat_kw = ("live animal", "animal product", "livestock")
    feed_kw = ("cereal", "grain", "barley", "agricultur")
    meat, feed, src = {}, {}, ""
    for url in probes:
        try:
            raw = get(url).decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001 — try the next shape
            print("[sa] probe failed:", url[:70], repr(e))
            continue
        if raw.lstrip()[:1] in "{[":
            try:
                j = json.loads(raw)
            except ValueError:
                continue
            for rec in _walk(j, ("name",)):
                nm = str(_pick(rec, "name") or "").lower()
                per, val = _pick(rec, "period", "date", "month"), _pick(rec, "value", "index")
                if per is None or val is None:
                    continue
                ym = str(per)[:7].replace("/", "-")
                if not re.match(r"^\d{4}-\d{2}$", ym):
                    continue
                val = _num(val)
                if val is None:
                    continue
                if any(k in nm for k in meat_kw):
                    meat[ym] = val
                elif any(k in nm for k in feed_kw):
                    feed[ym] = val
        else:  # CSV: month,series,value
            for row in csv.DictReader(io.StringIO(raw)):
                low = {k.lower().strip(): (v or "").strip() for k, v in row.items() if k}
                ym = (low.get("month") or low.get("period") or low.get("date") or "")[:7]
                nm = (low.get("series") or low.get("name") or low.get("division") or "").lower()
                try:
                    val = float(low.get("value") or low.get("index") or "")
                except ValueError:
                    continue
                if not re.match(r"^\d{4}-\d{2}$", ym):
                    continue
                if any(k in nm for k in meat_kw):
                    meat[ym] = val
                elif any(k in nm for k in feed_kw):
                    feed[ym] = val
        if meat and feed:
            src = url
            print(f"[sa] probe OK: {url[:70]} | meat={len(meat)} feed={len(feed)}")
            break
    months = sorted(set(meat) & set(feed))
    if not months:
        raise RuntimeError(
            "GASTAT WPI not machine-readable from any probed endpoint. If the WPI is "
            "bulletins-only, Saudi cannot join the panel — set SA_WPI_CSV to a CSV of "
            "month,series,value if someone extracts one.")
    rows = [[m, round(meat[m], 2), round(feed[m], 2), round(meat[m] / feed[m], 4)]
            for m in months]
    return {
        "source": f"Saudi GASTAT Wholesale Price Index (2014=100) via {src}: "
                  "live animals & animal products / cereals",
        "caveat": "IMPORTED FEED — feed is not domestically priced and sat under a "
                  "subsidy regime restructured mid-2010s. Not comparable to the "
                  "US/EU/TR grain-cycle ratio; label it wherever it is shown.",
        "columns": ["month", "meat_idx", "feed_idx", "parity_meat_over_feed"],
        "rows": rows,
    }


def build_merged():
    """Apples-to-apples file: per region, meat & feed indexed to 2015=100 + parity index."""
    def load(path):
        with open(path) as f:
            return json.load(f)
    def rebase(series):  # {m: v} -> 2015=100
        base = [v for m, v in series.items() if m.startswith("2015") and v]
        if not base:
            return {}
        b = sum(base) / len(base)
        return {m: round(v / b * 100, 2) for m, v in series.items() if v}
    out = {"base": "2015=100", "regions": {}}
    us = load("data/cattle-us.json")["rows"]
    meat = rebase({r[0]: r[1] for r in us if r[0] >= "2010"})
    feed = rebase({r[0]: r[2] for r in us if r[0] >= "2010"})
    out["regions"]["US"] = {
        "source": "FRED/BLS PPIs (slaughter cattle, corn)",
        "columns": ["month", "meat_idx", "feed_idx", "parity_idx"],
        "rows": [[m, meat[m], feed[m], round(meat[m] / feed[m], 4)]
                 for m in sorted(set(meat) & set(feed))]}
    eu = load("data/cattle-eu.json")["rows"]
    meat = rebase({r[0]: r[1] for r in eu})
    feed = rebase({r[0]: r[2] for r in eu if r[2]})
    if feed:
        out["regions"]["EU"] = {
            "source": "EC agrifood: young bull R3 carcass, feed grain",
            "columns": ["month", "meat_idx", "feed_idx", "parity_idx"],
            "rows": [[m, meat[m], feed[m], round(meat[m] / feed[m], 4)]
                     for m in sorted(set(meat) & set(feed))]}
    try:
        tr = load("data/cattle-tr.json")["rows"]
        meat = rebase({r[0]: r[1] for r in tr})
        feed = rebase({r[0]: r[2] for r in tr})
        if meat and feed:
            out["regions"]["TR"] = {
                "source": "TÜİK Yİ-ÜFE via EVDS: meat products, prepared animal feeds",
                "columns": ["month", "meat_idx", "feed_idx", "parity_idx"],
                "rows": [[m, meat[m], feed[m], round(meat[m] / feed[m], 4)]
                         for m in sorted(set(meat) & set(feed))]}
    except FileNotFoundError:
        pass
    # Israel and Saudi Arabia join on exactly the terms the other three did: rebased
    # to their own base-year mean, so only changes are compared, never levels.
    for code, path, label in [("IL", "data/cattle-il.json", "Israel CBS: agri output / fodder input"),
                              ("SA", "data/cattle-sa.json", "Saudi GASTAT WPI: live animals / cereals")]:
        try:
            raw = load(path)
        except FileNotFoundError:
            continue
        meat = rebase({r[0]: r[1] for r in raw["rows"]})
        feed = rebase({r[0]: r[2] for r in raw["rows"]})
        months = sorted(set(meat) & set(feed))
        if not months:
            # rebase() needs base-year months; without them the region would vanish
            # silently and the chart would just show four lines instead of five.
            print(f"[WARN] {code}: no base-year overlap, region not merged")
            continue
        block = {"source": label,
                 "columns": ["month", "meat_idx", "feed_idx", "parity_idx"],
                 "rows": [[m, meat[m], feed[m], round(meat[m] / feed[m], 4)] for m in months]}
        if raw.get("caveat"):
            block["caveat"] = raw["caveat"]
        out["regions"][code] = block
    with open("data/cattle-parity.json", "w") as f:
        json.dump(out, f, separators=(",", ":"))
    return out

def build_corn():
    """Sağlamlık testi verisi: her bölgede payda = MISIR.

    US: cattle-us.json zaten sığır/mısır (kopyalanır).
    EU: R3 karkas ÷ yemlik mısır (cereal API, productCodes=MAI — açıkça mısır).
    TR: et ürünleri ÜFE ÷ EVDS mısır serisi (CORN_TR_CODE env ile verilir;
        kod keşif modunda katalogdan bulunur)."""
    import os
    out = {"note": "denominator = maize/corn everywhere (robustness check)", "regions": {}}
    us = json.load(open("data/cattle-us.json"))["rows"]
    out["regions"]["US"] = {
        "source": "FRED/BLS: WPU0131 / WPU012202 (corn)",
        "columns": ["month", "meat", "corn", "parity"],
        "rows": [[m, c, k, round(c / k, 4)] for m, c, k, _ in us]}
    beef = _agrifood_monthly(
        "https://www.ec.europa.eu/agrifood/api/beef/prices"
        "?memberStateCodes=EU&categories=young%20bulls&qualities=R3"
        "&beginDate=01/01/2010&endDate=31/12/2026")
    scale = 100 if sum(beef.values()) / len(beef) > 3000 else 1
    beef = {m: v / scale for m, v in beef.items()}
    mai = _agrifood_monthly(
        "https://www.ec.europa.eu/agrifood/api/cereal/prices"
        "?productCodes=MAI&beginDate=01/01/2010&endDate=31/12/2026")
    ms = 100 if mai and sum(mai.values()) / len(mai) > 2000 else 1
    mai = {m: v / ms for m, v in mai.items()}
    months = sorted(set(beef) & set(mai))
    out["regions"]["EU"] = {
        "source": "EC agrifood: R3 carcass EUR/100kg / feed maize EUR/t (productCodes=MAI)",
        "columns": ["month", "meat", "corn", "parity"],
        "rows": [[m, round(beef[m], 2), round(mai[m], 2), round(beef[m] / mai[m], 4)]
                 for m in months]}
    code = os.environ.get("CORN_TR_CODE", "").strip()
    if code:
        key = os.environ.get("EVDS_KEY", "").strip()
        from evds import evdsAPI
        api = evdsAPI(key)
        codes = ["TP.TUFE1YI.T17", code]
        df = api.get_data(codes, startdate="01-01-2010", enddate="31-12-2026")
        cm, cc = [c.replace(".", "_") for c in codes]
        rows = []
        for _, r in df.iterrows():
            t = str(r.get("Tarih", ""))
            m_, c_ = r.get(cm), r.get(cc)
            if m_ is None or c_ is None or str(m_) == "nan" or str(c_) == "nan":
                continue
            parts = t.replace("/", "-").split("-")
            if len(parts) < 2:
                continue
            ym = f"{parts[0]}-{int(parts[1]):02d}"
            rows.append([ym, round(float(m_), 2), round(float(c_), 2),
                         round(float(m_) / float(c_), 4)])
        if rows:
            out["regions"]["TR"] = {
                "source": f"EVDS: TP.TUFE1YI.T17 / {code} (mısır)",
                "columns": ["month", "meat", "corn", "parity"],
                "rows": rows}
    with open("data/corn-parity.json", "w") as f:
        json.dump(out, f, separators=(",", ":"))
    return out

def main():
    import os
    mode = os.environ.get("MODE", "").strip()
    if mode == "discover":
        cat = build_tr_discovery()
        for g in cat["groups"]:
            for s in g.get("series", []):
                nm = s.get("name", "").lower()
                if any(k in nm for k in ("mısır", "misir", "maize", "corn")):
                    print("CORN-CANDIDATE:", s.get("code"), "|", s.get("name"), "| group:", g.get("group"))
        print("discovery done,", len(cat["groups"]), "groups scanned")
        return
    if mode == "corn":
        obj = build_corn()
        print("OK corn-parity regions:", ",".join(obj["regions"]),
              "| rows:", {k: len(v["rows"]) for k, v in obj["regions"].items()})
        return
    ok, fail = [], []
    for name, fn in [("data/cattle-us.json", build_us),
                     ("data/cattle-eu.json", build_eu),
                     ("data/cattle-tr.json", build_tr),
                     ("data/cattle-il.json", build_il),
                     ("data/cattle-sa.json", build_sa)]:
        try:
            obj = fn()
            with open(name, "w") as f:
                json.dump(obj, f, separators=(",", ":"))
            ok.append(f"{name} ({len(obj['rows'])} rows)")
        except Exception as e:  # noqa: BLE001 — report and continue
            fail.append(f"{name}: {type(e).__name__}: {e}")
    try:
        merged = build_merged()
        ok.append("data/cattle-parity.json (regions: " + ",".join(merged["regions"]) + ")")
    except Exception as e:  # noqa: BLE001
        fail.append(f"data/cattle-parity.json: {type(e).__name__}: {e}")
    print("OK:", "; ".join(ok) or "none")
    print("FAILED:", "; ".join(fail) or "none")
    if not ok:
        sys.exit(1)

if __name__ == "__main__":
    main()
