#!/usr/bin/env python3
"""Collect nine vintages of OECD-FAO Agricultural Outlook projections.

Every year the OECD and FAO publish a ten-year projection of world
agricultural prices and production. Nobody goes back and marks them. This
collects the projections so they can be marked.

OECD still serves its retired editions at stats.oecd.org, one dataset per
edition, HIGH_AGLINK_2015 through HIGH_AGLINK_2023. Each contains that
edition's history AND its forward projection, which is exactly what a
forecast scorecard needs: the 2015 edition's view of 2022, and the 2023
edition's record of what 2022 turned out to be.

Two coding schemes, established by scripts/probe_oecd_fao.py:

  2015-2019  COUNTRY  . COMMODITY . VARIABLE            world = WLD, price = XP
  2020       LOCATION . COMMODITY . VARIABLE            (COUNTRY renamed only)
  2021-2023  REF_AREA . FREQ . COMMODITY . MEASURE      world = W,   price = WP
             . UNIT_MEASURE . VERSION_ID                units pinned to USD_T

COMMODITY was recoded to CPC at the same time, so the two schemes are bridged
by name below. Coarse grains is deliberately absent: the old scheme's single
CG has no clean counterpart once the new scheme splits maize out of it, and a
mapping that needs a caveat is not a mapping.

Two traps this had to be rewritten around, both found the hard way.

The legacy endpoint IGNORES the dimension filter in the URL. Asking for
WLD.WT.XP returns the same ~55MB whole-database response as all/all does. A
first version issued 198 filtered requests, downloaded roughly ten gigabytes,
kept every series it was handed and produced an 833MB file that GitHub
refused. So each edition is fetched ONCE and filtered in memory, which is nine
requests instead of 198 and a file measured in kilobytes.

Observation keys index the TIME_PERIOD array in the order the API returns it,
which is NOT sorted — the probe read 1970..1979 then 1990. Sorting it first
silently mislabels every year.

Usage:  python3 scripts/fetch_oecd_fao.py [--out data/oecd-fao-vintages.json]
"""
import argparse, gzip, io, json, os, sys, time, urllib.error, urllib.request, zlib
from datetime import date

BASE = "https://stats.oecd.org/SDMX-JSON/data"
UA = "namikakmandev-data/1.0 (+https://namikakmandev.github.io)"
TIMEOUT = 240
EDITIONS = list(range(2015, 2024))

# old code -> (new code, plain name). Bridged by name from the probe dumps.
COMMODITIES = {
    "WT":  ("CPC_0111",       "Wheat"),
    "RI":  ("CPC_0113",       "Rice"),
    "BV":  ("CPC_EX_BV",      "Beef and veal"),
    "PK":  ("CPC_EX_PK",      "Pigmeat"),
    "PT":  ("CPC_EX_PT",      "Poultry meat"),
    "SH":  ("CPC_EX_SH",      "Sheepmeat"),
    "BT":  ("CPC_2224",       "Butter"),
    "SMP": ("CPC_EX_222121",  "Skim milk powder"),
    "WMP": ("CPC_22211",      "Whole milk powder"),
    "CH":  ("CPC_2225",       "Cheese"),
    "DDG": ("CPC_EX_DDG",     "Distillers dry grains"),
}
# old measure -> (new measure, new unit, plain name)
MEASURES = {
    "XP": ("WP", "USD_T", "World price"),
    "QP": ("QP", "T",     "Production"),
}


def fetch(url, tries=3):
    """GET with decompression and a couple of retries. -> bytes or None."""
    for attempt in range(tries):
        req = urllib.request.Request(url, headers={
            "User-Agent": UA, "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate"})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                raw = r.read()
                enc = (r.headers.get("Content-Encoding") or "").lower()
                if "gzip" in enc:
                    raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
                elif "deflate" in enc:
                    raw = zlib.decompress(raw, -zlib.MAX_WBITS)
                return raw
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if attempt == tries - 1:
                return None
        except Exception:                                    # noqa: BLE001
            if attempt == tries - 1:
                return None
        time.sleep(2 * (attempt + 1))
    return None


def series_from(body):
    """-> [(dimension code tuple, {year: value})]. Time order left untouched."""
    j = json.loads(body)
    data = j.get("data", j)
    st = (data.get("structures") or [data.get("structure", {})])[0]
    dims = st.get("dimensions", {})
    ser_dims = dims.get("series", [])
    # the API's own order — sorting this is what mislabels every observation
    years = [v.get("id") for d in dims.get("observation", [])
             for v in d.get("values", [])]
    ds = (data.get("dataSets") or [{}])[0]
    out = []
    for key, sv in (ds.get("series") or {}).items():
        idx = [int(i) for i in key.split(":")]
        codes = tuple(
            (ser_dims[p]["values"][i]["id"]
             if p < len(ser_dims) and i < len(ser_dims[p].get("values", []))
             else None)
            for p, i in enumerate(idx))
        obs = {}
        for i, val in (sv.get("observations") or {}).items():
            pos = int(i)
            if pos >= len(years):
                continue
            v = val[0] if isinstance(val, list) else val
            if v is not None:
                obs[int(years[pos])] = v
        if obs:
            out.append((codes, obs))
    return out


def wanted_series(body, vintage):
    """Pull just the series this study needs out of a whole-database response.

    Layout-agnostic on purpose. SDMX-JSON can put TIME_PERIOD in the series key
    or in the observation key, and can hand back either a `series` map or a flat
    `observations` map, and this archive does not do the same thing for every
    edition: 2021 and 2022 parsed cleanly while the other seven yielded exactly
    one observation each — the signature of reading a time list that does not
    describe the keys actually present.

    So instead of assuming, the series and observation dimensions are
    concatenated in order and every key is resolved against that combined list.
    Whichever slot TIME_PERIOD occupies, it is found by name.

    Returns ([(commodity_old, measure_old, {year: value})], diagnostics).
    """
    j = json.loads(body)
    data = j.get("data", j)
    structs = data.get("structures") or ([data["structure"]]
                                         if "structure" in data else [])
    ds = (data.get("dataSets") or [{}])[0]
    st = structs[ds.get("structure", 0)] if structs else {}
    dims = st.get("dimensions", {})
    ser_dims = dims.get("series", []) or []
    obs_dims = dims.get("observation", []) or []
    combined = list(ser_dims) + list(obs_dims)

    diag = {"n_structures": len(structs),
            "series_dims": [(d.get("id"), len(d.get("values", [])))
                            for d in ser_dims],
            "obs_dims": [(d.get("id"), len(d.get("values", [])))
                         for d in obs_dims],
            "has_series_map": bool(ds.get("series")),
            "has_flat_obs": bool(ds.get("observations"))}

    pos = {d.get("id"): i for i, d in enumerate(combined)}
    codes_at = [[v.get("id") for v in d.get("values", [])] for d in combined]
    names_at = [[(v.get("name") or "") for v in d.get("values", [])]
                for d in combined]

    new = vintage >= 2021
    area_dim = next((k for k in ("REF_AREA", "LOCATION", "COUNTRY")
                     if k in pos), None)
    meas_dim = "MEASURE" if "MEASURE" in pos else "VARIABLE"
    time_dim = next((k for k in pos if "TIME" in k.upper()), None)
    diag.update(area_dim=area_dim, meas_dim=meas_dim, time_dim=time_dim)
    if not area_dim or meas_dim not in pos or "COMMODITY" not in pos \
            or not time_dim:
        diag["fatal"] = f"missing a dimension; have {list(pos)}"
        return [], diag

    ai, ci, mi, ti = pos[area_dim], pos["COMMODITY"], pos[meas_dim], pos[time_dim]
    ui = pos.get("UNIT_MEASURE")

    world = {k for k, nm in enumerate(names_at[ai])
             if nm.strip().lower() == "world"}
    if not world:
        world = {k for k, c in enumerate(codes_at[ai]) if c in ("WLD", "W")}
    want_c = {k: old for old, (newc, _) in COMMODITIES.items()
              for k, c in enumerate(codes_at[ci])
              if c == (newc if new else old)}
    want_m = {k: old for old, (newm, _, _) in MEASURES.items()
              for k, c in enumerate(codes_at[mi])
              if c == (newm if new else old)}
    want_u = ({old: {k for k, c in enumerate(codes_at[ui])
                     if c == MEASURES[old][1]} for old in MEASURES}
              if (new and ui is not None) else None)
    diag.update(n_world=len(world), n_commodity_hits=len(want_c),
                n_measure_hits=len(want_m), n_time_values=len(codes_at[ti]))

    def keys():
        """Yield (full index list, value) for either layout."""
        if ds.get("series"):
            for skey, sv in ds["series"].items():
                sidx = [int(x) for x in skey.split(":")]
                for okey, val in (sv.get("observations") or {}).items():
                    yield sidx + [int(x) for x in okey.split(":")], val
        else:
            for okey, val in (ds.get("observations") or {}).items():
                yield [int(x) for x in okey.split(":")], val

    acc, seen, dropped = {}, 0, 0
    for idx, val in keys():
        seen += 1
        if len(idx) != len(combined):
            dropped += 1
            continue
        if idx[ai] not in world or idx[ci] not in want_c or idx[mi] not in want_m:
            continue
        old_c, old_m = want_c[idx[ci]], want_m[idx[mi]]
        if want_u is not None and idx[ui] not in want_u[old_m]:
            continue
        v = val[0] if isinstance(val, list) else val
        if v is None:
            continue
        year = codes_at[ti][idx[ti]]
        acc.setdefault((old_c, old_m), {})[int(year)] = v
    diag.update(keys_seen=seen, keys_wrong_width=dropped,
                matched_series=len(acc))
    return [(c, m, o) for (c, m), o in acc.items()], diag


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="data/oecd-fao-vintages.json")
    args = ap.parse_args(argv)

    print("OECD-FAO Agricultural Outlook — collecting vintages")
    print("  one request per edition; the URL filter is ignored by this API,")
    print("  so selection happens in memory\n")
    rows, misses, diags = [], [], {}
    for vintage in EDITIONS:
        ds = f"HIGH_AGLINK_{vintage}"
        body = fetch(f"{BASE}/{ds}/all/all")
        if not body:
            misses.append({"vintage": vintage, "error": "no response"})
            print(f"  {ds}: NO RESPONSE")
            continue
        try:
            ser, diag = wanted_series(body, vintage)
            diags[vintage] = diag
            err = diag.get("fatal")
        except Exception as e:                               # noqa: BLE001
            misses.append({"vintage": vintage, "error": str(e)[:160]})
            print(f"  {ds}: parse failed — {type(e).__name__}")
            continue
        finally:
            del body
        if err:
            misses.append({"vintage": vintage, "error": err})
        for old_c, old_m, obs in ser:
            rows.append({
                "vintage": vintage,
                "commodity": old_c,
                "commodity_name": COMMODITIES[old_c][1],
                "measure": old_m,
                "measure_name": MEASURES[old_m][2],
                "obs": {str(y): round(v, 4) for y, v in sorted(obs.items())},
            })
        got = sum(len(o) for _, _, o in ser)
        dg = diags.get(vintage, {})
        print(f"  {ds}: {len(ser):>3} series, {got:>6,} obs  |  "
              f"keys={dg.get('keys_seen', 0):>8,} "
              f"time_vals={dg.get('n_time_values')} "
              f"dims={[i for i, _ in dg.get('series_dims', [])]}"
              f"+{[i for i, _ in dg.get('obs_dims', [])]}")

    doc = {
        "source": "OECD-FAO Agricultural Outlook, retired editions",
        "source_url": "https://stats.oecd.org",
        "note": ("One dataset per edition (HIGH_AGLINK_YYYY). Each holds that "
                 "edition's history and its ten-year projection, so a vintage's "
                 "forecast can be scored against a later vintage's record."),
        "fetched_by": "scripts/fetch_oecd_fao.py",
        "fetched_at": date.today().isoformat(),
        "schemes": {"2015-2019": "COUNTRY.COMMODITY.VARIABLE (WLD, XP)",
                    "2020": "LOCATION.COMMODITY.VARIABLE (WLD, XP)",
                    "2021-2023": ("REF_AREA.FREQ.COMMODITY.MEASURE."
                                  "UNIT_MEASURE.VERSION_ID (W, WP, USD_T)")},
        "commodity_map": {k: {"new": v[0], "name": v[1]}
                          for k, v in COMMODITIES.items()},
        "excluded": ("Coarse grains: the old scheme's single CG has no clean "
                     "counterpart once the new scheme splits maize out."),
        "n_series": len(rows), "n_misses": len(misses),
        "diagnostics": diags,
        "misses": misses[:60],
        "series": rows,
    }
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as fh:
        json.dump(doc, fh, separators=(",", ":"))
    size = os.path.getsize(args.out)
    print(f"\n  {len(rows):,} series, {len(misses)} misses")
    print(f"  wrote {args.out} ({size:,} bytes)")
    if size > 20_000_000:
        # the first version produced 833MB and was rejected at push time, after
        # a 31-minute run. Fail here instead, where the reason is visible.
        print("  ERROR: output far larger than expected — selection is wrong")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
