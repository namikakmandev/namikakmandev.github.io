#!/usr/bin/env python3
"""Collect the ECB Survey of Professional Forecasters, and what actually happened.

The SPF asks professional forecasters for a probability DISTRIBUTION over
euro-area inflation, not just a number, and the ECB publishes every individual
response. That makes the honest question answerable: not "was the midpoint
right" but "was the stated uncertainty truthful".

Each row is one forecaster's probability for one outcome bucket, for one target
year, in one survey round:

    SPF.Q.U2.HICP.F4_0.2022.Q.001  ->  survey 2021-Q1, forecaster 001,
                                       P(2022 inflation >= 4.0%) = 0

The buckets are half-point wide and the TOP one is open-ended at 4.0% or more,
which is itself part of the story: 2022 came in at 8.4%, far outside the range
the survey form even offered.

Dimension order (verified from the CSV header, not assumed):
    FREQ . REF_AREA . FCT_TOPIC . FCT_BREAKDOWN . FCT_HORIZON . SURVEY_FREQ
    . FCT_SOURCE

Filtering was verified to genuinely narrow the response before this was
written — a target-year query returns 0.34% of the unfiltered rows.

  python3 scripts/fetch_ecb_spf.py
"""
import argparse, csv, gzip, io, json, os, sys, time, urllib.error, urllib.request, zlib
from collections import defaultdict
from datetime import date

API = "https://data-api.ecb.europa.eu/service"
TIMEOUT = 180
UA = "namikakmandev-data/1.0 (+https://namikakmandev.github.io)"
TARGET_YEARS = list(range(2000, 2026))


def fetch(url, tries=3):
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
                return raw.decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (404, 400):
                return None
            if attempt == tries - 1:
                return None
        except Exception:                                    # noqa: BLE001
            if attempt == tries - 1:
                return None
        time.sleep(2 * (attempt + 1))
    return None


def rows_of(text):
    return list(csv.DictReader(io.StringIO(text))) if text else []


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="data/ecb-spf.json")
    args = ap.parse_args(argv)

    print("ECB Survey of Professional Forecasters")
    forecasts = []          # one row per (target, round, forecaster, bucket)
    buckets_seen, misses = set(), []

    for target in TARGET_YEARS:
        text = fetch(f"{API}/data/SPF/..HICP..{target}..?format=csvdata")
        rs = rows_of(text)
        if not rs:
            misses.append({"target": target, "error": "no rows"})
            print(f"  {target}: —")
            continue
        kept = 0
        for r in rs:
            val = (r.get("OBS_VALUE") or "").strip()
            if val == "":
                continue
            try:
                v = float(val)
            except ValueError:
                continue
            b = r.get("FCT_BREAKDOWN") or ""
            buckets_seen.add(b)
            forecasts.append({
                "target": target,
                "round": r.get("TIME_PERIOD"),
                "who": r.get("FCT_SOURCE"),
                "bucket": b,
                "v": v,
            })
            kept += 1
        rounds = len({r["round"] for r in forecasts if r["target"] == target})
        who = len({r["who"] for r in forecasts if r["target"] == target})
        print(f"  {target}: {kept:>6,} values, {rounds:>3} survey rounds, "
              f"{who:>3} forecasters")

    # what actually happened: euro-area HICP, annual rate of change
    print("\n  realised HICP")
    actual = {}
    for key, label in (("A.U2.N.000000.4.ANR", "annual"),
                       ("M.U2.N.000000.4.ANR", "monthly")):
        text = fetch(f"{API}/data/ICP/{key}?format=csvdata")
        rs = rows_of(text)
        if not rs:
            continue
        if label == "annual":
            for r in rs:
                try:
                    actual[int(r["TIME_PERIOD"])] = float(r["OBS_VALUE"])
                except (ValueError, KeyError, TypeError):
                    pass
            print(f"    annual series: {len(actual)} years")
            break
        # fall back to averaging the monthly annual-rate series
        by_year = defaultdict(list)
        for r in rs:
            try:
                by_year[int(str(r["TIME_PERIOD"])[:4])].append(
                    float(r["OBS_VALUE"]))
            except (ValueError, KeyError, TypeError):
                pass
        actual = {y: round(sum(v) / len(v), 3)
                  for y, v in by_year.items() if len(v) == 12}
        print(f"    monthly averaged to {len(actual)} complete years")

    doc = {
        "source": "ECB Survey of Professional Forecasters, and ECB HICP",
        "source_url": "https://data.ecb.europa.eu/",
        "note": ("Individual forecaster probability distributions over euro-area "
                 "inflation, by target year and survey round, published openly by "
                 "the ECB. The top bucket is open-ended at 4.0% or more."),
        "fetched_by": "scripts/fetch_ecb_spf.py",
        "fetched_at": date.today().isoformat(),
        "dimension_order": ("FREQ.REF_AREA.FCT_TOPIC.FCT_BREAKDOWN.FCT_HORIZON."
                            "SURVEY_FREQ.FCT_SOURCE"),
        "buckets": sorted(buckets_seen),
        "n_forecasts": len(forecasts),
        "n_misses": len(misses), "misses": misses,
        "actual_hicp": {str(k): v for k, v in sorted(actual.items())},
        "forecasts": forecasts,
    }
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as fh:
        json.dump(doc, fh, separators=(",", ":"))
    size = os.path.getsize(args.out)
    print(f"\n  {len(forecasts):,} forecast values, {len(actual)} actual years")
    print(f"  buckets: {sorted(buckets_seen)}")
    print(f"  wrote {args.out} ({size:,} bytes)")
    if size > 60_000_000:
        print("  ERROR: output far larger than expected")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
