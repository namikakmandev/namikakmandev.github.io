#!/usr/bin/env python3
"""Discovery probe for the OECD-FAO Agricultural Outlook — round 2.

Round 1 answered the only question that could have killed the study: the
retired OECD.Stat editions are still served. HIGH_AGLINK_2015 through
HIGH_AGLINK_2023 all return SDMX-JSON, which means an old edition's ten-year
projections can be recovered and scored against what actually happened.

Round 2 works out how to read them. It is adaptive: fetch the data structure
first, learn the real dimension order and codes, then use those to pull a small
labelled slice. Nothing here is written against the API docs — every query is
built from what the previous response actually said.

What it has to establish:
  1. the dimension ids and order for an old edition (needed to filter at all)
  2. which codes carry commodities, variables and countries
  3. that the observations hold real numbers, not the zeros round 1 saw
  4. whether an old edition and a recent one share codes, so projections can be
     scored against the same database's later history

Runs in GitHub Actions; the dev sandbox cannot reach OECD.

  python3 scripts/probe_oecd_fao.py     # -> data/_oecd-fao-probe.json
"""
import json, os, sys, urllib.error, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

TIMEOUT = 120
MAX_BYTES = 40_000_000
UA = "namikakmandev-data-probe/2.0 (+https://namikakmandev.github.io)"
LEGACY = "https://stats.oecd.org"
EDITIONS = ("HIGH_AGLINK_2015", "HIGH_AGLINK_2023")
NS = {"s": "http://www.SDMX.org/resources/SDMXML/schemas/v2_0/structure",
      "m": "http://www.SDMX.org/resources/SDMXML/schemas/v2_0/message"}


def get(url, note=""):
    """Fetch, never raise. -> (status, bytes|None, error)."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            body = r.read(MAX_BYTES)
            print(f"    {r.status}  {len(body):>10,}b  {note or url[:70]}")
            return r.status, body, None
    except urllib.error.HTTPError as e:
        print(f"    {e.code}  {'':>10}   {note or url[:70]}  HTTPError")
        return e.code, None, f"HTTPError {e.code}"
    except Exception as e:                                   # noqa: BLE001
        print(f"      -  {'':>10}   {note or url[:70]}  {type(e).__name__}")
        return None, None, f"{type(e).__name__}: {e}"


def parse_dsd(body):
    """-> {dimension_id: {'codelist':.., 'n':.., 'sample':[(code,label)..]}}."""
    root = ET.fromstring(body)
    codelists = {}
    for cl in root.iter():
        if cl.tag.endswith("}CodeList") or cl.tag.endswith("}Codelist"):
            cid = cl.get("id")
            codes = []
            for c in cl:
                if not c.tag.endswith("}Code"):
                    continue
                val = c.get("value") or c.get("id")
                label = ""
                for d in c:
                    if d.tag.endswith("}Description") or d.tag.endswith("}Name"):
                        label = (d.text or "").strip()
                        break
                codes.append((val, label))
            codelists[cid] = codes

    dims = {}
    order = []
    for d in root.iter():
        if d.tag.endswith("}Dimension") and d.get("conceptRef"):
            did = d.get("conceptRef")
            if did in dims:
                continue
            order.append(did)
            cl = codelists.get(d.get("codelist"), [])
            dims[did] = {"codelist": d.get("codelist"), "n": len(cl),
                         "sample": cl[:30]}
    return order, dims, {k: len(v) for k, v in codelists.items()}


def summarise_data(body, note):
    """Pull real observations out of an SDMX-JSON response."""
    j = json.loads(body)
    data = j.get("data", j)
    out = {"note": note}
    structs = data.get("structures") or ([data["structure"]]
                                         if "structure" in data else [])
    if structs:
        st = structs[0]
        obsdims = st.get("dimensions", {}).get("observation", [])
        serdims = st.get("dimensions", {}).get("series", [])
        out["series_dimensions"] = [
            {"id": d.get("id"), "name": d.get("name"),
             "n": len(d.get("values", [])),
             "first": [v.get("id") for v in d.get("values", [])[:8]]}
            for d in serdims]
        out["observation_dimensions"] = [
            {"id": d.get("id"), "n": len(d.get("values", [])),
             "first": [v.get("id") for v in d.get("values", [])[:12]]}
            for d in obsdims]
    ds = (data.get("dataSets") or [{}])[0]
    obs = ds.get("observations")
    series = ds.get("series")
    samples = []
    if series:
        for k, v in list(series.items())[:6]:
            samples.append({"series_key": k,
                            "observations": dict(list(
                                v.get("observations", {}).items())[:12])})
    elif obs:
        samples = [{"obs_key": k, "value": v}
                   for k, v in list(obs.items())[:12]]
    out["samples"] = samples
    out["n_series"] = len(series or {})
    out["n_observations"] = len(obs or {})
    return out


def main():
    print("OECD-FAO Agricultural Outlook — discovery probe, round 2")
    print("  round 1 confirmed the retired editions still serve data;")
    print("  this works out how to read them.\n")
    out = {"probed_at": datetime.now(timezone.utc).isoformat(),
           "probed_by": "scripts/probe_oecd_fao.py (round 2)",
           "round1_finding": ("HIGH_AGLINK_2015..2023 all return 200 SDMX-JSON "
                              "from stats.oecd.org; 2024 and the FAO routes 404"),
           "editions": {}}

    for ed in EDITIONS:
        print(f"  {ed}")
        rec = {}
        # 1. the data structure, which is the only way to learn dimension order
        status, body, err = get(
            f"{LEGACY}/restsdmx/sdmx.ashx/GetDataStructure/{ed}", f"{ed} DSD")
        rec["dsd_status"] = status
        rec["dsd_error"] = err
        order = []
        if body:
            try:
                order, dims, cl_sizes = parse_dsd(body)
                rec["dimension_order"] = order
                rec["dimensions"] = dims
                rec["codelist_sizes"] = cl_sizes
                print(f"      dimensions: {order}")
            except Exception as e:                           # noqa: BLE001
                rec["dsd_parse_error"] = f"{type(e).__name__}: {e}"
                rec["dsd_head"] = body[:1500].decode("utf-8", "replace")

        # 2. a deliberately tiny slice, so the whole JSON arrives intact and the
        #    structures block is not truncated the way round 1's was
        filt = ".".join("" for _ in order) if order else "all"
        for label, url in (
            ("tiny_all_dims",
             f"{LEGACY}/SDMX-JSON/data/{ed}/{filt}/all"
             f"?startTime=2024&endTime=2024"),
            ("one_year_series",
             f"{LEGACY}/SDMX-JSON/data/{ed}/{filt}/all"
             f"?startTime=2023&endTime=2024&dimensionAtObservation=TIME_PERIOD"),
        ):
            st, b, e = get(url, f"{ed} {label}")
            entry = {"status": st, "error": e, "url": url,
                     "bytes": len(b) if b else 0}
            if b:
                try:
                    entry.update(summarise_data(b, label))
                except Exception as ex:                      # noqa: BLE001
                    entry["parse_error"] = f"{type(ex).__name__}: {ex}"
                    entry["head"] = b[:1200].decode("utf-8", "replace")
            rec[label] = entry
        out["editions"][ed] = rec
        print()

    os.makedirs("data", exist_ok=True)
    path = "data/_oecd-fao-probe.json"
    with open(path, "w") as fh:
        json.dump(out, fh, indent=1)
    print(f"  wrote {path} ({os.path.getsize(path):,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
