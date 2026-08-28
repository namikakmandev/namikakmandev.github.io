#!/usr/bin/env python3
"""Discovery probe for the OECD-FAO Agricultural Outlook — round 4.

Established so far:
  - the retired editions HIGH_AGLINK_2015..2023 are all still served
  - responses are gzipped, and detail=nodata returns the dimension structure
  - the 2015 edition is COUNTRY x COMMODITY x VARIABLE over 1970-2024
  - the 2023 edition is REF_AREA x COMMODITY x MEASURE x UNIT_MEASURE over
    1990-2032, with W = World and WP = World price
  - so OECD renamed the coding somewhere in between: WT became CPC_0111,
    VARIABLE became MEASURE

That renaming is the one thing standing between here and the study, because a
projection can only be scored against an outcome carrying the same code. Round
4 settles it, per edition, and proves the archive returns real numbers rather
than the zeros the first truncated round appeared to show.

For each edition it:
  1. reads the dimension structure and keeps the FULL code lists
  2. picks codes by matching names, not by assuming ids — wheat, world,
     a price measure — so it works under either coding scheme
  3. issues one narrow data query built from those codes and prints the
     values that come back, with their years

Runs in GitHub Actions; the dev sandbox cannot reach OECD.

  python3 scripts/probe_oecd_fao.py     # -> data/_oecd-fao-probe.json
"""
import gzip, io, json, os, sys, urllib.error, urllib.request, zlib
from datetime import datetime, timezone

TIMEOUT = 300
MAX_BYTES = 120_000_000
UA = "namikakmandev-data-probe/4.0 (+https://namikakmandev.github.io)"
LEGACY = "https://stats.oecd.org"
EDITIONS = [f"HIGH_AGLINK_{y}" for y in range(2015, 2024)]
FULL_CODES_FOR = {"HIGH_AGLINK_2015", "HIGH_AGLINK_2023"}


def get(url, note=""):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "*/*", "Accept-Encoding": "gzip, deflate"})
    rec = {"url": url}
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            raw = r.read(MAX_BYTES)
            enc = (r.headers.get("Content-Encoding") or "").lower()
            rec["truncated"] = len(raw) >= MAX_BYTES
            if "gzip" in enc:
                raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
            elif "deflate" in enc:
                raw = zlib.decompress(raw, -zlib.MAX_WBITS)
            rec.update(status=r.status, bytes=len(raw))
            rec["_body"] = raw
    except urllib.error.HTTPError as e:
        rec.update(status=e.code, error=f"HTTPError {e.code}")
    except Exception as e:                                   # noqa: BLE001
        rec.update(status=None, error=f"{type(e).__name__}: {e}")
    print(f"    {str(rec.get('status')):>5} {rec.get('bytes', 0):>12,}b  {note}")
    return rec


def structure_of(body):
    """-> (ordered series dimensions with full code lists, time values)."""
    j = json.loads(body)
    data = j.get("data", j)
    st = (data.get("structures") or [data.get("structure", {})])[0]
    dd = st.get("dimensions", {})
    series = [{"id": d.get("id"), "name": d.get("name"),
               "codes": [{"id": v.get("id"), "name": v.get("name")}
                         for v in d.get("values", [])]}
              for d in dd.get("series", [])]
    times = [v.get("id") for d in dd.get("observation", [])
             for v in d.get("values", [])]
    return series, sorted(times), data


def pick(codes, *wanted, exclude=()):
    """First code whose name contains all `wanted` words. Names, not ids."""
    for c in codes:
        nm = (c.get("name") or "").lower()
        if all(w in nm for w in wanted) and not any(x in nm for x in exclude):
            return c
    return None


def main():
    print("OECD-FAO Agricultural Outlook — discovery probe, round 4")
    print("  per edition: coding scheme, full code lists, and real numbers\n")
    out = {"probed_at": datetime.now(timezone.utc).isoformat(),
           "probed_by": "scripts/probe_oecd_fao.py (round 4)",
           "established": {
               "archive": "HIGH_AGLINK_2015..2023 all served, gzipped",
               "2015_scheme": "COUNTRY x COMMODITY x VARIABLE, 1970-2024",
               "2023_scheme": ("REF_AREA x COMMODITY x MEASURE x UNIT_MEASURE, "
                               "1990-2032, W=World, WP=World price"),
               "question": ("where does the coding change, and do the editions "
                            "return real values")},
           "editions": {}}

    for ed in EDITIONS:
        print(f"  {ed}")
        rec = {}
        r = get(f"{LEGACY}/SDMX-JSON/data/{ed}/all/all?detail=nodata",
                f"{ed} structure")
        body = r.pop("_body", None)
        rec["structure_status"] = r.get("status")
        rec["structure_error"] = r.get("error")
        if not body:
            out["editions"][ed] = rec
            print()
            continue
        try:
            series, times, _ = structure_of(body)
        except Exception as e:                               # noqa: BLE001
            rec["structure_parse_error"] = f"{type(e).__name__}: {e}"
            out["editions"][ed] = rec
            print()
            continue

        rec["dimension_order"] = [d["id"] for d in series]
        rec["dimension_sizes"] = {d["id"]: len(d["codes"]) for d in series}
        rec["time_min"], rec["time_max"] = (times[0], times[-1]) if times else (None, None)
        rec["n_time"] = len(times)
        print(f"      dims {rec['dimension_order']}  time "
              f"{rec['time_min']}..{rec['time_max']}")

        by_id = {d["id"]: d["codes"] for d in series}
        if ed in FULL_CODES_FOR:
            rec["full_codes"] = {d["id"]: d["codes"] for d in series}

        # 2. choose codes by NAME so this works under either scheme
        area_dim = "REF_AREA" if "REF_AREA" in by_id else "COUNTRY"
        meas_dim = "MEASURE" if "MEASURE" in by_id else "VARIABLE"
        wheat = pick(by_id.get("COMMODITY", []), "wheat")
        world = pick(by_id.get(area_dim, []), "world")
        price = (pick(by_id.get(meas_dim, []), "world price")
                 or pick(by_id.get(meas_dim, []), "producer price")
                 or pick(by_id.get(meas_dim, []), "price"))
        chosen = {"commodity": wheat, "area": world, "measure": price,
                  "area_dim": area_dim, "measure_dim": meas_dim}
        rec["chosen_codes"] = chosen
        print(f"      picked  wheat={wheat and wheat['id']}  "
              f"world={world and world['id']}  price={price and price['id']}")

        # 3. one narrow query built from those codes
        if wheat and world and price:
            parts = []
            for d in series:
                if d["id"] == area_dim:
                    parts.append(world["id"])
                elif d["id"] == "COMMODITY":
                    parts.append(wheat["id"])
                elif d["id"] == meas_dim:
                    parts.append(price["id"])
                else:
                    parts.append("")
            flt = ".".join(parts)
            rd = get(f"{LEGACY}/SDMX-JSON/data/{ed}/{flt}/all", f"{ed} {flt}")
            b2 = rd.pop("_body", None)
            rec["narrow_query"] = {k: v for k, v in rd.items() if k != "_body"}
            rec["narrow_query"]["filter"] = flt
            if b2:
                try:
                    s2, t2, data2 = structure_of(b2)
                    ds = (data2.get("dataSets") or [{}])[0]
                    vals = {}
                    for skey, sv in list((ds.get("series") or {}).items())[:4]:
                        vals[skey] = {t2[int(i)] if int(i) < len(t2) else i:
                                      (o[0] if isinstance(o, list) else o)
                                      for i, o in sv.get("observations", {}).items()}
                    rec["narrow_query"]["units"] = [
                        {d["id"]: [c["name"] for c in d["codes"]][:4]}
                        for d in s2 if d["id"] in ("UNIT_MEASURE",)]
                    rec["narrow_query"]["values"] = vals
                    some = next(iter(vals.values()), {})
                    yrs = sorted(some, key=lambda x: str(x))
                    print(f"      VALUES: {len(some)} obs, "
                          f"{yrs[:1]}..{yrs[-1:]}  e.g. "
                          f"{[(y, some[y]) for y in yrs[-3:]]}")
                except Exception as e:                       # noqa: BLE001
                    rec["narrow_query"]["parse_error"] = f"{type(e).__name__}: {e}"
        out["editions"][ed] = rec
        print()

    os.makedirs("data", exist_ok=True)
    path = "data/_oecd-fao-probe.json"
    with open(path, "w") as fh:
        json.dump(out, fh, indent=1, default=str)
    print(f"  wrote {path} ({os.path.getsize(path):,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
