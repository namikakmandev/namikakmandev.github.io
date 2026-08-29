#!/usr/bin/env python3
"""ECB Survey of Professional Forecasters — probe round 2: does filtering work?

Round 1 confirmed the study is possible. The SPF serves 470,979 series and the
rows are microdata, one per forecaster per probability bucket:

    SPF.A.U2.CORE.F2_0T2_4.P6M.Q.100
    "Forecaster 100 - Probability assigned to outcome - Core inflation from
     2.0 to 2.4 - Target period ends 6 months after survey round"

Dimension order, from the CSV header:
    FREQ . REF_AREA . FCT_TOPIC . FCT_BREAKDOWN . FCT_HORIZON . SURVEY_FREQ
    . FCT_SOURCE

Round 1's unfiltered requests both hit the 30MB read cap, so before building
anything this checks the one thing that wrecked the OECD attempt: whether a
narrowed request actually returns less. A filter that is silently ignored looks
exactly like a filter that worked, and the only tell is the response size.

Each request below is paired with what it SHOULD return, and the probe reports
the ratio rather than leaving it to be eyeballed later.

  python3 scripts/probe_ecb_spf.py     # -> data/_ecb-spf-probe.json
"""
import csv, gzip, io, json, os, sys, urllib.error, urllib.request, zlib
from collections import Counter
from datetime import datetime, timezone

API = "https://data-api.ecb.europa.eu/service"
TIMEOUT = 180
MAX_BYTES = 30_000_000
UA = "namikakmandev-data-probe/2.0 (+https://namikakmandev.github.io)"

# (name, url, what a working filter should do)
ROUTES = [
    ("baseline_all_keys",
     f"{API}/data/SPF?detail=serieskeysonly&format=csvdata",
     "everything — the yardstick the filtered calls must come in under"),
    ("keys_hicp_only",
     f"{API}/data/SPF/..HICP....?detail=serieskeysonly&format=csvdata",
     "HICP topic only — must be much smaller than baseline"),
    ("keys_hicp_2022",
     f"{API}/data/SPF/..HICP..2022..?detail=serieskeysonly&format=csvdata",
     "HICP, target year 2022 — smaller again"),
    ("data_hicp_2022_round2021",
     f"{API}/data/SPF/..HICP..2022..?startPeriod=2021&endPeriod=2021"
     f"&format=csvdata",
     "the real slice: every forecaster's 2022 distribution, as seen in 2021"),
    ("data_hicp_point_2022",
     f"{API}/data/SPF/..HICP.POINT.2022..?format=csvdata",
     "point forecasts for 2022, all survey rounds"),
]


def get(url, note):
    rec = {"name": note, "url": url}
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "*/*", "Accept-Encoding": "gzip, deflate"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            raw = r.read(MAX_BYTES)
            rec["hit_cap"] = len(raw) >= MAX_BYTES
            enc = (r.headers.get("Content-Encoding") or "").lower()
            if "gzip" in enc:
                raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
            elif "deflate" in enc:
                raw = zlib.decompress(raw, -zlib.MAX_WBITS)
            rec.update(status=r.status, bytes=len(raw))
            text = raw.decode("utf-8", "replace")
            rows = list(csv.DictReader(io.StringIO(text)))
            rec["rows"] = len(rows)
            if rows:
                rec["columns"] = list(rows[0])
                for dim in ("FCT_TOPIC", "FCT_BREAKDOWN", "FCT_HORIZON",
                            "FCT_SOURCE", "TIME_PERIOD", "FREQ"):
                    if dim in rows[0]:
                        vals = Counter(r.get(dim) for r in rows)
                        rec[f"distinct_{dim}"] = len(vals)
                        rec[f"top_{dim}"] = vals.most_common(14)
                rec["sample"] = [
                    {k: v for k, v in r.items()
                     if k in ("KEY", "FCT_BREAKDOWN", "FCT_HORIZON",
                              "FCT_SOURCE", "TIME_PERIOD", "OBS_VALUE",
                              "TITLE_COMPL")}
                    for r in rows[:6]]
    except urllib.error.HTTPError as e:
        rec.update(status=e.code, error=f"HTTPError {e.code}",
                   head=(e.read(600) or b"").decode("utf-8", "replace"))
    except Exception as e:                                   # noqa: BLE001
        rec.update(status=None, error=f"{type(e).__name__}: {e}")
    print(f"  {str(rec.get('status')):>5} {rec.get('bytes', 0):>11,}b "
          f"rows={rec.get('rows', 0):>8,} cap={str(rec.get('hit_cap', False)):<5} "
          f"{note}  {str(rec.get('error', ''))[:40]}")
    return rec


def main():
    print("ECB SPF — probe round 2: proving the filter actually filters\n")
    out = {"probed_at": datetime.now(timezone.utc).isoformat(),
           "probed_by": "scripts/probe_ecb_spf.py (round 2)",
           "round1": ("SPF serves 470,979 series as per-forecaster probability "
                      "microdata; HICP actuals available; dimension order is "
                      "FREQ.REF_AREA.FCT_TOPIC.FCT_BREAKDOWN.FCT_HORIZON."
                      "SURVEY_FREQ.FCT_SOURCE"),
           "question": ("Does a narrowed request return less? If not, the study "
                        "cannot be built the way the OECD one could not."),
           "routes": []}
    for name, url, expect in ROUTES:
        r = get(url, name)
        r["expectation"] = expect
        out["routes"].append(r)

    base = next((r for r in out["routes"] if r["name"] == "baseline_all_keys"),
                {})
    b_rows = base.get("rows") or 0
    verdict = {}
    for r in out["routes"][1:]:
        if r.get("rows") is not None and b_rows:
            ratio = r["rows"] / b_rows
            verdict[r["name"]] = {"rows": r["rows"], "share_of_baseline": round(ratio, 4),
                                  "filter_worked": ratio < 0.9}
    out["verdict"] = verdict
    out["filter_works"] = all(v["filter_worked"] for v in verdict.values()) \
        if verdict else None

    print("\n  filter check:")
    for k, v in verdict.items():
        print(f"    {k:<26} {v['rows']:>8,} rows  "
              f"{v['share_of_baseline'] * 100:>6.2f}% of baseline  "
              f"{'OK' if v['filter_worked'] else 'IGNORED'}")
    print(f"\n  filters work: {out['filter_works']}")

    os.makedirs("data", exist_ok=True)
    path = "data/_ecb-spf-probe.json"
    with open(path, "w") as fh:
        json.dump(out, fh, indent=1)
    print(f"  wrote {path} ({os.path.getsize(path):,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
