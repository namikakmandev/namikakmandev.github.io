#!/usr/bin/env python3
"""Discovery probe for the ECB Survey of Professional Forecasters.

The study: the SPF has run quarterly since 1999, and forecasters submit
probability DISTRIBUTIONS, not just point forecasts. That makes it scorable the
way FiveThirtyEight's archive was — the question is not whether the midpoint was
right but whether the stated uncertainty was honest. In 2021 the panel put
almost no probability on euro-area inflation above 4%; it reached 8.4%.

Two things have to exist for that study:
  A) the SPF probability distributions, by survey round and horizon
  B) realised HICP inflation, which is routine

This probe establishes what is actually served, and nothing else. It parses
nothing, assumes no dimension names, and decides nothing. The lesson from the
OECD attempt is written into it: check the response SIZE against what the query
should return, because a filter that is silently ignored looks exactly like a
filter that worked.

Runs in GitHub Actions; the dev sandbox cannot reach the ECB.

  python3 scripts/probe_ecb_spf.py     # -> data/_ecb-spf-probe.json
"""
import gzip, io, json, os, sys, urllib.error, urllib.request, zlib
from datetime import datetime, timezone

API = "https://data-api.ecb.europa.eu/service"
TIMEOUT = 120
MAX_BYTES = 30_000_000
HEAD = 2500
UA = "namikakmandev-data-probe/1.0 (+https://namikakmandev.github.io)"

ROUTES = [
    # 1. what dataflows exist at all, and which mention the survey
    ("dataflow_all", f"{API}/dataflow/ECB?format=sdmx-json"),
    # 2. the SPF structure — dimension names, before assuming any of them
    ("spf_datastructure",
     f"{API}/datastructure/ECB/ECB_SPF1?references=children&format=sdmx-json"),
    # 3. series keys only: cheap, and shows how the cube is laid out
    ("spf_serieskeys",
     f"{API}/data/SPF?detail=serieskeysonly&format=csvdata"),
    # 4. one observation per series — the smallest real data request
    ("spf_lastobs", f"{API}/data/SPF?lastNObservations=1&format=csvdata"),
    # 5. actuals: euro-area HICP, annual rate of change
    ("hicp_actual",
     f"{API}/data/ICP/M.U2.N.000000.4.ANR?startPeriod=2018-01&format=csvdata"),
]


def get(url, note):
    rec = {"name": note, "url": url}
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "*/*", "Accept-Encoding": "gzip, deflate"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            raw = r.read(MAX_BYTES)
            rec["truncated_at_cap"] = len(raw) >= MAX_BYTES
            enc = (r.headers.get("Content-Encoding") or "").lower()
            if "gzip" in enc:
                raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
            elif "deflate" in enc:
                raw = zlib.decompress(raw, -zlib.MAX_WBITS)
            rec.update(status=r.status, bytes=len(raw),
                       content_type=r.headers.get("Content-Type", ""))
            text = raw.decode("utf-8", "replace")
            rec["head"] = text[:HEAD]
            if "csv" in rec["content_type"].lower() or text[:200].count(",") > 3:
                lines = text.splitlines()
                rec["csv_header"] = lines[0] if lines else ""
                rec["csv_rows"] = len(lines) - 1
                rec["csv_sample"] = lines[1:6]
            else:
                try:
                    j = json.loads(text)
                    rec["json_top_keys"] = list(j)[:20]
                    blob = json.dumps(j)
                    rec["mentions_spf"] = blob.upper().count("SPF")
                except Exception:
                    pass
    except urllib.error.HTTPError as e:
        body = (e.read(HEAD) or b"").decode("utf-8", "replace")
        rec.update(status=e.code, error=f"HTTPError {e.code}", head=body)
    except Exception as e:                                   # noqa: BLE001
        rec.update(status=None, error=f"{type(e).__name__}: {e}")
    print(f"  {str(rec.get('status')):>5}  {rec.get('bytes', 0):>10,}b  "
          f"rows={str(rec.get('csv_rows', '-')):>8}  {note}  "
          f"{str(rec.get('error', ''))[:50]}")
    return rec


def main():
    print("ECB Survey of Professional Forecasters — discovery probe")
    print("  can the probability distributions be retrieved, and the actuals\n")
    out = {"probed_at": datetime.now(timezone.utc).isoformat(),
           "probed_by": "scripts/probe_ecb_spf.py",
           "question": ("Are the SPF probability distributions retrievable by "
                        "survey round and horizon, and is realised HICP "
                        "available to score them against?"),
           "routes": [get(u, n) for n, u in ROUTES]}
    ok = [r for r in out["routes"] if r.get("status") == 200]
    out["summary"] = {"n_ok": len(ok), "ok": [r["name"] for r in ok]}
    os.makedirs("data", exist_ok=True)
    path = "data/_ecb-spf-probe.json"
    with open(path, "w") as fh:
        json.dump(out, fh, indent=1)
    print(f"\n  {len(ok)}/{len(out['routes'])} answered: "
          f"{[r['name'] for r in ok]}")
    print(f"  wrote {path} ({os.path.getsize(path):,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
