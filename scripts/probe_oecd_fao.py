#!/usr/bin/env python3
"""Discovery probe for the OECD-FAO Agricultural Outlook — round 3.

Where the earlier rounds got to:
  1. The retired OECD.Stat editions are still served. HIGH_AGLINK_2015 through
     _2023 all answer with SDMX-JSON. The study is possible.
  2. Reading them failed twice, for two fixable reasons. The structure request
     came back as bytes that would not parse as XML at column 0 — a gzipped
     body this script never decompressed. And with no dimension order parsed,
     the data filter fell back to all/all, which asks for the whole database
     and truncated at the read cap every time.

Round 3 fixes both and stops asking for observations it does not need:

  - decompress gzip/deflate before parsing anything
  - use detail=nodata, which returns the full dimension structure with no
    observations at all, so the response is small enough to arrive intact
  - dump what the structure documents actually contain — root tag, distinct
    element names, a head — rather than assuming a schema version
  - only once the dimension order is known, build one narrow data query and
    show real labelled values

Runs in GitHub Actions; the dev sandbox cannot reach OECD.

  python3 scripts/probe_oecd_fao.py     # -> data/_oecd-fao-probe.json
"""
import gzip, io, json, os, sys, urllib.error, urllib.request, zlib
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone

TIMEOUT = 180
MAX_BYTES = 60_000_000
UA = "namikakmandev-data-probe/3.0 (+https://namikakmandev.github.io)"
LEGACY = "https://stats.oecd.org"
EDITIONS = ("HIGH_AGLINK_2015", "HIGH_AGLINK_2023")


def get(url, note=""):
    """Fetch and decompress. -> dict with status, body, truncated, error."""
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "*/*", "Accept-Encoding": "gzip, deflate"})
    rec = {"url": url}
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            raw = r.read(MAX_BYTES)
            enc = (r.headers.get("Content-Encoding") or "").lower()
            rec["content_encoding"] = enc
            rec["content_type"] = r.headers.get("Content-Type", "")
            rec["raw_bytes"] = len(raw)
            rec["truncated"] = len(raw) >= MAX_BYTES
            if "gzip" in enc:
                try:
                    raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
                except Exception as e:                       # noqa: BLE001
                    rec["gunzip_error"] = str(e)
            elif "deflate" in enc:
                try:
                    raw = zlib.decompress(raw, -zlib.MAX_WBITS)
                except Exception as e:                       # noqa: BLE001
                    rec["inflate_error"] = str(e)
            rec["status"] = r.status
            rec["bytes"] = len(raw)
            rec["_body"] = raw
    except urllib.error.HTTPError as e:
        rec.update(status=e.code, error=f"HTTPError {e.code}")
    except Exception as e:                                   # noqa: BLE001
        rec.update(status=None, error=f"{type(e).__name__}: {e}")
    print(f"    {str(rec.get('status')):>5}  {rec.get('bytes', 0):>11,}b  "
          f"enc={rec.get('content_encoding', '-') or '-':<8} "
          f"trunc={str(rec.get('truncated', False)):<5} {note}")
    return rec


def describe_xml(body):
    """Say what an XML document actually is, without assuming a schema."""
    out = {}
    head = body[:2500].decode("utf-8", "replace")
    out["head"] = head
    try:
        root = ET.fromstring(body)
    except Exception as e:                                   # noqa: BLE001
        out["parse_error"] = f"{type(e).__name__}: {e}"
        return out
    out["root_tag"] = root.tag
    tags = Counter(el.tag.split("}")[-1] for el in root.iter())
    out["element_counts"] = dict(tags.most_common(25))
    # Dimensions, whatever the schema version calls them
    dims = []
    for el in root.iter():
        if el.tag.endswith("}Dimension") or el.tag.endswith("Dimension"):
            dims.append({"id": el.get("id") or el.get("conceptRef"),
                         "codelist": el.get("codelist"),
                         "position": el.get("position"),
                         "attrs": {k: v for k, v in el.attrib.items()}})
    out["dimensions_found"] = dims[:30]
    return out


def describe_sdmx_json(body):
    """Pull dimension ids, sizes and sample codes out of an SDMX-JSON body."""
    out = {}
    try:
        j = json.loads(body)
    except Exception as e:                                   # noqa: BLE001
        out["parse_error"] = f"{type(e).__name__}: {e}"
        out["head"] = body[:1200].decode("utf-8", "replace")
        out["tail"] = body[-400:].decode("utf-8", "replace")
        return out
    data = j.get("data", j)
    structs = data.get("structures") or (
        [data["structure"]] if "structure" in data else [])
    if not structs:
        out["top_keys"] = list(j)
        return out
    st = structs[0]
    dd = st.get("dimensions", {})
    for slot in ("series", "observation", "dataSet"):
        vals = dd.get(slot) or []
        if not vals:
            continue
        out[f"dims_{slot}"] = [
            {"id": d.get("id"), "name": d.get("name"),
             "n": len(d.get("values", [])),
             "sample": [{"id": v.get("id"), "name": v.get("name")}
                        for v in d.get("values", [])[:12]]}
            for d in vals]
    ds = (data.get("dataSets") or [{}])[0]
    out["n_series"] = len(ds.get("series") or {})
    out["n_observations"] = len(ds.get("observations") or {})
    return out


def main():
    print("OECD-FAO Agricultural Outlook — discovery probe, round 3")
    print("  fixing gzip and the all/all blowup; asking for structure, not data\n")
    out = {"probed_at": datetime.now(timezone.utc).isoformat(),
           "probed_by": "scripts/probe_oecd_fao.py (round 3)",
           "prior_findings": {
               "round1": "HIGH_AGLINK_2015..2023 serve SDMX-JSON; 2024 and FAO 404",
               "round2": ("structure body unparseable at col 0 (gzip, never "
                          "decompressed) and all/all data requests truncated at "
                          "the read cap")},
           "editions": {}}

    for ed in EDITIONS:
        print(f"  {ed}")
        rec = {}
        # structure without observations — the whole point of detail=nodata
        for label, url in (
            ("json_nodata",
             f"{LEGACY}/SDMX-JSON/data/{ed}/all/all?detail=nodata"),
            ("json_serieskeysonly",
             f"{LEGACY}/SDMX-JSON/data/{ed}/all/all?detail=serieskeysonly"),
            ("dsd_xml",
             f"{LEGACY}/restsdmx/sdmx.ashx/GetDataStructure/{ed}"),
        ):
            r = get(url, f"{ed} {label}")
            body = r.pop("_body", None)
            if body:
                r.update(describe_xml(body) if label == "dsd_xml"
                         else describe_sdmx_json(body))
            rec[label] = r
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
